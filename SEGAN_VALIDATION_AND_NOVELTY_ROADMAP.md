# SEGAN validation and novelty roadmap

This document translates Jan's requested order of work into an acceptance
sequence for the current EV+BESS study:

1. validate the implementation;
2. establish the literature boundary and defensible novelty;
3. select figures and sensitivity analyses that test the novel claims.

No result should be promoted to the manuscript merely because it is
economically favorable. It must first pass the numerical, physical, settlement,
and provenance checks below.

## 1. Current evidence status

### Evidence that is currently usable

- The base Rolling source notebook now emits a 96-row executed validation trace
  for every simulated day. Each row is the first action actually implemented
  from one RT solve, not the remaining plan from the midnight solve.
- A corrected one-day audit for 2025-06-01 compares:
  - Rolling 24-hour Persistence;
  - Rolling 24-hour Perfect EV information;
  - a same-baseline full-horizon Perfect oracle.
- All three cases have 96 unique intervals, the same executed EV energy
  (21.663 kWh to numerical tolerance), terminal BESS SOC 0.5, meter balance
  within numerical tolerance, nonnegative actual AS, and no up/down capability
  violation.
- On that controlled day, net value is USD 89.16 for Persistence, USD 106.34
  for 24-hour Perfect, and USD 108.651719 for the oracle. The oracle achieved
  a 0.0090% MIP gap and exceeds the same-baseline Rolling Perfect result by
  USD 2.311719.

This is a smoke test and a graph-format validation. One successful day is not
evidence that the month-long implementation is bug-free.

### Evidence that must not be cited as final

The previously saved full-June oracle variants are superseded. Their EV
capability was constructed from a daily vehicle count and repeated across every
15-minute interval. That creates fictitious EV/AS headroom when vehicles are
not connected. Those files remain only as provenance records; they must be
regenerated with interval-specific connected-EV capability before use.

The independent MPC validation runner also previously selected a notebook cell
that contained the full 2x2 runner instead of the pure post-processing cell.
That source-selection bug is corrected. Formal independent Rolling monthly
results should be regenerated after the corrected oracle is accepted.

## 2. Publication validation ladder

The validation must progress in this order.

### Gate A: formulation and source audit

For every modeled interval, verify:

\[
p_t^{actual}=p_t^{DA,commit}+p_t^{RT,dev},
\]

\[
p_t^{GI}=p_t^{EV}+p_t^{BESS},
\]

\[
[p_t^{actual}]^+
+c_{RU,t}^{actual}+c_{SP,t}^{actual}+c_{NSP,t}^{actual}
\le P_t^{up},
\]

\[
[-p_t^{actual}]^+ + c_{RD,t}^{actual}\le P_t^{down},
\]

\[
P_t^{EV,max}
=\frac{1}{\Delta t}\sum_j \overline E_{j,t}^{EV}.
\]

The DA quantities used in RT must be immutable submitted commitments. The
reported RT energy quantity must be the signed deviation settled at the RT
price. Actual AS quantities must equal DA commitments plus signed RT changes
and remain nonnegative.

### Gate B: deterministic one-day regression

Use one fixed date and identical:

- realized EV sessions;
- initial and terminal SOC;
- historical NCD and PD thresholds;
- DA/RT/AS/TOU prices;
- baseline and interval EV capability;
- solver formulation and financial accounting.

Run Rolling Persistence, Rolling Perfect, and the same-baseline Perfect oracle.
Require all structural checks in `MPC_RESULT_VALIDATION_CHECKLIST.md`.

### Gate C: daily visual and machine-readable audit

For every reported day, save both a graph and an audit row. The daily graph must
show three columns only:

1. Rolling 24-hour Persistence;
2. Rolling 24-hour Perfect;
3. full-horizon Perfect oracle.

The required panels are:

- executed EV, BESS, and meter power with the EV baseline;
- separate DA commitment and RT-deviation bars, the actual position, and both
  physical bounds;
- actual RU, RD, SP, and NSP provision with the residual up/down capability;
- BESS SOC with DA LMP, RT LMP, and TOU price;
- log-scale meter/capability residuals.

The plot is supporting evidence. Acceptance decisions must use the associated
CSV tolerances rather than visual inspection alone.

### Gate D: selected-day stress tests

Before a month-long run, choose days that stress distinct mechanisms:

- largest EV-energy day;
- largest Persistence forecast error;
- largest DA/RT energy-price spread;
- largest AS price;
- day that sets or changes the monthly NCD/PD threshold;
- day with the smallest connected-EV capability;
- day with the largest 24-hour Perfect-to-Persistence value reversal, if any.

The formal MPC tolerance is 1%. If a reported ordering is smaller than the
solver's certified objective uncertainty, report the ordering as numerically
unresolved rather than forcing a tighter-gap rerun.

Gate D was completed for June 1, 3, 5, 12, 13, and 29. The six dates cover the
criteria above after removing duplicates. All 1,164 DA/RT solves were
`optimal`, no TimeLimit event occurred, the maximum achieved MIP gap was below
1%, and every physical/accounting audit passed. Reproducible evidence is saved
under:

- `Validation_Results/June_2025/short_tests/gate_d/`
- `Validation_Results/June_2025/short_tests/rolling/daily_graphs/`

The short third scenario is a one-day simultaneous Perfect benchmark, not a
slice of the full billing-period oracle. Its incumbent and best bound are both
reported; it is not used to claim full-period dominance.

### Gate E: formal June experiment

Only after Gates A-D pass:

- run the corrected full-June Perfect oracle;
- run the two Rolling 24-hour policies with trace capture;
- generate all daily audit CSV rows and selected representative-day figures;
- require a formal oracle gap no larger than 1%, and report both incumbent and
  certified bound;
- compare the oracle only to a trajectory with the same exogenous baseline,
  states, boundary conditions, constraints, and accounting.

A cross-baseline revenue difference is descriptive, not an oracle-dominance
test.

Gate E is complete for the immutable tag
`gate_e_20260726_c8250f11`. The Rolling 24-hour Perfect and Persistence cases
produced 5,820 accepted DA/RT solver records, all Gurobi status 2/CVXPY
`optimal`, with no TimeLimit event and maximum gap below 1%. The accepted
full-billing-period Perfect oracle terminated normally at the configured 1%
tolerance with a 0.8571% gap.

The accepted monthly net values are USD 10,733.15 for Rolling 24-hour Perfect,
USD 10,485.28 for Rolling 24-hour Persistence, and USD 12,565.15 for the
same-baseline full-billing-period Perfect oracle. The oracle therefore exceeds
the 24-hour Perfect policy by USD 1,832.00. This comparison uses the exact
Rolling Perfect exogenous baseline; the maximum saved baseline difference is
\(5\times 10^{-9}\) kW.

All 19 formal acceptance checks pass. Every June date has a PNG, PDF, physical
audit CSV, and cross-scenario CSV. The report and tables are saved under:

- `Validation_Results/June_2025/formal_runs/gate_e_20260726_c8250f11/GATE_E_VALIDATION_REPORT.md`
- `Validation_Results/June_2025/formal_runs/gate_e_20260726_c8250f11/gate_e_validation_checks.csv`
- `Validation_Results/June_2025/formal_runs/gate_e_20260726_c8250f11/gate_e_monthly_financial_comparison.csv`
- `Validation_Results/June_2025/formal_runs/gate_e_20260726_c8250f11/rolling/daily_graphs/`

An earlier 900-second oracle attempt is retained as provenance because it
found a higher feasible incumbent (USD 12,603.64) but stopped at a 1.2006%
gap. It is not substituted into the accepted 0.8571%-gap solver certificate.

### Gate F: independent reproducibility

Archive, outside Git where necessary:

- code commit hash and dirty-status record;
- input file hashes and date coverage;
- solver version, status, MIP gap, objective value, and objective bound;
- run configuration;
- daily trace/audit tables;
- regenerated paper figures.

SEGAN's data-policy expectations make this provenance important even if raw
site data cannot be publicly released.

## 3. CAISO implementation boundary

CAISO procures regulation up, regulation down, spinning reserve, and
non-spinning reserve. Spinning and non-spinning reserve must be deliverable
within 10 minutes; CAISO certification material also describes maintaining
reserve output for 30 minutes. Participation additionally requires
certification and telemetry.

The current model uses a common 0.5-hour energy-headroom constraint for the
upward products and regulation down. That is a transparent modeling assumption,
not a complete reproduction of CAISO certification, AGC mileage, performance,
no-pay, bid, or settlement rules. Before submission:

- keep the current 0.5-hour case as the reference assumption;
- separate product-specific duration/deployment assumptions in a sensitivity;
- state clearly that expected deployment factors are used;
- do not describe simulated AS revenue as an exact CAISO settlement;
- report minimum-size, aggregation, telemetry, certification, and
  scheduling-coordinator requirements as deployment limitations.

## 4. Literature boundary and defensible novelty

The following ideas are already established and must not be claimed as novel:

- MPC for EV charging or microgrid energy management;
- EV aggregation for reserve or ancillary-service provision;
- BESS value stacking, TOU arbitrage, demand-charge management, and PV
  self-consumption;
- coordination of EV chargers, PV, and BESS;
- use of a perfect-information oracle as an upper benchmark.

Close prior art includes:

- Chen et al. (2024, 2026): the two UCSD/TotalEnergies workplace-EV
  optimization predecessors;
- Chen et al. (2021): real-world UCSD BTM BESS value stacking for demand
  response and demand-charge management;
- Hermans et al. (2024): implemented MPC for more than 150 workplace chargers
  with PV;
- recent EV reserve/MPC studies that model aggregate feasibility under forecast
  uncertainty;
- recent BTM BESS studies that stack building/PV objectives and frequency
  reserve.

The strongest defensible contribution is therefore the tested combination and
its evidence chain:

1. **Execution-aware two-settlement accounting.** Fixed DA commitments, signed
   RT deviations, actual physical positions, and executed first-step accounting
   are kept distinct throughout the optimization and results.
2. **Retail-wholesale interaction at one campus meter.** EV service revenue,
   TOU cost, monthly demand charges, wholesale energy, and multiple AS products
   are evaluated jointly rather than reporting gross market revenue alone.
3. **Heterogeneous flexibility in one deliverability envelope.** Unidirectional
   workplace EV load flexibility and bidirectional BESS power/SOC are
   co-optimized without treating the EV fleet as V2G storage.
4. **Forecast value separated from horizon value.** Rolling Persistence and
   Rolling Perfect are compared with a true full-period oracle, making clear
   that a 24-hour perfect forecast is not a global upper bound.
5. **Auditability from executed dispatch.** Daily physical, market, financial,
   solver-quality, and constraint-residual evidence is retained in
   machine-readable form.

The paper should call these a market-timeline-consistent applied framework and
validation contribution, not a new MPC algorithm.

## 5. Sensitivity analyses guided by the novelty

Priority follows the claims above, not the availability of extra data.

### Priority 1: value-stack interaction

Vary AS availability/prices and retail demand-charge rates. Report where gross
wholesale revenue ceases to improve net BTM value and which retail component
causes the reversal.

### Priority 2: deliverability assumptions

Vary AS deployment factors and product duration assumptions. Report EV/BESS
capacity attribution, SOC headroom, actual AS, and revenue rather than capacity
awards alone.

### Priority 3: forecast and horizon value

Compare Rolling Persistence, Rolling Perfect, and full-period Perfect oracle.
Report both value gaps and the state/commitment trajectories that explain them.
Forecast error alone is insufficient.

### Priority 4: resource mix

Vary BESS power/energy rating and EV participation/connected capacity. Identify
whether the two resources are complementary or whether they compete for the
same meter and AS headroom.

### Priority 5: passive PV and building load

Add measured PV and building load as passive exogenous meter injections. Treat
this as a robustness test of the retail-wholesale result, not as the principal
novelty. Evaluate at least net-load magnitude, PV scaling, and forecast quality
after the base EV+BESS evidence is accepted.

### Priority 6: EV baseline definition

Repeat the central result under alternative defensible baseline rules. Because
the baseline determines claimed load-reduction headroom, this is a material
market-participation sensitivity, not merely a plotting choice.

## 6. Manuscript consequence

`Latex/main_segan_v2.6.tex` is the current manuscript source and already states
that numerical results must be regenerated. Do not insert the superseded
full-June oracle values. The next numerical-results edit should occur only after
the corrected June evidence passes Gate E. The main text should contain one
compact representative-day Rolling/oracle figure; the complete daily audit set
belongs in supplementary material or a data repository.

The manuscript now points to `Latex/references_v2.6.bib`, rather than the
legacy `references_v2.4.bib` or unused `references.bib`. All 20 citation keys
used by v2.6 resolve exactly once, and a standalone BibTeX smoke test passes.
The full Elsevier document still cannot compile on the current machine because
`elsarticle.cls` is not installed; this environment issue must be closed before
submission.

## 7. Evidence locations

Corrected one-day graph and audit:

```text
Validation_Results/June_2025/short_tests/rolling/daily_graphs/2025-06-01/
```

Corrected one-day Rolling MPC outputs:

```text
Validation_Results/June_2025/short_tests/rolling/mpc/
```

Corrected one-day oracle:

```text
Validation_Results/June_2025/short_tests/rolling_perfect/oracle/
```

Previously requested full-horizon oracle work:

```text
Validation_Results/June_2025/benchmark/oracle/
Validation_Results/June_2025/common/oracle/
Validation_Results/June_2025/rolling/oracle/
Validation_Results/June_2025/shrinking/oracle/
```

These old monthly oracle folders are now superseded for final quantitative use,
for the interval-capability reason documented above.

Previously requested same-state daily forecast comparison:

```text
Validation_Results/June_2025/rolling/matched_state/
Validation_Results/June_2025/shrinking/matched_state/
Validation_Results/June_2025/common/matched_state/matched_state_june_comparison.csv
Validation_Results/June_2025/common/matched_state/matched_state_exact_gap_audit.csv
```

The reusable validation program is:

```text
oracle_and_matched_state_validation.py
```

It is kept in the repository root; a one-file `tests/` directory is not needed.
