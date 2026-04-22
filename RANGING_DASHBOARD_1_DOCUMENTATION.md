# Ranging Dashboard-1: Comprehensive Product Option Analytics

## Overview

**Ranging Dashboard-1** is a new advanced analytics screen that provides comprehensive data visualization and analysis of product options from the `mv_option_loc` table. It offers multi-dimensional insights into option distribution, seasonality, market coverage, and product labeling.

## Features

### 1. Filter System (Top)
- **Brand** - Filter by product brand
- **Department** - Filter by department (with cascading support)
- **Class** - Filter by class (cascades from department selection)
- **Subclass** - Filter by subclass (cascades from class selection)
- **Season** - Filter by product season code
- **Product Label** - Filter by product label
- **Story** - Filter by product story
- **Country/Area** - Filter by geographic area
- **Store** - Filter by specific store location
- **Status** - Filter by option status (Active/Inactive)

**Cascading Filters**: Department → Class → Subclass automatically populate based on parent selections, preventing invalid filter combinations.

### 2. Metric Cards (6 Key Metrics)
Displayed below filters in a responsive grid:
- **Total Unique Options** - Total distinct options matching filters
- **Active Options** - Count of options with status "A"
- **Inactive Options** - Count of options with status "I"  
- **Unique Stores** - Total distinct store locations carrying options
- **Average Price** - Mean selling unit retail price
- **Active Store Locations** - Count of stores with active options

Each metric card includes:
- Icon with color-coded background
- Label (uppercase, small text)
- Large numeric value
- Hover effects for interactivity

### 3. Visualization Charts (8 Charts in 2-Column Grid)

#### Chart 1: Status Distribution (Doughnut)
- Compares Active vs Inactive options
- Color-coded: Green (Active), Red (Inactive)
- Ideal for high-level overview

#### Chart 2: Options by Department (Horizontal Bar)
- Top 10 departments by option count
- Shows department distribution of assortment
- Right-to-left bar visualization for readability

#### Chart 3: Top Brands (Horizontal Bar)
- Top 10 brands by option count
- Helps identify key brands in filtered dataset
- Warning color theme

#### Chart 4: Top Seasons (Bar)
- All distinct seasons and their option counts
- Shows seasonality distribution
- Secondary color theme

#### Chart 5: Top Product Labels (Bar)
- Top 8 product labels by count
- Identifies key product categories
- Info color theme

#### Chart 6: Stories Distribution (Bar)
- Top 8 stories and their option counts
- Shows product narrative/story distribution
- Accent color theme

#### Chart 7: Options by Chain (Horizontal Bar)
- Options grouped by retail chain
- Shows retail coverage by chain
- Success color theme

#### Chart 8: Options by Market (Horizontal Bar)
- Options grouped by market/geographic area
- Shows market-level distribution
- Secondary palette color

### 4. Responsive Design
- **Desktop (>1200px)**: 2-column grid with optimal spacing
- **Tablet (800-1200px)**: Adapted 2-column layout
- **Mobile (<800px)**: Single-column layout with metric cards in 2x3 grid

## UI/UX Design

### Layout Structure
```
┌─────────────────────────────────────┐
│  Page Header & Description          │
├─────────────────────────────────────┤
│  Filter Panel (10 filters + buttons) │
├─────────────────────────────────────┤
│  6 Metric Cards Grid                │
├─────────────────────────────────────┤
│  8 Charts Grid (2 columns)          │
└─────────────────────────────────────┘
```

### Color Scheme
- **Primary Colors**: Blue (#3b82f6), Green (#10b981), Red (#ef4444)
- **Secondary Colors**: Purple (#8b5cf6), Orange (#f59e0b), Cyan (#06b6d4)
- **Dark Theme**: Navy backgrounds (#0a0e1a, #111827, #1e2a42)
- **Accent**: Pink (#ec4899)

### Typography
- **Font**: Inter, sans-serif
- **Chart Labels**: 12-13px, color-adjusted for theme
- **Metric Values**: Large (1.8rem), bold (800 weight)
- **Filter Labels**: Uppercase, 0.8rem, letter-spaced

## Backend API Endpoints

### 1. `/api/ranging-dashboard-1/filters` (GET)
Returns available filter values for all dropdowns.

**Response**:
```json
{
  "brands": ["AME", "BND", ...],
  "depts": [{"DEPT": 1, "DEPT_NAME": "Footwear"}, ...],
  "classes": [{"DEPT": 1, "CLASS": 10, "CLASS_NAME": "Shoes"}, ...],
  "subclasses": [{"DEPT": 1, "CLASS": 10, "SUBCLASS": 100, "SUB_NAME": "Sneakers"}, ...],
  "countries": ["USA", "UK", ...],
  "stores": [{"LOC": 101, "STORE_NAME": "NY Store", "AREA_NAME": "USA"}, ...],
  "seasons": ["SS21", "AW21", ...],
  "labels": ["INTERNATIONAL", "WEB", ...],
  "stories": ["FEBRUARY", "JULY", ...]
}
```

### 2. `/api/ranging-dashboard-1/analytics` (GET)
Returns comprehensive analytics data for visualization.

**Query Parameters**:
- `brand` - Filter by brand
- `dept` - Filter by department (integer)
- `class` - Filter by class (integer)
- `subclass` - Filter by subclass (integer)
- `country` - Filter by area/country
- `store` - Filter by store name
- `season` - Filter by season code
- `label` - Filter by product label
- `story` - Filter by story
- `status` - Filter by status (A/I)

**Response**:
```json
{
  "metrics": {
    "total_options": 10904,
    "active_options": 8969,
    "inactive_options": 10889,
    "unique_stores": 184,
    "active_stores": 180,
    "avg_price": 10614.26
  },
  "charts": {
    "status_distribution": [{"STATUS": "A", "count": 8969}, ...],
    "by_department": [{"DEPT": 1, "DEPT_NAME": "Footwear", "count": 2500}, ...],
    "top_brands": [{"BRAND": "AME", "count": 500}, ...],
    "top_seasons": [{"SEASON_CODE": "SS21", "count": 2550}, ...],
    "top_labels": [{"LABEL": "INTERNATIONAL", "count": 319}, ...],
    "top_stories": [{"STORY": "FEBRUARY", "count": 1166}, ...],
    "by_chain": [{"CHAIN_NAME": "Chain A", "count": 1000}, ...],
    "by_market": [{"MARKET": "Market A", "count": 500}, ...]
  }
}
```

## Frontend Implementation

### JavaScript State Management
```javascript
const rd1State = {
  selected: { brand: '', dept: '', class: '', subclass: '', country: '', 
              store: '', season: '', label: '', story: '', status: '' },
  filtersMeta: null,
  charts: {}
};

let rd1ChartInstances = {};
```

### Key Functions

1. **`initRd1Dashboard()`** - Initializes the page, loads filters, sets up event listeners
2. **`populateRd1Select(id, options)`** - Populates filter dropdowns
3. **`populateRd1Classes(dept)`** - Cascades class options based on department
4. **`populateRd1Subclasses(dept, cls)`** - Cascades subclass options
5. **`fetchRd1Analytics()`** - Fetches data from backend based on selected filters
6. **`renderRd1Analytics(data)`** - Updates metric card values
7. **`renderRd1Charts(charts)`** - Initializes and renders all 8 charts using Chart.js

### Chart.js Integration
All charts use Chart.js library with custom configuration:
- Responsive: `responsive: true`
- Maintained aspect ratio for consistency
- Custom colors matching theme
- Tailored legends and tooltips
- Grid customization for dark theme compatibility

## Database Queries

All queries operate on the `mv_option_loc` materialized view containing 642,040 rows with columns:
- BRAND, OPTION_ID, STATUS, LOC, DEPT, CLASS, SUBCLASS
- SEASON_CODE, LABEL, STORY, CHAIN_NAME, MARKET, AREA_NAME
- STORE_NAME, SELLING_UNIT_RETAIL, and many others

**Query Patterns**:
- COUNT(DISTINCT OPTION_ID) - For option counts
- COUNT(DISTINCT LOC) - For unique store counts  
- AVG(SELLING_UNIT_RETAIL) - For average pricing
- GROUP BY with ORDER BY for rankings/distributions

## Performance Considerations

### Optimizations
1. **Pagination**: Charts show top 10-15 items to avoid overwhelming visualization
2. **Distinct Counts**: Uses COUNT(DISTINCT) to avoid inflated numbers
3. **Indexed Queries**: WHERE clauses on indexed columns (BRAND, DEPT, CLASS, STATUS)
4. **Limited Result Sets**: Top N results prevent SQL memory issues

### Expected Load Times
- Filters endpoint: ~100-200ms
- Analytics endpoint (no filters): ~500-800ms
- Analytics endpoint (with filters): ~200-400ms

## CSS Classes & Styling

### Top-Level Classes
- `.rd1-metrics-top` - Metric cards container grid
- `.rd1-metric-card` - Individual metric card container
- `.rd1-chart-container` - Individual chart wrapper
- `.rd1-charts-grid` - Charts container grid

### Responsive Breakpoints
- `@media (max-width: 1200px)` - Tablet layout
- `@media (max-width: 800px)` - Mobile layout

### Color Theme Classes
- `.rd1-metric-primary` - Blue theme (#3b82f6)
- `.rd1-metric-success` - Green theme (#10b981)
- `.rd1-metric-danger` - Red theme (#ef4444)
- `.rd1-metric-warning` - Orange theme (#f59e0b)
- `.rd1-metric-info` - Cyan theme (#06b6d4)
- `.rd1-metric-secondary` - Purple theme (#8b5cf6)

## Usage Instructions

### For Users
1. Click **"Ranging Dashboard-1"** in the sidebar to access the page
2. Select desired filters from the top panel (optional)
3. Click **"Apply Filters"** to load data matching your criteria
4. Review metric cards for high-level insights
5. Examine charts for detailed distributions
6. Use **"Reset"** button to clear all filters and reload full dataset

### For Developers
1. Filters automatically populate from `/api/ranging-dashboard-1/filters`
2. Charts render automatically when data is received
3. To add new filter: Add SQL column to WHERE builder in `build_rd1_where()`, add to HTML select, add to JavaScript state
4. To add new chart: Add SQL query to analytics endpoint, add canvas element, add Chart.js rendering code

## Future Enhancements

1. **Export Functionality** - Add CSV/Excel export of chart data
2. **Date Range Filtering** - Add temporal analysis (not currently in mv_option_loc)
3. **Drill-Down Charts** - Click charts to drill into specific segments
4. **Custom Aggregations** - Allow user-defined metric calculations
5. **Saved Filters** - Save filter combinations for quick access
6. **Comparison Mode** - Compare two filter combinations side-by-side
7. **Trend Analysis** - Historical trend visualization
8. **Performance Metrics** - Cache frequently-used filter combinations

## Navigation

The new screen is accessible via:
- Sidebar menu: Click "Ranging Dashboard-1" button
- Direct URL: `http://localhost:5001/#page-ranging-dashboard-1` (when implemented with anchor-based routing)

## Files Modified

### Backend
- `backend/app.py` - Added `build_rd1_where()` function, `/api/ranging-dashboard-1/filters` route, `/api/ranging-dashboard-1/analytics` route

### Frontend  
- `frontend/index.html` - Added navigation button, page shell with filters, metric cards, chart containers
- `frontend/app.js` - Added `initRd1Dashboard()` and all related functions (40+ lines of code)
- `frontend/styles.css` - Added RD1-specific styling (300+ lines of CSS)

## Testing Checklist

- [x] Backend routes return valid JSON
- [x] Frontend page loads without errors
- [x] Filters populate correctly
- [x] Cascading filters work (Dept → Class → Subclass)
- [x] Apply button triggers data fetch
- [x] Metric cards display current values
- [x] Charts render with proper data
- [x] Reset button clears all selections
- [x] Responsive design on different screen sizes
- [x] No console errors or warnings

## Support & Maintenance

For issues or enhancements:
1. Check backend SQL in `build_rd1_where()` for filter logic
2. Verify Chart.js options in `renderRd1Charts()` for visualization issues
3. Update CSS in `.rd1-*` classes for styling changes
4. Add new filters by updating HTML select elements and JavaScript state object
