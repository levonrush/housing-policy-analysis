# Australian housing policy dataset and analysis pack

This pack sets up a reproducible analysis of Australian dwelling prices, wages,
negative gearing, the 1999 CGT discount, interest rates, migration, housing
credit, dwelling supply, the GFC, COVID and later tax reform.

## Files

- `housing_policy_analysis.ipynb` — main notebook for running the full pipeline
- `build_housing_policy_dataset_v2.py`
- `analyse_housing_policy_effects_v2.py`
- `plot_housing_policy_series_v2.py`
- `housing_policy_methodology_v2.md`
- `environment.yml` — conda environment specification

## Main outcome

```text
log_price_wage_ratio = log(real_dwelling_price_index / real_wage_index)
```

## Main mechanism tests

```text
investor_credit_share × post_1999_cgt
mortgage_rate × post_1999_cgt
```

## Reversal tests

The reform variables are parameterised because the final policy design and
legislative status must be confirmed before publication.

```text
investor_credit_share × post_reform_implementation
mortgage_rate × post_reform_implementation
time_after_reform_implementation
```

## Macro shock controls

```text
gfc_shock
post_gfc
time_after_gfc
covid_shock
post_covid
time_after_covid
```

## Setup

```bash
conda env create -f environment.yml
conda activate housing-policy
jupyter notebook
```

Open `housing_policy_analysis.ipynb` and run the cells in order:

1. **Build** — downloads RBA files and creates the template (skips if data already exists)
2. **Data prep** — loads and derives analysis variables
3. **Analysis** — runs all 6 model types and writes summaries to `outputs/model_summaries/`
4. **Plotting** — generates figures to `outputs/figures/`

To use from the command line instead:

```bash
python build_housing_policy_dataset_v2.py
# Fill data/processed/housing_policy_quarterly.csv from official ABS/RBA/ATO sources.

python analyse_housing_policy_effects_v2.py
python plot_housing_policy_series_v2.py
```
