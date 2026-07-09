from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from datetime import datetime, timedelta
import db
import util
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)

# Required by Flask for session management
app.config['SECRET_KEY'] = 'a_very_secret_key_for_exam' 
# File Upload Configuration
UPLOAD_FOLDER = os.path.join('static', 'images', 'avatars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper function to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Simulated Current Time
SIMULATED_DAY = "Wednesday"
SIMULATED_TIME = "14:00"

# constant variables
GM = 'Guild Master'
AD = 'Adventurer'

# --- FLASK-LOGIN SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Tells Flask where to send users if they need to log in

@login_manager.user_loader
def load_user(user_id):
    # Uses the function we just added to db.py
    return db.get_user_by_id(user_id)


# changing filters. right now it's not possible to filter 2 sequential.
@app.route('/')
def index():
    day_filter = request.args.get('day')
    type_filter = request.args.get('quest_type')
    difficulty_filter = request.args.get('difficulty')
    
    sessions = db.get_quest_program(day_filter, type_filter, difficulty_filter)
    
    return render_template('index.html', 
                           sessions=sessions, 
                           current_day=SIMULATED_DAY, 
                           current_time=SIMULATED_TIME,
                           day_filter=day_filter,             
                           type_filter=type_filter,           
                           difficulty_filter=difficulty_filter)


@app.route('/register', methods=['GET', 'POST'])
def register():
    # If already logged in, send them to the homepage
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        # Back-end Validation
        if not username or not password or not role:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        if role not in [AD, GM]:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('register'))

        # Attempt to create the user
        if db.create_user(username, password, role):
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username is already taken.', 'danger')

    return render_template('register.html')


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        update_type = request.form.get('update_type')

        # Route the request to the appropriate helper function
        if update_type == 'username':
            util.handle_username_update(request.form, current_user.UId)
            
        elif update_type == 'password':
            util.handle_password_update(request.form, current_user.UId)
            
        elif update_type == 'avatar':
            util.handle_avatar_update(request.files, current_user, app.config)

        # Always redirect back after a POST
        return redirect(url_for('edit_profile'))

    # Handle GET request
    return render_template('edit_profile.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Verify credentials
        user = db.verify_user(username, password)
        
        if user:
            login_user(user) # This establishes the Flask-Login session
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

""" task 4. Quest session. to be ckecked."""
@app.route('/session/<int:session_id>', methods=['GET', 'POST'])
def session_detail(session_id):
    
    session_data = db.get_session_details(session_id)
    if not session_data:
        flash("Quest session not found.", "danger")
        return redirect(url_for('index'))

    availability = db.get_role_availability(session_id)

    # Delegate the heavy lifting to the helper function
    if request.method == 'POST':
        return util.handle_booking_request(session_id, session_data, availability)

    return render_template('session_detail.html', session=session_data, availability=availability)


@app.route('/profile')
@login_required
def profile():
    if current_user.role != AD:
        flash("Guild Masters have a different dashboard.", "info")
        return redirect(url_for('index')) # We will point this to GM Dashboard later

    raw_participations = db.get_user_participations(current_user.UId)
    
    # Convert rows to dictionaries to add the 'is_modifiable' flag
    participations = []
    for row in raw_participations:
        part_dict = dict(row)
        part_dict['is_modifiable'] = util.can_modify_session(
            row['day'], row['start_time'], SIMULATED_DAY, SIMULATED_TIME
        )
        participations.append(part_dict)

    return render_template('adventurer_profile.html', participations=participations)

@app.route('/profile/cancel/<int:participation_id>', methods=['POST'])
@login_required
def cancel_booking(participation_id):
    if current_user.role != AD:
        return redirect(url_for('index'))

    # 1. Fetch the record to ensure it belongs to this user
    part = db.get_participation_by_id(participation_id, current_user.UId)
    
    if not part:
        flash("Participation record not found or unauthorized.", "danger")
        return redirect(url_for('profile'))

    # 2. Re-verify the 8-hour rule on the backend
    if not util.can_modify_session(part['day'], part['start_time'], SIMULATED_DAY, SIMULATED_TIME):
        flash("Cannot cancel. This session starts in less than 8 hours.", "danger")
        return redirect(url_for('profile'))

    # 3. Execute cancellation
    db.cancel_participation(participation_id, current_user.UId)
    flash("Quest participation cancelled successfully.", "success")
    return redirect(url_for('profile'))

@app.route('/gm/dashboard')
@login_required
def gm_dashboard():
    # 1. Security Check
    if current_user.role != GM:
        flash("Access denied. Only Guild Masters can view this page.", "danger")
        return redirect(url_for('profile'))

    raw_stats = db.get_gm_dashboard_stats()
    quests_grouped = {}

    # 2. Data Processing & Grouping
    for row in raw_stats:
        qid = row['QId']
        
        # Initialize the quest group if it doesn't exist yet
        if qid not in quests_grouped:
            quests_grouped[qid] = {
                'title': row['title'],
                'sessions': []
            }
        
        # Calculate dynamic stats
        roles = {
            'Warrior': row['warrior_res'], 
            'Mage': row['mage_res'], 
            'Healer': row['healer_res']
        }
        
        max_res = max(roles.values())
        if max_res == 0:
            most_requested = "None yet"
        else:
            # Gets all roles tied for the highest number (e.g., "Warrior, Mage")
            most_requested = ", ".join([k for k, v in roles.items() if v == max_res])

        session_dict = dict(row)
        session_dict['remaining_places'] = 9 - row['total_reserved'] # 4W + 3M + 2H = 9 total
        session_dict['most_requested'] = most_requested
        
        quests_grouped[qid]['sessions'].append(session_dict)

    return render_template('gm_dashboard.html', quests_grouped=quests_grouped)

@app.route('/gm/cancel_session/<int:session_id>', methods=['POST'])
@login_required
def gm_cancel_session(session_id):
    if current_user.role != 'guild_master':
        return redirect(url_for('index'))

    success = db.cancel_session_if_empty(session_id)
    
    if success:
        flash("Session cancelled successfully.", "success")
    else:
        flash("Cannot cancel this session. Adventurers have already joined.", "danger")
        
    return redirect(url_for('gm_dashboard'))



@app.route('/gm/create_quest', methods=['GET', 'POST'])
@login_required
def create_quest():
    if current_user.role != GM:
        flash("Access denied. Only Guild Masters can create quests.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title')
        duration = request.form.get('duration')
        quest_type = request.form.get('quest_type')
        difficulty = request.form.get('difficulty')
        description = request.form.get('description')
        image_filename = request.form.get('image_filename') # Can be empty

        if not (title and duration and quest_type and difficulty):
            flash("Please fill in all mandatory fields.", "danger")
            return redirect(url_for('create_quest'))

        db.create_quest(title, int(duration), quest_type, difficulty, description, image_filename)
        flash("Quest created successfully! It is now permanently recorded.", "success")
        return redirect(url_for('gm_dashboard'))

    return render_template('create_quest.html')

@app.route('/gm/schedule_session', methods=['GET', 'POST'])
@login_required
def schedule_session():
    if current_user.role != GM:
        flash("Access denied.", "danger")
        return redirect(url_for('index'))

    # Fetch quests to populate the HTML <select> dropdown
    quests = db.get_all_quests_for_dropdown()

    if request.method == 'POST':
        quest_id = request.form.get('quest_id')
        day = request.form.get('day')
        start_time = request.form.get('start_time')
        location = request.form.get('location')

        if not (quest_id and day and start_time and location):
            flash("All fields are required to schedule a session.", "danger")
            return redirect(url_for('schedule_session'))

        # The Overlap Check
        if db.check_session_overlap(day, start_time, location):
            flash(f"Overlap detected: The {location} is already booked on {day} at {start_time}.", "danger")
            return redirect(url_for('schedule_session'))

        db.schedule_session(quest_id, day, start_time, location)
            
        flash("Quest session scheduled successfully!", "success")
        return redirect(url_for('gm_dashboard'))

    return render_template('schedule_session.html', quests=quests)



if __name__ == '__main__':
    # Add port=5001 to bypass the AirPlay conflict
    app.run(debug=True, port=5001)