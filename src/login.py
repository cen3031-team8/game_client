import dearpygui.dearpygui as dpg
import requests
import subprocess
import screeninfo
import json
import os

API_URL = "http://127.0.0.1:8508"
LOGIN_ENDPOINT = "/auth/login"
REGISTER_ENDPOINT = "/auth/register"
TOKEN_FILE = "token.json"


def save_token(token, user_id, username):
    """Save the JWT token and user info to a file for the client to use."""
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump({
                "token": token,
                "userId": user_id,
                "username": username
            }, f)
    except Exception as e:
        print(f"Error saving token: {e}")


def login_callback():
    username = dpg.get_value("username_input")
    password = dpg.get_value("password_input")

    dpg.set_value("status_text", "Logging in...")
    dpg.configure_item("status_text", color=(255, 255, 0))

    payload = {"username": username, "password": password}
    try:
        response = requests.post(API_URL + LOGIN_ENDPOINT, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Save token for client to use
            save_token(data.get("token"), data.get("userId"), data.get("username"))
            
            dpg.set_value("status_text", f"Login Successful! Welcome, {username}!")
            dpg.configure_item("status_text", color=(0, 255, 0))
            subprocess.Popen(["python3", "client.py"])
            dpg.stop_dearpygui()
        elif response.status_code == 401:
            dpg.set_value("status_text", f"Invalid username or password for {username}")
            dpg.configure_item("status_text", color=(255, 0, 0))
        else:
            error_message = response.json().get("error", "Unknown error")
            dpg.set_value("status_text", f"Login Failed: {error_message} ({response.status_code})")
            dpg.configure_item("status_text", color=(255, 0, 0))
    except Exception as e:
        dpg.set_value("status_text", f"Error: {e}")
        dpg.configure_item("status_text", color=(255, 0, 0))


def register_callback():
    username = dpg.get_value("username_input")
    password = dpg.get_value("password_input")

    dpg.set_value("status_text", "Registering...")
    dpg.configure_item("status_text", color=(255, 255, 0))

    # API requires email, so use username as email if not provided separately
    payload = {"username": username, "email": username + "@pokemon.local", "password": password}
    try:
        response = requests.post(API_URL + REGISTER_ENDPOINT, json=payload, timeout=5)
        if response.status_code in (200, 201):
            data = response.json()
            # Save token for client to use
            save_token(data.get("token"), data.get("userId"), data.get("username"))
            
            dpg.set_value("status_text", f"Registration successful for {username}! You can now log in.")
            dpg.configure_item("status_text", color=(0, 255, 0))
        elif response.status_code == 409:
            dpg.set_value("status_text", f"User '{username}' already exists.")
            dpg.configure_item("status_text", color=(255, 0, 0))
        else:
            err = response.json().get("error", "Unknown error")
            dpg.set_value("status_text", f"Registration failed: {err} ({response.status_code})")
            dpg.configure_item("status_text", color=(255, 0, 0))
    except Exception as e:
        dpg.set_value("status_text", f"Error: {e}")
        dpg.configure_item("status_text", color=(255, 0, 0))


# === UI ===
# --- UI SETUP (replace your current UI block with this) ---
dpg.create_context()

# Get screen dimensions
try:
    from screeninfo import get_monitors
    m = get_monitors()[0]
    screen_w, screen_h = m.width, m.height
except Exception:
    screen_w, screen_h = 1920, 1080

# Window: 16:9, ~1/4 screen width
win_w = int(screen_w * 0.40)
win_h = int(win_w * 9 / 16)
pos_x = (screen_w - win_w) // 2
pos_y = (screen_h - win_h) // 2

# form content width (everything centers as one block)
form_w = 280  # adjust if you want wider/narrower content

def center_form(_=None):
    """Center the form child window inside the main window (exactly)."""
    # main window size (in case DPI/OS tweaks it)
    ww, wh = dpg.get_item_rect_size("login_window")
    # form size (height auto-sizes to content)
    fw, fh = dpg.get_item_rect_size("form")
    # compute top-left so form is centered
    x = max((ww - fw) // 2, 0)
    y = max((wh - fh) // 2, 0)
    dpg.configure_item("form", pos=(x, y))

with dpg.window(label="Pokémon Login",
                tag="login_window",
                width=win_w, height=win_h,
                pos=(pos_x, pos_y),
                no_resize=True, no_move=True):

    # Child container that we will center precisely
    with dpg.child_window(tag="form",
                          width=form_w, autosize_y=True,
                          border=False, no_scrollbar=True):

        dpg.add_text("Welcome to Pokémon Game")
        dpg.add_separator()
        dpg.add_spacer(height=16)

        # Inputs with placeholder (no labels)
        input_w = form_w
        dpg.add_input_text(tag="username_input", hint="Username", width=input_w)
        dpg.add_input_text(tag="password_input", hint="Password", password=True, width=input_w)
        dpg.add_spacer(height=14)

        # Buttons centered because they live inside the centered form
        btn_w = 100
        # add an inner row where side spacers = (form_w - 2*btn_w - gap)/2
        gap = 12
        side = max((form_w - (2*btn_w + gap)) // 2, 0)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=side)
            dpg.add_button(label="Login", width=btn_w, callback=login_callback)
            dpg.add_spacer(width=gap)
            dpg.add_button(label="Register", width=btn_w, callback=register_callback)
            dpg.add_spacer(width=side)

        dpg.add_spacer(height=12)
        dpg.add_text("", tag="status_text", wrap=form_w)

# Create + show viewport, then center the form once sizes exist
dpg.create_viewport(title="Pokémon Login", width=win_w, height=win_h)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("login_window", True)

# Center after first frame so measured sizes are correct
dpg.set_frame_callback(1, center_form)

dpg.start_dearpygui()
dpg.destroy_context()

