"""Analyse Australian housing policy effects.

Expected input:
    data/processed/housing_policy_quarterly.csv

The script runs:
- interrupted time-series models
- controlled interrupted time-series models
- tax-amplifier interaction models
- reform-reversal models
- migration/supply interaction models
- a simple fixed-effects panel if geography is present
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import statsmodels.api as sm

from build_housing_policy_dataset_v2 import PolicyDates, add_derived_variables


INPUT_PATH = Path("data/processed/housing_policy_quarterly.csv")
OUTPUT_DIR = Path("outputs/model_summaries")


def existing_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    """Return only the requested columns that exist in the dataset."""

    return [column for column in columns if column in df.columns]


def write_text(path: Path, text: str) -> None:
    """Write a text file after creating its parent directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def prepare_data(path: Path = INPUT_PATH) -> pd.DataFrame:
    """Load the quarterly table and add derived policy variables."""

    df = pd.read_csv(path)
    df["quarter"] = pd.to_datetime(df["quarter"])
    sort_cols = ["geo", "quarter"] if "geo" in df.columns else ["quarter"]
    df = df.sort_values(sort_cols)
    return add_derived_variables(df, dates=PolicyDates())


def add_time_index(df: pd.DataFrame) -> pd.DataFrame:
    """Add a sequential time index for interrupted time-series models."""

    out = df.copy()
    if "geo" in out.columns:
        out["time"] = out.groupby("geo").cumcount()
    else:
        out["time"] = range(len(out))
    return out


def fit_hac_ols(df: pd.DataFrame, outcome: str, predictors: list[str], lags: int = 4):
    """Fit OLS with Newey-West standard errors."""

    model_df = df[[outcome] + predictors].dropna()
    x = sm.add_constant(model_df[predictors], has_constant="add")
    y = model_df[outcome]
    return sm.OLS(y, x).fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def run_model(df: pd.DataFrame, name: str, outcome: str, predictors: list[str]) -> None:
    """Fit and write one model, or write a useful skip message."""

    predictors = existing_columns(df, predictors)
    if outcome not in df.columns:
        write_text(OUTPUT_DIR / f"{name}.txt", f"Skipped: missing outcome column {outcome}.\n")
        return

    if not predictors:
        write_text(OUTPUT_DIR / f"{name}.txt", "Skipped: no requested predictors were present.\n")
        return

    model = fit_hac_ols(df, outcome, predictors)
    write_text(OUTPUT_DIR / f"{name}.txt", model.summary().as_text())


def run_interrupted_time_series(df: pd.DataFrame) -> None:
    """Test level and slope changes around CGT, GFC and COVID."""

    run_model(
        df,
        "01_interrupted_time_series",
        "log_price_wage_ratio",
        [
            "time",
            "post_1999_cgt",
            "time_after_1999",
            "gfc_shock",
            "post_gfc",
            "time_after_gfc",
            "covid_shock",
            "post_covid",
            "time_after_covid",
        ],
    )


def run_controlled_interrupted_time_series(df: pd.DataFrame) -> None:
    """Test whether the post-1999 change survives major confounders."""

    run_model(
        df,
        "02_controlled_interrupted_time_series",
        "log_price_wage_ratio",
        [
            "time",
            "post_1999_cgt",
            "time_after_1999",
            "mortgage_rate",
            "housing_credit_growth",
            "investor_credit_share",
            "nom_per_1000",
            "dwelling_completions_per_1000",
            "gfc_shock",
            "post_gfc",
            "time_after_gfc",
            "covid_shock",
            "post_covid",
            "time_after_covid",
        ],
    )


def run_tax_amplifier_model(df: pd.DataFrame) -> None:
    """Test whether CGT changed the transmission of rates and investor credit."""

    run_model(
        df,
        "03_tax_amplifier_model",
        "log_price_wage_ratio",
        [
            "time",
            "mortgage_rate",
            "housing_credit_growth",
            "investor_credit_share",
            "nom_per_1000",
            "dwelling_completions_per_1000",
            "post_1999_cgt",
            "time_after_1999",
            "investor_x_post_1999",
            "rate_x_post_1999",
            "gfc_shock",
            "post_gfc",
            "rate_x_post_gfc",
            "credit_growth_x_post_gfc",
            "covid_shock",
            "post_covid",
            "rate_x_post_covid",
            "credit_growth_x_post_covid",
        ],
    )


def run_reform_reversal_model(df: pd.DataFrame) -> None:
    """Test whether a later reform weakens investor/rate transmission."""

    run_model(
        df,
        "04_reform_reversal_model",
        "log_price_wage_ratio",
        [
            "time",
            "mortgage_rate",
            "housing_credit_growth",
            "investor_credit_share",
            "nom_per_1000",
            "dwelling_completions_per_1000",
            "post_1999_cgt",
            "investor_x_post_1999",
            "rate_x_post_1999",
            "gfc_shock",
            "post_gfc",
            "covid_shock",
            "post_covid",
            "post_reform_announcement",
            "time_after_reform_announcement",
            "post_reform_implementation",
            "time_after_reform_implementation",
            "investor_x_reform_announcement",
            "rate_x_reform_announcement",
            "investor_x_reform_implementation",
            "rate_x_reform_implementation",
        ],
    )


def run_migration_supply_model(df: pd.DataFrame) -> None:
    """Test whether migration pressure is stronger when supply is low."""

    run_model(
        df,
        "05_migration_supply_model",
        "log_price_wage_ratio",
        [
            "time",
            "mortgage_rate",
            "housing_credit_growth",
            "nom_per_1000",
            "dwelling_completions_per_1000",
            "low_supply",
            "migration_x_low_supply",
            "post_1999_cgt",
            "gfc_shock",
            "covid_shock",
        ],
    )


def run_panel_fixed_effects(df: pd.DataFrame) -> None:
    """Run a simple fixed-effects panel if geography is present."""

    if "geo" not in df.columns or df["geo"].nunique() < 2:
        write_text(
            OUTPUT_DIR / "06_panel_fixed_effects.txt",
            "Skipped: panel model needs at least two geographies in the geo column.\n",
        )
        return

    model_df = df.copy()
    model_df["quarter_str"] = model_df["quarter"].dt.to_period("Q").astype(str)

    predictors = existing_columns(
        model_df,
        [
            "nom_per_1000",
            "dwelling_completions_per_1000",
            "investor_credit_share",
            "post_1999_cgt",
            "investor_x_post_1999",
            "gfc_shock",
            "covid_shock",
            "post_reform_implementation",
            "investor_x_reform_implementation",
        ],
    )

    if not predictors:
        write_text(OUTPUT_DIR / "06_panel_fixed_effects.txt", "Skipped: no panel predictors present.\n")
        return

    design = pd.concat(
        [
            model_df[predictors],
            pd.get_dummies(model_df["geo"], prefix="geo", drop_first=True),
            pd.get_dummies(model_df["quarter_str"], prefix="quarter", drop_first=True),
        ],
        axis=1,
    )

    clean_df = pd.concat([model_df["log_price_wage_ratio"], design], axis=1).dropna()
    x = sm.add_constant(clean_df.drop(columns=["log_price_wage_ratio"]), has_constant="add")
    y = clean_df["log_price_wage_ratio"]

    model = sm.OLS(y, x).fit(cov_type="HC1")
    write_text(OUTPUT_DIR / "06_panel_fixed_effects.txt", model.summary().as_text())


def write_model_readme() -> None:
    """Write interpretation notes for the generated model outputs."""

    notes = """# Model interpretation notes

The main historical claim is supported only if:

1. The 1999 CGT level or slope terms are meaningful.
2. The result does not disappear after adding mortgage rates, credit, migration and dwelling completions.
3. `investor_x_post_1999` is positive.
4. `rate_x_post_1999` is negative.
5. GFC and COVID terms do not fully absorb the 1999 result.
6. A later reform, once legislated and observed, shows the opposite sign:
   - weaker investor-credit transmission
   - weaker rate transmission
   - lower post-reform price-wage slope

Grandfathering, anticipation, rate changes, migration and limited post-reform
observations can all mute the measured reform effect.
"""
    write_text(OUTPUT_DIR / "README.md", notes)


def main() -> None:
    """Run all available models and write summaries."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = add_time_index(prepare_data(INPUT_PATH))

    run_interrupted_time_series(df)
    run_controlled_interrupted_time_series(df)
    run_tax_amplifier_model(df)
    run_reform_reversal_model(df)
    run_migration_supply_model(df)
    run_panel_fixed_effects(df)
    write_model_readme()

    print(f"Model summaries written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
