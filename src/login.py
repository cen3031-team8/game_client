import dearpygui.dearpygui as dpg
import requests
import json


API_URL = "" # Ian can you change this 
LOGIN_ENDPOINT = "/auth/login"



def login_callback():
    """
    Called when the 'Login' button is clicked.
    Retrieves user/pass, sends to API, and updates UI with feedback.
    """
    # Get values from input fields
    username = dpg.get_value("username_input")
    password = dpg.get_value("password_input")

    # Update status text
    dpg.set_value("status_text", "Logging in...")
    dpg.configure_item("status_text", color=(255, 255, 0)) # Yellow

    # Prepare API request
    full_url = API_URL + LOGIN_ENDPOINT
    payload = {
        "user": username,
        "pass": password
    }
    
    # Send POST request
    try:
        response = requests.post(full_url, json=payload, timeout=5)

        # Handle response
        if response.status_code == 200:
            # Successful login
            dpg.set_value("status_text", f"Login Successful! Welcome, {username}!")
            dpg.configure_item("status_text", color=(0, 255, 0)) # Green
            # can later hide the login window and show the main game window
            # dpg.hide_item("login_window")
            # dpg.show_item("main_game_window") # (if you create one)
        else:
            # Failed login
            error_message = response.json().get("error", "Unknown error")
            dpg.set_value("status_text", f"Login Failed: {error_message} (Code: {response.status_code})")
            dpg.configure_item("status_text", color=(255, 0, 0)) # Red

    except requests.exceptions.ConnectionError:
        dpg.set_value("status_text", "Error: Could not connect to API at " + API_URL)
        dpg.configure_item("status_text", color=(255, 0, 0)) # Red
    except requests.exceptions.Timeout:
        dpg.set_value("status_text", "Error: Connection timed out.")
        dpg.configure_item("status_text", color=(255, 0, 0)) # Red
    except Exception as e:
        dpg.set_value("status_text", f"An unexpected error occurred: {e}")
        dpg.configure_item("status_text", color=(255, 0, 0)) # Red


# UI setup
dpg.create_context()

with dpg.window(label="Pokemon Game Login", width=400, height=300, tag="login_window"):
    dpg.add_text("Please log in to continue")
    dpg.add_separator()

    dpg.add_spacer(height=20)

    # Username
    dpg.add_input_text(label="Username", tag="username_input", width=200)
    
    # Password
    dpg.add_input_text(label="Password", tag="password_input", password=True, width=200)

    dpg.add_spacer(height=20)

    # Login Button
    dpg.add_button(label="Login", callback=login_callback, width=100)

    dpg.add_spacer(height=20)

    # Status Text
    dpg.add_text("", tag="status_text")

# Run app

dpg.create_viewport(title='Pokemon Login', width=400, height=300)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("login_window", True)
dpg.start_dearpygui()
dpg.destroy_context()
