import pygame
import os

pygame.init()

# Create a small window
screen = pygame.display.set_mode((800, 600))
screen.fill((255, 255, 255))

# Test text
hebrew_text = "זוהו פנים. אנא המתן..."  # "Face detected. Please wait..." in Hebrew
english_text = "Face detected. Please wait..."

# Try different font loading methods
print("Testing Hebrew rendering...")

# Method 1: Default font
try:
    font1 = pygame.font.Font(None, 48)
    text1 = font1.render(hebrew_text, True, (0, 0, 0))
    screen.blit(text1, (10, 10))
    print("Method 1 (default font): Rendered")
except Exception as e:
    print(f"Method 1 failed: {e}")

# Method 2: Specific font files that exist on your system
font_paths = [
    "/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSerifHebrew-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/culmus/DavidCLM-Medium.otf",
    "/usr/share/fonts/truetype/ezra/SILEOT.ttf",
]

y_pos = 100
for font_path in font_paths:
    if os.path.exists(font_path):
        try:
            font = pygame.font.Font(font_path, 36)
            text = font.render(hebrew_text, True, (0, 0, 0))
            screen.blit(text, (10, y_pos))
            
            # Also show the font name
            font_name = os.path.basename(font_path)
            label_font = pygame.font.Font(None, 20)
            label = label_font.render(font_name, True, (0, 0, 255))
            screen.blit(label, (10, y_pos + 40))
            
            print(f"Success: {font_path}")
            y_pos += 70
        except Exception as e:
            print(f"Failed: {font_path} - {e}")
    else:
        print(f"Not found: {font_path}")

# Also render English to compare
font_eng = pygame.font.Font(None, 48)
text_eng = font_eng.render(english_text, True, (0, 0, 255))
screen.blit(text_eng, (10, y_pos))

pygame.display.flip()

# Keep window open
print("\nPress Ctrl+C to exit...")
running = True
clock = pygame.time.Clock()
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    clock.tick(30)

pygame.quit()
