# June 2025 forecast-specific baseline validation

## Corrected monthly revenue comparison

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
| Shrinking Perfect benchmark | Full-horizon Perfect | Both | 16202.73 | 8202.82 | -10405.50 | -114.85 | -4873.66 | 23393.92 |

The two MPC source notebooks were rerun for June 1--30 after fixing the runner so each forecast scenario reloads its corresponding baseline history. Shrinking and Rolling share the forecast-specific pre-June history saved by the baseline notebook, then update separate implementation histories during June.

The full-horizon benchmark uses the corrected executed June baseline path from Shrinking + Perfect/full as the requested common exogenous baseline. It stopped at the study time limit with a complete feasible dispatch: objective $16202.73, certified upper bound $16622.16, and MIP gap 2.5886%. It is therefore a certified near-optimal baseline-conditioned benchmark, not an exact optimum.

## Full-market benchmark gap

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
| Benchmark meter balance | PASS | 0.00 kW |
| Benchmark terminal SOC | PASS | 0.5000 |
| Benchmark actual AS capacity nonnegative | PASS | minimum 0.00 kW |
| Benchmark certified MIP gap <= 3% | PASS | 2.5886% |

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
