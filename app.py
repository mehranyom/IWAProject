from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
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

@app.route('/')
def index():
    day_filter = request.args.get('day')
    type_filter = request.args.get('quest_type')
    difficulty_filter = request.args.get('difficulty')
    
    sessions = db.get_quest_program(day_filter, type_filter, difficulty_filter)
    
    return render_template('index.html', 
                           sessions=sessions, 
                           current_day=SIMULATED_DAY, 
                           current_time=SIMULATED_TIME)


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



if __name__ == '__main__':
    app.run(debug=True)