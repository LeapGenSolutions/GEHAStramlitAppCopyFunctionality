import os
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
import uuid
import requests
import json
from azure.cosmos import CosmosClient, exceptions
import re
import streamlit.components.v1 as components

def get_or_create_ids():
    """Generate or retrieve session and user IDs."""
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = str(uuid.uuid4())
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = str(uuid.uuid4())
    return st.session_state['session_id'], st.session_state['user_id']

def consume_api(url, user_query):
    """Uses requests POST to talk to the FastAPI backend, supports streaming."""
    headers = {'Content-Type': 'application/json'}
    config = {"configurable": {
        "session_id": st.session_state.session_id,
        "user_id": st.session_state.user_id
    }}
    user_query = 'search ' + user_query
    payload = {'input': {"question": user_query}, 'config': config}
    
    final_response = []
    tool_usage = False
    current_paragraph = []
    is_docsearch = False
    seen_content = set()  # Using a set to track all unique content
    
    def process_paragraph():
        if current_paragraph:
            paragraph = "".join(current_paragraph).strip()
            # Normalize the paragraph by removing extra whitespace and standardizing newlines
            normalized_paragraph = ' '.join(paragraph.split())
            if paragraph and normalized_paragraph not in seen_content:
                final_response.append(paragraph)
                seen_content.add(normalized_paragraph)
            current_paragraph.clear()
    
    try:
        with requests.post(url, json=payload, headers=headers, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        json_data = decoded_line[len('data: '):]
                        try:
                            data = json.loads(json_data)
                            if "event" in data:
                                kind = data["event"]
                                if kind == "on_tool_start":
                                    process_paragraph()
                                    tool_usage = True
                                    is_docsearch = "docsearch" in data.get("name", "").lower()
                                elif kind == "on_tool_end":
                                    process_paragraph()
                                    tool_usage = False
                                    is_docsearch = False
                                elif kind == "on_chat_model_stream" and not tool_usage:
                                    content = data["data"]["chunk"]["content"]
                                    current_paragraph.append(content)
                                    if '\n\n' in content or '. ' in content:
                                        process_paragraph()
                            elif "content" in data and tool_usage:
                                content = data["content"]
                                # Normalize the content
                                normalized_content = ' '.join(content.strip().split())
                                if normalized_content not in seen_content:
                                    if is_docsearch:
                                        current_paragraph.append(content)
                                        if '\n\n' in content:
                                            process_paragraph()
                                    else:
                                        process_paragraph()
                                        if content.strip():
                                            print(content)
                                            final_response.append(content)
                                            seen_content.add(content)
                                            # seen_content.add(normalized_content)
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        return f"An error occurred: {str(e)}"
    
    # Process any remaining content
    process_paragraph()
    # print(final_response)
    if final_response and len(final_response)>1:
        final_response.pop()
    
    return "\n\n".join(response for response in final_response if response.strip())
# App configuration


st.set_page_config(
    page_title="FastAPI Backend Bot",
    page_icon="Ã°Å¸Â¤â€“",
    layout="wide",
    initial_sidebar_state="collapsed"
)
 

st.markdown("""
<style>
    /* Hide header and unnecessary padding */
    header, button[kind="headerNoPadding"] {
        display: none !important;
    }
    
    /* Container styling */
    .block-container {
        padding-top: 8px;    
    }
    
    div[data-testid="stBottomBlockContainer"] {
        padding: 1rem;
        background-color: rgba(7, 2, 14, 1);
    }
    
    /* Chat message styling - Now white */
    .stChatMessage {
        background-color: #FFFFFF !important;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stChatMessage p {
        background-color: transparent !important;
        margin-bottom: 0;
        color: #000000 !important;
    }
    
    /* Main section styling */
    section[tabindex="0"] {
        background-color: rgba(7, 2, 14, 1);
        background-repeat: no-repeat;
        background-position: center;
        background-size: 300px 300px;
    }
    
    /* Text box styling - Pure white */
    textarea {
        background-color: #FFFFFF !important;
        border: none !important;
        color: #000000 !important;
        padding: 15px;
        font-size: 16px !important;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    }
    
    textarea:focus {
        outline: none;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }
    
    /* Feedback buttons styling */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        width: 40px;
    }
    
    button[data-testid="baseButton-secondary"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0;
        border-radius: 6px;
        transition: all 0.3s ease;
    }
    
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #F5F5F5 !important;
    }
    
    /* Submit button styling */
    div[data-testid="stChatInputSubmitButton"] {
        color: #000000 !important;
        opacity: 0.9;
        transition: opacity 0.3s ease;
    }
    
    div[data-testid="stChatInputSubmitButton"]:hover {
        opacity: 1;
    }
</style>
""", unsafe_allow_html=True)
def check_authentication():
    # Get query parameters using the new non-experimental API
    query_params = st.query_params
    
    # Extract username and admin flag
    username = query_params.get('name')
    useremail = query_params.get('preferred_username')
    multiturn=query_params.get('multiturn')
    
    if not username:
        st.error("Authentication Error: Please login through the main application")
        st.stop()
    
    return username, useremail,multiturn

def add_user_info(container, item_id, partition_key, user_name, user_email):
    try:
        # Read existing document
        document = container.read_item(item=item_id, partition_key=partition_key)
        
        # Add user info to document
        document['user_name'] = user_name
        document['user_email'] = user_email
        
        # Replace document in database
        container.replace_item(item_id, document)
        
    except exceptions.CosmosHttpResponseError as e:
        st.error(f"Error updating document: {e}")


def get_cosmos_client():
    # Replace with your actual Cosmos DB connection details
    endpoint = os.environ.get("AZURE_COSMOSDB_ENDPOINT")
    key =os.environ.get("COSMOS_DB_KEY")
    
    # Initialize the Cosmos client
    client = CosmosClient(endpoint, key)
    return client
 
def get_container(client, database_name=os.environ.get("AZURE_COSMOSDB_NAME"), container_name=os.environ.get("AZURE_COSMOSDB_CONTAINER_NAME_REDACTED")):
    database = client.get_database_client(database_name)
    container = database.get_container_client(container_name)
    return container
 
def render_feedback_buttons(message_id: str, response_content: str):
    """Render feedback buttons horizontally"""
    feedback_key = f"feedback_{message_id}"
    # copy_button_id = f"copy_button_{message_id}"
    # Create a horizontal container for buttons
    container = st.container()
    
    # Define a container for feedback buttons
    with container:
        cols = st.columns([1, 1, 8])  # Adjust column ratios for better spacing
        
        # Place buttons side by side
        
        with cols[0]:
            if st.button(":+1:", key=f"thumbs_up", help="Helpful response"):
                pass
        
        with cols[1]:
            if st.button(":-1:", key=f"thumbs_down", help="Not helpful response"):
                pass
        with cols[2]:
            if st.button(":clipboard:", key=f"copy_button", help="Copy Response!"):
                # Encode the content to avoid JS injection and preserve formatting
                copy_text = "hello world"  # Text to copy to clipboard
                import pyperclip
                pyperclip.copy("Hello world!")
                
   
#comment this
# url = "https://webapp-backend-botid-gy4phravzt2ak-staging.azurewebsites.net" + "/agent/stream_events"

BASE_URL = "https://webapp-backend-botid-gy4phravzt2ak-staging.azurewebsites.net"
CHAT_ENDPOINT = f"{BASE_URL}/agent/stream_events"
CHAT_ENDPOINT_ST = f"{BASE_URL}/agent_st/stream_events"
FEEDBACK_ENDPOINT = "f{BASE_URL}/feedback"


###
user_name, user_email,multiturn = check_authentication()
session_id, user_id = get_or_create_ids()

def create_ai_message(content: str, message_id: str = None):
    """Create an AI message with proper structure"""
    if message_id is None:
        message_id = str(uuid.uuid4())
    
    message = AIMessage(content=content)
    message.additional_kwargs = {
        'id': message_id,
        'type': 'ai',
        'data': {
            'content': content,
            'id': message_id,
            'additional_kwargs': {},
            'type': 'ai'
        }
    }
    return message


 
# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [AIMessage(content="Hello! I am your GEHA General Knowledge Assistant. What information are you seeking?")]
 
# Display chat history
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.write(message.content)
            message_id = message.additional_kwargs.get('id', str(uuid.uuid4()))
            render_feedback_buttons(message_id, message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.write(message.content)
            
# User input
# x=1
# multiturn=True
user_query = st.chat_input("Type your message here...")
if user_query is not None and user_query != "":

    st.session_state.chat_history.append(HumanMessage(content=user_query))

    with st.chat_message("Human"):
        st.markdown(user_query)
         
     
       


    with st.chat_message("AI"):
        message_id = str(uuid.uuid4())
        response_container = st.empty()
        
        
        full_response = ""
        with st.spinner(text=""):
            for chunk in consume_api(CHAT_ENDPOINT,user_query):
                full_response += chunk
                response_container.markdown(full_response)
                
 
        ai_message = create_ai_message(full_response, message_id)
       
        st.session_state.chat_history.append(ai_message)
        
        # Don't clear and rewrite - keep the streamed content
        render_feedback_buttons(message_id, full_response)


