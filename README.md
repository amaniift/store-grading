# Retail Analytics Suite

An enterprise-grade full-stack tool for store performance analysis, product management, and sales history exploration.

---

## 📖 Documentation

For detailed guides, please refer to the following:

- **[Technical Documentation](docs/TECHNICAL_DOCS.md)**: Architecture, API Reference, Database Schema, and Grading Logic.
- **[User Guide](docs/USER_GUIDE.md)**: Functional walkthrough for Store Grading, Product Master, Sales History, and Location Master.

---

## 🏗 Architecture

- **Backend**: Flask (Python) with Scikit-Learn (K-means) and Pandas.
- **Database**: SQLite (local persistence).
- **Frontend**: Vanilla JavaScript, HTML5, and CSS3 (Premium Dark Theme).

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install flask flask-cors pandas scikit-learn
```

### 2. Run the Server
The server handles database initialization and CSV data ingestion automatically on the first run.
```bash
cd backend
python app.py
```

### 3. Open the UI
Navigate to **http://localhost:5001** in your browser.

---

## 🛠 Features

- **Store Grading**: AI-powered performance clustering using multi-dimensional sales history.
- **Product Master**: Full catalog explorer with attribute filtering and pagination.
- **Location Master**: Detailed store directory with operational and geographic metadata.
- **Sales History**: Hierarchical analytics with dynamic product/location level aggregation.

---

## 📂 Source Code structure

```
store-grading/
├── backend/            # Python Flask server & logic
├── frontend/           # SPA frontend (HTML/JS/CSS)
├── docs/               # Detailed documentation
└── data/               # Source CSV data (expected)
```
