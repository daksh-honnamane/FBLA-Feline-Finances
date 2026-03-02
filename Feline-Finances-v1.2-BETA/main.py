import json
import os
import pygame
import sys
import random

pygame.init()
pygame.mixer.init()

# -------------------- SOUNDS --------------------
click_sounds = [pygame.mixer.Sound(f"assets/sounds/click_00{i}.ogg") for i in range(1, 6)]
error_sound = pygame.mixer.Sound("assets/sounds/error_005.ogg")

# -------------------- CAT IMAGES --------------------
cat_images = {
    "Orange": pygame.image.load("assets/cats/orange.png"),
    "Grey": pygame.image.load("assets/cats/grey.png"),
    "White": pygame.image.load("assets/cats/white.png"),
    "Calico": pygame.image.load("assets/cats/calico.png")
}

# -------------------- WINDOW --------------------
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Feline Finances")
icon = pygame.image.load("assets/ui/icon.png")
pygame.display.set_icon(icon)

clock = pygame.time.Clock()
font = pygame.font.SysFont("Comic Sans MS", 20)
big_font = pygame.font.SysFont("Comic Sans MS", 32)

# -------------------- COLORS --------------------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
COZY = (249, 230, 197)
BUTTON = (155, 182, 130)
BUTTON_HOVER = (135, 162, 110)

# -------------------- SAVE SETTINGS --------------------
SAVE_FILE = "save_data.json"
AUTOSAVE_INTERVAL = 10000

# -------------------- CAT CLASS --------------------
class Cat:
    def __init__(self, name, cat_type, personality):
        self.name = name
        self.cat_type = cat_type
        self.personality = personality
        self.hunger = 100
        self.happiness = 100
        self.energy = 100
        self.cleanliness = 100
        self.health = 100

    def feed(self):
        self.hunger = min(100, self.hunger + 20)

    def play(self):
        self.happiness = min(100, self.happiness + 20)
        self.energy = max(0, self.energy - 5)
        self.update_health()

    def rest(self):
        self.energy = min(100, self.energy + 30)
        self.happiness = min(100, self.happiness + 5)
        self.update_health()

    def clean(self):
        self.cleanliness = min(100, self.cleanliness + 30)
        self.happiness = min(100, self.happiness + 5)
        self.update_health()

    def update_health(self):
        self.health = (self.hunger + self.happiness + self.energy + self.cleanliness) / 4

# -------------------- SAVE / LOAD --------------------
def save_game(cat, money, total_spent, inventory):
    data = {
        "name": cat.name,
        "type": cat.cat_type,
        "personality": cat.personality,
        "stats": vars(cat),
        "money": money,
        "total_spent": total_spent,
        "inventory": inventory
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_game():
    if not os.path.exists(SAVE_FILE):
        return None
    with open(SAVE_FILE, "r") as f:
        return json.load(f)

# -------------------- HELPERS --------------------
def get_mood(cat):
    if cat.health < 40:
        return "Sick"
    elif cat.happiness < 40:
        return "Sad"
    elif cat.energy > 80:
        return "Energetic"
    return "Happy"

def draw_text(text, x, y, color=BLACK, f=font):
    screen.blit(f.render(text, True, color), (x, y))

def draw_stat_bar(x, y, width, height, value, max_value, color):
    # Background
    pygame.draw.rect(screen, (180, 180, 180), (x, y, width, height), border_radius=5)
    # Foreground
    fill_width = int(width * (value / max_value))
    pygame.draw.rect(screen, color, (x, y, fill_width, height), border_radius=5)
    # Border
    pygame.draw.rect(screen, BLACK, (x, y, width, height), 2, border_radius=5)

def draw_button(rect, text, check_hover=True):
    mouse = pygame.mouse.get_pos()
    color = BUTTON_HOVER if (check_hover and rect.collidepoint(mouse)) else BUTTON
    # Shadow
    shadow_rect = pygame.Rect(rect.x + 3, rect.y + 3, rect.width, rect.height)
    pygame.draw.rect(screen, (150, 150, 150), shadow_rect, border_radius=10)
    # Button
    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, rect, 2, border_radius=10)
    # Centered text
    text_surf = font.render(text, True, BLACK)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)

# -------------------- SETUP SCREEN (UPGRADED) --------------------
def setup_screen():
    name = ""
    types = ["Orange", "Grey", "White", "Calico"]
    personalities = ["Playful", "Lazy", "Shy", "Energetic"]

    type_index = 0
    pers_index = 0
    selection = 0

    arrow_offset = 0
    arrow_dir = 1

    while True:
        screen.fill(COZY)

        arrow_offset += arrow_dir * 0.5
        if abs(arrow_offset) > 5:
            arrow_dir *= -1

        draw_text("Create Your Cat", 50, 30, f=big_font)
        draw_text("UP/DOWN to select | LEFT/RIGHT to change | ENTER to confirm", 50, 70)

        rows = [140, 200, 260, 340]
        # Draw selection arrow
        pygame.draw.polygon(
            screen, BLACK,
            [(30 + arrow_offset, rows[selection] + 10),
             (50 + arrow_offset, rows[selection]),
             (50 + arrow_offset, rows[selection] + 20)]
        )

        draw_text("Name:", 60, 140)
        draw_text(name if name else "_", 200, 140)
        draw_text("Cat Type:", 60, 200)
        draw_text(types[type_index], 200, 200)
        draw_text("Personality:", 60, 260)
        draw_text(personalities[pers_index], 200, 260)
        draw_text("Start Game", 60, 340)

        # Preview cat
        preview_x, preview_y = 640, 260
        scale_x, scale_y = 150, 150
        cat_image = cat_images[types[type_index]]
        scaled_cat = pygame.transform.scale(cat_image, (scale_x, scale_y))
        cat_rect = scaled_cat.get_rect(center=(preview_x, preview_y))
        screen.blit(scaled_cat, cat_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selection = (selection - 1) % 4
                    random.choice(click_sounds).play()
                elif event.key == pygame.K_DOWN:
                    selection = (selection + 1) % 4
                    random.choice(click_sounds).play()
                elif event.key == pygame.K_LEFT:
                    if selection == 1:
                        type_index = (type_index - 1) % len(types)
                        random.choice(click_sounds).play()
                    elif selection == 2:
                        pers_index = (pers_index - 1) % len(personalities)
                        random.choice(click_sounds).play()
                elif event.key == pygame.K_RIGHT:
                    if selection == 1:
                        type_index = (type_index + 1) % len(types)
                        random.choice(click_sounds).play()
                    elif selection == 2:
                        pers_index = (pers_index + 1) % len(personalities)
                        random.choice(click_sounds).play()
                elif selection == 0:
                    if event.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                        random.choice(click_sounds).play()
                    elif event.unicode.isalpha() and len(name) < 10:
                        name += event.unicode
                        random.choice(click_sounds).play()
                elif event.key == pygame.K_RETURN and selection == 3 and name:
                    random.choice(click_sounds).play()
                    pygame.time.delay(200)
                    return name, types[type_index], personalities[pers_index]

        pygame.display.flip()
        clock.tick(60)

# -------------------- GAME SETUP --------------------
save_data = load_game()

if save_data:
    cat = Cat(save_data["name"], save_data["type"], save_data["personality"])
    for k, v in save_data["stats"].items():
        setattr(cat, k, v)
    money = save_data["money"]
    total_spent = save_data["total_spent"]
    inventory = save_data["inventory"]
else:
    cat_name, cat_type, personality = setup_screen()
    cat = Cat(cat_name, cat_type, personality)
    money = 50
    total_spent = 0
    inventory = {}

store_prices = {"Meowmunch": 5, "Purrplay": 10, "Furbath": 15}

# Store UI message/tooltip state
STORE_MSG_DURATION = 2000  # ms
store_message = ""
store_message_timer = 0

feed_btn = pygame.Rect(50, 500, 100, 40)
play_btn = pygame.Rect(160, 500, 100, 40)
clean_btn = pygame.Rect(270, 500, 100, 40)
rest_btn = pygame.Rect(380, 500, 100, 40)
chore_btn = pygame.Rect(700, 500, 160, 40)
store_btn = pygame.Rect(700, 440, 160, 40)

# -------------------- MAIN LOOP --------------------
running = True
time_passed = autosave_timer = 0
in_store = False
in_chore = False
active_minigame = None
trash_items = []
trash_collected = 0

while running:
    dt = clock.tick(60)
    time_passed += dt
    autosave_timer += dt
    store_message_timer = max(0, store_message_timer - dt)

    if autosave_timer >= AUTOSAVE_INTERVAL:
        save_game(cat, money, total_spent, inventory)
        autosave_timer = 0

    screen.fill(COZY)

    # -------------------- EVENT HANDLING --------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_game(cat, money, total_spent, inventory)
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and in_store:
                in_store = False
            if event.key == pygame.K_ESCAPE and in_chore:
                in_chore = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if in_store:
                # clicks only affect store overlay while open
                overlay_w = int(WIDTH * 0.7)
                overlay_h = int(HEIGHT * 0.7)
                overlay_x = (WIDTH - overlay_w) // 2
                overlay_y = (HEIGHT - overlay_h) // 2

                # Back button (top-right of overlay)
                back_rect = pygame.Rect(overlay_x + overlay_w - 110, overlay_y + 16, 90, 36)
                if back_rect.collidepoint(event.pos):
                    random.choice(click_sounds).play()
                    in_store = False
                else:
                    item_x = overlay_x + 40
                    y = overlay_y + 80
                    item_w = overlay_w - 80
                    item_h = 50
                    for item, price in store_prices.items():
                        rect = pygame.Rect(item_x, y, item_w, item_h)
                        if rect.collidepoint(event.pos):
                            if money >= price:
                                random.choice(click_sounds).play()
                                money -= price
                                total_spent += price
                                inventory[item] = inventory.get(item, 0) + 1
                            else:
                                # show temporary insufficient funds message
                                error_sound.play()
                                store_message = "Insufficient funds"
                                store_message_timer = STORE_MSG_DURATION
                        y += item_h + 20
            elif in_chore:
                # Handle minigame interactions
                if active_minigame == "trash":
                    # Check if trash items were clicked
                    for trash in trash_items:
                        if not trash["collected"]:
                            trash_rect = pygame.Rect(trash["x"], trash["y"], 30, 30)
                            if trash_rect.collidepoint(event.pos):
                                random.choice(click_sounds).play()
                                trash["collected"] = True
                
                # clicks only affect chore overlay while open
                overlay_w = int(WIDTH * 0.7)
                overlay_h = int(HEIGHT * 0.7)
                overlay_x = (WIDTH - overlay_w) // 2
                overlay_y = (HEIGHT - overlay_h) // 2

                # Back button (top-right of overlay)
                back_rect = pygame.Rect(overlay_x + overlay_w - 110, overlay_y + 16, 90, 36)
                if back_rect.collidepoint(event.pos):
                    random.choice(click_sounds).play()
                    in_chore = False
                    active_minigame = None
                else:
                    # Chore buttons (only show if not in minigame)
                    if not active_minigame:
                        chore_x = overlay_x + 50
                        chore_y = overlay_y + 100
                        chore_w = overlay_w - 100
                        chore_h = 60
                        chores = [("Take Out The Trash", "trash"), ("Put Away Laundry", "laundry"), ("Stove Top Sizzler", "stovetop")]
                        for i, (chore_name, chore_id) in enumerate(chores):
                            rect = pygame.Rect(chore_x, chore_y + i * (chore_h + 20), chore_w, chore_h)
                            if rect.collidepoint(event.pos):
                                random.choice(click_sounds).play()
                                active_minigame = chore_id
                                if chore_id == "trash":
                                    trash_items = []
                                    trash_collected = 0
                                    for j in range(5):
                                        x = overlay_x + 80 + random.randint(0, overlay_w - 160)
                                        y = overlay_y + 120 + random.randint(0, overlay_h - 200)
                                        trash_items.append({"x": x, "y": y, "collected": False})
            else:
                # normal game buttons (only when store/chore is closed)
                if feed_btn.collidepoint(event.pos) and inventory.get("Meowmunch", 0) > 0:
                    random.choice(click_sounds).play()
                    cat.feed()
                    inventory["Meowmunch"] -= 1
                if play_btn.collidepoint(event.pos) and inventory.get("Purrplay", 0) > 0:
                    random.choice(click_sounds).play()
                    cat.play()
                    inventory["Purrplay"] -= 1
                if rest_btn.collidepoint(event.pos):
                    random.choice(click_sounds).play()
                    cat.rest()
                if clean_btn.collidepoint(event.pos) and inventory.get("Furbath", 0) > 0:
                    random.choice(click_sounds).play()
                    cat.clean()
                    inventory["Furbath"] -= 1
                if chore_btn.collidepoint(event.pos):
                    random.choice(click_sounds).play()
                    in_chore = True
                if store_btn.collidepoint(event.pos):
                    random.choice(click_sounds).play()
                    in_store = not in_store

    # -------------------- TIME PASSING --------------------
    if time_passed > 5000:
        cat.hunger = max(0, cat.hunger - 2)
        cat.happiness = max(0, cat.happiness - 1)
        cat.energy = max(0, cat.energy - 1)
        cat.cleanliness = max(0, cat.cleanliness - 1)
        cat.update_health()
        time_passed = 0

    # -------------------- POLISHED UI --------------------
    # Left panel stats
    panel_x = 50
    panel_y = 140
    panel_spacing = 35
    bar_width = 200
    bar_height = 20

    stats = [
        ("Hunger", cat.hunger, (255, 100, 100)),
        ("Happiness", cat.happiness, (255, 255, 100)),
        ("Energy", cat.energy, (100, 255, 100)),
        ("Cleanliness", cat.cleanliness, (100, 200, 255)),
        ("Health", cat.health, (255, 150, 255))
    ]

    draw_text(f"{cat.name} the {cat.cat_type} Cat", 50, 30, f=big_font)
    draw_text(f"Personality: {cat.personality}", 50, 70)
    draw_text(f"Mood: {get_mood(cat)}", 50, 100)

    for i, (label, value, color) in enumerate(stats):
        y = panel_y + i * panel_spacing
        draw_text(label, panel_x, y)
        draw_stat_bar(panel_x + 120, y, bar_width, bar_height, value, 100, color)

    # Right panel money/inventory
    right_x = 700
    draw_text(f"Total Spent: ${total_spent}", right_x, 50)
    draw_text(f"Money: ${money}", right_x, 80)
    draw_text(f"Meowmunch: {inventory.get('Meowmunch',0)}", right_x, 110)
    draw_text(f"Purrplay: {inventory.get('Purrplay',0)}", right_x, 140)
    draw_text(f"Furbath: {inventory.get('Furbath',0)}", right_x, 170)

    # Buttons (disable hover when store/chore is open)
    draw_button(feed_btn, "Feed", check_hover=not in_store and not in_chore)
    draw_button(play_btn, "Play", check_hover=not in_store and not in_chore)
    draw_button(rest_btn, "Rest", check_hover=not in_store and not in_chore)
    draw_button(clean_btn, "Clean", check_hover=not in_store and not in_chore)
    draw_button(chore_btn, "The Taskboard", check_hover=not in_store and not in_chore)
    draw_button(store_btn, "Whiskermart", check_hover=not in_store and not in_chore)

    # Chore overlay (centered, covers ~70% of screen)
    if in_chore:
        overlay_w = int(WIDTH * 0.7)
        overlay_h = int(HEIGHT * 0.7)
        overlay_x = (WIDTH - overlay_w) // 2
        overlay_y = (HEIGHT - overlay_h) // 2

        # Semi-transparent dimming layer
        dim_surf = pygame.Surface((WIDTH, HEIGHT))
        dim_surf.set_alpha(120)
        dim_surf.fill(BLACK)
        screen.blit(dim_surf, (0, 0))

        # Shadow
        pygame.draw.rect(screen, (150, 150, 150), (overlay_x+6, overlay_y+6, overlay_w, overlay_h), border_radius=12)
        # Background
        pygame.draw.rect(screen, COZY, (overlay_x, overlay_y, overlay_w, overlay_h), border_radius=12)
        pygame.draw.rect(screen, BLACK, (overlay_x, overlay_y, overlay_w, overlay_h), 2, border_radius=12)

        # Back button (top-right)
        back_rect = pygame.Rect(overlay_x + overlay_w - 110, overlay_y + 16, 90, 36)
        draw_button(back_rect, "Back")

        # Handle minigames
        if active_minigame == "trash":
            # Render trash minigame
            draw_text("Take Out The Trash", overlay_x + 20, overlay_y + 12, f=big_font)
            
            # Count collected trash
            trash_collected = sum(1 for t in trash_items if t["collected"])
            draw_text(f"Trash: {trash_collected}/5 Collected", overlay_x + 50, overlay_y + 70)
            
            # Draw trash items
            for trash in trash_items:
                if not trash["collected"]:
                    trash_rect = pygame.Rect(trash["x"], trash["y"], 30, 30)
                    pygame.draw.rect(screen, (139, 90, 43), trash_rect, border_radius=5)
                    pygame.draw.rect(screen, BLACK, trash_rect, 2, border_radius=5)
            
            # Check if all trash collected
            if trash_collected == 5:
                money += 5
                active_minigame = None
                trash_items = []
        else:
            # Show chore buttons
            draw_text("The Taskboard", overlay_x + 20, overlay_y + 12, f=big_font)

            # Chore buttons
            chore_x = overlay_x + 50
            chore_y = overlay_y + 100
            chore_w = overlay_w - 100
            chore_h = 60
            chores = [("Take Out The Trash", "trash"), ("Put Away Laundry", "laundry"), ("Stove Top Sizzler", "stovetop")]
            for i, (chore_name, chore_id) in enumerate(chores):
                rect = pygame.Rect(chore_x, chore_y + i * (chore_h + 20), chore_w, chore_h)
                draw_button(rect, chore_name)

    # Store overlay (centered, covers ~70% of screen)
    if in_store:
        overlay_w = int(WIDTH * 0.7)
        overlay_h = int(HEIGHT * 0.7)
        overlay_x = (WIDTH - overlay_w) // 2
        overlay_y = (HEIGHT - overlay_h) // 2

        # Semi-transparent dimming layer
        dim_surf = pygame.Surface((WIDTH, HEIGHT))
        dim_surf.set_alpha(120)
        dim_surf.fill(BLACK)
        screen.blit(dim_surf, (0, 0))

        # Shadow
        pygame.draw.rect(screen, (150, 150, 150), (overlay_x+6, overlay_y+6, overlay_w, overlay_h), border_radius=12)
        # Background
        pygame.draw.rect(screen, COZY, (overlay_x, overlay_y, overlay_w, overlay_h), border_radius=12)
        pygame.draw.rect(screen, BLACK, (overlay_x, overlay_y, overlay_w, overlay_h), 2, border_radius=12)

        # Title and money
        draw_text("Whiskermart", overlay_x + 20, overlay_y + 12, f=big_font)
        draw_text(f"Money: ${money}", overlay_x + overlay_w - 260, overlay_y + 20)

        # Back button (top-right)
        back_rect = pygame.Rect(overlay_x + overlay_w - 110, overlay_y + 16, 90, 36)
        draw_button(back_rect, "Back")

        # Items with hover detection
        item_x = overlay_x + 40
        y = overlay_y + 80
        item_w = overlay_w - 80
        item_h = 50
        mouse = pygame.mouse.get_pos()
        for item, price in store_prices.items():
            rect = pygame.Rect(item_x, y, item_w, item_h)
            draw_button(rect, f"{item.title()} - ${price}")
            # Hover tooltip
            if rect.collidepoint(mouse):
                if money < price:
                    tooltip = "Not enough money"
                else:
                    tooltip = "Click to buy"
                tooltip_surf = font.render(tooltip, True, BLACK)
                tooltip_x = rect.right + 10
                tooltip_y = rect.centery - tooltip_surf.get_height() // 2
                pygame.draw.rect(screen, (255, 255, 200), (tooltip_x - 5, tooltip_y - 2, tooltip_surf.get_width() + 10, tooltip_surf.get_height() + 4))
                pygame.draw.rect(screen, BLACK, (tooltip_x - 5, tooltip_y - 2, tooltip_surf.get_width() + 10, tooltip_surf.get_height() + 4), 1)
                screen.blit(tooltip_surf, (tooltip_x, tooltip_y))
            y += item_h + 20
        
        # Show insufficient funds message
        if store_message_timer > 0:
            msg_surf = font.render(store_message, True, (255, 50, 50))
            msg_x = overlay_x + (overlay_w - msg_surf.get_width()) // 2
            msg_y = overlay_y + overlay_h - 50
            pygame.draw.rect(screen, (255, 200, 200), (msg_x - 10, msg_y - 5, msg_surf.get_width() + 20, msg_surf.get_height() + 10), border_radius=5)
            pygame.draw.rect(screen, (200, 0, 0), (msg_x - 10, msg_y - 5, msg_surf.get_width() + 20, msg_surf.get_height() + 10), 2, border_radius=5)
            screen.blit(msg_surf, (msg_x, msg_y))
        else:
            store_message = ""

    pygame.display.flip()

pygame.quit()
sys.exit()