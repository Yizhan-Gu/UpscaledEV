#!/usr/bin/env python3
"""Independent validation experiments for the two base EV+BESS MPC notebooks.

This file deliberately does not edit either source notebook.  It provides:

1. isolated June reruns of the existing Shrinking/Rolling 2x2 scenario grids;
2. a full-June perfect-information oracle using the realized EV sessions and the
   same retail/wholesale physical and two-settlement equations;
3. selected-day matched-state RT experiments in which the initial SOC, demand
   thresholds, and DA commitments are held fixed while only the RT forecast is
   changed between Perfect and Persistence;
4. machine-readable validation summaries under Validation_Results/June_2025.

Temporary execution workspaces are removed automatically.  Persistent outputs
are CSV/Markdown results only; no executed notebook copies are created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import gurobipy as gp
import holidays
import nbformat
import numpy as np
import pandas as pd
from gurobipy import GRB
from scipy import sparse


REPO = Path(__file__).resolve().parent
OUT_ROOT = REPO / "Validation_Results" / "June_2025"
SCRATCH_ROOT = Path("/private/tmp/upscaledev_june_validation")
DT_H = 0.25
GRID = pd.date_range("2025-06-01", "2025-07-01", freq="15min", inclusive="left")
N = len(GRID)

NOTEBOOKS = {
    "shrinking": "upscaledev_imp_shrinkingMPC.ipynb",
    "rolling": "upscaledev_imp_rollingMPC.ipynb",
}
RESULT_DIRS = {
    "shrinking": "Results_Shrinking",
    "rolling": "Results_Rolling",
}
FORECAST_PREFIX = {
    "perfect": "2025_PerfectSessionkWh_PerfectNumbEV_PerfectatArrival",
    "persistence": "2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival",
}


def _source(cell) -> str:
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else str(src)


def _find_cell(nb, marker: str, exclude: str | None = None) -> str:
    for cell in nb.cells:
        if cell.get("cell_type") != "code":
            continue
        src = _source(cell)
        if marker in src and (exclude is None or exclude not in src):
            return src
    raise RuntimeError(f"Notebook cell containing {marker!r} was not found")


def _prepare_scratch(controller: str, tag: str) -> Path:
    scratch = SCRATCH_ROOT / f"{controller}_{tag}"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    (scratch / "2025Data").symlink_to(REPO / "2025Data", target_is_directory=True)
    (scratch / "forecast_ED_PD.py").symlink_to(REPO / "forecast_ED_PD.py")
    shutil.copy2(REPO / NOTEBOOKS[controller], scratch / NOTEBOOKS[controller])
    # Both notebooks read the shared Shrinking baseline inputs from
    # Results_Shrinking/Dispatch. Rolling writes implementation results to
    # Results_Rolling.
    (scratch / "Results_Shrinking" / "Dispatch").mkdir(parents=True)
    (scratch / "Results_Shrinking" / "Plots").mkdir(parents=True)
    for baseline in (REPO / "Results_Shrinking" / "Dispatch").glob("*baseline.csv"):
        shutil.copy2(baseline, scratch / "Results_Shrinking" / "Dispatch" / baseline.name)
    (scratch / "Results_Rolling" / "Dispatch").mkdir(parents=True)
    (scratch / "Results_Rolling" / "Plots").mkdir(parents=True)
    return scratch


def _load_notebook_runtime(controller: str, scratch: Path) -> tuple[dict, object, str, str, str]:
    nb = nbformat.read(REPO / NOTEBOOKS[controller], as_version=4)
    env: dict = {"__name__": "__main__"}
    sys.path.insert(0, str(REPO))
    try:
        for idx in (3, 5, 7, 9):
            src = _source(nb.cells[idx])
            if idx == 3:
                src = re.sub(
                    r"os\.chdir\([^\n]+\)",
                    f"os.chdir({str(scratch)!r})",
                    src,
                    count=1,
                )
            exec(compile(src, f"{NOTEBOOKS[controller]}:cell{idx}", "exec"), env, env)
    finally:
        if sys.path and sys.path[0] == str(REPO):
            sys.path.pop(0)
    main = _find_cell(nb, "Main loop runtime", "Run July-August 2x2")
    # The notebook's 2x2 runner cell contains these marker strings while it
    # searches for the real post-processing cells. Exclude that runner or a
    # validation run can accidentally launch the complete scenario grid.
    runner_marker = "Run July-August 2x2 financial scenarios from the main notebook"
    daily = _find_cell(
        nb,
        "Save WM profit breakdown summary CSV",
        runner_marker,
    )
    summary = _find_cell(
        nb,
        "Run-Period Financial Summary CSVs Only",
        runner_marker,
    )
    main = re.sub(r"RUN_MAIN_LOOP_DIRECT\s*=\s*False", "RUN_MAIN_LOOP_DIRECT = True", main)
    return env, nb, main, daily, summary


def run_isolated_monthly_mpc(
    controller: str,
    days: list[int] | None = None,
    modes: list[str] | None = None,
    forecasts: list[str] | None = None,
    mip_gap: float | None = None,
    formal_tag: str | None = None,
    include_daily_plot: bool = False,
) -> None:
    """Run the source-notebook logic in an isolated June workspace.

    Complete-June defaults preserve the formal output layout. Any subset is
    written below ``short_tests`` and cannot overwrite the formal June snapshot.
    """
    days = list(range(1, 31)) if days is None else sorted(set(days))
    modes = ["full", "retail_only"] if modes is None else list(modes)
    forecasts = ["perfect", "persistence"] if forecasts is None else list(forecasts)
    if not days or any(day < 1 or day > 30 for day in days):
        raise ValueError("June test days must be integers from 1 through 30")
    if any(mode not in {"full", "retail_only"} for mode in modes):
        raise ValueError("MPC modes must be full and/or retail_only")
    if any(forecast not in FORECAST_PREFIX for forecast in forecasts):
        raise ValueError("MPC forecasts must be perfect and/or persistence")
    complete_june = (
        days == list(range(1, 31))
        and forecasts == ["perfect", "persistence"]
    )
    if formal_tag is not None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", formal_tag):
            raise ValueError(
                "formal_tag may contain only letters, numbers, underscore, dot, and dash"
            )
        if not complete_june:
            raise ValueError(
                "A versioned formal run requires all June days and both forecasts"
            )
    elif complete_june:
        raise ValueError(
            "A complete-June MPC run requires --formal-tag so historical formal "
            "results cannot be overwritten"
        )
    gap_tag = "" if mip_gap is None else f"_gap_{mip_gap:.0e}".replace("+", "")
    run_tag = (
        f"days_{days[0]:02d}-{days[-1]:02d}_"
        f"{'-'.join(modes)}_{'-'.join(forecasts)}{gap_tag}"
    )
    out = (
        OUT_ROOT / "formal_runs" / formal_tag / controller
        if formal_tag is not None
        else OUT_ROOT / "short_tests" / controller / "mpc" / run_tag
    )
    if formal_tag is not None and out.exists() and any(out.iterdir()):
        raise FileExistsError(
            f"Versioned formal output already exists and will not be overwritten: {out}"
        )
    scratch = _prepare_scratch(
        controller,
        f"formal_{formal_tag}" if formal_tag is not None else run_tag,
    )
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "mpc_run.log"
    started = time.time()
    old_cwd = Path.cwd()
    try:
        os.chdir(scratch)
        env, _nb, main, daily, summary = _load_notebook_runtime(controller, scratch)
        env.update(
            TARGET_SAVE="RT",
            RUN_MONTHS_CONFIG=[6],
            RUN_DAYS_CONFIG=days,
            RUN_MODES=modes,
            RUN_FORECAST_CONFIGS=[
                (
                    "PerfectSessionkWh" if forecast == "perfect" else "PersistenceSessionkWh",
                    "PerfectNumbEV" if forecast == "perfect" else "PersistenceNumbEV",
                    "PerfectatArrival",
                )
                for forecast in forecasts
            ],
            PLOT_DAILY_6PANEL_DATES="all" if include_daily_plot else [],
            ANALYSIS_DAYS_CONFIG=[],
            SAVE_FINAL_FINANCIAL_FIGURES=False,
            CLEAR_IMPLEMENTATION_AT_RUN_START=True,
        )
        if mip_gap is not None:
            env["GUROBI_MIPGAP"] = float(mip_gap)
        solver_audit_rows: list[dict] = []
        original_rt_recorder = env["_record_rt_solver_status"]

        def _solver_audit_row(problem, stage, date_label, interval_idx=None, case_label=None):
            extra = getattr(getattr(problem, "solver_stats", None), "extra_stats", None)

            def _safe_attr(name):
                try:
                    return float(getattr(extra, name))
                except Exception:
                    return float("nan")

            solver_audit_rows.append({
                "forecast": str(env.get("Fc_SessionkWh", "")),
                "mode": str(env.get("WM_Mode", "")),
                "stage": stage,
                "date": pd.Timestamp(date_label).strftime("%Y-%m-%d"),
                "interval": (
                    int(interval_idx) if interval_idx is not None else pd.NA
                ),
                "case": "" if case_label is None else str(case_label),
                "cvxpy_status": str(problem.status),
                "gurobi_status": getattr(extra, "Status", pd.NA),
                "runtime_s": _safe_attr("Runtime"),
                "mip_gap": _safe_attr("MIPGap"),
                "objective_value": _safe_attr("ObjVal"),
                "objective_bound": _safe_attr("ObjBound"),
                "node_count": _safe_attr("NodeCount"),
                "solution_count": _safe_attr("SolCount"),
            })

        def _record_rt_solver_status_with_audit(problem, date_label, interval_idx, case_label):
            original_rt_recorder(problem, date_label, interval_idx, case_label)
            _solver_audit_row(
                problem,
                "RT",
                date_label,
                interval_idx=interval_idx,
                case_label=case_label,
            )

        env["_record_rt_solver_status"] = _record_rt_solver_status_with_audit
        # Instrument the final DA status after any optional re-optimization.
        # Matching only the unique status-list update makes this resilient to
        # diagnostic code inserted between ``status = prob.status`` and the
        # point where the accepted DA solve is recorded.
        da_status_needle = """        Status_list_DA = Status_list_DA + [status]
"""
        da_status_replacement = """        _record_da_solver_status(prob, H_Start_DA)
        Status_list_DA = Status_list_DA + [status]
"""
        if da_status_needle not in main:
            raise RuntimeError("Could not instrument the DA solver audit")
        main = main.replace(da_status_needle, da_status_replacement, 1)
        env["_record_da_solver_status"] = (
            lambda problem, date_label: _solver_audit_row(
                problem,
                "DA",
                date_label,
            )
        )
        with log_path.open("w") as log:
            class Tee:
                def __init__(self, *streams): self.streams = streams
                def write(self, data):
                    for stream in self.streams: stream.write(data)
                    return len(data)
                def flush(self):
                    for stream in self.streams: stream.flush()
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout = Tee(old_stdout, log)
            sys.stderr = Tee(old_stderr, log)
            try:
                for fc_session, fc_num, fc_arrival in env["RUN_FORECAST_CONFIGS"]:
                    env.update(
                        Fc_SessionkWh=fc_session,
                        Fc_NumbEV=fc_num,
                        Fc_AtArrival=fc_arrival,
                    )
                    for mode in env["RUN_MODES"]:
                        env.update(
                            WM_Mode=mode,
                            Enable_WM=(mode == "full"),
                            RT_SOLVER_STATUS_COUNTS={},
                            RT_SOLVER_LIMIT_EVENTS=[],
                        )
                        try:
                            exec(
                                compile(
                                    main,
                                    f"{NOTEBOOKS[controller]}:main",
                                    "exec",
                                ),
                                env,
                                env,
                            )
                        except SystemExit as exc:
                            raise RuntimeError(
                                f"{controller}/{fc_session}/{mode}: source "
                                "notebook aborted before producing a complete "
                                "scenario"
                            ) from exc
                        if env["RT_SOLVER_LIMIT_EVENTS"]:
                            raise RuntimeError(
                                f"{controller}/{fc_session}/{mode}: RT watchdog triggered: "
                                f"{env['RT_SOLVER_LIMIT_EVENTS'][:3]}"
                            )
                    env["ANALYSIS_DAYS_CONFIG"] = [f"202506{d:02d}" for d in days]
                    exec(compile(daily, f"{NOTEBOOKS[controller]}:daily", "exec"), env, env)
                    exec(compile(summary, f"{NOTEBOOKS[controller]}:summary", "exec"), env, env)
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

        result_root = scratch / RESULT_DIRS[controller]
        for subdir in ("Dispatch", "Plots/Cost", "Validation_Traces"):
            src_root = result_root / subdir
            if not src_root.exists():
                continue
            for src in src_root.rglob("*.csv"):
                rel = src.relative_to(result_root)
                dst = out / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        solver_audit = pd.DataFrame(solver_audit_rows)
        solver_audit.to_csv(out / "solver_audit.csv", index=False)
        pd.DataFrame([{
            "controller": controller,
            "formal_tag": "" if formal_tag is None else formal_tag,
            "runtime_s": time.time() - started,
            "requested_mip_gap": float(env["GUROBI_MIPGAP"]),
            "run_days": ",".join(map(str, days)),
            "run_modes": ",".join(modes),
            "run_forecasts": ",".join(forecasts),
            "solver_audit_rows": len(solver_audit),
            "max_achieved_mip_gap": (
                float(solver_audit["mip_gap"].max())
                if not solver_audit.empty
                else float("nan")
            ),
            "time_limit_events": len(env["RT_SOLVER_LIMIT_EVENTS"]),
            "source_notebook": NOTEBOOKS[controller],
            "source_notebook_sha256": __import__("hashlib").sha256(
                (REPO / NOTEBOOKS[controller]).read_bytes()
            ).hexdigest(),
        }]).to_csv(out / "run_metadata.csv", index=False)
    finally:
        os.chdir(old_cwd)
        if scratch.exists():
            shutil.rmtree(scratch)


def _read_timeseries(
    path: Path,
    time_col: str,
    value_col: str,
    grid: pd.DatetimeIndex = GRID,
) -> np.ndarray:
    df = pd.read_csv(path)
    ts = pd.to_datetime(df[time_col], errors="raise")
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("America/Los_Angeles").dt.tz_localize(None)
    s = pd.Series(pd.to_numeric(df[value_col], errors="coerce").to_numpy(), index=ts)
    s = s[~s.index.duplicated(keep="last")].sort_index().reindex(grid)
    if s.isna().any():
        raise ValueError(f"Missing {value_col} values in {path}: {int(s.isna().sum())}")
    return s.to_numpy(float)


def _load_prices(grid: pd.DatetimeIndex = GRID) -> dict[str, np.ndarray]:
    p = REPO / "2025Data"
    ans = {
        "lmp_da": _read_timeseries(
            p / "LMP/2025/LMP_DA_2025_clean.csv",
            "Datetime",
            "Price($/kWh)",
            grid,
        ),
        "lmp_rt": _read_timeseries(
            p / "LMP/2025/LMP_FM_2025_clean.csv",
            "Datetime",
            "Price($/kWh)",
            grid,
        ),
    }
    for market, rel in (("da", "AS_DAM/AS_price_2025_clear.csv"), ("rt", "AS_RTM/AS_price_2025_clear.csv")):
        df = pd.read_csv(p / rel)
        ts = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert("America/Los_Angeles").dt.tz_localize(None)
        for key, col in (("ru", "RegUp"), ("rd", "RegDown"), ("sp", "Spin"), ("nsp", "NonSpin")):
            s = pd.Series(pd.to_numeric(df[col], errors="coerce").to_numpy(), index=ts)
            s = s[~s.index.duplicated(keep="last")].sort_index()
            if market == "da":
                s = s.reindex(grid, method="ffill")
            else:
                s = s.reindex(grid)
            if s.isna().any():
                raise ValueError(f"Missing {market.upper()} {col} values for June")
            # Native ASMP is $/MW per award interval.  DA is an hourly award
            # represented on four equal 15-min model slots, while each RT ASMP
            # settles one 15-min binding interval.  Both arrays are converted
            # to the common $/kWh-equivalent coefficient used with DT_H * kW.
            interval_scale = 1.0 if market == "da" else 1.0 / DT_H
            ans[f"as_{key}_{market}"] = s.to_numpy(float) * 0.001 * interval_scale
    return ans


def _build_ev_matrix(
    grid: pd.DatetimeIndex = GRID,
) -> tuple[sparse.csr_matrix, np.ndarray, pd.DataFrame]:
    cols = [
        "Interval start", "Interval end", "Session start", "Session end",
        "10-digit UID", "Interval kWh", "Interval max demand kW",
    ]
    df = pd.read_csv(
        REPO / "2025Data/EV_data/UCSD_AllSites_Merge_PostProcessedSession_QC.csv",
        usecols=cols,
        low_memory=False,
    )
    for c in ("Interval start", "Interval end", "Session start", "Session end"):
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["Interval kWh"] = pd.to_numeric(df["Interval kWh"], errors="coerce").fillna(0.0)
    df["Interval max demand kW"] = pd.to_numeric(df["Interval max demand kW"], errors="coerce")
    df = df[
        (df["Interval start"] >= grid[0])
        & (df["Interval start"] < grid[-1] + pd.Timedelta(minutes=15))
    ]
    df = df[(df["Interval start"] >= df["Session start"]) & (df["Interval end"] <= df["Session end"])]
    df = df.sort_values(["Interval start", "10-digit UID"]).reset_index(drop=True)
    n = len(grid)
    grid_loc = pd.Series(np.arange(n), index=grid)
    df["t"] = df["Interval start"].map(grid_loc)
    if df["t"].isna().any():
        raise ValueError("EV data contain intervals outside the selected 15-minute grid")

    upper = np.empty(len(df), dtype=float)
    session_rows: list[dict] = []
    group_index: list[np.ndarray] = []
    for uid, g in df.groupby("10-digit UID", sort=False):
        high_power = ((g["Interval kWh"] > 1.664) | (g["Interval max demand kW"] > 1.664 * 4)).any()
        cap = 4.16 if high_power else 1.664
        idx = g.index.to_numpy()
        upper[idx] = cap
        raw_target = float(g["Interval kWh"].sum())
        target = min(raw_target, cap * len(g))
        group_index.append(idx)
        session_rows.append({
            "uid": str(uid),
            "date": g["Interval start"].iloc[0].date().isoformat(),
            "target_kwh": target,
            "raw_kwh": raw_target,
            "available_intervals": len(g),
            "interval_cap_kwh": cap,
        })

    row = df["t"].to_numpy(int)
    col = np.arange(len(df))
    A = sparse.coo_matrix((np.ones(len(df)), (row, col)), shape=(n, len(df))).tocsr()
    S = sparse.lil_matrix((len(group_index), len(df)))
    for i, idx in enumerate(group_index):
        S[i, idx] = 1.0
    meta = pd.DataFrame(session_rows)
    meta.attrs["session_matrix"] = S.tocsr()
    return A, upper, meta


def _load_controller_baseline(
    controller: str,
    forecast: str = "persistence",
    grid: pd.DatetimeIndex = GRID,
) -> np.ndarray:
    impl = (
        OUT_ROOT
        / controller
        / "Dispatch"
        / f"{FORECAST_PREFIX[forecast]}_full_implementation.csv"
    )
    df = pd.read_csv(impl)
    ts = pd.to_datetime(df["Interval start"])
    s = pd.Series(pd.to_numeric(df["baseline_Base [kWh]"], errors="coerce").to_numpy() / DT_H, index=ts)
    s = s[~s.index.duplicated(keep="last")].reindex(grid)
    if s.isna().any():
        raise ValueError(f"{controller} monthly MPC baseline is incomplete: {int(s.isna().sum())} missing")
    return s.to_numpy(float)


def _short_mpc_run_root(
    day: pd.Timestamp,
    mip_gap: float | None = None,
) -> Path:
    gap_tag = "" if mip_gap is None else f"_gap_{mip_gap:.0e}".replace("+", "")
    run_tag = (
        f"days_{day.day:02d}-{day.day:02d}_"
        f"full_perfect-persistence{gap_tag}"
    )
    return OUT_ROOT / "short_tests" / "rolling" / "mpc" / run_tag


def _load_short_mpc_perfect_baseline(
    grid: pd.DatetimeIndex,
    mip_gap: float | None = None,
) -> np.ndarray:
    """Load the exact baseline used by one isolated Rolling Perfect short test."""
    unique_days = pd.DatetimeIndex(grid.normalize().unique())
    if len(unique_days) != 1:
        raise ValueError(
            "A short-MPC baseline currently requires exactly one complete day"
        )
    day = unique_days[0]
    trace = (
        _short_mpc_run_root(day, mip_gap)
        / "Validation_Traces"
        / f"{FORECAST_PREFIX['perfect']}_full"
        / f"rolling_validation_trace_{day:%Y%m%d}.csv"
    )
    df = pd.read_csv(trace)
    ts = pd.to_datetime(df["Interval start"], errors="raise")
    baseline = pd.Series(
        pd.to_numeric(df["baseline_kW"], errors="raise").to_numpy(),
        index=ts,
    )
    baseline = baseline[~baseline.index.duplicated(keep="last")].reindex(grid)
    if baseline.isna().any():
        raise ValueError(
            f"Short MPC baseline is incomplete: {int(baseline.isna().sum())} missing"
        )
    return baseline.to_numpy(float)


def _formal_run_root(formal_tag: str) -> Path:
    return OUT_ROOT / "formal_runs" / formal_tag


def _load_formal_run_perfect_baseline(
    grid: pd.DatetimeIndex,
    formal_tag: str,
) -> np.ndarray:
    """Load the exact executed Rolling-Perfect baseline for a formal run."""
    trace_root = (
        _formal_run_root(formal_tag)
        / "rolling"
        / "Validation_Traces"
        / f"{FORECAST_PREFIX['perfect']}_full"
    )
    files = sorted(trace_root.glob("rolling_validation_trace_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No Rolling Perfect validation traces found in {trace_root}"
        )
    frames = [pd.read_csv(path) for path in files]
    df = pd.concat(frames, ignore_index=True)
    ts = pd.to_datetime(df["Interval start"], errors="raise")
    baseline = pd.Series(
        pd.to_numeric(df["baseline_kW"], errors="raise").to_numpy(),
        index=ts,
    )
    if baseline.index.duplicated().any():
        raise ValueError("Formal Rolling Perfect traces contain duplicate timestamps")
    baseline = baseline.sort_index().reindex(grid)
    if baseline.isna().any():
        raise ValueError(
            f"Formal Rolling Perfect baseline is incomplete: "
            f"{int(baseline.isna().sum())} missing intervals"
        )
    return baseline.to_numpy(float)


def _load_current_results_perfect_baseline(
    grid: pd.DatetimeIndex,
) -> np.ndarray:
    """Load the exact baseline from the current formal Results_Rolling trace."""
    trace_root = (
        REPO
        / "Results_Rolling"
        / "Validation_Traces"
        / f"{FORECAST_PREFIX['perfect']}_full"
    )
    files = sorted(trace_root.glob("rolling_validation_trace_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No current Rolling Perfect validation traces found in {trace_root}"
        )
    df = pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
    ts = pd.to_datetime(df["Interval start"], errors="raise")
    baseline = pd.Series(
        pd.to_numeric(df["baseline_kW"], errors="raise").to_numpy(),
        index=ts,
    )
    baseline = baseline[~baseline.index.duplicated(keep="last")].sort_index().reindex(grid)
    if baseline.isna().any():
        raise ValueError(
            "Current Results_Rolling Perfect baseline is incomplete: "
            f"{int(baseline.isna().sum())} missing intervals"
        )
    return baseline.to_numpy(float)


def _load_shrinking_perfect_benchmark_baseline(
    grid: pd.DatetimeIndex = GRID,
) -> np.ndarray:
    """Load the corrected June baseline path from Shrinking + Perfect/full.

    This path starts from the Perfect dispatch history produced by the baseline
    notebook and is then updated by the executed Shrinking + Perfect June dispatch.
    It is the common exogenous baseline requested for the full-horizon benchmark.
    """
    impl = REPO / "Results_Shrinking" / "Dispatch" / f"{FORECAST_PREFIX['perfect']}_full_implementation.csv"
    df = pd.read_csv(impl, low_memory=False)
    ts = pd.to_datetime(df["Interval start"], errors="raise")
    s = pd.Series(pd.to_numeric(df["baseline_Base [kWh]"], errors="coerce").to_numpy() / DT_H, index=ts)
    s = s[~s.index.duplicated(keep="last")].reindex(grid)
    if s.isna().any():
        raise ValueError(f"Shrinking + Perfect benchmark baseline is incomplete: {int(s.isna().sum())} missing")
    return s.to_numpy(float)


def _load_common_offline_baseline(
    grid: pd.DatetimeIndex = GRID,
) -> np.ndarray:
    """Build one controller-independent June baseline from Perfect history.

    This reproduces the main notebooks' historical baseline rule without replacing
    any June history with Shrinking- or Rolling-specific implementation output:
    use the most recent 10 eligible weekdays or 4 eligible weekend/holiday days,
    search at most 45 days backward, and calculate each hour independently.
    """
    path = REPO / "Results_Shrinking/Dispatch/2025_PerfectSessionkWh_PerfectNumbEV_PerfectatArrival_baseline.csv"
    history = pd.read_csv(path, low_memory=False)
    history["Interval start"] = pd.to_datetime(history["Interval start"], errors="raise")
    history["Base [kWh]"] = pd.to_numeric(history["Base [kWh]"], errors="coerce")
    if history["Base [kWh]"].isna().any():
        raise ValueError("Common baseline history contains missing Base [kWh] values")
    us_holidays = set(holidays.US(years=2025).keys())

    def is_weekend_or_holiday(day: pd.Timestamp) -> bool:
        return day.dayofweek >= 5 or day.date() in us_holidays

    days = pd.DatetimeIndex(grid.normalize().unique())
    values = np.zeros(len(grid), dtype=float)
    for day_idx, day in enumerate(days):
        weekend = is_weekend_or_holiday(day)
        needed = 4 if weekend else 10
        hourly = np.zeros(24, dtype=float)
        for hour in range(24):
            samples = []
            for lag in range(1, 46):
                prior = day - pd.Timedelta(days=lag)
                if is_weekend_or_holiday(prior) != weekend:
                    continue
                rows = history[
                    (history["Interval start"].dt.normalize() == prior.normalize())
                    & (history["Interval start"].dt.hour == hour)
                ]
                if rows.empty:
                    continue
                if "event hour_Base" in rows and float(rows["event hour_Base"].iloc[0]) != 0.0:
                    continue
                samples.append(float(rows["Base [kWh]"].sum()) / 4.0)
                if len(samples) == needed:
                    break
            if not samples:
                raise ValueError(f"No eligible common-baseline samples for {day.date()} hour {hour}")
            hourly[hour] = float(np.mean(samples))
        values[day_idx * 96:(day_idx + 1) * 96] = np.repeat(hourly, 4) / DT_H
    return values


def _tou_rate(grid: pd.DatetimeIndex = GRID) -> np.ndarray:
    rate = np.empty(len(grid))
    hour = grid.hour + grid.minute / 60
    rate[(hour >= 16) & (hour < 21)] = 0.335 + 0.490
    rate[((hour >= 6) & (hour < 16)) | ((hour >= 21) & (hour < 24))] = 0.03921 + 0.175
    rate[(hour >= 0) & (hour < 6)] = 0.03921 + 0.0815
    return rate


def select_gate_d_stress_dates() -> list[str]:
    """Select reproducible June stress dates from raw inputs and prior screens.

    The prior matched-state comparison is used only to identify a numerically
    close/reversed ordering for re-testing. It is not treated as validation
    evidence for the current code.
    """
    A, ev_upper, ev_meta = _build_ev_matrix(GRID)
    p_ev_max = np.asarray(A @ ev_upper).reshape(-1) / DT_H
    prices = _load_prices(GRID)
    daily_index = pd.date_range("2025-06-01", "2025-06-30", freq="D")
    daily = pd.DataFrame(index=daily_index)
    daily.index.name = "Date"
    session_dates = pd.to_datetime(ev_meta["date"], errors="raise")
    daily["realized_EV_target_kWh"] = (
        ev_meta.assign(Date=session_dates)
        .groupby("Date")["target_kwh"]
        .sum()
        .reindex(daily_index, fill_value=0.0)
    )
    daily["connected_EV_capability_kWh_equiv"] = (
        pd.Series(p_ev_max * DT_H, index=GRID)
        .groupby(lambda x: x.normalize())
        .sum()
        .reindex(daily_index, fill_value=0.0)
    )
    daily["DA_RT_abs_price_spread_$per_kW_day"] = (
        pd.Series(
            np.abs(prices["lmp_rt"] - prices["lmp_da"]) * DT_H,
            index=GRID,
        )
        .groupby(lambda x: x.normalize())
        .sum()
        .reindex(daily_index)
    )
    as_keys = [key for key in prices if key.startswith("as_")]
    daily["AS_price_peak_$/kWh_equiv"] = (
        pd.Series(
            np.max(np.vstack([prices[key] for key in as_keys]), axis=0),
            index=GRID,
        )
        .groupby(lambda x: x.normalize())
        .max()
        .reindex(daily_index)
    )

    raw = pd.read_csv(
        REPO / "2025Data/EV_data/UCSD_AllSites_Merge_PostProcessedSession_QC.csv",
        usecols=["Interval start", "Interval kWh"],
        low_memory=False,
    )
    raw["Interval start"] = pd.to_datetime(raw["Interval start"], errors="coerce")
    raw["Interval kWh"] = pd.to_numeric(
        raw["Interval kWh"], errors="coerce"
    ).fillna(0.0)
    raw = raw[
        (raw["Interval start"] >= GRID[0])
        & (raw["Interval start"] < GRID[-1] + pd.Timedelta(minutes=15))
    ].copy()
    raw["Date"] = raw["Interval start"].dt.normalize()
    raw["is_PD_window"] = raw["Interval start"].dt.hour.between(16, 20)
    daily["realized_EV_PD_window_kWh"] = (
        raw[raw["is_PD_window"]]
        .groupby("Date")["Interval kWh"]
        .sum()
        .reindex(daily_index, fill_value=0.0)
    )

    persistence_summary = pd.read_csv(
        OUT_ROOT
        / "rolling"
        / "Dispatch"
        / f"{FORECAST_PREFIX['persistence']}_full_daily_summary.csv"
    )
    persistence_summary["Date"] = pd.to_datetime(
        persistence_summary["Date"].astype(str), errors="raise"
    )
    persistence_summary["abs_session_energy_error_kWh"] = (
        persistence_summary["Fc SessionkWh"]
        - persistence_summary["Real SessionkWh"]
    ).abs()
    daily["Persistence_abs_session_energy_error_kWh"] = (
        persistence_summary.groupby("Date")["abs_session_energy_error_kWh"]
        .sum()
        .reindex(daily_index, fill_value=0.0)
    )

    matched_path = (
        OUT_ROOT / "rolling" / "matched_state" / "matched_state_comparison.csv"
    )
    matched = pd.read_csv(matched_path)
    matched["Date"] = pd.to_datetime(matched["Date"], errors="raise")
    matched = matched.set_index("Date").reindex(daily_index)
    daily["prior_screen_Perfect_minus_Persistence_$"] = matched[
        "Perfect minus Persistence"
    ]

    active = daily["realized_EV_target_kWh"] > 0.0
    criteria = [
        (
            "largest_realized_EV_energy",
            daily["realized_EV_target_kWh"].idxmax(),
            "realized_EV_target_kWh",
            "Raw/QC EV session targets; NCD and fleet-throughput stress.",
        ),
        (
            "largest_Persistence_session_energy_error",
            daily["Persistence_abs_session_energy_error_kWh"].idxmax(),
            "Persistence_abs_session_energy_error_kWh",
            "Historical forecast screen only; rerun supplies current evidence.",
        ),
        (
            "largest_DA_RT_energy_price_spread",
            daily["DA_RT_abs_price_spread_$per_kW_day"].idxmax(),
            "DA_RT_abs_price_spread_$per_kW_day",
            "Raw June DA/RT LMP inputs.",
        ),
        (
            "largest_AS_price",
            daily["AS_price_peak_$/kWh_equiv"].idxmax(),
            "AS_price_peak_$/kWh_equiv",
            "Raw June DA/RT ancillary-service price inputs.",
        ),
        (
            "largest_PD_window_EV_energy",
            daily["realized_EV_PD_window_kWh"].idxmax(),
            "realized_EV_PD_window_kWh",
            "Raw/QC EV energy during the 16:00-21:00 PD window.",
        ),
        (
            "smallest_connected_EV_capability",
            daily.loc[active, "connected_EV_capability_kWh_equiv"].idxmin(),
            "connected_EV_capability_kWh_equiv",
            "Interval-specific connected-EV capability, excluding zero-EV days.",
        ),
        (
            "prior_closest_or_reversed_matched_state_ordering",
            daily["prior_screen_Perfect_minus_Persistence_$"].idxmin(),
            "prior_screen_Perfect_minus_Persistence_$",
            "Prior screen only; selected specifically for tighter-gap re-test.",
        ),
    ]
    selection_rows = []
    for criterion, date, metric, basis in criteria:
        selection_rows.append({
            "criterion": criterion,
            "Date": date.date().isoformat(),
            "metric": metric,
            "metric_value": float(daily.loc[date, metric]),
            "basis": basis,
        })
    out = OUT_ROOT / "short_tests" / "gate_d"
    out.mkdir(parents=True, exist_ok=True)
    daily.reset_index().to_csv(
        out / "stress_date_daily_metrics.csv",
        index=False,
        float_format="%.8f",
    )
    pd.DataFrame(selection_rows).to_csv(
        out / "stress_date_selection.csv",
        index=False,
        float_format="%.8f",
    )
    selected = sorted({row["Date"] for row in selection_rows})
    print("Selected Gate D stress dates:", ", ".join(selected))
    return selected


def run_monthly_oracle(
    controller: str,
    start_date: str = "2025-06-01",
    end_date: str = "2025-07-01",
    mip_gap: float = 1e-2,
    time_limit_s: float | None = 240.0,
    baseline_source: str = "auto",
    short_mpc_mip_gap: float | None = None,
    formal_tag: str | None = None,
    direction_seed_path: str | None = None,
    mip_focus: int = 1,
) -> None:
    """Solve a perfect-information oracle over one or more complete days.

    ``end_date`` is exclusive. The default remains the complete June billing
    period. Short runs are written below ``short_tests`` so they cannot overwrite
    the formal June artifacts.
    """
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start.time() != pd.Timestamp(start.date()).time() or end.time() != pd.Timestamp(end.date()).time():
        raise ValueError("Oracle start/end must be midnight-aligned")
    if end <= start:
        raise ValueError("Oracle end_date must be later than start_date")
    grid = pd.date_range(start, end, freq="15min", inclusive="left")
    if len(grid) == 0 or len(grid) % 96 != 0:
        raise ValueError("Oracle period must contain complete 24-hour days")
    n = len(grid)
    n_days = n // 96
    full_june = start == pd.Timestamp("2025-06-01") and end == pd.Timestamp("2025-07-01")
    if baseline_source not in {"auto", "formal", "short-mpc", "formal-run", "current-results"}:
        raise ValueError(
            "baseline_source must be auto, formal, short-mpc, formal-run, or current-results"
        )
    effective_baseline_source = baseline_source
    if effective_baseline_source == "auto":
        effective_baseline_source = (
            "formal-run"
            if (full_june and formal_tag is not None)
            else
            "short-mpc"
            if (not full_june and controller == "rolling_perfect")
            else "formal"
        )
    if effective_baseline_source == "short-mpc" and controller != "rolling_perfect":
        raise ValueError(
            "short-mpc baseline is currently defined only for rolling_perfect"
        )
    if effective_baseline_source == "formal-run":
        if controller != "rolling_perfect":
            raise ValueError(
                "formal-run baseline is currently defined only for rolling_perfect"
            )
        if formal_tag is None:
            raise ValueError("formal-run baseline requires formal_tag")
    if effective_baseline_source == "current-results" and controller != "rolling_perfect":
        raise ValueError(
            "current-results baseline is defined only for rolling_perfect"
        )
    if full_june:
        if effective_baseline_source == "short-mpc":
            raise ValueError("Formal full-June oracle cannot use a one-day short-MPC baseline")
        out = (
            _formal_run_root(formal_tag) / controller / "oracle"
            if formal_tag is not None
            else OUT_ROOT / controller / "oracle"
        )
        if formal_tag is not None and out.exists() and any(out.iterdir()):
            raise FileExistsError(
                f"Versioned formal oracle output already exists: {out}"
            )
    else:
        period_tag = f"{start:%Y-%m-%d}_to_{end - pd.Timedelta(days=1):%Y-%m-%d}"
        if effective_baseline_source == "short-mpc":
            period_tag += "_baseline-short-mpc"
        out = OUT_ROOT / "short_tests" / controller / "oracle" / period_tag
    out.mkdir(parents=True, exist_ok=True)
    prices = _load_prices(grid)
    if effective_baseline_source == "short-mpc":
        baseline = _load_short_mpc_perfect_baseline(
            grid,
            mip_gap=short_mpc_mip_gap,
        )
    elif effective_baseline_source == "current-results":
        baseline = _load_current_results_perfect_baseline(grid)
    elif effective_baseline_source == "formal-run":
        baseline = _load_formal_run_perfect_baseline(
            grid,
            formal_tag=formal_tag,
        )
    elif controller == "benchmark":
        baseline = _load_shrinking_perfect_benchmark_baseline(grid)
    elif controller == "common":
        baseline = _load_common_offline_baseline(grid)
    elif controller == "rolling_perfect":
        baseline = _load_controller_baseline("rolling", "perfect", grid)
    elif controller in ("rolling", "rolling_persistence"):
        baseline = _load_controller_baseline("rolling", "persistence", grid)
    else:
        baseline = _load_controller_baseline(controller, "persistence", grid)
    A, ev_upper, ev_meta = _build_ev_matrix(grid)
    S = ev_meta.attrs["session_matrix"]
    targets = ev_meta["target_kwh"].to_numpy(float)

    # Physical EV capability is interval-specific. A daily vehicle count repeated
    # over all 96 intervals creates fictitious AS headroom while vehicles are not
    # connected and is inconsistent with the corrected MPC notebooks.
    p_ev_max = np.asarray(A @ ev_upper).ravel() / DT_H
    p_up = 250.0 + baseline
    p_down = np.maximum(250.0 - baseline + p_ev_max, 0.0)
    m_ev = 1.05 * np.maximum.reduce([p_ev_max, np.abs(baseline), np.full(n, 1e-6)])

    model = gp.Model(f"perfect_oracle_{controller}_{start:%Y%m%d}_{end:%Y%m%d}")
    model.Params.MIPGap = float(mip_gap)
    model.Params.Threads = 6
    model.Params.Presolve = 2
    model.Params.NumericFocus = 1
    if mip_focus not in (0, 1, 2, 3):
        raise ValueError("mip_focus must be one of 0, 1, 2, or 3")
    model.Params.MIPFocus = int(mip_focus)
    model.Params.Heuristics = 0.2
    if time_limit_s is not None:
        model.Params.TimeLimit = float(time_limit_s)
    model.Params.OutputFlag = 1
    model.Params.LogFile = str(out / "oracle_gurobi.log")

    ev_x = model.addMVar(len(ev_upper), lb=0.0, ub=ev_upper, name="ev_kwh")
    p_ev = model.addMVar(n, lb=0.0, name="p_ev")
    model.addConstr(S @ ev_x == targets, name="ev_session_energy")
    model.addConstr(p_ev == (A @ ev_x) / DT_H, name="ev_aggregate")

    p_b = model.addMVar(n, lb=-250.0, ub=250.0, name="p_bess")
    p_ch = model.addMVar(n, lb=0.0, name="p_ch_bess")
    p_dch = model.addMVar(n, lb=0.0, name="p_dch_bess")
    p_ch_wm = model.addMVar(n, lb=0.0, name="p_ch_bess_wm")
    p_dch_wm = model.addMVar(n, lb=0.0, name="p_dch_bess_wm")
    p_ch_nwm = model.addMVar(n, lb=0.0, name="p_ch_bess_nwm")
    p_dch_nwm = model.addMVar(n, lb=0.0, name="p_dch_bess_nwm")
    soc = model.addMVar(n + 1, lb=0.05, ub=0.95, name="soc")
    b_b = model.addMVar(n, vtype=GRB.BINARY, name="b_ch_bess")
    model.addConstr(p_b == p_ch - p_dch)
    model.addConstr(p_ch == p_ch_wm + p_ch_nwm)
    model.addConstr(p_dch == p_dch_wm + p_dch_nwm)
    model.addConstr(p_ch <= 250.0 * b_b)
    model.addConstr(p_dch <= 250.0 * (1 - b_b))
    model.addConstr(soc[0] == 0.5)
    model.addConstr(soc[n] == 0.5)
    model.addConstr(
        soc[1:] == soc[:-1] + DT_H / 332.0 * (np.sqrt(0.9) * p_ch - p_dch / np.sqrt(0.9))
    )
    for d in range(n_days):
        sl = slice(d * 96, (d + 1) * 96)
        model.addConstr(DT_H * (p_ch[sl].sum() + p_dch[sl].sum()) <= 2 * 332.0 * (0.95 - 0.05))

    p_gi = model.addMVar(n, lb=-GRB.INFINITY, name="p_gi")
    model.addConstr(p_gi == p_ev + p_b)

    p_da = model.addMVar(n, lb=-p_down, ub=p_up, name="p_da_commit")
    p_actual = model.addMVar(n, lb=-p_down, ub=p_up, name="p_actual")
    p_pos = model.addMVar(n, lb=0.0, name="p_actual_pos")
    p_neg = model.addMVar(n, lb=0.0, name="p_actual_neg")
    model.addConstr(p_pos >= p_actual)
    model.addConstr(p_neg >= -p_actual)

    products = ("ru", "rd", "sp", "nsp")
    c_da = {x: model.addMVar(n, lb=0.0, name=f"c_{x}_da") for x in products}
    c_act = {x: model.addMVar(n, lb=0.0, name=f"c_{x}_actual") for x in products}
    c_up_da = c_da["ru"] + c_da["sp"] + c_da["nsp"]
    c_up_act = c_act["ru"] + c_act["sp"] + c_act["nsp"]
    model.addConstr(c_up_da <= p_up)
    model.addConstr(c_da["rd"] <= p_down)
    model.addConstr(p_pos + c_up_act <= p_up)
    model.addConstr(p_neg + c_act["rd"] <= p_down)

    # CAISO DA awards are hourly.  Keep the common 15-min physical clock, but
    # enforce one DA energy/capacity award across each four-interval hour.
    for hour_start in range(0, n, 4):
        for offset in (1, 2, 3):
            t = hour_start + offset
            model.addConstr(p_da[t] == p_da[hour_start], name=f"p_da_hour_{t}")
            for x in products:
                model.addConstr(
                    c_da[x][t] == c_da[x][hour_start],
                    name=f"c_{x}_da_hour_{t}",
                )

    p_ch_ev_wm = model.addMVar(n, lb=0.0, name="p_ch_ev_wm")
    p_dch_ev_wm = model.addMVar(n, lb=0.0, name="p_dch_ev_wm")
    p_ch_ev_nwm = model.addMVar(n, lb=0.0, name="p_ch_ev_nwm")
    p_dch_ev_nwm = model.addMVar(n, lb=0.0, name="p_dch_ev_nwm")
    b_ev = model.addMVar(n, vtype=GRB.BINARY, name="b_ch_ev")
    model.addConstr(p_ev - baseline == p_ch_ev_wm - p_dch_ev_wm + p_ch_ev_nwm - p_dch_ev_nwm)
    model.addConstr(p_ch_ev_wm + p_ch_ev_nwm <= m_ev * b_ev)
    model.addConstr(p_dch_ev_wm + p_dch_ev_nwm <= m_ev * (1 - b_ev))

    q = p_actual + 0.7 * c_act["ru"] - 0.7 * c_act["rd"] + 0.2 * c_act["sp"] + 0.2 * c_act["nsp"]
    p_ch_net = model.addMVar(n, lb=0.0, name="p_ch_net")
    p_dch_net = model.addMVar(n, lb=0.0, name="p_dch_net")
    b_net = model.addMVar(n, vtype=GRB.BINARY, name="b_ch_net")
    model.addConstr(p_dch_net >= q)
    model.addConstr(p_dch_net <= q + p_up * b_net)
    model.addConstr(p_ch_net >= -q)
    model.addConstr(p_ch_net <= -q + p_down * (1 - b_net))
    model.addConstr(p_ch_net <= p_down * b_net)
    model.addConstr(p_dch_net <= p_up * (1 - b_net))
    model.addConstr(p_ch_net - p_dch_net == p_ch_wm - p_dch_wm + p_ch_ev_wm - p_dch_ev_wm)
    model.addConstr(c_up_act <= p_up * (1 - b_net))
    model.addConstr(c_act["rd"] <= p_down * b_net)
    model.addConstr(soc[1:] >= 0.05 + (2 * DT_H) / (332.0 * np.sqrt(0.9)) * c_up_act)
    model.addConstr(soc[1:] <= 0.95 - (2 * DT_H * np.sqrt(0.9)) / 332.0 * c_act["rd"])

    ncd_peak = model.addVar(lb=0.0, name="monthly_ncd_peak")
    pd_peak = model.addVar(lb=0.0, name="monthly_pd_peak")
    model.addConstr(p_gi <= ncd_peak)
    pd_mask = (grid.hour >= 16) & (grid.hour < 21)
    model.addConstr(p_gi[pd_mask] <= pd_peak)

    deployment = 0.7 * c_act["ru"] - 0.7 * c_act["rd"] + 0.2 * c_act["sp"] + 0.2 * c_act["nsp"]
    wm_energy = DT_H * (
        prices["lmp_da"] @ p_da
        + prices["lmp_rt"] @ (p_actual - p_da)
        + prices["lmp_rt"] @ deployment
    )
    wm_capacity = gp.LinExpr()
    for x in products:
        wm_capacity += DT_H * (
            prices[f"as_{x}_da"] @ c_da[x]
            + prices[f"as_{x}_rt"] @ (c_act[x] - c_da[x])
        )
    ev_revenue = 0.4 * DT_H * p_ev.sum()
    tou_rate = _tou_rate(grid)
    tou_cost = DT_H * (tou_rate @ p_gi)
    total_value = ev_revenue + wm_energy + wm_capacity - tou_cost - 15.38 * ncd_peak - 3.05 * pd_peak
    model.setObjective(total_value, GRB.MAXIMIZE)

    # A guaranteed feasible retail-only start prevents the month-scale MIP from
    # wasting its first search phase on a poor incumbent.  It serves every EV
    # session, keeps BESS SOC at 50%, and uses no market products.
    session_counts = np.asarray(S.sum(axis=1)).ravel()
    ev_start = np.asarray(S.T @ (targets / session_counts)).ravel()
    p_ev_start = np.asarray(A @ ev_start).ravel() / DT_H
    ev_diff = p_ev_start - baseline
    ev_x.Start = ev_start
    p_ev.Start = p_ev_start
    p_b.Start = np.zeros(n)
    p_ch.Start = np.zeros(n)
    p_dch.Start = np.zeros(n)
    p_ch_wm.Start = np.zeros(n)
    p_dch_wm.Start = np.zeros(n)
    p_ch_nwm.Start = np.zeros(n)
    p_dch_nwm.Start = np.zeros(n)
    soc.Start = np.full(n + 1, 0.5)
    b_b.Start = np.zeros(n)
    p_gi.Start = p_ev_start
    p_da.Start = np.zeros(n)
    p_actual.Start = np.zeros(n)
    p_pos.Start = np.zeros(n)
    p_neg.Start = np.zeros(n)
    for x in products:
        c_da[x].Start = np.zeros(n)
        c_act[x].Start = np.zeros(n)
    p_ch_ev_wm.Start = np.zeros(n)
    p_dch_ev_wm.Start = np.zeros(n)
    p_ch_ev_nwm.Start = np.maximum(ev_diff, 0.0)
    p_dch_ev_nwm.Start = np.maximum(-ev_diff, 0.0)
    b_ev.Start = (ev_diff >= 0.0).astype(float)
    p_ch_net.Start = np.zeros(n)
    p_dch_net.Start = np.zeros(n)
    b_net.Start = np.zeros(n)
    ncd_peak.Start = max(float(np.max(p_ev_start)), 0.0)
    pd_peak.Start = max(float(np.max(p_ev_start[pd_mask])), 0.0)

    # Direction-polishing warm start.  The algebraic model is unchanged.  A
    # prior feasible dispatch may supply only the three binary directions; all
    # continuous values are re-optimized under the current model.  Without a
    # seed, infer the directions from the continuous relaxation as before.
    model.update()
    direction_vars = [b_b, b_ev, b_net]
    model.Params.OutputFlag = 0
    seed_dispatch = None
    if direction_seed_path is not None:
        seed_path = Path(direction_seed_path).expanduser().resolve()
        seed_dispatch = pd.read_csv(seed_path)
        seed_time = pd.to_datetime(
            seed_dispatch["Interval start"], errors="raise"
        )
        if len(seed_dispatch) != n or not np.array_equal(
            seed_time.to_numpy(dtype="datetime64[ns]"),
            grid.to_numpy(dtype="datetime64[ns]"),
        ):
            raise ValueError(
                "Direction-seed dispatch must exactly match the oracle time grid"
            )
        required_seed_columns = {
            "p_EV_kW",
            "p_BESS_kW",
            "p_actual_kW",
            "c_RU_actual_kW",
            "c_RD_actual_kW",
            "c_SP_actual_kW",
            "c_NSP_actual_kW",
        }
        missing = sorted(required_seed_columns - set(seed_dispatch.columns))
        if missing:
            raise ValueError(
                f"Direction-seed dispatch is missing columns: {missing}"
            )
        b_b_fix = (
            seed_dispatch["p_BESS_kW"].to_numpy(float) >= 0.0
        ).astype(float)
        b_ev_fix = (
            seed_dispatch["p_EV_kW"].to_numpy(float) - baseline >= 0.0
        ).astype(float)
        q_seed = (
            seed_dispatch["p_actual_kW"].to_numpy(float)
            + 0.7 * seed_dispatch["c_RU_actual_kW"].to_numpy(float)
            - 0.7 * seed_dispatch["c_RD_actual_kW"].to_numpy(float)
            + 0.2 * seed_dispatch["c_SP_actual_kW"].to_numpy(float)
            + 0.2 * seed_dispatch["c_NSP_actual_kW"].to_numpy(float)
        )
        b_net_fix = (q_seed < 0.0).astype(float)
    else:
        for mv in direction_vars:
            for var in mv.tolist():
                var.VType = GRB.CONTINUOUS
                var.LB = 0.0
                var.UB = 1.0
        model.update()
        model.optimize()
        if model.SolCount == 0:
            raise RuntimeError(
                f"Oracle returned no feasible incumbent (Gurobi status {model.Status})"
            )
        b_b_fix = (p_ch.X >= p_dch.X).astype(float)
        b_ev_fix = (p_ev.X - baseline >= 0.0).astype(float)
        q_relaxed = (
            p_actual.X + 0.7 * c_act["ru"].X - 0.7 * c_act["rd"].X
            + 0.2 * c_act["sp"].X + 0.2 * c_act["nsp"].X
        )
        b_net_fix = (q_relaxed < 0.0).astype(float)
    for mv, fixed in ((b_b, b_b_fix), (b_ev, b_ev_fix), (b_net, b_net_fix)):
        for var, value in zip(mv.tolist(), fixed):
            var.VType = GRB.BINARY
            var.LB = float(value)
            var.UB = float(value)
    model.update()
    model.optimize()
    polished = None
    if model.SolCount:
        polished = {var.VarName: float(var.X) for var in model.getVars()}
    for mv in direction_vars:
        for var in mv.tolist():
            var.LB = 0.0
            var.UB = 1.0
    model.update()
    if polished is not None:
        model.reset()
        for var in model.getVars():
            var.Start = polished[var.VarName]
    model.Params.OutputFlag = 1
    started = time.time()
    model.optimize()
    if model.SolCount == 0 or model.Status not in (GRB.OPTIMAL, GRB.TIME_LIMIT):
        raise RuntimeError(f"Oracle failed: status={model.Status}, solutions={model.SolCount}")
    if model.Status == GRB.TIME_LIMIT and model.MIPGap > 3.0e-2:
        raise RuntimeError(f"Oracle time-limited with unacceptable gap {model.MIPGap}")

    dispatch = pd.DataFrame({
        "Interval start": grid,
        "p_EV_kW": p_ev.X,
        "p_BESS_kW": p_b.X,
        "p_GI_kW": p_gi.X,
        "SOC": soc.X[1:],
        "p_DA_kW": p_da.X,
        "p_RT_deviation_kW": p_actual.X - p_da.X,
        "p_actual_kW": p_actual.X,
        "c_RU_DA_kW": c_da["ru"].X,
        "c_RU_RT_kW": c_act["ru"].X - c_da["ru"].X,
        "c_RU_actual_kW": c_act["ru"].X,
        "c_RD_DA_kW": c_da["rd"].X,
        "c_RD_RT_kW": c_act["rd"].X - c_da["rd"].X,
        "c_RD_actual_kW": c_act["rd"].X,
        "c_SP_DA_kW": c_da["sp"].X,
        "c_SP_RT_kW": c_act["sp"].X - c_da["sp"].X,
        "c_SP_actual_kW": c_act["sp"].X,
        "c_NSP_DA_kW": c_da["nsp"].X,
        "c_NSP_RT_kW": c_act["nsp"].X - c_da["nsp"].X,
        "c_NSP_actual_kW": c_act["nsp"].X,
        "baseline_kW": baseline,
        "P_EV_max_kW": p_ev_max,
        "p_up_bound_kW": p_up,
        "p_down_bound_kW": p_down,
        "LMP_DA_$/kWh": prices["lmp_da"],
        "LMP_RT_$/kWh": prices["lmp_rt"],
        "AS_RU_DA_$/kWh": prices["as_ru_da"],
        "AS_RU_RT_$/kWh": prices["as_ru_rt"],
        "AS_RD_DA_$/kWh": prices["as_rd_da"],
        "AS_RD_RT_$/kWh": prices["as_rd_rt"],
        "AS_SP_DA_$/kWh": prices["as_sp_da"],
        "AS_SP_RT_$/kWh": prices["as_sp_rt"],
        "AS_NSP_DA_$/kWh": prices["as_nsp_da"],
        "AS_NSP_RT_$/kWh": prices["as_nsp_rt"],
        "TOU_$/kWh": tou_rate,
    })
    dispatch.to_csv(out / "oracle_dispatch.csv", index=False, float_format="%.8f")
    ev_meta.drop(columns=[], errors="ignore").to_csv(out / "oracle_ev_sessions.csv", index=False)

    # Allocate the final monthly peak charge to the day on which each new peak is
    # first established.  These daily increments sum exactly to the monthly bill.
    rows = []
    running_ncd = 0.0
    running_pd = 0.0
    for d in range(n_days):
        sl = slice(d * 96, (d + 1) * 96)
        gi = p_gi.X[sl]
        ev = p_ev.X[sl]
        day_ncd = max(running_ncd, float(np.max(gi)), 0.0)
        day_pd = max(running_pd, float(np.max(gi[64:84])), 0.0)
        ncd_cost = 15.38 * (day_ncd - running_ncd)
        pd_cost = 3.05 * (day_pd - running_pd)
        running_ncd, running_pd = day_ncd, day_pd
        idx = np.arange(d * 96, (d + 1) * 96)
        dep = 0.7 * c_act["ru"].X[idx] - 0.7 * c_act["rd"].X[idx] + 0.2 * c_act["sp"].X[idx] + 0.2 * c_act["nsp"].X[idx]
        wm_e = DT_H * np.sum(
            prices["lmp_da"][idx] * p_da.X[idx]
            + prices["lmp_rt"][idx] * (p_actual.X[idx] - p_da.X[idx] + dep)
        )
        wm_c = 0.0
        for x in products:
            wm_c += DT_H * np.sum(
                prices[f"as_{x}_da"][idx] * c_da[x].X[idx]
                + prices[f"as_{x}_rt"][idx] * (c_act[x].X[idx] - c_da[x].X[idx])
            )
        ev_rev = 0.4 * DT_H * float(np.sum(ev))
        tou = DT_H * float(np.sum(tou_rate[idx] * gi))
        rows.append({
            "Date": grid[d * 96].date().isoformat(),
            "Total Revenue": ev_rev + wm_e + wm_c - tou - ncd_cost - pd_cost,
            "WM Revenue": wm_e + wm_c,
            "WM Energy Revenue": wm_e,
            "WM Capacity Revenue": wm_c,
            "TOU Cost": -tou,
            "PD Cost": -pd_cost,
            "NCD Cost": -ncd_cost,
            "EV Revenue": ev_rev,
            "EV Energy kWh": DT_H * float(np.sum(ev)),
            "NCD Peak kW": day_ncd,
            "PD Peak kW": day_pd,
            "End SOC": float(soc.X[(d + 1) * 96]),
        })
    daily = pd.DataFrame(rows)
    daily.to_csv(out / "oracle_daily_financial.csv", index=False, float_format="%.8f")
    status_names = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.INTERRUPTED: "INTERRUPTED",
    }
    baseline_sha256 = hashlib.sha256(
        np.ascontiguousarray(np.asarray(baseline, dtype="<f8")).tobytes()
    ).hexdigest()
    ev_capability_sha256 = hashlib.sha256(
        np.ascontiguousarray(np.asarray(p_ev_max, dtype="<f8")).tobytes()
    ).hexdigest()
    summary = {
        "controller_baseline": (
            "rolling_perfect_isolated_short_test_trace"
            if effective_baseline_source == "short-mpc"
            else "rolling_perfect_versioned_formal_trace"
            if effective_baseline_source == "formal-run"
            else "rolling_perfect_current_results_trace"
            if effective_baseline_source == "current-results"
            else "shrinking_perfect_executed_june_path"
            if controller == "benchmark"
            else "common_offline_perfect_history"
            if controller == "common"
            else "rolling_perfect_executed_baseline"
            if controller == "rolling_perfect"
            else "rolling_persistence_executed_baseline"
            if controller in ("rolling", "rolling_persistence")
            else controller
        ),
        "period_start": start.isoformat(),
        "period_end_exclusive": end.isoformat(),
        "interval_count": n,
        "interval_capability_rule": "sum_connected_session_interval_caps",
        "da_award_resolution": "hourly_block_repeated_on_15min_clock",
        "rt_award_resolution": "15min_binding_interval",
        "price_coefficient_unit": "USD_per_kWh_equivalent",
        "da_asmp_normalization": "native_USD_per_MW_divided_by_1000",
        "rt_asmp_normalization": "native_USD_per_MW_divided_by_1000_DT_H",
        "baseline_sha256_float64": baseline_sha256,
        "ev_capability_sha256_float64": ev_capability_sha256,
        "gurobi_version": ".".join(map(str, gp.gurobi.version())),
        "requested_mip_gap": float(mip_gap),
        "requested_mip_focus": int(mip_focus),
        "baseline_source_request": baseline_source,
        "effective_baseline_source": effective_baseline_source,
        "formal_tag": "" if formal_tag is None else formal_tag,
        "direction_seed_path": (
            "" if direction_seed_path is None else str(Path(direction_seed_path).resolve())
        ),
        "short_mpc_mip_gap_tag": (
            "source_default"
            if short_mpc_mip_gap is None
            else float(short_mpc_mip_gap)
        ),
        "requested_time_limit_s": (
            float(time_limit_s) if time_limit_s is not None else "none"
        ),
        "status": int(model.Status),
        "status_name": status_names.get(model.Status, f"STATUS_{model.Status}"),
        "time_limit_triggered": bool(model.Status == GRB.TIME_LIMIT),
        "solution_count": int(model.SolCount),
        "mip_gap": float(model.MIPGap),
        "runtime_s": time.time() - started,
        "objective_total_revenue": float(model.ObjVal),
        "objective_best_bound": float(model.ObjBound),
        "Total Revenue": float(daily["Total Revenue"].sum()),
        "WM Revenue": float(daily["WM Revenue"].sum()),
        "TOU Cost": float(daily["TOU Cost"].sum()),
        "PD Cost": float(daily["PD Cost"].sum()),
        "NCD Cost": float(daily["NCD Cost"].sum()),
        "EV Revenue": float(daily["EV Revenue"].sum()),
        "EV Energy kWh": float(daily["EV Energy kWh"].sum()),
        "terminal_soc": float(soc.X[-1]),
        "meter_balance_max_error_kW": float(np.max(np.abs(p_gi.X - p_ev.X - p_b.X))),
        "as_actual_min_kW": float(min(np.min(c_act[x].X) for x in products)),
        "ev_capability_max_violation_kW": float(np.max(p_ev.X - p_ev_max)),
        "actual_up_capability_max_violation_kW": float(
            np.max(
                np.maximum(p_actual.X, 0.0)
                + c_act["ru"].X
                + c_act["sp"].X
                + c_act["nsp"].X
                - p_up
            )
        ),
        "actual_down_capability_max_violation_kW": float(
            np.max(np.maximum(-p_actual.X, 0.0) + c_act["rd"].X - p_down)
        ),
    }
    pd.DataFrame([summary]).to_csv(out / "oracle_monthly_summary.csv", index=False)


def plot_daily_rolling_oracle_validation(
    day: str,
    oracle_controller: str = "rolling_perfect",
    source: str = "short",
    mip_gap: float | None = None,
    formal_tag: str | None = None,
) -> list[Path]:
    """Plot one-day Rolling Persistence/Perfect and benchmark traces.

    The plot intentionally uses executed first-step Rolling traces, never the
    day-start ``Opt_RT_t0`` planning trajectory. A short source is a standalone
    one-day simultaneous benchmark; only a formal source is a slice of the
    complete billing-period Perfect oracle.
    """
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    day_ts = pd.Timestamp(day).normalize()
    if source == "short":
        mpc_root = _short_mpc_run_root(day_ts, mip_gap)
        period_tag = f"{day_ts:%Y-%m-%d}_to_{day_ts:%Y-%m-%d}"
        oracle_root = (
            OUT_ROOT
            / "short_tests"
            / oracle_controller
            / "oracle"
            / f"{period_tag}_baseline-short-mpc"
        )
        output_root = OUT_ROOT / "short_tests" / "rolling" / "daily_graphs"
    elif source == "formal":
        formal_root = (
            _formal_run_root(formal_tag)
            if formal_tag is not None
            else OUT_ROOT
        )
        mpc_root = formal_root / "rolling"
        oracle_root = formal_root / oracle_controller / "oracle"
        output_root = formal_root / "rolling" / "daily_graphs"
    else:
        raise ValueError("source must be 'short' or 'formal'")

    benchmark_label = (
        "Full billing-period Perfect oracle"
        if source == "formal"
        else "One-day simultaneous Perfect benchmark"
    )
    scenario_specs = [
        (
            "Rolling 24 h Persistence",
            mpc_root
            / "Validation_Traces"
            / f"{FORECAST_PREFIX['persistence']}_full"
            / f"rolling_validation_trace_{day_ts:%Y%m%d}.csv",
            mpc_root
            / "Plots"
            / "Cost"
            / FORECAST_PREFIX["persistence"]
            / "daily_financial_detail.csv",
        ),
        (
            "Rolling 24 h Perfect",
            mpc_root
            / "Validation_Traces"
            / f"{FORECAST_PREFIX['perfect']}_full"
            / f"rolling_validation_trace_{day_ts:%Y%m%d}.csv",
            mpc_root
            / "Plots"
            / "Cost"
            / FORECAST_PREFIX["perfect"]
            / "daily_financial_detail.csv",
        ),
        (
            benchmark_label,
            oracle_root / "oracle_dispatch.csv",
            oracle_root / "oracle_daily_financial.csv",
        ),
    ]

    traces: list[pd.DataFrame] = []
    finances: list[pd.Series] = []
    for label, trace_path, financial_path in scenario_specs:
        if not trace_path.exists():
            raise FileNotFoundError(f"{label} trace not found: {trace_path}")
        if not financial_path.exists():
            raise FileNotFoundError(f"{label} financial data not found: {financial_path}")
        trace = pd.read_csv(trace_path)
        trace["Interval start"] = pd.to_datetime(trace["Interval start"], errors="raise")
        trace = trace[
            trace["Interval start"].dt.normalize() == day_ts
        ].reset_index(drop=True)
        if len(trace) != 96 or trace["Interval start"].duplicated().any():
            raise ValueError(f"{label} trace must contain 96 unique intervals")
        traces.append(trace)
        financial = pd.read_csv(financial_path)
        financial["Date"] = pd.to_datetime(financial["Date"], errors="raise")
        row = financial[financial["Date"].dt.normalize() == day_ts]
        if "Case" in row.columns:
            row = row[row["Case"] == "Both"]
        if len(row) != 1:
            raise ValueError(f"{label} financial table has {len(row)} rows for {day_ts.date()}")
        finances.append(row.iloc[0])

    required = {
        "p_EV_kW",
        "p_BESS_kW",
        "p_GI_kW",
        "SOC",
        "p_DA_kW",
        "p_RT_deviation_kW",
        "p_actual_kW",
        "c_RU_actual_kW",
        "c_RD_actual_kW",
        "c_SP_actual_kW",
        "c_NSP_actual_kW",
        "baseline_kW",
        "P_EV_max_kW",
        "p_up_bound_kW",
        "p_down_bound_kW",
        "LMP_DA_$/kWh",
        "LMP_RT_$/kWh",
        "TOU_$/kWh",
    }
    for (label, _, _), trace in zip(scenario_specs, traces):
        missing = required.difference(trace.columns)
        if missing:
            raise KeyError(f"{label} trace is missing {sorted(missing)}")
        if "meter_balance_residual_kW" not in trace:
            trace["meter_balance_residual_kW"] = (
                trace["p_GI_kW"] - trace["p_EV_kW"] - trace["p_BESS_kW"]
            )
        if "actual_up_capability_slack_kW" not in trace:
            trace["actual_up_capability_slack_kW"] = (
                trace["p_up_bound_kW"]
                - np.maximum(trace["p_actual_kW"], 0.0)
                - trace["c_RU_actual_kW"]
                - trace["c_SP_actual_kW"]
                - trace["c_NSP_actual_kW"]
            )
        if "actual_down_capability_slack_kW" not in trace:
            trace["actual_down_capability_slack_kW"] = (
                trace["p_down_bound_kW"]
                - np.maximum(-trace["p_actual_kW"], 0.0)
                - trace["c_RD_actual_kW"]
            )

    colors = {
        "ev": "#1f77b4",
        "bess": "#d62728",
        "grid": "#2ca02c",
        "baseline": "#6c757d",
        "da": "#4c78a8",
        "rt": "#35b8c5",
        "actual": "#111111",
        "ru": "#54a24b",
        "rd": "#e45756",
        "sp": "#b279a2",
        "nsp": "#ff9da6",
        "bound": "#f26b38",
    }
    fig, axes = plt.subplots(5, 3, figsize=(19, 20), sharex="col")
    energy_bar_width = pd.Timedelta(minutes=6)
    energy_bar_offset = pd.Timedelta(minutes=3)
    as_bar_width = pd.Timedelta(minutes=12)
    for col, ((label, _, _), trace, financial) in enumerate(
        zip(scenario_specs, traces, finances)
    ):
        x = trace["Interval start"]
        total = float(financial["Total Revenue"])
        axes[0, col].set_title(f"{label}\nDaily net value = ${total:,.2f}", fontsize=12)

        ax = axes[0, col]
        ax.step(x, trace["p_EV_kW"], where="post", color=colors["ev"], label="$p^{EV}$")
        ax.step(x, trace["p_BESS_kW"], where="post", color=colors["bess"], label="$p^{BESS}$")
        ax.step(x, trace["p_GI_kW"], where="post", color=colors["grid"], label="$p^{GI}$")
        ax.step(x, trace["baseline_kW"], where="post", color=colors["baseline"], linestyle="--", label="EV baseline")
        ax.axhline(0.0, color="0.25", linewidth=0.7)
        ax.set_ylabel("Power (kW)")
        ax.legend(ncol=2, fontsize=8, loc="upper right")

        ax = axes[1, col]
        ax.bar(
            x - energy_bar_offset,
            trace["p_DA_kW"],
            width=energy_bar_width,
            color=colors["da"],
            label="$p^{DA}$",
        )
        ax.bar(
            x + energy_bar_offset,
            trace["p_RT_deviation_kW"],
            width=energy_bar_width,
            color=colors["rt"],
            label="$p^{RT}$ deviation",
        )
        ax.step(x, trace["p_actual_kW"], where="mid", color=colors["actual"], linewidth=1.2, label="$p^{actual}$")
        ax.plot(
            x,
            trace["p_up_bound_kW"],
            color=colors["bound"],
            linewidth=1.0,
            label="actual-position upper limit",
        )
        ax.plot(
            x,
            -trace["p_down_bound_kW"],
            color=colors["bound"],
            linewidth=1.0,
            linestyle="--",
            label="actual-position lower limit",
        )
        ax.axhline(0.0, color="0.25", linewidth=0.7)
        ax.set_ylabel("Energy position (kW)")
        ax.legend(ncol=2, fontsize=8, loc="upper right")

        ax = axes[2, col]
        bottom_up = np.zeros(len(trace))
        for key, color, legend in (
            ("c_RU_actual_kW", colors["ru"], "RU actual"),
            ("c_SP_actual_kW", colors["sp"], "SP actual"),
            ("c_NSP_actual_kW", colors["nsp"], "NSP actual"),
        ):
            ax.bar(x, trace[key], bottom=bottom_up, width=as_bar_width, color=color, label=legend)
            bottom_up = bottom_up + trace[key].to_numpy(float)
        ax.bar(x, -trace["c_RD_actual_kW"], width=as_bar_width, color=colors["rd"], label="RD actual")
        as_up_room = trace["p_up_bound_kW"] - np.maximum(trace["p_actual_kW"], 0.0)
        as_down_room = trace["p_down_bound_kW"] - np.maximum(-trace["p_actual_kW"], 0.0)
        ax.plot(x, as_up_room, color=colors["bound"], linewidth=1.0, label="AS up room")
        ax.plot(x, -as_down_room, color=colors["bound"], linewidth=1.0, linestyle="--", label="-AS down room")
        ax.axhline(0.0, color="0.25", linewidth=0.7)
        ax.set_ylabel("Actual AS (kW)")
        ax.legend(ncol=2, fontsize=8, loc="upper right")

        ax = axes[3, col]
        ax.plot(x, 100.0 * trace["SOC"], color=colors["grid"], linewidth=1.5, label="BESS SOC")
        ax.set_ylabel("SOC (%)")
        ax.set_ylim(0, 100)
        ax2 = ax.twinx()
        ax2.step(x, trace["TOU_$/kWh"], where="post", color="#9467bd", label="TOU")
        ax2.step(x, trace["LMP_DA_$/kWh"], where="post", color=colors["da"], linestyle="--", label="LMP DA")
        ax2.step(x, trace["LMP_RT_$/kWh"], where="post", color=colors["rt"], linestyle=":", label="LMP RT")
        ax2.set_ylabel("Price ($/kWh)")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, ncol=2, fontsize=8, loc="upper right")

        ax = axes[4, col]
        meter = np.abs(trace["meter_balance_residual_kW"].to_numpy(float))
        up_violation = np.maximum(-trace["actual_up_capability_slack_kW"].to_numpy(float), 0.0)
        down_violation = np.maximum(-trace["actual_down_capability_slack_kW"].to_numpy(float), 0.0)
        ax.semilogy(x, np.maximum(meter, 1e-12), label="|meter residual|")
        ax.semilogy(x, np.maximum(up_violation, 1e-12), label="up-capability violation")
        ax.semilogy(x, np.maximum(down_violation, 1e-12), label="down-capability violation")
        ax.axhline(1e-6, color="#f26b38", linestyle="--", linewidth=1.0, label="$10^{-6}$ kW")
        ax.set_ylabel("Violation (kW)")
        ax.set_ylim(1e-12, 1e0)
        ax.legend(ncol=1, fontsize=8, loc="upper right")
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.tick_params(axis="x", rotation=45)
        ax.set_xlabel("Time of day")
        for row_ax in axes[:, col]:
            row_ax.set_xlim(day_ts, day_ts + pd.Timedelta(days=1))

    row_labels = [
        "(a) Executed physical power",
        "(b) Settlement components and bounded actual position",
        "(c) Actual ancillary-service provision",
        "(d) BESS SOC and prices",
        "(e) Numerical constraint violations",
    ]
    for row, row_label in enumerate(row_labels):
        axes[row, 0].text(
            -0.18,
            1.04,
            row_label,
            transform=axes[row, 0].transAxes,
            fontsize=11,
            fontweight="bold",
            va="bottom",
        )
        for ax in axes[row]:
            ax.grid(True, alpha=0.2)

    fig.suptitle(
        (
            "Rolling MPC and full billing-period oracle daily validation"
            if source == "formal"
            else "Rolling MPC and one-day simultaneous benchmark validation"
        )
        + f" — {day_ts:%Y-%m-%d}",
        fontsize=15,
        y=0.997,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.985))
    out = output_root / f"{day_ts:%Y-%m-%d}"
    out.mkdir(parents=True, exist_ok=True)
    png = out / "rolling_oracle_daily_validation.png"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    plt.close(fig)

    audit_rows = []
    for (label, trace_path, financial_path), trace, financial in zip(
        scenario_specs,
        traces,
        finances,
    ):
        actual_identity = np.max(
            np.abs(
                trace["p_actual_kW"].to_numpy(float)
                - trace["p_DA_kW"].to_numpy(float)
                - trace["p_RT_deviation_kW"].to_numpy(float)
            )
        )
        actual_as_min = min(
            float(trace[col].min())
            for col in (
                "c_RU_actual_kW",
                "c_RD_actual_kW",
                "c_SP_actual_kW",
                "c_NSP_actual_kW",
            )
        )
        audit_rows.append({
            "Scenario": label,
            "Trace file": str(trace_path.relative_to(REPO)),
            "Financial file": str(financial_path.relative_to(REPO)),
            "Intervals": len(trace),
            "Duplicate timestamps": int(trace["Interval start"].duplicated().sum()),
            "EV energy kWh": DT_H * float(trace["p_EV_kW"].sum()),
            "Terminal SOC": float(trace["SOC"].iloc[-1]),
            "Total Revenue": float(financial["Total Revenue"]),
            "meter balance max error kW": float(
                np.max(np.abs(trace["meter_balance_residual_kW"]))
            ),
            "p_actual identity max error kW": float(actual_identity),
            "actual AS minimum kW": actual_as_min,
            "up capability max violation kW": float(
                np.max(np.maximum(-trace["actual_up_capability_slack_kW"], 0.0))
            ),
            "down capability max violation kW": float(
                np.max(np.maximum(-trace["actual_down_capability_slack_kW"], 0.0))
            ),
        })
    audit = pd.DataFrame(audit_rows)
    audit.to_csv(out / "daily_validation_audit.csv", index=False, float_format="%.10g")
    cross = pd.DataFrame([{
        "Date": day_ts.date().isoformat(),
        "Perfect MPC vs oracle baseline max error kW": float(
            np.max(np.abs(traces[1]["baseline_kW"] - traces[2]["baseline_kW"]))
        ),
        "Persistence vs Perfect baseline max difference kW": float(
            np.max(np.abs(traces[0]["baseline_kW"] - traces[1]["baseline_kW"]))
        ),
        "Price input max error across scenarios": float(max(
            np.max(np.abs(traces[i][col] - traces[2][col]))
            for i in (0, 1)
            for col in ("LMP_DA_$/kWh", "LMP_RT_$/kWh", "TOU_$/kWh")
        )),
        "EV energy spread kWh": float(
            audit["EV energy kWh"].max() - audit["EV energy kWh"].min()
        ),
        "Benchmark minus Rolling Perfect revenue": float(
            audit.loc[audit["Scenario"] == benchmark_label, "Total Revenue"].iloc[0]
            - audit.loc[audit["Scenario"] == "Rolling 24 h Perfect", "Total Revenue"].iloc[0]
        ),
        "Perfect-baseline identical": bool(
            np.max(np.abs(traces[1]["baseline_kW"] - traces[2]["baseline_kW"])) <= 1e-8
        ),
    }])
    cross.to_csv(out / "daily_validation_cross_scenario.csv", index=False, float_format="%.10g")
    return [
        png,
        pdf,
        out / "daily_validation_audit.csv",
        out / "daily_validation_cross_scenario.csv",
    ]


def build_gate_d_stress_report() -> tuple[Path, Path]:
    """Aggregate the selected-day Rolling validation into CSV and Markdown."""
    selection_path = (
        OUT_ROOT / "short_tests" / "gate_d" / "stress_date_selection.csv"
    )
    selection = pd.read_csv(selection_path)
    dates = sorted(pd.to_datetime(selection["Date"], errors="raise").unique())
    rows = []
    for date_value in dates:
        day = pd.Timestamp(date_value).normalize()
        tagged_root = _short_mpc_run_root(day, 1e-2)
        mpc_root = tagged_root if tagged_root.exists() else _short_mpc_run_root(day)
        solver = pd.read_csv(mpc_root / "solver_audit.csv")
        metadata = pd.read_csv(mpc_root / "run_metadata.csv").iloc[0]
        finance = {}
        for forecast in ("perfect", "persistence"):
            financial_path = (
                mpc_root
                / "Plots"
                / "Cost"
                / FORECAST_PREFIX[forecast]
                / "daily_financial_detail.csv"
            )
            financial = pd.read_csv(financial_path)
            financial["Date"] = pd.to_datetime(
                financial["Date"], errors="raise"
            )
            financial = financial[
                financial["Date"].dt.normalize() == day
            ]
            if "Case" in financial:
                financial = financial[financial["Case"] == "Both"]
            if len(financial) != 1:
                raise ValueError(
                    f"{forecast} financial table has {len(financial)} rows for {day.date()}"
                )
            finance[forecast] = financial.iloc[0]

        graph_root = (
            OUT_ROOT
            / "short_tests"
            / "rolling"
            / "daily_graphs"
            / f"{day:%Y-%m-%d}"
        )
        audit = pd.read_csv(graph_root / "daily_validation_audit.csv")
        cross = pd.read_csv(
            graph_root / "daily_validation_cross_scenario.csv"
        ).iloc[0]
        oracle_root = (
            OUT_ROOT
            / "short_tests"
            / "rolling_perfect"
            / "oracle"
            / f"{day:%Y-%m-%d}_to_{day:%Y-%m-%d}_baseline-short-mpc"
        )
        oracle = pd.read_csv(oracle_root / "oracle_monthly_summary.csv").iloc[0]
        rolling_audit = audit[
            audit["Scenario"].isin(
                ["Rolling 24 h Perfect", "Rolling 24 h Persistence"]
            )
        ]
        perfect_total = float(finance["perfect"]["Total Revenue"])
        persistence_total = float(finance["persistence"]["Total Revenue"])
        ev_revenue_error = abs(
            float(finance["perfect"]["EV Revenue"])
            - float(finance["persistence"]["EV Revenue"])
        )
        rows.append({
            "Date": day.date().isoformat(),
            "selection_criteria": "; ".join(
                selection.loc[
                    pd.to_datetime(selection["Date"]).dt.normalize() == day,
                    "criterion",
                ].tolist()
            ),
            "MPC_requested_gap": float(metadata["requested_mip_gap"]),
            "MPC_max_achieved_gap": float(solver["mip_gap"].max()),
            "MPC_solver_rows": len(solver),
            "MPC_all_status_optimal": bool(
                (solver["cvxpy_status"] == "optimal").all()
            ),
            "MPC_time_limit_events": int(metadata["time_limit_events"]),
            "MPC_max_step_runtime_s": float(solver["runtime_s"].max()),
            "Perfect_total_revenue_$": perfect_total,
            "Persistence_total_revenue_$": persistence_total,
            "Perfect_minus_Persistence_$": perfect_total - persistence_total,
            "EV_revenue_difference_$": ev_revenue_error,
            "EV_energy_spread_kWh": float(
                rolling_audit["EV energy kWh"].max()
                - rolling_audit["EV energy kWh"].min()
            ),
            "terminal_SOC_max_error": float(
                np.max(np.abs(rolling_audit["Terminal SOC"] - 0.5))
            ),
            "meter_balance_max_error_kW": float(
                rolling_audit["meter balance max error kW"].max()
            ),
            "p_actual_identity_max_error_kW": float(
                rolling_audit["p_actual identity max error kW"].max()
            ),
            "actual_AS_minimum_kW": float(
                rolling_audit["actual AS minimum kW"].min()
            ),
            "up_capability_max_violation_kW": float(
                rolling_audit["up capability max violation kW"].max()
            ),
            "down_capability_max_violation_kW": float(
                rolling_audit["down capability max violation kW"].max()
            ),
            "Perfect_MPC_benchmark_baseline_error_kW": float(
                cross["Perfect MPC vs oracle baseline max error kW"]
            ),
            "price_input_max_error": float(
                cross["Price input max error across scenarios"]
            ),
            "one_day_benchmark_incumbent_$": float(oracle["Total Revenue"]),
            "one_day_benchmark_best_bound_$": float(
                oracle["objective_best_bound"]
            ),
            "one_day_benchmark_gap": float(oracle["mip_gap"]),
            "one_day_benchmark_status": str(oracle["status_name"]),
            "one_day_benchmark_minus_Perfect_$": (
                float(oracle["Total Revenue"]) - perfect_total
            ),
            "all_physical_checks_pass": bool(
                ev_revenue_error <= 0.01
                and float(
                    rolling_audit["EV energy kWh"].max()
                    - rolling_audit["EV energy kWh"].min()
                )
                <= 0.01
                and np.max(np.abs(rolling_audit["Terminal SOC"] - 0.5))
                <= 1e-6
                and rolling_audit["meter balance max error kW"].max() <= 1e-6
                and rolling_audit["p_actual identity max error kW"].max()
                <= 1e-6
                and rolling_audit["actual AS minimum kW"].min() >= -1e-6
                and rolling_audit["up capability max violation kW"].max()
                <= 1e-6
                and rolling_audit["down capability max violation kW"].max()
                <= 1e-6
                and float(
                    cross["Perfect MPC vs oracle baseline max error kW"]
                )
                <= 1e-8
                and float(cross["Price input max error across scenarios"])
                <= 1e-8
            ),
        })

    report = pd.DataFrame(rows)
    out = OUT_ROOT / "short_tests" / "gate_d"
    csv_path = out / "gate_d_stress_test_summary.csv"
    md_path = out / "GATE_D_STRESS_TEST_REPORT.md"
    report.to_csv(csv_path, index=False, float_format="%.10g")
    all_solver = bool(
        report["MPC_all_status_optimal"].all()
        and (report["MPC_time_limit_events"] == 0).all()
        and (report["MPC_max_achieved_gap"] <= 0.01 + 1e-12).all()
    )
    all_physical = bool(report["all_physical_checks_pass"].all())
    table_cols = [
        "Date",
        "MPC_max_achieved_gap",
        "MPC_max_step_runtime_s",
        "Perfect_total_revenue_$",
        "Persistence_total_revenue_$",
        "Perfect_minus_Persistence_$",
        "one_day_benchmark_incumbent_$",
        "one_day_benchmark_best_bound_$",
        "one_day_benchmark_gap",
        "all_physical_checks_pass",
    ]
    display = report[table_cols].copy()
    for col in display.select_dtypes(include=[np.number]).columns:
        display[col] = display[col].map(lambda value: f"{value:.6g}")
    header = "| " + " | ".join(display.columns) + " |"
    separator = "| " + " | ".join(["---"] * len(display.columns)) + " |"
    body = "\n".join(
        "| " + " | ".join(map(str, row)) + " |"
        for row in display.itertuples(index=False, name=None)
    )
    md_path.write_text(
        "# Gate D selected-day stress-test report\n\n"
        "All 24-hour MPC tests use the requested 1% MIP gap. The third "
        "scenario is a standalone one-day simultaneous Perfect benchmark, "
        "not a slice of the full billing-period oracle. Therefore its "
        "incumbent is diagnostic and is reported together with its certified "
        "best bound; only the future formal billing-period oracle has the "
        "full-period upper-bound interpretation.\n\n"
        f"- Solver audit pass: **{all_solver}**\n"
        f"- Physical/accounting audit pass: **{all_physical}**\n"
        "- Daily Perfect >= Persistence is reported empirically, not imposed "
        "as a correctness requirement.\n"
        "- Perfect and Persistence EV revenue equality tolerance: $0.01/day.\n\n"
        + header
        + "\n"
        + separator
        + "\n"
        + body
        + "\n",
        encoding="utf-8",
    )
    print(csv_path)
    print(md_path)
    return csv_path, md_path


def _matched_main_source(main: str) -> str:
    """Inject controlled thresholds, RT baseline, and immutable DA reference."""
    main = main.replace("_init_ncd = 0.0", "_init_ncd = float(MATCHED_INITIAL_NCD_KW)")
    main = main.replace("_init_pd = 0.0", "_init_pd = float(MATCHED_INITIAL_PD_KW)")
    baseline_needle = """        #Assign real values for RT (2 cases) amd DA
"""
    baseline_replacement = """        if MATCHED_RT_BASELINE_REFERENCE is not None:
            Baseline_Opt_fc = [
                np.asarray(_matched_baseline, dtype=float).copy()
                for _matched_baseline in MATCHED_RT_BASELINE_REFERENCE
            ]
        #Assign real values for RT (2 cases) amd DA
"""
    if baseline_needle not in main:
        raise RuntimeError("Could not locate RT baseline assignment for matched-state injection")
    main = main.replace(baseline_needle, baseline_replacement, 1)
    needle = """        p_RT_value_DA = p_RT.value
"""
    replacement = """        p_RT_value_DA = p_RT.value
        if MATCHED_DA_REFERENCE is not None:
            p_DA_value_DA = np.asarray(MATCHED_DA_REFERENCE['p_DA'], dtype=float).copy()
            c_RU_DA_value_DA = np.asarray(MATCHED_DA_REFERENCE['c_RU_DA'], dtype=float).copy()
            c_RD_DA_value_DA = np.asarray(MATCHED_DA_REFERENCE['c_RD_DA'], dtype=float).copy()
            c_SP_DA_value_DA = np.asarray(MATCHED_DA_REFERENCE['c_SP_DA'], dtype=float).copy()
            c_NSP_DA_value_DA = np.asarray(MATCHED_DA_REFERENCE['c_NSP_DA'], dtype=float).copy()
"""
    if needle not in main:
        raise RuntimeError("Could not locate DA result assignment for matched-state injection")
    return main.replace(needle, replacement, 1)


def run_matched_state(
    controller: str,
    dates: list[int] | None = None,
    mip_gap: float | None = None,
) -> None:
    """Run controlled one-day Perfect/Persistence RT comparisons.

    Each date starts from SOC=0.5, NCD threshold=100 kW and PD threshold=80 kW.
    Both forecasts use the same Perfect-history file and the same RT baseline
    vector captured from the Perfect run. The Perfect run's DA energy and AS
    awards are copied verbatim into the Persistence run. Thus the only scenario
    switch that reaches RT is the EV forecast information set.
    """
    dates = dates or [3, 15, 27]
    out = OUT_ROOT / controller / "matched_state"
    out.mkdir(parents=True, exist_ok=True)
    detail_rows = []
    summary_rows = []
    for day in dates:
        da_reference = None
        rt_baseline_reference = None
        for forecast in ("perfect", "persistence"):
            scratch = _prepare_scratch(controller, f"matched_{day:02d}_{forecast}")
            old_cwd = Path.cwd()
            try:
                os.chdir(scratch)
                env, _nb, main, _daily, _summary = _load_notebook_runtime(controller, scratch)
                main = _matched_main_source(main)
                common_baseline_path = (
                    scratch
                    / "Results_Shrinking"
                    / "Dispatch"
                    / f"{FORECAST_PREFIX['perfect']}_baseline.csv"
                )
                common_baseline = pd.read_csv(common_baseline_path, low_memory=False)
                common_baseline["Interval start"] = pd.to_datetime(
                    common_baseline["Interval start"], errors="raise"
                )
                env.update(
                    TARGET_SAVE="RT",
                    RUN_MONTHS_CONFIG=[6],
                    RUN_DAYS_CONFIG=[day],
                    PLOT_DAILY_6PANEL_DATES=[],
                    SAVE_FINAL_FINANCIAL_FIGURES=False,
                    CLEAR_IMPLEMENTATION_AT_RUN_START=True,
                    WM_Mode="full",
                    Enable_WM=True,
                    RT_SOLVER_STATUS_COUNTS={},
                    RT_SOLVER_LIMIT_EVENTS=[],
                    MATCHED_INITIAL_NCD_KW=100.0,
                    MATCHED_INITIAL_PD_KW=80.0,
                    MATCHED_DA_REFERENCE=da_reference,
                    MATCHED_RT_BASELINE_REFERENCE=rt_baseline_reference,
                    Dispatch_2025_baseline=common_baseline.copy(deep=True),
                )
                if mip_gap is not None:
                    env["GUROBI_MIPGAP"] = float(mip_gap)
                if forecast == "perfect":
                    env.update(
                        Fc_SessionkWh="PerfectSessionkWh",
                        Fc_NumbEV="PerfectNumbEV",
                        Fc_AtArrival="PerfectatArrival",
                    )
                else:
                    env.update(
                        Fc_SessionkWh="PersistenceSessionkWh",
                        Fc_NumbEV="PersistenceNumbEV",
                        Fc_AtArrival="PerfectatArrival",
                    )
                exec(compile(main, f"{NOTEBOOKS[controller]}:matched", "exec"), env, env)
                if env["RT_SOLVER_LIMIT_EVENTS"]:
                    raise RuntimeError(
                        f"Matched-state {controller} June {day}/{forecast} hit watchdog: "
                        f"{env['RT_SOLVER_LIMIT_EVENTS'][:3]}"
                    )
                if forecast == "perfect":
                    rt_baseline_reference = [
                        np.asarray(_baseline, float).copy()
                        for _baseline in env["Baseline_Opt_fc"]
                    ]
                    da_reference = {
                        "p_DA": np.asarray(env["p_DA_value_DA"], float).copy(),
                        "c_RU_DA": np.asarray(env["c_RU_DA_value_DA"], float).copy(),
                        "c_RD_DA": np.asarray(env["c_RD_DA_value_DA"], float).copy(),
                        "c_SP_DA": np.asarray(env["c_SP_DA_value_DA"], float).copy(),
                        "c_NSP_DA": np.asarray(env["c_NSP_DA_value_DA"], float).copy(),
                    }
                sol = env["Solver_Outputs_RT_Base"]
                p_gi = np.asarray(sol["p_GI"], float)
                p_ev = np.asarray(sol["p_EV"], float)
                p_bess = np.asarray(sol["p_BESS"], float)
                p_da = np.asarray(sol["p_DA"], float)
                p_rt = np.asarray(sol["p_RT"], float)
                p_ev_max = np.asarray(sol["P_EV_max"], float)
                wm = np.asarray(sol["Revenue_WM"], float)
                tou = np.asarray(sol["Cost_TOU"], float)
                ev_rev = np.asarray(sol["Revenue_EV"], float)
                ncd_cost = 15.38 * max(float(np.max(p_gi)) - 100.0, 0.0)
                pd_cost = 3.05 * max(float(np.max(p_gi[64:84])) - 80.0, 0.0)
                total = float(wm.sum() + ev_rev.sum() - tou.sum() - ncd_cost - pd_cost)
                summary_rows.append({
                    "Controller": controller.title(),
                    "Date": f"2025-06-{day:02d}",
                    "Forecast": forecast.title(),
                    "Initial SOC": 0.5,
                    "Initial NCD threshold kW": 100.0,
                    "Initial PD threshold kW": 80.0,
                    "Common baseline": "Perfect RT baseline vector",
                    "RT baseline max error kW": float(max(
                        np.max(np.abs(np.asarray(_actual, float) - np.asarray(_reference, float)))
                        for _actual, _reference in zip(env["Baseline_Opt_fc"], rt_baseline_reference)
                    )),
                    "Configured MIPGap": float(env["GUROBI_MIPGAP"]),
                    "Total Revenue": total,
                    "WM Revenue": float(wm.sum()),
                    "TOU Cost": -float(tou.sum()),
                    "PD Cost": -pd_cost,
                    "NCD Cost": -ncd_cost,
                    "EV Revenue": float(ev_rev.sum()),
                    "EV Energy kWh": float(DT_H * p_ev.sum()),
                    "P_EV_max peak kW": float(np.max(p_ev_max)),
                    "P_EV_max mean kW": float(np.mean(p_ev_max)),
                    "End SOC": float(np.asarray(sol["soc_BESS"], float)[-1]),
                    "DA reference max error kW": float(np.max(np.abs(p_da - da_reference["p_DA"]))),
                    "meter balance max error kW": float(np.max(np.abs(p_gi - p_ev - p_bess))),
                    "RT solver status counts": json.dumps(
                        env["RT_SOLVER_STATUS_COUNTS"], sort_keys=True
                    ),
                    "RT TimeLimit events": len(env["RT_SOLVER_LIMIT_EVENTS"]),
                })
                for t, stamp in enumerate(pd.date_range(f"2025-06-{day:02d}", periods=96, freq="15min")):
                    detail_rows.append({
                        "Controller": controller.title(),
                        "Date": f"2025-06-{day:02d}",
                        "Forecast": forecast.title(),
                        "Interval start": stamp,
                        "p_GI_kW": p_gi[t],
                        "p_EV_kW": p_ev[t],
                        "p_BESS_kW": p_bess[t],
                        "p_DA_kW": p_da[t],
                        "p_RT_deviation_kW": p_rt[t],
                        "p_actual_kW": p_da[t] + p_rt[t],
                        "P_EV_max_kW": p_ev_max[t],
                        "SOC": np.asarray(sol["soc_BESS"], float)[t],
                        "c_RU_DA_kW": np.asarray(sol["c_RU_DA"], float)[t],
                        "c_RU_RT_kW": np.asarray(sol["c_RU_RT"], float)[t],
                        "c_RD_DA_kW": np.asarray(sol["c_RD_DA"], float)[t],
                        "c_RD_RT_kW": np.asarray(sol["c_RD_RT"], float)[t],
                        "c_SP_DA_kW": np.asarray(sol["c_SP_DA"], float)[t],
                        "c_SP_RT_kW": np.asarray(sol["c_SP_RT"], float)[t],
                        "c_NSP_DA_kW": np.asarray(sol["c_NSP_DA"], float)[t],
                        "c_NSP_RT_kW": np.asarray(sol["c_NSP_RT"], float)[t],
                    })
            finally:
                os.chdir(old_cwd)
                if scratch.exists():
                    shutil.rmtree(scratch)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out / "matched_state_daily_summary.csv", index=False, float_format="%.8f")
    pd.DataFrame(detail_rows).to_csv(out / "matched_state_dispatch.csv", index=False, float_format="%.8f")
    pivot = summary.pivot(index="Date", columns="Forecast", values="Total Revenue")
    end_soc = summary.pivot(index="Date", columns="Forecast", values="End SOC")
    comparison = pd.DataFrame({
        "Controller": controller.title(),
        "Date": pivot.index,
        "Perfect Total Revenue": pivot["Perfect"].to_numpy(),
        "Persistence Total Revenue": pivot["Persistence"].to_numpy(),
        "Perfect minus Persistence": (pivot["Perfect"] - pivot["Persistence"]).to_numpy(),
        "Perfect better": (pivot["Perfect"] >= pivot["Persistence"] - 0.01).to_numpy(),
        "Perfect End SOC": end_soc["Perfect"].to_numpy(),
        "Persistence End SOC": end_soc["Persistence"].to_numpy(),
    })
    comparison.to_csv(out / "matched_state_comparison.csv", index=False, float_format="%.8f")
    _write_combined_matched_state_comparison()


def _write_combined_matched_state_comparison() -> None:
    """Write one controller-comparison table whenever matched outputs exist."""
    frames = []
    for controller in NOTEBOOKS:
        path = OUT_ROOT / controller / "matched_state" / "matched_state_comparison.csv"
        if path.exists():
            frames.append(pd.read_csv(path))
    if not frames:
        return
    combined = pd.concat(frames, ignore_index=True).sort_values(["Controller", "Date"])
    out = OUT_ROOT / "common" / "matched_state"
    out.mkdir(parents=True, exist_ok=True)
    combined["Formal Perfect better"] = combined["Perfect better"]
    audit_path = out / "matched_state_exact_gap_audit.csv"
    if audit_path.exists():
        audit = pd.read_csv(audit_path)[[
            "Controller",
            "Date",
            "Perfect Total Revenue",
            "Persistence Total Revenue",
            "Perfect minus Persistence",
        ]].rename(columns={
            "Perfect Total Revenue": "Exact Perfect Total Revenue",
            "Persistence Total Revenue": "Exact Persistence Total Revenue",
            "Perfect minus Persistence": "Exact Perfect minus Persistence",
        })
        combined = combined.merge(audit, on=["Controller", "Date"], how="left")
    else:
        combined["Exact Perfect Total Revenue"] = np.nan
        combined["Exact Persistence Total Revenue"] = np.nan
        combined["Exact Perfect minus Persistence"] = np.nan
    combined["Exact audit performed"] = combined["Exact Perfect minus Persistence"].notna()
    combined["Certified Perfect minus Persistence"] = combined[
        "Exact Perfect minus Persistence"
    ].fillna(combined["Perfect minus Persistence"])
    combined["Certified Perfect better"] = (
        combined["Certified Perfect minus Persistence"] >= -0.01
    )
    combined.to_csv(
        out / "matched_state_june_comparison.csv",
        index=False,
        float_format="%.8f",
    )


def build_gate_e_report(formal_tag: str) -> tuple[Path, Path]:
    """Audit one immutable, complete-June Rolling validation snapshot."""
    root = _formal_run_root(formal_tag)
    rolling_root = root / "rolling"
    oracle_root = root / "rolling_perfect" / "oracle"
    required = [
        rolling_root / "run_metadata.csv",
        rolling_root / "solver_audit.csv",
        oracle_root / "oracle_monthly_summary.csv",
        oracle_root / "oracle_daily_financial.csv",
        oracle_root / "oracle_dispatch.csv",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Gate E inputs are missing: {missing}")

    metadata = pd.read_csv(rolling_root / "run_metadata.csv").iloc[0]
    solver = pd.read_csv(rolling_root / "solver_audit.csv")
    oracle = pd.read_csv(oracle_root / "oracle_monthly_summary.csv").iloc[0]
    oracle_daily = pd.read_csv(oracle_root / "oracle_daily_financial.csv")

    finance_specs = {
        "Rolling 24 h Perfect": FORECAST_PREFIX["perfect"],
        "Rolling 24 h Persistence": FORECAST_PREFIX["persistence"],
    }
    daily_frames = []
    monthly_rows = []
    for scenario, prefix in finance_specs.items():
        path = (
            rolling_root
            / "Plots"
            / "Cost"
            / prefix
            / "daily_financial_detail.csv"
        )
        frame = pd.read_csv(path)
        frame = frame[frame["Case"] == "Both"].copy()
        frame.insert(0, "Scenario", scenario)
        daily_frames.append(frame)
        monthly_rows.append({
            "Scenario": scenario,
            **{
                column: float(frame[column].sum())
                for column in (
                    "Total Revenue",
                    "WM Revenue",
                    "TOU Cost",
                    "PD Cost",
                    "NCD Cost",
                    "EV Revenue",
                )
            },
        })
    oracle_daily_for_table = oracle_daily.copy()
    oracle_daily_for_table.insert(
        0, "Scenario", "Full billing-period Perfect oracle"
    )
    daily_frames.append(oracle_daily_for_table)
    monthly_rows.append({
        "Scenario": "Full billing-period Perfect oracle",
        **{
            column: float(oracle[column])
            for column in (
                "Total Revenue",
                "WM Revenue",
                "TOU Cost",
                "PD Cost",
                "NCD Cost",
                "EV Revenue",
            )
        },
    })
    daily_finance = pd.concat(daily_frames, ignore_index=True, sort=False)
    monthly = pd.DataFrame(monthly_rows)
    daily_path = root / "gate_e_daily_financial_comparison.csv"
    monthly_path = root / "gate_e_monthly_financial_comparison.csv"
    daily_finance.to_csv(daily_path, index=False, float_format="%.8f")
    monthly.to_csv(monthly_path, index=False, float_format="%.8f")

    graph_root = rolling_root / "daily_graphs"
    audit_files = sorted(graph_root.glob("2025-06-*/daily_validation_audit.csv"))
    cross_files = sorted(
        graph_root.glob("2025-06-*/daily_validation_cross_scenario.csv")
    )
    if len(audit_files) != 30 or len(cross_files) != 30:
        raise RuntimeError(
            "Gate E requires 30 daily audit and 30 cross-scenario files"
        )
    daily_audit = pd.concat(
        [pd.read_csv(path) for path in audit_files], ignore_index=True
    )
    cross = pd.concat(
        [pd.read_csv(path) for path in cross_files], ignore_index=True
    )

    perfect_daily = daily_frames[0].set_index("Date")
    persistence_daily = daily_frames[1].set_index("Date")
    rolling_ev_revenue_spread = (
        perfect_daily["EV Revenue"] - persistence_daily["EV Revenue"]
    ).abs()
    financial_identity = (
        daily_finance["WM Revenue"]
        + daily_finance["TOU Cost"]
        + daily_finance["PD Cost"]
        + daily_finance["NCD Cost"]
        + daily_finance["EV Revenue"]
        - daily_finance["Total Revenue"]
    ).abs()
    trace_files = sorted(
        (rolling_root / "Validation_Traces").glob(
            "*/rolling_validation_trace_202506*.csv"
        )
    )
    graph_pngs = sorted(
        graph_root.glob("2025-06-*/rolling_oracle_daily_validation.png")
    )
    final_day_audit = pd.read_csv(
        graph_root / "2025-06-30" / "daily_validation_audit.csv"
    )
    rolling_final_soc_error = float(
        (
            final_day_audit[
                final_day_audit["Scenario"].str.startswith("Rolling 24 h")
            ]["Terminal SOC"]
            - 0.5
        )
        .abs()
        .max()
    )
    rolling_perfect_total = float(
        monthly.loc[
            monthly["Scenario"] == "Rolling 24 h Perfect", "Total Revenue"
        ].iloc[0]
    )

    checks = [
        {
            "check": "Formal tag and complete-June scenario routing",
            "pass": bool(
                str(metadata["formal_tag"]) == formal_tag
                and str(metadata["run_modes"]) == "full"
                and str(metadata["run_forecasts"]) == "perfect,persistence"
                and len(str(metadata["run_days"]).split(",")) == 30
            ),
            "observed": f"{metadata['formal_tag']}; {metadata['run_modes']}; {metadata['run_forecasts']}",
            "criterion": "matching tag; full; perfect,persistence; 30 days",
        },
        {
            "check": "Rolling solver records complete",
            "pass": bool(len(solver) == 5820),
            "observed": len(solver),
            "criterion": "5820 = 2 x (30 DA + 2880 RT)",
        },
        {
            "check": "Every Rolling solve accepted by Gurobi/CVXPY",
            "pass": bool(
                (solver["gurobi_status"] == GRB.OPTIMAL).all()
                and solver["cvxpy_status"].eq("optimal").all()
            ),
            "observed": (
                f"Gurobi={solver['gurobi_status'].value_counts().to_dict()}, "
                f"CVXPY={solver['cvxpy_status'].value_counts().to_dict()}"
            ),
            "criterion": "all Gurobi status 2 and CVXPY optimal",
        },
        {
            "check": "Rolling MIP gap <= 1%",
            "pass": bool(solver["mip_gap"].max() <= 0.01 + 1e-12),
            "observed": float(solver["mip_gap"].max()),
            "criterion": "<= 0.01",
        },
        {
            "check": "No Rolling time-limit event",
            "pass": bool(
                int(metadata["time_limit_events"]) == 0
                and not (solver["gurobi_status"] == GRB.TIME_LIMIT).any()
            ),
            "observed": int(metadata["time_limit_events"]),
            "criterion": "0",
        },
        {
            "check": "Rolling traces complete and unique",
            "pass": bool(
                len(trace_files) == 60
                and len(daily_audit) == 90
                and daily_audit["Intervals"].eq(96).all()
                and daily_audit["Duplicate timestamps"].eq(0).all()
            ),
            "observed": f"{len(trace_files)} traces; {len(daily_audit)} scenario-days",
            "criterion": "60 traces; 90 scenario-days; 96 unique intervals each",
        },
        {
            "check": "Meter balance",
            "pass": bool(
                daily_audit["meter balance max error kW"].max() <= 1e-6
            ),
            "observed": float(
                daily_audit["meter balance max error kW"].max()
            ),
            "criterion": "<= 1e-6 kW",
        },
        {
            "check": "Settlement identity p_actual = p_DA + p_RT",
            "pass": bool(
                daily_audit["p_actual identity max error kW"].max() <= 1e-6
            ),
            "observed": float(
                daily_audit["p_actual identity max error kW"].max()
            ),
            "criterion": "<= 1e-6 kW",
        },
        {
            "check": "Actual AS nonnegative",
            "pass": bool(daily_audit["actual AS minimum kW"].min() >= -1e-6),
            "observed": float(daily_audit["actual AS minimum kW"].min()),
            "criterion": ">= -1e-6 kW",
        },
        {
            "check": "Actual up/down capability",
            "pass": bool(
                daily_audit["up capability max violation kW"].max() <= 1e-6
                and daily_audit[
                    "down capability max violation kW"
                ].max()
                <= 1e-6
            ),
            "observed": (
                f"up={daily_audit['up capability max violation kW'].max():.3e}, "
                f"down={daily_audit['down capability max violation kW'].max():.3e}"
            ),
            "criterion": "each <= 1e-6 kW",
        },
        {
            "check": "Daily EV energy equal across all three scenarios",
            "pass": bool(cross["EV energy spread kWh"].max() <= 1e-4),
            "observed": float(cross["EV energy spread kWh"].max()),
            "criterion": "<= 1e-4 kWh",
        },
        {
            "check": "Daily EV revenue equal for Rolling Perfect/Persistence",
            "pass": bool(rolling_ev_revenue_spread.max() <= 0.01 + 1e-12),
            "observed": float(rolling_ev_revenue_spread.max()),
            "criterion": "<= $0.01",
        },
        {
            "check": "Rolling final billing-period SOC",
            "pass": bool(rolling_final_soc_error <= 1e-6),
            "observed": rolling_final_soc_error,
            "criterion": "abs(SOC_end - 0.5) <= 1e-6",
        },
        {
            "check": "Oracle solver certificate",
            "pass": bool(
                str(oracle["status_name"]) == "OPTIMAL"
                and not bool(oracle["time_limit_triggered"])
                and float(oracle["mip_gap"]) <= 0.01 + 1e-12
            ),
            "observed": (
                f"{oracle['status_name']}; gap={float(oracle['mip_gap']):.8f}; "
                f"time_limit={bool(oracle['time_limit_triggered'])}"
            ),
            "criterion": "OPTIMAL at configured 1% tolerance; no time limit",
        },
        {
            "check": "Oracle physical and terminal-state audit",
            "pass": bool(
                float(oracle["meter_balance_max_error_kW"]) <= 1e-6
                and float(oracle["as_actual_min_kW"]) >= -1e-6
                and float(oracle["ev_capability_max_violation_kW"]) <= 1e-6
                and float(
                    oracle["actual_up_capability_max_violation_kW"]
                )
                <= 1e-6
                and float(
                    oracle["actual_down_capability_max_violation_kW"]
                )
                <= 1e-6
                and abs(float(oracle["terminal_soc"]) - 0.5) <= 1e-6
            ),
            "observed": (
                f"meter={float(oracle['meter_balance_max_error_kW']):.3e}; "
                f"terminal_SOC={float(oracle['terminal_soc']):.8f}"
            ),
            "criterion": "all residuals <= 1e-6; AS >= -1e-6; SOC_end=0.5",
        },
        {
            "check": "Oracle uses identical Rolling Perfect baseline",
            "pass": bool(
                cross[
                    "Perfect MPC vs oracle baseline max error kW"
                ].max()
                <= 1e-6
                and cross["Perfect-baseline identical"].astype(bool).all()
            ),
            "observed": float(
                cross[
                    "Perfect MPC vs oracle baseline max error kW"
                ].max()
            ),
            "criterion": "<= 1e-6 kW on every day",
        },
        {
            "check": "Oracle incumbent dominates Rolling 24 h Perfect",
            "pass": bool(float(oracle["Total Revenue"]) >= rolling_perfect_total),
            "observed": float(oracle["Total Revenue"]) - rolling_perfect_total,
            "criterion": "oracle minus MPC >= $0",
        },
        {
            "check": "Daily financial identities",
            "pass": bool(financial_identity.max() <= 0.03 + 1e-12),
            "observed": float(financial_identity.max()),
            "criterion": "<= $0.03 including independently rounded MPC rows",
        },
        {
            "check": "All daily validation figures written",
            "pass": bool(len(graph_pngs) == 30),
            "observed": f"{len(graph_pngs)} PNG",
            "criterion": "30 PNG at 300 dpi",
        },
    ]
    check_df = pd.DataFrame(checks)
    checks_path = root / "gate_e_validation_checks.csv"
    check_df.to_csv(checks_path, index=False)

    solver_summary = (
        solver.groupby(["forecast", "stage"], as_index=False)
        .agg(
            solves=("gurobi_status", "size"),
            max_mip_gap=("mip_gap", "max"),
            max_runtime_s=("runtime_s", "max"),
        )
        .sort_values(["forecast", "stage"])
    )
    solver_summary.to_csv(
        root / "gate_e_solver_summary.csv", index=False, float_format="%.8f"
    )

    archived_attempt_path = (
        root
        / "rolling_perfect"
        / "oracle_attempts"
        / "initial_900s_gap_0.012006"
        / "oracle_monthly_summary.csv"
    )
    archived_note = ""
    if archived_attempt_path.exists():
        archived = pd.read_csv(archived_attempt_path).iloc[0]
        archived_note = (
            f" The archived 900 s attempt found a higher feasible incumbent "
            f"(${float(archived['Total Revenue']):,.2f}) but stopped at "
            f"{100 * float(archived['mip_gap']):.4f}% gap; it is preserved as "
            "best-known feasible evidence and is not substituted into the "
            "accepted run's solver certificate."
        )

    def md_table(frame: pd.DataFrame, digits: int = 4) -> str:
        def fmt(value):
            if isinstance(value, (float, np.floating)):
                return f"{value:.{digits}f}"
            return str(value)
        headers = [str(column) for column in frame.columns]
        rows = [
            [fmt(value) for value in row]
            for row in frame.itertuples(index=False, name=None)
        ]
        return "\n".join([
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
            *["| " + " | ".join(row) + " |" for row in rows],
        ])

    all_pass = bool(check_df["pass"].astype(bool).all())
    report_path = root / "GATE_E_VALIDATION_REPORT.md"
    lines = [
        "# Gate E: formal June 2025 Rolling validation",
        "",
        f"- Formal tag: `{formal_tag}`",
        f"- Result: **{'PASS' if all_pass else 'FAIL'}**",
        f"- Source notebook: `{metadata['source_notebook']}`",
        f"- Source notebook SHA-256: `{metadata['source_notebook_sha256']}`",
        "- Solver tolerance: 1% relative MIP gap.",
        "",
        "## Monthly financial comparison",
        "",
        md_table(monthly, 2),
        "",
        (
            "The accepted full-billing-period Perfect oracle exceeds Rolling "
            f"24 h Perfect by ${float(oracle['Total Revenue']) - rolling_perfect_total:,.2f}. "
            "Gurobi terminated normally at the configured 1% tolerance "
            f"(reported gap {100 * float(oracle['mip_gap']):.4f}%)."
            + archived_note
        ),
        "",
        "## Solver summary",
        "",
        md_table(solver_summary, 6),
        "",
        "## Acceptance checks",
        "",
        md_table(check_df, 8),
        "",
        (
            "Every acceptance check passed. The formal snapshot is suitable "
            "for algorithm-validation discussion."
            if all_pass
            else "At least one acceptance check failed; do not use this snapshot as a paper result."
        ),
        "",
        "## Daily graphical evidence",
        "",
        (
            "Each date from 2025-06-01 through 2025-06-30 has a PNG, a PDF, "
            "a three-scenario physical audit, and a cross-scenario audit under "
            "`rolling/daily_graphs/YYYY-MM-DD/`. Columns are Rolling 24 h "
            "Persistence, Rolling 24 h Perfect, and the full billing-period "
            "Perfect oracle. Rows show executed physical power, separate DA/RT "
            "settlement components with bounded actual position, actual AS, "
            "BESS SOC/prices, and numerical violations."
        ),
        "",
        "## Interpretation boundary",
        "",
        (
            "The oracle is a clairvoyant full-billing-period benchmark under "
            "the same Rolling Perfect exogenous baseline and realized June "
            "inputs. The 24 h Perfect MPC is not expected to reproduce it "
            "because the MPC lacks information beyond its moving horizon and "
            "therefore makes locally optimal, path-dependent SOC, demand-peak, "
            "and irreversible DA-commitment decisions. Daily Perfect-versus-"
            "Persistence revenue ordering is diagnostic, not an acceptance "
            "condition."
        ),
        "",
    ]
    report_path.write_text("\n".join(lines))
    return report_path, checks_path


def build_validation_report() -> None:
    """Combine monthly notebook and oracle outputs into one acceptance report."""
    all_daily = []
    monthly_rows = []
    for controller in NOTEBOOKS:
        for forecast, prefix in FORECAST_PREFIX.items():
            p = OUT_ROOT / controller / "Plots" / "Cost" / prefix / "daily_financial_detail.csv"
            df = pd.read_csv(p)
            df["Controller"] = controller.title()
            df["Forecast"] = forecast.title()
            all_daily.append(df)
            for mode, g in df.groupby("Case"):
                monthly_rows.append({
                    "Controller": controller.title(),
                    "Forecast": forecast.title(),
                    "Mode": mode,
                    "Total Revenue": g["Total Revenue"].sum(),
                    "WM Revenue": g["WM Revenue"].sum(),
                    "TOU Cost": g["TOU Cost"].sum(),
                    "PD Cost": g["PD Cost"].sum(),
                    "NCD Cost": g["NCD Cost"].sum(),
                    "EV Revenue": g["EV Revenue"].sum(),
                })
    # The publication oracle is conditioned on the exact exogenous baseline
    # used by Rolling Perfect. This is the only saved oracle that can provide a
    # formal same-baseline dominance comparison with that MPC trajectory.
    oracle_path = (
        OUT_ROOT
        / "rolling_perfect"
        / "oracle"
        / "oracle_monthly_summary.csv"
    )
    oracle = pd.read_csv(oracle_path).iloc[0]
    if oracle.get("interval_capability_rule") != "sum_connected_session_interval_caps":
        raise RuntimeError(
            "The saved full-horizon oracle predates the interval-specific EV "
            "capability fix. Rerun `oracle benchmark` before rebuilding the report."
        )
    monthly_rows.append({
        "Controller": "Rolling-Perfect baseline oracle",
        "Forecast": "Full-horizon Perfect Oracle",
        "Mode": "Both",
        **{k: oracle[k] for k in ("Total Revenue", "WM Revenue", "TOU Cost", "PD Cost", "NCD Cost", "EV Revenue")},
    })
    daily = pd.concat(all_daily, ignore_index=True)
    monthly = pd.DataFrame(monthly_rows)
    monthly.to_csv(OUT_ROOT / "monthly_revenue_comparison.csv", index=False, float_format="%.2f")

    checks = []
    checks.append({"check": "All 8 MPC scenarios cover June 1-30", "pass": bool(all((g["Date"].nunique() == 30 and len(g) == 30) for _, g in daily.groupby(["Controller", "Forecast", "Case"]))), "max_error": 0.0, "tolerance": 0.0})
    # Hard A: daily EV revenue equality across all eight MPC combinations.
    piv = daily.pivot_table(index="Date", columns=["Controller", "Forecast", "Case"], values="EV Revenue", aggfunc="first")
    spread = piv.max(axis=1) - piv.min(axis=1)
    checks.append({"check": "Daily EV revenue equality across 8 MPC scenarios", "pass": bool((spread <= 0.01 + 1e-9).all()), "max_error": float(spread.max()), "tolerance": 0.01})
    # Executed EV energy from the eight implementation files.
    ev_energy = {}
    for controller in NOTEBOOKS:
        for forecast, prefix in FORECAST_PREFIX.items():
            for mode in ("full", "retail_only"):
                p = OUT_ROOT / controller / "Dispatch" / f"{prefix}_{mode}_implementation.csv"
                impl = pd.read_csv(p)
                impl["Date"] = pd.to_datetime(impl["Interval start"]).dt.date
                ev_energy[(controller, forecast, mode)] = impl.groupby("Date")["Base [kWh]"].sum()
    ev_energy_table = pd.DataFrame(ev_energy)
    energy_spread = ev_energy_table.max(axis=1) - ev_energy_table.min(axis=1)
    checks.append({"check": "Daily executed EV energy equality across 8 MPC scenarios", "pass": bool((energy_spread <= 1e-4).all()), "max_error": float(energy_spread.max()), "tolerance": 1e-4})
    # Check the rounded financial CSV identity exactly as required by the checklist.
    identity_error = (
        daily["WM Revenue"] + daily["TOU Cost"] + daily["PD Cost"]
        + daily["NCD Cost"] + daily["EV Revenue"] - daily["Total Revenue"]
    ).abs()
    checks.append({"check": "Rounded daily financial identity", "pass": bool((identity_error <= 0.03 + 1e-9).all()), "max_error": float(identity_error.max()), "tolerance": 0.03})
    # Hard D: Perfect retail-only daily equality between controllers.
    x = daily[(daily["Forecast"] == "Perfect") & (daily["Case"] == "Retail only")]
    piv = x.pivot_table(index="Date", columns="Controller", values="Total Revenue", aggfunc="first")
    err = (piv["Rolling"] - piv["Shrinking"]).abs()
    checks.append({"check": "Perfect retail-only daily controller equality", "pass": bool((err <= 0.01 + 1e-9).all()), "max_error": float(err.max()), "tolerance": 0.01})
    # Controller ordering is diagnostic only, not an acceptance gate.
    diagnostic_rows = []
    for forecast in ("Perfect", "Persistence"):
        for mode in ("Both", "Retail only"):
            vals = monthly[(monthly.Forecast == forecast) & (monthly.Mode == mode)].set_index("Controller")["Total Revenue"]
            delta = float(vals["Rolling"] - vals["Shrinking"])
            diagnostic_rows.append({
                "Forecast": forecast,
                "Mode": mode,
                "Rolling Total Revenue": float(vals["Rolling"]),
                "Shrinking Total Revenue": float(vals["Shrinking"]),
                "Rolling minus Shrinking": delta,
                "Acceptance rule": "Diagnostic only",
            })
    # Cross-baseline oracle/MPC gaps are descriptive only. A mathematical
    # dominance check requires the exact same exogenous baseline, initial states,
    # constraints, and accounting in both problems.
    benchmark_oracle = monthly[
        (monthly.Controller == "Rolling-Perfect baseline oracle")
        & (monthly.Forecast == "Full-horizon Perfect Oracle")
    ]["Total Revenue"].iloc[0]
    for controller in NOTEBOOKS:
        pers = monthly[(monthly.Controller == controller.title()) & (monthly.Forecast == "Persistence") & (monthly.Mode == "Both")]["Total Revenue"].iloc[0]
        diagnostic_rows.append({
            "Forecast": "Full-horizon Perfect Oracle vs Persistence",
            "Mode": "Both",
            "Rolling Total Revenue": float(benchmark_oracle),
            "Shrinking Total Revenue": float(pers),
            "Rolling minus Shrinking": float(benchmark_oracle - pers),
            "Acceptance rule": f"Descriptive only; baseline differs from {controller}",
        })
        matched = pd.read_csv(OUT_ROOT / controller / "matched_state" / "matched_state_daily_summary.csv")
        comp = pd.read_csv(OUT_ROOT / controller / "matched_state" / "matched_state_comparison.csv")
        checks.append({"check": f"{controller.title()} matched-state Perfect >= Persistence", "pass": bool(comp["Perfect better"].astype(bool).all()), "max_error": float(comp["Perfect minus Persistence"].min()), "tolerance": -0.01})
        checks.append({"check": f"{controller.title()} matched-state DA commitments identical", "pass": bool(matched["DA reference max error kW"].max() <= 1e-8), "max_error": float(matched["DA reference max error kW"].max()), "tolerance": 1e-8})
        ev_spread = matched.pivot(index="Date", columns="Forecast", values="EV Revenue").apply(lambda row: row.max() - row.min(), axis=1)
        checks.append({"check": f"{controller.title()} matched-state daily EV revenue equality", "pass": bool((ev_spread <= 0.01).all()), "max_error": float(ev_spread.max()), "tolerance": 0.01})
    oracle_meta = oracle
    checks.append({"check": "Benchmark oracle meter balance", "pass": bool(oracle_meta["meter_balance_max_error_kW"] <= 1e-3), "max_error": float(oracle_meta["meter_balance_max_error_kW"]), "tolerance": 1e-3})
    checks.append({"check": "Benchmark oracle terminal SOC", "pass": bool(abs(oracle_meta["terminal_soc"] - 0.5) <= 1e-4), "max_error": float(abs(oracle_meta["terminal_soc"] - 0.5)), "tolerance": 1e-4})
    checks.append({"check": "Benchmark oracle actual AS nonnegative", "pass": bool(oracle_meta["as_actual_min_kW"] >= -1e-6), "max_error": float(oracle_meta["as_actual_min_kW"]), "tolerance": -1e-6})
    checks.append({"check": "Benchmark oracle interval EV capability", "pass": bool(oracle_meta["ev_capability_max_violation_kW"] <= 1e-6), "max_error": float(oracle_meta["ev_capability_max_violation_kW"]), "tolerance": 1e-6})
    checks.append({"check": "Benchmark oracle actual upward capability", "pass": bool(oracle_meta["actual_up_capability_max_violation_kW"] <= 1e-6), "max_error": float(oracle_meta["actual_up_capability_max_violation_kW"]), "tolerance": 1e-6})
    checks.append({"check": "Benchmark oracle actual downward capability", "pass": bool(oracle_meta["actual_down_capability_max_violation_kW"] <= 1e-6), "max_error": float(oracle_meta["actual_down_capability_max_violation_kW"]), "tolerance": 1e-6})
    checks.append({"check": "Benchmark oracle MIP gap <= 1%", "pass": bool(oracle_meta["mip_gap"] <= 0.01 + 1e-12), "max_error": float(oracle_meta["mip_gap"]), "tolerance": 0.01})
    formal_rolling_perfect = float(
        monthly[
            (monthly.Controller == "Rolling")
            & (monthly.Forecast == "Perfect")
            & (monthly.Mode == "Both")
        ]["Total Revenue"].iloc[0]
    )
    checks.append({
        "check": "Same-baseline oracle incumbent >= Rolling Perfect",
        "pass": bool(float(oracle_meta["Total Revenue"]) >= formal_rolling_perfect - 0.03),
        "max_error": float(oracle_meta["Total Revenue"]) - formal_rolling_perfect,
        "tolerance": -0.03,
    })
    checks.append({
        "check": "Oracle certified bound >= Rolling Perfect",
        "pass": bool(float(oracle_meta["objective_best_bound"]) >= formal_rolling_perfect - 0.03),
        "max_error": float(oracle_meta["objective_best_bound"]) - formal_rolling_perfect,
        "tolerance": -0.03,
    })
    expected_baseline = _load_controller_baseline("rolling", "perfect", GRID)
    expected_baseline_hash = hashlib.sha256(
        np.ascontiguousarray(np.asarray(expected_baseline, dtype="<f8")).tobytes()
    ).hexdigest()
    checks.append({
        "check": "Oracle baseline hash equals Rolling Perfect baseline",
        "pass": bool(
            str(oracle_meta["baseline_sha256_float64"])
            == expected_baseline_hash
        ),
        "max_error": (
            0.0
            if str(oracle_meta["baseline_sha256_float64"])
            == expected_baseline_hash
            else 1.0
        ),
        "tolerance": 0.0,
    })
    check_df = pd.DataFrame(checks)
    check_df.to_csv(OUT_ROOT / "validation_checks.csv", index=False)
    diagnostic_df = pd.DataFrame(diagnostic_rows)
    diagnostic_df.to_csv(OUT_ROOT / "controller_diagnostics.csv", index=False)

    def md_table(df: pd.DataFrame, digits: int = 2) -> str:
        def fmt(x):
            if isinstance(x, (float, np.floating)):
                return f"{x:.{digits}f}"
            return str(x)
        headers = [str(c) for c in df.columns]
        rows = [[fmt(x) for x in row] for row in df.itertuples(index=False, name=None)]
        return "\n".join([
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
            *["| " + " | ".join(row) + " |" for row in rows],
        ])

    matched_all = []
    for controller in NOTEBOOKS:
        m = pd.read_csv(OUT_ROOT / controller / "matched_state" / "matched_state_comparison.csv")
        m.insert(0, "Controller", controller.title())
        matched_all.append(m)
    matched_table = pd.concat(matched_all, ignore_index=True)
    all_checks_pass = bool(check_df["pass"].astype(bool).all())
    acceptance_sentence = (
        "All current acceptance checks pass."
        if all_checks_pass
        else "One or more acceptance checks fail; these outputs are diagnostic "
             "and must not be used as paper results."
    )
    lines = [
        "# June 2025 independent validation results",
        "",
        "## Monthly revenue comparison",
        "",
        md_table(monthly, 2),
        "",
        "The 24-hour MPC rows are the isolated complete-June result snapshot generated after forecast-specific baseline routing was corrected. The publication oracle uses the same exogenous baseline path as Rolling Perfect and the full realized June EV/price data.",
        "",
        "The oracle status, incumbent objective, best bound, and certified MIP gap are recorded in `rolling_perfect/oracle/oracle_monthly_summary.csv`. A time-limited incumbent is described as a feasible near-optimal benchmark, never as an exact optimum.",
        "",
        "Important provenance note: the MPC runner reloads the forecast-specific pre-study baseline before each scenario. Perfect and Persistence then evolve different executed baseline and demand-threshold paths. The oracle is a formal same-baseline comparison with Rolling Perfect only. Its gap to Rolling Persistence is descriptive rather than a same-feasible-set dominance certificate.",
        "",
        "## Matched-state RT comparison",
        "",
        md_table(matched_table, 2),
        "",
        "Each pair uses SOC=0.5, NCD threshold=100 kW, PD threshold=80 kW, and byte-for-byte identical DA energy/AS commitments. Only the RT EV forecast changes.",
        "",
        "## Acceptance checks",
        "",
        md_table(check_df, 6),
        "",
        acceptance_sentence + " A reported financial-identity residual up to $0.03 is mathematically valid when five components and their total are independently rounded to cents.",
        "",
        "## Controller-ordering diagnostics (not acceptance checks)",
        "",
        md_table(diagnostic_df, 2),
        "",
        "Rolling-versus-Shrinking ordering is reported for interpretation only. A negative value does not indicate a model bug or invalidate the result.",
        "",
    ]
    (OUT_ROOT / "VALIDATION_REPORT.md").write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_mpc = sub.add_parser("mpc")
    p_mpc.add_argument("controller", choices=NOTEBOOKS)
    p_mpc.add_argument("--days", nargs="+", type=int, default=None)
    p_mpc.add_argument(
        "--modes",
        nargs="+",
        choices=["full", "retail_only"],
        default=None,
    )
    p_mpc.add_argument(
        "--forecasts",
        nargs="+",
        choices=["perfect", "persistence"],
        default=None,
    )
    p_mpc.add_argument(
        "--mip-gap",
        type=float,
        default=None,
        help=(
            "Override the source notebook MIP gap. The value is included in "
            "the isolated short-test directory name."
        ),
    )
    p_mpc.add_argument(
        "--formal-tag",
        default=None,
        help=(
            "Version label for a complete-June run. Required for complete "
            "June so historical formal results cannot be overwritten."
        ),
    )
    p_mpc.add_argument(
        "--include-daily-plot",
        action="store_true",
        help="Exercise the source notebook's daily 6-panel plotting and bound audit.",
    )
    p_oracle = sub.add_parser("oracle")
    p_oracle.add_argument(
        "controller",
        choices=[
            *NOTEBOOKS,
            "common",
            "benchmark",
            "rolling_perfect",
            "rolling_persistence",
        ],
    )
    p_oracle.add_argument("--start-date", default="2025-06-01")
    p_oracle.add_argument("--end-date", default="2025-07-01")
    p_oracle.add_argument("--mip-gap", type=float, default=1e-2)
    p_oracle.add_argument(
        "--time-limit",
        type=float,
        default=240.0,
        help="Seconds; use a negative value to disable the normal time limit.",
    )
    p_oracle.add_argument(
        "--baseline-source",
        choices=["auto", "formal", "short-mpc", "formal-run", "current-results"],
        default="auto",
        help=(
            "auto uses the matching isolated Rolling Perfect trace for one-day "
            "rolling_perfect tests and formal monthly output otherwise; "
            "current-results reads the current Results_Rolling Perfect trace."
        ),
    )
    p_oracle.add_argument(
        "--short-mpc-mip-gap",
        type=float,
        default=None,
        help="MIP-gap tag of the isolated MPC trace used as oracle baseline.",
    )
    p_oracle.add_argument(
        "--formal-tag",
        default=None,
        help="Version label used by a complete-June Rolling formal run.",
    )
    p_oracle.add_argument(
        "--direction-seed",
        default=None,
        help=(
            "Optional prior oracle_dispatch.csv used only to seed binary "
            "directions; continuous variables are re-optimized."
        ),
    )
    p_oracle.add_argument(
        "--mip-focus",
        type=int,
        choices=[0, 1, 2, 3],
        default=1,
        help="Gurobi MIPFocus; 3 prioritizes closing the certified bound.",
    )
    p_matched = sub.add_parser("matched")
    p_matched.add_argument("controller", choices=NOTEBOOKS)
    p_matched.add_argument("--dates", nargs="+", type=int, default=[3, 15, 27])
    p_matched.add_argument("--mip-gap", type=float, default=None)
    sub.add_parser(
        "select-stress-dates",
        help="Write the reproducible Gate D June stress-date screen.",
    )
    sub.add_parser(
        "gate-d-report",
        help="Aggregate selected-day solver, physics, and financial audits.",
    )
    p_gate_e = sub.add_parser(
        "gate-e-report",
        help="Audit one immutable complete-June Rolling/oracle snapshot.",
    )
    p_gate_e.add_argument(
        "--formal-tag",
        required=True,
        help="Version label of the complete-June formal run.",
    )
    p_plot = sub.add_parser("plot-daily")
    plot_dates = p_plot.add_mutually_exclusive_group(required=True)
    plot_dates.add_argument("--day", nargs="+")
    plot_dates.add_argument(
        "--all-days",
        action="store_true",
        help="Generate every date in the formal oracle daily financial file.",
    )
    p_plot.add_argument(
        "--source",
        choices=["short", "formal"],
        default="short",
    )
    p_plot.add_argument(
        "--oracle-controller",
        default="rolling_perfect",
        choices=["rolling_perfect", "rolling_persistence", "benchmark", "common"],
    )
    p_plot.add_argument(
        "--mip-gap",
        type=float,
        default=None,
        help="MIP gap tag of an isolated short MPC run.",
    )
    p_plot.add_argument(
        "--formal-tag",
        default=None,
        help="Version label for formal Rolling/oracle inputs and plot outputs.",
    )
    sub.add_parser("report")
    args = parser.parse_args()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    if args.command == "mpc":
        run_isolated_monthly_mpc(
            args.controller,
            days=args.days,
            modes=args.modes,
            forecasts=args.forecasts,
            mip_gap=args.mip_gap,
            formal_tag=args.formal_tag,
            include_daily_plot=args.include_daily_plot,
        )
    elif args.command == "oracle":
        run_monthly_oracle(
            args.controller,
            start_date=args.start_date,
            end_date=args.end_date,
            mip_gap=args.mip_gap,
            time_limit_s=None if args.time_limit < 0 else args.time_limit,
            baseline_source=args.baseline_source,
            short_mpc_mip_gap=args.short_mpc_mip_gap,
            formal_tag=args.formal_tag,
            direction_seed_path=args.direction_seed,
            mip_focus=args.mip_focus,
        )
    elif args.command == "matched":
        run_matched_state(args.controller, args.dates, args.mip_gap)
    elif args.command == "select-stress-dates":
        select_gate_d_stress_dates()
    elif args.command == "gate-d-report":
        build_gate_d_stress_report()
    elif args.command == "gate-e-report":
        for path in build_gate_e_report(args.formal_tag):
            print(path)
    elif args.command == "plot-daily":
        if args.all_days:
            if args.source != "formal":
                raise ValueError("--all-days requires --source formal")
            oracle_daily = (
                (
                    _formal_run_root(args.formal_tag)
                    if args.formal_tag is not None
                    else OUT_ROOT
                )
                / args.oracle_controller
                / "oracle"
                / "oracle_daily_financial.csv"
            )
            formal_days = (
                pd.to_datetime(pd.read_csv(oracle_daily)["Date"], errors="raise")
                .dt.strftime("%Y-%m-%d")
                .tolist()
            )
        else:
            formal_days = args.day
        for day in formal_days:
            for path in plot_daily_rolling_oracle_validation(
                day,
                oracle_controller=args.oracle_controller,
                source=args.source,
                mip_gap=args.mip_gap,
                formal_tag=args.formal_tag,
            ):
                print(path)
    elif args.command == "report":
        build_validation_report()


if __name__ == "__main__":
    main()
