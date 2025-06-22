import time
from pynput import mouse, keyboard
import json
import threading
import pyautogui # <-- New import!

# --- Global Variables ---
recorded_events = []
is_recording = False
recording_start_time = 0
is_playing = False # <-- New flag for playback state

# --- Event Handlers (from Step 1, unchanged) ---

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
        print(f"[REC] Click: ({x}, {y}) {button} {'Pressed' if pressed else 'Released'} @ {timestamp:.3f}s")

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
            # print(f"[REC] Move: ({x}, {y}) @ {timestamp:.3f}s")

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
        print(f"[REC] Scroll: ({x}, {y}) dx={dx}, dy={dy} @ {timestamp:.3f}s")

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
        
        # --- Hotkey to Stop Recording (ESC) ---
        if key == keyboard.Key.esc:
            print("\nESC key released. Stopping recording...")
            stop_recording_listeners()
            return False # Stop the keyboard listener


# --- Listener Management (from Step 1, with minor changes) ---

mouse_listener = None
keyboard_listener = None

def start_recording_listeners():
    """Starts listening for mouse and keyboard events."""
    global is_recording, recorded_events, recording_start_time, mouse_listener, keyboard_listener

    if is_recording:
        print("Already recording.")
        return
    if is_playing: # Prevent recording while playing
        print("Cannot start recording while playback is active. Stop playback first.")
        return

    recorded_events = []
    is_recording = True
    recording_start_time = time.time()
    print("\n--- Recording Started ---")
    print("Press ESC key to stop recording and save 'my_macro.json'.")
    print("Performing actions now...\n")

    mouse_listener = mouse.Listener(
        on_click=on_mouse_click,
        on_move=on_mouse_move,
        on_scroll=on_mouse_scroll
    )
    mouse_listener.start()

    keyboard_listener = keyboard.Listener(
        on_press=on_key_press,
        on_release=on_key_release
    )
    keyboard_listener.start()

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
        mouse_listener.join()
        print("Mouse listener stopped.")

    if keyboard_listener and keyboard_listener.is_alive():
        keyboard_listener.stop()
        keyboard_listener.join()
        print("Keyboard listener stopped.")
    
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

# --- NEW: Playback Functionality ---

def load_recorded_events(filename="my_macro.json"):
    """Loads recorded events from a JSON file."""
    global recorded_events
    try:
        with open(filename, 'r') as f:
            loaded_events = json.load(f)
            # Basic validation: Check if events have 'type' and 'time' keys
            if all(isinstance(e, dict) and "type" in e and "time" in e for e in loaded_events):
                recorded_events = loaded_events
                print(f"Successfully loaded {len(recorded_events)} events from '{filename}'.")
                return True
            else:
                print(f"Error: Invalid event format in '{filename}'.")
                return False
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found. Please record a macro first.")
        return False
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{filename}'.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while loading '{filename}': {e}")
        return False

def play_recorded_macro():
    """Plays back the currently loaded recorded events."""
    global is_playing, recorded_events

    if not recorded_events:
        print("No events loaded to play. Load a macro first!")
        return

    if is_playing:
        print("Playback is already active.")
        return
    
    if is_recording: # Prevent playing while recording
        print("Cannot start playback while recording is active. Stop recording first.")
        return

    is_playing = True
    print("\n--- Playback Started ---")
    print("Press F9 to STOP playback.") # Define a hotkey to stop playback (more on this below)

    # Use a separate thread for playback to keep the main script responsive
    playback_thread = threading.Thread(target=_execute_playback)
    playback_thread.daemon = True # Allow the main program to exit even if thread is running
    playback_thread.start()

def _execute_playback():
    """Internal function to handle the actual event execution."""
    global is_playing

    pyautogui.FAILSAFE = False # Disable failsafe for now. Be careful!
                               # In a real app, you might want to re-enable/manage this.
                               # Failsafe is good for development to stop runaway macros.
                               # pyautogui.FAILSAFE = True will stop if mouse is moved to top-left corner.

    last_event_time = 0
    try:
        for event in recorded_events:
            if not is_playing: # Check the flag to allow stopping playback mid-way
                print("Playback interrupted.")
                break

            # Calculate time to wait based on relative timestamps
            time_to_wait = event["time"] - last_event_time
            if time_to_wait > 0:
                time.sleep(time_to_wait)

            if event["type"] == "mouse_click":
                # pyautogui.click performs both mouseDown and mouseUp
                # We need to simulate the individual pressed/released states for accuracy
                button_name = event["button"].replace("Button.", "").lower()
                if event["pressed"]:
                    pyautogui.mouseDown(event["x"], event["y"], button=button_name)
                    print(f"[PLAY] Mouse Down: ({event['x']}, {event['y']}) {button_name}")
                else:
                    pyautogui.mouseUp(event["x"], event["y"], button=button_name)
                    print(f"[PLAY] Mouse Up: ({event['x']}, {event['y']}) {button_name}")

            elif event["type"] == "mouse_move":
                # pyautogui.moveTo can take a duration for smooth movement
                # For recorded macros, usually instant movement is desired unless duration was recorded.
                pyautogui.moveTo(event["x"], event["y"], _pause=False) # _pause=False prevents pyautogui's default 0.1s pause
                # print(f"[PLAY] Mouse Move: ({event['x']}, {event['y']})")

            elif event["type"] == "mouse_scroll":
                # pyautogui.scroll takes integer steps
                # dy is vertical scroll, dx is horizontal (less common for scroll wheel)
                scroll_amount = int(event["dy"]) # positive for up, negative for down
                pyautogui.scroll(scroll_amount, x=event["x"], y=event["y"])
                print(f"[PLAY] Mouse Scroll: ({event['x']}, {event['y']}) dy={scroll_amount}")

            elif event["type"] == "key_press":
                key_to_press = event["key"]
                # pyautogui.keyDown handles special keys (e.g., 'alt', 'shift') as strings
                # pynput gives 'Key.ctrl_l', so convert if necessary
                if key_to_press.startswith('Key.'):
                    key_to_press = key_to_press.split('Key.')[1].lower()
                pyautogui.keyDown(key_to_press, _pause=False)
                print(f"[PLAY] Key Down: {key_to_press}")

            elif event["type"] == "key_release":
                key_to_release = event["key"]
                if key_to_release.startswith('Key.'):
                    key_to_release = key_to_release.split('Key.')[1].lower()
                pyautogui.keyUp(key_to_release, _pause=False)
                print(f"[PLAY] Key Up: {key_to_release}")
            
            last_event_time = event["time"]

    except Exception as e:
        print(f"An error occurred during playback: {e}")
    finally:
        is_playing = False
        pyautogui.FAILSAFE = True # Re-enable failsafe after playback
        print("\n--- Playback Finished ---")

# --- Hotkey for stopping Playback (F9) ---
# We need a separate listener specifically for the F9 key to stop playback
# This listener runs in the background.

stop_playback_listener = None
def setup_playback_stop_listener():
    global stop_playback_listener
    def on_f9_release(key):
        if is_playing and key == keyboard.Key.f9:
            print("\nF9 key released. Stopping playback...")
            stop_playback()
            # return False # Don't stop this listener, it needs to stay active for future playbacks
    
    stop_playback_listener = keyboard.Listener(on_release=on_f9_release)
    stop_playback_listener.start()
    stop_playback_listener.join() # This will block, so we'll run it in a thread later

def stop_playback():
    """Sets the flag to stop the currently running playback."""
    global is_playing
    if is_playing:
        is_playing = False
        print("Playback stop requested.")
    else:
        print("No playback is currently active.")

# --- Main execution block ---
if __name__ == "__main__":
    print("Welcome to the Macro Recorder/Player (Step 2)")
    print("Ensure your Python environment/Terminal has Accessibility permissions.")
    print("\nCommands:")
    print("  'rec'   - Start recording (then press ESC to stop and save 'my_macro.json')")
    print("  'play'  - Load 'my_macro.json' and start playback (then press F9 to stop playback)")
    print("  'load'  - Load 'my_macro.json' without playing")
    print("  'exit'  - Exit the program")

    # Start the global F9 listener in a separate daemon thread
    # This listener should always be active to catch the stop hotkey
    stop_listener_thread = threading.Thread(target=setup_playback_stop_listener)
    stop_listener_thread.daemon = True # Make it a daemon so it exits with the main program
    stop_listener_thread.start()
    print("Background F9 stop listener started.")

    while True:
        command = input("\nEnter command: ").lower().strip()

        if command == "rec":
            start_recording_listeners()
            # Recording listeners will run in their own threads.
            # The main loop continues, but the `is_recording` flag
            # prevents other actions until recording is stopped.
            # We need to wait for recording to truly finish.
            while is_recording:
                time.sleep(0.1) # Keep main thread alive while recording is active
            
        elif command == "play":
            # Before playing, attempt to load the default macro file
            if not recorded_events: # Only load if no events are currently loaded
                load_success = load_recorded_events("my_macro.json")
                if not load_success:
                    continue # Skip playback if loading failed
            play_recorded_macro()
            # Playback runs in its own thread, main loop continues.
            # We don't need to wait here, as `is_playing` manages state.

        elif command == "load":
            load_recorded_events("my_macro.json")

        elif command == "exit":
            print("Exiting program.")
            if is_recording:
                stop_recording_listeners()
            if is_playing:
                stop_playback()
            # Give a moment for threads to clean up
            time.sleep(0.5) 
            break
        else:
            print("Unknown command. Please use 'rec', 'play', 'load', or 'exit'.")

# git tst set - fcph due dec25
