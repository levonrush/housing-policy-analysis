"""Derive variables and compute analysis features from raw data."""

from typing import Iterable, Optional

import numpy as np
import pandas as pd

from .config import PolicyDates, TEMPLATE_COLUMNS


def to_quarter(date_series: pd.Series) -> pd.Series:
    """Convert date-like values to quarter-end timestamps."""
    return pd.to_datetime(date_series).dt.to_period("Q").dt.to_timestamp("Q")


def quarterly_average(
    df: pd.DataFrame, date_col: str, value_cols: Iterable[str]
) -> pd.DataFrame:
    """Convert higher-frequency observations to quarterly averages."""
    out = df.copy()
    out["quarter"] = to_quarter(out[date_col])
    return out.groupby("quarter", as_index=False)[list(value_cols)].mean()


def quarter_counter(quarter: pd.Series, start_date: Optional[str]) -> pd.Series:
    """Count quarters since an event, returning zero before the event."""
    if start_date is None:
        return pd.Series(0, index=quarter.index)

    start = pd.Timestamp(start_date)
    quarter_period = pd.to_datetime(quarter).dt.to_period("Q")
    start_period = start.to_period("Q")
    counts = (quarter_period - start_period).apply(lambda x: x.n)
    return counts.clip(lower=0)


def add_derived_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Add numeric derivations (real indices, affordability, per-capita measures)."""
    out = df.copy()
    out["quarter"] = pd.to_datetime(out["quarter"])

    # Ensure numeric columns are float (handle Excel object dtype from imports)
    numeric_cols = [
        "dwelling_price_index", "wage_index", "cpi_index",
        "housing_credit", "owner_occupier_credit", "investor_housing_credit",
        "dwelling_completions", "dwelling_approvals",
        "population", "net_overseas_migration",
        "mortgage_rate", "cash_rate",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    # Real indices (deflate by CPI)
    if {"dwelling_price_index", "cpi_index"}.issubset(out.columns):
        out["real_dwelling_price_index"] = (
            out["dwelling_price_index"] / out["cpi_index"] * 100
        )

    if {"wage_index", "cpi_index"}.issubset(out.columns):
        out["real_wage_index"] = out["wage_index"] / out["cpi_index"] * 100

    # Affordability ratio
    if {"real_dwelling_price_index", "real_wage_index"}.issubset(out.columns):
        out["price_wage_ratio"] = (
            out["real_dwelling_price_index"] / out["real_wage_index"]
        )
        out["log_price_wage_ratio"] = np.log(out["price_wage_ratio"])

    # Housing credit: combine owner-occupier and investor
    if {"owner_occupier_credit", "investor_housing_credit"}.issubset(out.columns):
        out["housing_credit"] = (
            out["owner_occupier_credit"] + out["investor_housing_credit"]
        )
        out["investor_credit_share"] = (
            out["investor_housing_credit"] / out["housing_credit"] * 100
        )

    # Growth rates and per-capita measures
    if "housing_credit" in out.columns:
        out["housing_credit_growth"] = out["housing_credit"].pct_change(4) * 100

    if "population" in out.columns:
        out["population_growth"] = out["population"].pct_change(4) * 100

    if {"net_overseas_migration", "population"}.issubset(out.columns):
        out["nom_per_1000"] = out["net_overseas_migration"] / out["population"] * 1000

    if {"dwelling_completions", "population"}.issubset(out.columns):
        out["dwelling_completions_per_1000"] = (
            out["dwelling_completions"] / out["population"] * 1000
        )

    if {"dwelling_approvals", "population"}.issubset(out.columns):
        out["dwelling_approvals_per_1000"] = (
            out["dwelling_approvals"] / out["population"] * 1000
        )

    # Add default values for geo and dwelling_type if absent
    if "geo" not in out.columns:
        out["geo"] = "National"

    if "dwelling_type" not in out.columns:
        out["dwelling_type"] = "All dwellings"

    return out


def add_event_dummies(
    df: pd.DataFrame, dates: PolicyDates = PolicyDates()
) -> pd.DataFrame:
    """Add tax, GFC, COVID and reform intervention variables."""
    out = df.copy()
    out["quarter"] = pd.to_datetime(out["quarter"])

    out["post_1987_ng"] = (
        out["quarter"] >= pd.Timestamp(dates.negative_gearing_restored)
    ).astype(int)
    out["post_1999_cgt"] = (
        out["quarter"] >= pd.Timestamp(dates.cgt_discount)
    ).astype(int)
    out["time_after_1999"] = quarter_counter(out["quarter"], dates.cgt_discount)

    out["gfc_shock"] = (
        (out["quarter"] >= pd.Timestamp(dates.gfc_start))
        & (out["quarter"] <= pd.Timestamp(dates.gfc_end))
    ).astype(int)
    out["post_gfc"] = (out["quarter"] > pd.Timestamp(dates.gfc_end)).astype(int)
    out["time_after_gfc"] = quarter_counter(out["quarter"], dates.gfc_end)

    out["covid_shock"] = (
        (out["quarter"] >= pd.Timestamp(dates.covid_start))
        & (out["quarter"] <= pd.Timestamp(dates.covid_end))
    ).astype(int)
    out["post_covid"] = (
        out["quarter"] >= pd.Timestamp(dates.covid_post_start)
    ).astype(int)
    out["time_after_covid"] = quarter_counter(out["quarter"], dates.covid_post_start)

    # Reform announcement and implementation (handle None dates correctly)
    out["post_reform_announcement"] = 0
    out["time_after_reform_announcement"] = 0
    if dates.reform_announcement is not None:
        out["post_reform_announcement"] = (
            out["quarter"] >= pd.Timestamp(dates.reform_announcement)
        ).astype(int)
        out["time_after_reform_announcement"] = quarter_counter(
            out["quarter"], dates.reform_announcement
        )

    out["post_reform_implementation"] = 0
    out["time_after_reform_implementation"] = 0
    if dates.reform_implementation is not None:
        out["post_reform_implementation"] = (
            out["quarter"] >= pd.Timestamp(dates.reform_implementation)
        ).astype(int)
        out["time_after_reform_implementation"] = quarter_counter(
            out["quarter"], dates.reform_implementation
        )

    return out


def add_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """Add mechanism terms used to test policy transmission."""
    out = df.copy()

    if "investor_credit_share" in out.columns and "post_1999_cgt" in out.columns:
        out["investor_x_post_1999"] = (
            out["investor_credit_share"] * out["post_1999_cgt"]
        )

    if "investor_credit_share" in out.columns and "post_gfc" in out.columns:
        out["investor_x_post_gfc"] = out["investor_credit_share"] * out["post_gfc"]

    if "investor_credit_share" in out.columns and "post_covid" in out.columns:
        out["investor_x_post_covid"] = (
            out["investor_credit_share"] * out["post_covid"]
        )

    if "investor_credit_share" in out.columns:
        out["investor_x_reform_announcement"] = (
            out["investor_credit_share"] * out["post_reform_announcement"]
        )
        out["investor_x_reform_implementation"] = (
            out["investor_credit_share"] * out["post_reform_implementation"]
        )

    if "mortgage_rate" in out.columns:
        out["rate_x_post_1999"] = out["mortgage_rate"] * out["post_1999_cgt"]
        out["rate_x_post_gfc"] = out["mortgage_rate"] * out["post_gfc"]
        out["rate_x_post_covid"] = out["mortgage_rate"] * out["post_covid"]
        out["rate_x_reform_announcement"] = (
            out["mortgage_rate"] * out["post_reform_announcement"]
        )
        out["rate_x_reform_implementation"] = (
            out["mortgage_rate"] * out["post_reform_implementation"]
        )

    if "housing_credit_growth" in out.columns:
        out["credit_growth_x_post_gfc"] = (
            out["housing_credit_growth"] * out["post_gfc"]
        )
        out["credit_growth_x_post_covid"] = (
            out["housing_credit_growth"] * out["post_covid"]
        )

    if {"nom_per_1000", "dwelling_completions_per_1000"}.issubset(out.columns):
        median_supply = out["dwelling_completions_per_1000"].median()
        out["low_supply"] = (
            out["dwelling_completions_per_1000"] < median_supply
        ).astype(int)
        out["migration_x_low_supply"] = out["nom_per_1000"] * out["low_supply"]

    if {"nom_per_1000", "dwelling_approvals_per_1000"}.issubset(out.columns):
        out["migration_x_approvals"] = (
            out["nom_per_1000"] * out["dwelling_approvals_per_1000"]
        )

    if {"established_dwelling", "post_reform_implementation"}.issubset(out.columns):
        out["established_x_reform_implementation"] = (
            out["established_dwelling"] * out["post_reform_implementation"]
        )

    return out


def add_derived_variables(
    df: pd.DataFrame, dates: PolicyDates = PolicyDates()
) -> pd.DataFrame:
    """Top-level orchestrator: add all derived variables in order."""
    out = add_derived_numeric(df)
    out = add_event_dummies(out, dates=dates)
    out = add_interactions(out)
    return out


def add_time_index(df: pd.DataFrame) -> pd.DataFrame:
    """Add sequential time index for time-series models."""
    out = df.copy()
    out["quarter"] = pd.to_datetime(out["quarter"])

    if "geo" in out.columns and out["geo"].nunique() > 1:
        out["time"] = out.groupby("geo").cumcount()
    else:
        out["time"] = range(len(out))

    return out


def reorder_columns(
    df: pd.DataFrame, template_cols: list[str] = TEMPLATE_COLUMNS
) -> pd.DataFrame:
    """Reorder columns to match the template structure."""
    cols_to_keep = [col for col in template_cols if col in df.columns]
    return df[cols_to_keep]


def build_empty_analysis_template(output_path=None) -> None:
    """Create the expected final table structure before source loaders are filled."""
    from .config import PROCESSED_DATA_DIR, TEMPLATE_PATH

    path = output_path or TEMPLATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=TEMPLATE_COLUMNS).to_csv(path, index=False)
    return path
