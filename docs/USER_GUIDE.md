# User Guide - Retail Analytics Suite

Welcome to the **Retail Analytics Suite**. This guide will help you navigate and use the various modules of the application to analyze store performance, products, and sales history.

---

## 🧭 Navigation
The application uses a collapsible sidebar on the left to switch between pages:
- **Store Grading**: performance clustering.
- **Product Master**: product catalog.
- **Location Master**: store directory.
- **Sales History**: sales analytics.

---

## 📊 Store Grading
The core engine of the suite. It uses K-means clustering to group stores based on their sales volume.

### How to use:
1.  **Select Scope**: Choose a Department and Class. Optionally, select a Subclass.
2.  **Filter by Country**: (Optional) Narrows the clustering to a specific area.
3.  **Run Grading**: Click the blue "Generate Store Grading" button.
4.  **Confirm Clusters**: In the popup, choose how many grades you want (3, 4, or 5). Click "Run Grading".
5.  **Interpret Results**: 
    - **Grade 1**: High volume/performing stores.
    - **Grade 3/4/5**: Lower volume stores.

---

## 📦 Product Master
A centralized view of your entire product catalog.

### Features:
- **Filtering**: Filter by Brand, Department, Class, or Subclass.
- **Keyword Search**: Search for specific Option IDs or Descriptions.
- **Attributes**: View detailed attributes like Fabric, Color Family, Silhouette, and Collection.
- **Pagination**: Use the "Prev/Next" buttons to browse large catalogs.

---

## 📍 Location Master
A directory of all retail store locations and their specific attributes.

### Features:
- **Store Details**: View Store ID, Name, City, and Mall.
- **Operational Data**: Check Currency, Channel Type, and Default Warehouse ID.
- **Global Search**: Quickly find a store by its ID or Name.

---

## 📈 Sales History
A powerful hierarchical view of sales performance across products and locations.

### Dual Toggle Management:
- **Product Hierarchy**: Choose to see data at the Dept, Class, Subclass, or SKU level.
- **Location Aggregation**: 
    - **Country**: Aggregates all sales to the national level.
    - **Store**: Shows specific store-level performance.

### Filtering:
- **Hierarchy Filters**: Select specific depts/classes to narrow the view.
- **Date Range**: Enter a "Week From" and "Week To" (format: YYYYMMDD) to see growth over a specific period.
- **Sales Stats**: View the breakdown of Regular vs. Promo vs. Markdown sales units at the top of the page.

---

## 📥 Exporting Data
Most grids feature an **Export CSV** or **Download** functionality.
1.  Apply your desired filters.
2.  Click the "Export CSV" button (usually at the top right of the data grid).
3.  The file will be downloaded directly to your computer.
