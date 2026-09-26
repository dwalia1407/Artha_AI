import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

RAW_FILE = RAW_DIR / "rbi_raw.xlsx"

def clean_rbi():
    df = pd.read_excel(RAW_FILE, sheet_name=None)  # read all sheets
    # Assume a sheet named 'Rates' with columns: 'Date', 'Repo_Rate', 'Reverse_Repo_Rate'
    if 'Rates' in df:
        rates = df['Rates']
    else:
        # fallback to first sheet
        rates = list(df.values())[0]
    rates = rates.rename(columns=lambda x: x.strip().lower().replace(' ', '_'))
    # Clean date column
    if 'date' not in rates.columns:
        raise ValueError("RBI data must contain a 'date' column")
    rates['date'] = pd.to_datetime(rates['date'], errors='coerce')
    rates = rates.dropna(subset=['date'])
    # Replace '-' with NaN for rates columns
    for col in rates.columns:
        if col != 'date':
            rates[col] = pd.to_numeric(rates[col].replace('-', pd.NA), errors='coerce')
    # Forward fill monthly rates
    rates = rates.set_index('date').sort_index().asfreq('MS').ffill().reset_index()
    output_path = PROCESSED_DIR / "rbi_monthly_clean.csv"
    rates.to_csv(output_path, index=False)
    print(f"RBI cleaned data written to {output_path}")

if __name__ == "__main__":
    clean_rbi()
