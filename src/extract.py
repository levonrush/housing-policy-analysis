"""Extract quarterly data from Excel files and combine into housing policy dataset."""

from pathlib import Path

import pandas as pd

from .config import RAW_DATA_DIR, PROCESSED_DATA_DIR, EXTRACT_CONFIGS, PROCESSED_DATA_PATH
from .derive import to_quarter, add_derived_variables, reorder_columns


def load_abs_file(config) -> pd.DataFrame:
    """Load an ABS Excel file with metadata rows.

    ABS files have a specific structure:
    - Row 0: Series names
    - Row 9: Series IDs
    - Row 10+: Actual data with dates in column 0
    """
    file_path = RAW_DATA_DIR / config.filename

    if not file_path.exists():
        print(f"  ⚠ {config.filename} not found")
        return pd.DataFrame()

    try:
        # Read without header to access raw rows
        df = pd.read_excel(file_path, sheet_name=config.sheet, header=None)

        # Extract series IDs from row 9 (full row, including column 0)
        series_ids_row = df.iloc[9, :].tolist()

        # Build mapping: Series ID → Column Index
        sid_to_col = {sid: idx for idx, sid in enumerate(series_ids_row) if pd.notna(sid)}

        # Extract data starting from row 10
        result_data = {"date": df.iloc[config.data_start_row:, 0]}

        for out_col, series_id in config.value_columns.items():
            if series_id in sid_to_col:
                col_idx = sid_to_col[series_id]
                result_data[out_col] = df.iloc[config.data_start_row:, col_idx]
            else:
                print(f"    ⚠ Series {series_id} not found in {config.filename}")

        result = pd.DataFrame(result_data)

        if len(result) == 0 or list(result.columns) == ["date"]:
            print(f"    ⚠ No data extracted from {config.filename}")
            return pd.DataFrame()

        # Convert to quarter
        result["quarter"] = to_quarter(result["date"])

        # Average to quarterly (excluding date column)
        group_cols = [col for col in config.value_columns.keys() if col in result.columns]
        quarterly = result.groupby("quarter", as_index=False)[group_cols].agg(config.agg_method)

        return quarterly

    except Exception as e:
        print(f"  ❌ Error loading {config.filename}: {e}")
        return pd.DataFrame()


def load_rba_file(config) -> pd.DataFrame:
    """Load an RBA Excel file.

    RBA files have metadata in rows 0-10, data starts at row 11.
    Row 10 contains Series IDs.
    """
    file_path = RAW_DATA_DIR / config.filename

    if not file_path.exists():
        print(f"  ⚠ {config.filename} not found")
        return pd.DataFrame()

    try:
        # Read without header
        df = pd.read_excel(file_path, sheet_name=config.sheet, header=None)

        # Series IDs are in row 10
        series_ids = df.iloc[10, 1:].tolist()

        # Data starts at row 11
        data_df = df.iloc[11:, :].copy()
        data_df.columns = ["date"] + [f"col_{i}" for i in range(len(data_df.columns) - 1)]

        # Map series IDs to requested columns
        result_data = {"date": data_df["date"]}
        for out_col, series_id in config.value_columns.items():
            if series_id in series_ids:
                col_idx = series_ids.index(series_id) + 1  # +1 for date column
                result_data[out_col] = data_df.iloc[:, col_idx]

        result = pd.DataFrame(result_data)

        # Convert to quarter and average
        result["quarter"] = to_quarter(result["date"])
        group_cols = [col for col in config.value_columns.keys()]
        quarterly = result.groupby("quarter", as_index=False)[group_cols].mean()

        return quarterly

    except Exception as e:
        print(f"  ❌ Error loading {config.filename}: {e}")
        return pd.DataFrame()


def combine_data_sources(configs: list[dict] = None) -> pd.DataFrame:
    """Load and combine all configured data sources."""
    if configs is None:
        configs = EXTRACT_CONFIGS

    dfs = []
    for item in configs:
        config_type = item["type"]
        config = item["config"]

        print(f"  Loading {config.filename}...", end=" ")

        if config_type == "abs":
            df = load_abs_file(config)
        elif config_type == "rba":
            df = load_rba_file(config)
        else:
            print(f"❌ Unknown type {config_type}")
            continue

        if not df.empty:
            dfs.append(df)
            print(f"✓ ({len(df)} quarters)")
        else:
            print("(no data)")

    if not dfs:
        raise ValueError("No data sources loaded successfully")

    # Start with the first dataframe and join others on quarter
    result = dfs[0]
    for df in dfs[1:]:
        result = result.merge(df, on="quarter", how="outer")

    return result.sort_values("quarter").reset_index(drop=True)


def inspect_raw_file(filename: str) -> None:
    """Inspect an Excel file to find series IDs and structure."""
    file_path = RAW_DATA_DIR / filename

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    print(f"\n📋 Inspecting {filename}")
    print("=" * 70)

    try:
        xls = pd.ExcelFile(file_path)
        print(f"\nSheet names: {xls.sheet_names}")

        for sheet in xls.sheet_names[:2]:  # First 2 sheets
            print(f"\n--- Sheet: {sheet} ---")
            df = pd.read_excel(file_path, sheet_name=sheet, header=None)
            print(f"Shape: {df.shape}")
            print("\nFirst 15 rows:")
            print(df.iloc[:15, :].to_string())
            print(f"\nColumn headers (row 0): {df.iloc[0, :10].tolist()}")

    except Exception as e:
        print(f"Error: {e}")


def extract_quarterly(overwrite: bool = False) -> pd.DataFrame:
    """Extract quarterly data, orchestrating load → derive → reorder → write."""
    # Check if output already exists
    if PROCESSED_DATA_PATH.exists() and not overwrite:
        print(f"✓ Loading existing dataset from {PROCESSED_DATA_PATH}")
        df = pd.read_csv(PROCESSED_DATA_PATH)
        df["quarter"] = pd.to_datetime(df["quarter"])
        return df

    print("\n📊 Extracting quarterly data from Excel sources...\n")

    # Load and combine data from all sources
    df = combine_data_sources(EXTRACT_CONFIGS)
    print(f"\n✓ Combined {len(df)} quarters from sources")

    # Derive analysis variables
    print("📐 Deriving analysis variables...")
    df = add_derived_variables(df)

    # Reorder columns to match template
    df = reorder_columns(df)

    # Write to output
    PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DATA_PATH, index=False)

    print(f"\n✓ Dataset written to {PROCESSED_DATA_PATH}")
    print(f"  Shape: {df.shape}")
    print(f"  Quarters: {df['quarter'].min()} to {df['quarter'].max()}")
    print(f"  Columns: {df.shape[1]}")

    return df
