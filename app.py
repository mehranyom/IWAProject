from flask import Flask, render_template
import db


app = Flask(__name__)

SIMULATED_DAY = "Wednesday"
SIMULATED_TIME = "14:00"

@app.route('/')
def index():
    # Pass simulated time to templates for testing
    return render_template('index.html', current_day=SIMULATED_DAY, current_time=SIMULATED_TIME)

if __name__ == '__main__':
    app.run(debug=True)