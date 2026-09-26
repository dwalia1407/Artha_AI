import os
import pandas as pd
from pathlib import Path
from utils import detect_duplicates

RAW_DATA_DIR = Path(__file__).parent / "data" / "raw"
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = REPORTS_DIR / "data_profile_report.md"

def profile_file(path: Path) -> str:
    """Read a CSV or Excel file (sample rows) and return a markdown summary."""
    try:
        if path.suffix.lower() in {".csv", ".txt"}:
            df = pd.read_csv(path, nrows=1000)
        elif path.suffix.lower() in {".xlsx", ".xls"}:
            df = pd.read_excel(path, nrows=1000)
        else:
            return f"*Unsupported file type: {path.name}*"
    except Exception as e:
        return f"*Failed to read {path.name}: {e}*"

    lines = []
    lines.append(f"### {path.name}")
    lines.append(f"- **Rows (sample)**: {df.shape[0]}")
    lines.append(f"- **Columns**: {df.shape[1]}")
    lines.append("- **Column types**:")
    for col, dtype in df.dtypes.items():
        lines.append(f"  - `{col}`: {dtype}")
    missing = df.isna().sum().sum()
    lines.append(f"- **Total missing values (sample)**: {missing}")
    dup = detect_duplicates(df)
    lines.append(f"- **Duplicate rows (sample)**: {len(dup)}")
    lines.append("\n")
    return "\n".join(lines)

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("# Data Profiling Report\n\n")
        for root, _, files in os.walk(RAW_DATA_DIR):
            for file in files:
                path = Path(root) / file
                summary = profile_file(path)
                f.write(summary + "\n")
    print(f"Profiling report written to {LOG_FILE}")

if __name__ == "__main__":
    main()
