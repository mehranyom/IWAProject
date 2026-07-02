import sqlite3


"""
this function will connect the database and return conn.
so in the other functions, i will only call this function to get conn
instead of writing connection code everytime.
"""
def get_db_connection():
    
    # Connect to the local SQLite database file
    conn = sqlite3.connect('database.db')

    # Configure the connection to return dictionary-like rows instead of standard tuples 
    conn.row_factory = sqlite3.Row
    return conn


