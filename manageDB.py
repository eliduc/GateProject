#!/usr/bin/env python3
# manageDB.py - Version 2.0
# People Database Management Application

import sqlite3
import io
import os
import hashlib
from PIL import Image, ImageTk, ImageEnhance
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import paramiko
import json
import shutil
import cv2
import numpy as np
import threading
import time

# Version information
APP_VERSION = "2.0"
VERSION_INFO = """
People Database Manager v2.0

Changes in version 2.0:
• Added console progress indicator for database downloads
• Fixed initialization errors with photo display
• Improved UI feedback during long operations
• Added version information display
• Enhanced connection status messages
• Better error handling and user notifications
• Added status bar for operation feedback
• Added Exit button for convenient program closure
• Renamed Undup to UnDup for better readability
"""

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def download_database(config, progress_callback=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print("Connecting to remote server...")
        if progress_callback:
            progress_callback("Connecting to remote server...", 10)
        
        ssh.connect(config['rpi_host'], username=config['rpi_user'], password=config['rpi_password'])
        
        print("Connected. Opening SFTP channel...")
        if progress_callback:
            progress_callback("Connected. Opening SFTP channel...", 30)
        
        sftp = ssh.open_sftp()
        
        print("Getting file information...")
        if progress_callback:
            progress_callback("Getting file information...", 40)
        
        # Get remote file size for progress tracking
        remote_file_attrs = sftp.stat(config['db_faces_path'])
        file_size = remote_file_attrs.st_size
        
        print(f"Downloading database ({file_size // 1024} KB)...")
        if progress_callback:
            progress_callback(f"Downloading database ({file_size // 1024} KB)...", 50)
        
        # Download with progress tracking
        downloaded = 0
        with sftp.open(config['db_faces_path'], 'rb') as remote_file:
            with open('people_rm.db', 'wb') as local_file:
                while True:
                    data = remote_file.read(32768)  # Read in 32KB chunks
                    if not data:
                        break
                    local_file.write(data)
                    downloaded += len(data)
                    progress = 50 + int((downloaded / file_size) * 40)  # 50-90% range
                    progress_msg = f"Downloading... {downloaded // 1024}/{file_size // 1024} KB"
                    print(f"\r{progress_msg} ({progress}%)", end='', flush=True)
                    if progress_callback:
                        progress_callback(progress_msg, progress)
        
        print("\nDownload complete. Closing connection...")
        if progress_callback:
            progress_callback("Download complete. Closing connection...", 95)
        
        sftp.close()
        ssh.close()
        
        print("Database downloaded successfully!")
        if progress_callback:
            progress_callback("Database downloaded successfully!", 100)
        
        time.sleep(0.5)  # Brief pause to show completion
        return True
    except Exception as e:
        print(f"\nError downloading database: {str(e)}")
        if progress_callback:
            progress_callback(f"Error: {str(e)}", -1)
        return False

def save_local_database():
    try:
        shutil.copy('people_rm.db', 'people.db')
        print("Local database saved successfully.")
        return True
    except Exception as e:
        print(f"Error saving local database: {str(e)}")
        return False

def upload_database(config, progress_callback=None):
    if not save_local_database():
        return False

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print("Connecting to remote server...")
        if progress_callback:
            progress_callback("Connecting to remote server...", 10)
        
        ssh.connect(config['rpi_host'], username=config['rpi_user'], password=config['rpi_password'])
        
        print("Connected. Opening SFTP channel...")
        if progress_callback:
            progress_callback("Connected. Opening SFTP channel...", 30)
        
        sftp = ssh.open_sftp()
        
        print("Preparing to upload database...")
        if progress_callback:
            progress_callback("Preparing to upload database...", 40)
        
        # Get local file size for progress tracking
        file_size = os.path.getsize('people_rm.db')
        
        print(f"Uploading database ({file_size // 1024} KB)...")
        if progress_callback:
            progress_callback(f"Uploading database ({file_size // 1024} KB)...", 50)
        
        # Upload with progress tracking
        uploaded = 0
        with open('people_rm.db', 'rb') as local_file:
            with sftp.open(config['db_faces_path'], 'wb') as remote_file:
                while True:
                    data = local_file.read(32768)  # Read in 32KB chunks
                    if not data:
                        break
                    remote_file.write(data)
                    uploaded += len(data)
                    progress = 50 + int((uploaded / file_size) * 40)  # 50-90% range
                    progress_msg = f"Uploading... {uploaded // 1024}/{file_size // 1024} KB"
                    print(f"\r{progress_msg} ({progress}%)", end='', flush=True)
                    if progress_callback:
                        progress_callback(progress_msg, progress)
        
        print("\nUpload complete. Closing connection...")
        if progress_callback:
            progress_callback("Upload complete. Closing connection...", 95)
        
        sftp.close()
        ssh.close()
        
        print("Database uploaded successfully!")
        if progress_callback:
            progress_callback("Database uploaded successfully!", 100)
        
        time.sleep(0.5)  # Brief pause to show completion
        return True
    except Exception as e:
        print(f"\nError uploading database: {str(e)}")
        if progress_callback:
            progress_callback(f"Error: {str(e)}", -1)
        return False

class ProgressDialog:
    def __init__(self, parent, title="Progress"):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create widgets
        self.label = ttk.Label(self.dialog, text="Initializing...", font=('TkDefaultFont', 10))
        self.label.pack(pady=20)
        
        self.progress = ttk.Progressbar(self.dialog, length=350, mode='determinate')
        self.progress.pack(pady=10)
        
        self.error_occurred = False
        
        # Center on screen if parent is hidden
        self.dialog.update_idletasks()
        if parent.winfo_viewable():
            x = (parent.winfo_x() + (parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2))
            y = (parent.winfo_y() + (parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2))
        else:
            # Center on screen
            x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
            y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Force dialog to be on top
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        
        # Update to ensure dialog is shown
        self.dialog.update()
    
    def update(self, message, progress):
        try:
            if progress < 0:  # Error condition
                self.error_occurred = True
                self.label.config(text=message, foreground='red')
                self.dialog.after(2000, self.close)  # Close after 2 seconds
            else:
                self.label.config(text=message)
                self.progress['value'] = progress
                
                if progress >= 100:
                    self.dialog.after(500, self.close)  # Close after 0.5 seconds when complete
            
            # Force update to show changes
            self.dialog.update_idletasks()
        except:
            # If update fails, just continue
            pass
    
    def close(self):
        self.dialog.destroy()

class PeopleDBApp:
    def __init__(self, master, config):
        self.master = master
        self.master.title(f"People Database Management - v{APP_VERSION}")
        self.master.geometry("850x600")
        self.config = config
        self.changes_made = False

        # Initialize photo-related attributes first
        self.current_photo_index = 0
        self.total_photos = 0
        self.photos = []
        self.visible_photos = 0
        self.selected_photo = None
        self.captured_images = []

        # Show version info on startup (disabled)
        # self.show_version_info()

        self.create_database()
        self.create_widgets()

        # Bind the window close event
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show_version_info(self):
        messagebox.showinfo(f"Welcome to People Database Manager v{APP_VERSION}", VERSION_INFO)

    def create_database(self):
        conn = sqlite3.connect('people_rm.db')
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS persons
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      person_unique_id TEXT UNIQUE NOT NULL,
                      name TEXT NOT NULL,
                      surname TEXT NOT NULL,
                      language TEXT CHECK(language IN ('EN', 'IT', 'RU', 'HB', 'NA')) NOT NULL,
                      password_hash TEXT NOT NULL)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS photos
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      person_id INTEGER,
                      photo_data BLOB,
                      photo_type TEXT CHECK(photo_type IN ('jpeg', 'png')) NOT NULL,
                      FOREIGN KEY (person_id) REFERENCES persons(id))''')
        
        c.execute('''CREATE INDEX IF NOT EXISTS idx_person_unique_id ON persons(person_unique_id)''')
        
        conn.commit()
        conn.close()

    def create_widgets(self):
        # Add status bar
        self.status_frame = ttk.Frame(self.master)
        self.status_frame.pack(side='bottom', fill='x')
        
        self.status_label = ttk.Label(self.status_frame, text=f"Version {APP_VERSION} | Ready", relief='sunken')
        self.status_label.pack(side='left', fill='x', expand=True, padx=2, pady=2)

        self.tree = ttk.Treeview(self.master, columns=('ID', 'Name', 'Surname', 'Language'), show='headings')
        self.tree.heading('ID', text='ID')
        self.tree.heading('Name', text='Name')
        self.tree.heading('Surname', text='Surname')
        self.tree.heading('Language', text='Language')
        self.tree.pack(expand=True, fill='both', padx=10, pady=10)

        self.photo_frame = ttk.Frame(self.master)
        self.photo_frame.pack(fill='x', padx=10, pady=10)

        self.photo_canvas = tk.Canvas(self.photo_frame, height=120)
        self.photo_canvas.pack(side='top', fill='x', expand=True)

        self.nav_frame = ttk.Frame(self.master)
        self.nav_frame.pack(fill='x', padx=10, pady=5)

        self.left_button = tk.Button(self.nav_frame, text="◀", command=self.scroll_left, 
                                     state='disabled', font=('Arial', 16, 'bold'),
                                     relief='flat', bg='lightgray', fg='black')
        self.left_button.pack(side='left', padx=5)

        self.delete_frame = ttk.Frame(self.nav_frame)
        self.delete_frame.pack(side='left', expand=True, fill='x')

        self.delete_button = tk.Button(self.delete_frame, text="Delete", command=self.delete_selected_photo,
                                       font=('Arial', 12, 'bold'),
                                       relief='flat', bg='lightgray', fg='black')

        self.right_button = tk.Button(self.nav_frame, text="▶", command=self.scroll_right, 
                                      state='disabled', font=('Arial', 16, 'bold'),
                                      relief='flat', bg='lightgray', fg='black')
        self.right_button.pack(side='right', padx=5)

        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10, fill='x', padx=10)

        # Configure the button_frame to expand columns evenly
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)
        button_frame.columnconfigure(4, weight=1)
        button_frame.columnconfigure(5, weight=1)
        button_frame.columnconfigure(6, weight=1)

        # Create a custom style for larger buttons
        style = ttk.Style()
        style.configure('Larger.TButton', font=('TkDefaultFont', 12, 'bold'))
        style.configure('Exit.TButton', font=('TkDefaultFont', 12, 'bold'), foreground='red')

        ttk.Button(button_frame, text="Add Record", command=self.add_record, style='Larger.TButton').grid(row=0, column=0, padx=1, pady=5, sticky='ew')
        ttk.Button(button_frame, text="Edit Record", command=self.edit_record, style='Larger.TButton').grid(row=0, column=1, padx=1, pady=5, sticky='ew')
        ttk.Button(button_frame, text="Delete Record", command=self.delete_record, style='Larger.TButton').grid(row=0, column=2, padx=1, pady=5, sticky='ew')
        ttk.Button(button_frame, text="Add Photo", command=self.add_single_photo, style='Larger.TButton').grid(row=0, column=3, padx=1, pady=5, sticky='ew')
        ttk.Button(button_frame, text="Add Photos from Dir", command=self.add_photos, style='Larger.TButton').grid(row=0, column=4, padx=1, pady=5, sticky='ew')
        ttk.Button(button_frame, text="UnDup Photos", command=self.undup_photos, style='Larger.TButton').grid(row=0, column=5, padx=1, pady=5, sticky='ew')
        ttk.Button(button_frame, text="Exit", command=self.exit_program, style='Exit.TButton').grid(row=0, column=6, padx=1, pady=5, sticky='ew')

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.photo_canvas.bind('<Configure>', self.on_canvas_configure)

        self.refresh_records()

    def update_status(self, message):
        self.status_label.config(text=f"Version {APP_VERSION} | {message}")
        self.master.update_idletasks()

    def on_canvas_configure(self, event):
        # Only display photos if everything is properly initialized
        if hasattr(self, 'photos') and hasattr(self, 'current_photo_index') and hasattr(self, 'total_photos'):
            self.display_current_photos()

    def scroll_left(self):
        if self.current_photo_index > 0:
            self.current_photo_index -= 1
            self.display_current_photos()

    def scroll_right(self):
        if self.current_photo_index < self.total_photos - self.visible_photos:
            self.current_photo_index += 1
            self.display_current_photos()

    def display_current_photos(self):
        # Safeguard against uninitialized attributes
        if not hasattr(self, 'photos') or not hasattr(self, 'current_photo_index'):
            return
            
        self.photo_canvas.delete("all")
        canvas_width = self.photo_canvas.winfo_width()
        photo_width = 110  # 100px image + 10px padding
        self.visible_photos = max(canvas_width // photo_width, 1)

        for i in range(self.visible_photos):
            if self.current_photo_index + i < self.total_photos:
                photo = self.photos[self.current_photo_index + i]
                x = i*photo_width + 55
                y = 60
                image_item = self.photo_canvas.create_image(x, y, image=photo['image'])
                self.photo_canvas.tag_bind(image_item, '<Button-1>', lambda event, idx=self.current_photo_index + i: self.select_photo(idx))

                if photo.get('selected', False):
                    self.photo_canvas.create_rectangle(x-52, y-52, x+52, y+52, outline='green', width=2)

        self.left_button['state'] = 'normal' if self.current_photo_index > 0 else 'disabled'
        self.right_button['state'] = 'normal' if self.current_photo_index < self.total_photos - self.visible_photos else 'disabled'

    def select_photo(self, index):
        if self.selected_photo == index:
            self.photos[index]['selected'] = False
            self.selected_photo = None
            self.delete_button.pack_forget()  # Hide the delete button
        else:
            if self.selected_photo is not None:
                self.photos[self.selected_photo]['selected'] = False
            self.photos[index]['selected'] = True
            self.selected_photo = index

            original_image = Image.open(io.BytesIO(self.photos[index]['data']))
            enhancer = ImageEnhance.Brightness(original_image)
            brightened_image = enhancer.enhance(1.2)  # Increase brightness by 20%
            brightened_image.thumbnail((100, 100))
            self.photos[index]['image'] = ImageTk.PhotoImage(brightened_image)

            self.delete_button.pack(expand=True)  # Show the delete button

        self.display_current_photos()

    def delete_selected_photo(self):
        if self.selected_photo is None:
            return

        if not messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this photo?"):
            return

        selected_items = self.tree.selection()
        if not selected_items:
            return

        person_id = self.tree.item(selected_items[0])['values'][0]
        photo_id = self.photos[self.selected_photo]['id']

        conn = sqlite3.connect('people_rm.db')
        c = conn.cursor()
        c.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        conn.commit()
        conn.close()

        del self.photos[self.selected_photo]
        self.total_photos -= 1
        self.selected_photo = None

        if self.current_photo_index >= self.total_photos:
            self.current_photo_index = max(0, self.total_photos - self.visible_photos)

        self.delete_button.pack_forget()  # Hide the delete button after deletion
        self.display_current_photos()  # Refresh the photo display
        self.changes_made = True
        self.update_status("Photo deleted")

    def refresh_records(self):
        self.update_status("Refreshing records...")
        for i in self.tree.get_children():
            self.tree.delete(i)

        conn = sqlite3.connect('people_rm.db')
        c = conn.cursor()
        c.execute("SELECT person_unique_id, name, surname, language FROM persons")
        records = c.fetchall()
        conn.close()

        for record in records:
            self.tree.insert('', 'end', values=record)
        
        self.update_status(f"Loaded {len(records)} records")

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        person_id = self.tree.item(selected_items[0])['values'][0]
        self.update_status(f"Loading photos for {person_id}...")

        conn = sqlite3.connect('people_rm.db')
        c = conn.cursor()
        c.execute("""
            SELECT id, photo_data, photo_type 
            FROM photos 
            WHERE person_id = (SELECT id FROM persons WHERE person_unique_id = ?)
        """, (person_id,))
        photo_data = c.fetchall()
        conn.close()

        self.photos = []
        for photo_id, photo_bytes, photo_type in photo_data:
            image = Image.open(io.BytesIO(photo_bytes))
            image.thumbnail((100, 100))  # Resize image to thumbnail
            photo = ImageTk.PhotoImage(image)
            self.photos.append({'id': photo_id, 'image': photo, 'data': photo_bytes, 'selected': False})

        self.total_photos = len(self.photos)
        self.current_photo_index = 0
        self.selected_photo = None
        self.delete_button.pack_forget()  # Hide the delete button when a new person is selected
        self.display_current_photos()
        self.update_status(f"Loaded {self.total_photos} photos for {person_id}")

    def generate_unique_id(self, name, surname):
        base_id = (name[0] + surname[0]).upper()
        unique_id = base_id
        suffix = 0
        
        conn = sqlite3.connect('people_rm.db')
        c = conn.cursor()
        
        while True:
            c.execute("SELECT COUNT(*) FROM persons WHERE person_unique_id = ?", (unique_id,))
            if c.fetchone()[0] == 0:
                break
            suffix += 1
            unique_id = f"{base_id}{suffix}"
        
        conn.close()
        return unique_id

    def add_record(self):
        add_window = tk.Toplevel(self.master)
        add_window.title("Add New Record")

        ttk.Label(add_window, text="Name:").grid(row=0, column=0, padx=5, pady=5)
        name_entry = ttk.Entry(add_window)
        name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_window, text="Surname:").grid(row=1, column=0, padx=5, pady=5)
        surname_entry = ttk.Entry(add_window)
        surname_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(add_window, text="Language:").grid(row=2, column=0, padx=5, pady=5)
        language_var = tk.StringVar(value="EN")
        language_combo = ttk.Combobox(add_window, textvariable=language_var, values=["EN", "IT", "RU", "HB", "NA"])
        language_combo.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(add_window, text="Password:").grid(row=3, column=0, padx=5, pady=5)
        password_entry = ttk.Entry(add_window, show="*")
        password_entry.grid(row=3, column=1, padx=5, pady=5)

        # Add password visibility toggle
        self.password_visible = tk.BooleanVar(value=False)

        def toggle_password_visibility():
            current_password = password_entry.get()
            password_entry.delete(0, tk.END)
            if self.password_visible.get():
                password_entry.config(show="")
            else:
                password_entry.config(show="*")
            password_entry.insert(0, current_password)

        password_visible_checkbox = ttk.Checkbutton(add_window, text="Make password visible", 
                                                    variable=self.password_visible, 
                                                    command=toggle_password_visibility)
        password_visible_checkbox.grid(row=3, column=2, padx=5, pady=5)

        # Add pictures button
        ttk.Button(add_window, text="Add Pictures", command=lambda: self.open_camera(add_window)).grid(row=4, column=0, columnspan=2, pady=10)

        # Image display area
        self.image_frame = ttk.Frame(add_window)
        self.image_frame.grid(row=5, column=0, columnspan=3, padx=5, pady=5)

        def save_record():
            name = name_entry.get()
            surname = surname_entry.get()
            language = language_var.get()
            password = password_entry.get()

            if not all([name, surname, language, password]):
                messagebox.showerror("Error", "All fields are required")
                return

            person_unique_id = self.generate_unique_id(name, surname)
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            conn = sqlite3.connect('people_rm.db')
            c = conn.cursor()
            c.execute("INSERT INTO persons (person_unique_id, name, surname, language, password_hash) VALUES (?, ?, ?, ?, ?)",
                      (person_unique_id, name, surname, language, password_hash))
            
            person_id = c.lastrowid

            for img in self.captured_images:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                c.execute("INSERT INTO photos (person_id, photo_data, photo_type) VALUES (?, ?, ?)",
                          (person_id, img_byte_arr, 'png'))

            conn.commit()
            conn.close()

            add_window.destroy()
            self.refresh_records()
            self.changes_made = True
            self.captured_images = []  # Clear captured images after saving
            self.update_status(f"Added new record: {person_unique_id}")

        ttk.Button(add_window, text="Save", command=save_record).grid(row=6, column=0, columnspan=3, pady=10)

    def open_camera(self, parent_window):
        camera_window = tk.Toplevel(parent_window)
        camera_window.title("Camera")

        # Create a label to display the video feed
        video_label = ttk.Label(camera_window)
        video_label.pack(padx=10, pady=10)

        # Create buttons
        button_frame = ttk.Frame(camera_window)
        button_frame.pack(pady=10)

        take_pic_button = ttk.Button(button_frame, text="Take Pic", command=lambda: self.take_picture(video_label))
        take_pic_button.pack(side=tk.LEFT, padx=5)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=camera_window.destroy)
        cancel_button.pack(side=tk.LEFT, padx=5)

        # Open the camera
        self.cap = cv2.VideoCapture(0)

        def update_frame():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                video_label.imgtk = imgtk
                video_label.configure(image=imgtk)
            video_label.after(10, update_frame)

        update_frame()

    def take_picture(self, video_label):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)

            # Create a new window to display the captured image
            preview_window = tk.Toplevel(self.master)
            preview_window.title("Preview")

            # Display the captured image
            img.thumbnail((300, 300))
            imgtk = ImageTk.PhotoImage(image=img)
            image_label = ttk.Label(preview_window, image=imgtk)
            image_label.image = imgtk
            image_label.pack(padx=10, pady=10)

            # Create buttons for keep and re-take
            button_frame = ttk.Frame(preview_window)
            button_frame.pack(pady=10)

            keep_button = ttk.Button(button_frame, text="Keep", command=lambda: self.keep_image(img, preview_window))
            keep_button.pack(side=tk.LEFT, padx=5)

            retake_button = ttk.Button(button_frame, text="Re-take", command=preview_window.destroy)
            retake_button.pack(side=tk.LEFT, padx=5)

    def keep_image(self, img, preview_window):
        self.captured_images.append(img)
        preview_window.destroy()
        self.display_captured_images()

    def display_captured_images(self):
        # Clear existing images
        for widget in self.image_frame.winfo_children():
            widget.destroy()

        # Display captured images
        for i, img in enumerate(self.captured_images):
            img.thumbnail((100, 100))
            photo = ImageTk.PhotoImage(img)
            label = ttk.Label(self.image_frame, image=photo)
            label.image = photo
            label.grid(row=i // 3, column=i % 3, padx=5, pady=5)

    def edit_record(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a record to edit")
            return

        person_id = self.tree.item(selected_item[0])['values'][0]

        conn = sqlite3.connect('people_rm.db')
        c = conn.cursor()
        c.execute("SELECT * FROM persons WHERE person_unique_id = ?", (person_id,))
        record = c.fetchone()
        conn.close()

        if record:
            edit_window = tk.Toplevel(self.master)
            edit_window.title("Edit Record")

            ttk.Label(edit_window, text="Name:").grid(row=0, column=0, padx=5, pady=5)
            name_entry = ttk.Entry(edit_window)
            name_entry.insert(0, record[2])
            name_entry.grid(row=0, column=1, padx=5, pady=5)

            ttk.Label(edit_window, text="Surname:").grid(row=1, column=0, padx=5, pady=5)
            surname_entry = ttk.Entry(edit_window)
            surname_entry.insert(0, record[3])
            surname_entry.grid(row=1, column=1, padx=5, pady=5)

            ttk.Label(edit_window, text="Language:").grid(row=2, column=0, padx=5, pady=5)
            language_var = tk.StringVar(value=record[4])
            language_combo = ttk.Combobox(edit_window, textvariable=language_var, values=["EN", "IT", "RU", "HB", "NA"])
            language_combo.grid(row=2, column=1, padx=5, pady=5)

            ttk.Label(edit_window, text="Password:").grid(row=3, column=0, padx=5, pady=5)
            self.password_visible = tk.BooleanVar(value=False)
            password_entry = ttk.Entry(edit_window, show="*")
            password_entry.grid(row=3, column=1, padx=5, pady=5)

            # Store the actual password hash
            actual_password_hash = record[5]

            def toggle_password_visibility():
                current_password = password_entry.get()
                password_entry.delete(0, tk.END)
                if self.password_visible.get():
                    password_entry.config(show="")
                else:
                    password_entry.config(show="*")
                password_entry.insert(0, current_password)

            password_visible_checkbox = ttk.Checkbutton(edit_window, text="Make password visible", 
                                                        variable=self.password_visible, 
                                                        command=toggle_password_visibility)
            password_visible_checkbox.grid(row=3, column=2, padx=5, pady=5)

            # Initially set the password field to the actual password hash
            password_entry.insert(0, actual_password_hash)

            def save_changes():
                new_name = name_entry.get()
                new_surname = surname_entry.get()
                new_language = language_var.get()
                new_password = password_entry.get()

                conn = sqlite3.connect('people_rm.db')
                c = conn.cursor()
                
                if new_password == actual_password_hash:
                    # Password wasn't changed, keep the old one
                    c.execute("UPDATE persons SET name = ?, surname = ?, language = ? WHERE person_unique_id = ?",
                              (new_name, new_surname, new_language, person_id))
                else:
                    # Password was changed, update with new hash
                    new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
                    c.execute("UPDATE persons SET name = ?, surname = ?, language = ?, password_hash = ? WHERE person_unique_id = ?",
                              (new_name, new_surname, new_language, new_password_hash, person_id))
                
                conn.commit()
                conn.close()

                edit_window.destroy()
                self.refresh_records()
                self.changes_made = True
                self.update_status(f"Updated record: {person_id}")

            ttk.Button(edit_window, text="Save Changes", command=save_changes).grid(row=4, column=0, columnspan=3, pady=10)
            
    def delete_record(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a record to delete")
            return

        person_id = self.tree.item(selected_item[0])['values'][0]

        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this record?"):
            conn = sqlite3.connect('people_rm.db')
            c = conn.cursor()
            c.execute("DELETE FROM persons WHERE person_unique_id = ?", (person_id,))
            c.execute("DELETE FROM photos WHERE person_id = (SELECT id FROM persons WHERE person_unique_id = ?)", (person_id,))
            conn.commit()
            conn.close()

            self.refresh_records()
            self.photos = []
            self.total_photos = 0
            self.current_photo_index = 0
            self.selected_photo = None
            self.delete_button.pack_forget()  # Hide the delete button
            self.display_current_photos()
            self.changes_made = True
            self.update_status(f"Deleted record: {person_id}")

    def add_photos(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a record to add photos to")
            return

        person_id = self.tree.item(selected_item[0])['values'][0]

        # Open directory chooser dialog
        directory = filedialog.askdirectory(title="Select Directory with Photos")

        if not directory:
            return

        self.update_status("Adding photos from directory...")

        conn = sqlite3.connect('people_rm.db')
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM photos WHERE person_id = (SELECT id FROM persons WHERE person_unique_id = ?)", (person_id,))
        current_photo_count = c.fetchone()[0]

        if current_photo_count >= 20:
            messagebox.showinfo("Info", "Maximum number of photos (20) reached. Cannot add more photos.")
            conn.close()
            return

        added_count = 0
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                if current_photo_count + added_count >= 20:
                    messagebox.showinfo("Info", f"Maximum number of photos (20) reached. Stopping after adding {added_count} photos.")
                    break

                file_path = os.path.join(directory, filename)
                with open(file_path, 'rb') as file:
                    photo_data = file.read()

                photo_type = 'png' if filename.lower().endswith('.png') else 'jpeg'

                c.execute("""
                    INSERT INTO photos (person_id, photo_data, photo_type)
                    VALUES ((SELECT id FROM persons WHERE person_unique_id = ?), ?, ?)
                """, (person_id, photo_data, photo_type))

                added_count += 1

        conn.commit()
        conn.close()

        messagebox.showinfo("Success", f"Added {added_count} photos to the record")
        self.on_tree_select(None)  # Refresh the photo display
        self.changes_made = True
        self.update_status(f"Added {added_count} photos to {person_id}")

    def add_single_photo(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a record to add a photo to")
            return

        person_id = self.tree.item(selected_item[0])['values'][0]

        conn = sqlite3.connect('people_rm.db')
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM photos WHERE person_id = (SELECT id FROM persons WHERE person_unique_id = ?)", (person_id,))
        current_photo_count = c.fetchone()[0]

        if current_photo_count >= 20:
            messagebox.showinfo("Info", "Maximum number of photos (20) reached. Cannot add more photos.")
            conn.close()
            return

        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])

        if not file_path:
            conn.close()
            return

        with open(file_path, 'rb') as file:
            photo_data = file.read()

        photo_type = 'png' if file_path.lower().endswith('.png') else 'jpeg'

        c.execute("""
            INSERT INTO photos (person_id, photo_data, photo_type)
            VALUES ((SELECT id FROM persons WHERE person_unique_id = ?), ?, ?)
        """, (person_id, photo_data, photo_type))

        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Added 1 photo to the record")
        self.on_tree_select(None)  # Refresh the photo display
        self.changes_made = True
        self.update_status(f"Added 1 photo to {person_id}")

    def undup_photos(self):
        self.update_status("Removing duplicate photos...")
        
        conn = sqlite3.connect('people_rm.db')
        c = conn.cursor()

        # Get all persons
        c.execute("SELECT id FROM persons")
        persons = c.fetchall()

        total_records = len(persons)
        total_photos = 0
        duplicates_removed = 0

        for person in persons:
            person_id = person[0]
            
            # Get all photos for this person
            c.execute("SELECT id, photo_data FROM photos WHERE person_id = ?", (person_id,))
            photos = c.fetchall()
            
            total_photos += len(photos)
            
            # Use a dictionary to store unique photos
            unique_photos = {}
            
            for photo_id, photo_data in photos:
                # Create a hash of the photo data
                photo_hash = hashlib.md5(photo_data).hexdigest()
                
                if photo_hash in unique_photos:
                    # This is a duplicate, remove it
                    c.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
                    duplicates_removed += 1
                else:
                    unique_photos[photo_hash] = photo_id

        conn.commit()
        conn.close()

        messagebox.showinfo("UnDup Photos Result", 
                            f"Scanned {total_records} records and {total_photos} photos.\n"
                            f"Found and removed {duplicates_removed} duplicate photos.")
        
        # Refresh the display if the current record has photos
        self.on_tree_select(None)
        self.changes_made = True
        self.update_status(f"Removed {duplicates_removed} duplicate photos")

    def exit_program(self):
        """Handle the Exit button click - same as closing window"""
        self.update_status("Exiting program...")
        self.on_closing()

    def on_closing(self):
        if self.changes_made:
            if messagebox.askyesno("Save Changes", "Do you want to save changes to the local and remote database?"):
                print("\nUploading database changes...")
                print("Please wait...\n")
                
                # Use console progress for reliability
                success = upload_database(self.config)
                
                if success:
                    messagebox.showinfo("Success", "Changes saved to local and remote database.")
                else:
                    messagebox.showerror("Error", "Failed to save changes to remote database.")
        
        self.master.destroy()

def main():
    print(f"\nPeople Database Manager v{APP_VERSION}")
    print("=====================================")
    
    config = load_config()
    
    print("\nStarting database download...")
    print("Please wait, this may take a moment...")
    print("(Progress will be shown in the console)\n")
    
    # Use console progress for reliability
    download_success = download_database(config)
    
    if download_success:
        print("\nLaunching main application...")
        root = tk.Tk()
        app = PeopleDBApp(root, config)
        root.mainloop()
    else:
        print("\nFailed to download database.")
        # Create a root for the error message
        try:
            error_root = tk.Tk()
            error_root.withdraw()
            messagebox.showerror("Connection Error", "Failed to download database.\nPlease check your connection and try again.")
            error_root.destroy()
        except:
            pass

if __name__ == "__main__":
    main()