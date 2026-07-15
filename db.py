import sqlite3
from model import User
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

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
def get_quest_program(day_filter=None, type_filter=None, difficulty_filter=None, warrior_req=0, mage_req=0, healer_req=0):
    """Fetches sessions joined with quest info, applying optional filters."""
    conn = get_db_connection()
    
    query = '''
        SELECT sessions.SId, sessions.day, sessions.start_time, sessions.location,
               quests.title, quests.quest_type, quests.difficulty, quests.duration
        FROM sessions
        JOIN quests ON sessions.QId = quests.QId
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


    capacities = {'Warrior': (4, warrior_req), 'Mage': (3, mage_req), 'Healer': (2, healer_req)}
    
    for role_name, (max_cap, req_places) in capacities.items():
        if req_places > 0:
            query += '''
                AND ? - (
                    SELECT COALESCE(SUM(places_reserved), 0)
                    FROM participations
                    WHERE participations.SId = sessions.SId AND participations.party_role = ?
                ) >= ?
            '''
            params.extend([max_cap, role_name, req_places])

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
def get_user_by_id(uid):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = 'SELECT * FROM users WHERE UId = ?'
    cursor.execute(query, (uid,))
    user_row = cursor.fetchone()
    conn.close()
    
    if user_row:
        return User(id=user_row['UId'],
                    username=user_row['username'],
                    role=user_row['role'], 
                    avatar_filename=user_row['avatar_filename'])
    return None

def update_user_profile(user_id, new_username=None, new_password=None, new_avatar=None):
    """Dynamically updates the user's profile data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Store the exact columns we need to update
    update_fields = []
    params = []
    
    if new_username:
        update_fields.append("username = ?")
        params.append(new_username)
        
    if new_password:
        update_fields.append("password_hash = ?")
        params.append(generate_password_hash(new_password))
        
    if new_avatar:
        update_fields.append("avatar_filename = ?")
        params.append(new_avatar)
        
    # Safety check: if nothing was provided, just return True
    if not update_fields:
        return True
        
    # Join the fields together with commas
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE UId = ?"
    params.append(user_id)
    
    try:
        cursor.execute(query, tuple(params))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # This triggers if they try to change their username to one that already exists
        success = False
    finally:
        conn.close()
        
    return success

# to be completed to meet only one GM constraint
"""This Function hashes the password and inserts a new user into the database."""
def create_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Check if the username already exists (ignoring case)
    check_query = 'SELECT username FROM users WHERE LOWER(username) = LOWER(?)'
    cursor.execute(check_query, (username,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        # A match was found, so the username is taken
        cursor.close()
        conn.close()
        return False

    # 2. If it is unique, proceed with the insertion using their original casing
    insert_query = 'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)'
    hashed_password = generate_password_hash(password)
    success = False
    
    try:
        cursor.execute(insert_query, (username, hashed_password, 'Adventurer'))
        conn.commit()
        success = True
    except Exception as e:
        print('ERROR', str(e))
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
        return User(id=user_row['UId'], username=user_row['username'], role=user_row['role'], avatar_filename=user_row['avatar_filename'])
    
    return None

def get_all_quests_details():
    """Fetches all quests from the database to display on the main quests page."""
    conn = get_db_connection()
    quests = conn.execute('SELECT * FROM quests ORDER BY title').fetchall()
    conn.close()
    return quests

def get_quest_and_sessions(quest_id):
    """Fetches a specific quest's details and all sessions related to it."""
    conn = get_db_connection()
    
    quest = conn.execute('SELECT * FROM quests WHERE QId = ?', (quest_id,)).fetchone()
    
    # Sort logically by Day of Week, then by Time
    sessions_query = '''
        SELECT SId, day, start_time, location 
        FROM sessions 
        WHERE QId = ? 
        ORDER BY 
        CASE day
            WHEN 'Monday' THEN 1
            WHEN 'Tuesday' THEN 2
            WHEN 'Wednesday' THEN 3
            WHEN 'Thursday' THEN 4
            WHEN 'Friday' THEN 5
            WHEN 'Saturday' THEN 6
            WHEN 'Sunday' THEN 7
        END, start_time ASC
    '''
    sessions = conn.execute(sessions_query, (quest_id,)).fetchall()
    conn.close()
    
    return quest, sessions

""" these 3 function are for task 4. Quest session detail.
these has to be checked."""

def get_session_details(sid):
    """Fetches complete details for a specific session by joining tables."""
    conn = get_db_connection()
    query = '''
        SELECT sessions.SId, sessions.day, sessions.start_time, sessions.location,
               quests.title, quests.duration, quests.quest_type, quests.difficulty, 
               quests.description, quests.image_filename
        FROM sessions
        JOIN quests ON sessions.QId = quests.QId
        WHERE sessions.SId = ?
    '''
    session_data = conn.execute(query, (sid,)).fetchone()
    conn.close()
    return session_data


"""
Calculates how many places are left for each role in a session and return a dictionary as output containing availablity
for each role like this: {'Warrior': 4, 'Mage': 3, 'Healer': 2}
"""
def get_role_availability(sid):
    conn = get_db_connection()
    query = '''
        SELECT party_role, SUM(places_reserved) as taken
        FROM participations
        WHERE SId = ?
        GROUP BY party_role
    '''
    results = conn.execute(query, (sid,)).fetchall()
    conn.close()

    # Base capacity defined by exam rules
    availability = {'Warrior': 4, 'Mage': 3, 'Healer': 2}
    
    # Subtract taken places
    for row in results:
        role = row['party_role']
        if role in availability: # check if this "if" statement is necessary or not
            availability[role] -= row['taken']
            
    return availability


"""
Fetches all sessions an adventurer has currently joined to check limits and overlaps.
"""
def get_adventurer_schedule(uid):
    conn = get_db_connection()
    query = '''
        SELECT sessions.SId, sessions.day, sessions.start_time, quests.duration, participations.places_reserved
        FROM participations
        JOIN sessions ON participations.SId = sessions.SId
        JOIN quests ON sessions.QId = quests.QId
        WHERE participations.UId = ?
    '''
    schedule = conn.execute(query, (uid,)).fetchall()
    conn.close()
    return schedule


"""
Inserts the new participation record.
"""
def join_session(sid, uid, party_role, places):
    conn = get_db_connection()
    query = '''
        INSERT INTO participations (SId, UId, party_role, places_reserved)
        VALUES (?, ?, ?, ?)
    '''
    cursor = conn.cursor()
    cursor.execute(query, (sid, uid, party_role, places))
    conn.commit()
    conn.close()


def get_user_participations(user_id):
    """Fetches all joined quests for a specific adventurer, ordered logically."""
    conn = get_db_connection()
    query = '''
        SELECT p.PId as participation_id, p.party_role, p.places_reserved,
               s.SId as session_id, s.day, s.start_time, s.location,
               q.title, q.duration, q.quest_type
        FROM participations p
        JOIN sessions s ON p.SId = s.SId
        JOIN quests q ON s.QId = q.QId
        WHERE p.UId = ?
        ORDER BY 
        CASE s.day
            WHEN 'Monday' THEN 1
            WHEN 'Tuesday' THEN 2
            WHEN 'Wednesday' THEN 3
            WHEN 'Thursday' THEN 4
            WHEN 'Friday' THEN 5
            WHEN 'Saturday' THEN 6
            WHEN 'Sunday' THEN 7
        END, s.start_time ASC
    '''
    participations = conn.execute(query, (user_id,)).fetchall()
    conn.close()
    return participations

def get_participation_by_id(participation_id, user_id):
    """Fetches a specific participation to verify ownership and limits before modifying/cancelling."""
    conn = get_db_connection()
    query = '''
        SELECT p.PId, p.SId, p.party_role, p.places_reserved, s.day, s.start_time 
        FROM participations p
        JOIN sessions s ON p.SId = s.SId
        WHERE p.PId = ? AND p.UId = ?
    '''
    participation = conn.execute(query, (participation_id, user_id)).fetchone()
    conn.close()
    return participation

def cancel_participation(participation_id, user_id):
    """Deletes the participation record from the database."""
    conn = get_db_connection()
    # The user_id check ensures a user cannot delete someone else's booking maliciously
    query = 'DELETE FROM participations WHERE PId = ? AND UId = ?'
    conn.execute(query, 
                 (participation_id, user_id))
    conn.commit()
    conn.close()

def update_participation(participation_id, user_id, new_role, new_places):
    """Updates the role and reserved places for an existing participation."""
    conn = get_db_connection()
    query = '''
        UPDATE participations 
        SET party_role = ?, places_reserved = ? 
        WHERE PId = ? AND UId = ?
    '''
    conn.execute(query, (new_role, new_places, participation_id, user_id))
    conn.commit()
    conn.close()


"""Guild Master dashboard related"""

def get_gm_dashboard_stats():
    conn = get_db_connection()
    
    # Using LEFT JOIN on sessions ensures quests without sessions are included.
    # We must GROUP BY q.QId as well, otherwise all quests without a session 
    # would get bundled into a single row.
    query = '''
        SELECT 
            q.QId, q.title, 
            s.SId, s.day, s.start_time, s.location,
            COALESCE(SUM(p.places_reserved), 0) as total_reserved,
            COALESCE(SUM(CASE WHEN p.party_role = 'Warrior' THEN p.places_reserved ELSE 0 END), 0) as warrior_res,
            COALESCE(SUM(CASE WHEN p.party_role = 'Mage' THEN p.places_reserved ELSE 0 END), 0) as mage_res,
            COALESCE(SUM(CASE WHEN p.party_role = 'Healer' THEN p.places_reserved ELSE 0 END), 0) as healer_res
        FROM quests q
        LEFT JOIN sessions s ON q.QId = s.QId
        LEFT JOIN participations p ON s.SId = p.SId
        GROUP BY q.QId, s.SId
        ORDER BY q.title, 
        CASE s.day
            WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
            WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7
        END, s.start_time
    '''
    stats = conn.execute(query).fetchall()
    conn.close()
    return stats


"""
Deletes a session strictly if zero adventurers have joined it.
"""
def cancel_session_if_empty(session_id):
    conn = get_db_connection()
    
    # Check participant count first
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM participations WHERE SId = ?', (session_id,))
    count = cursor.fetchone()['count']
    
    if count > 0:
        conn.close()
        return False # Cannot cancel
        
    # Safe to delete
    cursor.execute('DELETE FROM sessions WHERE SId = ?', (session_id,))
    conn.commit()
    conn.close()
    return True

def update_single_session_field(session_id, field_name, new_value):
    """Updates a single session field strictly if zero adventurers have joined."""
    # Strict whitelist to prevent SQL injection on column names
    allowed_fields = ['day', 'start_time', 'location']
    if field_name not in allowed_fields:
        return False
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Verify participant count is 0
    cursor.execute('SELECT COUNT(*) as count FROM participations WHERE SId = ?', (session_id,))
    if cursor.fetchone()['count'] > 0:
        conn.close()
        return False 
        
    # 2. Update the specific field dynamically
    query = f'UPDATE sessions SET {field_name} = ? WHERE SId = ?'
    cursor.execute(query, (new_value, session_id))
    conn.commit()
    conn.close()
    return True

"""guild master form"""
def create_quest(title, duration, quest_type, difficulty, description, image_filename):
    """Inserts a new quest. Once created, it is immutable."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO quests (title, duration, quest_type, difficulty, description, image_filename)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, duration, quest_type, difficulty, description, image_filename))
    conn.commit()
    conn.close()

def get_all_quests_for_dropdown():
    """Fetches quests to populate the scheduling form."""
    conn = get_db_connection()
    # Using your updated QId column
    quests = conn.execute('SELECT QId, title FROM quests ORDER BY title').fetchall()
    conn.close()
    return quests

def check_session_overlap(day, start_time, duration, location, exclude_session_id=None):
    """Returns True if the new session time window overlaps with any existing session at the same location."""
    conn = get_db_connection()
    
    # Fetch all sessions for that day and location, joining with quests to get their durations
    query = '''
        SELECT s.SId, s.start_time, q.duration 
        FROM sessions s
        JOIN quests q ON s.QId = q.QId
        WHERE s.day = ? AND s.location = ?
    '''
    params = [day, location]
    
    # If modifying an existing session, exclude it from the overlap check
    if exclude_session_id:
        query += ' AND s.SId != ?'
        params.append(exclude_session_id)
        
    existing_sessions = conn.execute(query, params).fetchall()
    conn.close()
    
    # Calculate start and end times for the new session
    new_start = datetime.strptime(start_time, '%H:%M')
    new_end = new_start + timedelta(minutes=int(duration))
    
    # Check against all existing sessions at that location
    for session in existing_sessions:
        task_start = datetime.strptime(session['start_time'], '%H:%M')
        task_end = task_start + timedelta(minutes=session['duration'])
        
        # Formula for time overlap: (Start A < End B) and (Start B < End A)
        if new_start < task_end and task_start < new_end:
            return True
            
    return False

def schedule_session(quest_id, day, start_time, location):
    """Inserts a new scheduled session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Using your updated QId column
    cursor.execute('''
        INSERT INTO sessions (QId, day, start_time, location)
        VALUES (?, ?, ?, ?)
    ''', (quest_id, day, start_time, location))
    conn.commit()
    conn.close()