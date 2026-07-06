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
app = Flask(__name__)

# Required by Flask for session management
app.config['SECRET_KEY'] = 'a_very_secret_key_for_exam' 

# Simulated Current Time
SIMULATED_DAY = "Wednesday"
SIMULATED_TIME = "14:00"

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

        if role not in ['adventurer', 'guild_master']:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('register'))

        # Attempt to create the user
        if db.create_user(username, password, role):
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username is already taken.', 'danger')

    return render_template('register.html')

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

    if request.method == 'POST':
        # 1. Authentication Check
        if not current_user.is_authenticated:
            flash("You must be logged in to join a quest.", "warning")
            return redirect(url_for('login'))
            
        # 2. Role Check
        if current_user.role != 'adventurer':
            flash("Guild Masters cannot join quest sessions.", "danger")
            return redirect(url_for('session_detail', session_id=session_id))

        party_role = request.form.get('party_role')
        places = int(request.form.get('places_reserved', 1))

        # 3. Capacity Check
        if availability.get(party_role, 0) < places:
            flash(f"Not enough places available for the {party_role} role.", "danger")
            return redirect(url_for('session_detail', session_id=session_id))

        schedule = db.get_adventurer_schedule(current_user.UId)
        
        # 4. Weekly Limit Check (Max 3)
        if len(schedule) >= 3:
            flash("You have reached your weekly limit of 3 quest sessions.", "danger")
            return redirect(url_for('session_detail', session_id=session_id))

        # 5. Time Overlap Check (And duplicate joining prevention)
        new_start = datetime.strptime(session_data['start_time'], '%H:%M')
        new_end = new_start + timedelta(minutes=session_data['duration'])

        for task in schedule:
            if task['day'] == session_data['day']:
                task_start = datetime.strptime(task['start_time'], '%H:%M')
                task_end = task_start + timedelta(minutes=task['duration'])
                
                # Formula for time overlap: (Start A < End B) and (Start B < End A)
                if new_start < task_end and task_start < new_end:
                    flash("This session overlaps in time with another quest you have joined.", "danger")
                    return redirect(url_for('session_detail', session_id=session_id))

        # If all checks pass, save to database
        db.join_session(session_id, current_user.UId, party_role, places)
        flash(f"Successfully joined the quest as {party_role} (Places: {places})!", "success")
        return redirect(url_for('index')) # We will change this to redirect to the profile page later

    return render_template('session_detail.html', session=session_data, availability=availability)

if __name__ == '__main__':
    app.run(debug=True)