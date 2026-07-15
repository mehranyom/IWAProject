from datetime import datetime, timedelta
from flask import request, redirect, url_for, flash
from flask_login import current_user
import db
import os
from werkzeug.utils import secure_filename
from app import allowed_file


def has_time_overlap(new_session, schedule):
    """
    Calculates if a new session overlaps with an adventurer's existing schedule.
    An adventurer cannot join two quest sessions that overlap in time[cite: 1].
    """
    new_start = datetime.strptime(new_session['start_time'], '%H:%M')
    new_end = new_start + timedelta(minutes=new_session['duration'])

    for task in schedule:
        # Guard clause: If the sessions are on different days, they cannot overlap.
        if task['day'] != new_session['day']:
            continue 
            
        task_start = datetime.strptime(task['start_time'], '%H:%M')
        task_end = task_start + timedelta(minutes=task['duration'])
        
        # Overlap occurs if the new session starts before the old one ends AND the old one starts before the new one ends.
        if new_start < task_end and task_start < new_end:
            return True
            
    return False

def handle_booking_request(session_id, session_data, availability, current_day, current_time):
    """Processes all business logic and validation checks required for joining a quest."""
    
    # To join a quest, an adventurer must be registered and logged in[cite: 1].
    if not current_user.is_authenticated:
        flash("You must be logged in to join a quest.", "warning")
        return redirect(url_for('login'))
        
    # The Guild Master can browse the website like adventurers, but cannot join quest sessions[cite: 1].
    if current_user.role != 'Adventurer':
        flash("Guild Masters cannot join quest sessions.", "danger")
        return redirect(url_for('session_detail', session_id=session_id))

    # Calculate total hours to prevent booking sessions that have passed in the simulated week.
    session_total = get_total_hours(session_data['day'], session_data['start_time'])
    current_total = get_total_hours(current_day, current_time)
    
    if session_total < current_total:
        flash("You cannot join a quest session that has already passed.", "danger")
        return redirect(url_for('session_detail', session_id=session_id))

    party_role = request.form.get('party_role')
    places = int(request.form.get('places_reserved', 1))

    # checking that input for number of reserves is limited between 1 and 2
    if places < 1 or places > 2:
        flash("You can reserve at most 2 places per quest session.", "danger")
        return redirect(url_for('session_detail', session_id=session_id))

    # Once all places for a role category are taken, it is no longer possible to join with that role[cite: 1].
    if availability.get(party_role, 0) < places:
        flash(f"Not enough places available for the {party_role} role.", "danger")
        return redirect(url_for('session_detail', session_id=session_id))

    schedule = db.get_adventurer_schedule(current_user.UId)
    
    # Each adventurer can reserve at most 2 places per session and join at most 3 sessions (total places) per week[cite: 1].
    total_places_booked = sum(task['places_reserved'] for task in schedule)
    
    if total_places_booked + places > 3:
        flash(f"Weekly limit reached! You can only reserve {3 - total_places_booked} more place(s) this week.", "danger")
        return redirect(url_for('session_detail', session_id=session_id))

    # Verify time constraints[cite: 1].
    if has_time_overlap(session_data, schedule):
        flash("This session overlaps in time with another quest you have joined.", "danger")
        return redirect(url_for('session_detail', session_id=session_id))

    # If all checks pass, record the participation
    db.join_session(session_id, current_user.UId, party_role, places)
    flash(f"Successfully joined the quest as {party_role} (Places: {places})!", "success")
    return redirect(url_for('index'))


def get_total_hours(day_str, time_str):
    """
    Converts a string representation of a day and time into absolute hours since Monday 00:00.
    This enables easy arithmetic for determining past/future constraints in the simulated week[cite: 1].
    """
    days = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
        "Friday": 4, "Saturday": 5, "Sunday": 6
    }
    hours, minutes = map(int, time_str.split(':'))
    return (days[day_str] * 24) + hours + (minutes / 60.0)

def can_modify_session(session_day, session_time, current_day, current_time):
    """
    Quest participations can be modified only if the related quest session starts 
    more than 8 hours after the simulated current day and time[cite: 1].
    """
    session_total = get_total_hours(session_day, session_time)
    current_total = get_total_hours(current_day, current_time)
    
    # Returns True if the gap between now and the session start is greater than 8 hours.
    return (session_total - current_total) > 8


# --- Profile Modification Helpers ---

def handle_username_update(form_data, user_id):
    """Processes an update to the user's username identifier."""
    new_username = form_data.get('username')
    success = db.update_user_profile(user_id=user_id, new_username=new_username)
    
    if success:
        flash('Username updated successfully!', 'success')
    else:
        flash('That username is already taken! Please choose another.', 'danger')

def handle_password_update(form_data, user_id):
    """Verifies and processes a password change request."""
    new_password = form_data.get('password')
    confirm_password = form_data.get('confirm_password')
    
    if new_password != confirm_password:
        flash('New passwords do not match. Please try again.', 'danger')
        return
        
    success = db.update_user_profile(user_id=user_id, new_password=new_password)
    
    if success:
        flash('Password updated successfully!', 'success')
    else:
        flash('An error occurred while updating your password.', 'danger')

def handle_avatar_update(files_data, current_user, app_config):
    """Processes an avatar upload, secures the filename, saves it, and deletes the old file to conserve space."""
    if 'avatar' not in files_data:
        flash('No file uploaded.', 'danger')
        return
        
    file = files_data['avatar']
    
    if not (file and file.filename != '' and allowed_file(file.filename)):
        flash('Invalid file type or no file selected.', 'danger')
        return

    # 1. Save new file securely
    original_filename = secure_filename(file.filename)
    avatar_filename = f"user_{current_user.UId}_{original_filename}"
    save_path = os.path.join(app_config['UPLOAD_FOLDER'], avatar_filename)
    file.save(save_path)
    
    # 2. Delete the user's old avatar if it exists
    if current_user.avatar_filename:
        old_avatar_path = os.path.join(app_config['UPLOAD_FOLDER'], current_user.avatar_filename)
        if os.path.exists(old_avatar_path):
            try:
                os.remove(old_avatar_path)
            except OSError as e:
                print(f"Warning: Failed to delete old avatar {old_avatar_path}: {e}")
                
    # 3. Update the database record with the new filename
    success = db.update_user_profile(user_id=current_user.UId, new_avatar=avatar_filename)
    
    if success:
        flash('Profile picture updated successfully!', 'success')
    else:
        flash('An error occurred while saving your avatar.', 'danger')