"""
store-grading.py — K-means clustering engine for store grading.

Can be run standalone (CLI) or called programmatically by the Flask API.

Usage (standalone):
    python store-grading.py --dept 108 --class 3 --level class
    python store-grading.py --dept 108 --class 3 --subclass 17 --level subclass
    python store-grading.py --dept 108 --class 3 --level subclass --country SAU
"""

import argparse
import sqlite3
import sys
import os
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ─── Paths ───────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from database import get_db

CREATE_ID = "KMEAN_PY"


def date_to_week_int(date_str):
    """Converts YYYY-MM-DD string or YYYYWW integer string to YYYYWW integer format."""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    # Check if it's already YYYYWW (6 digits)
    if len(date_str) == 6 and date_str.isdigit():
        return int(date_str)

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        year, week, _ = dt.isocalendar()
        return year * 100 + week
    except:
        return None


# ─── Feature Engineering ─────────────────────────────────────────────────────

def build_features(df: pd.DataFrame, level: str, group_keys: list[str]) -> pd.DataFrame:
    """
    Aggregate sales_hist_fact (with product & location joins already done)
    into one row per group_key combination, with clustering features.

    Features:
      - total_units      : total units sold (regular + promo + markdown)
      - base_history     : sum of BASE_HISTORY
      - weeks_of_sales   : number of distinct weeks with sales
      - avg_weekly_units : total_units / weeks_of_sales
    """
    df = df.copy()
    df["total_units"] = (
        df["REGULAR_SLS_UNITS"].fillna(0)
        + df["PROMO_SLS_UNITS"].fillna(0)
        + df["MRKDWN_SLS_UNITS"].fillna(0)
    )

    agg = df.groupby(group_keys, as_index=False, observed=True).agg(
        total_units=("total_units", "sum"),
        base_history=("BASE_HISTORY", "sum"),
        weeks_of_sales=("TIME_ID", "nunique"),
    )
    agg["avg_weekly_units"] = (
        agg["total_units"] / agg["weeks_of_sales"].replace(0, np.nan)
    ).fillna(0)

    return agg


# ─── K-means Clustering ──────────────────────────────────────────────────────

FEATURE_COLS = ["total_units", "base_history", "avg_weekly_units", "weeks_of_sales"]

def assign_grades(agg_df: pd.DataFrame, n_clusters: int = 3) -> pd.DataFrame:
    """
    Run K-means on feature columns; sort cluster centroids by avg_weekly_units
    so that Grade 1 = best performing stores, Grade 3 = lowest.

    Returns agg_df with an additional 'GRADE' column.
    """
    n = len(agg_df)
    k = min(n_clusters, n)

    if k < 2:
        # Only one or zero stores for this scope — assign Grade 1
        agg_df = agg_df.copy()
        agg_df["GRADE"] = "1"
        agg_df["cluster_id"] = 0
        return agg_df

    feature_matrix = agg_df[FEATURE_COLS].fillna(0).values
    scaler = StandardScaler()
    scaled = scaler.fit_transform(feature_matrix)

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    agg_df = agg_df.copy()
    agg_df["cluster_id"] = kmeans.fit_predict(scaled)

    # Determine grade rank: cluster with highest avg_weekly_units centroid → Grade 1
    centroid_avg = (
        agg_df.groupby("cluster_id")["avg_weekly_units"].mean()
        .sort_values(ascending=False)
    )
    rank_map = {cluster: str(rank + 1) for rank, cluster in enumerate(centroid_avg.index)}
    agg_df["GRADE"] = agg_df["cluster_id"].map(rank_map)

    return agg_df


# ─── Upsert to store_grade ───────────────────────────────────────────────────

def upsert_grades(conn: sqlite3.Connection, rows: list[dict]) -> tuple[int, int]:
    """
    Insert or update rows into store_grade.
    Match key: (BRAND, LOCATION, DEPT, CLASS, SUBCLASS) — SUBCLASS can be NULL.

    Returns (inserts, updates).
    """
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    inserts = 0
    updates = 0

    for row in rows:
        subclass = row.get("SUBCLASS")  # May be None for class-level

        # Check for existing record
        if subclass is None:
            existing = conn.execute("""
                SELECT STORE_GRADE_ID FROM store_grade
                WHERE BRAND=? AND LOCATION=? AND DEPT=? AND CLASS=? AND SUBCLASS IS NULL
            """, (row["BRAND"], row["LOCATION"], row["DEPT"], row["CLASS"])).fetchone()
        else:
            existing = conn.execute("""
                SELECT STORE_GRADE_ID FROM store_grade
                WHERE BRAND=? AND LOCATION=? AND DEPT=? AND CLASS=? AND SUBCLASS=?
            """, (row["BRAND"], row["LOCATION"], row["DEPT"], row["CLASS"], subclass)).fetchone()

        if existing:
            conn.execute("""
                UPDATE store_grade
                SET GRADE=?, LAST_UPDATE_DATETIME=?, LAST_UPDATE_ID=?, COUNTRY=?
                WHERE STORE_GRADE_ID=?
            """, (row["GRADE"], now, CREATE_ID, row.get("COUNTRY"), existing[0]))
            updates += 1
        else:
            conn.execute("""
                INSERT INTO store_grade
                    (BRAND, LOCATION, COUNTRY, DEPT, CLASS, SUBCLASS, GRADE,
                     CREATE_DATETIME, CREATE_ID, LAST_UPDATE_DATETIME, LAST_UPDATE_ID)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            """, (
                row["BRAND"], row["LOCATION"], row.get("COUNTRY"),
                row["DEPT"], row["CLASS"], subclass,
                row["GRADE"], now, CREATE_ID
            ))
            inserts += 1

    conn.commit()
    return inserts, updates


def update_store_grades(conn, updates: list) -> int:
    """Manual update of grades and publish status."""
    from datetime import datetime
    now = datetime.now().isoformat()
    count = 0
    for up in updates:
        sg_id = up.get("store_grade_id")
        grade = up.get("grade")
        status = up.get("status", "Y")  # Default to 'Y' for publish
        if not sg_id: continue
        conn.execute("""
            UPDATE store_grade
            SET GRADE=?, PUBLISH_STATUS=?, LAST_UPDATE_DATETIME=?, LAST_UPDATE_ID=?
            WHERE STORE_GRADE_ID=?
        """, (grade, status, now, CREATE_ID, sg_id))
        count += 1
    conn.commit()
    return count


# ─── Main Grading Function ───────────────────────────────────────────────────

def run_grading(
    dept: int,
    class_ = None,
    level: str = "class",
    subclass = None,
    store = None,
    country = None,
    n_clusters = 3,
    from_date = None,
    to_date = None,
) -> dict:
    """
    Core grading function. Called by both CLI and Flask API.

    Parameters
    ----------
    dept      : mandatory
    class_    : optional filter (if None, grades all classes in dept)
    level     : 'class' or 'subclass'
    subclass  : optional filter (subclass_level only uses this as an additional filter)
    store     : optional store/location filter
    country   : optional AREA_NAME filter
    n_clusters: number of K-means clusters (default 3)
    from_date : optional start date (YYYY-MM-DD)
    to_date   : optional end date (YYYY-MM-DD)

    Returns a summary dict.
    """
    level = level.lower().strip()
    if level not in ("class", "subclass"):
        raise ValueError("level must be 'class' or 'subclass'")

    conn = get_db()

    # ── Build SQL query ──────────────────────────────────────────────────────
    sql = """
        SELECT
            s.BRAND,
            s.STORE         AS LOCATION,
            s.TIME_ID,
            s.OPTION_ID,
            s.REGULAR_SLS_UNITS,
            s.PROMO_SLS_UNITS,
            s.MRKDWN_SLS_UNITS,
            s.BASE_HISTORY,
            p.DEPT,
            p.CLASS,
            p.SUBCLASS,
            l.AREA_NAME     AS COUNTRY,
            l.STORE_NAME
        FROM sales_hist_fact s
        JOIN product_option_dim p ON s.OPTION_ID = p.OPTION_ID
        LEFT JOIN location_st_master l ON s.STORE = l.STORE
        WHERE p.DEPT = ?
    """
    params: list = [dept]

    if class_ is not None:
        sql += " AND p.CLASS = ?"
        params.append(class_)

    from_week = date_to_week_int(from_date)
    to_week = date_to_week_int(to_date)

    if from_week:
        sql += " AND s.TIME_ID >= ?"
        params.append(from_week)
    if to_week:
        sql += " AND s.TIME_ID <= ?"
        params.append(to_week)

    if level == "subclass" and subclass is not None:
        sql += " AND p.SUBCLASS = ?"
        params.append(subclass)

    if store is not None:
        sql += " AND s.STORE = ?"
        params.append(store)

    if country is not None:
        sql += " AND l.AREA_NAME = ?"
        params.append(country)

    df = pd.read_sql_query(sql, conn, params=params)

    if df.empty:
        conn.close()
        msg = f"No sales data found for dept={dept}"
        if class_: msg += f", class={class_}"
        return {"status": "no_data", "inserts": 0, "updates": 0, "message": msg}

    # ── Determine grouping keys by level ─────────────────────────────────────
    if level == "class":
        group_keys = ["BRAND", "LOCATION", "COUNTRY", "DEPT", "CLASS"]
    else:  # subclass
        group_keys = ["BRAND", "LOCATION", "COUNTRY", "DEPT", "CLASS", "SUBCLASS"]

    # Filter out rows where subclass is null when running subclass-level
    if level == "subclass":
        df = df[df["SUBCLASS"].notna()]
        if df.empty:
            conn.close()
            return {"status": "no_data", "inserts": 0, "updates": 0,
                    "message": "No subclass data found for given filters"}

    # ── Aggregate + cluster ──────────────────────────────────────────────────
    # We loop if we are in a batch mode:
    # 1. All Classes (irrespective of level)
    # 2. All Subclasses (with a fixed class)
    
    batch_mode = False
    batch_cols = []
    
    if class_ is None:
        batch_mode = True
        batch_cols = ["CLASS"]
        if level == "subclass" and subclass is None:
            batch_cols = ["CLASS", "SUBCLASS"]
    elif level == "subclass" and subclass is None:
        batch_mode = True
        batch_cols = ["CLASS", "SUBCLASS"]
    
    if batch_mode:
        # Determine unique scopes to grade independently
        df_scopes = df[batch_cols].dropna().drop_duplicates()
        graded_parts = []
        for _, scope_row in df_scopes.iterrows():
            # Filter df for this specific scope
            mask = True
            for col in batch_cols:
                mask = mask & (df[col] == scope_row[col])
            
            scope_df = df[mask]
            if scope_df.empty: continue
            
            agg = build_features(scope_df, level, group_keys)
            if agg.empty: continue
            
            graded_scope = assign_grades(agg, n_clusters=n_clusters)
            graded_parts.append(graded_scope)
            
        graded = pd.concat(graded_parts, ignore_index=True) if graded_parts else pd.DataFrame()
    else:
        # Single scope (fixed class, and optionally fixed subclass)
        agg = build_features(df, level, group_keys)
        graded = assign_grades(agg, n_clusters=n_clusters)

    if graded.empty:
        conn.close()
        return {"status": "no_data", "inserts": 0, "updates": 0,
                "message": "No data to grade after filtering."}

    # ── Build upsert rows ────────────────────────────────────────────────────
    rows = []
    for _, r in graded.iterrows():
        row = {
            "BRAND":    r["BRAND"],
            "LOCATION": int(r["LOCATION"]),
            "COUNTRY":  r.get("COUNTRY"),
            "DEPT":     int(r["DEPT"]),
            "CLASS":    int(r["CLASS"]),
            "SUBCLASS": int(r["SUBCLASS"]) if level == "subclass" and pd.notna(r.get("SUBCLASS")) else None,
            "GRADE":    r["GRADE"],
        }
        rows.append(row)

    inserts, updates = upsert_grades(conn, rows)
    conn.close()

    return {
        "status":   "success",
        "level":    level,
        "dept":     dept,
        "class":    class_,
        "subclass": subclass,
        "country":  country,
        "store":    store,
        "rows_processed": len(graded),
        "inserts":  inserts,
        "updates":  updates,
        "message":  f"Grading complete. {inserts} inserted, {updates} updated.",
    }


# ─── CLI Entry Point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Store Grading — K-means Clustering")
    parser.add_argument("--dept",     type=int, required=True,  help="Department number (mandatory)")
    parser.add_argument("--class",    type=int, required=True,  dest="class_",
                        help="Class number (mandatory)")
    parser.add_argument("--level",    type=str, default="class",
                        choices=["class", "subclass"], help="Grading level")
    parser.add_argument("--subclass", type=int, default=None,   help="Subclass filter (optional)")
    parser.add_argument("--store",    type=int, default=None,   help="Store/location filter (optional)")
    parser.add_argument("--country",  type=str, default=None,   help="Area/country filter (optional)")
    parser.add_argument("--clusters", type=int, default=3,      help="Number of grades/clusters (default 3)")

    args = parser.parse_args()
    result = run_grading(
        dept=args.dept,
        class_=args.class_,
        level=args.level,
        subclass=args.subclass,
        store=args.store,
        country=args.country,
        n_clusters=args.clusters,
    )
    print(result)
    if result["status"] == "success":
        print(f"\n✅ {result['message']}")
    else:
        print(f"\n⚠️  {result['message']}")
        sys.exit(1)
