# UPSCALeDEV 2024 Reproduction and Run Workflow

This document explains how to reproduce the current EV+BESS study from a fresh
Git clone. It is written for collaborators who have the code but do not have the
large CSV/ZIP inputs that are excluded from Git.

## 1. What the repository currently runs

The main experiment is a 2 x 2 controller/forecast comparison:

| Controller | EV forecast | Output root |
|---|---|---|
| Shrinking-horizon MPC | Perfect | `Results/` |
| Shrinking-horizon MPC | Persistence | `Results/` |
| Rolling 24-hour MPC | Perfect | `Results_Rolling/` |
| Rolling 24-hour MPC | Persistence | `Results_Rolling/` |

Each scenario is run in two operating modes:

- `full`: retail tariff plus wholesale energy and ancillary services.
- `retail_only`: retail tariff optimization without wholesale participation.

The current paper experiment uses June 1 through July 30, 2025 (60 days). July
31 is intentionally excluded because a true 24-hour rolling Perfect forecast
for that day would require EV data from August 1. PV and building-load data
exist in `2025Data/`, but they are not yet connected to the optimization.
The ML-at-arrival forecast is also not part of the current 2 x 2 study.

## 2. Why a Git-only clone cannot run

The repository `.gitignore` excludes:

- all `*.csv` files;
- all `*.zip` files;
- all `*.png` files;
- the complete `Results/` directory.

Therefore, GitHub contains the notebooks and Python code but not the EV data,
CAISO market data, baseline dispatch files, optimization results, or paper
figures. A collaborator must receive a separate data bundle.

## 3. Recommended collaborator route

For reproducing the optimization, do not require the collaborator to download
and rebuild every raw dataset. Transfer the following preprocessed-data bundle:

```text
UPSCALeDEV_2024/
├── 2025Data/
│   ├── EV_data/
│   │   └── UCSD_AllSites_Merge_PostProcessedSession_QC.csv
│   ├── AS_DAM/
│   │   └── AS_price_2025_clear.csv
│   ├── AS_RTM/
│   │   └── AS_price_2025_clear.csv
│   └── LMP/
│       └── 2025/
│           ├── DA/
│           │   └── YYYYMMDD_LMP.csv
│           ├── FM/
│           │   └── YYYYMMDD_LMP.csv
│           ├── LMP_DA_2025_clean.csv
│           └── LMP_FM_2025_clean.csv
├── Results/
│   └── Dispatch/
│       ├── 2025_PerfectSessionkWh_PerfectNumbEV_PerfectatArrival_baseline.csv
│       └── 2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival_baseline.csv
├── Driver_Table.csv
└── PowerFlex input for EV statistics to be plugged into master sheet_2024.csv
```

For the June-July study, the minimal bundle is approximately 140 MB:

- processed EV QC data: approximately 120 MB;
- June-July daily DA/FM LMP files: approximately 14 MB;
- cleared DA/RT AS files: approximately 1.2 MB;
- two baseline files: approximately 4 MB.

The raw PowerFlex interval file alone is approximately 378 MB and the
intermediate merged files exceed 500 MB each. They are unnecessary when the
processed QC CSV is provided.

Use a shared institutional drive, Box, OneDrive, Google Drive, or another
approved storage service for the data bundle. Preserve the directory names
exactly when extracting it into the Git clone.

## 4. Environment setup

Run all notebooks with the repository root as the working directory.

Recommended setup:

```bash
conda create -n upscaledev python=3.11 -y
conda activate upscaledev
python -m pip install jupyterlab numpy pandas scipy matplotlib seaborn plotly \
    holidays tqdm requests cvxpy gurobipy scs nbformat
```

The locally imported `forecast_ED_PD.py` currently imports additional ML
packages even though the ML forecast is disabled. Install these as well unless
that module is later made lazy:

```bash
python -m pip install scikit-learn kneed tensorflow keras joblib pytz
```

The CAISO downloader additionally needs:

```bash
python -m pip install gridstatus tabula-py tabulate termcolor
```

Gurobi must have a working license on the collaborator's machine. Verify before
running the MPC notebooks:

```bash
python -c "import gurobipy as gp; print(gp.gurobi.version())"
```

Then start Jupyter from the repository root:

```bash
cd /path/to/UPSCALeDEV_2024
jupyter lab
```

### 4.1 Environment actually used for the verified MPC smoke test

The current shrinking/rolling MPC notebooks were most recently verified with
the following local Jupyter runtime. This is a reproducibility snapshot, not a
requirement that every collaborator must use the newest version of every
package:

```text
Python                    3.13.0
JupyterLab                4.5.6
IPython                   9.13.0
ipykernel                 7.2.0
nbconvert                 7.17.1
nbformat                  5.10.4

numpy                     2.4.4
pandas                    3.0.2
scipy                     1.17.1
matplotlib                3.10.9
seaborn                   0.13.2
plotly                    6.7.0
holidays                  0.95
tqdm                      4.67.3
requests                  2.33.1

cvxpy                     1.8.2
gurobipy                  13.0.1
scs                       3.2.11

scikit-learn              1.8.0
kneed                     0.8.6
tensorflow                2.21.0
keras                     3.14.0
joblib                    1.5.3
pytz                      2026.1.post1
```

The rolling one-day 2 x 2 smoke test described in this repository completed
successfully in this environment.

For a fresh collaborator installation, Python 3.11 is still the conservative
recommendation because it has broad compatibility with CVXPY, Gurobi, and the
ML dependencies. The exact Python 3.13 snapshot above is useful when a result
must be reproduced as closely as possible.

### 4.2 Separate downloader environment

The repository-local `.conda` environment is different:

```text
Python                    3.11.13
numpy                     2.2.4
pandas                    2.2.3
matplotlib                3.10.1
requests                  2.32.3
gridstatus                0.29.1
tabula-py                 2.10.0
tabulate                  0.9.0
termcolor                 2.5.0
ipykernel                 6.30.1
```

It contains the CAISO downloader dependencies but currently does not contain
CVXPY. Therefore:

- use the main optimization environment for `upscaledev_baseline.ipynb`,
  `upscaledev_imp.ipynb`, `upscaledev_imp_rollingMPC.ipynb`, and plotting;
- use the downloader environment for `AS_download.ipynb` when needed;
- do not assume that selecting the notebook's historical
  `TotalEnergies2024` display name selects the correct interpreter;
- verify the active kernel with:

```python
import sys
print(sys.executable)
print(sys.version)
```

Also verify the two critical optimization packages inside that same notebook
kernel:

```python
import cvxpy as cp
import gurobipy as gp
print(cp.__version__)
print(gp.gurobi.version())
```

## 5. Required directory setup

Input directories are not all created by the main notebooks. Create them before
copying data:

```bash
mkdir -p 2025Data/EV_data
mkdir -p 2025Data/AS_DAM 2025Data/AS_RTM
mkdir -p 2025Data/LMP/2025/DA 2025Data/LMP/2025/RT 2025Data/LMP/2025/FM
mkdir -p Results/Dispatch Results/Plots
mkdir -p Results_Rolling/Dispatch Results_Rolling/Plots
mkdir -p Paper_Figures/financial_comparison
```

Most deeper output directories are created automatically with
`mkdir(parents=True, exist_ok=True)`.

## 6. Portability changes required on another computer

Several notebooks still contain absolute paths beginning with:

```text
/Users/admin/Desktop/EV_program/Total Transfer/PowerFlex_Code/UPSCALeDEV_2024
```

Before running on another computer, search for them:

```bash
rg -n "/Users/admin/" --glob "*.ipynb" --glob "*.py"
```

At minimum, update the project-root configuration in:

- `AS_download.ipynb`;
- `LMP_download.ipynb`;
- `upscaledev_EVdata_postprocessing.ipynb`;
- `upscaledev_baseline.ipynb`.

The two main MPC notebooks use relative paths for the active Perfect and
Persistence cases. Absolute ML paths are only reached when
`Fc_AtArrival == 'MLatArrival'`, which is not part of the current experiment.

## 7. Data preparation route A: use the preprocessed bundle

This is the recommended reproduction route.

1. Clone the GitHub repository.
2. Create the directories in Section 5.
3. Copy the preprocessed data bundle into the clone.
4. Confirm that the following six essential inputs exist:

```bash
test -f 2025Data/EV_data/UCSD_AllSites_Merge_PostProcessedSession_QC.csv
test -f 2025Data/AS_DAM/AS_price_2025_clear.csv
test -f 2025Data/AS_RTM/AS_price_2025_clear.csv
test -f Results/Dispatch/2025_PerfectSessionkWh_PerfectNumbEV_PerfectatArrival_baseline.csv
test -f Results/Dispatch/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival_baseline.csv
test -f 2025Data/LMP/2025/LMP_DA_2025_clean.csv
```

5. Confirm that one DA and one FM daily LMP file exist for every simulated day.
6. Skip the EV postprocessing, AS download, LMP download, and baseline notebooks.
7. Continue with Section 10.

## 8. Data preparation route B: rebuild from raw data

Use this route only when the collaborator has the raw PowerFlex exports and
wants to regenerate all processed inputs.

### 8.1 EV data

Run:

```text
upscaledev_EVdata_postprocessing.ipynb
```

Before running:

1. Replace its hardcoded `os.chdir(.../2025Data/EV_data)` path.
2. Put the raw PowerFlex session and interval exports in `2025Data/EV_data/`.
3. Add every raw filename to `EV_RAW_SESSION_FILES` and
   `EV_RAW_INTERVAL_FILES`.
4. Set `TheDate_Start` and the exclusive `TheDate_End`.
5. Confirm that
   `PowerFlex input for EV statistics to be plugged into master sheet_2024.csv`
   exists at the project root.

Required final output:

```text
2025Data/EV_data/UCSD_AllSites_Merge_PostProcessedSession_QC.csv
```

Inspect the printed QC counts and date range before proceeding.

### 8.2 CAISO ancillary-service prices

Run:

```text
AS_download.ipynb
```

Set `year`, `download_start`, and the exclusive `download_end`. Update all
hardcoded project paths. CAISO may return HTTP 429 when queried too quickly;
retain the notebook's retry/throttling behavior and avoid parallel downloads.

Required final outputs:

```text
2025Data/AS_DAM/AS_price_2025_clear.csv
2025Data/AS_RTM/AS_price_2025_clear.csv
```

### 8.3 CAISO LMP prices

Run:

```text
LMP_download.ipynb
```

Set `project_root`, `months_to_download`, `start_date`, `end_date`, and
`node_name`. The current study uses node `UCM_6_N001`.

The notebook downloads, unzips, renames by actual operating date, checks date
coverage, and creates 15-minute clean files.

Required outputs:

```text
2025Data/LMP/2025/DA/YYYYMMDD_LMP.csv
2025Data/LMP/2025/FM/YYYYMMDD_LMP.csv
2025Data/LMP/2025/LMP_DA_2025_clean.csv
2025Data/LMP/2025/LMP_FM_2025_clean.csv
```

The main optimization reads the daily DA/FM files. The annual clean files are
also used by the run preflight check and plotting workflow.

## 9. Generate the two initial baseline files

Skip this section when the two baseline CSVs were supplied in the data bundle.

Run:

```text
upscaledev_baseline.ipynb
```

The baseline notebook currently generates one forecast configuration at a
time. Run it twice:

1. `PerfectSessionkWh + PerfectNumbEV + PerfectatArrival`;
2. `PersistenceSessionkWh + PersistenceNumbEV + PerfectatArrival`.

For the June-July main study, the current baseline configuration uses February
through May/June historical operation before the main run. Verify
`start_RT_month` and the exclusive `target_RT_month` before execution.

Do not start the MPC notebooks until both files exist:

```text
Results/Dispatch/2025_PerfectSessionkWh_PerfectNumbEV_PerfectatArrival_baseline.csv
Results/Dispatch/2025_PersistenceSessionkWh_PersistenceNumbEV_PerfectatArrival_baseline.csv
```

## 10. Run the shrinking-horizon MPC

Open:

```text
upscaledev_imp.ipynb
```

Use the final user-control cell near the bottom:

```python
RUN_MONTHS_CONFIG = [6, 7]
RUN_DAYS_CONFIG = list(range(1, 31))
RUN_MODES = ['full', 'retail_only']
RUN_FORECAST_CONFIGS = [
    ('PerfectSessionkWh', 'PerfectNumbEV', 'PerfectatArrival'),
    ('PersistenceSessionkWh', 'PersistenceNumbEV', 'PerfectatArrival'),
]
PLOT_DAILY_6PANEL_DATES = 'all'
```

Run the notebook from top to bottom. This configuration runs all 30 days of
June and July 1-30, giving the same 60-day comparison window to all scenarios.
Run June and July together when the experiment requires continuous
executed-dispatch baseline learning across the two months.

Primary outputs:

```text
Results/Dispatch/*_implementation.csv
Results/Dispatch/*_daily_summary.csv
Results/Plots/Solver_RT_Choices/<scenario>/<date>/
Results/Plots/Cost/<forecast>/daily_financial_detail.csv
Results/Plots/Cost/<forecast>/monthly_financial_summary.csv
```

## 11. Run the rolling 24-hour MPC

Open:

```text
upscaledev_imp_rollingMPC.ipynb
```

Use the same month/day/mode/forecast controls. Its output root is:

```text
Results_Rolling/
```

The corrected Perfect EV forecast at RT step `k` now uses:

```text
[day 0, k:96] actual EV data + [day 1, 0:k] actual EV data
```

The EV column set is the union of day-0 and day-1 vehicles. A next-day session
is required to finish within the current horizon only when its departure is
inside that horizon; otherwise it is bounded by its known session energy but is
not forced to finish early.

Important boundary condition: a true rolling Perfect forecast requires EV data
through one calendar day after the final simulated day. The current QC file
ends on 2025-07-31, so the configured common study end date is July 30. If July
31 is added later, first obtain and process the August 1 EV export. Do not
silently interpret a missing next day as perfect information.

## 12. Validate every completed main run

For each implementation CSV:

- expected rows = number of simulated days x 96;
- `Interval start` must be unique and strictly cover the requested dates;
- no interval should contain NaN in the physical dispatch columns.

For each daily summary, group by `Date` and verify:

```text
sum(Real SessionkWh) == sum(Dispatched_base_withoutBESS)
```

Use tolerance `1e-4 kWh`.

For each daily financial table, verify:

```text
Total Revenue
= WM Revenue + TOU Cost + PD Cost + NCD Cost + EV Revenue
```

Allow `$0.01` for CSV rounding. Revenue is positive and cost is negative.

Also inspect notebook output for:

- `infeasible`, `infeasible_or_unbounded`, or unusable solver status;
- missing LMP/AS dates;
- Gurobi license errors;
- EV session-energy feasibility reconciliation warnings.

## 13. Generate comparison figures and tables

After both main notebooks finish, run:

```text
paper_financial_comparison_plots.ipynb
```

It reads the four `daily_financial_detail.csv` files from `Results/` and
`Results_Rolling/`. It generates full-period and month-specific comparison
figures and CSV summaries under:

```text
Paper_Figures/financial_comparison/
```

The notebook includes:

- daily financial-value distributions;
- Both-minus-Retail heatmaps;
- scenario subplots showing Retail-only and Both together;
- monthly and full-period financial summaries.

Run `timeline.ipynb` separately only when the market/MPC timeline figure needs
to be regenerated.

## 14. Common failure modes

| Symptom | Most likely cause | Action |
|---|---|---|
| EV QC CSV not found | Large data was not in Git | Copy the preprocessed data bundle |
| `pd.read_csv(''.join(filename_Input))` fails | Missing daily DA/FM LMP file | Check the exact `YYYYMMDD_LMP.csv` coverage |
| AS month is empty or `.dt` fails | Missing/incorrect cleared AS file | Re-run AS cleaning and verify `datetime` |
| Baseline CSV not found | Baseline outputs are ignored by Git | Copy or regenerate both baseline files |
| Import of `forecast_ED_PD` fails | ML dependencies are imported eagerly | Install the packages in Section 4 |
| Gurobi license error | Solver installed but not licensed | Configure an academic/WLS/local license |
| Rolling Perfect has zero post-midnight EVs | Missing day+1 EV data | Add the next calendar day to the QC CSV |
| Different results when months run separately | State/history window differs | Use the intended continuous run and identical initial conditions |
| Notebook writes to the wrong computer path | Hardcoded `/Users/admin/` path | Replace paths listed in Section 6 |

## 15. Git and data-sharing practice

Commit code, notebooks, documentation, and small configuration files to Git.
Do not commit raw PowerFlex exports, CAISO ZIP/XML files, generated dispatch
CSVs, or solver-output folders.

For each shared data bundle, include:

- a date/version label;
- the EV, AS, and LMP coverage dates;
- the CAISO node name;
- checksums for the six essential processed inputs;
- a note stating whether baseline CSVs are included.

This keeps Git lightweight while making every paper result traceable to one
specific external data snapshot.
