from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, role, avatar_filename):
        self.UId = id
        self.username = username
        self.role = role
        self.avatar_filename = avatar_filename
    def get_id(self):
        # Flask-Login requires this to be returned as a string!
        return str(self.UId)