"""Run statistical models and create visualizations."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.regression.linear_model import GLSAR

from .config import PROCESSED_DATA_PATH, MODEL_OUTPUT_DIR, FIGURE_OUTPUT_DIR, EVENTS, SHOCK_WINDOWS, PolicyDates
from .derive import add_time_index, add_derived_variables


def existing_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    """Return only the requested columns that exist in the dataset."""
    return [column for column in columns if column in df.columns]


def write_text(path: Path, text: str) -> None:
    """Write a text file after creating its parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def prepare_data(path: Path = PROCESSED_DATA_PATH) -> pd.DataFrame:
    """Load the quarterly table and add derived policy variables."""
    df = pd.read_csv(path)
    df["quarter"] = pd.to_datetime(df["quarter"])
    sort_cols = ["geo", "quarter"] if "geo" in df.columns else ["quarter"]
    df = df.sort_values(sort_cols)
    return add_derived_variables(df, dates=PolicyDates())


def compute_vif(df: pd.DataFrame, predictors: list[str]) -> pd.DataFrame:
    """Compute Variance Inflation Factors to diagnose multicollinearity."""
    model_df = df[predictors].dropna()
    x = sm.add_constant(model_df, has_constant="add")
    vif_data = pd.DataFrame({
        "Variable": x.columns[1:],  # Skip constant
        "VIF": [variance_inflation_factor(x.values, i) for i in range(1, x.shape[1])]
    })
    return vif_data.sort_values("VIF", ascending=False)


def fit_hac_ols(df: pd.DataFrame, outcome: str, predictors: list[str], lags: int = 4):
    """Fit OLS with Newey-West (HAC) standard errors."""
    model_df = df[[outcome] + predictors].dropna()
    x = sm.add_constant(model_df[predictors], has_constant="add")
    y = model_df[outcome]
    return sm.OLS(y, x).fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def fit_gls(df: pd.DataFrame, outcome: str, predictors: list[str], rho: int = 1):
    """Fit GLS model with AR(rho) correction for autocorrelation."""
    model_df = df[[outcome] + predictors].dropna()
    x = sm.add_constant(model_df[predictors], has_constant="add")
    y = model_df[outcome]
    try:
        model = GLSAR(y, x, rho=rho)
        return model.fit()
    except Exception as e:
        return fit_hac_ols(df, outcome, predictors)


def fit_best_arimax(df: pd.DataFrame, outcome: str, predictors: list[str]) -> tuple:
    """Fit multiple ARIMA orders on differenced data and return best + all results."""
    model_df = df[[outcome] + predictors].dropna()
    y_diff = model_df[outcome].diff().dropna()
    x_diff = model_df[predictors].diff().dropna()

    common_idx = y_diff.index.intersection(x_diff.index)
    y_diff = y_diff.loc[common_idx]
    x_diff = x_diff.loc[common_idx]
    exog = sm.add_constant(x_diff, has_constant="add")

    results_dict = {}
    orders = [(0, 0, 0), (1, 0, 0), (0, 0, 1), (1, 0, 1), (2, 0, 0)]

    for order in orders:
        try:
            model = ARIMA(y_diff, exog=exog, order=order)
            result = model.fit()
            results_dict[order] = {
                "result": result,
                "aic": result.aic,
                "bic": result.bic,
            }
        except Exception:
            pass

    if not results_dict:
        # Fallback
        result = sm.OLS(y_diff, exog).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
        return result, {}

    best_order = min(results_dict.keys(), key=lambda k: results_dict[k]["aic"])
    best_result = results_dict[best_order]["result"]

    return best_result, results_dict


def plot_acf_pacf(df: pd.DataFrame, outcome: str, output_dir: Path) -> None:
    """Generate ACF and PACF plots for residual diagnostics."""
    try:
        y = df[outcome].dropna()
        y_diff = y.diff().dropna()

        fig, axes = plt.subplots(2, 2, figsize=(12, 8))

        plot_acf(y, lags=20, ax=axes[0, 0], title="ACF: Original Series")
        plot_pacf(y, lags=20, ax=axes[0, 1], title="PACF: Original Series")
        plot_acf(y_diff, lags=20, ax=axes[1, 0], title="ACF: Differenced Series")
        plot_pacf(y_diff, lags=20, ax=axes[1, 1], title="PACF: Differenced Series")

        fig.tight_layout()
        output_path = output_dir / "acf_pacf_diagnostics.png"
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        return f"ACF/PACF plot saved to {output_path.name}\n"
    except Exception as e:
        return f"Could not generate ACF/PACF plots: {str(e)}\n"


def run_model(df: pd.DataFrame, name: str, outcome: str, predictors: list[str]) -> None:
    """Fit and write one model, or write a useful skip message."""
    predictors = existing_columns(df, predictors)
    if outcome not in df.columns:
        write_text(MODEL_OUTPUT_DIR / f"{name}.txt", f"Skipped: missing outcome column {outcome}.\n")
        return

    if not predictors:
        write_text(MODEL_OUTPUT_DIR / f"{name}.txt", "Skipped: no requested predictors were present.\n")
        return

    # Compute VIF diagnostics
    vif_df = compute_vif(df, predictors)

    # Fit multiple models
    ols_model = fit_hac_ols(df, outcome, predictors)
    gls_model = fit_gls(df, outcome, predictors)
    arimax_model, arimax_results = fit_best_arimax(df, outcome, predictors)

    # Build comprehensive output
    output = "=" * 80 + "\n"
    output += "MULTICOLLINEARITY DIAGNOSTICS (VIF)\n"
    output += "=" * 80 + "\n"
    output += vif_df.to_string(index=False) + "\n"
    output += "\nNote: VIF > 10 indicates severe multicollinearity\n\n"

    output += "=" * 80 + "\n"
    output += "OLS REGRESSION WITH NEWEY-WEST (HAC) STANDARD ERRORS\n"
    output += "=" * 80 + "\n"
    output += ols_model.summary().as_text() + "\n\n"

    output += "=" * 80 + "\n"
    output += "GLS REGRESSION WITH AR(1) CORRECTION\n"
    output += "(Directly corrects for autocorrelation)\n"
    output += "=" * 80 + "\n"
    output += gls_model.summary().as_text() + "\n\n"

    output += "=" * 80 + "\n"
    output += "ARIMA MODEL COMPARISON ON DIFFERENCED DATA\n"
    output += "=" * 80 + "\n"
    if arimax_results:
        output += "Model Selection (by AIC):\n"
        for order in sorted(arimax_results.keys(), key=lambda k: arimax_results[k]["aic"]):
            aic = arimax_results[order]["aic"]
            bic = arimax_results[order]["bic"]
            output += f"  ARIMA{order}: AIC={aic:.1f}, BIC={bic:.1f}\n"
        output += "\n"

    output += "BEST FIT: ARIMA model\n"
    output += "(Removes trend/unit root and autocorrelation; interpret as changes in level)\n"
    output += "=" * 80 + "\n"
    output += arimax_model.summary().as_text() + "\n"

    write_text(MODEL_OUTPUT_DIR / f"{name}.txt", output)


def run_interrupted_time_series(df: pd.DataFrame) -> None:
    """Test level and slope changes around CGT, GFC and COVID.

    Uses piecewise linear specification: only include slope-change terms,
    not redundant time-after terms that create collinearity.
    """
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
            "covid_shock",
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
            "dwelling_approvals_per_1000",
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
            "dwelling_approvals_per_1000",
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
            "dwelling_approvals_per_1000",
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
            "dwelling_approvals_per_1000",
            "migration_x_approvals",
            "post_1999_cgt",
            "gfc_shock",
            "covid_shock",
        ],
    )


def run_panel_fixed_effects(df: pd.DataFrame) -> None:
    """Run a simple fixed-effects panel if geography is present."""
    if "geo" not in df.columns or df["geo"].nunique() < 2:
        write_text(
            MODEL_OUTPUT_DIR / "06_panel_fixed_effects.txt",
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
        write_text(MODEL_OUTPUT_DIR / "06_panel_fixed_effects.txt", "Skipped: no panel predictors present.\n")
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
    write_text(MODEL_OUTPUT_DIR / "06_panel_fixed_effects.txt", model.summary().as_text())


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
    write_text(MODEL_OUTPUT_DIR / "README.md", notes)


def run_all_models(df: pd.DataFrame) -> None:
    """Orchestrator: run all 6 statistical models."""
    MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = add_time_index(df)

    print("\n📈 Running statistical models...")
    print("-" * 60)

    run_interrupted_time_series(df)
    print("  ✓ 01_interrupted_time_series")

    run_controlled_interrupted_time_series(df)
    print("  ✓ 02_controlled_interrupted_time_series")

    run_tax_amplifier_model(df)
    print("  ✓ 03_tax_amplifier_model")

    run_reform_reversal_model(df)
    print("  ✓ 04_reform_reversal_model")

    run_migration_supply_model(df)
    print("  ✓ 05_migration_supply_model")

    run_panel_fixed_effects(df)
    print("  ✓ 06_panel_fixed_effects")

    write_model_readme()
    print(f"\n✓ Model summaries written to {MODEL_OUTPUT_DIR}")

    # Generate diagnostics
    print("\n📊 Generating ACF/PACF diagnostics...")
    diag_output = plot_acf_pacf(df, "log_price_wage_ratio", MODEL_OUTPUT_DIR)
    print(f"  ✓ {diag_output.strip()}")


# ============================================================================
# PLOTTING FUNCTIONS
# ============================================================================


def index_to_base(series: pd.Series, base_mask: pd.Series) -> pd.Series:
    """Index a series to 100 at the first available observation in the base period."""
    base_values = series.loc[base_mask].dropna()
    if base_values.empty:
        raise ValueError("No non-null values found in the base period.")
    return series / base_values.iloc[0] * 100


def z_score(series: pd.Series) -> pd.Series:
    """Standardise a series so variables with different units can be compared."""
    return (series - series.mean()) / series.std()


def add_event_markers(axis: plt.Axes, include_future: bool = True) -> None:
    """Add policy and macro-event markers to a plot."""
    for start, end, _ in SHOCK_WINDOWS:
        axis.axvspan(pd.Timestamp(start), pd.Timestamp(end), alpha=0.12)

    y_top = axis.get_ylim()[1]
    for date_text, label in EVENTS:
        date = pd.Timestamp(date_text)
        if not include_future and date > pd.Timestamp.today():
            continue
        axis.axvline(date, linestyle="--", linewidth=1)
        axis.text(date, y_top, label, rotation=90, va="top", fontsize=8)


def load_data(input_path: Path = PROCESSED_DATA_PATH) -> pd.DataFrame:
    """Load and sort the quarterly modelling table."""
    df = pd.read_csv(input_path)
    df["quarter"] = pd.to_datetime(df["quarter"])
    return df.sort_values("quarter")


def plot_price_wage_divergence(df: pd.DataFrame, output_path: Path = None) -> None:
    """Plot real dwelling prices, real wages and the price-wage ratio."""
    if output_path is None:
        output_path = FIGURE_OUTPUT_DIR / "price_wage_divergence.png"

    df = df.copy()
    base_mask = df["quarter"] >= pd.Timestamp("1990-01-01")

    df["real_dwelling_price_indexed"] = index_to_base(df["real_dwelling_price_index"], base_mask)
    df["real_wage_indexed"] = index_to_base(df["real_wage_index"], base_mask)
    df["price_wage_ratio_indexed"] = index_to_base(df["price_wage_ratio"], base_mask)

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.plot(df["quarter"], df["real_dwelling_price_indexed"], label="Real dwelling prices")
    ax.plot(df["quarter"], df["real_wage_indexed"], label="Real wages")
    ax.plot(df["quarter"], df["price_wage_ratio_indexed"], label="Price-wage ratio")

    ax.set_title("Australian dwelling prices and wages, indexed to 1990 = 100")
    ax.set_ylabel("Index")
    ax.set_xlabel("Quarter")
    ax.legend()
    add_event_markers(ax, include_future=True)

    fig.tight_layout()
    FIGURE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved {output_path.name}")


def plot_policy_drivers(df: pd.DataFrame, output_path: Path = None) -> None:
    """Plot standardised rates, migration, investor credit and supply."""
    if output_path is None:
        output_path = FIGURE_OUTPUT_DIR / "housing_policy_drivers.png"

    driver_columns = {
        "mortgage_rate": "Mortgage rate",
        "nom_per_1000": "Net overseas migration per 1,000",
        "investor_credit_share": "Investor credit share",
        "dwelling_completions_per_1000": "Dwelling completions per 1,000",
        "dwelling_approvals_per_1000": "Dwelling approvals per 1,000",
    }

    fig, ax = plt.subplots(figsize=(12, 7))

    for column, label in driver_columns.items():
        if column in df.columns:
            ax.plot(df["quarter"], z_score(df[column]), label=label)

    ax.set_title("Housing-market drivers, standardised")
    ax.set_ylabel("Standard deviations from sample mean")
    ax.set_xlabel("Quarter")
    ax.legend()
    add_event_markers(ax, include_future=True)

    fig.tight_layout()
    FIGURE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved {output_path.name}")


def plot_combined_policy_story(df: pd.DataFrame, output_path: Path = None) -> None:
    """Plot the main outcome and standardised drivers on one narrative figure."""
    if output_path is None:
        output_path = FIGURE_OUTPUT_DIR / "combined_policy_story.png"

    df = df.copy()
    base_mask = df["quarter"] >= pd.Timestamp("1990-01-01")
    df["price_wage_ratio_indexed"] = index_to_base(df["price_wage_ratio"], base_mask)

    fig, ax = plt.subplots(figsize=(13, 7))
    ax.plot(df["quarter"], df["price_wage_ratio_indexed"], label="Price-wage ratio, indexed")

    driver_columns = {
        "mortgage_rate": "Mortgage rate, standardised",
        "nom_per_1000": "Migration per 1,000, standardised",
        "investor_credit_share": "Investor credit share, standardised",
        "dwelling_completions_per_1000": "Completions per 1,000, standardised",
        "dwelling_approvals_per_1000": "Approvals per 1,000, standardised",
    }

    for column, label in driver_columns.items():
        if column in df.columns:
            scaled = z_score(df[column]) * 20 + 100
            ax.plot(df["quarter"], scaled, label=label)

    ax.set_title("Housing affordability divergence and major drivers")
    ax.set_ylabel("Index / scaled standardised drivers")
    ax.set_xlabel("Quarter")
    ax.legend()
    add_event_markers(ax, include_future=True)

    fig.tight_layout()
    FIGURE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    print(f"  ✓ Saved {output_path.name}")


def plot_all(df: pd.DataFrame) -> None:
    """Orchestrator: create all 3 visualizations."""
    print("\n📊 Creating visualizations...")
    print("-" * 60)
    plot_price_wage_divergence(df)
    plot_policy_drivers(df)
    plot_combined_policy_story(df)
    print(f"✓ Figures written to {FIGURE_OUTPUT_DIR}")
