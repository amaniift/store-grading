"""
database.py — SQLite database initialization and CSV loading utility.
Run directly to initialize the DB and load all source CSVs.
"""

import sqlite3
import pandas as pd
import os
import sys

# ─── Paths ──────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "store_grading.db")

# CSVs are looked up relative to this file's parent or the user's Downloads
CANDIDATE_DIRS = [
    os.path.join(BASE_DIR, "..", "data"),
    r"C:\Users\amankumar.singh\Downloads",
]


def find_csv(filename: str) -> str:
    for d in CANDIDATE_DIRS:
        p = os.path.join(d, filename)
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(
        f"Could not find '{filename}' in any of: {CANDIDATE_DIRS}"
    )


# ─── Connection ──────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─── DDL ─────────────────────────────────────────────────────────────────────

DDL_SALES_HIST_FACT = """
CREATE TABLE IF NOT EXISTS sales_hist_fact (
    BRAND             TEXT,
    TIME_ID           INTEGER,
    OPTION_ID         TEXT,
    STORE             INTEGER,
    REGULAR_SLS_UNITS REAL,
    PROMO_SLS_UNITS   REAL,
    MRKDWN_SLS_UNITS  REAL,
    BASE_HISTORY      REAL
)
"""

DDL_PRODUCT_OPTION_DIM = """
CREATE TABLE IF NOT EXISTS product_option_dim (
    BRAND                TEXT,
    OPTION_ID            TEXT PRIMARY KEY,
    OPTION_DESC          TEXT,
    VPN                  TEXT,
    LIKE_ITEM            TEXT,
    DEPT                 INTEGER,
    DEPT_NAME            TEXT,
    CLASS                INTEGER,
    CLASS_NAME           TEXT,
    SUBCLASS             INTEGER,
    SUB_NAME             TEXT,
    FABRIC               TEXT,
    COLOR_SHADE          TEXT,
    COLOR_FAMILY         TEXT,
    SEASON_CODE          TEXT,
    SEASONALITY          TEXT,
    SILHOUETTE           TEXT,
    COLLECTION           TEXT,
    SLEEVE_LENGTH        TEXT,
    LENGTH               TEXT,
    HEEL_TYPE            TEXT,
    GENDER               TEXT,
    SIZERANGE            TEXT,
    PRICE_STRATEGY       TEXT,
    STORY                TEXT,
    SELLING_PHASE        TEXT,
    LABEL                TEXT,
    CREATE_ID            TEXT,
    CREATE_DATETIME      TEXT,
    LAST_UPDATE_DATETIME TEXT,
    LAST_UPDATE_ID       TEXT,
    SUBDEPARTMENT        TEXT,
    SUBDEPARTMENT_NAME   TEXT
)
"""

DDL_LOCATION_ST_MASTER = """
CREATE TABLE IF NOT EXISTS location_st_master (
    STORE                          INTEGER PRIMARY KEY,
    STORE_NAME                     TEXT,
    STORE_CLASS                    TEXT,
    STORE_MGR_NAME                 TEXT,
    STORE_OPEN_DATE                TEXT,
    STORE_CLOSE_DATE               TEXT,
    PHONE_NUMBER                   TEXT,
    EMAIL                          TEXT,
    TOTAL_SQUARE_FT                REAL,
    SELLING_SQUARE_FT              REAL,
    LINEAR_DISTANCE                TEXT,
    VAT_REGION                     TEXT,
    STOCKHOLDING_IND               TEXT,
    CHANNEL_ID                     INTEGER,
    FORMAT_NAME                    TEXT,
    STORE_FORMAT                   TEXT,
    MALL_NAME                      TEXT,
    TRANSFER_ZONE                  INTEGER,
    DEFAULT_WH                     TEXT,
    DEFAULT_RDC                    TEXT,
    STOP_ORDER_DAYS                TEXT,
    START_ORDER_DAYS               TEXT,
    CURRENCY_CODE                  TEXT,
    LANG                           INTEGER,
    TSF_ENTITY_ID                  INTEGER,
    ORG_UNIT_ID                    INTEGER,
    AUTO_RCV                       TEXT,
    STORE_TYPE                     TEXT,
    TIMEZONE_NAME                  TEXT,
    CUSTOMER_ORDER_LOC_IND         TEXT,
    CREATE_ID                      TEXT,
    CREATE_DATETIME                TEXT,
    BANNER_NAME                    TEXT,
    CHAIN_NAME                     TEXT,
    CHAIN_MGR_NAME                 TEXT,
    CHAIN_CURRENCY_CODE            TEXT,
    CHANNEL_NAME                   TEXT,
    CHANNEL_TYPE                   TEXT,
    CO_NAME                        TEXT,
    CO_ADD1                        TEXT,
    CO_ADD2                        TEXT,
    CO_ADD3                        TEXT,
    CO_CITY                        TEXT,
    CO_STATE                       TEXT,
    CO_COUNTRY                     TEXT,
    CO_POST                        TEXT,
    CO_NAME_SECONDARY              TEXT,
    CO_JURISDICTION_CODE           TEXT,
    DISTRICT_NAME                  TEXT,
    DISTRICT_MGR_NAME              TEXT,
    DISTRICT_CURRENCY_CODE         TEXT,
    REGION_NAME                    TEXT,
    REGION_MGR_NAME                TEXT,
    REGION_CURRENCY_CODE           TEXT,
    COMPANY                        INTEGER,
    CHAIN                          INTEGER,
    AREA                           INTEGER,
    REGION                         INTEGER,
    DISTRICT                       INTEGER,
    ADD_1                          TEXT,
    ADD_2                          TEXT,
    ADD_3                          TEXT,
    CITY                           TEXT,
    STATE                          TEXT,
    COUNTRY_ID                     TEXT,
    POST                           TEXT,
    CONTACT_NAME                   TEXT,
    COUNTY                         TEXT,
    JURISDICTION_CODE              TEXT,
    AREA_NAME                      TEXT,
    AREA_CURRENCY_CODE             TEXT,
    AREA_MGR_NAME                  TEXT,
    BUDGET_CCID                    TEXT,
    BRAND                          TEXT,
    BRAND_NAME                     TEXT,
    MAIN_BRAND                     TEXT,
    BUSINESS_UNIT                  TEXT,
    BUSSUNIT_DESC                  TEXT,
    BOX_DESC                       TEXT,
    STORE_COMP_STATUS              TEXT,
    STORE_COMP_EFFECTIVE_DATE      TEXT,
    STORE_COMP_DISCONTINUE_DATE    TEXT,
    SOLO_MULTIBOX                  TEXT,
    LEGACY_STORE_CODE              TEXT,
    RFID_ENABLED                   TEXT,
    ELIGIBLE_FOR_FORECAST          TEXT
)
"""

DDL_STORE_GRADE = """
CREATE TABLE IF NOT EXISTS store_grade (
    STORE_GRADE_ID        INTEGER PRIMARY KEY AUTOINCREMENT,
    BRAND                 TEXT,
    LOCATION              INTEGER NOT NULL,
    COUNTRY               TEXT,
    DEPT                  INTEGER,
    CLASS                 INTEGER,
    SUBCLASS              INTEGER,
    GRADE                 TEXT,
    CREATE_DATETIME       TEXT,
    LAST_UPDATE_ID        TEXT,
    PUBLISH_STATUS        TEXT DEFAULT 'N'
)
"""

DDL_GRADING_RUN_LOG = """
CREATE TABLE IF NOT EXISTS grading_run_log (
    RUN_ID          INTEGER PRIMARY KEY AUTOINCREMENT,
    BRAND           TEXT,
    DEPT            INTEGER,
    CLASS           INTEGER,
    SUBCLASS        INTEGER,
    COUNTRY         TEXT,
    STORE           INTEGER,
    LEVEL           TEXT,
    CLUSTERS        INTEGER,
    FROM_DATE       TEXT,
    TO_DATE         TEXT,
    STATUS          TEXT, -- SUBMITTED, IN_PROGRESS, COMPLETED, ERROR
    MESSAGE         TEXT,
    START_TIME      TEXT,
    END_TIME        TEXT
)
"""

DDL_FORECASTS_FACT = """
CREATE TABLE IF NOT EXISTS forecasts_fact (
    OPTION_ID    TEXT,
    STORE        INTEGER,
    TIME_ID      INTEGER,
    UNITS        REAL,
    MODEL_USED   TEXT,
    PRIMARY KEY (OPTION_ID, STORE, TIME_ID)
)
"""

ORACLE_DDL_REFERENCE = """
-- Oracle-compatible DDL (reference only — app uses SQLite)
CREATE TABLE store_grade (
    STORE_GRADE_ID        NUMBER            NOT NULL,
    BRAND                 VARCHAR2(12 BYTE),
    LOCATION              NUMBER(10,0)      NOT NULL,
    COUNTRY               VARCHAR2(10 BYTE),
    DEPT                  NUMBER(4,0),
    CLASS                 NUMBER(4,0),
    SUBCLASS              NUMBER(4,0),
    GRADE                 VARCHAR2(10 CHAR),
    CREATE_DATETIME       DATE,
    CREATE_ID             VARCHAR2(200 BYTE),
    LAST_UPDATE_DATETIME  DATE,
    LAST_UPDATE_ID        VARCHAR2(200 BYTE),
    CONSTRAINT pk_store_grade PRIMARY KEY (STORE_GRADE_ID)
);
CREATE SEQUENCE store_grade_seq START WITH 1 INCREMENT BY 1;
"""


# ─── Loaders ─────────────────────────────────────────────────────────────────

def _detect_encoding(csv_path: str) -> str:
    """Read full file bytes to determine if the file is UTF-8 or Latin-1."""
    with open(csv_path, 'rb') as f:
        raw = f.read()
    try:
        raw.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        return 'latin-1'


def _load_csv_to_table(conn: sqlite3.Connection, csv_name: str, table: str,
                        chunksize: int = 10_000) -> int:
    csv_path = find_csv(csv_name)
    print(f"  Loading {csv_name} -> {table}  (from {csv_path})")
    encoding = _detect_encoding(csv_path)
    if encoding != 'utf-8':
        print(f"    Detected encoding: {encoding}")

    total = 0
    first = True
    for chunk in pd.read_csv(csv_path, chunksize=chunksize, low_memory=False, encoding=encoding):
        chunk.columns = [c.strip().upper() for c in chunk.columns]
        # First chunk replaces the table (clears any partial previous load), rest appends
        mode = "replace" if first else "append"
        chunk.to_sql(table, conn, if_exists=mode, index=False)
        total += len(chunk)
        first = False

    print(f"    -> {total} rows loaded")
    return total


def init_db(force_reload: bool = False) -> None:
    """Create tables and load CSVs. Pass force_reload=True to drop & reload source tables."""
    conn = get_db()
    cur = conn.cursor()

    print("Creating tables...")
    for ddl in [DDL_SALES_HIST_FACT, DDL_PRODUCT_OPTION_DIM, DDL_LOCATION_ST_MASTER, DDL_STORE_GRADE, DDL_GRADING_RUN_LOG, DDL_FORECASTS_FACT]:
        cur.execute(ddl)
    
    # Migration for PUBLISH_STATUS if it doesn't exist
    try:
        cur.execute("ALTER TABLE store_grade ADD COLUMN PUBLISH_STATUS TEXT DEFAULT 'N'")
    except sqlite3.OperationalError:
        pass  # Column already exists
        
    conn.commit()

    for table, csv_file in [
        ("sales_hist_fact",   "sales_hist_fact.csv"),
        ("product_option_dim","product_option_dim.csv"),
        ("location_st_master","location_st_master.csv"),
    ]:
        row_count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if row_count > 0 and not force_reload:
            print(f"  {table}: already has {row_count} rows — skipping load (use force_reload=True to reload)")
        else:
            if force_reload:
                cur.execute(f"DELETE FROM {table}")
                conn.commit()
            _load_csv_to_table(conn, csv_file, table)

    conn.close()
    print(f"\n[OK] Database ready: {DB_PATH}")


if __name__ == "__main__":
    force = "--force" in sys.argv
    print(f"{'Force-reloading' if force else 'Initializing'} database...")
    init_db(force_reload=force)
