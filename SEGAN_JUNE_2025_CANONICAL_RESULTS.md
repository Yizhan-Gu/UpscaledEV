# Canonical June 2025 site-study snapshot

This file records the accepted local snapshot produced by
`upscaledev_imp_rollingMPC.ipynb` on 2026-08-23. Large CSV/PNG outputs remain
excluded from Git and are stored locally under
`Results_Rolling/Site_Cases_2025/`.

## Configuration

- Controller: Rolling 24-hour MPC
- Dates: 2025-06-01 through 2025-06-30
- Sites: NTPLL and Center Hall
- Resource case: `FULL_BTM`
- EV forecast updaters: Persistence and Perfect
- BESS: 250 kW / 332 kWh
- Gurobi target MIP gap: 1%
- Solver threads: 2
- Building/PV scope: passive signed-PCC retail settlement only; no wholesale
  energy or ancillary-service offers from these resources
- Model-source SHA-256:
  `55ba3a80a5ebc59e3a27cf555e69c5de81f5804a364a906ac3fba5b167b61e1d`

## June financial comparison (US dollars)

| Site | Forecast | Total | WM | TOU | PD | NCD | EV driver revenue |
|---|---:|---:|---:|---:|---:|---:|---:|
| NTPLL | Persistence | -204,939.73 | 4,219.02 | -188,775.20 | -3,622.82 | -18,667.00 | 1,906.31 |
| NTPLL | Perfect | -204,564.70 | 4,267.70 | -188,766.89 | -3,617.70 | -18,354.13 | 1,906.31 |
| Center Hall | Persistence | -5,404.66 | 4,715.89 | -10,131.78 | -344.46 | -2,289.00 | 2,644.75 |
| Center Hall | Perfect | -5,929.79 | 4,486.60 | -11,073.97 | -305.45 | -1,681.77 | 2,644.75 |

Perfect is not required to dominate Persistence for a finite-horizon MPC path;
the complete interpretation rule is maintained in
`MPC_RESULT_VALIDATION_CHECKLIST.md`.

## Validation gate

All four site/forecast cases passed:

- 2,880/2,880 executed RT steps reached `optimal` status per case;
- zero time-limit events;
- maximum PCC balance residual below `8.6e-7 kW`;
- passive-resource wholesale position exactly zero;
- actual RU/RD/SP/NSP capacity nonnegative within numerical tolerance;
- BESS SOC remained within `[0.05, 0.95]`;
- no numeric NaN values in implementation outputs;
- maximum reported financial-identity residual: USD 0.01;
- net-meter reconstruction residual: approximately `1.0e-6 kW`;
- forecast-paired EV energy is equal within `2e-7 kWh` at each site.

The machine-readable tables are:

- `Results_Rolling/Site_Cases_2025/tables/june_Both_FULL_BTM_Both_financial_comparison.csv`
- `Results_Rolling/Site_Cases_2025/tables/june_Both_FULL_BTM_Both_validation_summary.csv`
- `Results_Rolling/Site_Cases_2025/june_Both_FULL_BTM_Both_manifest.json`
