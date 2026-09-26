import pandas as pd
from pathlib import Path
import os

# Paths
ROOT_DIR = Path(__file__).parent
RAW_HCES_DIR = ROOT_DIR / "data_extracted" / "data" / "HCES_Data_2023-24_Csv"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = PROCESSED_DIR / "hces_combined.csv"

def merge_hces_levels():
    """Merge all LEVEL‑*.csv files from the extracted HCES folder into a single CSV.
    After successful merge, the original LEVEL files are removed to clean up the
    repository.
    """
    csv_files = list(RAW_HCES_DIR.glob("LEVEL *.csv"))
    if not csv_files:
        print(f"No LEVEL files found in {RAW_HCES_DIR}")
        return
    # Process files in chunks to avoid high memory usage
    first_write = True
    for file_path in csv_files:
        try:
            for chunk in pd.read_csv(file_path, chunksize=500000):
                chunk["source_level"] = file_path.name
                if first_write:
                    chunk.to_csv(OUTPUT_FILE, index=False, mode='w')
                    first_write = False
                else:
                    chunk.to_csv(OUTPUT_FILE, index=False, header=False, mode='a')
        except Exception as e:
            print(f"Failed to process {file_path.name}: {e}")
            continue
    # Delete original files
    for file_path in csv_files:
        try:
            os.remove(file_path)
            print(f"Deleted raw file {file_path.name}")
        except Exception as e:
            print(f"Could not delete {file_path.name}: {e}")

if __name__ == "__main__":
    merge_hces_levels()
