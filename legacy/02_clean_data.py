# -*- coding: utf-8 -*-
"""
Data cleaning script for the Artha AI FMS project.

- Cleans the combined HCES dataset (data/processed/hces_combined.csv) and writes a cleaned version.
- Removes unnecessary raw files (e.g., leftover LEVEL CSVs, test files).
- Archives unused zip files (data.zip, tester.zip) into an "archive" folder.
- Creates a zip archive of the processed data directory for easy distribution.

The script is idempotent: running it multiple times will not duplicate work.
"""

import os
import shutil
import zipfile
from pathlib import Path
import pandas as pd
import fnmatch

# Project root
ROOT_DIR = Path(__file__).parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
ARCHIVE_DIR = ROOT_DIR / "archive"

# Ensure archive directory exists
ARCHIVE_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Clean HCES combined data
# ---------------------------------------------------------------------------
COMBINED_FILE = PROCESSED_DIR / "hces_combined.csv"
CLEANED_FILE = PROCESSED_DIR / "hces_clean.csv"

def clean_hces(input_path: Path, output_path: Path) -> None:
    """Read the large HCES CSV in chunks, apply basic cleaning, and write out.

    Cleaning steps:
    1. Strip whitespace from column names and lower‑case them.
    2. Remove completely empty columns.
    3. Drop duplicate rows based on all columns.
    4. For numeric columns, fill NaNs with the column median.
    5. For categorical columns, fill NaNs with the string "unknown".
    """
    if not input_path.exists():
        print(f"[HCES CLEAN] Input file not found: {input_path}")
        return

    # Write header only once
    first_chunk = True
    for chunk in pd.read_csv(input_path, chunksize=100_000, on_bad_lines='skip', engine='python'):
        # Standardise column names
        chunk.columns = [col.strip().lower() for col in chunk.columns]
        # Drop empty columns
        chunk.dropna(axis=1, how="all", inplace=True)
        # Drop duplicate rows within the chunk
        chunk.drop_duplicates(inplace=True)
        # Fill missing values
        for col in chunk.columns:
            if pd.api.types.is_numeric_dtype(chunk[col]):
                median = chunk[col].median()
                chunk[col] = chunk[col].fillna(median)
            else:
                chunk[col] = chunk[col].fillna("unknown")
        # Write to output
        if first_chunk:
            chunk.to_csv(output_path, index=False, mode="w")
            first_chunk = False
        else:
            chunk.to_csv(output_path, index=False, header=False, mode="a")
    print(f"[HCES CLEAN] Cleaned data written to {output_path}")

# Run cleaning
clean_hces(COMBINED_FILE, CLEANED_FILE)

# ---------------------------------------------------------------------------
# 2. Remove unnecessary raw files
# ---------------------------------------------------------------------------
# Define patterns of files that are required for the pipeline. Everything else is deleted.
REQUIRED_PATTERNS = []

def is_required(file_name: str) -> bool:
    """Return True if the file matches any of the required patterns."""
    for pattern in REQUIRED_PATTERNS:
        if fnmatch.fnmatch(file_name, pattern):
            return True
    return False

if RAW_DIR.is_dir():
    for item in RAW_DIR.iterdir():
        if item.is_file() and not is_required(item.name):
            try:
                item.unlink()
                print(f"[RAW CLEAN] Removed unnecessary raw file: {item.name}")
            except Exception as e:
                print(f"[RAW CLEAN] Failed to delete {item.name}: {e}")

# ---------------------------------------------------------------------------
# 3. Archive unused zip files
# ---------------------------------------------------------------------------
ZIP_FILES = list(ROOT_DIR.glob("*.zip"))
for zip_path in ZIP_FILES:
    try:
        destination = ARCHIVE_DIR / zip_path.name
        shutil.move(str(zip_path), str(destination))
        print(f"[ZIP ARCHIVE] Moved {zip_path.name} to archive folder")
    except Exception as e:
        print(f"[ZIP ARCHIVE] Could not move {zip_path.name}: {e}")

# ---------------------------------------------------------------------------
# 4. Zip the processed data directory (excluding the combined raw file to save space)
# ---------------------------------------------------------------------------
# PROCESSED_ZIP = ROOT_DIR / "processed_data.zip"
# with zipfile.ZipFile(PROCESSED_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
#     for file_path in PROCESSED_DIR.rglob("*.csv"):
#         # Skip the huge combined file if you only need the cleaned version
#         if file_path.name == "hces_combined.csv":
#             continue
#         zipf.write(file_path, arcname=file_path.relative_to(ROOT_DIR))
#         print(f"[ZIP CREATE] Added {file_path.name} to archive")
# print(f"[ZIP CREATE] Processed data archive created at {PROCESSED_ZIP}")
