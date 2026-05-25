# Data Extraction and Dataset Guide

## Overview

This guide covers the data pipeline: downloading sources, extracting quarterly series, deriving analysis variables, and troubleshooting missing columns.

## Dataset Status

**Current**: 419 quarters (1922 Q2 – 2026 Q4) × 42+ columns

**Target**: 50 columns (all required for full analysis)

### Column Coverage

| Status | Count | Notes |
|--------|-------|-------|
| ✅ Fully available | 45 | Base extractions + auto-derived variables |
| ⚠️ Partially available | 2 | Available once additional data sourced |
| 📋 Template-defined | 50 | Total columns when complete |

## Step 1: Download Data

Run from the notebook or CLI:

```python
from src.download import download_all
download_all(overwrite=False)
```

**What happens:**
- RBA files download via direct URLs (reliable)
- ABS files scraped from landing pages (may require manual fallback)
- `source_pages.csv` written with all source links
- Manual steps printed for files that need attention

**Manual downloads**:
If ABS scraping fails, visit the URLs in `data/processed/source_pages.csv` and download Excel files directly to `data/raw/`.

## Step 2: Extract Quarterly Data

Run from the notebook or CLI:

```python
from src.extract import extract_quarterly
df = extract_quarterly(overwrite=False)
```

**What happens:**
- Reads 9 configured Excel files from `data/raw/`
- Extracts Series IDs per config in `src/config.EXTRACT_CONFIGS`
- Averages to quarterly frequency
- Merges all sources on `quarter`
- Writes to `data/processed/housing_policy_quarterly.csv`

**If files are missing:**
The script will print warnings and skip them. Fill in the missing files and re-run.

## Step 3: Inspect Files to Find Series IDs

If you need to add new data sources, inspect the Excel structure:

```python
from src.extract import inspect_raw_file
inspect_raw_file("filename.xlsx")
```

**What it shows:**
- Sheet names
- First 15 rows and column headers
- Helps identify where data actually lives

**Example output:**
```
📋 Inspecting rba_f01_interest_rates_money_market.xlsx
Sheet names: ['Data', 'Notes']

--- Sheet: Data ---
Shape: (1000, 8)
First 15 rows:
  [matrix display]

Column headers (row 0): ['Date', 'RBACRT', 'RBAJD', ...]
```

## Step 4: Add Missing Columns

### Easily added (auto-derivable)

These are calculated automatically in `src/derive.py`:

- **housing_credit_growth** = `housing_credit.pct_change(4) * 100`
- **geo** = `"National"` (default if not in data)
- **dwelling_type** = `"All dwellings"` (default if not in data)
- **Interaction columns** depending on base columns

### Requires additional data sources

**household_debt_to_income** (RBA B21)
- Already in `config.RBA_FILES` to download
- Series ID: `LHINCSQQ` (verify after download)
- Add to `config.EXTRACT_CONFIGS` once you have it

**established_dwelling** (ABS 6416.0 Table 2)
- Separate series for established vs. new dwelling prices
- Likely in file `641602.xlsx` from ABS
- Add to `SOURCE_PAGES` in config, then create extraction config

**Interaction columns** (depend on above)
- `credit_growth_x_post_gfc`, `credit_growth_x_post_covid`
- `established_x_reform_implementation`
- Auto-generated once base columns exist

## Troubleshooting

### Series not found in Excel file

**Check:**
1. Verify Series ID spelling (case-sensitive)
2. Run `inspect_raw_file()` to see all available IDs
3. Confirm it's in the expected row (row 9 for ABS, row 10 for RBA)

**Solution:**
- Update `value_columns` dict with correct Series ID
- Re-run extraction

### Missing columns after extraction

**Check:**
1. File exists in `data/raw/`?
2. Series ID in `config.EXTRACT_CONFIGS`?
3. No errors in extraction output?

**Solution:**
- Print the extracted dataframe to see which columns made it through
- Check for null/NaN series (data may be missing for that series)

### File parsing errors

**Common:**
- Wrong `sheet` name or index
- Wrong `data_start_row` for that file type
- Data type mismatch (string dates vs. datetime)

**Solution:**
- Use `inspect_raw_file()` to verify structure
- Adjust config and re-run

## Data Sources Reference

### RBA Files (Direct URLs)

| File | Series | Status |
|------|--------|--------|
| F01 (Interest Rates) | FIRMMCRT (Cash Rate) | ✅ Working |
| F05 (Lending Rates) | FILRHLBVS (Mortgage Rate) | ✅ Working |
| D02 (Credit) | DLCACOHN, DLCACIHN (housing credit) | ⚠️ Needs config |
| G01 (CPI) | GCPIAG (Consumer Price Index) | ✅ Working |
| B21 (Household Finances) | LHINCSQQ (Debt-to-Income) | ⏳ To be added |

### ABS Files (Scrape or Manual)

| File | Series | Status |
|------|--------|--------|
| 310101 | A2133251W (Population), A2133254C (Migration) | ⏳ Population only |
| 634501 | A2603039T (Wage Price) | ✅ Working |
| 641601 | A83728455L (Property Prices) | ✅ Working |
| 641602 | Established dwelling prices | 📋 Not yet configured |
| 8752001 | A83776195X (Dwelling Completions) | ✅ Working |

### Template (50 columns)

See `src/config.TEMPLATE_COLUMNS` for the complete list of target columns.

## Advanced: Adding Custom Data Sources

If you have external data (e.g., from government reports or manual calculations):

1. **Create CSV in `data/raw/`** with columns: `quarter`, `column_name`
   ```csv
   quarter,household_debt_to_income
   2000-03-31,50.0
   2000-06-30,51.5
   ```

2. **Add extract config** to `src/config.EXTRACT_CONFIGS`:
   ```python
   {
       "type": "csv",
       "config": ExtractConfig(
           filename="custom_data.csv",
           sheet=0,
           header_row=0,
           date_column="quarter",
           value_columns={"household_debt_to_income": "household_debt_to_income"},
       ),
   }
   ```

3. **Add CSV loader** to `src/extract.py` (contact maintainer or check code comments)

## Running the Full Pipeline

### From notebook (recommended):

```python
# Setup
from src.download import download_all
from src.extract import extract_quarterly
from src.derive import add_derived_variables
from src.analyze import run_all_models, plot_all

# Download
download_all(overwrite=False)

# Extract
df = extract_quarterly(overwrite=False)

# Analyze
df = add_derived_variables(df)
run_all_models(df)
plot_all(df)
```

### From CLI:

```bash
python -c "from src.download import download_all; download_all()"
python -c "from src.extract import extract_quarterly; extract_quarterly()"
jupyter notebook housing_policy_analysis.ipynb  # Run analysis cells
```

## Support

For issues:
- **Extraction errors**: Use `inspect_raw_file()` to see structure
- **Missing columns**: Check `src/config.EXTRACT_CONFIGS` for that source
- **Series not found**: Verify spelling and file/sheet location
- **Data type issues**: Ensure dates are parsed as datetime, values as float

Check `src/config.py` for all configuration constants and Series ID definitions.
