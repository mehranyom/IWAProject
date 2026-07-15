from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
import db
import util
import os
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)

# Required by Flask for session management
app.config['SECRET_KEY'] = '8f42a73054b17c43d03f0254c79893d5' 
# Required by Flask for securing forms to validate them on the back end.
csrf = CSRFProtect(app)

# File Upload Configuration for profile avatars and quest promotional images.
UPLOAD_FOLDER = os.path.join('static', 'images', 'avatars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper function to check file extensions for uploaded images
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Simulated Current Time 
# The application uses a simulated current day and time within a fictional week to test modifiable and non-modifiable participations.
SIMULATED_DAY = "Monday"
SIMULATED_TIME = "11:00"

# Constant variables defining the two types of registered users.
GM = 'Guild Master'
AD = 'Adventurer'

# --- FLASK-LOGIN SETUP ---
# Use of Flask-Login for authentication management as per technical requirements.
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Tells Flask where to send users if they need to log in

@login_manager.user_loader
def load_user(user_id):
    # Loads the user from the database using the session's stored user ID
    return db.get_user_by_id(user_id)


@app.route('/')
def index():
    # On the homepage, all users see a short version of the available quest program.
    # Through specific filters, users can explore quest sessions by day, quest type, difficulty level, or available role.
    day_filter = request.args.get('day')
    type_filter = request.args.get('quest_type')
    difficulty_filter = request.args.get('difficulty')
    warrior_places = int(request.args.get('warrior_places', 0))
    mage_places = int(request.args.get('mage_places', 0))
    healer_places = int(request.args.get('healer_places', 0))
    
    # Retrieve the filtered sessions from the database
    sessions = db.get_quest_program(
        day_filter, type_filter, difficulty_filter, 
        warrior_places, mage_places, healer_places
    )

    return render_template('index.html', 
                           sessions=sessions, 
                           current_day=SIMULATED_DAY, 
                           current_time=SIMULATED_TIME,
                           day_filter=day_filter,             
                           type_filter=type_filter,           
                           difficulty_filter=difficulty_filter,
                           warrior_places=warrior_places,
                           mage_places=mage_places,
                           healer_places=healer_places)


@app.route('/register', methods=['GET', 'POST'])
def register():
    # If already logged in, send them to the homepage
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        # Registration requires a unique field used to identify the user, such as a username.
        username = request.form.get('username')
        password = request.form.get('password')

        # Back-end Validation for mandatory fields.
        if not username or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('register'))

        # Attempt to create the user in the database
        if db.create_user(username, password):
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username is already taken.', 'danger')

    return render_template('register.html')


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    # Allows authenticated users to update their profile information
    if request.method == 'POST':
        update_type = request.form.get('update_type')

        # Route the request to the appropriate helper function based on the form submitted
        if update_type == 'username':
            util.handle_username_update(request.form, current_user.UId)
            
        elif update_type == 'password':
            util.handle_password_update(request.form, current_user.UId)
            
        elif update_type == 'avatar':
            util.handle_avatar_update(request.files, current_user, app.config)

        # Always redirect back after a POST to prevent duplicate submissions
        return redirect(url_for('edit_profile'))

    # Handle GET request to display the edit profile form
    return render_template('edit_profile.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    # To join a quest, an adventurer must be registered and logged in.
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Verify credentials against the database hash
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


@app.route('/quests')
def all_quests():
    # Fetches and displays a list of all available quests
    quests = db.get_all_quests_details()
    return render_template('quests.html', quests=quests)

@app.route('/quest/<int:quest_id>')
def quest_detail(quest_id):
    # Retrieves comprehensive information about a specific quest and its scheduled sessions
    quest, sessions = db.get_quest_and_sessions(quest_id)
    
    if not quest:
        flash("Quest not found.", "danger")
        return redirect(url_for('all_quests'))
        
    return render_template('quest_detail.html', quest=quest, sessions=sessions)


@app.route('/session/<int:session_id>', methods=['GET', 'POST'])
def session_detail(session_id):
    # By clicking on a quest session, users can view all detailed information.
    session_data = db.get_session_details(session_id)
    if not session_data:
        flash("Quest session not found.", "danger")
        return redirect(url_for('index'))

    # Check remaining places for Warrior, Mage, and Healer roles.
    availability = db.get_role_availability(session_id)

    # Calculate if the session has already passed based on the simulated current day and time.
    session_total = util.get_total_hours(session_data['day'], session_data['start_time'])
    current_total = util.get_total_hours(SIMULATED_DAY, SIMULATED_TIME)
    is_expired = session_total < current_total

    # Delegate the heavy lifting of joining a session to the helper function in util.py
    if request.method == 'POST':
        return util.handle_booking_request(
            session_id, 
            session_data, 
            availability,
            SIMULATED_DAY,
            SIMULATED_TIME
        )

    # Pass session details, role availability, and expiration status to the template
    return render_template(
        'session_detail.html', 
        session=session_data, 
        availability=availability,
        is_expired=is_expired
    )


@app.route('/profile')
@login_required
def profile():
    # The profile page shows the adventurer's participations: quest title, day, time, location, role, and reserved places.
    if current_user.role != AD:
        flash("Guild Masters have a different dashboard.", "info")
        return redirect(url_for('gm_dashboard'))

    raw_participations = db.get_user_participations(current_user.UId)
    
    # Convert rows to dictionaries to add the 'is_modifiable' flag based on the 8-hour rule.
    participations = []
    total_places = 0
    for row in raw_participations:
        part_dict = dict(row)
        # Quest participations can be modified only if the session starts more than 8 hours after the simulated time.
        part_dict['is_modifiable'] = util.can_modify_session(
            row['day'], row['start_time'], SIMULATED_DAY, SIMULATED_TIME
        )
        total_places += row['places_reserved']
        participations.append(part_dict)

    return render_template('adventurer_profile.html', participations=participations, total_places=total_places)


@app.route('/profile/cancel/<int:participation_id>', methods=['POST'])
@login_required
def cancel_booking(participation_id):
    if current_user.role != AD:
        return redirect(url_for('index'))

    # 1. Fetch the record to ensure it belongs to the currently logged-in user
    part = db.get_participation_by_id(participation_id, current_user.UId)
    
    if not part:
        flash("Participation record not found or unauthorized.", "danger")
        return redirect(url_for('profile'))

    # 2. Re-verify the 8-hour cancellation rule on the backend to prevent malicious requests.
    if not util.can_modify_session(part['day'], part['start_time'], SIMULATED_DAY, SIMULATED_TIME):
        flash("Cannot cancel. This session starts in less than 8 hours.", "danger")
        return redirect(url_for('profile'))

    # 3. Execute cancellation in the database
    db.cancel_participation(participation_id, current_user.UId)
    flash("Quest participation cancelled successfully.", "success")
    return redirect(url_for('profile'))


@app.route('/profile/modify/<int:participation_id>', methods=['POST'])
@login_required
def modify_booking(participation_id):
    if current_user.role != AD:
        return redirect(url_for('index'))

    new_role = request.form.get('party_role')
    new_places = int(request.form.get('places_reserved', 1))

    # checking that input for number of reserves is limited between 1 and 2
    if new_places < 1 or new_places > 2:
        flash("You can reserve at most 2 places per quest session.", "danger")
        return redirect(url_for('profile'))

    part = db.get_participation_by_id(participation_id, current_user.UId)
    
    if not part:
        flash("Participation record not found.", "danger")
        return redirect(url_for('profile'))

    # Re-verify the 8-hour modification rule on the backend.
    if not util.can_modify_session(part['day'], part['start_time'], SIMULATED_DAY, SIMULATED_TIME):
        flash("Cannot modify. This session starts in less than 8 hours.", "danger")
        return redirect(url_for('profile'))

    # Check capacity constraints for the session to ensure places aren't overbooked.
    availability = db.get_role_availability(part['SId'])
    
    # "Refund" the user's currently held places to the availability pool to accurately test new capacity
    availability[part['party_role']] = availability.get(part['party_role'], 0) + part['places_reserved']
    
    if availability.get(new_role, 0) < new_places:
        flash(f"Not enough places available for {new_role}.", "danger")
        return redirect(url_for('profile'))
        
    # Each adventurer can join at most 3 quest sessions during the week.
    schedule = db.get_adventurer_schedule(current_user.UId)
    current_total_places = sum(task['places_reserved'] for task in schedule)
    
    if (current_total_places - part['places_reserved'] + new_places) > 3:
        flash("Modification exceeds your weekly limit of 3 quest places.", "danger")
        return redirect(url_for('profile'))

    # Execute the modification in the database
    db.update_participation(participation_id, current_user.UId, new_role, new_places)
    flash("Quest participation modified successfully.", "success")
    return redirect(url_for('profile'))


@app.route('/gm/dashboard')
@login_required
def gm_dashboard():
    # Security Check: Ensure only the Guild Master can access this view.
    if current_user.role != GM:
        flash("Access denied. Only Guild Masters can view this page.", "danger")
        return redirect(url_for('profile'))

    raw_stats = db.get_gm_dashboard_stats()
    quests_grouped = {}

    # Data Processing & Grouping: The Guild Master profile page shows scheduled sessions grouped by their quests.
    for row in raw_stats:
        qid = row['QId']
        
        # Initialize the quest group (creates the card/section even if no sessions exist yet)
        if qid not in quests_grouped:
            quests_grouped[qid] = {
                'title': row['title'],
                'sessions': []
            }
        
        # Only process and append session data if a session actually exists
        if row['SId'] is not None:
            # Calculate dynamic statistics for the Guild Master (remaining places, most requested roles).
            roles = {
                'Warrior': row['warrior_res'], 
                'Mage': row['mage_res'], 
                'Healer': row['healer_res']
            }
            
            max_res = max(roles.values())
            if max_res == 0:
                most_requested = "None yet"
            else:
                # Gets all roles tied for the highest number of reservations
                most_requested = ", ".join([k for k, v in roles.items() if v == max_res])

            session_dict = dict(row)
            # Total capacity is 9 places (4 Warrior + 3 Mage + 2 Healer).
            session_dict['remaining_places'] = 9 - row['total_reserved'] 
            session_dict['most_requested'] = most_requested
            
            quests_grouped[qid]['sessions'].append(session_dict)

    return render_template('gm_dashboard.html', quests_grouped=quests_grouped)


@app.route('/gm/cancel_session/<int:session_id>', methods=['POST'])
@login_required
def gm_cancel_session(session_id):
    if current_user.role != GM:
        return redirect(url_for('index'))

    # A quest session can be cancelled only if no adventurer has joined it.
    success = db.cancel_session_if_empty(session_id)
    
    if success:
        flash("Session cancelled successfully.", "success")
    else:
        flash("Cannot cancel this session. Adventurers have already joined.", "danger")
        
    return redirect(url_for('gm_dashboard'))


@app.route('/gm/edit_session_field/<int:session_id>', methods=['POST'])
@login_required
def gm_edit_session_field(session_id):
    if current_user.role != GM:
        return redirect(url_for('index'))

    update_type = request.form.get('update_type')
    new_value = request.form.get('new_value')

    if not update_type or not new_value:
        flash("Invalid submission.", "danger")
        return redirect(url_for('gm_dashboard'))
    
    # Check if a modification happened to a field that can cause an overlap constraint violation
    if update_type in ['day', 'start_time', 'location']:
        session_row = db.get_session_details(session_id)
        session_data = dict(session_row)
        session_data[f'{update_type}'] = new_value
        
        day = session_data['day']
        start_time = session_data['start_time']
        location = session_data['location']
        duration = session_data['duration'] 
        
        # When modifying, the system must prevent overlaps in the same day, time and location.
        if db.check_session_overlap(day, start_time, duration, location, exclude_session_id=session_id):
            flash(f"Overlap detected: The {location} is already booked on {day} around {start_time}.", "danger")
            return redirect(url_for('gm_dashboard'))

    # Attempt the update using the DB function. Session modifications are allowed if no adventurer has joined.
    success = db.update_single_session_field(session_id, update_type, new_value)
    
    if success:
        flash(f"Session {update_type.replace('_', ' ')} updated successfully.", "success")
    else:
        flash("Cannot modify this session. Adventurers have already joined.", "danger")
        
    return redirect(url_for('gm_dashboard'))


@app.route('/gm/create_quest', methods=['GET', 'POST'])
@login_required
def create_quest():
    # The Guild Master can manage the weekly quest program and create new quests.
    if current_user.role != GM:
        flash("Access denied. Only Guild Masters can create quests.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Retrieve mandatory quest information: title, duration, type, difficulty, description, image.
        title = request.form.get('title')
        duration = request.form.get('duration')
        quest_type = request.form.get('quest_type')
        difficulty = request.form.get('difficulty')
        description = request.form.get('description')
        
        image_file = request.files.get('image_file')
        image_filename = "dq.jpg" # Default fallback image if no file is uploaded

        # Safely handle and store the promotional image or illustration.
        if image_file and image_file.filename != '' and allowed_file(image_file.filename):
            original_filename = secure_filename(image_file.filename)
            image_filename = f"quest_{original_filename}"
            
            quest_upload_path = os.path.join('static', 'images', 'quests')
            os.makedirs(quest_upload_path, exist_ok=True) 
            
            save_path = os.path.join(quest_upload_path, image_filename)
            image_file.save(save_path)

        if not (title and duration and quest_type and difficulty):
            flash("Please fill in all mandatory fields.", "danger")
            return redirect(url_for('create_quest'))

        db.create_quest(title, int(duration), quest_type, difficulty, description, image_filename)
        # Once created, a quest cannot be modified.
        flash("Quest created successfully! It is now permanently recorded.", "success")
        return redirect(url_for('gm_dashboard'))

    return render_template('create_quest.html')


@app.route('/gm/schedule_session', methods=['GET', 'POST'])
@login_required
def schedule_session():
    # The Guild Master can schedule related quest sessions.
    if current_user.role != GM:
        flash("Access denied.", "danger")
        return redirect(url_for('index'))

    # Fetch existing quests to populate the HTML <select> dropdown
    quests = db.get_all_quests_for_dropdown()

    if request.method == 'POST':
        quest_id = request.form.get('quest_id')
        day = request.form.get('day')
        start_time = request.form.get('start_time')
        location = request.form.get('location')

        if not (quest_id and day and start_time and location):
            flash("All fields are required to schedule a session.", "danger")
            return redirect(url_for('schedule_session'))

        # Fetch the quest duration to accurately calculate the end time
        quest_data, _ = db.get_quest_and_sessions(quest_id)
        duration = quest_data['duration']

        # Prevent overlaps in the same day, time and location so each location hosts one session at a time.
        if db.check_session_overlap(day, start_time, duration, location):
            flash(f"Overlap detected: The {location} is already booked on {day} around {start_time}.", "danger")
            return redirect(url_for('schedule_session'))

        db.schedule_session(quest_id, day, start_time, location)
            
        flash("Quest session scheduled successfully!", "success")
        return redirect(url_for('gm_dashboard'))

    return render_template('schedule_session.html', quests=quests)


if __name__ == '__main__':
    # Add port=5001 to bypass the AirPlay conflict locally
    app.run(debug=True, port=5001)