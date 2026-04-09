# Store Grading Tool

A full-stack enterprise tool that assigns store grades based on historical sales performance using **K-means clustering**.

---

## Architecture

```
Store_grading/
├── backend/
│   ├── app.py              # Flask REST API
│   ├── database.py         # SQLite DB creation + CSV loading
│   ├── store-grading.py    # K-means grading engine (standalone or via API)
│   ├── requirements.txt
│   └── store_grading.db    # SQLite DB (auto-created on first run)
├── frontend/
│   ├── index.html          # Enterprise UI
│   ├── styles.css          # Premium dark theme CSS
│   └── app.js              # Filter/search/generate logic
└── README.md
```

---

## Quick Start

### 1. Install Dependencies
```bash
pip install flask flask-cors pandas scikit-learn
```

### 2. Run the Server (auto-initializes DB + loads CSVs)
```bash
cd backend
python app.py
```

### 3. Open the UI
Navigate to: **http://localhost:5000**

---

## CSV Data Sources

The app expects these CSVs (looked up in `../data/` first, then `C:\Users\amankumar.singh\Downloads\`):

| File | Table |
|------|-------|
| `sales_hist_fact.csv` | `sales_hist_fact` |
| `product_option_dim.csv` | `product_option_dim` |
| `location_st_master.csv` | `location_st_master` |

To force a reload: `python backend/database.py --force`

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | Health check |
| GET | `/api/filters` | All filter dropdown data |
| GET | `/api/classes?dept=X` | Cascading class list |
| GET | `/api/subclasses?dept=X&class=Y` | Cascading subclass list |
| GET | `/api/store-grades?dept=X&class=Y[&subclass=Z&country=C&store=S&page=1&page_size=50]` | Query store grades |
| POST | `/api/generate-grades` | Trigger K-means grading |

### Generate Grades Request Body
```json
{
  "dept":     108,
  "class":    3,
  "level":    "class",       // or "subclass"
  "subclass": null,          // optional
  "store":    null,          // optional
  "country":  "SAU",         // optional
  "clusters": 3              // optional, default 3
}
```

---

## Grading Logic

1. **Data joins**: `sales_hist_fact` → `product_option_dim` (via OPTION_ID) → `location_st_master` (via STORE)
2. **Feature aggregation** per store-product group:
   - `total_units` = SUM(REGULAR + PROMO + MRKDWN sales units)
   - `base_history` = SUM(BASE_HISTORY)
   - `weeks_of_sales` = COUNT(DISTINCT TIME_ID)
   - `avg_weekly_units` = total_units / weeks_of_sales
3. **K-means clustering** (sklearn, StandardScaler + KMeans)
4. **Grade assignment**: cluster with highest `avg_weekly_units` centroid = Grade **1** (best), lowest = Grade **3**
5. **Upsert** into `store_grade` table

### Level Behavior
| Level | Group Key | SUBCLASS in output |
|-------|-----------|--------------------|
| Class | BRAND + LOCATION + COUNTRY + DEPT + CLASS | NULL |
| Subclass | BRAND + LOCATION + COUNTRY + DEPT + CLASS + SUBCLASS | Populated |

---

## CLI Usage (standalone grading)

```bash
# Class-level grading
python backend/store-grading.py --dept 108 --class 3 --level class

# Subclass-level grading with country filter
python backend/store-grading.py --dept 108 --class 3 --level subclass --country SAU

# With custom number of grade clusters
python backend/store-grading.py --dept 108 --class 3 --level class --clusters 4
```

---

## Assumptions

| Assumption | Rationale |
|---|---|
| SQLite used instead of Oracle | No Oracle connection provided; same SQL syntax, same logical schema |
| `AREA_NAME` = Country filter | Confirmed from `location_st_master.csv` — contains region/country names |
| Join: `sales_hist_fact.STORE → location_st_master.STORE` | Both have a numeric STORE column |
| Join: `sales_hist_fact.OPTION_ID → product_option_dim.OPTION_ID` | Matching key format (e.g., `130213005_AMEC001`) |
| Grade 1 = best performing | Cluster with highest avg_weekly_units = Grade 1 (most desirable for allocation) |
| `n_clusters = min(3, n_samples)` | Prevents crash when fewer than 3 unique stores exist for a scope |
