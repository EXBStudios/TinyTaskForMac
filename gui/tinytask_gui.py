import time
from pynput import mouse, keyboard
import json
import threading
import pyautogui
import tkinter as tk
from tkinter import filedialog, messagebox
import requests # <-- New import!
import os       # <-- New import!
import zipfile  # <-- New import!
import shutil   # <-- New import!

# --- Versioning for Updater ---
CURRENT_VERSION = "v1.0.0"

GITHUB_REPO_OWNER = "EXBStudios"
GITHUB_REPO_NAME = "TinyTaskForMac"
GITHUB_RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"

# --- Global Variables ---
recorded_events = []
is_recording = False
recording_start_time = 0
is_playing = False

# Tkinter GUI elements
status_label = None
record_button = None
stop_record_button = None
play_button = None
stop_play_button = None
save_button = None
load_button = None
update_button = None # <-- New button

# --- Event Handlers (from previous steps, unchanged logic) ---

def on_mouse_click(x, y, button, pressed):
    global recorded_events, is_recording, recording_start_time
    if is_recording:
        event_type = "mouse_click"
        timestamp = time.time() - recording_start_time
        recorded_events.append({
            "type": event_type,
            "x": x,
            "y": y,
            "button": str(button),
            "pressed": pressed,
            "time": timestamp
        })

def on_mouse_move(x, y):
    global recorded_events, is_recording, recording_start_time
    if is_recording:
        event_type = "mouse_move"
        timestamp = time.time() - recording_start_time
        if not recorded_events or \
           recorded_events[-1]["type"] != event_type or \
           abs(recorded_events[-1]["x"] - x) > 1 or \
           abs(recorded_events[-1]["y"] - y) > 1:
            recorded_events.append({
                "type": event_type,
                "x": x,
                "y": y,
                "time": timestamp
            })

def on_mouse_scroll(x, y, dx, dy):
    global recorded_events, is_recording, recording_start_time
    if is_recording:
        event_type = "mouse_scroll"
        timestamp = time.time() - recording_start_time
        recorded_events.append({
            "type": event_type,
            "x": x,
            "y": y,
            "dx": dx,
            "dy": dy,
            "time": timestamp
        })

def on_key_press(key):
    global recorded_events, is_recording, recording_start_time
    if is_recording:
        event_type = "key_press"
        timestamp = time.time() - recording_start_time
        try:
            char = key.char
        except AttributeError:
            char = str(key)
        recorded_events.append({
            "type": event_type,
            "key": char,
            "time": timestamp
        })

def on_key_release(key):
    global recorded_events, is_recording, recording_start_time
    if is_recording:
        event_type = "key_release"
        timestamp = time.time() - recording_start_time
        try:
            char = key.char
        except AttributeError:
            char = str(key)
        recorded_events.append({
            "type": event_type,
            "key": char,
            "time": timestamp
        })

# --- Listener Management (from previous steps, unchanged logic) ---

mouse_listener = None
keyboard_listener = None

def update_status(message):
    if status_label:
        status_label.config(text=f"Status: {message}")
    print(f"Status: {message}") # Keep console output for debugging

def enable_buttons():
    record_button.config(state=tk.NORMAL)
    stop_record_button.config(state=tk.DISABLED)
    play_button.config(state=tk.NORMAL)
    stop_play_button.config(state=tk.DISABLED)
    save_button.config(state=tk.NORMAL)
    load_button.config(state=tk.NORMAL)
    update_button.config(state=tk.NORMAL) # Enable update button

def disable_for_recording():
    record_button.config(state=tk.DISABLED)
    stop_record_button.config(state=tk.NORMAL)
    play_button.config(state=tk.DISABLED)
    stop_play_button.config(state=tk.DISABLED)
    save_button.config(state=tk.DISABLED)
    load_button.config(state=tk.DISABLED)
    update_button.config(state=tk.DISABLED) # Disable update during recording/playback

def disable_for_playback():
    record_button.config(state=tk.DISABLED)
    stop_record_button.config(state=tk.DISABLED)
    play_button.config(state=tk.DISABLED)
    stop_play_button.config(state=tk.NORMAL)
    save_button.config(state=tk.DISABLED)
    load_button.config(state=tk.DISABLED)
    update_button.config(state=tk.DISABLED) # Disable update during recording/playback

def start_recording():
    global is_recording, recorded_events, recording_start_time, mouse_listener, keyboard_listener

    if is_recording:
        update_status("Already recording.")
        return
    if is_playing:
        update_status("Cannot start recording while playback is active. Stop playback first.")
        return

    recorded_events = []
    is_recording = True
    recording_start_time = time.time()
    update_status("Recording... Perform actions, then click 'Stop Recording'.")
    disable_for_recording()

    mouse_listener = mouse.Listener(
        on_click=on_mouse_click,
        on_move=on_mouse_move,
        on_scroll=on_mouse_scroll
    )
    keyboard_listener = keyboard.Listener(
        on_press=on_key_press,
        on_release=on_key_release
    )
    mouse_listener.start()
    keyboard_listener.start()

def stop_recording():
    global is_recording, mouse_listener, keyboard_listener

    if not is_recording:
        update_status("Not currently recording.")
        return

    is_recording = False
    update_status("Stopped recording.")
    enable_buttons()

    if mouse_listener and mouse_listener.is_alive():
        mouse_listener.stop()
        mouse_listener.join()
    if keyboard_listener and keyboard_listener.is_alive():
        keyboard_listener.stop()
        keyboard_listener.join()
    
    save_recorded_events_gui()

def save_recorded_events_gui():
    if not recorded_events:
        messagebox.showinfo("Info", "No macro recorded to save.")
        return

    filepath = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON files", "*.json")],
                                            initialfile="my_macro.json")
    if filepath:
        try:
            with open(filepath, 'w') as f:
                json.dump(recorded_events, f, indent=4)
            update_status(f"Saved {len(recorded_events)} events to '{filepath}'.")
            messagebox.showinfo("Success", f"Macro saved successfully to:\n{filepath}")
        except Exception as e:
            update_status(f"Error saving macro: {e}")
            messagebox.showerror("Error", f"Failed to save macro: {e}")
    else:
        update_status("Save operation cancelled.")

def load_recorded_events_gui():
    global recorded_events

    filepath = filedialog.askopenfilename(defaultextension=".json",
                                          filetypes=[("JSON files", "*.json")])
    if filepath:
        try:
            with open(filepath, 'r') as f:
                loaded_events = json.load(f)
                if all(isinstance(e, dict) and "type" in e and "time" in e for e in loaded_events):
                    recorded_events = loaded_events
                    update_status(f"Loaded {len(recorded_events)} events from '{filepath}'.")
                    messagebox.showinfo("Success", f"Macro loaded successfully from:\n{filepath}")
                else:
                    raise ValueError("Invalid macro file format.")
        except FileNotFoundError:
            update_status(f"Error: File not found: '{filepath}'.")
            messagebox.showerror("Error", f"File not found:\n{filepath}")
        except json.JSONDecodeError:
            update_status(f"Error: Invalid JSON format in '{filepath}'.")
            messagebox.showerror("Error", f"Invalid macro file format:\n{filepath}")
        except Exception as e:
            update_status(f"An unexpected error occurred loading macro: {e}")
            messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")
    else:
        update_status("Load operation cancelled.")

# --- Playback Functionality (from previous steps, unchanged logic) ---

def play_recorded_macro():
    global is_playing, recorded_events

    if not recorded_events:
        update_status("No events loaded to play. Load a macro first!")
        messagebox.showinfo("Info", "No macro loaded. Please load one first.")
        return

    if is_playing:
        update_status("Playback is already active.")
        return
    
    if is_recording:
        update_status("Cannot start playback while recording is active. Stop recording first.")
        return

    is_playing = True
    update_status("Playing macro... Click 'Stop Playback' or press F9 to stop.")
    disable_for_playback()

    playback_thread = threading.Thread(target=_execute_playback)
    playback_thread.daemon = True
    playback_thread.start()

def _execute_playback():
    global is_playing

    pyautogui.PAUSE = 0.001
    pyautogui.FAILSAFE = True

    last_event_time = 0
    try:
        for event in recorded_events:
            if not is_playing:
                update_status("Playback interrupted.")
                break

            time_to_wait = event["time"] - last_event_time
            if time_to_wait > 0:
                time.sleep(time_to_wait)

            if event["type"] == "mouse_click":
                button_name = event["button"].replace("Button.", "").lower()
                if event["pressed"]:
                    pyautogui.mouseDown(event["x"], event["y"], button=button_name, _pause=False)
                else:
                    pyautogui.mouseUp(event["x"], event["y"], button=button_name, _pause=False)
            elif event["type"] == "mouse_move":
                pyautogui.moveTo(event["x"], event["y"], _pause=False)
            elif event["type"] == "mouse_scroll":
                scroll_amount = int(event["dy"])
                pyautogui.scroll(scroll_amount, x=event["x"], y=event["y"], _pause=False)
            elif event["type"] == "key_press":
                key_to_press = event["key"]
                if key_to_press.startswith('Key.'):
                    key_to_press = key_to_press.split('Key.')[1].lower()
                pyautogui.keyDown(key_to_press, _pause=False)
            elif event["type"] == "key_release":
                key_to_release = event["key"]
                if key_to_release.startswith('Key.'):
                    key_to_release = key_to_release.split('Key.')[1].lower()
                pyautogui.keyUp(key_to_release, _pause=False)
            
            last_event_time = event["time"]

    except pyautogui.FailSafeException:
        update_status("Playback stopped by Failsafe (mouse moved to top-left corner).")
        messagebox.showinfo("Playback Stopped", "Macro playback was stopped by moving mouse to top-left corner (Failsafe).")
    except Exception as e:
        update_status(f"An error occurred during playback: {e}")
        messagebox.showerror("Playback Error", f"An error occurred during playback: {e}")
    finally:
        is_playing = False
        update_status("Playback finished.")
        enable_buttons()

def stop_playback():
    global is_playing
    if is_playing:
        is_playing = False
        update_status("Playback stop requested.")
    else:
        update_status("No playback is currently active.")

# --- Hotkey for stopping Playback (F9) ---
stop_playback_listener = None

def setup_playback_stop_listener():
    global stop_playback_listener
    def on_f9_release(key):
        if is_playing and key == keyboard.Key.f9:
            print("F9 hotkey detected. Requesting playback stop.")
            if hasattr(setup_playback_stop_listener, 'root_instance'):
                setup_playback_stop_listener.root_instance.after(0, stop_playback)
            return False # Keep the listener active
    
    if stop_playback_listener is None:
        stop_playback_listener = keyboard.Listener(on_release=on_f9_release)
        stop_playback_listener.start()


# --- NEW: Updater Functionality ---

def check_for_updates():
    """Checks GitHub for the latest release version."""
    update_button.config(state=tk.DISABLED) # Disable button during check
    update_status("Checking for updates...")
    try:
        response = requests.get(GITHUB_RELEASES_API_URL, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        latest_release = response.json()
        latest_version = latest_release['tag_name']
        download_url = latest_release['zipball_url'] # URL to download the source code zip

        if latest_version != CURRENT_VERSION:
            update_status(f"New version {latest_version} available! Current: {CURRENT_VERSION}")
            if messagebox.askyesno("Update Available",
                                   f"Version {latest_version} is available. Do you want to download and install it?\n\n"
                                   "Warning: This will overwrite your current script files. Please save any unsaved macros."):
                
                # Run download and install in a separate thread to keep GUI responsive
                update_thread = threading.Thread(target=download_and_install_update, args=(download_url, latest_version))
                update_thread.daemon = True
                update_thread.start()
            else:
                update_status("Update cancelled by user.")
                update_button.config(state=tk.NORMAL)
        else:
            update_status(f"You are running the latest version ({CURRENT_VERSION}).")
            messagebox.showinfo("No Update", f"You are running the latest version ({CURRENT_VERSION}).")
            update_button.config(state=tk.NORMAL)

    except requests.exceptions.RequestException as e:
        update_status(f"Error checking for updates: {e}")
        messagebox.showerror("Update Error", f"Could not check for updates. Error: {e}\n\nPlease check your internet connection and GitHub repository name.")
        update_button.config(state=tk.NORMAL)
    except Exception as e:
        update_status(f"An unexpected error occurred during update check: {e}")
        messagebox.showerror("Update Error", f"An unexpected error occurred during update check: {e}")
        update_button.config(state=tk.NORMAL)

def download_and_install_update(download_url, new_version):
    """Downloads the new version and attempts to replace current files."""
    try:
        update_status(f"Downloading update {new_version}...")
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()

        # Get the directory of the current script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        temp_zip_path = os.path.join(current_dir, "update.zip")
        temp_extract_dir = os.path.join(current_dir, "temp_update_extract")

        with open(temp_zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        update_status("Extracting update...")
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            # GitHub zipballs contain a top-level directory like repo-name-commit_hash
            # We need to extract that and then move its contents.
            # Get the name of the top-level directory
            top_level_dir = zip_ref.namelist()[0].split('/')[0] # e.g., TinyTaskForMac-hash
            zip_ref.extractall(temp_extract_dir)

        # Move files from the extracted top-level directory to the current directory
        extracted_source_path = os.path.join(temp_extract_dir, top_level_dir)
        
        update_status("Installing update...")
        # Iterate over files/dirs in the extracted source and overwrite current ones
        # Be careful: This will overwrite *all* files from the repo.
        # If you have other files (like my_macro.json) that shouldn't be overwritten,
        # you need to explicitly exclude them or handle them.
        for item in os.listdir(extracted_source_path):
            s = os.path.join(extracted_source_path, item)
            d = os.path.join(current_dir, item)
            
            # Avoid overwriting the temp zip or the current running script immediately
            # (though the script will be restarted, so it's less critical for the script itself)
            if item == os.path.basename(__file__):
                continue # Skip the main script for now, let's replace it last or restart will fail

            if os.path.isdir(s):
                if os.path.exists(d):
                    shutil.rmtree(d) # Remove existing directory to ensure clean copy
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d) # copy2 preserves metadata

        # Now, replace the main script if it was updated
        shutil.copy2(os.path.join(extracted_source_path, os.path.basename(__file__)), os.path.join(current_dir, os.path.basename(__file__)))


        update_status("Update successful! Please restart the application.")
        messagebox.showinfo("Update Complete",
                             f"TinyTask for Mac has been updated to version {new_version}.\n\n"
                             "Please restart the application to apply the changes.")

    except requests.exceptions.RequestException as e:
        update_status(f"Error downloading update: {e}")
        messagebox.showerror("Download Error", f"Failed to download update. Error: {e}")
    except zipfile.BadZipFile:
        update_status("Error: Downloaded file is not a valid zip archive.")
        messagebox.showerror("Update Error", "Downloaded file is corrupted or not a valid zip.")
    except Exception as e:
        update_status(f"An error occurred during update installation: {e}")
        messagebox.showerror("Installation Error", f"An error occurred during installation: {e}")
    finally:
        # Clean up temporary files
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)
        
        enable_buttons() # Re-enable buttons, especially update

# --- GUI Setup ---
def create_gui():
    global status_label, record_button, stop_record_button, play_button, stop_play_button, save_button, load_button, update_button

    root = tk.Tk()
    root.title(f"TinyTask for Mac (v{CURRENT_VERSION})") # Show version in title
    root.geometry("300x360") # Adjusted size for new button
    root.resizable(False, False)

    setup_playback_stop_listener.root_instance = root

    status_label = tk.Label(root, text="Status: Idle.", font=("Helvetica", 12), wraplength=280)
    status_label.pack(pady=10)

    button_width = 20

    record_button = tk.Button(root, text="Record", command=start_recording, width=button_width, bg="#4CAF50", fg="white")
    record_button.pack(pady=3)

    stop_record_button = tk.Button(root, text="Stop Recording", command=stop_recording, width=button_width, bg="#f44336", fg="white", state=tk.DISABLED)
    stop_record_button.pack(pady=3)

    play_button = tk.Button(root, text="Play", command=play_recorded_macro, width=button_width, bg="#2196F3", fg="white")
    play_button.pack(pady=3)

    stop_play_button = tk.Button(root, text="Stop Playback (F9)", command=stop_playback, width=button_width, bg="#FF9800", fg="white", state=tk.DISABLED)
    stop_play_button.pack(pady=3)

    save_button = tk.Button(root, text="Save Macro", command=save_recorded_events_gui, width=button_width)
    save_button.pack(pady=3)

    load_button = tk.Button(root, text="Load Macro", command=load_recorded_events_gui, width=button_width)
    load_button.pack(pady=3)

    update_button = tk.Button(root, text="Check for Updates", command=check_for_updates, width=button_width, bg="#607D8B", fg="white") # New button
    update_button.pack(pady=10) # More padding for this one

    if stop_playback_listener is None:
        hotkey_thread = threading.Thread(target=setup_playback_stop_listener)
        hotkey_thread.daemon = True
        hotkey_thread.start()
        print("Background F9 stop listener started.")

    def on_closing():
        if is_recording:
            stop_recording()
        if is_playing:
            stop_playback()
        time.sleep(0.5) 
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()

if __name__ == "__main__":
    # Ensure requests is installed
    try:
        import requests
    except ImportError:
        print("The 'requests' library is not installed. Please install it: pip install requests")
        exit()

    print(f"Starting TinyTask GUI for Mac (Version {CURRENT_VERSION})...")
    print("IMPORTANT: Ensure your Python environment or terminal has Accessibility and Input Monitoring permissions in System Settings.")
    create_gui()
