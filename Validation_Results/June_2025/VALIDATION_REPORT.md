# June 2025 forecast-specific baseline validation

> **Publication status (2026-07-25): the saved full-June oracle values below
> are superseded and must not be cited.** The earlier oracle repeated a
> daily vehicle-count capability across every 15-minute interval instead of
> using interval-specific connected-EV capability. The independent MPC runner
> also had a notebook-cell selection error that has now been corrected. The
> eight historical MPC rows and matched-state results are retained for
> provenance, but the formal Rolling monthly experiment and full-June oracle
> must be regenerated before manuscript use.

## Corrected short regression after the audit

The corrected 2025-06-01 test uses interval-specific EV capability and a true
96-step executed trace.

| Scenario | Net value (USD) | EV energy (kWh) | Terminal SOC | Max meter error (kW) | Max capability violation (kW) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rolling 24 h Persistence | 89.16 | 21.663000 | 0.5000 | 9.87e-13 | 5.68e-14 |
| Rolling 24 h Perfect | 106.34 | 21.663000 | 0.5000 | 8.88e-16 | 6.25e-13 |
| Full-horizon Perfect oracle | 108.651719 | 21.663000 | 0.5000 | 1.00e-08 | 0.00 |

The oracle is formally comparable to Rolling Perfect on this day: their
baseline differs by no more than 4.0e-09 kW, all price inputs match within
3.33e-09, and the oracle achieved a 0.0090% MIP gap. It exceeds Rolling Perfect
by USD 2.311719. Persistence uses a different forecast-driven baseline (maximum
difference 11.319752 kW), so the oracle-versus-Persistence value difference is
descriptive rather than a same-feasible-set dominance test.

Evidence:

- `short_tests/rolling/daily_graphs/2025-06-01/`
- `short_tests/rolling/mpc/days_01-01_full_perfect-persistence/`
- `short_tests/rolling_perfect/oracle/2025-06-01_to_2025-06-01/`

## Historical monthly revenue comparison

| Controller | Forecast | Mode | Total Revenue | WM Revenue | TOU Cost | PD Cost | NCD Cost | EV Revenue |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Shrinking | Perfect | Both | 13185.49 | 6945.11 | -12415.06 | -310.73 | -4427.74 | 23393.92 |
| Shrinking | Perfect | Retail only | 6240.92 | 0.00 | -12414.51 | -310.73 | -4427.74 | 23393.92 |
| Shrinking | Persistence | Both | 13712.13 | 7134.06 | -11511.11 | -518.13 | -4786.62 | 23393.92 |
| Shrinking | Persistence | Retail only | 5342.25 | 0.00 | -11625.73 | -492.94 | -5932.99 | 23393.92 |
| Rolling | Perfect | Both | 13335.60 | 6949.95 | -12301.27 | -279.26 | -4427.75 | 23393.92 |
| Rolling | Perfect | Retail only | 6240.92 | 0.00 | -12414.51 | -310.73 | -4427.74 | 23393.92 |
| Rolling | Persistence | Both | 13404.15 | 7188.54 | -11338.51 | -530.88 | -5308.89 | 23393.92 |
| Rolling | Persistence | Retail only | 6549.50 | 0.00 | -11631.63 | -275.30 | -4937.48 | 23393.92 |
| SUPERSEDED legacy benchmark | Full-horizon Perfect | Both | 16202.73 | 8202.82 | -10405.50 | -114.85 | -4873.66 | 23393.92 |

The two MPC source notebooks were rerun for June 1--30 after fixing the runner so each forecast scenario reloads its corresponding baseline history. Shrinking and Rolling share the forecast-specific pre-June history saved by the baseline notebook, then update separate implementation histories during June.

The legacy full-horizon benchmark stopped at the study time limit with a
complete feasible dispatch, objective USD 16202.73, certified upper bound USD
16622.16, and MIP gap 2.5886%. It predates the interval-specific EV-capability
fix and is retained only to document provenance. It is not a valid quantitative
benchmark for the current formulation.

## Superseded legacy benchmark gaps (not validation evidence)

| MPC case | MPC revenue | Benchmark minus MPC |
| --- | ---: | ---: |
| Shrinking Perfect | 13185.49 | 3017.24 |
| Shrinking Persistence | 13712.13 | 2490.60 |
| Rolling Perfect | 13335.60 | 2867.13 |
| Rolling Persistence | 13404.15 | 2798.58 |

## Validation checks

| Check | Result | Maximum error / detail |
| --- | --- | ---: |
| Eight MPC scenarios contain 2880 intervals and 30 dates | PASS | 0 missing intervals |
| Duplicate timestamps in all implementation files | PASS | 0 |
| Numeric missing values in all implementation files | PASS | 0 |
| Forecast-specific baseline routing, one-day regression | PASS | 7.11e-15 kWh |
| RT TimeLimit not triggered in all eight monthly scenarios | PASS | 8/8 scenario audits passed |
| Daily EV revenue equality across eight scenarios | PASS | $0.00 |
| Daily executed EV energy equality across eight scenarios | PASS | 8.19e-12 kWh |
| Perfect retail-only daily equality across controllers | PASS | $0.00 |
| Rounded daily financial identity | PASS | $0.01 |
| Legacy benchmark meter balance | SUPERSEDED | interval-capability formulation changed |
| Legacy benchmark terminal SOC | SUPERSEDED | interval-capability formulation changed |
| Legacy benchmark actual AS capacity nonnegative | SUPERSEDED | interval-capability formulation changed |
| Legacy benchmark certified MIP gap <= 3% | SUPERSEDED | final target is <= 1% |

Rolling-versus-Shrinking and Perfect-versus-Persistence ordering remain diagnostic rather than acceptance rules for finite-horizon MPC. In particular, a 24-hour receding Perfect forecast is not the same mathematical object as the full-horizon benchmark.

## Corrected complete-June matched-state RT comparison

The earlier 30-day matched-state CSVs were superseded. Although the old runner
loaded the same Perfect-history baseline file, the notebook still selected the
current-day RT baseline for Perfect and the previous comparable-day RT baseline
for Persistence. The old experiment therefore changed two inputs and cannot be
used as a forecast-only correctness test.

The validation runner now copies the Perfect RT baseline vector into the
Persistence run, as well as fixing initial SOC (0.5), NCD threshold (100 kW), PD
threshold (80 kW), realized EV sessions, and byte-identical DA energy/AS
commitments.

The corrected complete-June 1%-gap results are:

| Controller | Perfect total revenue | Persistence total revenue | Perfect minus Persistence | Direct-pass days |
| --- | ---: | ---: | ---: | ---: |
| Shrinking | -30904.31 | -43654.07 | 12749.77 | 28 / 30 |
| Rolling | -30901.60 | -61223.50 | 30321.90 | 29 / 30 |

All 11,520 formal RT solves are `optimal`. TimeLimit events, RT-baseline error,
DA-reference error, and meter-balance error are all zero. Daily EV revenue is
identical, maximum EV-energy spread is approximately 1.1e-8 kWh, and every
terminal SOC is 0.5.

The three 1%-gap exceptions were re-solved with `MIPGap=0`:

| Controller | Date | 1% Perfect minus Persistence | Exact Perfect minus Persistence |
| --- | --- | ---: | ---: |
| Shrinking | 2025-06-14 | -0.331138 | 0.803790 |
| Shrinking | 2025-06-29 | -1.133547 | 0.703287 |
| Rolling | 2025-06-29 | -0.480312 | 1.002149 |

All exception dates therefore pass after exact recheck. Exact Perfect values
match between Shrinking and Rolling on the audited dates. The USD 2.70
difference between their formal 1%-gap monthly Perfect sums is attributable to
different near-optimal incumbents rather than different Perfect formulations.

Saved evidence:

- `Validation_Results/June_2025/shrinking/matched_state/`
- `Validation_Results/June_2025/rolling/matched_state/`
- `Validation_Results/June_2025/common/matched_state/matched_state_june_comparison.csv`
- `Validation_Results/June_2025/common/matched_state/matched_state_exact_gap_audit.csv`

## Gate D selected-day Rolling stress tests

The data-driven screen selected June 1, 3, 5, 12, 13, and 29 after removing
duplicate criteria. These dates cover minimum connected-EV capability, maximum
DA/RT energy-price spread, maximum AS price, maximum realized EV energy,
maximum Persistence session-energy error, maximum PD-window EV energy, and the
historically closest/reversed matched-state ordering.

All six 24-hour Rolling Perfect/Persistence pairs used `MIPGap=1%`. Across
1,164 DA/RT solves:

- every CVXPY status was `optimal`;
- no TimeLimit or emergency-watchdog event occurred;
- maximum achieved MIP gap was 0.999897%;
- the slowest individual solve took 12.2863 seconds;
- daily EV revenue and executed EV energy were identical between forecasts;
- terminal BESS SOC was 0.5 in every case;
- meter balance, actual-position identity, actual AS nonnegativity, and
  up/down capability checks passed.

An initial validation-tool error was found and corrected: one-day benchmarks
after June 1 had read the old formal monthly Rolling baseline instead of the
baseline used by the isolated Perfect trace. The maximum mismatch reached
44.62 kW. Short benchmarks now load the exact trace `baseline_kW` vector and
write to a separate `baseline-short-mpc` directory. The final cross-scenario
baseline error is no more than \(5\times10^{-9}\) kW.

The third short-test scenario is a standalone one-day simultaneous Perfect
benchmark. It is not the full billing-period oracle and therefore is not used
to assert billing-period dominance. With the accepted 1% MIP tolerance, both
its incumbent and certified best bound are reported.

Saved evidence:

- `Validation_Results/June_2025/short_tests/gate_d/GATE_D_STRESS_TEST_REPORT.md`
- `Validation_Results/June_2025/short_tests/gate_d/gate_d_stress_test_summary.csv`
- `Validation_Results/June_2025/short_tests/rolling/daily_graphs/`

## Gate E formal June Rolling validation

Gate E passes under immutable formal tag `gate_e_20260726_c8250f11`.

| Scenario | Total Revenue | WM Revenue | TOU Cost | PD Cost | NCD Cost | EV Revenue |
|---|---:|---:|---:|---:|---:|---:|
| Rolling 24 h Perfect | 10733.15 | 4347.03 | -12300.80 | -279.25 | -4427.75 | 23393.92 |
| Rolling 24 h Persistence | 10485.28 | 4421.87 | -11092.27 | -467.84 | -5770.41 | 23393.92 |
| Full billing-period Perfect oracle | 12565.15 | 4564.69 | -10404.95 | -114.85 | -4873.66 | 23393.92 |

All 5,820 Rolling DA/RT solves are accepted at the configured 1% gap, with no
TimeLimit event. The oracle terminated normally at 0.8571% gap and exceeds the
same-baseline Rolling 24 h Perfect result by USD 1,832.00. All 19 formal
solver, trace, physical, settlement, EV-service, financial, baseline, terminal
state, and figure-completeness checks pass.

Each of the 30 dates has a three-column validation figure comparing Rolling
Persistence, Rolling 24 h Perfect, and the full billing-period Perfect oracle,
plus physical and cross-scenario audit CSVs. Formal evidence is saved under:

- `Validation_Results/June_2025/formal_runs/gate_e_20260726_c8250f11/GATE_E_VALIDATION_REPORT.md`
- `Validation_Results/June_2025/formal_runs/gate_e_20260726_c8250f11/gate_e_validation_checks.csv`
- `Validation_Results/June_2025/formal_runs/gate_e_20260726_c8250f11/rolling/daily_graphs/`

The archived 900-second oracle attempt is retained because it found a higher
feasible incumbent (USD 12,603.64) but did not pass the 1% certificate
(1.2006% gap). It is not combined with the accepted run's solver bound.
