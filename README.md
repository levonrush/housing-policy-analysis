# Australian Housing Policy Analysis

A reproducible analysis of Australian dwelling prices, wages, and the 1999 CGT discount.

**Quick Start**: Clone → `conda activate housing-policy` → `jupyter notebook housing_policy_analysis.ipynb` → Run All

## Overview

This project analyzes whether the 1999 capital gains tax (CGT) discount changed dwelling price dynamics in Australia, relative to wage growth. The analysis runs interrupted time-series models with controls for interest rates, housing credit, migration, and dwelling supply.

**Key claim**: The 1999 CGT amplified investor demand, which transmitted into dwelling prices via two channels:
1. **Investor credit** — the share of housing loans going to investors increased
2. **Rate transmission** — mortgage rate changes more strongly affected prices post-1999

**Testing approach**: 
- 6 OLS models with Newey-West standard errors
- Controls for macro shocks (GFC, COVID)
- Hypothetical later reform to test reversibility
- Geographic variation (if data available)

## Repository Structure

```
housing-policy-analysis/
├── housing_policy_analysis.ipynb    ← Main entry point (run all cells)
├── environment.yml                   ← Conda environment
├── README.md                         ← This file
│
├── src/                              ← Python modules
│   ├── config.py                     ← Constants and configurations
│   ├── download.py                   ← Download RBA/ABS/ATO data
│   ├── extract.py                    ← Extract quarterly series from Excel
│   ├── derive.py                     ← Compute analysis variables
│   └── analyze.py                    ← Statistical models and plots
│
├── data/
│   ├── raw/                          ← Excel files (auto-downloaded)
│   └── processed/                    ← housing_policy_quarterly.csv (derived)
│
├── outputs/
│   ├── model_summaries/              ← 6 OLS models (txt) + README
│   └── figures/                      ← 3 PNG visualizations
│
└── docs/
    ├── methodology.md                ← Full methodology (9 hypotheses, 5 models)
    └── data_guide.md                 ← Data extraction and troubleshooting
```

## Setup

### 1. Environment

```bash
conda env create -f environment.yml
conda activate housing-policy
```

### 2. Run the notebook

```bash
cd /path/to/housing-policy-analysis
jupyter notebook housing_policy_analysis.ipynb
```

Click "Run All" cells or run section-by-section:

1. **Download** — Fetch RBA files, write ABS/ATO URLs
2. **Extract** — Read Excel, combine sources, derive variables
3. **Prepare** — Calculate real indices, policy dummies, interactions
4. **Models** — Run 6 OLS models with Newey-West SEs
5. **Visualize** — Plot price-wage divergence, drivers, and combined narrative

### 3. Output

- `outputs/model_summaries/` — Statistical results (txt files)
- `outputs/figures/` — Three PNG figures
- `data/processed/housing_policy_quarterly.csv` — Final dataset (42–50 columns)

## Data

### Sources (automated download)

**RBA** (direct URLs):
- Interest Rates (F01) → `cash_rate`
- Lending Rates (F05) → `mortgage_rate`
- Credit Aggregates (D02) → `housing_credit`, `investor_credit_share` *(needs series ID)*
- Consumer Price (G01) → `cpi_index`
- Household Finances (B21) → `household_debt_to_income` *(needs series ID)*

**ABS** (scrape or manual):
- Population/Migration (310101) → `population`, `net_overseas_migration` *(population needs verification)*
- Wage Price Index (634501) → `wage_index`
- Property Price Index (641601) → `dwelling_price_index`
- Building Activity (8752001) → `dwelling_completions`

### Derived Variables (automatic)

```
real_dwelling_price_index = dwelling_price_index / cpi_index * 100
real_wage_index = wage_index / cpi_index * 100
price_wage_ratio = real_dwelling_price_index / real_wage_index
log_price_wage_ratio = log(price_wage_ratio)  ← OUTCOME

nom_per_1000 = net_overseas_migration / population * 1000
dwelling_completions_per_1000 = dwelling_completions / population * 1000
housing_credit_growth = housing_credit.pct_change(4) * 100
investor_credit_share = investor_housing_credit / housing_credit * 100

post_1987_ng, post_1999_cgt, gfc_shock, covid_shock, reform_* ← DUMMIES

investor_x_post_1999 = investor_credit_share * post_1999_cgt
rate_x_post_1999 = mortgage_rate * post_1999_cgt
[+ 13 more interactions] ← MECHANISMS
```

## Statistical Models

| # | Name | Outcome | Tests |
|---|------|---------|-------|
| 1 | Interrupted Time Series | log_price_wage_ratio | Level/slope breaks at 1999, GFC, COVID |
| 2 | Controlled ITS | log_price_wage_ratio | Survives rates, credit, migration, supply controls |
| 3 | Tax Amplifier | log_price_wage_ratio | CGT changed investor & rate transmission |
| 4 | Reform Reversal | log_price_wage_ratio | Later reform weakens 1999 effects |
| 5 | Migration × Supply | log_price_wage_ratio | Migration matters more when supply tight |
| 6 | Panel Fixed Effects | log_price_wage_ratio | Geographic variation (if geo data available) |

**All models**: OLS with Newey-West (HAC) standard errors, 4-lag maximum.

## Key Results

The analysis tests 6 hypotheses. Main claim is supported if:

1. ✓ Post-1999 level or slope term is significant (Model 1)
2. ✓ Effect survives controls for major confounders (Model 2)
3. ✓ `investor_x_post_1999` interaction is positive (Model 3)
4. ✓ `rate_x_post_1999` interaction is negative (Model 3)
5. ✓ GFC and COVID do not absorb the 1999 effect (Model 1)
6. ✓ Later reform reverses the investor/rate channels (Model 4 opposite signs)

See `outputs/model_summaries/README.md` after running analysis.

## Figures

1. **Price-wage divergence** — Real dwelling prices, real wages, and ratio (indexed to 1990 = 100)
2. **Policy drivers** — Standardized mortgage rates, migration, investor credit, supply
3. **Combined narrative** — Price-wage ratio alongside scaled drivers

All figures include policy dates (vertical lines) and macro shock windows (shaded regions).

## Data Completeness

**Current**: 42–45 columns populated
**Target**: 50 columns

**Missing 5 columns** (require additional data):
- `household_debt_to_income` — RBA B21 (in config, needs Series ID verification)
- `established_dwelling` — ABS 6416.0 Table 2 (not yet downloaded)
- `established_x_reform_implementation` — derived from above

See `docs/data_guide.md` for how to add missing data.

## Methodology

Full methodology including:
- 9 research hypotheses (H1–H9)
- 5 model specifications with formal regressors
- Inference rules (what constitutes "support")

See `docs/methodology.md`.

## Troubleshooting

### Import errors

Make sure you're running the notebook from the project root directory.

### File not found errors

Check `data/raw/` — Excel files should be downloaded automatically. If missing:
1. Check network connection
2. Run `download_all(overwrite=True)` to retry
3. See `data/processed/source_pages.csv` for manual download links

### Series not found in Excel

Run `inspect_raw_file("filename.xlsx")` to see available Series IDs.

### Missing columns in dataset

See `docs/data_guide.md` — explains which columns require additional data sources and how to add them.

## Citation

If you use this analysis, please cite:

```
Author, Year. "Australian Housing Policy Analysis."
GitHub repository. https://github.com/...
```

## License

[Specify license]

## Contact

For questions or issues, open a GitHub issue or contact the maintainer.

---

**Last updated**: 2026-05-22  
**Python version**: 3.11+  
**Data coverage**: 1922 Q2 – 2026 Q4 (419 quarters)
