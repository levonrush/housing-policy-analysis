"""Plot Australian housing, wages, policy events and macro drivers.

Expected input:
    data/processed/housing_policy_quarterly.csv

Figures:
    outputs/figures/price_wage_divergence.png
    outputs/figures/housing_policy_drivers.png
    outputs/figures/combined_policy_story.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


INPUT_PATH = Path("data/processed/housing_policy_quarterly.csv")
OUTPUT_DIR = Path("outputs/figures")


EVENTS = [
    ("1987-09-30", "Negative gearing restored"),
    ("1999-12-31", "CGT discount"),
    ("2008-09-30", "GFC"),
    ("2020-03-31", "COVID"),
    ("2026-06-30", "Reform announcement"),
    ("2027-09-30", "Reform implementation"),
]

SHOCK_WINDOWS = [
    ("2008-09-30", "2009-06-30", "GFC window"),
    ("2020-03-31", "2021-12-31", "COVID window"),
]


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


def load_data(input_path: Path = INPUT_PATH) -> pd.DataFrame:
    """Load and sort the quarterly modelling table."""

    df = pd.read_csv(input_path)
    df["quarter"] = pd.to_datetime(df["quarter"])
    return df.sort_values("quarter")


def plot_price_wage_divergence(df: pd.DataFrame, output_path: Path) -> None:
    """Plot real dwelling prices, real wages and the price-wage ratio."""

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
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def plot_policy_drivers(df: pd.DataFrame, output_path: Path) -> None:
    """Plot standardised rates, migration, investor credit and supply."""

    driver_columns = {
        "mortgage_rate": "Mortgage rate",
        "nom_per_1000": "Net overseas migration per 1,000",
        "investor_credit_share": "Investor credit share",
        "dwelling_completions_per_1000": "Dwelling completions per 1,000",
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
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def plot_combined_policy_story(df: pd.DataFrame, output_path: Path) -> None:
    """Plot the main outcome and standardised drivers on one narrative figure."""

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
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def main() -> None:
    """Create all figures from the quarterly modelling table."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data(INPUT_PATH)

    plot_price_wage_divergence(df, OUTPUT_DIR / "price_wage_divergence.png")
    plot_policy_drivers(df, OUTPUT_DIR / "housing_policy_drivers.png")
    plot_combined_policy_story(df, OUTPUT_DIR / "combined_policy_story.png")

    print(f"Figures written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
