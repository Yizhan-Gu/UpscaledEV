# TODO list for paper version 2.2

This document collects items intentionally kept out of the manuscript text so the paper itself does not contain visible TODO markers.

## 1. Author and affiliation checks

- Confirm final author order.
- Confirm Jan Kleissl is the corresponding author.
- Confirm UCSD affiliation wording: `Center for Energy Research, University of California San Diego`.
- Confirm TotalEnergies affiliation for Hadi Eshraghi and Wente Zeng. Use either TotalEnergies SE or the specific TotalEnergies U.S./external affiliation preferred by the project team.
- Confirm whether Hadi's email `hadi.eshraghi@external.totalenergies.com` should appear in the manuscript or only in the submission system.
- Confirm whether Wente's email `wente.zeng@totalenergies.com` should appear in the manuscript or only in the submission system.

## 2. Figures to provide or rename in Overleaf

The v2.2 manuscript assumes manually uploaded paper figures. Confirm exact file names and update `\includegraphics` calls if needed.

Required or recommended figures:

- `market_bidding_mpc_timeline.png`: market bidding and MPC timeline figure.
- Monthly comparison figure for all completed controller/forecast/mode combinations.
- Monthly value-stack decomposition figure.
- Daily financial comparison figure.
- Representative-day 6-panel operational figure from `Solver_RT_Choices` or its subfolders.
- Optional UCSD campus/site map placeholder.
- Optional EV station/map photo placeholder.
- Optional BESS/site photo placeholder.

Important: do not use the earlier generated `controller_comparison` figure unless it is regenerated from verified project CSV files.

## 3. Results and CSV-backed tables

Now that the 2 × 2 cases have been run, generate or verify tables for:

- shrinking MPC + perfect forecast + retail-only;
- shrinking MPC + perfect forecast + wholesale-enabled/both;
- shrinking MPC + persistence forecast + retail-only;
- shrinking MPC + persistence forecast + wholesale-enabled/both;
- rolling MPC + perfect forecast + retail-only;
- rolling MPC + perfect forecast + wholesale-enabled/both;
- rolling MPC + persistence forecast + retail-only;
- rolling MPC + persistence forecast + wholesale-enabled/both.

For each case, verify:

- EV revenue;
- wholesale-market revenue;
- TOU energy cost;
- peak-demand cost;
- non-coincident demand cost;
- net value / total revenue;
- delivered EV energy;
- whether all EV service requirements are satisfied.

Also generate or verify supplementary tables from:

- `monthly_financial_summary.csv`;
- `daily_financial_detail.csv`;
- representative-day product-level revenue/cost CSVs;
- per-step DA/RT/AS revenue and cost breakdown files if available.

## 4. Plotting workflow

Create or update a dedicated `paper_plotting.ipynb` to generate paper-quality figures from verified CSV outputs.

Recommended outputs:

- monthly controller × forecast comparison;
- monthly value-stack decomposition;
- daily total revenue / net value comparison;
- wholesale revenue decomposition;
- representative-day 6-panel figure;
- optional compact appendix figures.

Use consistent font size, line width, color palette, labels, and export resolution. Confirm all figures remain readable in Elsevier 5p/two-column format.

## 5. Forecasting and control assumptions to verify

- Prices are treated as perfect/known exogenous inputs in the current study; only EV-related quantities are forecast.
- Once an EV arrives, its true session information is assumed known for the remaining connection interval.
- Perfect forecast is used as an information benchmark, not as a real deployable forecast.
- Persistence forecast is the main practical forecast used for deployable evaluation.
- ML forecasting is removed from the manuscript for now.

## 6. MPC and penalty formulation checks

The manuscript currently explains the use of a soft penalty for deviations from DA commitments. Verify against code:

- exact penalty term;
- penalty coefficient or tuning parameter;
- whether the penalty applies to RT energy, AS capacity, DA awarded quantities, or another commitment variable;
- hard-constraint infeasibility behavior for rolling MPC;
- whether shrinking hard mode remains feasible only for limited daily tests.

## 7. Optimization formulation consistency checks

Cross-check manuscript and appendix equations against the current implementation notebooks and `clean.tex`:

- EV power and energy-state equations;
- EV arrival/departure treatment;
- EV no-V2G nonnegativity;
- aggregate EV available charging capability;
- BESS SOC dynamics and bounds;
- BESS charge/discharge split;
- retail TOU, peak-demand, and non-coincident demand costs;
- DA and RT energy variables;
- AS capacity variables and deployment factors;
- DA/RT positive-negative linearization;
- binary charge/discharge logic;
- AS duration constraints;
- revenue attribution formulas;
- EV baseline and flexibility definitions.

## 8. References to verify

- Check references 14 and 15 manually. They may not discuss BESS or wholesale-market participation and should not be cited for claims they do not support.
- Add verified BibTeX entries for the two prior collaborator/senior-student papers.
- Confirm citation keys, titles, authors, years, journals/conferences, DOIs, and URLs.
- Ensure all citations in text appear in `references.bib` and all bibliography entries are cited.
- Standardize citation style with `elsarticle-num` or the final SEGAN/Elsevier numeric style.

## 9. Text cleanup before submission

- Remove any remaining coding-style phrases such as file names, configuration names, or raw notebook variable names from the main narrative unless necessary.
- Keep project implementation details in reproducibility/data-processing descriptions, not in high-level conceptual sections.
- Ensure no TODO markers remain in the final manuscript.
- Ensure the abstract is under 250 words.
- Ensure highlights have 3–5 bullets and each bullet is under 85 characters including spaces.
- Ensure all figures and tables are cited in order.
- Ensure all equations are cited or clearly introduced in text.

## 10. Future work and limitations

Current items to keep as limitations/future work rather than completed results:

- additional simulation months;
- sensitivity analysis;
- PV integration;
- building-load integration;
- possible baseline calculation revision;
- overnight charging scenarios;
- ML forecast evaluation if revived later.

## 11. Suggested next version target

Version 2.3 should focus on:

- replacing all placeholder or missing figures with verified uploaded figures;
- inserting CSV-backed tables for the completed 2 × 2 cases;
- tightening figure captions based on the actual images;
- checking equations against code;
- fixing references 14 and 15;
- cleaning the manuscript of any remaining implementation-style wording.
