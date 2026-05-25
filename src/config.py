"""Configuration for housing policy analysis project."""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# Directory paths (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "model_summaries"
FIGURE_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "figures"

# Data file paths
PROCESSED_DATA_PATH = PROCESSED_DATA_DIR / "housing_policy_quarterly.csv"
SOURCE_PAGES_PATH = PROCESSED_DATA_DIR / "source_pages.csv"
TEMPLATE_PATH = PROCESSED_DATA_DIR / "housing_policy_quarterly_template.csv"


@dataclass(frozen=True)
class SourceFile:
    """A source file that can be downloaded directly."""

    name: str
    url: str
    filename: str


@dataclass(frozen=True)
class ExtractConfig:
    """Configuration for extracting a data series from an Excel file."""

    filename: str
    sheet: str | int
    header_row: int
    date_column: int | str
    value_columns: dict[str, str]
    data_start_row: int = 10
    agg_method: str = "mean"


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
    reform_announcement: Optional[str] = "2026-06-30"
    reform_implementation: Optional[str] = "2027-09-30"


# Policy and macro events for visualization
EVENTS = [
    ("1987-09-30", "Negative gearing restored"),
    ("1999-12-31", "CGT discount"),
    ("2008-09-30", "GFC"),
    ("2020-03-31", "COVID"),
    ("2026-06-30", "Reform announcement"),
    ("2027-09-30", "Reform implementation"),
]

# Shock windows for highlighting on plots
SHOCK_WINDOWS = [
    ("2008-09-30", "2009-06-30", "GFC window"),
    ("2020-03-31", "2021-12-31", "COVID window"),
]

# Base period for indexing price-wage figures
BASE_PERIOD_START = "1990-01-01"


# RBA files to download
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

# ABS and ATO source pages for manual downloads
SOURCE_PAGES = {
    "abs_total_value_dwellings": "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/total-value-dwellings/latest-release",
    "abs_residential_property_price_indexes": "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/residential-property-price-indexes-eight-capital-cities/latest-release",
    "abs_wage_price_index": "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/wage-price-index-australia/latest-release",
    "abs_average_weekly_earnings": "https://www.abs.gov.au/statistics/labour/earnings-and-working-conditions/average-weekly-earnings-australia/latest-release",
    "abs_cpi": "https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/consumer-price-index-australia/latest-release",
    "abs_population_nom": "https://www.abs.gov.au/statistics/people/population/national-state-and-territory-population/latest-release",
    "abs_building_activity": "https://www.abs.gov.au/statistics/industry/building-and-construction/building-activity-australia/latest-release",
    "abs_building_approvals": "https://www.abs.gov.au/statistics/industry/building-and-construction/building-approvals-australia/latest-release",
    "abs_lending_indicators": "https://www.abs.gov.au/statistics/economy/finance/lending-indicators/latest-release",
    "ato_taxation_statistics": "https://www.ato.gov.au/about-ato/research-and-statistics/in-detail/taxation-statistics/taxation-statistics-previous-editions",
}

# Configuration for extracting data from each source file.
# ABS files use load_abs_file() - reads Series IDs from row 9 to locate data
# RBA files use load_rba_file() - reads Series IDs from row 10 to locate data

EXTRACT_CONFIGS = [
    # ABS 310101 - Population and Migration
    {
        "type": "abs",
        "config": ExtractConfig(
            filename="310101.xlsx",
            sheet="Data1",
            header_row=0,
            date_column=0,
            value_columns={
                "population": "A2133251W",  # Estimated Resident Population
                "net_overseas_migration": "A2133254C",  # Net Overseas Migration
            },
        ),
    },
    # ABS 634501 - Wage Price Index
    {
        "type": "abs",
        "config": ExtractConfig(
            filename="634501.xlsx",
            sheet="Data1",
            header_row=0,
            date_column=0,
            value_columns={
                "wage_index": "A2603039T",  # Quarterly Index - Total hourly rates of pay
            },
        ),
    },
    # ABS 641601 - Residential Property Price Index
    {
        "type": "abs",
        "config": ExtractConfig(
            filename="641601.xlsx",
            sheet="Data1",
            header_row=0,
            date_column=0,
            value_columns={
                "dwelling_price_index": "A83728455L",  # Weighted average of capital cities
            },
        ),
    },
    # ABS 8752001 - Building Activity (dwelling completions)
    {
        "type": "abs",
        "config": ExtractConfig(
            filename="8752001.xlsx",
            sheet="Data1",
            header_row=0,
            date_column=0,
            value_columns={
                "dwelling_completions": "A83776195X",  # Value of work done - Dwelling construction
            },
        ),
    },
    # ABS 8731.0 - Building Approvals (monthly unit counts → quarterly sum)
    # Note: Using NSW Total Sectors (Table 01, A418511A) as proxy for national trend
    {
        "type": "abs",
        "config": ExtractConfig(
            filename="abs_abs_building_approvals.xlsx",
            sheet="Data1",
            header_row=0,
            date_column=0,
            value_columns={
                "dwelling_approvals": "A418511A",  # NSW; Houses; Total Sectors; Original (seasonally unadjusted)
            },
            data_start_row=10,
            agg_method="sum",
        ),
    },
    # RBA F01 - Interest Rates (Cash Rate)
    {
        "type": "rba",
        "config": ExtractConfig(
            filename="rba_f01_interest_rates_money_market.xlsx",
            sheet="Data",
            header_row=0,
            date_column=0,
            value_columns={
                "cash_rate": "FIRMMCRT",  # Cash Rate Target
            },
        ),
    },
    # RBA F05 - Lending Rates (Mortgage Rate)
    {
        "type": "rba",
        "config": ExtractConfig(
            filename="rba_f05_indicator_lending_rates.xlsx",
            sheet="Data",
            header_row=0,
            date_column=0,
            value_columns={
                "mortgage_rate": "FILRHLBVS",  # Housing loans; Banks; Variable; Standard
            },
        ),
    },
    # RBA D02 - Lending and Credit (Housing)
    {
        "type": "rba",
        "config": ExtractConfig(
            filename="rba_d02_lending_credit_aggregates.xlsx",
            sheet="Data",
            header_row=0,
            date_column=0,
            value_columns={
                "owner_occupier_credit": "DLCACOHN",  # Owner-occupier housing credit
                "investor_housing_credit": "DLCACIHN",  # Investor housing credit
            },
        ),
    },
    # RBA G01 - Consumer Price Inflation (quarterly)
    {
        "type": "rba",
        "config": ExtractConfig(
            filename="rba_g01_consumer_price_inflation.xlsx",
            sheet="Data",
            header_row=0,
            date_column=0,
            value_columns={
                "cpi_index": "GCPIAG",  # Consumer price index
            },
        ),
    },
    # RBA B21 - Household Finances (Debt-to-Income)
    {
        "type": "rba",
        "config": ExtractConfig(
            filename="rba_b21_household_finances.xlsx",
            sheet="Data",
            header_row=0,
            date_column=0,
            value_columns={
                "household_debt_to_income": "LHINCSQQ",  # Household debt to income
            },
        ),
    },
]

# Target template columns (50-column structure)
TEMPLATE_COLUMNS = [
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
    "dwelling_approvals",
    "dwelling_approvals_per_1000",
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
    "migration_x_approvals",
    "established_x_reform_implementation",
]
