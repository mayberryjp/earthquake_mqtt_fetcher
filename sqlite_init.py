import sqlite3

# Connect to the database
conn = sqlite3.connect('earthquake.db')
c = conn.cursor()

# Create a table
c.execute('''CREATE TABLE IF NOT EXISTS earthquakes
             (eid text PRIMARY KEY, arrival_timestamp text, atom_timestamp text, json_timestamp text)''')