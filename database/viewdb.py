import sqlite3

def view_users():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, first_name, last_name, email FROM users")
    users = cursor.fetchall()

    if users:
        print("📋 Users in the database:")
        for user in users:
            print(f"ID: {user[0]} | Name: {user[1]} {user[2]} | Email: {user[3]}")
    else:
        print("⚠️ No users found in the database.")

    conn.close()

if __name__ == "__main__":
    view_users()
