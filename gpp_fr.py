import os
import cv2
import face_recognition
import numpy as np
import time
import sqlite3
from PIL import Image
import io
from datetime import datetime
import platform

# Set the environment variable to use X11 instead of Wayland
#os.environ["QT_QPA_PLATFORM"] = "xcb"

VERSION = "1.6"
MODIFICATIONS = "Added automatic OS detection for video capture compatibility; Added window focus and topmost properties for face recognition window"

VERSION = "1.5.5"
MODIFICATIONS = "Added automatic OS detection for video capture compatibility"

def load_known_faces_from_db(db_path):
    known_face_encodings = []
    known_face_ids = []

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT persons.id, photos.photo_data FROM persons JOIN photos ON persons.id = photos.person_id")
    rows = c.fetchall()
    conn.close()

    current_id = None
    photo_count = 0

    for person_id, photo_data in rows:
        if current_id is None:
            current_id = person_id
            photo_count = 0

        if person_id != current_id:
            print(f"Person ID {current_id}: {photo_count} photos")
            current_id = person_id
            photo_count = 0

        image = Image.open(io.BytesIO(photo_data))
        image = image.convert("RGB")  # Ensure image is in RGB format
        image_np = np.array(image)
        face_encodings = face_recognition.face_encodings(image_np)
        if face_encodings:
            known_face_encodings.append(face_encodings[0])
            known_face_ids.append(person_id)
            photo_count += 1

    if current_id is not None:
        print(f"Person ID {current_id}: {photo_count} photos")

    return known_face_encodings, known_face_ids

def adjust_brightness(frame, alpha, beta):
    return cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)

def recognize_face(known_face_encodings, known_face_ids):
    # Detect operating system and use appropriate video capture method
    current_os = platform.system()
    
    if current_os == "Windows":
        video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # for Windows
    else:
        video_capture = cv2.VideoCapture(0)  # for Raspberry Pi and other Linux systems
    
    if not video_capture.isOpened():
        print(f"Error: Could not open video device on {current_os}.")
        return "Error"

    # Get screen resolution
    screen_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    screen_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Create the window with a unique name
    window_name = "Face Recognition System"
    cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    # Set window to be topmost (this works on Windows)
    if current_os == "Windows":
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    
    # Force window to front
    cv2.imshow(window_name, np.zeros((screen_height, screen_width, 3), dtype=np.uint8))
    cv2.waitKey(1)
    
    # For Linux/Raspberry Pi, we might need to use wmctrl if available
    if current_os == "Linux":
        try:
            import subprocess
            subprocess.run(['wmctrl', '-a', window_name], capture_output=True)
        except:
            pass  # wmctrl might not be installed

    # Connect to the database
    db_path = "people.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Failed to grab frame")
            continue

        # Resize frame to fit the screen dimensions
        frame = cv2.resize(frame, (screen_width, screen_height))

        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        recognized_id = None
        for face_encoding, face_location in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)

            if True in matches:  # Check if there is at least one match
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    recognized_id = str(known_face_ids[best_match_index])
            else:
                recognized_id = "Stranger"

            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top, right, bottom, left = face_location
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a green rectangle around the face for all cases
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        if recognized_id:
            if recognized_id == "Stranger":
                text = "Hello, Stranger"
            else:
                # Look up the person's name in the database
                c.execute("SELECT name FROM persons WHERE id = ?", (recognized_id,))
                result = c.fetchone()
                if result:
                    name = result[0]
                    text = f"Hello, {name}"
                else:
                    text = f"Hello, ID: {recognized_id}"

            font = cv2.FONT_HERSHEY_DUPLEX
            text_size = cv2.getTextSize(text, font, 1.5, 2)[0]
            text_x = (frame.shape[1] - text_size[0]) // 2
            text_y = 50
            cv2.putText(frame, text, (text_x, text_y), font, 1.5, (0, 255, 0), 2)
            
            cv2.imshow(window_name, frame)
            cv2.waitKey(500)  # Display for 0.5 seconds

            # Take a screenshot
            screenshot_filename = "face.jpg"
            cv2.imwrite(screenshot_filename, frame)
            print("Screenshot saved")

            # Flash the brightness 3 times
            for _ in range(3):
                dark_frame = adjust_brightness(frame, alpha=0.75, beta=0)
                cv2.imshow(window_name, dark_frame)
                cv2.waitKey(200)  # Display for 0.2 seconds

                bright_frame = adjust_brightness(frame, alpha=1.25, beta=0)
                cv2.imshow(window_name, bright_frame)
                cv2.waitKey(200)  # Display for 0.2 seconds

            if recognized_id == "Stranger":
                print("Stranger detected")
            else:
                print(f"Face recognized, Person ID: {recognized_id}, Name: {name}")
            
            conn.close()  # Close the database connection
            video_capture.release()
            cv2.destroyAllWindows()
            return recognized_id

        cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()
    conn.close()  # Ensure the database connection is closed if we exit the loop
    return None  # This should never be reached under normal circumstances

def main():
    print(f"Version: {VERSION}")
    print(f"Modifications: {MODIFICATIONS}")

    db_path = "people.db"

    known_face_encodings, known_face_ids = load_known_faces_from_db(db_path)

    recognized_id = recognize_face(known_face_encodings, known_face_ids)
    print(f"Result: {recognized_id}")

if __name__ == "__main__":
    main()