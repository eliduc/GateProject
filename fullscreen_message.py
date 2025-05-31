import pygame
import os

class FullScreenMessage:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            pygame.init()
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.width, self.height = self.screen.get_size()
            self.font_cache = {}
            self.bg_color = (44, 62, 80)  # Dark blue-grey background
            self.text_color = (236, 240, 241)  # Light grey text
            self.initialized = True

    def show_message(self, message, duration=0):
        self.screen.fill(self.bg_color)
        font_size = self.calculate_font_size(message)
        font = self.get_font(font_size)
        
        lines = self.text_wrap(message, font, self.width * 0.8)
        y = self.height // 2 - (len(lines) * font.get_linesize()) // 2

        for line in lines:
            text_surface = font.render(line, True, self.text_color)
            text_rect = text_surface.get_rect(center=(self.width // 2, y))
            self.screen.blit(text_surface, text_rect)
            y += font.get_linesize()

        pygame.display.flip()

        if duration > 0:
            pygame.time.wait(int(duration * 1000))

    def calculate_font_size(self, message):
        target_height = self.height * 0.5
        max_font_size = self.height // 4
        
        for font_size in range(max_font_size, 10, -1):
            font = self.get_font(font_size)
            lines = self.text_wrap(message, font, self.width * 0.8)
            total_height = font.get_linesize() * len(lines)
            
            if total_height <= target_height:
                return font_size
        
        return 10

    def get_font(self, size):
        # Create a cache key that includes size
        cache_key = f"universal_{size}"
        
        if cache_key not in self.font_cache:
            # Use fonts that support multiple scripts including Hebrew
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
                        #print(f"Loaded font: {font_path} for size {size}")
                        font_loaded = True
                        break
                    except Exception as e:
                        continue
            
            if not font_loaded:
                self.font_cache[cache_key] = pygame.font.Font(None, size)
                print(f"Using default font for size {size}")
                    
        return self.font_cache[cache_key]

    def text_wrap(self, text, font, max_width):
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

def show_fullscreen_message(message, duration=0):
    """Convenience function to show a fullscreen message"""
    app = FullScreenMessage()
    app.show_message(message, duration)