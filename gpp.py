# ==============================================================================
# VERSION 2.0.2 CHANGES
#
# - Implemented a hybrid two-phase face recognition model (HOG -> CNN).
# - Stage 1 uses the fast 'hog' model to detect potential faces on every frame.
#   This keeps the system responsive and provides a visual cue (yellow box).
# - Stage 2 triggers the accurate but slow 'cnn' model only after a face
#   has been stable in the frame for a short duration.
# - This approach balances performance and accuracy, preventing both false
#   positives on objects and misidentification due to motion blur, which
#   is ideal for embedded systems like the Raspberry Pi.
# - Optimized by further reducing the processing frame resolution.
# ==============================================================================

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import pygame
import cv2
import face_recognition
import numpy as np
import time
import sqlite3
import hashlib
import pickle
from datetime import datetime
import configparser
import pandas as pd
import socket
import threading
from PIL import Image
import io
import platform

from translations import get_translations_cached as load_translations, get_message
from TelegramButtons import telegram_button_handler
from ControlSwitch import control_shelly_switch

VERSION = "2.0.2"
MODIFICATIONS = "Using mixed HOG->CNN model for performance and accuracy"

# Read configuration
config = configparser.ConfigParser()
config.read('gpp.ini')

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

class UnifiedGateSystem:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.screen_width, self.screen_height = self.screen.get_size()
        pygame.display.set_caption("Gate Project System")
        
        # Colors
        self.bg_color = (44, 62, 80)
        self.text_color = (236, 240, 241)
        
        # Fonts cache
        self.font_cache = {}
        
        # Face recognition data
        self.known_face_encodings = []
        self.known_face_ids = []
        
        # Camera
        self.video_capture = None
        self.init_camera()
        
        # Clock for FPS control
        self.clock = pygame.time.Clock()
        
        # Database connections
        self.init_databases()
        
    def init_camera(self):
        """Initialize camera with platform-specific settings"""
        current_os = platform.system()
        print(f"Running on {current_os}")
        
        if current_os == "Windows":
            self.video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        else:
            self.video_capture = cv2.VideoCapture(0)
        
        if not self.video_capture.isOpened():
            print(f"Error: Could not open video device on {current_os}.")
            return False
        
        # Get camera resolution
        self.cam_width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.cam_height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Camera resolution: {self.cam_width}x{self.cam_height}")
        return True
    
    def init_databases(self):
        """Initialize database connections"""
        # Events database
        conn = sqlite3.connect(EVENTS_DB)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS events
                     (date TEXT, time TEXT, picture BLOB, name TEXT, surname TEXT, action_code INTEGER)''')
        conn.commit()
        conn.close()
    
    def get_font(self, size):
        """Get or create font with caching"""
        cache_key = f"universal_{size}"
        
        if cache_key not in self.font_cache:
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            ]
            
            font_loaded = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        self.font_cache[cache_key] = pygame.font.Font(font_path, size)
                        font_loaded = True
                        break
                    except:
                        continue
            
            if not font_loaded:
                self.font_cache[cache_key] = pygame.font.Font(None, size)
                    
        return self.font_cache[cache_key]
    
    def show_message(self, message, duration=0):
        """Show fullscreen message"""
        self.screen.fill(self.bg_color)
        font_size = self.calculate_font_size(message)
        font = self.get_font(font_size)
        
        lines = self.text_wrap(message, font, self.screen_width * 0.8)
        y = self.screen_height // 2 - (len(lines) * font.get_linesize()) // 2

        for line in lines:
            text_surface = font.render(line, True, self.text_color)
            text_rect = text_surface.get_rect(center=(self.screen_width // 2, y))
            self.screen.blit(text_surface, text_rect)
            y += font.get_linesize()

        pygame.display.flip()

        if duration > 0:
            pygame.time.wait(int(duration * 1000))
    
    def calculate_font_size(self, message):
        """Calculate optimal font size for message"""
        target_height = self.screen_height * 0.5
        max_font_size = self.screen_height // 4
        
        for font_size in range(max_font_size, 10, -1):
            font = self.get_font(font_size)
            lines = self.text_wrap(message, font, self.screen_width * 0.8)
            total_height = font.get_linesize() * len(lines)
            
            if total_height <= target_height:
                return font_size
        
        return 10
    
    def text_wrap(self, text, font, max_width):
        """Wrap text to fit within max_width"""
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        return lines
    
    def pattern_metapixel(self):
        """Show pattern (placeholder)"""
        return 0
    
    def face_recognition_loop(self):
        """
        Face recognition loop with a two-phase (HOG -> CNN) approach for performance and reliability.
        1. Fast 'hog' model runs on every frame to detect potential faces.
        2. Once a face is stable for a moment, the accurate 'cnn' model is triggered
           for a high-quality recognition to prevent misidentification of partial faces.
        """
        help_text_it_line1 = "Posiziona il tuo viso"
        help_text_it_line2 = "davanti alla telecamera"
        help_text_en_line1 = "Please position your face"
        help_text_en_line2 = "in front of the camera"
        
        help_text_it_closer = "Avvicinati alla telecamera"
        help_text_en_closer = "Please come closer to the camera"

        font = self.get_font(int(self.screen_height / 30))
        name_font = self.get_font(int(self.screen_height / 20))
        
        recognition_candidate_time = None
        CONFIRMATION_DELAY = 0.7  # Delay in seconds for face stabilization
        
        # Optimization: Reduce the frame resolution further to increase speed.
        # Note: fx/fy is now 0.2, so coordinates must be scaled back up by a factor of 5.
        RESIZE_FACTOR = 0.2
        SCALE_UP_FACTOR = 1 / RESIZE_FACTOR

        # Clear camera buffer
        for _ in range(10):
            if self.video_capture.isOpened():
                self.video_capture.read()
        
        while True:
            ret, frame = self.video_capture.read()
            if not ret:
                continue
            
            frame = self.scale_frame_to_screen(frame)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # A smaller frame for analysis
            small_frame = cv2.resize(rgb_frame, (0, 0), fx=RESIZE_FACTOR, fy=RESIZE_FACTOR)
            
            # STAGE 1: Fast detection with HOG on every frame
            hog_face_locations = face_recognition.face_locations(small_frame, model='hog')
            
            frame_surface = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
            self.screen.blit(frame_surface, (0, 0))

            if not hog_face_locations:
                # If no faces are found, reset the timer and show the help message
                recognition_candidate_time = None
                center_y = self.screen_height // 2; line_spacing = 35
                text_surface = font.render(help_text_it_line1, True, (255, 255, 255)); text_rect = text_surface.get_rect(center=(self.screen_width // 2, center_y - line_spacing * 2)); self.screen.blit(text_surface, text_rect)
                text_surface = font.render(help_text_it_line2, True, (255, 255, 255)); text_rect = text_surface.get_rect(center=(self.screen_width // 2, center_y - line_spacing)); self.screen.blit(text_surface, text_rect)
                text_surface = font.render(help_text_en_line1, True, (200, 200, 200)); text_rect = text_surface.get_rect(center=(self.screen_width // 2, center_y + line_spacing)); self.screen.blit(text_surface, text_rect)
                text_surface = font.render(help_text_en_line2, True, (200, 200, 200)); text_rect = text_surface.get_rect(center=(self.screen_width // 2, center_y + line_spacing * 2)); self.screen.blit(text_surface, text_rect)
            else:
                # Face found! Draw a yellow "pending" box
                for (top, right, bottom, left) in hog_face_locations:
                    top *= SCALE_UP_FACTOR; right *= SCALE_UP_FACTOR; bottom *= SCALE_UP_FACTOR; left *= SCALE_UP_FACTOR
                    pygame.draw.rect(self.screen, (255, 255, 0), (left, top, right - left, bottom - top), 2)

                # Check if this is the first time the face is detected
                if recognition_candidate_time is None:
                    recognition_candidate_time = time.time()

                # If the face has been stable in the frame for long enough
                if time.time() - recognition_candidate_time > CONFIRMATION_DELAY:
                    # STAGE 2: Trigger the accurate but slow CNN recognition
                    
                    # Display a "Scanning..." message
                    scan_text_surface = name_font.render("Scanning...", True, (0, 255, 0))
                    scan_text_rect = scan_text_surface.get_rect(center=(self.screen_width // 2, 50))
                    self.screen.blit(scan_text_surface, scan_text_rect)
                    pygame.display.flip()

                    # Use CNN for the final, precise location
                    cnn_face_locations = face_recognition.face_locations(small_frame, model='cnn')
                    
                    if not cnn_face_locations:
                        # If CNN finds no face (HOG was wrong), reset the timer
                        recognition_candidate_time = None
                        continue

                    face_encodings = face_recognition.face_encodings(small_frame, cnn_face_locations)
                    face_encoding = face_encodings[0] # Take the first face found
                    
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.5)
                    recognized_id = "Stranger"
                    if True in matches:
                        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            recognized_id = str(self.known_face_ids[best_match_index])
                    
                    if recognized_id:
                        (top, right, bottom, left) = cnn_face_locations[0]
                        top *= SCALE_UP_FACTOR; right *= SCALE_UP_FACTOR; bottom *= SCALE_UP_FACTOR; left *= SCALE_UP_FACTOR
                        pygame.draw.rect(self.screen, (0, 255, 0), (left, top, right - left, bottom - top), 2)
                        
                        if recognized_id == "Stranger": text = "Hello, Stranger"
                        else:
                            conn = sqlite3.connect('people.db'); c = conn.cursor()
                            c.execute("SELECT name FROM persons WHERE id = ?", (recognized_id,)); result = c.fetchone(); conn.close()
                            if result: text = f"Hello, {result[0]}"
                            else: text = f"Hello, ID: {recognized_id}"
                        
                        text_surface = name_font.render(text, True, (0, 255, 0))
                        text_rect = text_surface.get_rect(center=(self.screen_width // 2, 50))
                        self.screen.blit(text_surface, text_rect)
                        pygame.display.flip()
                        pygame.time.wait(1000)
                        
                        pygame.image.save(self.screen, "face.jpg")
                        
                        for _ in range(3):
                            brightness = pygame.Surface((self.screen_width, self.screen_height)); brightness.set_alpha(64); brightness.fill((0, 0, 0)); self.screen.blit(brightness, (0, 0)); pygame.display.flip(); pygame.time.wait(200)
                            self.screen.blit(frame_surface, (0, 0)); pygame.draw.rect(self.screen, (0, 255, 0), (left, top, right - left, bottom - top), 2); self.screen.blit(text_surface, text_rect); pygame.display.flip(); pygame.time.wait(200)
                        
                        for _ in range(5):
                            if self.video_capture.isOpened(): self.video_capture.read()
                        
                        return recognized_id

            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
                    return None
            
            self.clock.tick(30)
    
    def scale_frame_to_screen(self, frame):
        """Scale camera frame to fit screen"""
        cam_aspect = self.cam_width / self.cam_height
        screen_aspect = self.screen_width / self.screen_height
        
        if cam_aspect > screen_aspect:
            new_width = int(self.cam_height * screen_aspect)
            crop_x = (self.cam_width - new_width) // 2
            frame = frame[:, crop_x:crop_x + new_width]
            frame = cv2.resize(frame, (self.screen_width, self.screen_height))
        else:
            new_height = int(self.cam_width / screen_aspect)
            crop_y = (self.cam_height - new_height) // 2
            frame = frame[crop_y:crop_y + new_height, :]
            frame = cv2.resize(frame, (self.screen_width, self.screen_height))
        
        return frame
    
    def show_keyboard(self, password_hash, max_attempts, user_lang, user_name):
        """Show keyboard using pygame"""
        translations = load_translations('gate_project_translations.md', user_lang)
        
        pygame.mouse.set_visible(False)
        
        # Keyboard state
        entered_code = ""
        attempts = max_attempts
        last_interaction_time = time.time()
        n_to = int(config['Time-Outs']['to_keyb'])
        
        # Create button layout
        buttons = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['*', '0', get_message(31, translations)],  # Delete
            [get_message(33, translations), get_message(34, translations), get_message(32, translations)]  # Cancel, Ping, Enter
        ]
        
        button_width = self.screen_width // 3
        button_height = self.screen_height // 6
        header_height = self.screen_height // 6
        
        # Fonts - match original sizes
        message_font_size = int(self.screen_height / 30)
        user_name_font_size = int(message_font_size * 1.6)
        countdown_font_size = int((self.screen_height / 50) * 1.5)
        
        button_font = self.get_font(int(self.screen_height / 16))
        message_font = self.get_font(message_font_size)
        user_name_font = self.get_font(user_name_font_size)
        countdown_font = self.get_font(countdown_font_size)
        code_font = button_font  # Code display uses same font as buttons
        
        # Colors from original
        message_color = (25, 118, 210)  # '#1976D2'
        user_name_color = (244, 67, 54)  # '#F44336'
        bg_color = (240, 240, 240)  # '#F0F0F0'
        
        running = True
        result = None
        
        while running:
            current_time = time.time()
            
            # Check timeout
            if current_time - last_interaction_time > n_to:
                result = -2  # Timeout
                break
            
            # Clear screen with light background
            self.screen.fill(bg_color)
            
            # Draw header area (top 1/6 of screen)
            # Left side: User name + message
            user_name_surface = user_name_font.render(user_name, True, user_name_color)
            user_name_rect = user_name_surface.get_rect(topleft=(20, header_height // 2 - user_name_font_size // 2))
            self.screen.blit(user_name_surface, user_name_rect)
            
            # Message after name
            message_text = f", {get_message(16, translations)} {attempts}"
            message_surface = message_font.render(message_text, True, message_color)
            message_x = user_name_rect.right + 5
            message_rect = message_surface.get_rect(left=message_x, centery=user_name_rect.centery)
            self.screen.blit(message_surface, message_rect)
            
            # Center: Countdown timer with background
            remaining_time = max(0, n_to - int(current_time - last_interaction_time))
            countdown_bg_color = (76, 175, 80)  # '#4CAF50' - green
            if remaining_time <= 3:
                countdown_font_color = (255, 0, 0)  # red
            elif remaining_time <= 5:
                countdown_font_color = (255, 165, 0)  # orange
            else:
                countdown_font_color = (255, 255, 255)  # white
            
            # Countdown background box
            countdown_width = 80
            countdown_height = header_height * 0.8
            countdown_rect = pygame.Rect(
                self.screen_width // 2 - countdown_width // 2,
                header_height * 0.1,
                countdown_width,
                countdown_height
            )
            pygame.draw.rect(self.screen, countdown_bg_color, countdown_rect)
            
            # Countdown text
            countdown_surface = countdown_font.render(str(remaining_time), True, countdown_font_color)
            countdown_text_rect = countdown_surface.get_rect(center=countdown_rect.center)
            self.screen.blit(countdown_surface, countdown_text_rect)
            
            # Right side: Code display with white background
            code_display = '*' * len(entered_code)
            code_bg_width = self.screen_width // 4
            code_bg_rect = pygame.Rect(
                self.screen_width - code_bg_width - 20,
                header_height * 0.1,
                code_bg_width,
                countdown_height
            )
            pygame.draw.rect(self.screen, (255, 255, 255), code_bg_rect)
            pygame.draw.rect(self.screen, (200, 200, 200), code_bg_rect, 2)  # Border
            
            # Code text
            if code_display:
                code_surface = code_font.render(code_display, True, (51, 51, 51))
                code_text_rect = code_surface.get_rect(center=code_bg_rect.center)
                self.screen.blit(code_surface, code_text_rect)
            
            # Draw buttons
            for row_idx, row in enumerate(buttons):
                for col_idx, button_text in enumerate(row):
                    x = col_idx * button_width
                    y = header_height + row_idx * button_height
                    
                    # Determine button color from original
                    if button_text.isdigit() or button_text == '*':
                        color = (63, 81, 181)  # '#3F51B5' - number buttons
                    elif button_text == get_message(32, translations):  # Enter
                        color = (76, 175, 80)  # '#4CAF50' - green
                    elif button_text == get_message(33, translations):  # Cancel
                        color = (244, 67, 54)  # '#F44336' - red
                    elif button_text == get_message(34, translations):  # Ping
                        color = (255, 152, 0)  # '#FF9800' - orange
                    elif button_text == get_message(31, translations):  # Delete
                        color = (158, 158, 158)  # '#9E9E9E' - grey
                    else:
                        color = (0, 121, 107)  # '#00796B' - action color
                    
                    # Draw button with small padding
                    button_rect = pygame.Rect(x + 2, y + 2, button_width - 4, button_height - 4)
                    pygame.draw.rect(self.screen, color, button_rect)
                    
                    # Draw button text
                    text_surface = button_font.render(button_text, True, (255, 255, 255))
                    text_rect = text_surface.get_rect(center=button_rect.center)
                    self.screen.blit(text_surface, text_rect)
            
            pygame.display.flip()
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    result = -1
                    running = False
                
                elif event.type == pygame.KEYDOWN:
                    last_interaction_time = time.time()
                    
                    if event.key == pygame.K_ESCAPE:
                        result = -1
                        running = False
                    
                    elif event.key >= pygame.K_0 and event.key <= pygame.K_9:
                        entered_code += str(event.key - pygame.K_0)
                    
                    elif event.key == pygame.K_BACKSPACE:
                        entered_code = entered_code[:-1]
                    
                    elif event.key == pygame.K_RETURN:
                        if entered_code == "***000***":
                            result = -100
                            running = False
                        else:
                            # Check password
                            should_show_alarm = entered_code.startswith('*')
                            code_to_check = entered_code[1:] if should_show_alarm else entered_code
                            
                            if code_to_check:
                                entered_hash = hashlib.sha256(code_to_check.encode()).hexdigest()
                                if entered_hash == password_hash:
                                    if should_show_alarm:
                                        result = self.show_alarm_menu(translations)
                                        running = False
                                    else:
                                        result = 1
                                        running = False
                                else:
                                    attempts -= 1
                                    if attempts == 0:
                                        self.flash_failure_message(user_name, translations)
                                        result = -2
                                        running = False
                                    else:
                                        message_text = f", {get_message(17, translations)} {attempts}"
                                        self.blink_message(message_text, user_name, attempts, translations)
                                    entered_code = ""
                            else:
                                message_text = f", {get_message(16, translations)} {attempts}"
                                self.blink_message(message_text, user_name, attempts, translations)
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    last_interaction_time = time.time()
                    x, y = event.pos
                    
                    if y > header_height:
                        row = (y - header_height) // button_height
                        col = x // button_width
                        
                        if 0 <= row < len(buttons) and 0 <= col < len(buttons[row]):
                            button_text = buttons[row][col]
                            
                            if button_text.isdigit() or button_text == '*':
                                entered_code += button_text
                            elif button_text == get_message(31, translations):  # Delete
                                entered_code = entered_code[:-1]
                            elif button_text == get_message(32, translations):  # Enter
                                # Same logic as RETURN key
                                if entered_code == "***000***":
                                    result = -100
                                    running = False
                                else:
                                    should_show_alarm = entered_code.startswith('*')
                                    code_to_check = entered_code[1:] if should_show_alarm else entered_code
                                    
                                    if code_to_check:
                                        entered_hash = hashlib.sha256(code_to_check.encode()).hexdigest()
                                        if entered_hash == password_hash:
                                            if should_show_alarm:
                                                result = self.show_alarm_menu(translations)
                                                running = False
                                            else:
                                                result = 1
                                                running = False
                                        else:
                                            attempts -= 1
                                            if attempts == 0:
                                                self.flash_failure_message(user_name, translations)
                                                result = -2
                                                running = False
                                            else:
                                                message_text = f", {get_message(17, translations)} {attempts}"
                                                self.blink_message(message_text, user_name, attempts, translations)
                                            entered_code = ""
                                    else:
                                        message_text = f", {get_message(16, translations)} {attempts}"
                                        self.blink_message(message_text, user_name, attempts, translations)
                            elif button_text == get_message(33, translations):  # Cancel
                                result = -1
                                running = False
                            elif button_text == get_message(34, translations):  # Ping
                                result = 0
                                running = False
            
            self.clock.tick(30)
            pygame.mouse.set_visible(True)
        
        return result
    
    def blink_message(self, message_text, user_name, attempts, translations):
        """Blink message three times"""
        message_font_size = int(self.screen_height / 30)
        user_name_font_size = int(message_font_size * 1.6)
        
        message_font = self.get_font(message_font_size)
        user_name_font = self.get_font(user_name_font_size)
        
        message_color = (25, 118, 210)
        user_name_color = (244, 67, 54)
        bg_color = (240, 240, 240)
        
        for _ in range(3):
            # Show message
            pygame.draw.rect(self.screen, bg_color, (0, 0, self.screen_width, self.screen_height // 6))
            
            user_name_surface = user_name_font.render(user_name, True, user_name_color)
            user_name_rect = user_name_surface.get_rect(topleft=(20, self.screen_height // 12 - user_name_font_size // 2))
            self.screen.blit(user_name_surface, user_name_rect)
            
            message_surface = message_font.render(message_text, True, message_color)
            message_x = user_name_rect.right + 5
            message_rect = message_surface.get_rect(left=message_x, centery=user_name_rect.centery)
            self.screen.blit(message_surface, message_rect)
            
            pygame.display.flip()
            pygame.time.wait(200)
            
            # Hide message
            pygame.draw.rect(self.screen, bg_color, (0, 0, self.screen_width, self.screen_height // 6))
            
            user_name_surface = user_name_font.render(user_name, True, user_name_color)
            self.screen.blit(user_name_surface, user_name_rect)
            
            pygame.display.flip()
            pygame.time.wait(200)
        
        # Show message again
        message_surface = message_font.render(message_text, True, message_color)
        self.screen.blit(message_surface, message_rect)
        pygame.display.flip()
    
    def flash_failure_message(self, user_name, translations):
        """Flash failure message five times"""
        failure_message = get_message(18, translations)  # Failed! The police is on their way!
        bold_font = self.get_font(int(self.screen_height / 20))
        user_name_font = self.get_font(int(self.screen_height / 30 * 1.6))
        
        bg_color = (240, 240, 240)
        user_name_color = (244, 67, 54)
        
        for _ in range(5):
            # Show message
            pygame.draw.rect(self.screen, bg_color, (0, 0, self.screen_width, self.screen_height // 6))
            
            user_name_surface = user_name_font.render(user_name, True, user_name_color)
            user_name_rect = user_name_surface.get_rect(topleft=(20, self.screen_height // 12 - user_name_font.get_height() // 2))
            self.screen.blit(user_name_surface, user_name_rect)
            
            message_surface = bold_font.render(failure_message, True, (255, 0, 0))
            message_x = user_name_rect.right + 5
            message_rect = message_surface.get_rect(left=message_x, centery=user_name_rect.centery)
            self.screen.blit(message_surface, message_rect)
            
            pygame.display.flip()
            pygame.time.wait(500)
            
            # Hide message
            pygame.draw.rect(self.screen, bg_color, (0, 0, self.screen_width, self.screen_height // 6))
            
            user_name_surface = user_name_font.render(user_name, True, user_name_color)
            self.screen.blit(user_name_surface, user_name_rect)
            
            pygame.display.flip()
            pygame.time.wait(500)
        
        # Show message again
        message_surface = bold_font.render(failure_message, True, (255, 0, 0))
        self.screen.blit(message_surface, message_rect)
        pygame.display.flip()
    
    def show_alarm_menu(self, translations):
        """Show alarm setup menu"""
        buttons = [
            (get_message(20, translations), 11, (76, 175, 80)),   # '#4CAF50' - Day mode
            (get_message(21, translations), 12, (33, 150, 243)),  # '#2196F3' - Night mode
            (get_message(22, translations), 10, (255, 193, 7)),   # '#FFC107' - Turn off
            (get_message(23, translations), -1, (244, 67, 54)),   # '#F44336' - Cancel
        ]
        
        button_width = self.screen_width // 2
        button_height = self.screen_height // 2
        button_font = self.get_font(int(self.screen_height / 16))
        bg_color = (240, 240, 240)  # '#F0F0F0'
        
        running = True
        result = -1
        
        while running:
            self.screen.fill(bg_color)
            
            for idx, (text, code, color) in enumerate(buttons):
                row = idx // 2
                col = idx % 2
                x = col * button_width
                y = row * button_height
                
                button_rect = pygame.Rect(x + 10, y + 10, button_width - 20, button_height - 20)
                pygame.draw.rect(self.screen, color, button_rect)
                
                # Wrap text if needed
                lines = self.text_wrap(text, button_font, button_width - 40)
                line_height = button_font.get_linesize()
                total_height = len(lines) * line_height
                start_y = button_rect.centery - total_height // 2
                
                for line in lines:
                    text_surface = button_font.render(line, True, (255, 255, 255))
                    text_rect = text_surface.get_rect(centerx=button_rect.centerx, y=start_y)
                    self.screen.blit(text_surface, text_rect)
                    start_y += line_height
            
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    result = -1
                    running = False
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    col = x // button_width
                    row = y // button_height
                    idx = row * 2 + col
                    
                    if 0 <= idx < len(buttons):
                        result = buttons[idx][1]
                        running = False
            
            self.clock.tick(30)
        
        return result
    
    def load_face_encodings(self):
        """Load face encodings from database"""
        self.known_face_encodings = []
        self.known_face_ids = []
        
        conn = sqlite3.connect('people.db')
        c = conn.cursor()
        c.execute("SELECT persons.id, photos.photo_data FROM persons JOIN photos ON persons.id = photos.person_id")
        rows = c.fetchall()
        conn.close()
        
        for person_id, photo_data in rows:
            image = Image.open(io.BytesIO(photo_data))
            image = image.convert("RGB")
            image_np = np.array(image)
            face_encodings = face_recognition.face_encodings(image_np)
            if face_encodings:
                self.known_face_encodings.append(face_encodings[0])
                self.known_face_ids.append(person_id)
        
        print(f"Loaded {len(self.known_face_encodings)} face encodings")
    
    def cleanup(self):
        """Clean up resources"""
        if self.video_capture:
            self.video_capture.release()
        pygame.quit()


# Helper functions from original modules
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

def preload_face_encodings(system):
    """Preload face encodings with caching"""
    db_path = 'people.db'
    
    if not cache_exists():
        print("Cache files not found. Recalculating face encodings.")
        system.load_face_encodings()
        db_hash = calculate_db_hash(db_path)
        save_cache(system.known_face_encodings, system.known_face_ids, db_hash)
    else:
        stored_db_hash = load_db_hash()
        current_db_hash = calculate_db_hash(db_path)
        if stored_db_hash != current_db_hash:
            print("Database has changed. Recalculating face encodings.")
            system.load_face_encodings()
            save_cache(system.known_face_encodings, system.known_face_ids, current_db_hash)
        else:
            print("Loading face encodings from cache.")
            system.known_face_encodings, system.known_face_ids = load_cache()

def get_person_info(person_id):
    conn = sqlite3.connect('people.db')
    c = conn.cursor()
    try:
        c.execute("SELECT name, surname, language FROM persons WHERE id = ?", (person_id,))
        result = c.fetchone()
        conn.close()
        return result
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.close()
        return None

def id_2_pass(person_id):
    conn = sqlite3.connect('people.db')
    c = conn.cursor()
    try:
        c.execute("SELECT password_hash FROM persons WHERE id = ?", (person_id,))
        result = c.fetchone()
        conn.close()
        if result:
            return result[0]
        return None
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.close()
        return None

def get_stranger_info():
    conn = sqlite3.connect('people.db')
    c = conn.cursor()
    try:
        c.execute("SELECT password_hash, language FROM persons WHERE name = ?", ("Stranger",))
        result = c.fetchone()
        conn.close()
        if result:
            return result
        else:
            return hashlib.sha256("1965".encode()).hexdigest(), "EN"
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.close()
        return hashlib.sha256("1965".encode()).hexdigest(), "EN"

def log_event(date, time, picture, name, surname, action_code):
    conn = sqlite3.connect(EVENTS_DB)
    c = conn.cursor()
    c.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
              (date, time, picture, name, surname, action_code))
    conn.commit()
    conn.close()

def check_internet_connection(host="8.8.8.8", port=53, timeout=1):
    """Fast internet check with short timeout"""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

def send_telegram_async(message, photo_path, buttons, user_lang):
    """Send Telegram message in background thread"""
    def send():
        try:
            print(f"Sending Telegram message in background...")
            start = time.time()
            telegram_button_handler(message, photo_path, buttons=buttons, user_lang=user_lang)
            print(f"Telegram sent in {time.time() - start:.2f} seconds")
        except Exception as e:
            print(f"Error sending Telegram: {e}")
    
    thread = threading.Thread(target=send, daemon=True)
    thread.start()
    return thread

def main():
    """Main program loop"""
    print(f"Gate Project System Version: {VERSION}")
    print(f"Modifications: {MODIFICATIONS}")
    
    # Initialize unified system
    system = UnifiedGateSystem()
    
    # Preload face encodings
    print("Preloading face encodings...")
    preload_face_encodings(system)
    
    print("Face encodings loaded. Starting main loop...")
    
    # Import alarm functions here to avoid circular imports
    from Alarm_Off import alarm_off
    from Alarm_On import alarm_on
    
    try:
        while True:
            # Use system default language for initial messages
            system_translations = load_translations('gate_project_translations.md', DEFAULT_SYSTEM_LANGUAGE)
            system.show_message(get_message(1, system_translations))  # Welcome message
            
            result = system.pattern_metapixel()
            if result != 0:
                system.show_message(get_message(2, system_translations))  # Problem with message display
                break
            
            system.show_message(get_message(3, system_translations))  # Initializing face recognition...
            recognized_id = system.face_recognition_loop()
            
            if recognized_id is None:
                continue
            
            print(f"Recognition result: {recognized_id}")
            
            # Process recognition result
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Get person info
            if recognized_id == "Stranger":
                stranger_password_hash, user_lang = get_stranger_info()
                if user_lang is None or user_lang == "":
                    user_lang = DEFAULT_SYSTEM_LANGUAGE
                translations = load_translations('gate_project_translations.md', user_lang)
                message = get_message(31, translations)
                password_hash = stranger_password_hash
                ping_message = get_message(32, translations)
                name = "Unrecognized"
                surname = "Person"
                user_name = "Stranger"
                send_picture = True
            else:
                person_info = get_person_info(recognized_id)
                if person_info:
                    name, surname, user_lang = person_info
                    if user_lang is None or user_lang == "":
                        user_lang = DEFAULT_SYSTEM_LANGUAGE
                    translations = load_translations('gate_project_translations.md', user_lang)
                    message = f"{name} {surname} {get_message(35, translations)}"
                    password_hash = id_2_pass(recognized_id)
                    ping_message = f"{get_message(34, translations)} {name} {surname}!"
                    user_name = name
                    send_picture = True
                else:
                    stranger_password_hash, user_lang = get_stranger_info()
                    if user_lang is None or user_lang == "":
                        user_lang = DEFAULT_SYSTEM_LANGUAGE
                    translations = load_translations('gate_project_translations.md', user_lang)
                    message = get_message(36, translations)
                    password_hash = stranger_password_hash
                    ping_message = get_message(37, translations)
                    name = "Unknown"
                    surname = "Unknown"
                    user_name = "Unknown"
                    send_picture = True
            
            # Check internet and send Telegram
            has_internet = check_internet_connection(host="8.8.8.8", port=53, timeout=1)
            telegram_thread = None
            if has_internet and send_picture:
                telegram_thread = send_telegram_async(message, "face.jpg", False, user_lang)
            
            # Show keyboard
            max_attempts = 3
            keyboard_result = system.show_keyboard(password_hash, max_attempts, user_lang, user_name)
            
            print(f"Keyboard returned with result: {keyboard_result}")
            
            # Handle keyboard results
            action_code = keyboard_result
            
            if keyboard_result == -100:
                print("Exit code entered - terminating program")
                break
            
            elif keyboard_result == 1:  # Correct password
                system.show_message(get_message(6, translations))  # Switching off alarm...
                alarm_result = alarm_off(user_lang, system)
                if alarm_result == 1:
                    try:
                        control_shelly_switch(ip_gate)
                        system.show_message(get_message(7, translations), gate_open_short)
                        control_shelly_switch(ip_gate)
                        system.show_message(get_message(7, translations), gate_wait_short)
                        control_shelly_switch(ip_gate)
                    except Exception as e:
                        system.show_message(f"{get_message(8, translations)} {e}")
                else:
                    system.show_message(get_message(9, translations))
                action_code = 1
            
            elif keyboard_result == 11:  # Set alarm (Day mode)
                system.show_message(get_message(10, translations))
                alarm_result = alarm_on(False, user_lang, system)
                
            elif keyboard_result == 12:  # Set alarm (Night mode)
                system.show_message(get_message(11, translations))
                alarm_result = alarm_on(True, user_lang, system)
                
            elif keyboard_result == 10:  # Turn off alarm
                system.show_message(get_message(6, translations))
                alarm_result = alarm_off(user_lang, system)
                system.show_message(get_message(24, translations), 1)
                
            elif keyboard_result == 0:  # Ping Lev
                system.show_message(get_message(12, translations))
                if has_internet:
                    ping_result = telegram_button_handler(ping_message, "face.jpg", buttons=True, user_lang=user_lang)
                    
                    if ping_result == "+1":
                        action_code = 2
                        system.show_message(get_message(6, translations))
                        alarm_result = alarm_off(user_lang, system)
                        if alarm_result == 1:
                            try:
                                control_shelly_switch(ip_gate)
                                system.show_message(get_message(7, translations), gate_open_short)
                                control_shelly_switch(ip_gate)
                                system.show_message(get_message(7, translations), gate_wait_short)
                                control_shelly_switch(ip_gate)
                            except Exception as e:
                                system.show_message(f"{get_message(8, translations)} {e}")
                        else:
                            system.show_message(get_message(9, translations))
                    elif ping_result == "-1":
                        action_code = 3
                        system.show_message(get_message(13, translations), 7)
                    else:
                        action_code = 4
                        system.show_message(get_message(14, translations), 7)
                else:
                    system.show_message("No internet connection for ping", 3)
                    action_code = 4
            
            # Wait for Telegram thread if still running
            if telegram_thread and telegram_thread.is_alive():
                telegram_thread.join(timeout=2)
            
            # Log event
            with open("face.jpg", "rb") as image_file:
                image_data = image_file.read()
            log_event(current_date, current_time, image_data, name, surname, action_code)
            
            # Clear camera buffer and add delay to prevent false detections
            if keyboard_result in [-1, -2, 10, 11, 12]:  # Cancel, timeout, or alarm commands
                # Clear display
                system.screen.fill(system.bg_color)
                pygame.display.flip()
                
                # Clear camera buffer
                for _ in range(10):
                    if system.video_capture.isOpened():
                        system.video_capture.read()
                
                # Small delay to ensure person has moved away
                pygame.time.wait(500)
    
    finally:
        print("Program completed.")
        system.cleanup()

if __name__ == "__main__":
    main()