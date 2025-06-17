import configparser
from ControlSwitch import control_shelly_switch
# from ReadIFTTT import check_alarm_state  # Not used in current version
import time
import pygame
import sys
import os
import pandas as pd

from translations import get_translations_cached as load_translations, get_message

def alarm_on(NightMode, user_lang, system):
    """
    Turn on alarm
    
    Args:
        NightMode: Whether to use night mode
        user_lang: Language code
        system: UnifiedGateSystem instance (required)
    """
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
        from Alarm_Off import alarm_off
        alarm_off(user_lang, system, False)    #Comment when check_alarm_state() is corrected
        time.sleep(2)
        
        return set_alarm(ip_relay, translations, system)
    elif alarm_state == 1:  # Alarm is already on
        return confirm_set_alarm(ip_relay, translations, system)
    else:
        system.show_message(get_message(25, translations), 5)  # Error reading alarm state
        return -1

def set_alarm(ip_relay, translations, system):
    try:
        control_shelly_switch(ip_relay)
        alarm_state = 1 # delete when alarm_state will be controlled
        
        for attempt in range(3):
            #alarm_state = check_alarm_state()
            
            if alarm_state == 1:
                system.show_message(get_message(27, translations), 2)  # The alarm is set!
                return 1
            
            time.sleep(2)
            
        system.show_message(get_message(28, translations), 5)  # Failed to set the alarm
        return 0
    
    except Exception as e:
        error_msg = f"{get_message(29, translations)} {str(e)}"  # An error occurred when setting alarm
        system.show_message(error_msg, 5)
        return -1

def confirm_set_alarm(ip_relay, translations, system):
    # Use pygame confirmation dialog
    result = ask_confirmation_pygame(system, get_message(30, translations))  # The alarm appears to be set
    
    if result:
        return set_alarm(ip_relay, translations, system)
    else:
        return 2

def ask_confirmation_pygame(system, message):
    """Ask confirmation using pygame (unified system)"""
    font = system.get_font(int(system.screen_height / 20))
    button_font = system.get_font(int(system.screen_height / 16))
    
    running = True
    result = None
    
    while running:
        system.screen.fill(system.bg_color)
        
        # Draw message
        lines = system.text_wrap(message + " (Y/N)?", font, system.screen_width * 0.8)
        y = system.screen_height // 3
        
        for line in lines:
            text_surface = font.render(line, True, system.text_color)
            text_rect = text_surface.get_rect(center=(system.screen_width // 2, y))
            system.screen.blit(text_surface, text_rect)
            y += font.get_linesize()
        
        # Draw buttons
        button_width = system.screen_width // 3
        button_height = system.screen_height // 6
        button_y = system.screen_height * 2 // 3
        
        # Yes button
        yes_rect = pygame.Rect(system.screen_width // 4 - button_width // 2, 
                               button_y, button_width, button_height)
        pygame.draw.rect(system.screen, (76, 175, 80), yes_rect)
        pygame.draw.rect(system.screen, (255, 255, 255), yes_rect, 2)
        yes_text = button_font.render("Yes (Y)", True, (255, 255, 255))
        yes_text_rect = yes_text.get_rect(center=yes_rect.center)
        system.screen.blit(yes_text, yes_text_rect)
        
        # No button
        no_rect = pygame.Rect(3 * system.screen_width // 4 - button_width // 2,
                              button_y, button_width, button_height)
        pygame.draw.rect(system.screen, (244, 67, 54), no_rect)
        pygame.draw.rect(system.screen, (255, 255, 255), no_rect, 2)
        no_text = button_font.render("No (N)", True, (255, 255, 255))
        no_text_rect = no_text.get_rect(center=no_rect.center)
        system.screen.blit(no_text, no_text_rect)
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result = False
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    result = True
                    running = False
                elif event.key == pygame.K_n or event.key == pygame.K_ESCAPE:
                    result = False
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if yes_rect.collidepoint(event.pos):
                    result = True
                    running = False
                elif no_rect.collidepoint(event.pos):
                    result = False
                    running = False
        
        system.clock.tick(30)
    
    return result

if __name__ == "__main__":
    # This won't work without system object
    print("This module requires UnifiedGateSystem instance")
    print("Please run gpp.py instead")