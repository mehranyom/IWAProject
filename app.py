from flask import Flask, render_template, request
from flask_login import LoginManager
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
# -------------------------

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

if __name__ == '__main__':
    app.run(debug=True)