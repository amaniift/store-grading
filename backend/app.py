"""
app.py — Flask REST API for the Store Grading Tool.

Endpoints:
  GET  /api/filters               — distinct filter options
  GET  /api/classes?dept=X        — cascading: classes for a dept
  GET  /api/subclasses?dept=X&class=Y — cascading: subclasses
  GET  /api/store-grades          — query store_grade table
  POST /api/generate-grades       — trigger K-means grading
  GET  /                          — serve frontend
"""

from database import get_db, init_db
import pandas as pd
import importlib.util
import os
import sys
import json
import traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

_grading_spec = importlib.util.spec_from_file_location(
    "store_grading_engine",
    os.path.join(BASE_DIR, "store-grading.py")
)
_grading_mod = importlib.util.module_from_spec(_grading_spec)
_grading_spec.loader.exec_module(_grading_mod)
run_grading = _grading_mod.run_grading
update_store_grades = _grading_mod.update_store_grades

# Background Task Executor
executor = ThreadPoolExecutor(max_workers=4)

# ─── App Setup ───────────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# ─── Helper ──────────────────────────────────────────────────────────────────


def rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


def log_grading_run(params: dict) -> int:
    """Create initial log entry for a grading run."""
    conn = get_db()
    now = datetime.now().isoformat()
    cur = conn.execute("""
        INSERT INTO grading_run_log (
            DEPT, CLASS, SUBCLASS, LEVEL, COUNTRY, STORE, CLUSTERS, 
            FROM_DATE, TO_DATE, STATUS, START_TIME
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'SUBMITTED', ?)
    """, (
        params.get("dept"), params.get("class"), params.get("subclass"),
        params.get("level"), params.get("country"), params.get("store"),
        params.get("clusters"), params.get("from_date"), params.get("to_date"),
        now
    ))
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id


def update_run_status(run_id: int, status: str, message: str = None):
    """Update status, end_time and message for a grading run."""
    conn = get_db()
    end_time = datetime.now().isoformat() if status in [
        'COMPLETED', 'ERROR'] else None
    conn.execute("""
        UPDATE grading_run_log 
        SET STATUS=?, MESSAGE=?, END_TIME=? 
        WHERE RUN_ID=?
    """, (status, message, end_time, run_id))
    conn.commit()
    conn.close()


def background_grading_task(run_id: int, params: dict):
    """Task executed in worker thread."""
    try:
        update_run_status(run_id, 'IN_PROGRESS')
        result = run_grading(
            dept=int(params.get("dept")),
            class_=int(params.get("class")) if params.get("class") else None,
            level=params.get("level", "class"),
            subclass=int(params.get("subclass")) if params.get(
                "subclass") else None,
            store=int(params.get("store")) if params.get("store") else None,
            country=params.get("country") or None,
            n_clusters=int(params.get("clusters", 3)),
            from_date=params.get("from_date"),
            to_date=params.get("to_date")
        )
        msg = f"Completed. {result.get('inserts', 0)} inserts, {result.get('updates', 0)} updates."
        update_run_status(run_id, 'COMPLETED', msg)
    except Exception as e:
        traceback.print_exc()
        update_run_status(run_id, 'ERROR', str(e))


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# ── Filter Data ──────────────────────────────────────────────────────────────

@app.route("/api/filters")
def get_filters():
    """
    Returns distinct values for all filter dropdowns.
    Dept, Class, Subclass sourced from product_option_dim.
    Store, Country sourced from location_st_master.
    """
    try:
        conn = get_db()

        depts = rows_to_list(conn.execute(
            "SELECT DISTINCT DEPT, DEPT_NAME FROM product_option_dim "
            "WHERE DEPT IS NOT NULL ORDER BY DEPT"
        ).fetchall())

        classes = rows_to_list(conn.execute(
            "SELECT DISTINCT DEPT, CLASS, CLASS_NAME FROM product_option_dim "
            "WHERE CLASS IS NOT NULL ORDER BY DEPT, CLASS"
        ).fetchall())

        subclasses = rows_to_list(conn.execute(
            "SELECT DISTINCT DEPT, CLASS, SUBCLASS, SUB_NAME FROM product_option_dim "
            "WHERE SUBCLASS IS NOT NULL ORDER BY DEPT, CLASS, SUBCLASS"
        ).fetchall())

        stores = rows_to_list(conn.execute(
            "SELECT DISTINCT STORE, STORE_NAME, AREA_NAME FROM location_st_master "
            "WHERE STORE IS NOT NULL ORDER BY STORE_NAME"
        ).fetchall())

        countries = rows_to_list(conn.execute(
            "SELECT DISTINCT AREA_NAME FROM location_st_master "
            "WHERE AREA_NAME IS NOT NULL AND AREA_NAME != '' ORDER BY AREA_NAME"
        ).fetchall())

        types = [r["STORE_TYPE"] for r in rows_to_list(conn.execute(
            "SELECT DISTINCT STORE_TYPE FROM location_st_master "
            "WHERE STORE_TYPE IS NOT NULL ORDER BY STORE_TYPE"
        ).fetchall())]

        time_ids = [r["TIME_ID"] for r in rows_to_list(conn.execute(
            "SELECT DISTINCT TIME_ID FROM sales_hist_fact "
            "WHERE TIME_ID IS NOT NULL ORDER BY TIME_ID DESC"
        ).fetchall())]

        conn.close()
        return jsonify({
            "depts":      depts,
            "classes":    classes,
            "subclasses": subclasses,
            "stores":     stores,
            "countries":  countries,
            "types":      types,
            "time_ids":   time_ids,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/classes")
def get_classes():
    dept = request.args.get("dept", type=int)
    if not dept:
        return jsonify({"error": "dept is required"}), 400
    try:
        conn = get_db()
        rows = rows_to_list(conn.execute(
            "SELECT DISTINCT CLASS, CLASS_NAME FROM product_option_dim "
            "WHERE DEPT=? AND CLASS IS NOT NULL ORDER BY CLASS", (dept,)
        ).fetchall())
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/subclasses")
def get_subclasses():
    dept = request.args.get("dept",  type=int)
    class_ = request.args.get("class", type=int)
    if not dept or not class_:
        return jsonify({"error": "dept and class are required"}), 400
    try:
        conn = get_db()
        rows = rows_to_list(conn.execute(
            "SELECT DISTINCT SUBCLASS, SUB_NAME FROM product_option_dim "
            "WHERE DEPT=? AND CLASS=? AND SUBCLASS IS NOT NULL ORDER BY SUBCLASS",
            (dept, class_)
        ).fetchall())
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Admin Page ──────────────────────────────────────────────────────────────

@app.route("/api/admin/graded-scopes")
def get_graded_scopes():
    """
    Returns unique combinations of Brand/Dept/Class/Subclass that have grades.
    """
    brand = request.args.get("brand")
    dept = request.args.get("dept",     type=int)
    class_ = request.args.get("class",    type=int)
    subclass = request.args.get("subclass", type=int)

    try:
        conn = get_db()
        sql = """
            SELECT 
                s.BRAND, s.DEPT, p.DEPT_NAME, s.CLASS, p.CLASS_NAME, 
                s.SUBCLASS, p.SUB_NAME, COUNT(*) as STORE_COUNT
            FROM (SELECT DISTINCT BRAND, DEPT, CLASS, SUBCLASS, LOCATION FROM store_grade) s
            LEFT JOIN product_option_dim p ON s.DEPT=p.DEPT AND s.CLASS=p.CLASS 
                AND (s.SUBCLASS=p.SUBCLASS OR (s.SUBCLASS IS NULL AND p.SUBCLASS IS NULL))
            WHERE 1=1
        """
        params = []
        if brand:
            sql += " AND s.BRAND = ?"
            params.append(brand)
        if dept:
            sql += " AND s.DEPT = ?"
            params.append(dept)
        if class_:
            sql += " AND s.CLASS = ?"
            params.append(class_)
        if subclass:
            sql += " AND s.SUBCLASS = ?"
            params.append(subclass)

        sql += " GROUP BY s.BRAND, s.DEPT, s.CLASS, s.SUBCLASS ORDER BY s.BRAND, s.DEPT, s.CLASS, s.SUBCLASS"

        rows = conn.execute(sql, params).fetchall()

        # Format the grouped results
        result = []
        for r in rows:
            result.append({
                "brand": r["BRAND"],
                "dept": r["DEPT"],
                "dept_name": r["DEPT_NAME"] or f"Dept {r['DEPT']}",
                "class": r["CLASS"],
                "class_name": r["CLASS_NAME"] or f"Class {r['CLASS']}",
                "subclass": r["SUBCLASS"],
                "subclass_name": r["SUB_NAME"] if r["SUBCLASS"] is not None else "CLASS LEVEL",
                "count": r["STORE_COUNT"]
            })

        conn.close()
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/bulk-delete-grades", methods=["POST"])
def bulk_delete_grades():
    """
    Deletes store grades for multiple provided scopes.
    Body: [{"brand": "...", "dept": ..., "class": ..., "subclass": ...}, ...]
    """
    scopes = request.json
    if not isinstance(scopes, list):
        return jsonify({"error": "Expected a list of scopes"}), 400

    try:
        conn = get_db()
        total_deleted = 0

        for scope in scopes:
            brand = scope.get("brand")
            dept = scope.get("dept")
            cls = scope.get("class")
            sub = scope.get("subclass")  # Can be null

            if not brand or dept is None or cls is None:
                continue

            if sub is None:
                query = "DELETE FROM store_grade WHERE BRAND=? AND DEPT=? AND CLASS=? AND SUBCLASS IS NULL"
                params = (brand, dept, cls)
            else:
                query = "DELETE FROM store_grade WHERE BRAND=? AND DEPT=? AND CLASS=? AND SUBCLASS=?"
                params = (brand, dept, cls, sub)

            cursor = conn.execute(query, params)
            total_deleted += cursor.rowcount

        conn.commit()
        conn.close()
        return jsonify({"success": True, "deleted_count": total_deleted})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Store Grades ─────────────────────────────────────────────────────────────

@app.route("/api/store-grades")
def get_store_grades():
    """
    Query store_grade with optional filters.
    Required: dept, class
    Optional: subclass, store, country, page, page_size
    """
    dept = request.args.get("dept",     type=int)
    class_ = request.args.get("class",    type=int)
    subclass = request.args.get("subclass", type=int, default=None)
    store = request.args.get("store",    type=int, default=None)
    country = request.args.get("country",  type=str, default=None)
    level = request.args.get("level",  type=str, default="class")
    page = request.args.get("page",     type=int, default=1)
    page_size = request.args.get("page_size", type=int, default=100)

    if not dept:
        return jsonify({"error": "dept is required"}), 400

    try:
        conn = get_db()

        sql = """
            SELECT
                sg.STORE_GRADE_ID,
                sg.BRAND,
                sg.LOCATION,
                l.STORE_NAME,
                sg.COUNTRY,
                sg.DEPT,
                p_dept.DEPT_NAME,
                sg.CLASS,
                p_cls.CLASS_NAME,
                sg.SUBCLASS,
                p_sub.SUB_NAME,
                sg.GRADE,
                sg.CREATE_DATETIME,
                sg.CREATE_ID,
                sg.LAST_UPDATE_DATETIME,
                sg.LAST_UPDATE_ID,
                sg.PUBLISH_STATUS
            FROM store_grade sg
            LEFT JOIN location_st_master l ON sg.LOCATION = l.STORE
            LEFT JOIN (
                SELECT DISTINCT DEPT, DEPT_NAME FROM product_option_dim
            ) p_dept ON sg.DEPT = p_dept.DEPT
            LEFT JOIN (
                SELECT DISTINCT DEPT, CLASS, CLASS_NAME FROM product_option_dim
            ) p_cls ON sg.DEPT = p_cls.DEPT AND sg.CLASS = p_cls.CLASS
            LEFT JOIN (
                SELECT DISTINCT DEPT, CLASS, SUBCLASS, SUB_NAME FROM product_option_dim
            ) p_sub ON sg.DEPT = p_sub.DEPT AND sg.CLASS = p_sub.CLASS
                    AND sg.SUBCLASS = p_sub.SUBCLASS
            WHERE sg.DEPT = ?
        """
        params: list = [dept]

        if class_ is not None:
            sql += " AND sg.CLASS = ?"
            params.append(class_)

        # Level filter logic:
        # class level = SUBCLASS is NULL
        # subclass level = SUBCLASS is NOT NULL
        if level == "class":
            sql += " AND sg.SUBCLASS IS NULL"
        else:
            sql += " AND sg.SUBCLASS IS NOT NULL"

        if subclass is not None:
            sql += " AND sg.SUBCLASS = ?"
            params.append(subclass)

        if store is not None:
            sql += " AND sg.LOCATION = ?"
            params.append(store)

        if country:
            sql += " AND sg.COUNTRY = ?"
            params.append(country)

        # Count total
        count_sql = f"SELECT COUNT(*) FROM ({sql})"
        total = conn.execute(count_sql, params).fetchone()[0]

        # Calculate grade counts for stats
        stats_sql = f"SELECT GRADE, COUNT(*) FROM ({sql}) GROUP BY GRADE"
        stats_rows = conn.execute(stats_sql, params).fetchall()
        grade_counts = {str(r[0]): r[1] for r in stats_rows}

        # Paginate
        offset = (page - 1) * page_size
        sql += f" ORDER BY sg.GRADE, sg.LOCATION LIMIT {page_size} OFFSET {offset}"
        rows = rows_to_list(conn.execute(sql, params).fetchall())
        conn.close()

        return jsonify({
            "total": total,
            "grade_counts": grade_counts,
            "page":  page,
            "page_size": page_size,
            "data":  rows,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Generate Grades ───────────────────────────────────────────────────────────

@app.route("/api/generate-grades", methods=["POST"])
def generate_grades():
    """
    Trigger the K-means grading process.
    Body JSON:
      {
        "dept":     108,
        "class":    3,
        "level":    "class" | "subclass",
        "subclass": null,      (optional)
        "store":    null,      (optional)
        "country":  "SAU",    (optional)
        "clusters": 3          (optional)
      }
    """
    body = request.get_json(silent=True) or {}
    dept = body.get("dept")
    class_ = body.get("class")
    level = body.get("level", "class")
    subclass = body.get("subclass")
    store = body.get("store")
    country = body.get("country")
    clusters = body.get("clusters", 3)
    from_date = body.get("from_date")
    to_date = body.get("to_date")

    if not dept:
        return jsonify({"error": "dept is required"}), 400

    try:
        # 1. Log the submission
        run_id = log_grading_run(body)

        # 2. Dispatch to background thread
        executor.submit(background_grading_task, run_id, body)

        return jsonify({"status": "submitted", "run_id": run_id}), 202
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/grading-runs")
def get_grading_runs():
    """Fetch history of grading runs."""
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM grading_run_log ORDER BY RUN_ID DESC LIMIT 50").fetchall()
        conn.close()
        return jsonify({"data": rows_to_list(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Product Master ────────────────────────────────────────────────────────────

@app.route("/api/product-master")
def get_product_master():
    """
    Paginated product master data from product_option_dim.
    Optional filters: dept, class, subclass, brand, search (OPTION_ID / OPTION_DESC).
    """
    dept = request.args.get("dept",     type=int,  default=None)
    class_ = request.args.get("class",    type=int,  default=None)
    subclass = request.args.get("subclass", type=int,  default=None)
    brand = request.args.get("brand",    type=str,  default=None)
    search = request.args.get("search",   type=str,  default=None)
    page = request.args.get("page",     type=int,  default=1)
    page_size = request.args.get("page_size", type=int, default=50)

    try:
        conn = get_db()

        sql = """
            SELECT
                BRAND, OPTION_ID, OPTION_DESC, VPN,
                DEPT, DEPT_NAME, CLASS, CLASS_NAME,
                SUBCLASS, SUB_NAME,
                FABRIC, COLOR_SHADE, COLOR_FAMILY,
                SEASON_CODE, SEASONALITY, SILHOUETTE,
                GENDER, PRICE_STRATEGY, SELLING_PHASE,
                LABEL, COLLECTION
            FROM product_option_dim
            WHERE 1=1
        """
        params: list = []

        if dept is not None:
            sql += " AND DEPT = ?"
            params.append(dept)
        if class_ is not None:
            sql += " AND CLASS = ?"
            params.append(class_)
        if subclass is not None:
            sql += " AND SUBCLASS = ?"
            params.append(subclass)
        if brand:
            sql += " AND BRAND = ?"
            params.append(brand)
        if search:
            sql += " AND (OPTION_ID LIKE ? OR OPTION_DESC LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]

        total = conn.execute(
            f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
        offset = (page - 1) * page_size
        sql += f" ORDER BY BRAND, DEPT, CLASS, SUBCLASS, OPTION_ID LIMIT {page_size} OFFSET {offset}"
        rows = rows_to_list(conn.execute(sql, params).fetchall())

        # distinct brands for filter dropdown
        brands = [r["BRAND"] for r in rows_to_list(
            conn.execute(
                "SELECT DISTINCT BRAND FROM product_option_dim WHERE BRAND IS NOT NULL ORDER BY BRAND").fetchall()
        )]

        conn.close()
        return jsonify({"total": total, "page": page, "page_size": page_size,
                        "brands": brands, "data": rows})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/location-master")
def get_location_master():
    """
    Paginated location master from location_st_master.
    Optional filters: country (AREA_NAME), city, type (STORE_TYPE), search (STORE/STORE_NAME).
    """
    country = request.args.get("country",   type=str, default=None)
    city = request.args.get("city",      type=str, default=None)
    type_ = request.args.get("type",      type=str, default=None)
    search = request.args.get("search",    type=str, default=None)
    page = request.args.get("page",      type=int, default=1)
    page_size = request.args.get("page_size", type=int, default=50)

    try:
        conn = get_db()
        sql = """
            SELECT 
                STORE, STORE_NAME, AREA_NAME AS COUNTRY, 
                CITY, CURRENCY_CODE, CHANNEL_TYPE, TOTAL_SQUARE_FT, 
                MALL_NAME, BRAND_NAME, DEFAULT_WH, CHANNEL_NAME
            FROM location_st_master
            WHERE 1=1
        """
        params = []
        if country:
            sql += " AND AREA_NAME = ?"
            params.append(country)
        if city:
            sql += " AND CITY = ?"
            params.append(city)
        if type_:
            sql += " AND STORE_TYPE = ?"
            params.append(type_)
        if search:
            sql += " AND (CAST(STORE AS TEXT) LIKE ? OR STORE_NAME LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]

        total = conn.execute(
            f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
        offset = (page - 1) * page_size
        sql += f" ORDER BY AREA_NAME, CITY, STORE LIMIT {page_size} OFFSET {offset}"
        rows = rows_to_list(conn.execute(sql, params).fetchall())

        # Metadata for filters
        countries = [r["AREA_NAME"] for r in rows_to_list(
            conn.execute(
                "SELECT DISTINCT AREA_NAME FROM location_st_master WHERE AREA_NAME IS NOT NULL ORDER BY AREA_NAME").fetchall()
        )]
        types = [r["STORE_TYPE"] for r in rows_to_list(
            conn.execute(
                "SELECT DISTINCT STORE_TYPE FROM location_st_master WHERE STORE_TYPE IS NOT NULL ORDER BY STORE_TYPE").fetchall()
        )]

        conn.close()
        return jsonify({
            "total": total, "page": page, "page_size": page_size,
            "countries": countries, "types": types, "data": rows
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Sales History ─────────────────────────────────────────────────────────────

@app.route("/api/sales-history")
def get_sales_history():
    """
    Aggregated sales history at configurable hierarchy + location levels.
    level    : dept | class | subclass | sku
    loc_level: country | store  (controls location grouping granularity)
    Optional : dept, class, subclass, store (only used when loc_level=store), country, date_from, date_to
    """
    level = request.args.get("level",     type=str, default="class")
    loc_level = request.args.get("loc_level", type=str, default="store")
    dept = request.args.get("dept",      type=int, default=None)
    class_ = request.args.get("class",     type=int, default=None)
    subclass = request.args.get("subclass",  type=int, default=None)
    store = request.args.get("store",     type=int, default=None)
    country = request.args.get("country",   type=str, default=None)
    date_from = request.args.get("date_from", type=str, default=None)
    date_to = request.args.get("date_to",   type=str, default=None)
    page = request.args.get("page",      type=int, default=1)
    page_size = request.args.get("page_size", type=int, default=50)

    valid_levels = ("dept", "class", "subclass", "sku")
    valid_loc_levels = ("country", "store")
    if level not in valid_levels:
        return jsonify({"error": f"level must be one of {valid_levels}"}), 400
    if loc_level not in valid_loc_levels:
        return jsonify({"error": f"loc_level must be one of {valid_loc_levels}"}), 400

    try:
        conn = get_db()

        # Base query: join sales → product → location
        base_sql = """
            FROM sales_hist_fact s
            JOIN product_option_dim p ON s.OPTION_ID = p.OPTION_ID
            LEFT JOIN location_st_master l ON s.STORE = l.STORE
            WHERE 1=1
        """
        params: list = []

        if dept is not None:
            base_sql += " AND p.DEPT = ?"
            params.append(dept)
        if class_ is not None:
            base_sql += " AND p.CLASS = ?"
            params.append(class_)
        if subclass is not None:
            base_sql += " AND p.SUBCLASS = ?"
            params.append(subclass)
        # Store filter only applied at store level
        if store is not None and loc_level == "store":
            base_sql += " AND s.STORE = ?"
            params.append(store)
        if country:
            base_sql += " AND l.AREA_NAME = ?"
            params.append(country)
        if date_from:
            base_sql += " AND s.TIME_ID >= ?"
            params.append(date_from)
        if date_to:
            base_sql += " AND s.TIME_ID <= ?"
            params.append(date_to)

        # Product hierarchy dims per level
        level_dims = {
            "dept":     ["p.BRAND", "p.DEPT", "p.DEPT_NAME"],
            "class":    ["p.BRAND", "p.DEPT", "p.DEPT_NAME", "p.CLASS", "p.CLASS_NAME"],
            "subclass": ["p.BRAND", "p.DEPT", "p.DEPT_NAME", "p.CLASS", "p.CLASS_NAME",
                         "p.SUBCLASS", "p.SUB_NAME"],
            "sku":      ["p.BRAND", "p.DEPT", "p.DEPT_NAME", "p.CLASS", "p.CLASS_NAME",
                         "p.SUBCLASS", "p.SUB_NAME", "p.OPTION_ID", "p.OPTION_DESC"],
        }

        # Location dims depend on loc_level
        # For SELECT we alias l.AREA_NAME → COUNTRY; for GROUP BY we use the raw column
        if loc_level == "country":
            loc_select = ["l.AREA_NAME AS COUNTRY"]
            loc_groupby = ["l.AREA_NAME"]
        else:  # store
            loc_select = ["s.STORE", "l.STORE_NAME", "l.AREA_NAME AS COUNTRY"]
            loc_groupby = ["s.STORE", "l.STORE_NAME", "l.AREA_NAME"]

        sel_cols = level_dims[level] + loc_select
        grp_cols = level_dims[level] + loc_groupby
        select_str = ", ".join(sel_cols)
        group_by = ", ".join(grp_cols)

        agg_cols = """
            SUM(s.REGULAR_SLS_UNITS)  AS REGULAR_UNITS,
            SUM(s.PROMO_SLS_UNITS)    AS PROMO_UNITS,
            SUM(s.MRKDWN_SLS_UNITS)   AS MRKDWN_UNITS,
            SUM(s.REGULAR_SLS_UNITS + s.PROMO_SLS_UNITS + s.MRKDWN_SLS_UNITS) AS TOTAL_UNITS,
            SUM(s.BASE_HISTORY)        AS BASE_HISTORY,
            COUNT(DISTINCT s.TIME_ID)  AS WEEKS_WITH_SALES
        """

        agg_sql = f"SELECT {select_str}, {agg_cols} {base_sql} GROUP BY {group_by}"

        total = conn.execute(
            f"SELECT COUNT(*) FROM ({agg_sql})", params).fetchone()[0]

        offset = (page - 1) * page_size
        paged_sql = agg_sql + \
            f" ORDER BY TOTAL_UNITS DESC LIMIT {page_size} OFFSET {offset}"
        rows = rows_to_list(conn.execute(paged_sql, params).fetchall())

        conn.close()
        return jsonify({"total": total, "page": page, "page_size": page_size,
                        "level": level, "loc_level": loc_level, "data": rows})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ─── Startup ─────────────────────────────────────────────────────────────────


@app.route("/api/publish-grades", methods=["POST"])
def publish_grades():
    try:
        data = request.json
        updates = data.get("updates", [])
        if not updates:
            return jsonify({"error": "No updates provided"}), 400

        conn = get_db()
        count = update_store_grades(conn, updates)
        conn.close()

        return jsonify({"status": "success", "updated": count})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/forecast", methods=["POST"])
def generate_forecast():
    """
    Aggregated forecast endpoint.
    Accepts individual filter parameters — all optional except dept (minimum scope).
    Aggregates historical sales at whatever product-hierarchy + location scope is selected,
    then runs the forecasting model on the aggregated time series.

    Body JSON:
      {
        "dept": 107,                (required — minimum scope)
        "class_": 3,                (optional)
        "subclass": 6,              (optional)
        "item_id": "130213005_...", (optional — specific SKU)
        "store_id": "33186",        (optional — specific store)
        "country": "SAU",           (optional — filter by country/area)
        "model": "exponential_smoothing" | "arima",
        "force_compute": false
      }
    """
    body = request.get_json(silent=True) or {}
    dept = body.get("dept")
    class_ = body.get("class")
    subclass = body.get("subclass")
    item_id = body.get("item_id")       # specific SKU
    store_id = body.get("store_id")      # specific store
    country = body.get("country")       # country/area filter
    model_requested = body.get("model")
    model_type = model_requested or "exponential_smoothing"
    model_params = body.get("model_params") or {}
    force_compute = body.get("force_compute", False)

    if not dept:
        return jsonify({"error": "Department is required (minimum scope)."}), 400

    conn = get_db()

    # ── Build dynamic WHERE clause ─────────────────────────────────────────
    def _build_filters():
        """Returns (where_clauses[], params[]) for both history and forecast queries."""
        clauses = []
        params = []

        # Product hierarchy filters (always join through product_option_dim)
        clauses.append("p.DEPT = ?")
        params.append(int(dept))

        if class_:
            clauses.append("p.CLASS = ?")
            params.append(int(class_))
        if subclass:
            clauses.append("p.SUBCLASS = ?")
            params.append(int(subclass))
        if item_id:
            clauses.append("p.OPTION_ID = ?")
            params.append(str(item_id))

        # Location filters
        if store_id:
            clauses.append("s.STORE = ?")
            params.append(int(store_id))
        if country:
            clauses.append("l.AREA_NAME = ?")
            params.append(country)

        return clauses, params

    where_clauses, query_params = _build_filters()
    where_sql = " AND ".join(where_clauses)

    scope_descriptor = {
        "dept": int(dept),
        "class": int(class_) if class_ else None,
        "subclass": int(subclass) if subclass else None,
        "item_id": str(item_id) if item_id else None,
        "store_id": int(store_id) if store_id else None,
        "country": country or None,
        "model": model_type,
    }
    scope_key = json.dumps(
        scope_descriptor, sort_keys=True, separators=(",", ":"))

    cache_table_sql = """
        CREATE TABLE IF NOT EXISTS forecast_agg_cache (
            CACHE_KEY       TEXT PRIMARY KEY,
            SCOPE_JSON      TEXT NOT NULL,
            MODEL_USED      TEXT NOT NULL,
            SOURCE          TEXT NOT NULL,
            HISTORICAL_DATES TEXT NOT NULL,
            HISTORICAL_SALES TEXT NOT NULL,
            FORECAST_DATES   TEXT NOT NULL,
            FORECAST_SALES   TEXT NOT NULL,
            LAST_UPDATED     TEXT NOT NULL
        )
    """

    hist_query = f"""
        SELECT s.TIME_ID, SUM(s.REGULAR_SLS_UNITS + s.PROMO_SLS_UNITS + s.MRKDWN_SLS_UNITS) AS TOTAL_SALES
        FROM sales_hist_fact s
        JOIN product_option_dim p ON s.OPTION_ID = p.OPTION_ID
        LEFT JOIN location_st_master l ON s.STORE = l.STORE
        WHERE {where_sql}
        GROUP BY s.TIME_ID
        ORDER BY s.TIME_ID ASC
    """

    # ── 1. Try pre-computed forecasts (aggregated from forecasts_fact) ──────
    if not force_compute:
        # First prefer latest live-computed aggregate for this exact scope/model.
        try:
            conn.execute(cache_table_sql)
            cache_row = conn.execute(
                """
                SELECT MODEL_USED, SOURCE, HISTORICAL_DATES, HISTORICAL_SALES,
                       FORECAST_DATES, FORECAST_SALES
                FROM forecast_agg_cache
                WHERE CACHE_KEY = ?
                """,
                (scope_key,),
            ).fetchone()
        except Exception:
            cache_row = None

        if cache_row:
            try:
                historical_dates = json.loads(cache_row["HISTORICAL_DATES"])
                historical_sales = json.loads(cache_row["HISTORICAL_SALES"])
                forecast_dates = json.loads(cache_row["FORECAST_DATES"])
                forecast_sales = json.loads(cache_row["FORECAST_SALES"])
            except Exception:
                historical_dates = []
                historical_sales = []
                forecast_dates = []
                forecast_sales = []

            if forecast_dates and forecast_sales:
                conn.close()
                return jsonify({
                    "status": "success",
                    "source": "cached live computation",
                    "model_used": cache_row["MODEL_USED"] or model_type,
                    "historical_dates": historical_dates,
                    "historical_sales": historical_sales,
                    "forecast_dates": forecast_dates,
                    "forecast_sales": forecast_sales,
                })

        # Build forecast aggregation query from forecasts_fact
        fc_clauses = []
        fc_params = []
        fc_clauses.append("p.DEPT = ?")
        fc_params.append(int(dept))
        if class_:
            fc_clauses.append("p.CLASS = ?")
            fc_params.append(int(class_))
        if subclass:
            fc_clauses.append("p.SUBCLASS = ?")
            fc_params.append(int(subclass))
        if item_id:
            fc_clauses.append("f.OPTION_ID = ?")
            fc_params.append(str(item_id))
        if store_id:
            fc_clauses.append("f.STORE = ?")
            fc_params.append(int(store_id))
        if country:
            fc_clauses.append("l.AREA_NAME = ?")
            fc_params.append(country)
        if model_requested:
            fc_clauses.append("f.MODEL_USED = ?")
            fc_params.append(model_type)

        fc_where = " AND ".join(fc_clauses)

        cached_query = f"""
            SELECT f.TIME_ID, SUM(f.UNITS) AS TOTAL_UNITS, f.MODEL_USED
            FROM forecasts_fact f
            JOIN product_option_dim p ON f.OPTION_ID = p.OPTION_ID
            LEFT JOIN location_st_master l ON f.STORE = l.STORE
            WHERE {fc_where}
            GROUP BY f.TIME_ID
            ORDER BY f.TIME_ID ASC
        """
        try:
            cached_df = pd.read_sql_query(cached_query, conn, params=fc_params)
        except Exception:
            cached_df = pd.DataFrame()

        if not cached_df.empty:
            # Fetch aggregated historical data too
            hist_df = pd.read_sql_query(hist_query, conn, params=query_params)
            conn.close()
            return jsonify({
                "status": "success",
                "source": "pre-computed (aggregated)",
                "model_used": cached_df["MODEL_USED"].iloc[0] if "MODEL_USED" in cached_df.columns else "exponential_smoothing",
                "historical_dates": hist_df["TIME_ID"].astype(str).tolist(),
                "historical_sales": hist_df["TOTAL_SALES"].tolist(),
                "forecast_dates": cached_df["TIME_ID"].astype(str).tolist(),
                "forecast_sales": [round(v, 2) for v in cached_df["TOTAL_UNITS"].tolist()]
            })

    # ── 2. Live computation on aggregated historical series ────────────────
    df = pd.read_sql_query(hist_query, conn, params=query_params)
    conn.close()

    if df.empty or len(df) < 5:
        return jsonify({"error": "Insufficient historical data for the selected scope."}), 400

    series = df["TOTAL_SALES"].values
    last_time_id = df["TIME_ID"].iloc[-1]

    def _as_int(value, fallback, minimum=1):
        try:
            parsed = int(value)
            return parsed if parsed >= minimum else fallback
        except (TypeError, ValueError):
            return fallback

    def _as_bool(value, fallback=False):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        if isinstance(value, (int, float)):
            return bool(value)
        return fallback

    def _normalize_hw_component(value):
        if value is None:
            return None
        raw = str(value).strip().lower()
        mapping = {
            "none": None,
            "null": None,
            "": None,
            "add": "add",
            "additive": "add",
            "mul": "mul",
            "multiplicative": "mul",
        }
        return mapping.get(raw, None)

    forecast_weeks = _as_int(model_params.get("forecast_horizon"), 52)
    model_params_used = {"forecast_horizon": forecast_weeks}

    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        from statsmodels.tsa.arima.model import ARIMA

        if model_type == "exponential_smoothing":
            # Accept both UI-friendly keys (trend_type/seasonality_type/seasonal_period)
            # and statsmodels keys (trend/seasonal/seasonal_periods) for compatibility.
            trend_raw = model_params.get(
                "trend_type", model_params.get("trend", "additive"))
            seasonal_raw = model_params.get(
                "seasonality_type", model_params.get("seasonal", "none"))
            trend = _normalize_hw_component(trend_raw)
            seasonal = _normalize_hw_component(seasonal_raw)
            seasonal_periods = _as_int(
                model_params.get("seasonal_period",
                                 model_params.get("seasonal_periods", 52)),
                52,
                minimum=2,
            )
            damped_trend = _as_bool(model_params.get("damped_trend"), False)
            if trend is None:
                damped_trend = False

            hw_kwargs = {
                "trend": trend,
                "seasonal": seasonal,
                "damped_trend": damped_trend,
                "initialization_method": "estimated",
            }
            if seasonal is not None:
                hw_kwargs["seasonal_periods"] = seasonal_periods

            model = ExponentialSmoothing(series, **hw_kwargs)
            fit_model = model.fit()
            forecast_values = fit_model.forecast(forecast_weeks).tolist()

            model_params_used.update({
                "trend": trend,
                "seasonal": seasonal,
                "seasonal_periods": seasonal_periods if seasonal is not None else None,
                "damped_trend": damped_trend,
            })
        elif model_type == "arima":
            order = model_params.get("order", (1, 1, 1))
            if isinstance(order, str):
                order = [p.strip() for p in order.split(",")]
            if isinstance(order, (list, tuple)) and len(order) == 3:
                try:
                    order = tuple(int(v) for v in order)
                except (TypeError, ValueError):
                    order = (1, 1, 1)
            else:
                order = (1, 1, 1)

            model = ARIMA(series, order=order)
            fit_model = model.fit()
            forecast_values = fit_model.forecast(forecast_weeks).tolist()
            model_params_used.update({"order": list(order)})
        else:
            return jsonify({"error": "Unknown model selected."}), 400

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Model failed to calculate: {str(e)}"}), 500

    # Generate future TIME_IDs
    year = int(str(last_time_id)[:4])
    week = int(str(last_time_id)[4:])

    future_labels = []
    for _ in range(forecast_weeks):
        week += 1
        if week > 52:
            week = 1
            year += 1
        future_labels.append(f"{year}{week:02d}")

    rounded_forecast = [max(0, round(float(v), 2)) for v in forecast_values]

    # Persist latest live-computed aggregate for exact scope/model so Search is stable.
    persist_conn = None
    try:
        persist_conn = get_db()
        persist_conn.execute(cache_table_sql)
        cache_scope_payload = {
            **scope_descriptor,
            "model_params_used": model_params_used,
        }
        persist_conn.execute(
            """
            INSERT OR REPLACE INTO forecast_agg_cache (
                CACHE_KEY, SCOPE_JSON, MODEL_USED, SOURCE,
                HISTORICAL_DATES, HISTORICAL_SALES, FORECAST_DATES, FORECAST_SALES,
                LAST_UPDATED
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scope_key,
                json.dumps(cache_scope_payload, sort_keys=True),
                model_type,
                "live computation",
                json.dumps(df["TIME_ID"].astype(str).tolist()),
                json.dumps(df["TOTAL_SALES"].tolist()),
                json.dumps(future_labels),
                json.dumps(rounded_forecast),
                datetime.now().isoformat(),
            ),
        )

        # Keep forecasts_fact in sync when scope is a single SKU+store pair.
        if item_id and store_id:
            opt_id = str(item_id)
            st_id = int(store_id)
            persist_conn.execute(
                "DELETE FROM forecasts_fact WHERE OPTION_ID = ? AND STORE = ?",
                (opt_id, st_id),
            )
            persist_conn.executemany(
                """
                INSERT INTO forecasts_fact (OPTION_ID, STORE, TIME_ID, UNITS, MODEL_USED)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (opt_id, st_id, int(tid), units, model_type)
                    for tid, units in zip(future_labels, rounded_forecast)
                ],
            )

        persist_conn.commit()
    except Exception:
        traceback.print_exc()
    finally:
        if persist_conn:
            persist_conn.close()

    return jsonify({
        "status": "success",
        "source": "live computation",
        "model_used": model_type,
        "model_params_used": model_params_used,
        "historical_dates": df["TIME_ID"].astype(str).tolist(),
        "historical_sales": df["TOTAL_SALES"].tolist(),
        "forecast_dates": future_labels,
        "forecast_sales": rounded_forecast
    })


if __name__ == "__main__":
    print("Initializing database (first run only)...")
    init_db(force_reload=False)
    print(f"Starting Flask server — frontend at http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
