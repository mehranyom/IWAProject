from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, role):
        self.UId = id
        self.username = username
        self.role = role
    
    def get_id(self):
        # Flask-Login requires this to be returned as a string!
        return str(self.UId)