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

    # Delegate the heavy lifting to the helper function
    if request.method == 'POST':
        return util.handle_booking_request(session_id, session_data, availability)

    return render_template('session_detail.html', session=session_data, availability=availability)


@app.route('/profile')
@login_required
def profile():
    if current_user.role != 'adventurer':
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
    if current_user.role != 'adventurer':
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

if __name__ == '__main__':
    app.run(debug=True)