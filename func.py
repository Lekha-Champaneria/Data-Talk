import pyodbc
import pandas as pd
import os

class AllFunctions:

    def _make_pyodbc_client():
        """Establish a connection to the database and return the cursor and connection."""
        try:
            server = os.getenv("ROCKET_SQL_SERVER")  # replace with your server
            database = os.getenv("ROCKET_SQL_DATABASE")  # replace with your database
            username = os.getenv("ROCKET_SQL_USERNAME")  # replace with your username
            password = "R!thod123"  # replace with your password
            driver = "{ODBC Driver 18 for SQL Server}"  # ODBC driver for SQL Server
            # Establish connection
            conn = pyodbc.connect(f'DRIVER={driver};'
                                f'SERVER={server};'
                                f'DATABASE={database};'
                                f'UID={username};'
                                f'PWD={password}')
            cursor = conn.cursor()
            return cursor,conn
            # # server = 'govt-chat-history.database.windows.net'
            # # database = 'grieviance'
            # # password = 'test'
            # # username = '6unamat@'
            # # connection_string = f"Driver={{ODBC Driver 17 for SQL Server}};Server=tcp:{server},1433;Database={database};Uid={username};Pwd={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
            # connection_string="Driver={ODBC Driver 17 for SQL Server};Server=tcp:govt-chat-history.database.windows.net,1433;Database=grieviance;Uid=test;Pwd=6unamat@;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
            # # connection_string="Driver={ODBC Driver 17 for SQL Server};Server=tcp:whatsappbot.database.windows.net,1433;Database=ClothingStore;Uid=BHAVY;Pwd=ADMIN_admin;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

            # conn = pyodbc.connect(connection_string)
            # cursor = conn.cursor()
            # return cursor, conn
        
        except Exception as e:
            print(f"Error connecting to the database: {e}")
            raise


    def create_grievance_table(cursor, conn):
        """Create the grievance table if it doesn't already exist."""
        # cursor, conn = AllFunctions._make_pyodbc_client()

        create_table_query = '''
        IF NOT EXISTS (
            SELECT * FROM sysobjects WHERE name='grievance' AND xtype='U'
        )
        CREATE TABLE grievance (
            id INT IDENTITY(1,1) PRIMARY KEY,
            query NVARCHAR(MAX),
            user NVARCHAR(255),
            department NVARCHAR(255)
        )
        '''

        try:
            cursor.execute(create_table_query)
            conn.commit()
            print("Grievance table created successfully.")
        except Exception as e:
            print(f"Failed to create grievance table: {e}")
        finally:
            conn.close()

    @staticmethod
    def execute_query(query, user, department):
        """Insert a query into the grievance table."""
        cursor, conn = AllFunctions._make_pyodbc_client()

        insert_query = "INSERT INTO grievance (query, user, department) VALUES (?, ?, ?)"

        try:
            cursor.execute(insert_query, query, user, department)
            conn.commit()
            print("Query inserted into the grievance table successfully.")
        except Exception as e:
            print(f"Failed to insert query: {e}")
        finally:
            conn.close()

    @staticmethod
    def dump_data_to_sql(data, table_name):
        """Dump a DataFrame into a SQL table."""
        cursor, conn = AllFunctions._make_pyodbc_client()

        columns = ', '.join(f"[{col}] NVARCHAR(MAX)" for col in data.columns)
        create_table_query = f"CREATE TABLE {table_name} ({columns})"

        try:
            cursor.execute(create_table_query)
            conn.commit()
            print(f"Table '{table_name}' created successfully.")
        except Exception as e:
            print(f"Table creation failed: {e}")

        for _, row in data.iterrows():
            placeholders = ', '.join(['?'] * len(row))
            insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"

            try:
                cursor.execute(insert_query, *row)
            except Exception as e:
                print(f"Failed to insert row: {e}")

        conn.commit()
        conn.close()
        print(f"Data inserted into '{table_name}'.")


