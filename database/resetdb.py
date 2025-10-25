# DONOT USE UNLESS WE KNOW
import sqlite3

def reset_database():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Drop and recreate the users table
    cursor.execute("DROP TABLE IF EXISTS users")

    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database reset! 'users' table is now empty and recreated.")

if __name__ == "__main__":
    reset_database()
