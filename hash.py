import sqlite3
from werkzeug.security import generate_password_hash

def update_passwords_to_hashes():
    # 1. Connect to your database
    # Make sure this points to your actual database file (e.g., 'guild.db')
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 2. Fetch all current users
    cursor.execute("SELECT UId, username, password_hash FROM users")
    users = cursor.fetchall()

    updated_count = 0

    for user in users:
        user_id = user['UId']
        current_password = user['password_hash']
        
        # 3. Check if it's already hashed
        # Werkzeug hashes typically start with 'pbkdf2:sha256' or 'scrypt'
        if current_password.startswith('pbkdf2:') or current_password.startswith('scrypt:'):
            print(f"User {user['username']} is already hashed. Skipping.")
            continue
            
        # 4. Hash the plain text password
        new_hashed_password = generate_password_hash(current_password)
        
        # 5. Update the row in the database
        cursor.execute("""
            UPDATE users 
            SET password_hash = ? 
            WHERE UId = ?
        """, (new_hashed_password, user_id))
        
        print(f"Successfully hashed password for user: {user['username']}")
        updated_count += 1

    # 6. Commit the changes and close the connection
    conn.commit()
    conn.close()
    
    print(f"\nFinished! Updated {updated_count} accounts.")

if __name__ == '__main__':
    update_passwords_to_hashes()