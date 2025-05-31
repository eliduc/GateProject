import configparser
from ControlSwitch import control_shelly_switch
from ReadIFTTT import check_alarm_state
import time
import pygame
import sys
import os
import pandas as pd

from Alarm_Off import alarm_off
from fullscreen_message import FullScreenMessage, show_fullscreen_message

from translations import get_translations_cached as load_translations, get_message

def alarm_on(NightMode, user_lang):
    translations = load_translations('gate_project_translations.md', user_lang)
    
    config = configparser.ConfigParser()
    config.read('gpp.ini')
    
    if NightMode:
        ip_relay = config['IP_adresses']['ip_night'].strip('"')
    else:
        ip_relay = config['IP_adresses']['ip_arm'].strip('"')
    
    # Uncheck when check_alarm_state() is corrected
    alarm_state = 0
    #alarm_state = check_alarm_state()
    
    if alarm_state == 0:  # Alarm is off
        alarm_off(user_lang, False)    #Comment when check_alarm_state() is corrected
        time.sleep(2)
        
        return set_alarm(ip_relay, translations)
    elif alarm_state == 1:  # Alarm is already on
        return confirm_set_alarm(ip_relay, translations)
    else:
        show_fullscreen_message(get_message(25, translations), 5)  # Error reading alarm state
        return -1

def set_alarm(ip_relay, translations):
    try:
        control_shelly_switch(ip_relay)
        alarm_state = 1 # delete when alarm_state will be controlled
        
        for attempt in range(3):
            #alarm_state = check_alarm_state()
            
            if alarm_state == 1:
                show_fullscreen_message(get_message(27, translations), 2)  # The alarm is set!
                return 1
            
            time.sleep(2)
            
        show_fullscreen_message(get_message(28, translations), 5)  # Failed to set the alarm
        return 0
    
    except Exception as e:
        show_fullscreen_message(f"{get_message(29, translations)} {str(e)}", 5)  # An error occurred when setting alarm
        return -1

def confirm_set_alarm(ip_relay, translations):
    app = FullScreenMessage()
    result = ask_confirmation(app, get_message(30, translations))  # The alarm appears to be set
    
    if result:
        return set_alarm(ip_relay, translations)
    else:
        return 2

def ask_confirmation(app, message):
    app.show_message(message)
    clock = pygame.time.Clock()
    result = None

    while result is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    result = True
                elif event.key == pygame.K_n:
                    result = False

        pygame.display.flip()
        clock.tick(30)

    return result

if __name__ == "__main__":
    pygame.init()
    user_lang = "EN"  # Default language for testing
    result = alarm_on(True, user_lang)  # Test with Night Mode
    print(f"Alarm_On result: {result}")
    pygame.quit()
    sys.exit()