

# Introduction to Web Applications - Exam Project

**Fantasy Adventure Guild Management System**

## 🌐 Live Deployment

The web application is successfully deployed and accessible at the following URL:
**[https://mehranyom.pythonanywhere.com/](https://mehranyom.pythonanywhere.com/)**

## ⏱️ Simulated Environment

To facilitate the testing of time-based constraints (such as the 8-hour modification rule), the application operates on a simulated current day and time within a fictional week:

* **Current Simulated Day:** Monday
* **Current Simulated Time:** 11:00

## 🔐 User Credentials

The database has been pre-populated with the required sample data, including 1 Guild Master and 6 Adventurers.

**Global Password for all accounts:** `123698745Kc`

| Role | Username | Password |
| --- | --- | --- |
| **Guild Master** | `juan` | `123698745Kc` |
| **Adventurer** | `pablo` | `123698745Kc` |
| **Adventurer** | `stefano_gm` | `123698745Kc` |
| **Adventurer** | `vincent_v` | `123698745Kc` |
| **Adventurer** | `mia_wallace` | `123698745Kc` |
| **Adventurer** | `icarus` | `123698745Kc` |
| **Adventurer** | `satoshi` | `123698745Kc` |

---

## 🧪 Testing Instructions

The application has been loaded with sample data (quests, sessions, and participations) to test all primary constraints. Follow the instructions below to verify the core functional requirements.

### 1. Testing the 8-Hour Modification Rule (Adventurer)

Because the simulated time is set to **Monday 11:00**, the 8-hour threshold for modifying or cancelling a quest participation is **Monday 19:00**.

* **Log in as an Adventurer** (e.g., `mia_wallace` or `vincent_v`) and navigate to the **Profile** page.
* **Non-Modifiable:** Any joined session starting *before* Monday 19:00 (or on a previous day conceptually) will be locked. The UI will prevent modifications or cancellations.
* **Modifiable:** Any joined session starting *after* Monday 19:00 will display options to update the selected role/places or cancel the booking entirely.

### 2. Testing Adventurer Booking Constraints

While logged in as an Adventurer, navigate to the homepage or a specific quest session to test the validation rules:

* **Capacity Limit:** Attempt to book more than **2 places** for a single session to trigger the backend validation error.
* **Weekly Limit:** Attempt to join sessions such that your total reserved places exceed **3 places** for the week.
* **Time Overlap:** Attempt to join a new session that occurs at the exact same day and time as a session you are already participating in.
* **Role Capacity:** Locate the session where a specific role (e.g., Healer) is already fully booked. The system will prevent you from reserving that role.

### 3. Testing Guild Master Functionality

* **Log in as the Guild Master** (`juan`) and navigate to the **GM Dashboard**.
* **Edit/Cancel Sessions:** Locate a scheduled session that currently has **0 participants**. You will be able to freely modify its day, time, or location, or cancel it entirely.
* **Locked Sessions:** Locate a session that already has active adventurer participations. The system will block any attempts to modify or cancel it.
* **Overlap Prevention:** Attempt to schedule a new session (or modify an empty one) to a time and location that is already occupied by another session. The overlap detection will block the action.
* **Create Quests:** Use the dedicated form to create a new quest (including an image upload) and schedule a new session for it.