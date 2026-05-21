"""Build a quarterly Australian housing policy dataset.

The script creates a conservative scaffold for a publishable housing-policy
analysis. It downloads stable RBA files, writes official source pages for manual
ABS/ATO pulls, and defines the modelling variables, policy events and derived
features used by the analysis scripts.

Run in an internet-enabled Python environment, preferably Azure ML.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import requests


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


@dataclass(frozen=True)
class SourceFile:
    """A source file that can be downloaded directly."""

    name: str
    url: str
    filename: str


@dataclass(frozen=True)
class PolicyDates:
    """Policy and macro-event dates used to generate intervention variables.

    Dates are quarter-end timestamps so joins and event dummies behave cleanly
    on quarterly data.

    The reform dates are parameterised. Check final legislation before using
    reform variables in a publishable model.
    """

    negative_gearing_restored: str = "1987-09-30"
    cgt_discount: str = "1999-12-31"
    gfc_start: str = "2008-09-30"
    gfc_end: str = "2009-06-30"
    covid_start: str = "2020-03-31"
    covid_end: str = "2021-12-31"
    covid_post_start: str = "2022-03-31"
    reform_announcement: str | None = "2026-06-30"
    reform_implementation: str | None = "2027-09-30"


RBA_FILES = [
    SourceFile(
        name="rba_f01_interest_rates_money_market",
        url="https://www.rba.gov.au/statistics/tables/xls/f01hist.xlsx",
        filename="rba_f01_interest_rates_money_market.xlsx",
    ),
    SourceFile(
        name="rba_f05_indicator_lending_rates",
        url="https://www.rba.gov.au/statistics/tables/xls/f05hist.xlsx",
        filename="rba_f05_indicator_lending_rates.xlsx",
    ),
    SourceFile(
        name="rba_d02_lending_credit_aggregates",
        url="https://www.rba.gov.au/statistics/tables/xls/d02hist.xlsx",
        filename="rba_d02_lending_credit_aggregates.xlsx",
    ),
    SourceFile(
        name="rba_b21_household_finances",
        url="https://www.rba.gov.au/statistics/tables/xls/b21hist.xlsx",
        filename="rba_b21_household_finances.xlsx",
    ),
    SourceFile(
        name="rba_g01_consumer_price_inflation",
        url="https://www.rba.gov.au/statistics/tables/xls/g01hist.xlsx",
        filename="rba_g01_consumer_price_inflation.xlsx",
    ),
]

SOURCE_PAGES = {
    "abs_total_value_dwellings": "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/total-value-dwellings/latest-release",
    "abs_residential_property_price_indexes_archived": "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/residential-property-price-indexes-eight-capital-cities/latest-release",
    "abs_wage_price_index": "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/wage-price-index-australia/latest-release",
    "abs_average_weekly_earnings": "https://www.abs.gov.au/statistics/labour/earnings-and-working-conditions/average-weekly-earnings-australia/latest-release",
    "abs_cpi": "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/latest-release",
    "abs_population_nom": "https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/latest-release",
    "abs_building_activity": "https://www.abs.gov.au/statistics/industry/building-and-construction/building-activity-australia/latest-release",
    "abs_lending_indicators": "https://www.abs.gov.au/statistics/economy/finance/lending-indicators/latest-release",
    "ato_taxation_statistics": "https://www.ato.gov.au/about-ato/research-and-statistics/in-detail/taxation-statistics/taxation-statistics-previous-editions",
}


def ensure_dirs() -> None:
    """Create data folders before writing raw files or processed outputs."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def download_file(source: SourceFile, overwrite: bool = False) -> Path | None:
    """Download a source file with a stable publisher URL. Returns None if unavailable."""

    out_path = RAW_DIR / source.filename
    if out_path.exists() and not overwrite:
        return out_path

    try:
        response = requests.get(source.url, timeout=60)
        response.raise_for_status()
        out_path.write_bytes(response.content)
        return out_path
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not download {source.name} from {source.url}: {e}")
        return None


def download_rba_files(overwrite: bool = False) -> list[Path]:
    """Download the RBA files used for rates, credit, CPI and debt controls."""

    results = [download_file(source, overwrite=overwrite) for source in RBA_FILES]
    return [path for path in results if path is not None]


def write_source_pages() -> Path:
    """Write ABS/ATO source landing pages for manual and auditable downloads."""

    path = PROCESSED_DIR / "source_pages.csv"
    rows = [{"source_name": key, "url": value} for key, value in SOURCE_PAGES.items()]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def to_quarter(date_series: pd.Series) -> pd.Series:
    """Convert date-like values to quarter-end timestamps."""

    return pd.to_datetime(date_series).dt.to_period("Q").dt.to_timestamp("Q")


def quarterly_average(df: pd.DataFrame, date_col: str, value_cols: Iterable[str]) -> pd.DataFrame:
    """Convert higher-frequency observations to quarterly averages."""

    out = df.copy()
    out["quarter"] = to_quarter(out[date_col])
    return out.groupby("quarter", as_index=False)[list(value_cols)].mean()


def quarter_counter(quarter: pd.Series, start_date: str | None) -> pd.Series:
    """Count quarters since an event, returning zero before the event."""

    if start_date is None:
        return pd.Series(0, index=quarter.index)

    start = pd.Timestamp(start_date)
    quarter_period = pd.to_datetime(quarter).dt.to_period("Q")
    start_period = start.to_period("Q")
    counts = (quarter_period - start_period).apply(lambda x: x.n)
    return counts.clip(lower=0)


def add_event_dummies(df: pd.DataFrame, dates: PolicyDates = PolicyDates()) -> pd.DataFrame:
    """Add tax, GFC, COVID and reform intervention variables."""

    out = df.copy()
    out["quarter"] = pd.to_datetime(out["quarter"])

    out["post_1987_ng"] = (out["quarter"] >= pd.Timestamp(dates.negative_gearing_restored)).astype(int)
    out["post_1999_cgt"] = (out["quarter"] >= pd.Timestamp(dates.cgt_discount)).astype(int)
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
    out["post_covid"] = (out["quarter"] >= pd.Timestamp(dates.covid_post_start)).astype(int)
    out["time_after_covid"] = quarter_counter(out["quarter"], dates.covid_post_start)

    out["post_reform_announcement"] = 0
    out["time_after_reform_announcement"] = 0
    if dates.reform_announcement is not None:
        out["post_reform_announcement"] = (
            out["quarter"] >= pd.Timestamp(dates.reform_announcement)
        ).astype(int)
        out["time_after_reform_announcement"] = quarter_counter(out["quarter"], dates.reform_announcement)

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

    if "investor_credit_share" in out.columns:
        out["investor_x_post_1999"] = out["investor_credit_share"] * out["post_1999_cgt"]
        out["investor_x_post_gfc"] = out["investor_credit_share"] * out["post_gfc"]
        out["investor_x_post_covid"] = out["investor_credit_share"] * out["post_covid"]
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
        out["rate_x_reform_announcement"] = out["mortgage_rate"] * out["post_reform_announcement"]
        out["rate_x_reform_implementation"] = (
            out["mortgage_rate"] * out["post_reform_implementation"]
        )

    if "housing_credit_growth" in out.columns:
        out["credit_growth_x_post_gfc"] = out["housing_credit_growth"] * out["post_gfc"]
        out["credit_growth_x_post_covid"] = out["housing_credit_growth"] * out["post_covid"]

    if {"nom_per_1000", "dwelling_completions_per_1000"}.issubset(out.columns):
        median_supply = out["dwelling_completions_per_1000"].median()
        out["low_supply"] = (out["dwelling_completions_per_1000"] < median_supply).astype(int)
        out["migration_x_low_supply"] = out["nom_per_1000"] * out["low_supply"]

    if {"established_dwelling", "post_reform_implementation"}.issubset(out.columns):
        out["established_x_reform_implementation"] = (
            out["established_dwelling"] * out["post_reform_implementation"]
        )

    return out


def add_derived_variables(df: pd.DataFrame, dates: PolicyDates = PolicyDates()) -> pd.DataFrame:
    """Add affordability, scale and event variables after source tables are joined."""

    out = df.copy()
    out["quarter"] = pd.to_datetime(out["quarter"])

    if {"dwelling_price_index", "cpi_index"}.issubset(out.columns):
        out["real_dwelling_price_index"] = out["dwelling_price_index"] / out["cpi_index"] * 100

    if {"wage_index", "cpi_index"}.issubset(out.columns):
        out["real_wage_index"] = out["wage_index"] / out["cpi_index"] * 100

    if {"real_dwelling_price_index", "real_wage_index"}.issubset(out.columns):
        out["price_wage_ratio"] = out["real_dwelling_price_index"] / out["real_wage_index"]
        out["log_price_wage_ratio"] = np.log(out["price_wage_ratio"])

    if {"net_overseas_migration", "population"}.issubset(out.columns):
        out["nom_per_1000"] = out["net_overseas_migration"] / out["population"] * 1000

    if {"dwelling_completions", "population"}.issubset(out.columns):
        out["dwelling_completions_per_1000"] = out["dwelling_completions"] / out["population"] * 1000

    if "housing_credit" in out.columns:
        out["housing_credit_growth"] = out["housing_credit"].pct_change(4) * 100

    out = add_event_dummies(out, dates=dates)
    return add_interactions(out)


def build_empty_analysis_template() -> Path:
    """Create the expected final table structure before source loaders are filled."""

    columns = [
        "quarter",
        "geo",
        "dwelling_type",
        "established_dwelling",
        "dwelling_price_index",
        "cpi_index",
        "real_dwelling_price_index",
        "wage_index",
        "real_wage_index",
        "price_wage_ratio",
        "log_price_wage_ratio",
        "mortgage_rate",
        "cash_rate",
        "housing_credit",
        "housing_credit_growth",
        "investor_credit_share",
        "net_overseas_migration",
        "population",
        "nom_per_1000",
        "population_growth",
        "dwelling_completions",
        "dwelling_completions_per_1000",
        "household_debt_to_income",
        "post_1987_ng",
        "post_1999_cgt",
        "time_after_1999",
        "gfc_shock",
        "post_gfc",
        "time_after_gfc",
        "covid_shock",
        "post_covid",
        "time_after_covid",
        "post_reform_announcement",
        "time_after_reform_announcement",
        "post_reform_implementation",
        "time_after_reform_implementation",
        "investor_x_post_1999",
        "rate_x_post_1999",
        "investor_x_post_gfc",
        "rate_x_post_gfc",
        "credit_growth_x_post_gfc",
        "investor_x_post_covid",
        "rate_x_post_covid",
        "credit_growth_x_post_covid",
        "investor_x_reform_announcement",
        "rate_x_reform_announcement",
        "investor_x_reform_implementation",
        "rate_x_reform_implementation",
        "migration_x_low_supply",
        "established_x_reform_implementation",
    ]

    path = PROCESSED_DIR / "housing_policy_quarterly_template.csv"
    pd.DataFrame(columns=columns).to_csv(path, index=False)
    return path


def main() -> None:
    """Run the reproducible setup step."""

    ensure_dirs()
    downloaded = download_rba_files(overwrite=False)
    source_page_path = write_source_pages()
    template_path = build_empty_analysis_template()

    print("Downloaded RBA files:")
    for path in downloaded:
        print(f"- {path}")

    print(f"\nABS/ATO source pages written to: {source_page_path}")
    print(f"Analysis template written to: {template_path}")


if __name__ == "__main__":
    main()
