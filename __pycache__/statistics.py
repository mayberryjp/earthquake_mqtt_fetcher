import sqlite3


DATABASE="C:\\users\\rimayber\\Downloads\\earthquake.db"

connection = sqlite3.connect(DATABASE)
cursor = connection.cursor()

query = """
    SELECT AVG(strftime('%s', arrival_timestamp) - strftime('%s', atom_timestamp)) AS average_time_difference_seconds
    FROM earthquakes;
"""
cursor.execute(query)

# Fetch the result
result = cursor.fetchone()


# Access the average time difference in seconds
atom_average_delay = result[0]


query = """
    SELECT AVG(strftime('%s', arrival_timestamp) - strftime('%s', json_timestamp)) AS average_time_difference_seconds
    FROM earthquakes;
"""
cursor.execute(query)

# Fetch the result
result = cursor.fetchone()


# Access the average time difference in seconds
json_average_delay = result[0]


query = """
    SELECT AVG(strftime('%s', atom_timestamp) - strftime('%s', json_timestamp)) AS average_time_difference_seconds
    FROM earthquakes;
"""
cursor.execute(query)

# Fetch the result
result = cursor.fetchone()

# Access the average time difference in seconds
atom_to_json_delay_comparison = result[0]

query = """
    SELECT AVG(strftime('%s', atom_timestamp) - strftime('%s', json_timestamp)) AS average_time_difference_seconds
    FROM earthquakes;
"""
cursor.execute(query)

# Fetch the result
result = cursor.fetchone()

# Access the average time difference in seconds
atom_to_json_delay_comparison = result[0]


query = """
    SELECT COUNT(*)
    FROM earthquakes
    WHERE atom_timestamp < json_timestamp;
"""
cursor.execute(query)

# Fetch the result
result = cursor.fetchone()

atom_wins=result[0]


query = """
    SELECT COUNT(*)
    FROM earthquakes;
"""
cursor.execute(query)

# Fetch the result
result = cursor.fetchone()

total_rows=result[0]



win_percent = (atom_wins / total_rows) * 100


query = """
    SELECT MAX(strftime('%s', arrival_timestamp) - strftime('%s', json_timestamp)) AS min_time_difference_seconds
    FROM earthquakes;
"""
cursor.execute(query)

# Fetch the result
result = cursor.fetchone()

min_json=result[0]


query = """
    SELECT MAX(strftime('%s', arrival_timestamp) - strftime('%s', atom_timestamp)) AS min_time_difference_seconds
    FROM earthquakes;
"""
cursor.execute(query)

# Fetch the result
result = cursor.fetchone()

min_atom=result[0]


query = """
    SELECT MIN(strftime('%s', arrival_timestamp) - strftime('%s', json_timestamp)) AS min_time_difference_seconds
    FROM earthquakes;
"""
cursor.execute(query)

# Fetch the result
result = cursor.fetchone()

max_json=result[0]


query = """
    SELECT MIN(strftime('%s', arrival_timestamp) - strftime('%s', atom_timestamp)) AS min_time_difference_seconds
    FROM earthquakes;
"""
cursor.execute(query)

# Fetch the result
result = cursor.fetchone()

max_atom=result[0]

# Close the cursor and connection
cursor.close()
connection.close()

print(f"Average Time Difference in Seconds (ATOM): {atom_average_delay}")
print(f"Average Time Difference in Seconds (JSON): {json_average_delay}")
print(f"Average Time Difference in Seconds (ATOM VS JSON): {atom_to_json_delay_comparison}")
print(f"Atom Win Rate: {atom_wins} / {total_rows} or {win_percent}")
print(f"Min Time Difference in Seconds (ATOM): {min_atom}")
print(f"Min Time Difference in Seconds (JSON): {min_json}")
print(f"Max Time Difference in Seconds (ATOM): {max_atom}")
print(f"Max Time Difference in Seconds (JSON): {max_json}")