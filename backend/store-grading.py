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


# ─── Main Grading Function ───────────────────────────────────────────────────

def run_grading(
    dept: int,
    class_: int,
    level: str = "class",
    subclass: int | None = None,
    store: int | None = None,
    country: str | None = None,
    n_clusters: int = 3,
) -> dict:
    """
    Core grading function. Called by both CLI and Flask API.

    Parameters
    ----------
    dept      : mandatory
    class_    : mandatory
    level     : 'class' or 'subclass'
    subclass  : optional filter (subclass_level only uses this as an additional filter)
    store     : optional store/location filter
    country   : optional AREA_NAME filter
    n_clusters: number of K-means clusters (default 3)

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
          AND p.CLASS = ?
    """
    params: list = [dept, class_]

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
        return {"status": "no_data", "inserts": 0, "updates": 0,
                "message": f"No sales data found for dept={dept}, class={class_}"}

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
    if level == "subclass" and subclass is None:
        # ── "All Subclasses" mode: run K-means independently per subclass ──
        # Each subclass competes only within itself, ensuring grades are
        # always spread relative to stores in that subclass, never across
        # the combined pool of all subclasses.
        all_subclasses = df["SUBCLASS"].dropna().unique()
        graded_parts = []
        for sc in all_subclasses:
            sc_df = df[df["SUBCLASS"] == sc]
            agg = build_features(sc_df, level, group_keys)
            graded_sc = assign_grades(agg, n_clusters=n_clusters)
            graded_parts.append(graded_sc)
        graded = pd.concat(graded_parts, ignore_index=True) if graded_parts else pd.DataFrame()
    else:
        # Single subclass (or class-level): grade as one batch
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
