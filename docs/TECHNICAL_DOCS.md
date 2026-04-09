# Technical Documentation - Retail Analytics Suite

This document provides a detailed technical overview of the Retail Analytics Suite for developers and maintainers.

---

## 🏗 Architecture Overview

The application follows a standard **Client-Server** architecture with the following stack:

- **Backend**: Python 3.10+ / Flask (REST API)
- **Database**: SQLite (local file-based storage)
- **Frontend**: Vanilla JavaScript (ES6+), HTML5, and CSS3 (Custom Dark Theme)
- **Analysis**: Scikit-Learn (K-means clustering), Pandas (Data processing)

### Project Structure
```
store-grading/
├── backend/
│   ├── app.py              # Primary Flask entry point and API handlers
│   ├── database.py         # DB schema definition and CSV ingestion logic
│   ├── store-grading.py    # K-means clustering engine and logic
│   ├── requirements.txt    # Python dependencies
│   └── store_grading.db    # SQLite database (auto-generated)
├── frontend/
│   ├── index.html          # SPA layout and App Shell
│   ├── styles.css          # Design system and layout styling
│   └── app.js              # Client-side routing, state management, and API integration
├── docs/                   # Documentation
└── data/                   # Expected location for source CSV files
```

---

## 🗄 Database Schema

The system uses SQLite. On initial startup, `backend/database.py` validates the persistence layer and loads data from CSVs if the tables are empty.

### Core Tables

#### `sales_hist_fact`
Stores transactional history. 
- **Keys**: `STORE`, `OPTION_ID`, `TIME_ID`
- **Stats**: `REGULAR_SALES_UNITS`, `PROMO_SALES_UNITS`, `MRKDWN_SALES_UNITS`, `BASE_HISTORY`

#### `product_option_dim`
Product master data.
- **Key**: `OPTION_ID`
- **Attributes**: `BRAND`, `DEPT`, `CLASS`, `SUBCLASS`, `FABRIC`, `COLOR_FAMILY`, etc.

#### `location_st_master`
Store master data.
- **Key**: `STORE` (Store ID)
- **Attributes**: `STORE_NAME`, `AREA_NAME` (Country), `CITY`, `CURRENCY_CODE`, `STORE_TYPE`, `TOTAL_SQUARE_FT`, `DEFAULT_WH`.

#### `store_grade`
Target table for the grading engine.
- **Composite Key**: `STORE`, `DEPT`, `CLASS`, `SUBCLASS`
- **Columns**: `GRADE` (1-4), `CLUSTER_ID`, `AVG_WEEKLY_UNITS`.

---

## 🚀 API Reference

### 1. Filters & Hierarchy
- **`GET /api/filters`**: Returns all distinct values for dropdowns (Depts, Countries, Brands, etc.).
- **`GET /api/classes?dept=X`**: Returns subclasses belonging to a specific department.
- **`GET /api/subclasses?dept=X&class=Y`**: Returns subclasses for a specific dept/class.

### 2. Store Grading
- **`GET /api/store-grades`**: Query existing grades.
  - Params: `dept`, `class`, `subclass` (optional), `page`.
- **`POST /api/generate-grades`**: Triggers the K-means engine for a specific hierarchy level.
  - Body: `{ dept, class, level: "class"|"subclass", clusters: N }`.

### 3. Analytics, Masters & Admin
- **`GET /api/product-master`**: Paginated product list with attribute filters.
- **`GET /api/location-master`**: Paginated store list with country/type filters.
- **`GET /api/sales-history`**: Hierarchical sales aggregation.
- **`GET /api/admin/graded-scopes`**: Discovers unique Brand/Dept/Class/Subclass segments with existing grades.
- **`POST /api/admin/bulk-delete-grades`**: Bulk removes grades for a list of scopes in a single transaction.

---

## 🧠 Grading Logic (K-means)

The logic resides in `backend/store-grading.py`.

1. **Aggregation**: Aggregates sales by Store and Item within the requested hierarchy scope.
2. **Feature Engineering**: Calculates `avg_weekly_units` (Total Units / Total Weeks with positive sales).
3. **Normalization**: Uses `StandardScaler` to normalize the feature vector.
4. **Clustering**: Runs `KMeans(n_clusters=k)`.
5. **Ranking**: Clusters are sorted by their `avg_weekly_units` centroids.
   - **Grade 1**: Highest volume cluster.
   - **Grade 4**: Lowest volume cluster.
6. **Persistence**: Grades are upserted into the `store_grade` table using an `ON CONFLICT` strategy.

---

## 🛠 Setup & Development

### Local Requirements
- Python 3.10+
- Dependencies: `pip install flask flask-cors pandas scikit-learn`

### Running the Project
1. Open terminal in the `backend/` directory.
2. Run `python app.py`.
3. The server starts on port `5001`.
4. Visit `http://localhost:5001` in your browser.
