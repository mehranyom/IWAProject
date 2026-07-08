from datetime import datetime, timedelta
from flask import request, redirect, url_for, flash
from flask_login import current_user
import db


def has_time_overlap(new_session, schedule):
    """Calculates if a new session overlaps with an existing schedule."""
    new_start = datetime.strptime(new_session['start_time'], '%H:%M')
    new_end = new_start + timedelta(minutes=new_session['duration'])

    for task in schedule:
        # Using 'continue' acts as a guard clause inside the loop, preventing deep nesting
        if task['day'] != new_session['day']:
            continue 
            
        task_start = datetime.strptime(task['start_time'], '%H:%M')
        task_end = task_start + timedelta(minutes=task['duration'])
        
        # Formula for time overlap: (Start A < End B) and (Start B < End A)
        if new_start < task_end and task_start < new_end:
            return True
            
    return False

def handle_booking_request(session_id, session_data, availability):
    """Processes all validation checks for joining a quest."""
    if not current_user.is_authenticated:
        flash("You must be logged in to join a quest.", "warning")
        return redirect(url_for('login'))
        
    if current_user.role != 'Adventurer':
        flash("Guild Masters cannot join quest sessions.", "danger")
        return redirect(url_for('session_detail', session_id=session_id))

    party_role = request.form.get('party_role')
    places = int(request.form.get('places_reserved', 1))

    if availability.get(party_role, 0) < places:
        flash(f"Not enough places available for the {party_role} role.", "danger")
        return redirect(url_for('session_detail', session_id=session_id))

    schedule = db.get_adventurer_schedule(current_user.UId)
    
    if len(schedule) >= 3:
        flash("You have reached your weekly limit of 3 quest sessions.", "danger")
        return redirect(url_for('session_detail', session_id=session_id))

    # Call the new helper function here
    if has_time_overlap(session_data, schedule):
        flash("This session overlaps in time with another quest you have joined.", "danger")
        return redirect(url_for('session_detail', session_id=session_id))

    db.join_session(session_id, current_user.UId, party_role, places)
    flash(f"Successfully joined the quest as {party_role} (Places: {places})!", "success")
    return redirect(url_for('index'))


def get_total_hours(day_str, time_str):
    """Converts a day and time into total hours since Monday 00:00."""
    days = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
        "Friday": 4, "Saturday": 5, "Sunday": 6
    }
    hours, minutes = map(int, time_str.split(':'))
    return (days[day_str] * 24) + hours + (minutes / 60.0)

def can_modify_session(session_day, session_time, current_day, current_time):
    """Returns True if the session starts more than 8 hours from now."""
    session_total = get_total_hours(session_day, session_time)
    current_total = get_total_hours(current_day, current_time)
    
    # If the current total is higher, the session is in the past
    return (session_total - current_total) > 8