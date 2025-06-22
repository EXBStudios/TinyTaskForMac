import time
from pynput import mouse, keyboard
import json
import threading
import pyautogui
import tkinter as tk
from tkinter import filedialog, messagebox

# --- Global Variables ---
recorded_events = []
is_recording = False
recording_start_time = 0
is_playing = False

# Tkinter GUI elements (will be initialized in create_gui)
status_label = None
record_button = None
stop_record_button = None
play_button = None
stop_play_button = None
save_button = None
load_button = None

# --- Event Handlers (from Step 1 & 2, unchanged logic) ---

def on_mouse_click(x, y, button, pressed):
    """Callback for mouse click events."""
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
        # print(f"[REC] Click: ({x}, {y}) {button} {'Pressed' if pressed else 'Released'} @ {timestamp:.3f}s") # Suppress console prints for GUI

def on_mouse_move(x, y):
    """Callback for mouse movement events."""
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
    """Callback for mouse scroll events."""
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
        # print(f"[REC] Scroll: ({x}, {y}) dx={dx}, dy={dy} @ {timestamp:.3f}s")

def on_key_press(key):
    """Callback for keyboard key press events."""
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
        # print(f"[REC] Key Press: {char} @ {timestamp:.3f}s")

def on_key_release(key):
    """Callback for keyboard key release events."""
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
        # print(f"[REC] Key Release: {char} @ {timestamp:.3f}s")

        # No ESC hotkey for stopping recording here; we'll use GUI button

# --- Listener Management (Adapted for GUI) ---

mouse_listener = None
keyboard_listener = None

def update_status(message):
    if status_label:
        status_label.config(text=f"Status: {message}")
    print(f"Status: {message}") # Keep console output for debugging

def enable_buttons():
    record_button.config(state=tk.NORMAL)
    stop_record_button.config(state=tk.DISABLED) # Stop Record is disabled when not recording
    play_button.config(state=tk.NORMAL)
    stop_play_button.config(state=tk.DISABLED) # Stop Play is disabled when not playing
    save_button.config(state=tk.NORMAL)
    load_button.config(state=tk.NORMAL)

def disable_for_recording():
    record_button.config(state=tk.DISABLED)
    stop_record_button.config(state=tk.NORMAL)
    play_button.config(state=tk.DISABLED)
    stop_play_button.config(state=tk.DISABLED)
    save_button.config(state=tk.DISABLED)
    load_button.config(state=tk.DISABLED)

def disable_for_playback():
    record_button.config(state=tk.DISABLED)
    stop_record_button.config(state=tk.DISABLED)
    play_button.config(state=tk.DISABLED)
    stop_play_button.config(state=tk.NORMAL)
    save_button.config(state=tk.DISABLED)
    load_button.config(state=tk.DISABLED)


def start_recording():
    """Starts listening for mouse and keyboard events via GUI button."""
    global is_recording, recorded_events, recording_start_time, mouse_listener, keyboard_listener

    if is_recording:
        update_status("Already recording.")
        return
    if is_playing:
        update_status("Cannot start recording while playback is active. Stop playback first.")
        return

    recorded_events = [] # Clear previous recordings
    is_recording = True
    recording_start_time = time.time()
    update_status("Recording... Perform actions, then click 'Stop Recording'.")
    disable_for_recording()

    # Start listeners in separate threads to not block the GUI
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
    """Stops listening for mouse and keyboard events via GUI button."""
    global is_recording, mouse_listener, keyboard_listener

    if not is_recording:
        update_status("Not currently recording.")
        return

    is_recording = False
    update_status("Stopped recording.")
    enable_buttons() # Re-enable appropriate buttons

    if mouse_listener and mouse_listener.is_alive():
        mouse_listener.stop()
        mouse_listener.join()
    if keyboard_listener and keyboard_listener.is_alive():
        keyboard_listener.stop()
        keyboard_listener.join()
    
    # After stopping, automatically prompt to save (or save to default)
    save_recorded_events_gui()

def save_recorded_events_gui():
    """Saves the recorded events to a JSON file via GUI."""
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
    """Loads recorded events from a JSON file via GUI."""
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

# --- Playback Functionality (Adapted for GUI) ---

def play_recorded_macro():
    """Plays back the currently loaded recorded events via GUI button."""
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
    """Internal function to handle the actual event execution."""
    global is_playing

    # Set up pyautogui's default pause and failsafe
    pyautogui.PAUSE = 0.001 # Smallest possible pause between actions
    pyautogui.FAILSAFE = True # Re-enable failsafe for playback if not disabled specifically

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
        enable_buttons() # Re-enable appropriate buttons

def stop_playback():
    """Sets the flag to stop the currently running playback via GUI button."""
    global is_playing
    if is_playing:
        is_playing = False
        update_status("Playback stop requested.")
        # The _execute_playback thread will pick up the flag and stop itself
    else:
        update_status("No playback is currently active.")

# --- Hotkey for stopping Playback (F9) ---
# This listener runs in a background daemon thread to catch the F9 key
stop_playback_listener = None

def setup_playback_stop_listener():
    global stop_playback_listener
    def on_f9_release(key):
        # We check both is_playing and the key, and also ensure the main GUI thread is not locked up
        if is_playing and key == keyboard.Key.f9:
            print("F9 hotkey detected. Requesting playback stop.") # For console debug
            # Use root.after to safely call stop_playback in the main Tkinter thread
            if hasattr(setup_playback_stop_listener, 'root_instance'):
                setup_playback_stop_listener.root_instance.after(0, stop_playback)
            return False # Stop this specific listener iteration, but the thread keeps running for future F9 presses

    # Create a new listener each time this function is called, or ensure it's managed once
    if stop_playback_listener is None:
        stop_playback_listener = keyboard.Listener(on_release=on_f9_release)
        stop_playback_listener.start()
        # No .join() here, as this thread should run indefinitely in the background
        # It's a daemon thread, so it will exit when the main program exits.

# --- GUI Setup ---
def create_gui():
    global status_label, record_button, stop_record_button, play_button, stop_play_button, save_button, load_button

    root = tk.Tk()
    root.title("TinyTask for Mac")
    root.geometry("300x320") # Adjusted size
    root.resizable(False, False) # Prevent resizing

    # Make root_instance available for the F9 hotkey handler
    setup_playback_stop_listener.root_instance = root

    # Labels
    status_label = tk.Label(root, text="Status: Idle.", font=("Helvetica", 12), wraplength=280)
    status_label.pack(pady=10)

    # Buttons
    button_width = 20 # Standardized width for buttons

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

    # Start the F9 hotkey listener as a daemon thread
    # It only needs to be started once.
    if stop_playback_listener is None: # Only start if not already started
        hotkey_thread = threading.Thread(target=setup_playback_stop_listener)
        hotkey_thread.daemon = True
        hotkey_thread.start()
        print("Background F9 stop listener started.") # Console debug

    # Handle window closing to ensure listeners are stopped
    def on_closing():
        if is_recording:
            stop_recording() # This will also save
        if is_playing:
            stop_playback()
        # Give some time for threads to shut down
        time.sleep(0.5)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()

if __name__ == "__main__":
    print("Starting TinyTask GUI for Mac...")
    print("IMPORTANT: Ensure your Python environment or terminal has Accessibility and Input Monitoring permissions in System Settings.")
    create_gui()
