"""Matched SEGAN controls; reads the main notebook without altering it.

From the project checkout, use the TotalEnergies2024 Python environment:
    python /path/to/ntpll_market_access.py batch /path/to/new-result-directory
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np
import pandas as pd

BOOK = Path("upscaledev_imp_rollingMPC.ipynb")
INPUTS = Path("Results_Rolling/Site_Cases_2025/segan_continuous_soc_six_sites_20261112/inputs")
FORECAST = "PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival"
HISTORY_INPUT = INPUTS / "baseline_dispatch/NTPLL" / f"2025_{FORECAST}_baseline.csv"
EV = INPUTS / "NTPLL_EV_2025_QC.csv"
METER = INPUTS / "NTPLL_BTM_2025_15min_QC.csv"
CASES = ["retail", "energy", "energy_as"]
DT = .25
AS = ["RU", "RD", "SP", "NSP"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(src, old, new):
    if src.count(old) != 1:
        raise ValueError(f"Source anchor not unique: {old!r}")
    return src.replace(old, new, 1)


def study_case(case, output, days, end):
    sys.path.insert(0, str(BOOK.resolve().parent))
    try:
        os.nice(10)
    except PermissionError:
        pass
    mode = "retail_only" if case == "retail" else "full"
    os.environ.update(SEGAN_SOC_BOUNDARY="continuous", SEGAN_STUDY_START="2025-03-01",
                      CANONICAL_EVALUATION_END=f"2025-03-{end:02d}", SEGAN_GAP_RETRY="0",
                      SEGAN_DEMAND_PLANNING="historical_tail", SEGAN_SOLVE_TIME_LIMIT_S="90",
                      CANONICAL_SOLVER_THREADS="2", RUN_CANONICAL_STUDY="0",
                      CANONICAL_RESULTS_ROOT=str(output),
                      SEGAN_WORKER_PROGRESS_FILE=str(output/"progress.json"))
    book = {c["id"]: "".join(c["source"]) for c in json.loads(BOOK.read_bytes())["cells"]
            if c["cell_type"] == "code" and "id" in c}
    ns = {"__name__": "__main__", "display": lambda *a, **kw: None}
    def cell(id):
        exec(compile(book[id], id, "exec"), ns)
    for id in ("2d0b8c3c", "d340deb2", "06840fdb"):
        cell(id)
    history = pd.read_csv(HISTORY_INPUT, parse_dates=["Interval start"])
    history = history.loc[history["Interval start"] < "2025-03-01"]
    assert pd.DatetimeIndex(history["Interval start"]).equals(pd.date_range("2025-02-01", periods=28*96, freq="15min"))
    history_path = output/"preperiod_history.csv"
    history.to_csv(history_path, index=False)
    ns.update(EV_DATA_FILE=EV, BASELINE_DISPATCH_FILE=history_path, VERSION_DIR=str(output),
              PASSIVE_DER_ENABLED=True, BTM_BUILDING_FILE=METER, BTM_PV_FILE=METER,
              AS_ACTIVATION_MODE="caiso_regulation", Fc_SessionkWh="PersistenceSessionkWh",
              Fc_NumbEV="PersistenceNumbEV", Fc_AtArrival="PerfectatArrival",
              RUN_MONTHS_CONFIG=[3], RUN_DAYS_CONFIG=list(range(1, days+1)),
              RUN_MODES=[mode], WM_Mode=mode, Enable_WM=mode=="full",
              CLEAR_IMPLEMENTATION_AT_RUN_START=True, SERVICE_LEVEL_MIN=1.,
              _SEGAN_INITIAL_SOC=.5, SENSITIVITY_ENABLED=False, PLOT_DAILY_6PANEL_DATES=[],
              ANALYSIS_DAYS_CONFIG=[f"202503{d:02d}" for d in range(1, days+1)],
              SAVE_FINAL_FINANCIAL_FIGURES=False)
    cell("abaef745")
    source = book["4c6f4da9"]
    source = replace(source, "RUN_MAIN_LOOP_DIRECT = False", "RUN_MAIN_LOOP_DIRECT = True")
    source = replace(source, "(WM_Mode == 'retail_only') or is_last_run_day or monthly_probe_end",
                     "is_last_run_day or monthly_probe_end")
    # Apply the identical physical BESS direction/rating in *all* arms.
    # The legacy retail branch did not include the full-market direction binaries.
    direction = "b_ch_BESS + b_dch_BESS <= 1, p_ch_BESS <= P_BESS_max * b_ch_BESS, p_dch_BESS <= P_BESS_max * b_dch_BESS,"
    da_anchor = "            constraints_WM = [\n                p_DA == 0, p_RT == 0,"
    rt_anchor = "            else:\n                constraints += [\n                    p_DA == 0,\n                    p_RT == 0,"
    source = replace(source, da_anchor, da_anchor + "\n                " + direction)
    source = replace(source, rt_anchor, rt_anchor + "\n                    " + direction)
    # When AS are disabled, retain the energy market and zero all AS decisions
    # in both stages; the physical and financial AS contributions are then zero.
    if case == "energy":
        zero = ", ".join(f"c_{p}_{stage} == 0" for p in AS for stage in ("DA", "RT"))
        a = "        # NOTE: Combine all constraints\n"
        b = "            penalty_BESS = cp.Constant(0.0)\n            objective = cp.Minimize(Cost_Opt + penalty_WM + penalty_BESS)"
        source = replace(source, a, f"        constraints_WM += [{zero}]\n" + a)
        source = replace(source, b, f"            constraints += [{zero}]\n" + b)
    manifest = dict(case=case, mode=mode, site="NTPLL", forecast="Persistence", days=days,
                    terminal_date=f"2025-03-{end:02d}", initial_SOC=.5, terminal_target=.5,
                    demand_planning="historical_tail", initial_PD_kW=0, initial_NCD_kW=0,
                    initial_history_sha256=sha(history_path), book_sha256=sha(BOOK),
                    input_ev_sha256=sha(EV), input_meter_sha256=sha(METER),
                    core_executed_sha256=hashlib.sha256(source.encode()).hexdigest(),
                    relative_gap=0.01, retry_allowed=False)
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    exec(compile(source, "matched_NTPLL_rolling_model", "exec"), ns)
    cell("d813f102")
    cell("ee2bfddf")
    audit_case(case, output, days, end, ns)


def audit_case(case, output, days, end, ns):
    mode = "retail_only" if case == "retail" else "full"
    prefix = f"2025_{FORECAST}"
    key = f"{prefix}_{mode}"
    diag = output/"Diagnostics"/f"{FORECAST}_{mode}"
    readlog = lambda file: [json.loads(l) for l in (diag/file).read_text().splitlines()]
    clock = pd.date_range("2025-03-01", periods=days*96, freq="15min", name="Interval start")
    traces = pd.concat([pd.read_csv(p,parse_dates=["Interval start"]) for p in
                        sorted((output/"Validation_Traces"/key).glob("*.csv"))]).set_index("Interval start")
    imp = pd.read_csv(output/"Dispatch"/f"{key}_implementation.csv", parse_dates=["Interval start"]).set_index("Interval start")
    assert traces.index.equals(clock) and imp.index.equals(clock)
    close = lambda a,b,tol=1e-5: np.testing.assert_allclose(a,b,atol=tol,rtol=0)
    def read_wm(day):
        path = output/"Plots/Solver_RT_Choices"/key/f"{day:%Y%m%d}"/f"RT_WM_profit_breakdown_{mode}.csv"
        return pd.read_csv(path, parse_dates=["Interval start"]).set_index("Interval start")
    wm = pd.concat([read_wm(d) for d in clock.normalize().unique()])
    assert wm.index.equals(clock)
    gi, ev, bess, soc = [traces[k].to_numpy() for k in ["p_GI_kW", "p_EV_kW", "p_BESS_kW","SOC"]]
    close(gi, traces.p_load_kW-traces.p_PV_kW+ev+bess)
    close(imp["Base [kWh]"], DT*ev)
    close(imp["Base_meter [kWh]"], DT*gi)
    soc_change = DT/332.*(np.maximum(bess,0.)*np.sqrt(.90)+np.minimum(bess,0.)/np.sqrt(.90))
    close(soc - np.r_[.5,soc[:-1]], soc_change, 2e-6)
    assert soc.min()>=.05-1e-6 and soc.max()<=.95+1e-6
    assert max(abs(bess))<=250+1e-5 and np.abs(bess).reshape(-1,96).sum(axis=1).max()*DT<=597.6+1e-4
    if days == end:
        close(soc[-1],.5,1e-6)
    close(traces.passive_WM_position_kW,0.,1e-9)
    close(traces.p_DA_kW+traces.p_RT_deviation_kW,traces.p_actual_kW)
    for p in AS:
        close(traces[f"c_{p}_DA_kW"]+traces[f"c_{p}_RT_kW"],traces[f"c_{p}_actual_kW"])
        assert traces[f"c_{p}_actual_kW"].min()>=-1e-5
    if case != "energy_as":
        close(traces.filter(regex="^c_").to_numpy(),0.)
    if case == "retail":
        close(traces[["p_DA_kW","p_RT_deviation_kW","p_actual_kW"]],0.)
        close(wm.profit_sum_all_products,0.)
    assert traces.filter(regex="capability_slack").min().min()>=-1e-5
    close(np.ptp(traces[["p_DA_kW", *[f"c_{p}_DA_kW" for p in AS]]].to_numpy().reshape(-1,4,5),axis=1),0.)
    certs = readlog("solver_certificates.jsonl")
    assert len(certs)==days*97 and all(c["accepted"] and ns["_segan_certificate_is_acceptable"](c) for c in certs)
    assert len({(c["stage"], c["date"], c["interval"]) for c in certs})==days*97
    assert sum(c["stage"]=="DA" for c in certs)==days
    refs = readlog("peak_reference.jsonl")
    assert len(refs)==days*97 and all(r["stage"] in {"DA","RT"} for r in refs)
    assert all(pd.Timestamp(b["end_exclusive"])<=pd.Timestamp(r["cutoff"]) for r in refs for b in r["blocks"])
    vsteps = readlog("actual_vehicle_ledger.jsonl")
    assert len(vsteps)==len(clock)
    ves = {(s["day"],v["EV"]):v for s in vsteps for v in s["vehicles"]}
    service = max(abs(v["request_kWh"]-v["cumulative_kWh"]) for v in ves.values())
    assert service<=1.01e-4
    ncd = np.maximum.accumulate(np.maximum(gi,0))
    on_peak = ns["get_sdge_on_peak_mask"](clock)
    pd_peak = np.maximum.accumulate(np.maximum(gi*on_peak,0))
    close(ncd,imp.NCD_Base,2e-5)
    close(pd_peak,imp.PD_Base,2e-5)
    for r in refs:
        i=clock.get_loc(pd.Timestamp(r["start"]))
        close([r["actual_NCD_kW"],r["actual_PD_kW"]],
              [ncd[i-1],pd_peak[i-1]] if i else [0,0],2e-5)
        assert abs(sum(r["weights"])-1)<1e-10 and not r["actual_bill_uses_reference"]
    ecols = [f"c_{p}_{s}_energy" for p in AS for s in ("DA","RT")]
    ccols = [f"c_{p}_{s}_capacity" for p in AS for s in ("DA","RT")]
    frame = pd.DataFrame({
        "scheduled_WM_energy":wm.p_DA_profit+wm.p_RT_profit, "AS_deployment":wm[ecols].sum(axis=1),
        "AS_capacity":wm[ccols].sum(axis=1), "WM Revenue":wm.profit_sum_all_products,
        "TOU Cost":-imp["Base_meter [kWh]"]*traces["TOU_$/kWh"],
        "PD Cost":-np.diff(np.r_[0,pd_peak])*.63, "NCD Cost":-np.diff(np.r_[0,ncd])*15.38,
        "EV Revenue":DT*ev*.4, "EV kWh":DT*ev,
        "charge_kWh":DT*np.maximum(bess,0.), "discharge_kWh":-DT*np.minimum(bess,0.),
    },index=clock)
    close(frame["WM Revenue"],frame[["scheduled_WM_energy","AS_deployment","AS_capacity"]].sum(axis=1),7e-5)
    frame["Total Revenue"] = frame[["WM Revenue","TOU Cost","PD Cost","NCD Cost","EV Revenue"]].sum(axis=1)
    daily = frame.resample("D").sum()
    published = pd.read_csv(output/"Plots/Cost"/prefix/"daily_financial_detail.csv",parse_dates=["Date"]).set_index("Date")
    assert published.index.equals(daily.index)
    for c in ["WM Revenue","TOU Cost","PD Cost","NCD Cost","EV Revenue","Total Revenue"]:
        close(daily[c],published[c],.0053)
    frame["NCD_peak_kW"],frame["PD_peak_kW"] = ncd,pd_peak
    frame.to_csv(output/"interval_accounts.csv")
    daily.to_csv(output/"daily_accounts.csv")
    cert = dict(status="PASS", case=case, solves=len(certs), max_gap=max(c["MIPGap"] for c in certs),
                end_SOC=soc[-1], NCD_kW=ncd[-1], PD_kW=pd_peak[-1], max_EV_service_residual_kWh=service,
                max_meter_error_kW=traces.meter_balance_residual_kW.abs().max(), **frame[daily.columns].sum().to_dict())
    (output/"PASS.json").write_text(json.dumps(cert, indent=2)+"\n")


def machine_ok():
    objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
    ctypes.CDLL("/System/Library/Frameworks/Foundation.framework/Foundation")
    cls, sel, msg = objc.objc_getClass, objc.sel_registerName, objc.objc_msgSend
    cls.argtypes = sel.argtypes = [ctypes.c_char_p]
    cls.restype = sel.restype = ctypes.c_void_p
    msg.argtypes = [ctypes.c_void_p,ctypes.c_void_p]
    msg.restype = ctypes.c_void_p
    obj = msg(cls(b"NSProcessInfo"),sel(b"processInfo"))
    msg.restype = ctypes.c_long
    therm=msg(obj,sel(b"thermalState"))
    if therm>=2 or "'AC Power'" not in subprocess.check_output(["/usr/bin/pmset","-g","batt"],text=True):
        raise RuntimeError(f"Temperature/AC safety stop, thermal state {therm}")


def batch(root):
    root.mkdir()
    for phase, days, end in [("smoke", 1, 31), ("march", 31, 31)]:
        pending = list(CASES)
        running = {}
        try:
            while pending or running:
                machine_ok()
                while pending and len(running)<2:
                    case=pending.pop(0)
                    out=root/phase/case
                    out.mkdir(parents=True)
                    env=dict(os.environ, MPLBACKEND="Agg", MPLCONFIGDIR=os.environ.get("MPLCONFIGDIR",str(root/"mpl")),
                             OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
                    with (out/"execution.log").open("x") as log:
                        proc=subprocess.Popen([sys.executable,"-u",__file__,case,str(out),str(days),str(end)],
                                              env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    running[case]=(proc,out,time.time())
                    print(f"{phase}/{case}: RUNNING",flush=True)
                for case,(proc,out,start) in list(running.items()):
                    rc=proc.poll()
                    if rc is not None:
                        if rc or not (out/"PASS.json").is_file():
                            raise RuntimeError(f"{phase}/{case} failed acceptance: {out/'execution.log'} (exit {rc})")
                        print(f"{phase}/{case}: PASS",flush=True)
                        del running[case]
                    else:
                        progress=out/"progress.json"
                        if time.time()-(progress.stat().st_mtime if progress.exists() else start)>145:
                            raise TimeoutError(out)
                if running:
                    time.sleep(3)
        finally:
            for proc,_,_ in running.values():
                if proc.poll() is None:
                    os.killpg(proc.pid,signal.SIGTERM)
        d=[pd.read_csv(root/phase/c/"daily_accounts.csv")["EV kWh"].to_numpy() for c in CASES]
        assert np.ptp(d,axis=0).max()<=1e-4
        manifests=[json.loads((root/phase/c/"manifest.json").read_text()) for c in CASES]
        for fixed in set(manifests[0])-{"case","mode","core_executed_sha256"}:
            assert len({m[fixed] for m in manifests})==1, fixed
        pd.DataFrame([json.loads((root/phase/c/"PASS.json").read_text()) for c in CASES]).to_csv(root/f"{phase}_comparison.csv",index=False)


if __name__ == "__main__":
    action, path, *rest=sys.argv[1:]
    if action=="batch":
        batch(Path(path).resolve())
    else:
        study_case(action,Path(path).resolve(),*map(int,rest))
