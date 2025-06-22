# (c) EXB Studios - An Amajei Global Inc. Company, 2025. All rights reserved. See /Copyright/ for more info.
import time
from pynput import mouse, keyboard
import json
import threading

# --- Global Variables ---
# List to store all recorded events
recorded_events = []
# Flag to control recording state
is_recording = False
# To calculate relative timestamps for playback accuracy
recording_start_time = 0

# --- Event Handlers (Functions that get called when an input event occurs) ---

def on_mouse_click(x, y, button, pressed):
    """Callback for mouse click events."""
    global recorded_events, is_recording, recording_start_time
    if is_recording:
        event_type = "mouse_click"
        timestamp = time.time() - recording_start_time
        # Store whether the button was pressed down or released up
        recorded_events.append({
            "type": event_type,
            "x": x,
            "y": y,
            "button": str(button),  # Convert button object to string (e.g., "Button.left")
            "pressed": pressed,
            "time": timestamp
        })
        print(f"[REC] Click: ({x}, {y}) {button} {'Pressed' if pressed else 'Released'} @ {timestamp:.3f}s")

def on_mouse_move(x, y):
    """Callback for mouse movement events."""
    global recorded_events, is_recording, recording_start_time
    if is_recording:
        event_type = "mouse_move"
        timestamp = time.time() - recording_start_time
        # Only record if the mouse has moved a significant distance
        # or if it's the first move event after a non-move event.
        # This reduces redundant data for small jitters.
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
            # print(f"[REC] Move: ({x}, {y}) @ {timestamp:.3f}s") # Uncomment for verbose move logging

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
            "dx": dx, # Horizontal scroll amount
            "dy": dy, # Vertical scroll amount
            "time": timestamp
        })
        print(f"[REC] Scroll: ({x}, {y}) dx={dx}, dy={dy} @ {timestamp:.3f}s")

def on_key_press(key):
    """Callback for keyboard key press events."""
    global recorded_events, is_recording, recording_start_time
    if is_recording:
        event_type = "key_press"
        timestamp = time.time() - recording_start_time
        try:
            # Handle alphanumeric keys (e.g., 'a', '1')
            char = key.char
        except AttributeError:
            # Handle special keys (e.g., Key.space, Key.ctrl_l)
            char = str(key)
        recorded_events.append({
            "type": event_type,
            "key": char,
            "time": timestamp
        })
        print(f"[REC] Key Press: {char} @ {timestamp:.3f}s")

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
        print(f"[REC] Key Release: {char} @ {timestamp:.3f}s")
        
        # --- Stopping Recording with a Hotkey ---
        # For simplicity, let's use 'esc' key release to stop recording.
        # In a GUI app, you'd use a button.
        if key == keyboard.Key.esc:
            print("\nESC key released. Stopping recording...")
            stop_recording_listeners()
            return False # Stop the keyboard listener


# --- Listener Management ---

# We'll keep references to the listeners so we can stop them later
mouse_listener = None
keyboard_listener = None

def start_recording_listeners():
    """Starts listening for mouse and keyboard events."""
    global is_recording, recorded_events, recording_start_time, mouse_listener, keyboard_listener

    if is_recording:
        print("Already recording.")
        return

    recorded_events = [] # Clear previous recordings
    is_recording = True
    recording_start_time = time.time()
    print("\n--- Recording Started ---")
    print("Press ESC key to stop recording and save.")
    print("Performing actions now...\n")

    # Start mouse listener in a non-blocking way
    mouse_listener = mouse.Listener(
        on_click=on_mouse_click,
        on_move=on_mouse_move,
        on_scroll=on_mouse_scroll
    )
    mouse_listener.start() # start() runs the listener in a separate thread

    # Start keyboard listener in a non-blocking way
    keyboard_listener = keyboard.Listener(
        on_press=on_key_press,
        on_release=on_key_release
    )
    keyboard_listener.start() # start() runs the listener in a separate thread

def stop_recording_listeners():
    """Stops listening for mouse and keyboard events."""
    global is_recording, mouse_listener, keyboard_listener

    if not is_recording:
        print("Not currently recording.")
        return

    is_recording = False
    print("\n--- Recording Stopped ---")

    if mouse_listener and mouse_listener.is_alive():
        mouse_listener.stop()
        mouse_listener.join() # Wait for the listener thread to finish
        print("Mouse listener stopped.")

    if keyboard_listener and keyboard_listener.is_alive():
        keyboard_listener.stop()
        keyboard_listener.join() # Wait for the listener thread to finish
        print("Keyboard listener stopped.")
    
    # Save the recorded events to a JSON file
    save_recorded_events("my_macro.json")

def save_recorded_events(filename="macro_events.json"):
    """Saves the recorded events to a JSON file."""
    if recorded_events:
        try:
            with open(filename, 'w') as f:
                json.dump(recorded_events, f, indent=4)
            print(f"Recorded {len(recorded_events)} events. Saved to '{filename}'")
        except Exception as e:
            print(f"Error saving events to '{filename}': {e}")
    else:
        print("No events to save.")

# --- Main execution block ---
if __name__ == "__main__":
    print("Welcome to the Macro Recorder (Step 1)")
    print("Ensure your Python environment/Terminal has Accessibility permissions.")
    print("Ready to record. The recording will start immediately.")
    print("Perform your actions, then press the 'ESC' key to stop recording.")

    # Start the recording process
    start_recording_listeners()

    # The main thread will now wait for the listeners to finish (which they won't
    # until the ESC key is pressed or the program is manually terminated).
    # This prevents the script from exiting immediately while listeners are in background threads.
    # We could also use a simple input() or a while loop for a more controlled exit.
    # For now, the `keyboard.Listener`'s `on_release` handler for ESC will stop them.
    # We add a small delay to allow listeners to properly start before exiting the main thread.
    try:
        while is_recording:
            time.sleep(0.1) # Keep main thread alive while recording
    except KeyboardInterrupt:
        print("\nProgram interrupted by user (Ctrl+C). Stopping recording.")
        stop_recording_listeners()

    print("Exiting Macro Recorder.")
