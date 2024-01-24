import sqlite3
import json
import statistics

def stats():

        DATABASE="earthquake.db"

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

        data={
                "atom_average_delay": atom_average_delay,
                "json_average_delay": json_average_delay,
                "win_percent": win_percent,
                "min_atom": min_atom,
                "min_json": min_json,
                }

        return data

if __name__ == "__main__":
    data = stats()
    data_string = json.dumps(data)
    print(data_string)