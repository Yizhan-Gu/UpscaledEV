# Rolling MPC Implementation Notes for UPSCALeDEV

## 1. Overview

The implementation simulates real-time EV charging dispatch under a rolling model predictive control (MPC) framework. The original implementation used a shrinking-horizon MPC, where at each time step the optimizer only considered the remaining intervals of the current day. The new implementation keeps a fixed 96-step horizon at every real-time decision point, corresponding to 24 hours with 15-minute resolution.

The main purpose of the rolling MPC implementation is to support dynamic forecast updates while preserving strict real-time execution consistency. At every interval, the model updates the EV information available at that time, solves a forward-looking optimization problem, executes only the first control action, and then rolls forward to the next interval.

The implementation supports two market-operation modes:

- `full`: retail tariff cost plus wholesale market participation.
- `retail_only`: retail tariff cost only, with wholesale market variables disabled.

## 2. Time Resolution and Horizon

The dispatch interval is 15 minutes:

```text
dt = 15 minutes = 0.25 hours
```

Each day contains:

```text
96 intervals
```

At real-time step `k`, the optimizer receives a fixed-length horizon:

```text
H = 96
```

This differs from the original shrinking-horizon implementation, where:

```text
H = 96 - k
```

The fixed-horizon design allows the optimizer to maintain a full 24-hour look-ahead window at every real-time decision step. Since the current day only has `96 - k` intervals remaining, the horizon extends beyond midnight. The post-midnight portion is filled using a persistence-style forecast based on the current day's already executed EV load.

## 3. Daily Data Structure

For each simulated day, the code builds real and forecast EV tables:

- EV arrival tables
- EV availability matrices
- EV session energy tables
- EV charging upper-bound matrices
- EV service-level tables
- Baseline and event-hour profiles

The key EV matrices are:

```text
IntervalkWh_max_real      real per-interval charging availability
IntervalkWh_max_fc_fix    persistence/forecast per-interval charging availability
SessionkWh_table_real     true EV session energy
SessionkWh_table_fc_fix   forecast EV session energy
SessionkWh_nEta           remaining required EV energy after service-level adjustment
Dispatch                  actually executed EV charging energy
```

The EV fleet is stored by type:

```text
j = 0: all EVs
j = 1: Tesla EVs
j = 2: non-Tesla EVs
```

The implementation runs two service cases:

```text
Base   full service requirement
Case1  reduced service requirement using eta
```

## 4. Dynamic Forecast Update

At the beginning of day 0, the persistence forecast is initialized using the previous day's 24-hour data. During real-time operation, the forecast is dynamically updated as real EV arrivals are observed.

At real-time step `k`, the forecast horizon passed to the optimizer is conceptually:

```text
[1 : k]       real day-0 arrival and availability data already observed
[k+1 : 96]    persistence forecast from day -1
[97 : k+96]   day-0 already executed EV load used as persistence tail
```

Previously, the final segment `[97 : k+96]` was padded with zeros. This created an unrealistic rolling forecast tail. The current implementation replaces that zero padding with the realized EV dispatch load from the beginning of day 0 up to the current step.

Because the optimizer uses a per-EV availability matrix, the persistence tail is constructed at the EV-column level rather than as an aggregate load. Specifically, the executed dispatch matrices for Tesla and non-Tesla EVs are concatenated:

```text
tail_ub_realized = concat(Dispatch[Tesla], Dispatch[NonTesla])[:k]
```

Then, when the 96-step rolling horizon extends past the current day, the missing rows are filled using this already executed day-0 EV load.

## 5. Real-Time Rolling MPC Loop

At each 15-minute real-time step `k`, the implementation performs the following sequence.

First, it identifies EVs that arrived during the previous interval. For newly arrived EVs, the real-time tables are updated using actual arrival and session information. This includes:

- renaming forecast EV columns to real EV identifiers,
- replacing forecast availability with real availability,
- replacing forecast session energy with real session energy,
- updating service-level-adjusted remaining energy,
- updating upper bounds for reduced-service cases.

Second, the dynamic forecast is refreshed. For persistence forecasting, observed EVs use real day-0 data, while unobserved future EVs continue to use persistence forecast data. The beyond-midnight tail uses already executed day-0 EV load.

Third, the rolling MPC optimization problem is solved for each case. The model optimizes over a 96-step horizon but only the first time-step action is executed.

Fourth, the implementation dispatches energy only to EVs that are physically present and available at the current interval. This is critical: the optimizer may forecast future EVs, but the executed first action is constrained to real current availability.

Finally, the remaining EV energy state is updated by subtracting the actually executed dispatch:

```text
remaining_energy_after_k = remaining_energy_before_k - executed_dispatch_k
```

This closes the loop between optimization and physical execution.

## 6. Optimization Model

At each real-time step, the MPC model includes:

- EV charging decision variables,
- grid import variables,
- BESS charge/discharge variables,
- BESS state-of-charge variables,
- wholesale market variables if market participation is enabled.

The EV charging table is:

```text
E_EV[t, n]
```

where `t` is the time index in the rolling horizon and `n` is the EV index.

The aggregate EV charging energy at each time step is:

```text
E_step[t] = sum_n E_EV[t, n]
```

The EV charging power is:

```text
p_EV[t] = E_step[t] / dt
```

The grid import is:

```text
p_GI[t] = p_EV[t] + p_BESS[t]
```

The EV charging decision is bounded by forecast or real charging availability:

```text
0 <= E_EV[t, n] <= EV_upper_bound[t, n]
```

The total energy assigned to each EV over the rolling horizon must satisfy the EV's remaining energy requirement:

```text
sum_t E_EV[t, n] >= E_required[n]
```

and it must not exceed the corresponding upper bound:

```text
sum_t E_EV[t, n] <= E_max[n]
```

## 7. Day-0 Energy Closure Constraint

One important correction is needed when the rolling horizon extends beyond midnight. If the optimizer is allowed to satisfy today's EV energy requirement using the post-midnight persistence tail, then the physical day-0 dispatch may fail to deliver all true day-0 EV energy.

To prevent this, the implementation adds a day-0 truncation constraint. Let:

```text
M_today[t] = 1 if rolling-horizon step t is still within day 0
           = 0 otherwise
```

Then the optimizer must satisfy the day-0 remaining EV energy within the day-0 portion of the horizon:

```text
sum_t M_today[t] * E_EV[t, n] >= E_today_required[n]
```

This ensures that the persistence tail improves forecast shape but cannot be used to satisfy same-day EV service obligations.

## 8. First-Step Execution Constraint

Another important correction concerns the first MPC action. In a rolling forecast, future EVs may appear in the 96-step forecast matrix. However, at the current real-time step, only EVs that have actually arrived can be charged.

Therefore, before solving the MPC, the first row of the EV upper-bound matrix is clipped by the real current availability:

```text
EV_upper_bound[0, n] = min(EV_upper_bound[0, n], EV_real_current_availability[n])
```

This prevents the optimizer from assigning the immediate dispatch action to forecast EVs that have not physically arrived.

This correction is essential for consistency between optimized EV power and actually executed EV dispatch.

## 9. BESS Model

The BESS model includes charging power, discharging power, net BESS power, and SOC. The SOC dynamics are:

```text
SOC[t+1] = SOC[t] + dt / C_BESS * (sqrt(gamma) * p_ch[t] - p_dch[t] / sqrt(gamma))
```

The SOC is constrained between minimum and maximum limits:

```text
SOC_min <= SOC[t] <= SOC_max
```

The daily BESS throughput is also limited:

```text
dt * sum_t (p_ch[t] + p_dch[t]) + throughput_used <= throughput_limit
```

For the last simulated day, the terminal SOC is constrained to return to 0.5 at midnight.

## 10. Retail Cost

The retail cost includes:

- time-of-use energy cost,
- non-coincident demand charge,
- peak-period demand charge,
- EV service revenue.

The grid import `p_GI` is used to calculate demand charges and TOU cost. The demand charge thresholds are updated dynamically based on the actually executed dispatch and BESS operation.

## 11. Wholesale Market Participation

In `full` mode, the model includes wholesale market variables for:

- day-ahead energy,
- real-time energy,
- regulation up,
- regulation down,
- spinning reserve,
- non-spinning reserve.

The model includes capacity feasibility constraints, direction-alignment constraints, and soft penalties for deviations from day-ahead awards.

In `retail_only` mode, wholesale market participation is disabled:

```text
Enable_WM = False
```

The wholesale variables are constrained to zero, so the resulting optimization represents retail-only operation.

## 12. Execution and Reconciliation

After solving the optimization problem at each real-time step, only the first control action is executed. The executed dispatch is written into:

```text
Dispatch[j][i][k, :]
```

The remaining EV energy is then updated using the actual executed dispatch rather than the planned full-horizon schedule.

At the end of each day, the implementation performs a strict energy reconciliation for the base case:

```text
sum(actual executed EV dispatch) == sum(true day-0 EV session energy)
```

If the equality fails within tolerance, the code stops and prints the mismatch:

```text
dispatched, real_session, diff
```

This check ensures that the rolling MPC implementation preserves strict same-day EV energy delivery.

## 13. Output Files

The implementation writes daily results to:

```text
Results_Rolling/Dispatch/
```

Key outputs include:

```text
*_implementation.csv
*_daily_summary.csv
```

The implementation file stores interval-level dispatch and cost-related quantities. The daily summary file stores EV-level forecast, real session energy, service-level information, and executed dispatch totals.

## 14. Current Computational Profile

For a one-day test with `full` mode, the current implementation takes approximately 80 seconds. Most of the runtime is spent inside Gurobi:

```text
dynamic forecast and parameter update: small
Gurobi optimization: dominant
result extraction and saving: small
```

The main computational burden comes from solving two real-time MPC cases across 96 intervals. In `full` mode, the model includes wholesale market variables and binary variables. In `retail_only` mode, the market variables are disabled, but the current code still builds the same broad model structure and constrains wholesale variables to zero.

## 15. Potential Improvements

The most important future speed improvement would be to build a separate retail-only model that omits all wholesale market variables and binary variables. This would reduce the optimization size substantially.

Other possible improvements include:

- separating forecast construction, model construction, solve, execution, and output into independent functions,
- reducing repeated dataframe reindexing inside the 96-step loop,
- caching EV column mappings,
- avoiding unnecessary construction of disabled wholesale variables in retail-only mode,
- creating clearer validation utilities for daily energy reconciliation.

The current implementation is suitable for long simulation runs, but the code could be made cleaner and faster by modularizing the main loop and specializing the retail-only optimization model.
