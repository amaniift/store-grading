import sqlite3
import pandas as pd
import os
import sys
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import get_db

def generate_all_forecasts():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Get all unique SKU/Store combinations from actuals
    print("Fetching active SKU/Store combinations from database...")
    pairs = cursor.execute("SELECT DISTINCT OPTION_ID, STORE FROM sales_hist_fact").fetchall()
    total = len(pairs)
    print(f"Found {total} unique combinations with historical data.")
    
    # 2. Iterate and forecast
    count = 0
    forecast_weeks = 52
    
    # Create the table if it doesn't exist (safety)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts_fact (
            OPTION_ID    TEXT,
            STORE        INTEGER,
            TIME_ID      INTEGER,
            UNITS        REAL,
            MODEL_USED   TEXT,
            PRIMARY KEY (OPTION_ID, STORE, TIME_ID)
        )
    """)
    
    print("Starting batch forecasting (Holt-Winters)...")
    
    for opt_id, store in pairs:
        count += 1
        if count % 100 == 0 or count == total:
            print(f"  Progress: {count}/{total} ({(count/total*100):.1f}%)")
            conn.commit() # Commit periodically
            
        try:
            # Query history
            query = """
                SELECT TIME_ID, (REGULAR_SLS_UNITS + PROMO_SLS_UNITS + MRKDWN_SLS_UNITS) as TOTAL_SALES 
                FROM sales_hist_fact 
                WHERE OPTION_ID = ? AND STORE = ? 
                ORDER BY TIME_ID ASC
            """
            df = pd.read_sql_query(query, conn, params=(opt_id, store))
            
            # Need at least a few points for a trend
            if len(df) < 5:
                continue
                
            series = df["TOTAL_SALES"].values
            last_time_id = df["TIME_ID"].iloc[-1]
            
            # Holt-Winters (Exponential Smoothing)
            model = ExponentialSmoothing(series, trend="add", seasonal=None, initialization_method="estimated")
            fit_model = model.fit()
            forecast_values = fit_model.forecast(forecast_weeks)
            
            # Generate future TIME_IDs
            year = int(str(last_time_id)[:4])
            week = int(str(last_time_id)[4:])
            
            inserts = []
            for val in forecast_values:
                week += 1
                if week > 52:
                    week = 1
                    year += 1
                t_id = int(f"{year}{week:02d}")
                # Scale float to a reasonable precision
                inserts.append((opt_id, store, t_id, round(float(val), 2), 'exponential_smoothing'))
            
            # Clear old forecasts for this pair to avoid unique constraint violations
            cursor.execute("DELETE FROM forecasts_fact WHERE OPTION_ID = ? AND STORE = ?", (opt_id, store))
            
            # Bulk Insert
            cursor.executemany("""
                INSERT INTO forecasts_fact (OPTION_ID, STORE, TIME_ID, UNITS, MODEL_USED) 
                VALUES (?, ?, ?, ?, ?)
            """, inserts)
            
        except Exception:
            # Individual failures (e.g. all zeros) shouldn't stop the whole batch
            continue
            
    conn.commit()
    conn.close()
    print("\n[SUCCESS] Batch forecasting complete. Results stored in 'forecasts_fact'.")

if __name__ == "__main__":
    generate_all_forecasts()
