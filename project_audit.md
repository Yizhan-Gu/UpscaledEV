# Project Audit for SEGAN Journal Paper

Audit date: 2026-06-12  
Project folder: `/Users/admin/Desktop/EV_program/Total Transfer/PowerFlex_Code/UPSCALeDEV_2024`

Scope: recursive scan of the project folder, excluding very large/internal folders where appropriate for summary counts (`.git`, `.conda`, `__pycache__`, and `Sessions_Data`). No paper files were rewritten during this audit.

## 1. Current Main TeX File

There are two LaTeX sources relevant to the paper:

1. `clean.tex`
   - Location: project root.
   - Status: formula/model draft only.
   - Class: `\documentclass[conference]{IEEEtran}`.
   - Uses `biblatex` with `\addbibresource{references.bib}`, but no `references.bib` exists next to `clean.tex` in the project root.
   - Content is mainly mathematical formulation, nomenclature, and constraints. It is not a complete journal manuscript.

2. `upscaledev_ieee_paper_overleaf_source.zip`
   - Location: project root.
   - This is the current complete manuscript package.
   - Inside the zip, the main manuscript is `upscaledev_ieee_paper/main.tex`.
   - Class: `\documentclass[journal]{IEEEtran}`.
   - Includes `references.bib`, `main.bbl`, `IEEEtran.cls`, and figure assets.
   - This should be treated as the current main paper draft, but it is still inside a zip rather than extracted as a normal editable paper folder.

Important journal-format note: the target journal is Sustainable Energy, Grids and Networks (SEGAN), which is an Elsevier journal, while the current complete manuscript is in IEEEtran format. Before submission, the manuscript should likely be migrated from IEEEtran to the Elsevier/SEGAN-compatible format after checking the latest SEGAN Guide for Authors.

## 2. Figures, Tables, and Result Files in the Project

### High-Level File Inventory

Filtered recursive count excluding `.git`, `.conda`, `__pycache__`, and `Sessions_Data`:

| Extension | Count |
|---|---:|
| `.csv` | 3360 |
| `.zip` | 1096 |
| `.png` | 619 |
| `.xml` | 284 |
| `.py` | 60 |
| `.ipynb` | 9 |
| `.pdf` | 14 |
| `.pptx` | 2 |
| `.md` | 3 |
| `.tex` | 1 |
| `.docx` | 1 |
| `.html` | 1 |
| `.json` | 1 |
| `.txt` | 2 |

### Main Notebooks

| File | Role |
|---|---|
| `upscaledev_imp.ipynb` | Old/shrinking MPC implementation. |
| `upscaledev_imp_rollingMPC.ipynb` | New rolling MPC implementation. |
| `upscaledev_baseline.ipynb` | Baseline simulation. |
| `upscaledev_EVdata_postprocessing.ipynb` | EV data post-processing. |
| `Bess_only_test.ipynb` | BESS-only tests/plots. |
| `timeline.ipynb` | Timeline/market-bidding figure work. |
| `AS_download.ipynb`, `LMP_download.ipynb`, `LMP_modifying.ipynb` | Market data acquisition/processing. |

### Main Input Data

| Folder/File | Contents |
|---|---|
| `2025Data/EV_data/` | Raw and processed UCSD EV session/interval data, plus QC figures. |
| `2025Data/Bldg_data/Bldg_load.csv` | Building load. |
| `2025Data/PV_data/CSV_2025-08-06-18-42-25.csv` | PV data. |
| `2025Data/LMP/` | CAISO LMP data, including many daily zip/xml/csv files and cleaned 2025 LMP CSVs. |
| `2025Data/AS_DAM/`, `2025Data/AS_RTM/` | Ancillary-service price data and plots. |
| `Forecasting/` | ML forecasting datasets and scripts. |
| `References/` | CAISO, tariff, DSGS, and market reference PDFs/PPTX. |

### Main Result Folders

| Folder | Contents |
|---|---|
| `Results/Dispatch/` | Shrinking/old controller dispatch and daily summary CSVs. Includes persistence and perfect forecast variants, full/both, retail-only, wm-only, and baseline outputs. |
| `Results_Rolling/Dispatch/` | Rolling controller dispatch and daily summary CSVs. Contains persistence full/both and retail-only implementation and daily summary files. |
| `Results/Plots/Cost/...` | Shrinking financial summary CSVs and value-stack figures. |
| `Results_Rolling/Plots/Cost/...` | Rolling financial summary CSVs and value-stack figures. |
| `Results/Plots/Solver_DA_Choices/` | Many per-day DA optimization CSVs and 6-panel diagnostic PNGs. |
| `Results/Plots/Solver_RT_Choices/` | Many per-day shrinking RT optimization CSVs and 6-panel diagnostic PNGs. |
| `Results_Rolling/Plots/Solver_RT_Choices/` | Many per-day rolling RT optimization CSVs and 6-panel diagnostic PNGs. |
| `Results/Plots/Daily_Price_Tables/202507/` | 31 daily July 2025 price table CSVs. |
| `Results_Rolling/Plots/Daily_Price_Tables/202507/` | 31 rolling-side daily July 2025 price table CSVs. |
| `Results/BESS_test/` | 31 daily BESS-only optimization PNGs plus monthly BESS operations plot. |

### Key Cost/Result Files

Shrinking cost outputs:

- `Results/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/monthly_financial_summary.csv`
- `Results/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_financial_detail.csv`
- `Results/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/monthly_summary_grouped_bar.png`
- `Results/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_value_stack_comparison.png`
- `Results/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_wm_revenue_breakdown_2x1.png`
- `Results/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_financial_metrics_all.png`
- `Results/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_financial_metrics_hbar.png`
- `Results/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_wm_delta.png`

Rolling cost outputs:

- `Results_Rolling/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/monthly_financial_summary.csv`
- `Results_Rolling/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_financial_detail.csv`
- `Results_Rolling/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/monthly_summary_grouped_bar.png`
- `Results_Rolling/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_value_stack_comparison.png`
- `Results_Rolling/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_wm_revenue_breakdown_2x1.png`
- `Results_Rolling/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_financial_metrics_all.png`
- `Results_Rolling/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_financial_metrics_hbar.png`
- `Results_Rolling/Plots/Cost/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival/daily_wm_delta.png`

Representative figure dimensions:

| Figure | Size |
|---|---:|
| `Results/Plots/Timeline_Market_Bidding_MPC.png` | 5369 x 1768 |
| `Results/Plots/Scheme_Yizhan.png` | 3672 x 2072 |
| `Results/Plots/c_e_TOU_AL_Summer.png` | 1000 x 500 |
| `Results/BESS_test/BESS_Operations.png` | 4500 x 1800 |
| Shrinking `monthly_summary_grouped_bar.png` | 1963 x 1156 |
| Shrinking `daily_value_stack_comparison.png` | 2863 x 1688 |
| Shrinking `daily_wm_revenue_breakdown_2x1.png` | 3690 x 1506 |
| Rolling `monthly_summary_grouped_bar.png` | 1963 x 1156 |
| Rolling `daily_value_stack_comparison.png` | 2863 x 1688 |
| Rolling `daily_wm_revenue_breakdown_2x1.png` | 3690 x 1506 |
| Rolling `daily_financial_metrics_all.png` | 3970 x 3279 |

### Confirmed Monthly Results from CSVs

From shrinking `monthly_financial_summary.csv`:

| Case | Total Revenue | WM Revenue | TOU Cost | PD Cost | NCD Cost | EV Revenue |
|---|---:|---:|---:|---:|---:|---:|
| Retail only | 7875.04 | 0.00 | -9039.14 | -281.14 | -4752.45 | 21947.80 |
| Both | 8240.38 | 3513.12 | -10490.10 | -300.81 | -6429.66 | 21947.80 |

From rolling `monthly_financial_summary.csv`:

| Case | Total Revenue | WM Revenue | TOU Cost | PD Cost | NCD Cost | EV Revenue |
|---|---:|---:|---:|---:|---:|---:|
| Retail only | 7936.10 | 0.00 | -8546.65 | -88.91 | -5376.12 | 21947.80 |
| Both | 7926.01 | 3735.76 | -10850.23 | -278.23 | -6629.05 | 21947.80 |

These values match the current manuscript text inside `upscaledev_ieee_paper_overleaf_source.zip`.

## 3. Which Figures/Tables/Results Are Already in the Paper

The current complete manuscript is `upscaledev_ieee_paper/main.tex` inside the zip.

### Figures Included in Current Paper

The paper references these four figures:

| Paper figure | File inside zip | Source/meaning |
|---|---|---|
| Monthly value-stack comparison | `figures/monthly_summary_grouped_bar.png` | Rolling cost/value-stack figure. |
| Controller comparison | `figures/controller_comparison.png` | Custom rolling-vs-shrinking net value figure. |
| Daily wholesale revenue decomposition | `figures/daily_wm_revenue_breakdown_2x1.png` | Rolling wholesale revenue breakdown. |
| Daily value-stack comparison | `figures/daily_value_stack_comparison.png` | Rolling daily value-stack figure. |

### Tables Included in Current Paper

The current manuscript includes these tables:

| Table | Content |
|---|---|
| `tab:rolling_procedure` | Execution-aware rolling MPC procedure. |
| `tab:monthly` | Monthly value stack for shrinking and rolling, retail-only and both. |
| `tab:controller_comparison` | Rolling vs shrinking net monthly value by operating mode. |
| `tab:wm_decomp` | Rolling wholesale revenue decomposition by asset/function. |

### Results Included in Current Paper

Already included:

- Monthly financial comparison of shrinking vs rolling.
- Retail-only vs both comparison.
- EV energy reconciliation statement for all four controller-mode combinations.
- Rolling wholesale revenue decomposition.
- Interpretation that rolling retail-only beats shrinking retail-only, while shrinking both beats rolling both.
- Solver settings: Gurobi through CVXPY, 0.1% MIP gap, 0.5 s RT solve time limit.

### Figures/Results Not Yet Included

Strong candidates not yet used:

- `daily_financial_metrics_all.png` is packaged in the zip but not referenced by `main.tex`.
- `daily_financial_metrics_hbar.png` is not packaged/included.
- `daily_wm_delta.png` is not packaged/included.
- Shrinking-specific cost plots from `Results/Plots/Cost/...` are not packaged/included. The current paper uses the rolling cost figures plus one custom controller-comparison plot. For a fair SEGAN paper, at least one combined rolling/shrinking comparison figure would be stronger than showing rolling-only value-stack figures.
- `Results/Plots/Timeline_Market_Bidding_MPC.png` is not included. This could be useful as a methodology/workflow figure.
- `Results/Plots/Scheme_Yizhan.png` is not included. This could be useful as a system architecture figure if visually polished.
- `Results/BESS_test/BESS_Operations.png` and daily BESS-only plots are not included. These are likely supplementary unless BESS operation is central to a result section.
- DA/RT six-panel solver diagnostic plots are not included. These are too detailed for the main paper but could support an appendix/supplement with one representative day.
- Daily price table CSVs are not included. They are data products, not paper tables, unless a representative price day is needed.
- Forecasting datasets in `Forecasting/` are not discussed in the current paper except indirectly through persistence forecasting.

## 4. Formulas/Constraints in `clean.tex` Not Yet in Current Paper

The current paper includes simplified versions of the objective, EV service constraints, BESS SOC, grid import, retail cost, wholesale revenue, up/down capacity envelopes, persistence update, first-step clip, and energy reconciliation.

The following details from `clean.tex` are missing or only summarized in the current paper:

1. EV boundary-condition state equations:
   - `e_{a_i,i}=e_{a_i}`
   - `e_{d_i,i}=e_{d_i}`
   - `e_{0,i}=0`

2. Detailed per-EV energy-state evolution:
   - `e_{t,i}=e_{t-1,i}+p_{t,i}^{EV} Delta t / eta_i^{EV}`
   - `0 <= e_{t,i} <= e_{d_i}`
   - The current paper uses direct interval energy delivery `x_{t,i}` and aggregate power, which is cleaner but less complete than the original state formulation.

3. Exact connectedness/binary availability definition:
   - `b_{t,i}^{EV}=1` if `a_i <= t <= d_i`, otherwise zero.
   - Current paper uses `m_{t,i}` but does not fully spell out the arrival/departure piecewise definition.

4. BESS terminal equality:
   - `soc_0^{BESS}=soc_96^{BESS}`.
   - Current paper discusses BESS SOC and throughput but does not explicitly state this terminal daily equality.

5. BESS wholesale/non-wholesale split:
   - `p_ch,BESS = p_ch,BESS,WM + p_ch,BESS,NWM`
   - `p_dch,BESS = p_dch,BESS,WM + p_dch,BESS,NWM`
   - Current paper uses a higher-level BESS model and wholesale envelope but not this decomposition.

6. Detailed wholesale variable definitions:
   - Free energy variables, nonnegative capacity variables, and binary variables for DA/RT and ancillary-service products.
   - Current paper only gives compact revenue and capability-envelope notation.

7. Exact BESS-only and BESS+EV capacity constraints:
   - BESS-only up/down envelopes.
   - BESS+EV constraints using `max(p_DA,0)`, `max(-p_DA,0)`, `max(p_RT,0)`, and `max(-p_RT,0)`.
   - Current paper summarizes upward/downward products by `P_up` and `P_down` but omits the full linearized implementation details.

8. Binary directionality and big-M constraints:
   - `b_ch,BESS + b_dch,BESS <= 1`
   - `b_ch,EV + b_dch,EV <= 1`
   - `b_ch,net + b_dch,net <= 1`
   - `M^EV = 2 P_{t,max}^{EV}`
   - `p_EV - B_EV = p_ch,EV - p_dch,EV`
   - Current paper only states that binary direction variables prevent simultaneous net charge/discharge.

9. Detailed net charging/discharging constraints:
   - Full definitions of `p_ch,net` and `p_dch,net` relative to energy and ancillary-service deployment terms.
   - Current paper omits these implementation equations.

10. Ancillary-service duration constraints:
    - Constraints using `T_DU`, `SOC_min`, `SOC_max`, capacity products, and BESS energy capacity.
    - Current paper mentions duration constraints but does not write them explicitly.

11. Full revenue decomposition formulas:
    - Energy vs capacity decomposition.
    - Asset attribution formulas for BESS vs EV using weights `omega`.
    - Current paper includes the decomposition result table but not the full mathematical attribution equations.

12. Nomenclature table:
    - `clean.tex` contains a nomenclature block; the current paper uses IEEE keywords but no nomenclature table/list.

Recommendation: for a SEGAN journal version, keep the compact model in the main Methodology section, then add an Appendix or Supplementary Material section titled something like `Complete MILP Formulation`. That appendix should migrate the missing `clean.tex` constraints instead of crowding the main narrative.

## 5. LaTeX Compile Status

Compile target tested:

- `/tmp/upscale_audit_paper/upscaledev_ieee_paper/main.tex`, extracted from `upscaledev_ieee_paper_overleaf_source.zip`.

Compile command sequence:

```bash
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

Result:

- Compile exit code: `0`.
- PDF generated successfully in `/tmp/upscale_audit_paper/upscaledev_ieee_paper/main.pdf`.
- No fatal LaTeX errors were found after the full compile sequence.

Warnings/notes:

- First `pdflatex` pass naturally reported undefined citations and references before BibTeX and reruns. These resolved after the full sequence.
- The manuscript uses `\bibliographystyle{unsrt}` while `\bibliographystyle{IEEEtran}` is commented out. The comment says IEEEtran can be used on Overleaf if `IEEEtran.bst` is available.
- Current complete paper format is IEEEtran, not an Elsevier/SEGAN template.
- `clean.tex` was not treated as the active compile target because it is an incomplete formula draft and lacks a local `references.bib` in the root.

## 6. Suggested Next Integration Steps

1. Extract the current paper zip into a normal version-controlled folder, for example `paper_segan/`, and make that the active manuscript folder.

2. Decide the final target format before more writing:
   - If submitting to SEGAN, migrate from IEEEtran to the Elsevier-compatible template/class.
   - Keep the IEEE version only as an intermediate writing draft.

3. Strengthen the figure set:
   - Add a system/methodology figure using `Timeline_Market_Bidding_MPC.png` and/or a polished version of `Scheme_Yizhan.png`.
   - Add one fair rolling-vs-shrinking value-stack figure. The current `controller_comparison.png` is useful but too compressed by itself.
   - Consider including `daily_financial_metrics_all.png` or a cleaner replacement if daily variability is important.
   - Move detailed solver diagnostic plots to appendix/supplement, not main text.

4. Strengthen the formulation:
   - Keep the main text compact.
   - Add an appendix/supplement with the missing `clean.tex` constraints: EV state dynamics, BESS terminal constraint, WM/NWM BESS split, direction binaries, big-M EV decomposition, ancillary duration constraints, and revenue attribution formulas.

5. Strengthen reproducibility:
   - Add a short data/workflow section mapping raw data folders to processed inputs and final result CSVs.
   - Clearly state that `Results` is shrinking and `Results_Rolling` is rolling.
   - Add a table of solver settings shared by both controllers: solver, threads, MIP gap, time limit, horizon length, interval length, forecast method.

6. Clarify the central scientific message:
   - Rolling MPC improves retail-only operation in July 2025.
   - Shrinking MPC achieves higher profit in the wholesale-enabled case because rolling earns more WM revenue but creates larger TOU/NCD exposure.
   - This is a meaningful result, not necessarily a bug, provided identical solver settings and exact EV energy reconciliation remain documented.

7. Clean the submission package:
   - Include only manuscript source, bibliography, required figures, and maybe appendix/supplement.
   - Exclude raw result folders, notebooks, `.DS_Store`, `.conda`, `.git`, and bulk CAISO zip/xml data from the Overleaf/submission package.

## Bottom Line

The project has enough material for a SEGAN journal paper, and the current complete manuscript zip compiles successfully. The main gap is integration: the paper currently uses an IEEE format, includes only a subset of the available figures, and summarizes several important constraints from `clean.tex` rather than carrying the complete MILP details. The next best move is to extract the paper into a dedicated `paper_segan/` folder, migrate formatting for SEGAN, add a compact methodology/system figure, add a fair rolling-vs-shrinking comparison figure/table, and move the detailed `clean.tex` constraints into an appendix or supplement.
