# save this as app.py
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from openai import AzureOpenAI
import os
import json
from flask_cors import CORS
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.tools import Tool
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import PromptTemplate
import time
import numpy as np
from concurrent.futures import TimeoutError
from functions import AllFunctions
from azure.cosmos import CosmosClient
import uuid
from sklearn.metrics.pairwise import cosine_similarity
import os, uuid
from azure.storage.blob import BlobServiceClient
import pandas as pd
import os
import io
from io import BytesIO
import time
import azure.cognitiveservices.speech as speechsdk
from azure.storage.blob import BlobServiceClient
import matplotlib.pyplot as plt

# Load environment variables
load_dotenv()
# chat_history = []

# Initialize Azure OpenAI
llm = AzureChatOpenAI(
    # model="gpt-4o",
    deployment_name="gpt-4o",
    azure_endpoint="ADD_YOUR_AZURE_OPENAI_ENDPOINT_HERE",
    temperature=0,
    api_version="2025-01-01-preview",
    api_key="ADD_YOUR_AZURE_OPENAI_API_KEY_HERE"
)

is_file = False

# Initialize Cosmos DB
client = CosmosClient(
    os.getenv("AZURE_COSMOS_ENDPOINT"), 
    os.getenv("AZURE_CLIENT_SECRET")
)
database = client.get_database_client("Rocket Science")
container = database.get_container_client("ChatHistory")
container_chatlist = database.get_container_client("ChatList")

# Initialize OpenAI client
openai_client = AllFunctions._make_open_ai_client()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

def get_embedding(text, model="text-embedding-ada-002"):
    
    openai_client_embed = AzureOpenAI(
            api_version="2023-05-15",
            azure_endpoint="ADD_YOUR_AZURE_OPENAI_EMBEDDING_ENDPOINT_HERE",
            api_key="ADD_YOUR_AZURE_OPENAI_EMBEDDING_API_KEY_HERE",
            azure_deployment="text-embedding-ada-002"
        )
    return openai_client_embed.embeddings.create(input = [text], model=model).data[0].embedding


def generate_dynamic_name(file_name):
    # Remove the extension and replace invalid characters (if any)
    base_name = os.path.splitext(file_name)[0]
    table_name = base_name.replace('-', '_').replace('.', '_')  # Ensure it's SQL-safe
    return table_name

def generate_sql_query(user_query):
   
    # Create the SQL query prompt
    sql_query_prompt = '''
        You are an SQL database master whose sole responsibility is to generate SQL queries accurately and efficiently. The queries you create will be directly executed on the database, so accuracy is crucial. Follow these guidelines:
        Understand the Task: Carefully read the user's requirements for the SQL query.
        Output Accurate SQL: Generate only the SQL query that meets the requirements. Do not include any explanations or additional text.
        Use Proper Syntax: Follow SQL best practices and ensure the syntax is valid.
        Remove Unwanted Content: If the input contains an SQL query, remove any unwanted or unnecessary text and return only the cleaned SQL query as a string format, which can be directly executed.
        Match the Example: Use the style and structure demonstrated in the example below as a reference:
        Bad SQL Query Example:
        sqlCopyEditSELECT Department.DepartmentName, COUNT(Employee.EmployeeID) AS TotalEmployees FROM Employee JOIN Department ON Employee.DepartmentID = Department.DepartmentID GROUP BY Department.DepartmentName"
 
        Good SQL Query Example:
        sqlCopyEditSELECT Department.DepartmentName, COUNT(Employee.EmployeeID) AS TotalEmployees FROM Employee JOIN Department ON Employee.DepartmentID = Department.DepartmentID GROUP BY Department.DepartmentName;
       
       
        When you are ready, generate or clean the SQL query provided and return it in string format for direct execution.
 
    '''
   
    # Send the query to the model
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": sql_query_prompt},
            {"role": "user", "content": user_query}
        ]
    )
   
    # Extract and return the generated SQL query
    sql_query = response.choices[0].message.content.strip()
    return sql_query

def fetch_data_using_query_from_database(query:str):
    print("Inside Query:", query)

    cleaned_query = generate_sql_query(query)
    cleaned_query = cleaned_query.replace("```sql", "").replace("```", "").strip()

    print("Cleaned Query:", cleaned_query)
    
    cursor, conn = AllFunctions._make_pyodbc_client()
    
    try:
        cursor.execute(cleaned_query)
        rows = cursor.fetchall()
        return str(rows)+" YOUR TASK IS DONE! stop!"
    except Exception as e:
        print("174 ",e)
    finally:
        cursor.close()
        conn.close()
        print("Database operation completed")

def graph_function(plot_code):
    """
    Executes matplotlib plot code, saves the plot as an image, and uploads it to Azure Blob Storage.
    
    Args:
        plot_code (str): String containing matplotlib plotting code
    
    Returns:
        str: URL of the uploaded plot in Azure Blob Storage
    """
    try:
        # Create a new figure to ensure clean state
        plt.figure()
        
        # Execute the plotting code
        exec(plot_code)
        # Save plot to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        # Close the plot to free memory
        plt.close()
        
        # Upload to Azure Blob Storage
        blob_service_client = BlobServiceClient.from_connection_string("ADD_YOUR_AZURE_STORAGE_CONNECTION_STRING_HERE")
        container_client = blob_service_client.get_container_client("graphs")
        blob_name = str(uuid.uuid1())+".png"  # Convert UUID to string
        # Upload the image
        container_client.upload_blob(name=blob_name, data=buf.getvalue(), overwrite=True)
        
        # Get the blob URL
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_client.container_name}/{blob_name}"
        
        return blob_url
        
    except Exception as e:
        plt.close()  # Ensure plot is closed even if there's an error
        raise Exception(f"Error processing plot: {str(e)}")
    

graph_tool = Tool(
    name="generate_graph_tool",
    func=graph_function,
    description="Useful to generate a graph and retrive the link of the graph to user. Use only when data seems to be presentable in a graph."
)

# Define tools
tools = [
    Tool(
        name="fetch_data_using_query_from_database",
        func=fetch_data_using_query_from_database,
        description="Useful for when you want to fetch data using proper sql query",
    ),
    Tool(
        name="generate_graph_tool",
        func=graph_function,
        description="Useful to generate a graph and retrive the link of the graph to user. Use only when data seems to be presentable in a graph."
    )
]

tool_names = ["fetch_data_using_query_from_database"]

# Updated prompt template
# prompt_template = """
#     #Role:
#         You are an expert Database engineer. Your task is to serve user data. You have access to these tools: {tools}
    
#     #Description:
#         1. Get User input, and understand.
#         2. Check relevancy.
#         3. Check user intent.
#         4. Choose the appropriate response format based on whether tools are needed.

#     # Response Format:
    
#     IF TOOLS ARE NEEDED, use this format:
#     ```
#         Question: the input question you must answer
#         Thought: you should always think about what to do
#         Action: the action to take, should be one of [{tool_names}]
#         Action Input: the input to the action
#         Observation: the result of the action
#         Thought: I now know the final answer
#         Final Answer: the final answer to the original input question
#     ```

#     IF NO TOOLS ARE NEEDED, use this format:
#     ```
#         Question: the input question you must answer
#         Thought: I should respond directly since no tools are needed
#         Final Answer: the final answer to the original input question
#     ```

#     # Response Schema (for all responses):
#     {{
#         relevant_table_names: array,
#         user_input: string,
#         sql_query: string (if error is empty),
#         user_intention: string (strictly summarized in one line),
#         relevance: boolean,
#         error_message: string (if applicable),
#         response_message: string (if user_intention is not to fetch data),
#         data: String (SQL Response if applicable)
#     }}
    
#     # Notes:
#         - If the user input is irrelevant or no tools are needed, respond directly without attempting to use tools
#         - Keep responses user friendly and concise
#         - Strictly follow the Response Schema
#         - Only use tools when absolutely necessary for database operations
#         - For database queries, always limit results to 50 rows using 'TOP 50'
#         - Available tables: Assets, Employee, Certifications, Meeting_Rooms, Department, Asset_Allocation, Salary

#     Begin!

#     Question: {input}
#     Thought:{agent_scratchpad}
# """



@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    time.sleep(1)
    user_message = request.json.get('message', '')
    response = f"I received: {user_message}"
    return jsonify({
        'response': response,
        'timestamp': time.strftime('%H:%M')
    })

@app.route('/feedback', methods=['POST'])
def feedback():
    try:
        feedback_data = request.json
        message = feedback_data.get('message')
        feedback_value = feedback_data.get('feedback')
        
        print(f"Feedback received - Message: {message}, Value: {feedback_value}")
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback recorded successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    

def get_chatlist(query, parameters):
    results = container_chatlist.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True  # Enable cross-partition queries if needed
    )

    return results

def create_chat(chat_id_frontend, user_query):

    chat_id = str(uuid.uuid1())
    container_chatlist.upsert_item({
        'id': chat_id,
        "chatId": chat_id_frontend,
        "content": user_query[:10]
        # 'timestamp': datetime.datetime.now(datetime.UTC)
    })

# Function to query history
def find_match(query_embedding, chat_id, threshold=0.98):
    # print(307)
    # Step 2: Fetch data from Cosmos DB
    query = "SELECT c.id, c.You, c.AI, c.embedding FROM c WHERE c.chatId = @chat_id"
    parameters = [{"name": "@chat_id", "value": chat_id}]
    items = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    # Step 3: Compute similarity scores
    results = []
    for item in items:
        stored_embedding = np.array(item["embedding"])  # Convert stored embedding to NumPy array

        # Reshape the embeddings to 2D
        query_embedding_reshaped = query_embedding.reshape(1, -1)  # Shape becomes (1, 1536)
        stored_embedding_reshaped = stored_embedding.reshape(1, -1)  # Shape becomes (1, 1536)

        # Compute cosine similarity
        similarity = cosine_similarity(query_embedding_reshaped, stored_embedding_reshaped)[0][0]  # Extract scalar similarity

        # Check if similarity exceeds the threshold
        if similarity > threshold:
            results.append({
                "id": item["id"],
                "You": item["You"],
                "AI": item.get("AI", ""),
                "similarity": similarity
            })
            
    # Step 4: Sort results by similarity
    results = sorted(results, key=lambda x: x["similarity"], reverse=True)
    # print(results)
    return results

@app.route("/getresponse", methods=["POST"])
def getresponse():
    # print("test","/"*100)
    table_data = AllFunctions.get_table_data(["Employees"])
    # print("test2","/"*100)
    try:
        # print("345")
        data = request.get_json()
        user_message = data.get('message')
        current_chat_id = data.get('currentChatId')

        is_file = False
        # create_chat(current_chat_id, user_message)

        query = "SELECT * FROM c WHERE c.chatId = @value order by c._ts"
        parameters = [{"name": "@value", "value": current_chat_id}]
        chat_items  = list(get_chatlist(query, parameters))
        # print(chat_items)

        chat_history = []
        if chat_items:  # Check if the list is non-empty
            # print("Chat exists:", chat_items)
            res = container.query_items(
                    query="SELECT c.AI, c.You as user FROM c WHERE c.chatId = @value order by c._ts",
                    parameters=[{"name": "@value", "value": current_chat_id}],
                    enable_cross_partition_query=True
            )
            if res:
                for chat in res:
                    chat_history.append(chat)
                # print(chat_history)
            if 'file' in chat_items[0]:
                is_file = True
                # print(is_file)
                table_data = AllFunctions.get_table_data([str(chat_items[0]['table'])])
            else:
                # print("else, 364")
                pass
        else:
            print("Chat Not Exist : ", chat_items)
            create_chat(current_chat_id, user_message)
            # print("chat created")

        if not user_message:
            return jsonify({"error": "User query is required"}), 400
        # print("375")
        embedding = get_embedding(
            user_message,
            model="text-embedding-ada-002" # model should be set to the deployment name you chose when you deployed the text-embedding-ada-002 (Version 2) model
        )
        
        item  =  find_match(np.array(embedding), current_chat_id)
        # print("380")
        if item:
            # print("Match Found : ", item)
            # chat_history.append(f"AI: {item[0]['AI']}")
            # print("384")
            container.upsert_item({
                    'id': str(uuid.uuid4()),
                    'chatId': current_chat_id,
                    'AI': item[0]['AI'],
                    'You': user_message,
                    'feedback': None,
                    'embedding': embedding
                })
            
            # print(" after upsert 394")
            return jsonify({
                'response': item[0]['AI'],
                'timestamp': time.strftime('%H:%M')
            })
        else:
            pass
            # print("401")
    except Exception as e:
        print("error ",e)

    # print("406")
    try:
        # chat_history.append(f"You: {user_message}")
        # history_input = "\n".join(chat_history) + "\nYou: " + user_message
        # formatted_data = AllFunctions.format_table_data_for_prompt(table_data)
        # print(formatted_data)
        if chat_history == []:
            message_for_chat_history = "No chat history available"
        else:
            message_for_chat_history = f"""
                refer to this chat history for your reference: ``` {chat_history[-10:] if len(chat_history)>10 else chat_history} REFER THIS, IF YOU THINK YOU CAN ANSWER USING THIS DATA, NO NEED TO USE ANY TOOLS.```
            """

        print(message_for_chat_history)
        prompt_template = """
            #Role:
                You are an expert Database engineer who can also handle basic conversations. You have access to these tools: {tools}
            
            #Description:
                1. First, determine if the input is:
                - A conversational message (greeting, personal info, chitchat), to answer the user query try to refer chat history for getting the context, if available.
                - A database-related query
                2. For conversational messages:
                - Respond naturally without using tools
                - Use the direct response format
                3. For database queries:
                - Check relevancy and user intent, only allow data retrieval, Strictly don't allow anyone to deletion updation.
                - Use tools if needed
                4. If the user wants to display the number of rows for the ouput do the following:
                - If the number of rows are equal or less than 100 display it in the response.
                - But if that number of rows are more than 100 at that time strictly display only the first 50 rows of the table.  
                - The Azure SQL does not take the word "Limit" for making the sql query, so instead of "limit" use any other keyword.
                    - Continue the chain of 50 rows only when the user commands to go continue. 
            ---
            #Sample Data for your reference:
            ```
                {table_data}
            ```
        
            # Notes:
            - chat history is just for your reference, only to provide you 
            - You must refer to formatted data for generating sql query
            - While generating sql queries make sure that it should follow this format:

                
            # Response Format:
            
            FOR CONVERSATIONAL MESSAGES, use this format:
            ```
                Question: the input message
                Thought: This is a conversational message, no tools needed
                Final Answer: string ["your friendly response if intention is to 'chat' else the summary of the fetched data."]
            ```
        
            FOR DATABASE QUERIES that need tools:
            ```
                Question: the database query
                Thought: you should always think about what to do
                Action: the action to take, should be one of [{tool_names}]
                Action Input: the input to the action
                Observation: the result of the action
                Thought: I now know the final answer
                Final Answer: string ["agent response"]
            ```
            ###
            Chat history:  {message_for_chat_history}
            ###
            Begin!
        
            Question: {input}
            Thought:{agent_scratchpad}
        """
        # prompt = PromptTemplate.from_template(prompt_template)
        
        # Create the PromptTemplate instance and let it derive `input_variables`
        prompt = PromptTemplate.from_template(
            prompt_template,
            partial_variables={
                'table_data':table_data,
                "message_for_chat_history":message_for_chat_history
            }
        )


        # Create ReAct agent and inject variables
        variables = {
            "formatted_data": table_data,  # Only inject the formatted data
        }


        # Create ReAct agent
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=prompt.partial(**variables),  # Inject variables directly
            stop_sequence=True,
        )

        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )

        history_input = user_message
        
        # Add timeout to prevent infinite loops
        start_time = time.time()
        MAX_EXECUTION_TIME = 30  # 30 seconds timeout
        
        def invoke_with_timeout():
            if time.time() - start_time > MAX_EXECUTION_TIME:
                raise TimeoutError("Agent execution timed out")
            return agent_executor.invoke({"input": history_input})
        
        try:
            
            responses = invoke_with_timeout()
            ai_response : str = responses['output']
            ai_response = ai_response.replace("```", "").strip()
            print("ai_response : ", type(ai_response), ai_response)

            try:
                # Attempt to parse the string as JSON
                parsed_response = json.loads(ai_response)
                ai_response = parsed_response.get("response_message")
                
            except json.JSONDecodeError:
                # Handle the case where it's a normal string
                print("ai_response is not a valid JSON string.")

            # chat_history.append(f"AI: {ai_response}")
    
            # Update Cosmos DB with AI response
            container.upsert_item({
                'id': str(uuid.uuid4()),
                'chatId': current_chat_id,
                'AI': ai_response,
                'You': user_message,
                'feedback': None,
                'embedding': embedding
            })
            
            
            return jsonify({
                'response': ai_response,
                'timestamp': time.strftime('%H:%M')
            })
            
            
        except TimeoutError:
            error_message = "The request timed out. Please try a different query or rephrase your question."
            print(error_message)
            # chat_history.append(f"AI: {error_message}")
            return jsonify({
                'response': error_message,
                'timestamp': time.strftime('%H:%M')
            }), 408
            
    except Exception as e:
        print(e)
        error_message = f"An error occurred: {str(e)}"
        # chat_history.append(f"AI: {error_message}")
        return jsonify({
            'status': 'error',
            'message': error_message
        }), 500

@app.route('/chats', methods=['GET'])
def get_chats():
    query = "SELECT c.chatId, c.content FROM c"
    items  = get_chatlist(query, [])
    item_list = list(items)
    return jsonify(item_list)

@app.route('/chat-history', methods=['GET'])
def get_chat_history():
    # Get the chat_id from query parameters
    chat_id = request.args.get('chat_id')
    
    # Validate chat_id
    if not chat_id:
        return jsonify({'error': 'chat_id is required'}), 400

    query = "SELECT c.You, c.AI FROM c WHERE c.chatId = @value order by c._ts"
    parameters = [{"name": "@value", "value": chat_id}]

    chat_history  = container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True  # Enable cross-partition queries if needed
    )

    # Transform chat history into the desired format
    messages = []
    for entry in chat_history:
        # User's message
        if entry.get('You'):
            messages.append({
                'content': entry['You'],
                'type': 'user',
                'feedback': entry.get('feedback')
            })
        # AI's response
        if entry.get('AI'):
            messages.append({
                'content': entry['AI'],
                'type': 'bot',
                'feedback': entry.get('feedback')
            })

    # Return the formatted chat history
    return jsonify({'messages': messages})


def read_dynamic_file(file_name, container_name, connection_string):
    # Initialize Blob Service Client
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)

    # Download the blob content
    download_stream = blob_client.download_blob()
    file_content = download_stream.readall()
    
    # Detect file type and read it into a DataFrame
    _, file_extension = os.path.splitext(file_name)
    if file_extension == '.csv':
        data = pd.read_csv(BytesIO(file_content))
    elif file_extension in ['.xlsx', '.xls']:
        data = pd.read_excel(BytesIO(file_content))
    else:
        raise ValueError("Unsupported file format. Use CSV or Excel.")
    
    return data


def dump_data_to_sql(data, table_name):

    cursor, conn = AllFunctions._make_pyodbc_client()
    # Create table dynamically based on DataFrame
    columns = ', '.join(f"[{col}] NVARCHAR(MAX)" for col in data.columns)
    create_table_query = f"CREATE TABLE {table_name} ({columns})"
    
    try:
        cursor.execute(create_table_query)
        conn.commit()
        print(f"Table '{table_name}' created successfully.")
    except Exception as e:
        print(f"Table creation failed: {e}")

    # Insert data
    for index, row in data.iterrows():
        # Convert row to a list and handle potential float conversion issues
        row_data = [None if pd.isna(value) else str(value) for value in row]
        placeholders = ', '.join(['?'] * len(row_data))
        insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"
        # print("727")
        try:
            cursor.execute(insert_query, *row_data)
            # print("729")
        except Exception as e:
            print(f"Data insertion failed at row {index}: {e}")
    conn.commit()
    print("731")
    conn.close()
    print(f"Data inserted into '{table_name}'.")


@app.route('/upload', methods=['POST'])
def upload_file():
    print("Upload Hit")
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    # Get the uploaded file
    file = request.files['file']
    file_name_main = file.filename

    chat_id = str(uuid.uuid1())
    chat_id_frontend = f"chat_{int(time.time() * 1000)}"

    # Extract the file name and extension
    file_name, file_extension = file_name_main.rsplit('.', 1)
    # Generate a timestamp
    timestamp = time.strftime('%Y%m%d_%H%M%S')

    # Create the new dynamic filename
    dynamic_filename_with_extension = f"{file_name}_{timestamp}.{file_extension}"
    dynamic_tablename = generate_dynamic_name(dynamic_filename_with_extension)

    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = "rocketcontainer"
    
    try:
        # Initialize Azure Blob Service Client
        print("before Blob")
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=dynamic_filename_with_extension)

        # Upload file to Azure Blob Storage
        blob_client.upload_blob(file, overwrite=True)
        print("769")
        data = read_dynamic_file(dynamic_filename_with_extension, container_name, connect_str)
        print("data: ",data.head())
        print("data dump start")
        dump_data_to_sql(data, dynamic_tablename)
        print("data dump done")

        print("after Blob")
        # # Read the uploaded file into a DataFrame
        # file_content = file.read()
        # _, file_extension = os.path.splitext(file_name)
        # if file_extension == '.csv':
        #     data = pd.read_csv(BytesIO(file_content))
        # elif file_extension in ['.xlsx', '.xls']:
        #     data = pd.read_excel(BytesIO(file_content))
        # else:
        #     return jsonify({"error": "Unsupported file format. Use CSV or Excel."}), 400
        print(data.head())
        # Optionally, preview or process the DataFrame
        preview = data.head().to_dict()
        print({
            'id': chat_id,
            "chatId": chat_id_frontend,
            "content": file_name_main,
            "file": dynamic_filename_with_extension,
            "table": dynamic_tablename
            # 'timestamp': datetime.datetime.now(datetime.UTC)
        })
        container_chatlist.upsert_item({
            'id': chat_id,
            "chatId": chat_id_frontend,
            "content": file_name_main,
            "file": dynamic_filename_with_extension,
            "table": dynamic_tablename
            # 'timestamp': datetime.datetime.now(datetime.UTC)
        })
        embedding = get_embedding(
            "Uploaded File : \n" + file_name_main,
            model="text-embedding-ada-002" # model should be set to the deployment name you chose when you deployed the text-embedding-ada-002 (Version 2) model
        )

        container.upsert_item({
                'id': str(uuid.uuid4()),
                'chatId': chat_id_frontend,
                'AI': '',
                'You': "Uploaded File : \n" + file_name_main,
                'feedback': None,
                'embedding': embedding
            })

        return jsonify({"message": f"File '{file_name}' uploaded successfully.", "preview": preview}), 200
    except Exception as e:
        print("err0r", e)
        return jsonify({"error": str(e)}), 500

import azure.cognitiveservices.speech as speechsdk
import os
import wave

def validate_audio_file(file_path):
    """Validate if the audio file exists and is in the correct format"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    
    try:
        with wave.open(file_path, 'rb') as wave_file:
            # Check if it's a valid WAV file
            channels = wave_file.getnchannels()
            sample_width = wave_file.getsampwidth()
            frame_rate = wave_file.getframerate()
            
            print(f"Audio file details:")
            print(f"Channels: {channels}")
            print(f"Sample width: {sample_width} bytes")
            print(f"Frame rate: {frame_rate} Hz")
            
            # Azure Speech SDK typically works best with:
            # - 16-bit PCM
            # - Sample rates: 8000, 16000, or 48000 Hz
            # - Mono or stereo
            
            if sample_width != 2:  # 2 bytes = 16-bit
                print("Warning: Audio file is not 16-bit PCM")
    except wave.Error:
        raise ValueError("Invalid or corrupted WAV file")

def get_transcribe_audio(file_path):
    """Transcribe audio file using Azure Speech SDK with improved error handling"""
    try:
        # Validate the audio file first
        validate_audio_file(file_path)
        
        # Convert file path to absolute path
        file_path = os.path.abspath(file_path)
        print(f"Processing file: {file_path}")
        
        # Initialize speech config
        speech_config = speechsdk.SpeechConfig(
            subscription="DtF6KCHDUuaemviqPs217JNfMXaLAz8h1lYLVPVNSYPQB6vpkz1FJQQJ99BCACYeBjFXJ3w3AAAYACOGxrrb",
            region="eastus"
        )
        speech_config.speech_recognition_language = "en-US"
        
        # Initialize audio config with the absolute path
        audio_config = speechsdk.audio.AudioConfig(filename=file_path)
        
        # Create speech recognizer
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )
        
        print("Starting transcription...")
        
        # Set up event handlers for detailed debugging
        def handle_recognized(evt):
            print(f"Recognition result: {evt.result.text}")
            
        def handle_canceled(evt):
            print(f"Recognition canceled: {evt.result.cancellation_details.reason}")
            print(f"Error details: {evt.result.cancellation_details.error_details}")
            
        speech_recognizer.recognized.connect(handle_recognized)
        speech_recognizer.canceled.connect(handle_canceled)
        
        # Perform the transcription
        result = speech_recognizer.recognize_once_async().get()
        
        # Handle the result
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return f"{result.text}"
        elif result.reason == speechsdk.ResultReason.NoMatch:
            error_details = result.no_match_details
            return f"No speech could be recognized. Error: {error_details.reason}"
        elif result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details
            return f"Transcription canceled. Reason: {details.reason}, Error details: {details.error_details}"
            
    except FileNotFoundError as e:
        return f"File error: {str(e)}"
    except ValueError as e:
        return f"Audio format error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

# def get_transcribe_audio(file_path):
#     print(file_path, "743")
#     speech_config = speechsdk.SpeechConfig(subscription="801fa391-a958-44e6-b87f-f0a37a1bb1d2", region="eastus")
#     speech_config.speech_recognition_language="en-US"

#     audio_config = speechsdk.audio.AudioConfig(filename=file_path)
#     # audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
#     print("749")
#     speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

#     print("Speak into your microphone.")
#     speech_recognition_result = speech_recognizer.recognize_once_async().get()

#     if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
#         return ("Recognized: {}".format(speech_recognition_result.text))
#     elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
#         return ("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
#     elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
#         cancellation_details = speech_recognition_result.cancellation_details
#         print("Speech Recognition canceled: {}".format(cancellation_details.reason))
#         if cancellation_details.reason == speechsdk.CancellationReason.Error:
#             return ("Error details: {}".format(cancellation_details.error_details))
#             print("Did you set the speech resource key and region values?")


#     print("Transcribing audio file:", file_path)
    # azure_speech_api_url = "https://ai-lekhachampaneria8487ai737923018098.cognitiveservices.azure.com/speechtotext/transcriptions:transcribe?api-version=2024-05-15-preview"  # Adjust the region
    # api_key = "1Qe9ilJSF0xhK57juVWLhbdqlwfMoxMH7ZJHbJXHkbJ6AGpvu8jzJQQJ99BAACYeBjFXJ3w3AAAYACOGgZgE"

    # headers = {
    #     'Ocp-Apim-Subscription-Key': api_key,
    #     'Content-Type': 'application/json'
    # }

    # Define transcription parameters, modify them based on your needs
    # transcription_params = {
    #     "locale": "en-US",  # Specify the locale for the transcription
    #     "recordingsUrl": "string",  # Optional: If you're sending a URL instead of a file
    # }

    # api_key = "801fa391-a958-44e6-b87f-f0a37a1bb1d2"
    # region = "eastus"
    # # endpoint = f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
    # endpoint = f"https://ai-lekhachampaneria8487ai737923018098.cognitiveservices.azure.com/speechtotext/transcriptions:transcribe?api-version=2024-05-15-preview"
    
    # headers = {
    #     "Ocp-Apim-Subscription-Key": api_key,
    #     "Content-Type": "audio/wav",
    # }
    
    # params = {
    #     "language": "en-US"
    # }
    
    # with open(file_path, "rb") as audio_file:
    #     response = requests.post(azure_speech_api_url, headers=headers, params=params, data=audio_file)
    
    # if response.status_code == 200:
    #     result = response.json()
    #     print("Transcription:", result.get("DisplayText", "No transcription available"))
    #     return result.get("DisplayText", "No transcription available")
    # else:
    #     print("Error:", response.status_code, response.text)
    #     return  ''


# Route to handle the audio file upload and transcription
@app.route('/api/voice', methods=['POST'])
def transcribe_audio():

    print("request : ", request)

    if 'audio' not in request.files:
        print("No Audio file upploaded")
        return jsonify({'error': 'No audio file uploaded'}), 400
    
    # Save the audio file temporarily
    audio_file = request.files['audio']
    print("audio_file file uploaded", audio_file)

    # filename = f"audio_{int(time.time() * 1000)}.wav"

    # print("audio_file.filename", filename)

    audio_file_path = os.path.join('data', 'response.wav') #'response.wav' #os.path.join('', 'response.wav')
    audio_file.save(audio_file_path)

    # print("saved", audio_file_path)
    time.sleep(3)
    
    # Now, we send this audio file to Azure Speech API for transcription
    try:
        print("try")
        transcript = get_transcribe_audio(audio_file_path)
        return jsonify({'transcription': transcript})
    except Exception as e:
        print('error : ',  str(e))
        return jsonify({'error': str(e)}), 500
    

if __name__ == "__main__":
    app.run(debug=True, port=5000)