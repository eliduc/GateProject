import tkinter as tk
import tkinter as tk
import tkinter as tk
import tkinter as tk
import tkinter as tk
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, font
import sqlite3
from PIL import Image, ImageTk
from io import BytesIO
from datetime import datetime
import paramiko
import json
import os

def download_database(config):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(config['rpi_host'], username=config['rpi_user'], password=config['rpi_password'])
        sftp = ssh.open_sftp()
        sftp.get(config['db_log_path'], 'events_rm.db')  # Changed from 'db_path' to 'db_log_path'
        sftp.close()
        ssh.close()
        print("Database downloaded successfully.")
    except Exception as e:
        print(f"Error downloading database: {str(e)}")
        return False
    return True

class LogViewer:
    def __init__(self, master):
        self.master = master
        self.master.title("Event Log Viewer")
        
        # Get screen width and height
        self.screen_width = self.master.winfo_screenwidth()
        self.screen_height = self.master.winfo_screenheight()
        
        # Set window to full screen
        self.master.geometry(f"{self.screen_width}x{self.screen_height}")
        
        # Set up styles
        self.setup_styles()
        
        self.current_index = 0
        self.records = self.load_records()
        self.create_widgets()
        self.show_record()

    def setup_styles(self):
        # Create a custom style
        style = ttk.Style()
        style.theme_use('clam')

        # Define colors
        bg_color = "#f0f0f0"
        fg_color = "#333333"
        accent_color = "#4a90e2"
        disabled_color = "#cccccc"

        # Configure styles
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=('Helvetica', 10))
        style.configure("TButton", background=accent_color, foreground="white", font=('Helvetica', 10, 'bold'), padding=5)
        style.map("TButton", 
                  background=[('active', "#3a80d2"), ('disabled', disabled_color)],
                  foreground=[('disabled', '#666666')])
        
        # Apply background color to the main window
        self.master.configure(bg=bg_color)

    def load_records(self, filters=None):
        conn = sqlite3.connect('events_rm.db')
        c = conn.cursor()
        query = "SELECT * FROM events"
        params = []
        
        if filters:
            conditions = []
            if filters['date_from']:
                conditions.append("date >= ?")
                params.append(filters['date_from'])
            if filters['date_to']:
                conditions.append("date <= ?")
                params.append(filters['date_to'])
            if filters['name']:
                conditions.append("name LIKE ?")
                params.append(f"%{filters['name']}%")
            if filters['surname']:
                conditions.append("surname LIKE ?")
                params.append(f"%{filters['surname']}%")
            if filters['action'] is not None:
                conditions.append("action_code = ?")
                params.append(filters['action'])
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY date DESC, time DESC"
        
        c.execute(query, params)
        records = c.fetchall()
        conn.close()
        return records

    def create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

        # Left frame for image
        left_frame = ttk.Frame(main_frame, padding="5")
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.grid_columnconfigure(0, weight=3)

        # Right frame for info and buttons
        right_frame = ttk.Frame(main_frame, padding="5")
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.grid_columnconfigure(1, weight=1)

        # Image
        self.image_label = ttk.Label(left_frame)
        self.image_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        # Navigation buttons
        nav_frame = ttk.Frame(left_frame, padding="5")
        nav_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))

        self.prev_button = ttk.Button(nav_frame, text="Previous", command=self.show_previous)
        self.prev_button.grid(row=0, column=0, padx=(0, 5))

        self.next_button = ttk.Button(nav_frame, text="Next", command=self.show_next)
        self.next_button.grid(row=0, column=1)

        # Info labels
        info_frame = ttk.Frame(right_frame, padding="5")
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N))

        labels = ["Date:", "Time:", "Name:", "Surname:", "Action:"]
        self.info_values = {}

        for i, label in enumerate(labels):
            ttk.Label(info_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=2)
            self.info_values[label] = ttk.Label(info_frame, text="")
            self.info_values[label].grid(row=i, column=1, sticky=tk.W, pady=2)

        # Filter and Exit buttons
        self.filter_button = ttk.Button(right_frame, text="Filter", command=self.open_filter_window)
        self.filter_button.grid(row=1, column=0, pady=5, sticky=tk.E)

        self.exit_button = ttk.Button(right_frame, text="Exit", command=self.master.quit)
        self.exit_button.grid(row=2, column=0, pady=5, sticky=tk.E)

    def translate_action(self, code):
        actions = {
            1: "Correct password",
            -2: "Wrong password 3 times",
            -1: "Cancel",
            -3: "Keyboard time-out",
            2: "Ping Lev - Open Gate",
            3: "Ping Lev - Cancel",
            4: "Ping Lev - Time-out"
        }
        return actions.get(code, f"Unknown action (code: {code})")

    def show_record(self):
        if not self.records:
            messagebox.showinfo("No Records", "No records found matching the criteria.")
            return

        if 0 <= self.current_index < len(self.records):
            record = self.records[self.current_index]
            self.info_values["Date:"].config(text=record[0])
            self.info_values["Time:"].config(text=record[1])
            self.info_values["Name:"].config(text=record[3])
            self.info_values["Surname:"].config(text=record[4])
            self.info_values["Action:"].config(text=self.translate_action(record[5]))

            image_data = record[2]
            image = Image.open(BytesIO(image_data))
            
            # Calculate the aspect ratio of the image
            img_width, img_height = image.size
            aspect_ratio = img_width / img_height

            # Calculate the maximum size that fits the frame while maintaining aspect ratio
            max_width = int(self.screen_width * 0.6)  # 60% of screen width
            max_height = int(self.screen_height * 0.7)  # 70% of screen height
            
            if max_width / aspect_ratio <= max_height:
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:
                new_height = max_height
                new_width = int(max_height * aspect_ratio)

            # Resize the image
            image = image.resize((new_width, new_height), Image.LANCZOS)
            
            photo = ImageTk.PhotoImage(image)
            self.image_label.config(image=photo)
            self.image_label.image = photo

            # Update button states
            self.update_button_states()

    def update_button_states(self):
        self.prev_button.state(['!disabled'] if self.current_index < len(self.records) - 1 else ['disabled'])
        self.next_button.state(['!disabled'] if self.current_index > 0 else ['disabled'])

    def show_previous(self):
        if self.current_index < len(self.records) - 1:
            self.current_index += 1
            self.show_record()

    def show_next(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_record()

    def open_filter_window(self):
        filter_window = tk.Toplevel(self.master)
        filter_window.title("Filter Records")
        filter_window.geometry("400x300")

        ttk.Label(filter_window, text="Date From:").grid(row=0, column=0, padx=5, pady=5)
        date_from = ttk.Entry(filter_window)
        date_from.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filter_window, text="Date To:").grid(row=1, column=0, padx=5, pady=5)
        date_to = ttk.Entry(filter_window)
        date_to.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(filter_window, text="Name:").grid(row=2, column=0, padx=5, pady=5)
        name = ttk.Entry(filter_window)
        name.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(filter_window, text="Surname:").grid(row=3, column=0, padx=5, pady=5)
        surname = ttk.Entry(filter_window)
        surname.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(filter_window, text="Action:").grid(row=4, column=0, padx=5, pady=5)
        action = ttk.Combobox(filter_window, values=list(self.translate_action(i) for i in range(-3, 5)))
        action.grid(row=4, column=1, padx=5, pady=5)

        def apply_filter():
            filters = {
                'date_from': date_from.get(),
                'date_to': date_to.get(),
                'name': name.get(),
                'surname': surname.get(),
                'action': next((k for k, v in self.translate_action(0).items() if v == action.get()), None)
            }
            self.records = self.load_records(filters)
            self.current_index = 0
            self.show_record()
            filter_window.destroy()

        ttk.Button(filter_window, text="Apply Filter", command=apply_filter).grid(row=5, column=0, columnspan=2, pady=10)

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

if __name__ == "__main__":
    config = load_config()
    if download_database(config):
        root = tk.Tk()
        app = LogViewer(root)
        root.mainloop()
    else:
        print("Failed to download database. Please check your connection and try again.")