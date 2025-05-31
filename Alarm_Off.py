import configparser
from ControlSwitch import control_shelly_switch
import time
import pygame
import sys
import os
import pandas as pd

from translations import get_translations_cached as load_translations, get_message

from fullscreen_message import show_fullscreen_message

# Uncheck when check_alarm_state is corrected
#from ReadIFTTT import check_alarm_state


def alarm_off(user_lang, message=True): 
    translations = load_translations('gate_project_translations.md', user_lang)
    
    config = configparser.ConfigParser()
    config.read('gpp.ini')
    ip_off = config['IP_adresses']['ip_off'].strip('"')

    for attempt in range(3):
        try:
            control_shelly_switch(ip_off)
            
            #turning off alarm check. Uncomment when check_alarm_state() corrected
            #alarm_state = check_alarm_state()
            alarm_state = 0 
            
            if alarm_state == 0:
                if message:
                    show_fullscreen_message(get_message(24, translations))  # Alarm successfully switched off
                return 1
            
            if attempt < 2:
                time.sleep(2)
        
        except Exception as e:
            error_message = f"{get_message(25, translations)} {str(e)}"  # An error occurred:
            if attempt == 2:  # Show message only on the last attempt
                show_fullscreen_message(error_message, 5)
            if attempt < 2:
                time.sleep(5)
            else:
                return -1
    
    show_fullscreen_message(get_message(26, translations), 5)  # Failed to switch off the alarm
    return -1

if __name__ == "__main__":
    user_lang = "EN"  # Default language for testing
    result = alarm_off(user_lang)
    print(f"Alarm_Off result: {result}")
    show_fullscreen_message(get_message(1, load_translations('gate_project_translations.md', user_lang)), 3)  # Welcome to Gate System (as a test message)
    pygame.quit()
    sys.exit()