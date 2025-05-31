import tkinter as tk
from tkinter import font as tkfont
import hashlib
import time
import configparser
import multiprocessing
import os
import pandas as pd

from translations import get_translations_cached as load_translations, get_message

VERSION = "1.3"
MODIFICATIONS = "Moved load_translations, get_message to a separate module. New function get_translations_cached for caching the translation table"

# Version 1.2
# Improvements implemented:
# - Corrected alarm setup screen to ensure proper fullscreen display.
# - Applied explicit geometry settings (using screen dimensions) before the fullscreen attribute for the alarm window.
# - Verified that the alarm window and its contents now utilize the full screen dimensions, similar to the keyboard menu.

def read_timeout_from_config():
    config = configparser.ConfigParser()
    try:
        config.read('gpp.ini')
        timeout = config.getint('Time-Outs', 'to_keyb')
        return timeout
    except Exception as e:
        print(f"Error reading timeout from config: {e}")
        return 10

def keyboard_process(password_hash, max_attempts, result_queue, user_lang, user_name):
    translations = load_translations('gate_project_translations.md', user_lang)
    
    root = tk.Tk()
    root.withdraw()
    window = tk.Toplevel(root)
    window.title(get_message(15, translations))  # Enter the code
    window.attributes('-topmost', True)
    window.attributes('-fullscreen', True)
    window.focus_force()
    window.config(cursor="none")  # Hide the mouse pointer
    
    last_interaction_time = time.time()
    
    attempts = [max_attempts]
    result = [None]
    entered_code = [""]
    window_active = [True]
    scheduled_events = []

    n_to = read_timeout_from_config()

    code_var = tk.StringVar()
    user_name_var = tk.StringVar()
    rest_of_message_var = tk.StringVar()
    countdown_var = tk.StringVar()
    user_name_var.set(user_name)
    rest_of_message_var.set(f", {get_message(16, translations)} {attempts[0]}")
    countdown_var.set(str(n_to))

    def check_timeout_and_update():
        nonlocal last_interaction_time
        if not window_active[0]:
            return

        current_time = time.time()
        if current_time - last_interaction_time > n_to:
            close_window(-2)  # Timeout
        else:
            remaining_time = max(0, n_to - int(current_time - last_interaction_time))
            countdown_var.set(f"{remaining_time}")
            if remaining_time <= 3:
                countdown_display.configure(fg='red')
            elif remaining_time <= 5:
                countdown_display.configure(fg='orange')
            else:
                countdown_display.configure(fg='white')
            
            if window_active[0]:
                event_id = window.after(100, check_timeout_and_update)
                scheduled_events.append(event_id)

    def close_window(res):
        window_active[0] = False
        result[0] = res
        for event_id in scheduled_events:
            window.after_cancel(event_id)
        window.quit()

    def on_button_click(value):
        nonlocal last_interaction_time
        last_interaction_time = time.time()

        if value == get_message(32, translations):  # Enter
            if entered_code[0] == "***000***":
                close_window(-100)
                return

            should_show_alarm_setup = entered_code[0].startswith('*')
            code_to_check = entered_code[0][1:] if should_show_alarm_setup else entered_code[0]

            if code_to_check:
                entered_hash = hashlib.sha256(code_to_check.encode()).hexdigest()
                if entered_hash == password_hash:
                    if should_show_alarm_setup:
                        window.withdraw() # Withdraw the keyboard window before showing alarm setup
                        display_alarm_setup_screen()
                    else:
                        close_window(1)  # Correct password without *
                    return
                else:
                    attempts[0] -= 1
                    if attempts[0] == 0:
                        flash_failure_message()
                        close_window(-2)  # Failed: Maximum attempts reached
                        return
                    else:
                        update_message(f", {get_message(17, translations)} {attempts[0]}")
                        entered_code[0] = ""
                        code_var.set("")
            else:
                blink_message(f", {get_message(16, translations)} {attempts[0]}")
        elif value == get_message(31, translations):  # Delete
            entered_code[0] = entered_code[0][:-1]
            code_var.set('●' * len(entered_code[0]))
        elif value == get_message(33, translations):  # Cancel
            close_window(-1)  # Cancelled by user
        elif value == get_message(34, translations):  # Ping Lev
            close_window(0)  # Ping Lev
        else:
            entered_code[0] += value
            code_var.set('●' * len(entered_code[0]))

    def display_alarm_setup_screen():
            alarm_window = tk.Toplevel(root)
            alarm_window.title("Alarm Setup")

            # Query screen dimensions first
            screen_width = alarm_window.winfo_screenwidth()
            screen_height = alarm_window.winfo_screenheight()

            # --- MODIFICATIONS FOR DIRECT POSITIONING CONTROL ---
            # 1. Remove or comment out the -fullscreen attribute
            # alarm_window.attributes('-fullscreen', True) 

            # 2. Use overrideredirect to bypass window manager decorations and some positioning rules
            alarm_window.overrideredirect(True)

            # 3. Set the geometry with the negative offset to shift up
            # This will position the window's top edge 10 pixels above the screen's top edge.
            alarm_window.geometry(f"{screen_width}x{screen_height}+0-10") 
            # --- END MODIFICATIONS ---
            
            alarm_window.attributes('-topmost', True) # Keep topmost if needed
            alarm_window.focus_force()
            alarm_window.config(cursor="none")
            
            alarm_window.configure(bg='#F0F0F0')
            
            # Use a distinct name for the main frame in the alarm window
            main_alarm_frame = tk.Frame(alarm_window, bg='#F0F0F0') 
            main_alarm_frame.pack(expand=True, fill='both')
            
            main_alarm_frame.grid_columnconfigure(0, weight=1)
            main_alarm_frame.grid_columnconfigure(1, weight=1)
            main_alarm_frame.grid_rowconfigure(0, weight=1)
            main_alarm_frame.grid_rowconfigure(1, weight=1)
            
            # Use a distinct name for the button font in the alarm window
            alarm_button_font = tkfont.Font(family="Helvetica", size=int(screen_height/16), weight="bold") 
            
            # Use a distinct name for the alarm buttons configuration list
            alarm_buttons_config = [ 
                (get_message(20, translations), 11, '#4CAF50'),
                (get_message(21, translations), 12, '#2196F3'),
                (get_message(22, translations), 10, '#FFC107'),
                (get_message(23, translations), -1, '#F44336'),
            ]
            
            def handle_alarm_action(return_code):
                if alarm_window.winfo_exists(): # Check if window still exists before destroying
                    alarm_window.destroy()
                close_window(return_code) # This will call quit on the hidden root's mainloop
            
            for idx, (button_text_val, return_code_val, color_val) in enumerate(alarm_buttons_config): # Use distinct loop variables
                row_idx = idx // 2 # Use distinct loop variables
                col_idx = idx % 2 # Use distinct loop variables
                
                # Assign button to a local variable `btn_widget` to avoid potential lambda issues with `btn` from outer scope if it existed
                btn_widget = tk.Button(main_alarm_frame, text=button_text_val, font=alarm_button_font, bg=color_val, fg='white',
                                activebackground=color_val, activeforeground='white',
                                command=lambda rc=return_code_val: handle_alarm_action(rc),
                                wraplength=int(screen_width/2.2))
                
                btn_widget.grid(row=row_idx, column=col_idx, sticky='nsew')
                
                # Ensure lambda captures the correct button instance and color for hover effects
                btn_widget.bind("<Enter>", lambda event, current_btn=btn_widget: current_btn.config(bg=current_btn.cget('activebackground')))
                btn_widget.bind("<Leave>", lambda event, current_btn=btn_widget, original_color=color_val: current_btn.config(bg=original_color))
            
            # With overrideredirect(True), window manager's default Escape key behavior for fullscreen is gone.
            # This custom binding will destroy the alarm window.
            alarm_window.bind('<Escape>', lambda event: handle_alarm_action(-1)) # Or alarm_window.destroy() then close_window(-1)
            
            # WM_DELETE_WINDOW protocol might not be honored by all WMs for overrideredirect windows,
            # but it's good practice to keep it.
            alarm_window.protocol("WM_DELETE_WINDOW", lambda: handle_alarm_action(-1))
            
            alarm_window.update_idletasks()
            alarm_window.update()
            
            if main_alarm_frame.winfo_exists(): # Check if frame exists
                main_alarm_frame.update_idletasks()

    def update_message(text):
        rest_of_message_var.set(text)

    def blink_message(text):
        for _ in range(3):
            rest_of_message_var.set(text)
            window.update()
            time.sleep(0.2)
            rest_of_message_var.set("")
            window.update()
            time.sleep(0.2)
        rest_of_message_var.set(text)

    def flash_failure_message():
        failure_message = get_message(18, translations)
        bold_font = tkfont.Font(family="Helvetica", size=int(screen_height/20), weight="bold") # screen_height needs to be accessible
        
        for _ in range(5):
            rest_of_message_var.set(failure_message)
            # Ensure rest_of_message_label is configured with this font, or pass font to label
            # This part might need rest_of_message_label to be accessible or to reconfigure it here.
            # For simplicity, we assume the label exists and can be configured.
            if 'rest_of_message_label' in locals() or 'rest_of_message_label' in globals():
                 rest_of_message_label.configure(font=bold_font, fg='red')
            window.update()
            time.sleep(0.5)
            rest_of_message_var.set("")
            # Revert font if necessary
            if 'rest_of_message_label' in locals() or 'rest_of_message_label' in globals():
                rest_of_message_label.configure(font=message_font, fg=message_color) # Assuming message_font and message_color are accessible
            window.update()
            time.sleep(0.5)
        rest_of_message_var.set(failure_message)
        if 'rest_of_message_label' in locals() or 'rest_of_message_label' in globals():
            rest_of_message_label.configure(font=bold_font, fg='red') # Keep it red at the end

    # Get screen dimensions for the main keyboard window
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight() # Define screen_height for keyboard_process scope

    window.configure(bg='#F0F0F0')

    message_font_size = int(screen_height / 30)
    user_name_font_size = int(message_font_size * 1.6)
    countdown_font_size = int((screen_height / 50) * 1.5)

    user_name_font = tkfont.Font(family="Helvetica", size=user_name_font_size, weight="bold")
    message_font = tkfont.Font(family="Helvetica", size=message_font_size) # Used in flash_failure_message
    button_font = tkfont.Font(family="Helvetica", size=int(screen_height/16), weight="bold")
    countdown_font = tkfont.Font(family="Helvetica", size=countdown_font_size, weight="bold")

    message_color = '#1976D2'  # Used in flash_failure_message
    user_name_color = '#F44336'

    main_frame = tk.Frame(window, bg='#F0F0F0')
    main_frame.pack(expand=True, fill='both')

    main_frame.grid_columnconfigure((0, 1, 2), weight=1)
    main_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=1)

    top_frame = tk.Frame(main_frame, bg='#F0F0F0')
    top_frame.grid(row=0, column=0, columnspan=3, sticky='nsew')

    top_frame.grid_columnconfigure(0, weight=3)
    top_frame.grid_columnconfigure(1, weight=1)
    top_frame.grid_columnconfigure(2, weight=3)
    top_frame.grid_rowconfigure(0, weight=1)

    message_frame = tk.Frame(top_frame, bg='#F0F0F0')
    message_frame.grid(row=0, column=0, sticky='w')
    message_frame.grid_columnconfigure(0, weight=0)
    message_frame.grid_columnconfigure(1, weight=1)

    user_name_label = tk.Label(message_frame, textvariable=user_name_var, font=user_name_font, fg=user_name_color, bg='#F0F0F0', anchor='w')
    user_name_label.grid(row=0, column=0, sticky='w')

    rest_of_message_label = tk.Label(message_frame, textvariable=rest_of_message_var, font=message_font, fg=message_color, bg='#F0F0F0', anchor='w')
    rest_of_message_label.grid(row=0, column=1, sticky='w')

    countdown_display = tk.Label(top_frame, textvariable=countdown_var, font=countdown_font, fg='white', bg='#4CAF50')
    countdown_display.grid(row=0, column=1, sticky='nsew')
    countdown_display.grid_propagate(False)

    code_display = tk.Label(top_frame, textvariable=code_var, font=button_font, bg='white', fg='#333333')
    code_display.grid(row=0, column=2, sticky='nsew')

    buttons = [
        '1', '2', '3',
        '4', '5', '6',
        '7', '8', '9',
        '*', '0', get_message(31, translations),
        get_message(33, translations), get_message(34, translations), get_message(32, translations)
    ]

    colors = {
        'number': '#3F51B5',
        'action': '#00796B',
        get_message(32, translations): '#4CAF50',
        get_message(33, translations): '#F44336',
        get_message(34, translations): '#FF9800',
        get_message(31, translations): '#9E9E9E',
    }

    row_val, col_val = 1, 0 # Renamed to avoid conflict with alarm_buttons loop vars
    for button_text in buttons:
        if button_text.isdigit() or button_text == '*':
            bg_color = colors['number']
        elif button_text in [get_message(32, translations), get_message(33, translations), get_message(31, translations), get_message(34, translations)]:
            bg_color = colors[button_text]
        else:
            bg_color = colors['action']
        
        btn = tk.Button(main_frame, text=button_text, font=button_font, bg=bg_color, fg='white',
                        activebackground=bg_color, activeforeground='white',
                        command=lambda x=button_text: on_button_click(x))
        
        btn.grid(row=row_val, column=col_val, sticky='nsew')
        
        col_val += 1
        if col_val >= 3:
            col_val = 0
            row_val += 1

    window.bind('<Escape>', lambda event: window.attributes('-fullscreen', False))
    window.protocol("WM_DELETE_WINDOW", lambda: close_window(-1))

    check_timeout_id = window.after(100, check_timeout_and_update)
    scheduled_events.append(check_timeout_id)

    window.mainloop()
    result_queue.put(result[0])

def create_keyboard(password_hash, max_attempts, user_lang, user_name):
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=keyboard_process, args=(password_hash, max_attempts, result_queue, user_lang, user_name))
    process.start()
    process.join()
    result = result_queue.get()
    return result

if __name__ == "__main__":
    # Create a dummy gpp.ini for testing if it doesn't exist
    if not os.path.exists('gpp.ini'):
        config = configparser.ConfigParser()
        config['Time-Outs'] = {'to_keyb': '60'} # Default 60s timeout for testing
        with open('gpp.ini', 'w') as configfile:
            config.write(configfile)

    # Create a dummy translations file for testing if it doesn't exist
    if not os.path.exists('gate_project_translations.md'):
        translations_content = """Phrase ID|EN|IT
--- | --- | ---
15|Enter the code|Inserisci il codice
16|attempts left:|tentativi rimasti:
17|Incorrect. Attempts left:|Errato. Tentativi rimasti:
18|Failed! The police is on their way!|Fallito! La polizia sta arrivando!
20|Set Alarm (Day Mode)|Imposta Allarme (Giorno)
21|Set Alarm (Night Mode)|Imposta Allarme (Notte)
22|Switch Off Alarm|Disattiva Allarme
23|Cancel|Annulla
31|Delete|Cancella
32|Enter|Invio
33|Cancel|Annulla
34|Ping Lev|Chiama Lev
"""
        with open('gate_project_translations.md', 'w', encoding='utf-8') as f:
            f.write(translations_content)
            
    password_hash = hashlib.sha256("1234".encode()).hexdigest()
    max_attempts = 3
    user_lang = "EN"
    user_name = "Test User"
    result = create_keyboard(password_hash, max_attempts, user_lang, user_name)
    print(f"Keyboard result: {result}")