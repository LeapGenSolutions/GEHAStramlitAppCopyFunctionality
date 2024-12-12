import streamlit as st
import random
from st_copy_to_clipboard import st_copy_to_clipboard


def render_feedback_buttons(message_id: str):
    """Render feedback buttons horizontally"""
    feedback_key = f"feedback_{message_id}"
    # copy_button_id = f"copy_button_{message_id}"
    # Create a horizontal container for buttons
    print("Im here")
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
                print("Copy button pressed!")
                # Encode the content to avoid JS injection and preserve formatting
                copy_text = "hello world"  # Text to copy to clipboard
                # import pyperclip
                # pyperclip.copy("Hello world!")
                st_copy_to_clipboard("My name is")
    
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # if "copied" not in st.session_state: 
# #     st.session_state.copied = []
    
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])
        
# if prompt := st.chat_input("What is up?"):

#     st.session_state.messages.append({"role": "user", "content": prompt})
    
#     with st.chat_message("user"):
#         st.markdown(prompt)

#     assistant_response = random.choice([
#         "Hello there!",
#         "Hi human!", 
#         "Need help?",
#         """st.title("Simple chat")"""
#     ])
    
#     full_response = ""
#     for chunk in assistant_response.split():
#         full_response += chunk + " "
        
#     with st.chat_message("assistant"):
#         st.markdown(full_response)
            
render_feedback_buttons("123")

    # st.session_state.messages.append({"role": "assistant", "content": full_response})
    
# for text in st.session_state.copied:
#     st.toast(f"Copied to clipboard: {text}", icon='✅' )