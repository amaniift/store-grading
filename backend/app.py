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

import os
import sys
import json
import traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from database import get_db, init_db

# Import the grading function (store-grading.py uses hyphen, so we use importlib)
import importlib.util

_grading_spec = importlib.util.spec_from_file_location(
    "store_grading_engine",
    os.path.join(BASE_DIR, "store-grading.py")
)
_grading_mod = importlib.util.module_from_spec(_grading_spec)
_grading_spec.loader.exec_module(_grading_mod)
run_grading = _grading_mod.run_grading

# ─── App Setup ───────────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# ─── Helper ──────────────────────────────────────────────────────────────────

def rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


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
            "SELECT DISTINCT STORE, STORE_NAME FROM location_st_master "
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

        conn.close()
        return jsonify({
            "depts":      depts,
            "classes":    classes,
            "subclasses": subclasses,
            "stores":     stores,
            "countries":  countries,
            "types":      types,
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
    dept  = request.args.get("dept",  type=int)
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


# ── Store Grades ─────────────────────────────────────────────────────────────

@app.route("/api/store-grades")
def get_store_grades():
    """
    Query store_grade with optional filters.
    Required: dept, class
    Optional: subclass, store, country, page, page_size
    """
    dept    = request.args.get("dept",     type=int)
    class_  = request.args.get("class",    type=int)
    subclass = request.args.get("subclass", type=int, default=None)
    store   = request.args.get("store",    type=int, default=None)
    country = request.args.get("country",  type=str, default=None)
    level   = request.args.get("level",  type=str, default="class")
    page    = request.args.get("page",     type=int, default=1)
    page_size = request.args.get("page_size", type=int, default=100)

    if not dept or not class_:
        return jsonify({"error": "dept and class are required"}), 400

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
                sg.LAST_UPDATE_ID
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
            WHERE sg.DEPT = ? AND sg.CLASS = ?
        """
        params: list = [dept, class_]

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
    dept    = body.get("dept")
    class_  = body.get("class")
    level   = body.get("level", "class")
    subclass = body.get("subclass")
    store   = body.get("store")
    country = body.get("country")
    clusters = body.get("clusters", 3)

    if not dept or not class_:
        return jsonify({"error": "dept and class are required"}), 400

    try:
        result = run_grading(
            dept=int(dept),
            class_=int(class_),
            level=level,
            subclass=int(subclass) if subclass else None,
            store=int(store) if store else None,
            country=country or None,
            n_clusters=int(clusters),
        )
        status_code = 200 if result["status"] == "success" else 422
        return jsonify(result), status_code
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Product Master ────────────────────────────────────────────────────────────

@app.route("/api/product-master")
def get_product_master():
    """
    Paginated product master data from product_option_dim.
    Optional filters: dept, class, subclass, brand, search (OPTION_ID / OPTION_DESC).
    """
    dept     = request.args.get("dept",     type=int,  default=None)
    class_   = request.args.get("class",    type=int,  default=None)
    subclass = request.args.get("subclass", type=int,  default=None)
    brand    = request.args.get("brand",    type=str,  default=None)
    search   = request.args.get("search",   type=str,  default=None)
    page     = request.args.get("page",     type=int,  default=1)
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

        total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
        offset = (page - 1) * page_size
        sql += f" ORDER BY BRAND, DEPT, CLASS, SUBCLASS, OPTION_ID LIMIT {page_size} OFFSET {offset}"
        rows = rows_to_list(conn.execute(sql, params).fetchall())

        # distinct brands for filter dropdown
        brands = [r["BRAND"] for r in rows_to_list(
            conn.execute("SELECT DISTINCT BRAND FROM product_option_dim WHERE BRAND IS NOT NULL ORDER BY BRAND").fetchall()
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
    country   = request.args.get("country",   type=str, default=None)
    city      = request.args.get("city",      type=str, default=None)
    type_     = request.args.get("type",      type=str, default=None)
    search    = request.args.get("search",    type=str, default=None)
    page      = request.args.get("page",      type=int, default=1)
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

        total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
        offset = (page - 1) * page_size
        sql += f" ORDER BY AREA_NAME, CITY, STORE LIMIT {page_size} OFFSET {offset}"
        rows = rows_to_list(conn.execute(sql, params).fetchall())

        # Metadata for filters
        countries = [r["AREA_NAME"] for r in rows_to_list(
            conn.execute("SELECT DISTINCT AREA_NAME FROM location_st_master WHERE AREA_NAME IS NOT NULL ORDER BY AREA_NAME").fetchall()
        )]
        types = [r["STORE_TYPE"] for r in rows_to_list(
            conn.execute("SELECT DISTINCT STORE_TYPE FROM location_st_master WHERE STORE_TYPE IS NOT NULL ORDER BY STORE_TYPE").fetchall()
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
    level     = request.args.get("level",     type=str, default="class")
    loc_level = request.args.get("loc_level", type=str, default="store")
    dept      = request.args.get("dept",      type=int, default=None)
    class_    = request.args.get("class",     type=int, default=None)
    subclass  = request.args.get("subclass",  type=int, default=None)
    store     = request.args.get("store",     type=int, default=None)
    country   = request.args.get("country",   type=str, default=None)
    date_from = request.args.get("date_from", type=str, default=None)
    date_to   = request.args.get("date_to",   type=str, default=None)
    page      = request.args.get("page",      type=int, default=1)
    page_size = request.args.get("page_size", type=int, default=50)

    valid_levels    = ("dept", "class", "subclass", "sku")
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
            loc_select  = ["l.AREA_NAME AS COUNTRY"]
            loc_groupby = ["l.AREA_NAME"]
        else:  # store
            loc_select  = ["s.STORE", "l.STORE_NAME", "l.AREA_NAME AS COUNTRY"]
            loc_groupby = ["s.STORE", "l.STORE_NAME", "l.AREA_NAME"]

        sel_cols   = level_dims[level] + loc_select
        grp_cols   = level_dims[level] + loc_groupby
        select_str = ", ".join(sel_cols)
        group_by   = ", ".join(grp_cols)

        agg_cols = """
            SUM(s.REGULAR_SLS_UNITS)  AS REGULAR_UNITS,
            SUM(s.PROMO_SLS_UNITS)    AS PROMO_UNITS,
            SUM(s.MRKDWN_SLS_UNITS)   AS MRKDWN_UNITS,
            SUM(s.REGULAR_SLS_UNITS + s.PROMO_SLS_UNITS + s.MRKDWN_SLS_UNITS) AS TOTAL_UNITS,
            SUM(s.BASE_HISTORY)        AS BASE_HISTORY,
            COUNT(DISTINCT s.TIME_ID)  AS WEEKS_WITH_SALES
        """

        agg_sql = f"SELECT {select_str}, {agg_cols} {base_sql} GROUP BY {group_by}"

        total = conn.execute(f"SELECT COUNT(*) FROM ({agg_sql})", params).fetchone()[0]

        offset    = (page - 1) * page_size
        paged_sql = agg_sql + f" ORDER BY TOTAL_UNITS DESC LIMIT {page_size} OFFSET {offset}"
        rows      = rows_to_list(conn.execute(paged_sql, params).fetchall())

        conn.close()
        return jsonify({"total": total, "page": page, "page_size": page_size,
                        "level": level, "loc_level": loc_level, "data": rows})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ─── Startup ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Initializing database (first run only)...")
    init_db(force_reload=False)
    print(f"Starting Flask server — frontend at http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)

