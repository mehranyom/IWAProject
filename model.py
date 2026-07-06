from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, role):
        self.UId = id
        self.username = username
        self.role = role