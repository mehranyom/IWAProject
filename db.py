import sqlite3
from model import User
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

def get_db_connection():
    """
    Connects to the local SQLite database file and configures the connection
    to return dictionary-like rows. This avoids writing repetitive connection code.
    Use of SQLite as a relational database for the back end is required[cite: 1].
    """
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_quest_program(day_filter=None, type_filter=None, difficulty_filter=None, warrior_req=0, mage_req=0, healer_req=0):
    """
    Fetches sessions joined with quest info, applying optional filters.
    Allows users to explore quest sessions by day, quest type, difficulty level, or available role[cite: 1].
    """
    conn = get_db_connection()
    
    query = '''
        SELECT sessions.SId, sessions.day, sessions.start_time, sessions.location,
               quests.title, quests.quest_type, quests.difficulty, quests.duration
        FROM sessions
        JOIN quests ON sessions.QId = quests.QId
        WHERE 1=1
    '''
    params = []
    
    # Apply specific filters if they are provided in the request arguments
    if day_filter:
        query += ' AND sessions.day = ?'
        params.append(day_filter)
    if type_filter:
        query += ' AND quests.quest_type = ?'
        params.append(type_filter)
    if difficulty_filter:
        query += ' AND quests.difficulty = ?'
        params.append(difficulty_filter)

    # Validate against the required places for each role category[cite: 1].
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

    # Sort logically by Day of the Week, then by Time to present an ordered schedule[cite: 1].
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


def get_user_by_id(uid):
    """Fetches a user from the database by their unique ID and returns a User object."""
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
    """Dynamically updates the user's profile data (username, password hash, or avatar)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
        
    # Safety check: if no fields were provided, exit early
    if not update_fields:
        return True
        
    query = f"UPDATE users SET {', '.join(update_fields)} WHERE UId = ?"
    params.append(user_id)
    
    try:
        cursor.execute(query, tuple(params))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # Prevents setting a username that already exists in the database
        success = False
    finally:
        conn.close()
        
    return success


def create_user(username, password):
    """
    Hashes the password and inserts a new registered user (Adventurer) into the database.
    Registration requires a unique field (username) to identify the user[cite: 1].
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Check if the username already exists (case-insensitive check)
    check_query = 'SELECT username FROM users WHERE LOWER(username) = LOWER(?)'
    cursor.execute(check_query, (username,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        cursor.close()
        conn.close()
        return False

    # 2. Insert as 'Adventurer' since standard registration is for adventurers[cite: 1].
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


def verify_user(username, password):
    """Verifies a user's login credentials against the stored password hash."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = 'SELECT * FROM users WHERE username = ?'
    cursor.execute(query, (username,))
    user_row = cursor.fetchone()
    conn.close()

    if user_row and check_password_hash(user_row['password_hash'], password):
        return User(id=user_row['UId'], username=user_row['username'], role=user_row['role'], avatar_filename=user_row['avatar_filename'])
    
    return None

def get_all_quests_details():
    """Fetches all quests from the database to display on the main quests index."""
    conn = get_db_connection()
    quests = conn.execute('SELECT * FROM quests ORDER BY title').fetchall()
    conn.close()
    return quests

def get_quest_and_sessions(quest_id):
    """
    Fetches a specific quest's details alongside its connected quest sessions, 
    including day, starting time, and location[cite: 1].
    """
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


def get_session_details(sid):
    """Fetches complete details for a specific session by joining the sessions and quests tables."""
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


def get_role_availability(sid):
    """
    Calculates how many places are left for each role category in a given session.
    Each quest session supports Warrior (4), Mage (3), and Healer (2) roles[cite: 1].
    """
    conn = get_db_connection()
    query = '''
        SELECT party_role, SUM(places_reserved) as taken
        FROM participations
        WHERE SId = ?
        GROUP BY party_role
    '''
    results = conn.execute(query, (sid,)).fetchall()
    conn.close()

    # Base capacity constraints defined by the exam requirements[cite: 1].
    availability = {'Warrior': 4, 'Mage': 3, 'Healer': 2}
    
    # Subtract currently reserved places to find the remaining availability
    for row in results:
        role = row['party_role']
        if role in availability: 
            availability[role] -= row['taken']
            
    return availability


def get_adventurer_schedule(uid):
    """
    Fetches all sessions an adventurer has currently joined. 
    Used to verify the 3-place weekly limit and check for time overlaps[cite: 1].
    """
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


def join_session(sid, uid, party_role, places):
    """Inserts a new participation record linking the user to a session with their selected role and places."""
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
    """Fetches all joined quests for a specific adventurer, ordered logically to display on their profile page[cite: 1]."""
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
    """Fetches a specific participation to verify ownership and timing before allowing modification or cancellation."""
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
    """Deletes the participation record. The user_id check ensures a user cannot delete someone else's booking maliciously."""
    conn = get_db_connection()
    query = 'DELETE FROM participations WHERE PId = ? AND UId = ?'
    conn.execute(query, (participation_id, user_id))
    conn.commit()
    conn.close()

def update_participation(participation_id, user_id, new_role, new_places):
    """Updates the role category and number of reserved places for an existing participation."""
    conn = get_db_connection()
    query = '''
        UPDATE participations 
        SET party_role = ?, places_reserved = ? 
        WHERE PId = ? AND UId = ?
    '''
    conn.execute(query, (new_role, new_places, participation_id, user_id))
    conn.commit()
    conn.close()


# --- Guild Master Dashboard Related ---

def get_gm_dashboard_stats():
    """
    Fetches all scheduled quest sessions grouped/linked by their respective quests,
    along with participation statistics such as reserved places per role category[cite: 1].
    """
    conn = get_db_connection()
    
    # LEFT JOIN ensures quests without active sessions are still included in the dashboard.
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


def cancel_session_if_empty(session_id):
    """Deletes a session strictly if no adventurer has joined it[cite: 1]."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify participant count is exactly 0
    cursor.execute('SELECT COUNT(*) as count FROM participations WHERE SId = ?', (session_id,))
    count = cursor.fetchone()['count']
    
    if count > 0:
        conn.close()
        return False # Cancellation blocked due to active participants
        
    # Safe to delete
    cursor.execute('DELETE FROM sessions WHERE SId = ?', (session_id,))
    conn.commit()
    conn.close()
    return True

def update_single_session_field(session_id, field_name, new_value):
    """Updates a single session field (day, time, location) strictly if no adventurer has joined it[cite: 1]."""
    # Strict whitelist to prevent SQL injection on column names
    allowed_fields = ['day', 'start_time', 'location']
    if field_name not in allowed_fields:
        return False
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify participant count is exactly 0 before modifying[cite: 1].
    cursor.execute('SELECT COUNT(*) as count FROM participations WHERE SId = ?', (session_id,))
    if cursor.fetchone()['count'] > 0:
        conn.close()
        return False 
        
    # Execute dynamic update
    query = f'UPDATE sessions SET {field_name} = ? WHERE SId = ?'
    cursor.execute(query, (new_value, session_id))
    conn.commit()
    conn.close()
    return True


def create_quest(title, duration, quest_type, difficulty, description, image_filename):
    """Inserts a new quest into the database. Once created, a quest cannot be modified[cite: 1]."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO quests (title, duration, quest_type, difficulty, description, image_filename)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, duration, quest_type, difficulty, description, image_filename))
    conn.commit()
    conn.close()

def get_all_quests_for_dropdown():
    """Fetches basic quest info to populate the scheduling form for the Guild Master."""
    conn = get_db_connection()
    quests = conn.execute('SELECT QId, title FROM quests ORDER BY title').fetchall()
    conn.close()
    return quests

def check_session_overlap(day, start_time, duration, location, exclude_session_id=None):
    """
    Returns True if the new session time window overlaps with any existing session at the same location.
    The system must prevent overlaps so that each location hosts only one quest session at a time[cite: 1].
    """
    conn = get_db_connection()
    
    query = '''
        SELECT s.SId, s.start_time, q.duration 
        FROM sessions s
        JOIN quests q ON s.QId = q.QId
        WHERE s.day = ? AND s.location = ?
    '''
    params = [day, location]
    
    # If a GM is modifying an existing session, exclude it from the overlap logic
    if exclude_session_id:
        query += ' AND s.SId != ?'
        params.append(exclude_session_id)
        
    existing_sessions = conn.execute(query, params).fetchall()
    conn.close()
    
    # Calculate start and end times for the incoming session
    new_start = datetime.strptime(start_time, '%H:%M')
    new_end = new_start + timedelta(minutes=int(duration))
    
    # Check against all existing sessions at that specific location
    for session in existing_sessions:
        task_start = datetime.strptime(session['start_time'], '%H:%M')
        task_end = task_start + timedelta(minutes=session['duration'])
        
        # Formula for time overlap logic: (Start A < End B) and (Start B < End A)
        if new_start < task_end and task_start < new_end:
            return True
            
    return False

def schedule_session(quest_id, day, start_time, location):
    """Inserts a new scheduled session created by the Guild Master."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO sessions (QId, day, start_time, location)
        VALUES (?, ?, ?, ?)
    ''', (quest_id, day, start_time, location))
    conn.commit()
    conn.close()