import sqlite3

db_path = "/Users/gsoto/Desktop/suple/suplementos.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists first
    cursor.execute("PRAGMA table_info(customers)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "marketing_opt_in" not in columns:
        print("Adding marketing_opt_in column to customers table...")
        cursor.execute("ALTER TABLE customers ADD COLUMN marketing_opt_in BOOLEAN DEFAULT 1")
        conn.commit()
        print("Column marketing_opt_in added successfully.")
    else:
        print("Column marketing_opt_in already exists.")
        
except sqlite3.Error as error:
    print("Error while executing sqlite script", error)
finally:
    if conn:
        conn.close()
