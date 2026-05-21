"""Configuration for housing policy analysis project."""

from pathlib import Path
from dataclasses import dataclass


# Directory paths
RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")
MODEL_OUTPUT_DIR = Path("outputs/model_summaries")
FIGURE_OUTPUT_DIR = Path("outputs/figures")

# Data paths
PROCESSED_DATA_PATH = PROCESSED_DATA_DIR / "housing_policy_quarterly.csv"
SOURCE_PAGES_PATH = PROCESSED_DATA_DIR / "source_pages.csv"
TEMPLATE_PATH = PROCESSED_DATA_DIR / "housing_policy_quarterly_template.csv"


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
