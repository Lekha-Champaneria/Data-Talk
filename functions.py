from dotenv import load_dotenv
from openai import AzureOpenAI
import pyodbc
import os
import json
load_dotenv()
class AllFunctions:
        
    def _make_open_ai_client():
        # Open AI Client code yaha pe aaega
        openai_client = AzureOpenAI(
            api_version="2025-01-01-preview",
            azure_endpoint="https://<your-azure-endpoint>.openai.azure.com/openai/deployments/<your-deployment-name>/chat/completions?api-version=2025-01-01-preview",
            api_key="<your-api-key>",
            azure_deployment="<your-deployment-name>"
        )
        # res = openai_client.chat.completions.create(
        #     model="gpt-4o",
        #     messages=[
        #         {"role": "system", "content": "You are a helpful assistant."},
        #         {"role": "user", "content": "Hello! How can I assist you today?"}
        #     ]
        # )
        # print(res.choices[0].message.content)
        return openai_client

    def _make_pyodbc_client():
        # Step 2: Set up the connection to Azure SQL Database
        server = os.getenv("ROCKET_SQL_SERVER")  # replace with your server
        database = os.getenv("ROCKET_SQL_DATABASE")  # replace with your database
        username = os.getenv("ROCKET_SQL_USERNAME")  # replace with your username
        password = os.getenv("ROCKET_SQL_PASSWORD")  # replace with your password
        driver = "{ODBC Driver 18 for SQL Server}"  # ODBC driver for SQL Server
        # Establish connection
        conn = pyodbc.connect(f'DRIVER={driver};'
                            f'SERVER={server};'
                            f'DATABASE={database};'
                            f'UID={username};'
                            f'PWD={password}')
        cursor = conn.cursor()
        return cursor,conn
    
    def get_table_data(tables):
        server = os.getenv("ROCKET_SQL_SERVER")
        database = os.getenv("ROCKET_SQL_DATABASE")
        password = os.getenv("ROCKET_SQL_PASSWORD")
        username = os.getenv("ROCKET_SQL_USERNAME")
        connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{server},1433;Database={database};Uid={username};Pwd={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

        table_data = {"content":"tables"}
        
        # Establish connection using pyodbc
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
    
        try:
            

            # List of table names to retrieve data from
            # tables = 
            print("inside try ", "*"*100)
            for table in tables:
                
                # Fetch column names
                cursor.execute(f"SELECT * FROM {table} WHERE 1=0")  # Get column names without fetching any data
                columns = [column[0] for column in cursor.description]

                # Fetch the first two rows of the table
                cursor.execute(f"SELECT TOP 2 * FROM {table}")
                rows = cursor.fetchall()

                # Store the columns and first two rows in the dictionary
                table_data[table] = {
                    "columns": columns,
                    "first_two_rows": rows
                }

            print("after loop", "*"*100)
            return table_data

        except Exception as e:
            print(f"Error occurred: {e}")
            return {"error":"Data Not Available, just chat with user"}
        
        finally:
            cursor.close()
            conn.close()
    
    def format_table_data_for_prompt(table_data):
        print(table_data, "82")
        try:
            tables_list = []
            formatted_data = ""
            for table, data in table_data.items():
                print(table, " : ", data)
                print(data["columns"])
                tables_list.append(table)
                formatted_data += f"Table: {table}\nColumns: {', '.join(data['columns'])}\nFirst Two Rows:\n"
                for row in data['first_two_rows']:
                    formatted_data += f"{', '.join(map(str, row))}\n"
                formatted_data += "\n"
                print("\n\n\n\n",formatted_data,"\n\n\n\n")
            return formatted_data
        except:
            return formatted_data if formatted_data else "Data Not available currently, chat with the user meanwhile"

    def _get_data(cursor):
        # server = os.getenv("ROCKET_SQL_SERVER")  # replace with your server
        # database = os.getenv("ROCKET_SQL_DATABASE")  # replace with your database
        # password = os.getenv("ROCKET_SQL_PASSWORD")  # replace with your password
        # connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{server},1433;Database={database};Uid=amit;Pwd={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

        table_data = {}
        try:
            # Establish connection using pyodbc
            # conn = pyodbc.connect(connection_string)
            # cursor = conn.cursor()

            # List of table names to retrieve data from
            tables = ["Employees"]

            for table in tables:
                # Fetch column names
                cursor.execute(f"SELECT * FROM {table} WHERE 1=0")  # Get column names without fetching any data
                columns = [column[0] for column in cursor.description]

                # Fetch the first two rows of the table
                cursor.execute(f"SELECT TOP 2 * FROM {table}")
                rows = cursor.fetchall()

                # Store the columns and first two rows in the dictionary
                table_data[table] = {
                    "columns": columns,
                    "first_two_rows": rows
                }

            return table_data
        except Exception as e:
            print(f"Error occurred: {e}")
            return None  

    def _format_table_data_for_prompt(table_data):
        tables_list = []
        formatted_data = ""
        for table, data in table_data.items():
            tables_list.append(table)
            formatted_data += f"Table: {table}\nColumns: {', '.join(data['columns'])}\nFirst Two Rows:\n"
            for row in data['first_two_rows']:
                formatted_data += f"{', '.join(map(str, row))}\n"
            formatted_data += "\n"
        return tables_list, formatted_data

    def _call_open_ai_with_prompt(prompt, UserInput, openai_client):
        res = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": UserInput}
            ]
        )

        tab = res.choices[0].message.content.strip("```")
        response = tab.replace("json", "")
        response = response.replace("\n","")
        response = dict(json.loads(response))

        return response

    def _execute_query(cursor, sql_query):
        try:
            # Execute the query
            cursor.execute(sql_query)
            
            # Fetch column names
            columns = [column[0] for column in cursor.description]
            print(columns)
            
            # Fetch all rows
            rows = cursor.fetchall()
            
            # Format the results into a list of dictionaries
            results = [dict(zip(columns, row)) for row in rows]
            
            return {"status": "success", "data": results}
        except Exception as e:
            # Return error details
            return {"status": "error", "message": str(e)}
