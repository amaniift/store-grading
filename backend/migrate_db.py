import sqlite3

def migrate():
    conn = sqlite3.connect('store_grading.db')
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(mv_option_loc)")
    cols = [c[1] for c in cursor.fetchall()]
    
    new_cols = [
        ('PLR_STATUS', 'TEXT'),
        ('REPLENISHABLE', 'TEXT'),
        ('LAST_UPDATE_ID', 'TEXT'),
        ('LAST_UPDATE_DATETIME', 'TEXT')
    ]
    
    for col_name, col_type in new_cols:
        if col_name not in cols:
            print(f"Adding column {col_name} to mv_option_loc")
            cursor.execute(f"ALTER TABLE mv_option_loc ADD COLUMN {col_name} {col_type}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
