import os
import sqlite3
import hashlib
import pickle
from datetime import datetime
import configparser
import pandas as pd
import socket

from gpp_fr import recognize_face, load_known_faces_from_db
from KeybTO import create_keyboard
from TelegramButtons import telegram_button_handler

from Alarm_Off import alarm_off
from fullscreen_message import show_fullscreen_message

from ControlSwitch import control_shelly_switch
from Alarm_On import alarm_on

from translations import get_translations_cached as load_translations, get_message

#from pattern_metapixel import pattern_metapixel

VERSION = "1.6"
MODIFICATIONS = "class class FullScreenMessage: moved to a separate module fullscreen_message.py"

#VERSION = "1.5.1"
#MODIFICATIONS = "Fixed the sequence of translation table calls so that all elements are always displayed in the correct language"

#VERSION = "1.5"
#MODIFICATIONS = "Moved load_translations, get_message to a separate module. New function get_translations_cached for caching the translation table"

#VERSION = "1.4"
#MODIFICATIONS = "Fixed alarm setup screen to display in proper fullscreen; Added support for Russian and Hebrew translations; Modified gate opening sequence to use multiple short pulses instead of single long delay"

#VERSION = "1.3"
#MODIFICATIONS = "Fixed Russian and Hebrew translations"

#VERSION = "1.2"
#MODIFICATIONS = "Fixed alarm setup screen to display in proper fullscreen"

# Read configuration from gpp.ini
config = configparser.ConfigParser()
config.read('gpp.ini')

#import os
#os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = r'C:\Users\rlgle\anaconda3\envs\GP\Library\plugins\platforms'
#os.environ['QT_QPA_PLATFORM'] = 'windows'

DEFAULT_SYSTEM_LANGUAGE = "EN"

ip_arm = config['IP_adresses']['ip_arm'].strip('"')
ip_night = config['IP_adresses']['ip_night'].strip('"')
ip_off = config['IP_adresses']['ip_off'].strip('"')
ip_gate = config['IP_adresses']['ip_gate'].strip('"')
gate_delay = config['OpenGate']['gate_delay'].strip('"')
gate_open_short = int(config['OpenGate']['gate_open_short'].strip('"'))
gate_wait_short = int(config['OpenGate']['gate_wait_short'].strip('"'))

ENCODINGS_FILE = "known_face_encodings.pkl"
IDS_FILE = "known_face_ids.pkl"
DB_HASH_FILE = "db_hash.txt"
EVENTS_DB = "events.db"

class DatabaseConnection:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None

    def __enter__(self):
        self.connection = sqlite3.connect(self.db_path)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()

db_connection = DatabaseConnection('people.db')
events_db_connection = DatabaseConnection(EVENTS_DB)

def init_events_db():
    with events_db_connection as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS events
                     (date TEXT, time TEXT, picture BLOB, name TEXT, surname TEXT, action_code INTEGER)''')
        conn.commit()

def calculate_db_hash(db_path):
    hasher = hashlib.md5()
    with open(db_path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def save_cache(encodings, ids, db_hash):
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(encodings, f)
    with open(IDS_FILE, "wb") as f:
        pickle.dump(ids, f)
    with open(DB_HASH_FILE, "w") as f:
        f.write(db_hash)

def load_cache():
    with open(ENCODINGS_FILE, "rb") as f:
        encodings = pickle.load(f)
    with open(IDS_FILE, "rb") as f:
        ids = pickle.load(f)
    return encodings, ids

def load_db_hash():
    with open(DB_HASH_FILE, "r") as f:
        return f.read().strip()

def cache_exists():
    return os.path.exists(ENCODINGS_FILE) and os.path.exists(IDS_FILE) and os.path.exists(DB_HASH_FILE)

def load_face_encodings(db_path):
    known_face_encodings, known_face_ids = load_known_faces_from_db(db_path)
    db_hash = calculate_db_hash(db_path)
    save_cache(known_face_encodings, known_face_ids, db_hash)
    return known_face_encodings, known_face_ids

def preload_face_encodings(db_path):
    if not cache_exists():
        print("Cache files not found. Recalculating face encodings.")
        return load_face_encodings(db_path)
    else:
        stored_db_hash = load_db_hash()
        current_db_hash = calculate_db_hash(db_path)
        if stored_db_hash != current_db_hash:
            print("Database has changed. Recalculating face encodings.")
            return load_face_encodings(db_path)
        else:
            print("Loading face encodings from cache.")
            return load_cache()

def get_person_info(person_id):
    with db_connection as conn:
        c = conn.cursor()
        try:
            c.execute("SELECT name, surname, language FROM persons WHERE id = ?", (person_id,))
            result = c.fetchone()
            if result:
                return result
            else:
                print(f"No person found for ID: {person_id}")
                return None
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return None

def id_2_pass(person_id):
    with db_connection as conn:
        c = conn.cursor()
        try:
            c.execute("SELECT password_hash FROM persons WHERE id = ?", (person_id,))
            result = c.fetchone()
            if result:
                return result[0]
            else:
                print(f"No password hash found for person ID: {person_id}")
                return None
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return None

def get_stranger_info():
    with db_connection as conn:
        c = conn.cursor()
        try:
            c.execute("SELECT password_hash, language FROM persons WHERE name = ?", ("Stranger",))
            result = c.fetchone()
            if result:
                return result
            else:
                print("No 'Stranger' record found in database. Using default values.")
                return hashlib.sha256("1965".encode()).hexdigest(), "EN"
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return hashlib.sha256("1965".encode()).hexdigest(), "EN"

def log_event(date, time, picture, name, surname, action_code):
    with events_db_connection as conn:
        c = conn.cursor()
        c.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
                  (date, time, picture, name, surname, action_code))
        conn.commit()

def check_internet_connection(host="8.8.8.8", port=53, timeout=3):
    """
    Check if there is an active Internet connection by attempting
    to connect to a well-known DNS server (e.g., Google's 8.8.8.8).
    
    Args:
    host (str): Target host to connect (default is 8.8.8.8)
    port (int): Port number to connect (default is 53, DNS service)
    timeout (int): Timeout in seconds before connection attempt times out
    
    Returns:
    bool: True if the connection is successful, False otherwise
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        return False


def main():
    print(f"Gate Project System Version: {VERSION}")
    print(f"Modifications: {MODIFICATIONS}")

    init_events_db()

    print("Preloading face encodings...")
    known_face_encodings, known_face_ids = preload_face_encodings('people.db')
    
    print("Face encodings loaded. Starting main loop...")

    while True:
        # Use system default language for initial messages
        system_translations = load_translations('gate_project_translations.md', DEFAULT_SYSTEM_LANGUAGE)
        show_fullscreen_message(get_message(1, system_translations))  # Welcome message
        
#        result = pattern_metapixel()
#
#        if result != 0:
#            show_fullscreen_message(get_message(2, system_translations))  # Problem with message display
#            break

        show_fullscreen_message(get_message(3, system_translations))  # Initializing face recognition...
        recognized_id = recognize_face(known_face_encodings, known_face_ids)
        
        print(f"Recognition result: {recognized_id}")

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")

        if recognized_id is None:
            show_fullscreen_message(get_message(4, system_translations))  # No face detected...
            continue
        # NOW determine the user's language and load their translations
        if recognized_id == "Stranger":
            stranger_password_hash, user_lang = get_stranger_info()
            # If stranger has no language set, use system default
            if user_lang is None or user_lang == "":
                user_lang = DEFAULT_SYSTEM_LANGUAGE
            translations = load_translations('gate_project_translations.md', user_lang)
            show_fullscreen_message(get_message(5, translations))  # Face detected. Please wait...
            message = get_message(31, translations)  # Unrecognized person at the main gate
            password_hash = stranger_password_hash
            ping_message = get_message(32, translations)  # You have been pinged by an unrecognized person!
            name = "Unrecognized"
            surname = "Person"
            user_name = "Stranger"  # Set user_name for unrecognized person
            send_picture = True
        else:
            person_info = get_person_info(recognized_id)
            if person_info:
                name, surname, user_lang = person_info
                # If person has no language set, use system default
                if user_lang is None or user_lang == "":
                    user_lang = DEFAULT_SYSTEM_LANGUAGE
                translations = load_translations('gate_project_translations.md', user_lang)
                show_fullscreen_message(get_message(5, translations))  # Face detected. Please wait...
                message = f"{name} {surname} {get_message(35, translations)}"  # is at the gate
                password_hash = id_2_pass(recognized_id)
                ping_message = f"{get_message(34, translations)} {name} {surname}!"  # You have been pinged by
                user_name = name  # Set user_name to only the first name
                #send_picture = False
                send_picture = True
            else:
                stranger_password_hash, user_lang = get_stranger_info()
                # If no language info, use system default
                if user_lang is None or user_lang == "":
                    user_lang = DEFAULT_SYSTEM_LANGUAGE
                translations = load_translations('gate_project_translations.md', user_lang)
                show_fullscreen_message(get_message(5, translations))  # Face detected. Please wait...
                message = get_message(36, translations)  # Unknown person at the main gate
                password_hash = stranger_password_hash
                ping_message = get_message(37, translations)  # You have been pinged by an unknown person!
                name = "Unknown"
                surname = "Unknown"
                user_name = "Unknown"  # Set user_name for unknown person
                send_picture = True
                
        if not check_internet_connection(host="8.8.8.8", port=53, timeout=3):
            # Use the current language for error message
            error_translations = translations if 'translations' in locals() else system_translations
            show_fullscreen_message(get_message(38, error_translations) if 38 in error_translations else "No internet connection. Cannot proceed", 5)
            continue
            
            
        if send_picture:
            telegram_button_handler(message, "face.jpg", buttons=False, user_lang=user_lang)
        else:
            telegram_button_handler(message, None, buttons=False, user_lang=user_lang)

        max_attempts = 3
        keyboard_result = create_keyboard(password_hash, max_attempts, user_lang, user_name)

        if keyboard_result == -100:
            show_fullscreen_message(get_message(2, translations))  # Problem with message display
            break

        action_code = keyboard_result

        if keyboard_result == 1:  # Correct password provided
            print("Keyboard result = 1")
            show_fullscreen_message(get_message(6, translations))  # Switching off alarm...
            alarm_result = alarm_off(user_lang)
            if alarm_result == 1:
                try:
                    # First gate opening signal
                    control_shelly_switch(ip_gate)
                    # Show opening gate message for gate_open_short seconds
                    show_fullscreen_message(get_message(7, translations), gate_open_short)  # Opening gate...
                    # Second gate opening signal
                    control_shelly_switch(ip_gate)
                    # Show the message again while waiting gate_wait_short seconds
                    show_fullscreen_message(get_message(7, translations), gate_wait_short)  # Opening gate...
                    # Third gate opening signal
                    control_shelly_switch(ip_gate)
                except Exception as e:
                    show_fullscreen_message(f"{get_message(8, translations)} {e}")  # Error opening gate:
            else:
                show_fullscreen_message(get_message(9, translations))  # Failed to switch off the alarm
            action_code = 1  # Correct password
        elif keyboard_result == 11:  # Set alarm (Day mode)
            show_fullscreen_message(get_message(10, translations))  # Switching on alarm (Day mode)...
            alarm_result = alarm_on(False, user_lang)
        elif keyboard_result == 12:  # Set alarm (Night mode)
            show_fullscreen_message(get_message(11, translations))  # Switching on alarm (Night mode)...
            alarm_result = alarm_on(True, user_lang)
        elif keyboard_result == 10:  # Turn off alarm
            show_fullscreen_message(get_message(6, translations))  # Switching off alarm...
            alarm_result = alarm_off(user_lang)
            print("Alarm successfully switched off")
            show_fullscreen_message(get_message(24, translations),1)  # Alarm successfully  switched off ...
            print("Alarm switched off by command")
        elif keyboard_result == 0:  # Ping Lev button pressed
            show_fullscreen_message(get_message(12, translations))  # Pinging Lev...
            ping_result = telegram_button_handler(ping_message, "face.jpg", buttons=True, user_lang=user_lang)
            
            if ping_result == "+1":
                action_code = 2  # Ping Lev - Open Gate
                show_fullscreen_message(get_message(6, translations))  # Switching off alarm...
                alarm_result = alarm_off(user_lang)
                if alarm_result == 1:
                    try:
                        # First gate opening signal
                        control_shelly_switch(ip_gate)
                        # Show opening gate message for gate_open_short seconds
                        show_fullscreen_message(get_message(7, translations), gate_open_short)  # Opening gate...
                        # Second gate opening signal
                        control_shelly_switch(ip_gate)
                        # Show the message again while waiting gate_wait_short seconds
                        show_fullscreen_message(get_message(7, translations), gate_wait_short)  # Opening gate...
                        # Third gate opening signal
                        control_shelly_switch(ip_gate)
                    except Exception as e:
                        show_fullscreen_message(f"{get_message(8, translations)} {e}")  # Error opening gate:
                else:
                    show_fullscreen_message(get_message(9, translations))  # Failed to switch off the alarm
            elif ping_result == "-1":
                action_code = 3  # Ping Lev - Cancel
                show_fullscreen_message(get_message(13, translations), 7)  # Sorry, but you are not authorized...
            else:
                action_code = 4  # Ping Lev - Time-out
                show_fullscreen_message(get_message(14, translations), 7)  # Sorry, but Lev is not available...

        with open("face.jpg", "rb") as image_file:
            image_data = image_file.read()
        log_event(current_date, current_time, image_data, name, surname, action_code)

    print("Program completed.")

if __name__ == "__main__":
    main()