import sqlite3
from model import User
from werkzeug.security import generate_password_hash, check_password_hash

"""
this function will connect the database and return conn.
so in the other functions, i will only call this function to get conn
instead of writing connection code everytime.
"""
def get_db_connection():

    # Connect to the local SQLite database file
    conn = sqlite3.connect('database.db')

    # Configure the connection to return dictionary-like rows instead of standard tuples 
    conn.row_factory = sqlite3.Row
    return conn


## to be implemented again
def get_quest_program(day_filter=None, type_filter=None, difficulty_filter=None):
    """Fetches sessions joined with quest info, applying optional filters."""
    conn = get_db_connection()
    
    query = '''
        SELECT sessions.id as session_id, sessions.day, sessions.start_time, sessions.location,
               quests.title, quests.quest_type, quests.difficulty, quests.duration
        FROM sessions
        JOIN quests ON sessions.quest_id = quests.id
        WHERE 1=1
    '''
    params = []
    
    # Apply filters if they exist
    if day_filter:
        query += ' AND sessions.day = ?'
        params.append(day_filter)
    if type_filter:
        query += ' AND quests.quest_type = ?'
        params.append(type_filter)
    if difficulty_filter:
        query += ' AND quests.difficulty = ?'
        params.append(difficulty_filter)

    # Sort logically by Day of Week, then by Time
    query += '''
        ORDER BY 
        CASE sessions.day
            WHEN 'Monday' THEN 1
            WHEN 'Tuesday' THEN 2
            WHEN 'Wednesday' THEN 3
            WHEN 'Thursday' THEN 4
            WHEN 'Friday' THEN 5
            WHEN 'Saturday' THEN 6
            WHEN 'Sunday' THEN 7
        END,
        sessions.start_time ASC
    '''
    
    sessions = conn.execute(query, params).fetchall()
    conn.close()
    return sessions


"""This function fetches a user from the database and returns a User object."""
def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = 'SELECT * FROM users WHERE id = ?'
    cursor.execute(query, (user_id,))
    user_row = cursor.fetchone()
    conn.close()
    
    if user_row:
        return User(id=user_row['id'], username=user_row['username'], role=user_row['role'])
    return None


# to be completed to meet only one GM constraint
"""This Function hashes the password and inserts a new user into the database."""
def create_user(username, password, role):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = 'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)'
    # Securely hash the password before saving
    hashed_password = generate_password_hash(password)
    
    try:
        cursor.execute(query, (username, hashed_password, role))
        conn.commit()
        success = True
    except Exception as e:
        print('ERROR', str(e)) # to be completed
        # if something goes wrong: rollback
        conn.rollback()

    cursor.close()
    conn.close()

        
    return success

"""This functuin checks if a user exists and the password is correct."""
# domething to be completed here
def verify_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = 'SELECT * FROM users WHERE username = ?'
    cursor.execute(query, (username,))
    user_row = cursor.fetchone()
    conn.close()

    # If the user exists AND the provided password matches the stored hash
    if user_row and check_password_hash(user_row['password_hash'], password):
        return User(id=user_row['id'], username=user_row['username'], role=user_row['role'])
    
    return None
