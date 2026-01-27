import pandas as pd
import os

CSV_FILE = "nifty100.csv"

# 1. Define the Sector Mapping
INDUSTRY_TO_SECTOR = {
    'Financial Services': '^NSEBANK',
    'Information Technology': '^CNXIT',
    'Automobile and Auto Components': '^CNXAUTO',
    'Oil Gas & Consumable Fuels': '^CNXENERGY',
    'Fast Moving Consumer Goods': '^CNXFMCG',
    'Metals & Mining': '^CNXMETAL',
    'Healthcare': '^CNXPHARMA',
    'Realty': '^CNXREALTY',
    'Consumer Durables': '^CNXCONSUM',
    'Consumer Services': '^CNXCONSUM',
    'Power': '^CNXENERGY',
    'Construction Materials': '^CNXINFRA',
    'Construction': '^CNXINFRA',
    'Capital Goods': '^CNXINFRA',
    'Telecommunication': '^CNXINFRA',
    'Services': '^CNXSERVICE',
    'Chemicals': '^CNXCMDT'
}

def update_csv():
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found.")
        return

    try:
        df = pd.read_csv(CSV_FILE)
        
        # Create Sector Index column based on Industry
        df['Sector_Index'] = df['Industry'].map(INDUSTRY_TO_SECTOR)
        
        # Fill NaN with ^NSEI (Nifty 50) as fallback if mapping fails
        df['Sector_Index'] = df['Sector_Index'].fillna('^NSEI')

        df.to_csv(CSV_FILE, index=False)
        print(f"Successfully updated {CSV_FILE} with Sector_Index column.")
        print(df[['Symbol', 'Industry', 'Sector_Index']].head())

    except Exception as e:
        print(f"Failed to update CSV: {e}")

if __name__ == "__main__":
    update_csv()
