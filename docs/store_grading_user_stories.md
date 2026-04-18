# User Stories: Store Grading Page

This document outlines the business requirements and user interactions for the **Store Grading** module within the Retail Analytics Suite.

---

## Story 1: Business-Context Awareness (Toggling Granularity)
**As a** Retail Planner,  
**I want to** toggle between "Class Level" and "Subclass Level" grading,  
**So that** I can decide if I want a single performance grade for the entire class or specific grades for individual subclasses.

### Acceptance Criteria:
- The Retail Planner can switch between "Class Level" and "Subclass Level" using a toggle at the top of the filter panel.
- When "Class Level" is selected, the **Subclass filter** is automatically disabled and cleared.
- Selecting a granularity immediately updates the "scope description" in the generation modal to reflect how many grades will be generated per store.

---

## Story 2: Hierarchical Filtering (Cascading Dropdowns)
**As a** Retail Planner,  
**I want** the filters to dynamically update based on my selections,  
**So that** I only see Classes and Subclasses that belong to the selected Department.

### Acceptance Criteria:
- Selecting a **Department** populates the **Class** dropdown.
- Selecting a **Class** populates the **Subclass** dropdown (if in Subclass view).
- Resetting a parent filter (e.g., Dept) automatically clears and disables all child filters (Class, Subclass).
- The "Search" and "Generate" buttons remain disabled until the minimum required hierarchy (Dept + Class) is selected.

---

## Story 3: Intelligent Clustering Execution
**As a** Retail Planner,  
**I want to** trigger a K-means clustering run for a specific product and location segment,  
**So that** I can group stores into performance buckets (Grade 1, 2, 3) based on historical sales.

### Acceptance Criteria:
- Clicking "Generate" opens a confirmation modal showing the total scope (Selected Dept, Class, Country, etc.).
- The Retail Planner can select the number of clusters (3, 4, or 5).
- The system prevents redundant clicking during execution via a "Generating..." state.
- Upon submission, the Retail Planner receives a unique "Run ID" and can track progress in a dedicated status history.

---

## Story 4: Background Run Monitoring
**As a** Retail Planner,  
**I want to** view the history of my grading runs and their status,  
**So that** I can verify if a run was successful or see why it failed without staying on the same page.

### Acceptance Criteria:
- A "Run Status" button opens a history modal showing the 10 most recent runs.
- Each run entry shows its ID, Status (Submitted, In Progress, Completed, Error), and Parameters.
- Statuses are color-coded (Green for success, Red for failure) for quick visual scanning.
- A "Refresh" button allows manual polling of active runs by the Retail Planner.

---

## Story 5: Grade Insight Dashboard
**As a** Retail Planner,  
**I want to** see a summary of the clustering results for my current view,  
**So that** I can quickly understand the distribution of high-performing vs. low-performing stores.

### Acceptance Criteria:
- The dashboard displays four summary cards: **Grade 1 Count**, **Grade 2 Count**, **Grade 3 Count**, and **Total Results**.
- These counts represent the **entire result set** for the selected filters, not just the visible page.
- Summary numbers update automatically whenever a search or generation is performed by the Retail Planner.

---

## Story 6: Data Grid Exploration & Sorting
**As a** Retail Planner,  
**I want to** browse the store grading results in a paginated grid,  
**So that** I can review individual store performance attributes like `total_units`, `base_history`, and `avg_weekly_units`.

### Acceptance Criteria:
- Results are displayed in a clean, scrollable grid with 50 rows per page.
- Columns are sortable (ascending/descending) by clicking the column header.
- The grid includes crucial location context (Store ID, Store Name, Country) for every result.
- A "Results Label" at the top indicates to the Retail Planner if no data was found or if filters need selection.

---

## Story 7: Portable Analysis (CSV Export)
**As a** Retail Planner,  
**I want to** download my clustering results as a CSV file,  
**So that** I can import them into Excel or other reporting tools for further processing.

### Acceptance Criteria:
- The "Export CSV" button is enabled only when data is visible in the grid.
- The exported filename includes the Department and Class name for easy identification.
- The CSV file contains all data columns currently visible in the UI for the Retail Planner.
