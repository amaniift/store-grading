import sqlite3
conn = sqlite3.connect('store_grading.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT * FROM store_grade LIMIT 5').fetchall()
for r in rows:
    print(dict(zip(r.keys(), tuple(r))))
total = conn.execute('SELECT COUNT(*) FROM store_grade').fetchone()[0]
print(f'\nTotal store_grade rows: {total}')
conn.close()
