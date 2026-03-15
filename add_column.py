import sqlite3

db_path = "/Users/gsoto/Desktop/suple/suplementos.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists first
    cursor.execute("PRAGMA table_info(campaigns)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "variables_mapping" not in columns:
        print("Adding variables_mapping column to campaigns table...")
        cursor.execute("ALTER TABLE campaigns ADD COLUMN variables_mapping JSON")
        conn.commit()
        print("Column added successfully.")
    else:
        print("Column variables_mapping already exists.")
        
except sqlite3.Error as error:
    print("Error while executing sqlite script", error)
finally:
    if conn:
        conn.close()
