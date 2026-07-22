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

## Matched-state RT comparison retained from the independent test

| Controller | Date | Perfect Total Revenue | Persistence Total Revenue | Perfect minus Persistence |
| --- | --- | ---: | ---: | ---: |
| Shrinking | 2025-06-03 | -1482.91 | -3364.96 | 1882.04 |
| Shrinking | 2025-06-15 | 443.84 | 442.13 | 1.71 |
| Shrinking | 2025-06-27 | -1269.93 | -1746.56 | 476.63 |
| Rolling | 2025-06-03 | -1482.93 | -3713.98 | 2231.04 |
| Rolling | 2025-06-15 | 443.76 | 438.00 | 5.76 |
| Rolling | 2025-06-27 | -1269.41 | -2484.43 | 1215.03 |

Each matched-state pair fixes the same initial SOC, demand thresholds, and DA energy/AS commitments; only the RT EV forecast changes.
