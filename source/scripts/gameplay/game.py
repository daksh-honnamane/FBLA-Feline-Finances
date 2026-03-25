import random
import sys

import pygame

from core.config import AUTOSAVE_INTERVAL, BLACK, BLUE, BUTTON, COZY, GOLD, HEIGHT, ITEM_DETAILS, PANEL, RED, SAVE_GOAL, STORE_ITEMS, TIME_STEP_MS, VET_COST, VET_HEAL, WHITE, WIDTH
from core.models import Cat
from core.storage import create_default_progress, load_game, reset_save_file, save_game
from engine.assets_loader import load_assets
from interface.ui import UIContext, setup_screen


class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.ui = UIContext()
        assets = load_assets()
        self.click_sounds = assets["click_sounds"]
        self.error_sound = assets["error_sound"]
        self.cat_images = assets["cat_images"]
        self.title_image = assets["title_image"]
        self.title_size = self.title_image.get_size()
        self.title_button_rect = pygame.Rect(1160, 190, 780, 205)
        self.title_button_radius = 36
        self.scaled_title_image = None
        self.scaled_title_size = None
        self.snapshot_font = pygame.font.SysFont("Comic Sans MS", 14)
        self.badge_font = pygame.font.SysFont("Comic Sans MS", 13)
        self.pet_display_images = {
            cat_type: pygame.transform.smoothscale(image, (162, 162))
            for cat_type, image in self.cat_images.items()
        }

        self.cat = None
        self.progress = None

        self.feed_btn = pygame.Rect(50, 500, 100, 40)
        self.play_btn = pygame.Rect(160, 500, 100, 40)
        self.clean_btn = pygame.Rect(270, 500, 100, 40)
        self.rest_btn = pygame.Rect(380, 500, 100, 40)
        self.menu_btn = pygame.Rect(700, 300, 160, 40)
        self.inventory_btn = pygame.Rect(700, 350, 160, 40)
        self.vet_btn = pygame.Rect(700, 400, 160, 40)
        self.store_btn = pygame.Rect(700, 450, 160, 40)
        self.chore_btn = pygame.Rect(700, 500, 160, 40)

        self.running = True
        self.time_passed = 0
        self.autosave_timer = 0
        self.active_overlay = None
        self.overlay_stack = []
        self.active_chore = None
        self.chore_state = {}
        self.dragged_laundry_index = None
        self.drag_offset = (0, 0)
        self.status_message = ""
        self.status_timer = 0
        self.badge_message = ""
        self.badge_timer = 0
        self.dead_reason = ""

        self.oven_round_duration = 2200
        self.oven_safe_min = 0.44
        self.oven_safe_max = 0.56
        self.oven_undercooked_limit = 0.28
        self.oven_burned_limit = 0.72
        self.oven_undercooked_timeout = 850
        self.oven_burned_timeout = 700

    def sync_active_overlay(self):
        self.active_overlay = self.overlay_stack[-1] if self.overlay_stack else None

    def open_overlay(self, overlay_name):
        self.overlay_stack.append(overlay_name)
        self.sync_active_overlay()

    def close_current_overlay(self):
        if self.active_overlay == "chore":
            self.reset_chore_state()
        if self.overlay_stack:
            self.overlay_stack.pop()
        self.sync_active_overlay()

    def clear_overlays(self):
        self.overlay_stack.clear()
        self.active_overlay = None
        self.reset_chore_state()

    def get_chore_catalog(self):
        return [
            ("Take Out The Trash", "trash", "$10"),
            ("Put Away Laundry", "laundry", "$15"),
            ("Perfect Bake", "oven", "$20"),
        ]

    def get_oven_layout(self, rect):
        gauge_rect = pygame.Rect(rect.x + 80, rect.y + 188, rect.width - 160, 66)
        button_rect = pygame.Rect(rect.centerx - 120, rect.bottom - 108, 240, 54)
        return gauge_rect, button_rect

    def setup_oven_round(self, state):
        state["pointer"] = random.uniform(0.36, 0.46)
        state["round_timer"] = self.oven_round_duration
        state["undercook_time"] = 0
        state["burn_time"] = 0
        state["hold_active"] = False

    def finish_oven_round(self, result):
        self.chore_state["results"].append(result)
        completed_rounds = len(self.chore_state["results"])
        success_count = sum(entry == "success" for entry in self.chore_state["results"])

        if completed_rounds >= 6:
            if success_count >= 4:
                return True, f"Perfect Bake finished with {success_count}/6 cakes baked just right. Earned $20."
            self.chore_state = self.spawn_chore_state("oven", self.ui.overlay_rect())
            return False, f"Only {success_count}/6 cakes baked correctly. Try Perfect Bake again."

        self.setup_oven_round(self.chore_state)
        if result == "success":
            return False, f"Round {completed_rounds}/6 landed in the green zone."
        if result == "undercooked":
            return False, f"Round {completed_rounds}/6 stayed too cool and came out undercooked."
        return False, f"Round {completed_rounds}/6 overheated and burned."

    def update_active_chore(self, dt):
        if self.active_chore != "oven" or not self.chore_state:
            return False, ""

        if not self.chore_state.get("has_started", False):
            return False, ""

        pointer_shift = 0.00105 * dt if self.chore_state["hold_active"] else -0.00082 * dt
        self.chore_state["pointer"] = max(0.0, min(1.0, self.chore_state["pointer"] + pointer_shift))
        self.chore_state["round_timer"] = max(0, self.chore_state["round_timer"] - dt)

        if self.chore_state["pointer"] <= self.oven_undercooked_limit:
            self.chore_state["undercook_time"] += dt
        if self.chore_state["pointer"] >= self.oven_burned_limit:
            self.chore_state["burn_time"] += dt

        if self.chore_state["round_timer"] == 0:
            if self.chore_state["burn_time"] >= self.oven_burned_timeout:
                return self.finish_oven_round("burned")
            if self.chore_state["undercook_time"] >= self.oven_undercooked_timeout:
                return self.finish_oven_round("undercooked")
            if self.oven_safe_min <= self.chore_state["pointer"] <= self.oven_safe_max:
                return self.finish_oven_round("success")
            if self.chore_state["pointer"] < self.oven_safe_min:
                return self.finish_oven_round("undercooked")
            return self.finish_oven_round("burned")

        return False, ""

    def handle_overlay_back(self):
        if self.active_overlay == "chore" and self.active_chore:
            self.reset_chore_state()
            return
        self.close_current_overlay()

    def point_in_rounded_rect(self, point, rect, radius):
        if not rect.collidepoint(point):
            return False

        local_x = point[0] - rect.x
        local_y = point[1] - rect.y
        inner_width = rect.width - 2 * radius
        inner_height = rect.height - 2 * radius

        if radius <= local_x <= radius + inner_width:
            return True
        if radius <= local_y <= radius + inner_height:
            return True

        corner_centers = [
            (radius, radius),
            (rect.width - radius, radius),
            (radius, rect.height - radius),
            (rect.width - radius, rect.height - radius),
        ]
        for center_x, center_y in corner_centers:
            if (local_x - center_x) ** 2 + (local_y - center_y) ** 2 <= radius ** 2:
                return True

        return False

    def get_title_draw_metrics(self, title_size):
        title_width, title_height = title_size
        scale = min(self.ui.window_width / title_width, self.ui.window_height / title_height)
        draw_width = max(1, int(title_width * scale))
        draw_height = max(1, int(title_height * scale))
        offset_x = (self.ui.window_width - draw_width) // 2
        offset_y = (self.ui.window_height - draw_height) // 2
        return scale, offset_x, offset_y, draw_width, draw_height

    def window_to_title_pos(self, window_pos, title_size, scale, offset_x, offset_y):
        local_x = window_pos[0] - offset_x
        local_y = window_pos[1] - offset_y
        if not (0 <= local_x <= title_size[0] * scale and 0 <= local_y <= title_size[1] * scale):
            return None
        return (local_x / scale, local_y / scale)

    def show_title_screen(self):
        while self.running:
            scale, offset_x, offset_y, draw_width, draw_height = self.get_title_draw_metrics(self.title_size)
            draw_size = (draw_width, draw_height)
            if self.scaled_title_image is None or self.scaled_title_size != draw_size:
                self.scaled_title_image = pygame.transform.smoothscale(self.title_image, draw_size)
                self.scaled_title_size = draw_size
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return False

                if event.type == pygame.VIDEORESIZE:
                    self.ui.window = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.ui.update_render_metrics(event.w, event.h)

                if event.type == pygame.WINDOWSIZECHANGED:
                    self.ui.update_render_metrics(event.x, event.y)

                if event.type == pygame.MOUSEBUTTONDOWN:
                    click_pos = self.window_to_title_pos(event.pos, self.title_size, scale, offset_x, offset_y)
                    if click_pos is not None and self.point_in_rounded_rect(click_pos, self.title_button_rect, self.title_button_radius):
                        self.play_click()
                        return True

            self.ui.window.fill(COZY)
            self.ui.window.blit(self.scaled_title_image, (offset_x, offset_y))
            pygame.display.flip()
            self.ui.clock.tick(60)

        return False

    def play_click(self):
        random.choice(self.click_sounds).play()

    def load_or_create_game(self):
        loaded = load_game()
        if loaded is not None:
            return loaded
        return self.start_new_game()

    def start_new_game(self):
        cat_name, cat_type, personality = setup_screen(self.ui, self.play_click, self.cat_images)
        return Cat(cat_name, cat_type, personality), create_default_progress()

    def get_mood(self):
        if self.cat.dead_stat():
            return "Gone"
        if self.cat.health <= 25:
            return "Critical"
        if self.cat.health <= 45:
            return "Sick"
        if self.cat.happiness <= 30:
            return "Sad"
        if self.cat.energy >= 80 and self.cat.happiness >= 70:
            return "Energetic"
        return "Happy"

    def get_status_color(self):
        mood = self.get_mood()
        if mood == "Critical":
            return RED
        if mood == "Sick":
            return (204, 130, 130)
        if mood == "Sad":
            return (140, 150, 200)
        if mood == "Energetic":
            return GOLD
        return BUTTON

    def unlock_achievements(self):
        achievements = self.progress["achievements"]
        newly_unlocked = []
        if self.progress["total_earned"] >= 25 and "Chore Champion" not in achievements:
            achievements.append("Chore Champion")
            newly_unlocked.append("Chore Champion")
        if self.progress["vet_visits"] >= 1 and "Responsible Owner" not in achievements:
            achievements.append("Responsible Owner")
            newly_unlocked.append("Responsible Owner")
        if self.progress["care_actions"] >= 20 and "Daily Routine" not in achievements:
            achievements.append("Daily Routine")
            newly_unlocked.append("Daily Routine")
        if all(getattr(self.cat, stat_name) >= 60 for stat_name in ("hunger", "happiness", "energy", "cleanliness")) and self.cat.health >= 70:
            if "Well Loved" not in achievements:
                achievements.append("Well Loved")
                newly_unlocked.append("Well Loved")
        self.progress["achievements"] = achievements[:6]
        if newly_unlocked:
            if len(newly_unlocked) == 1:
                self.badge_message = f"New badge unlocked: {newly_unlocked[0]}"
            else:
                self.badge_message = "New badges unlocked: " + ", ".join(newly_unlocked)
            self.badge_timer = 5000

    def get_badge_catalog(self):
        return [
            {
                "name": "Chore Champion",
                "description": "Earn at least $25 by staying on top of chores.",
                "color": GOLD,
            },
            {
                "name": "Responsible Owner",
                "description": "Take your cat to the vet at least once.",
                "color": BLUE,
            },
            {
                "name": "Daily Routine",
                "description": "Complete 20 care actions across feeding, play, rest, and baths.",
                "color": BUTTON,
            },
            {
                "name": "Well Loved",
                "description": "Keep all main stats above 60 while health stays strong.",
                "color": (255, 170, 120),
            },
        ]

    def get_report_lines(self):
        return [
            f"Mood: {self.get_mood()}",
            f"Age Ticks Survived: {self.cat.age_days}",
            f"Money Available: ${self.progress['money']}",
            f"Total Earned: ${self.progress['total_earned']}",
            f"Total Spent: ${self.progress['total_spent']}",
            f"Food Costs: ${self.progress['expense_breakdown']['Food']}",
            f"Toy Costs: ${self.progress['expense_breakdown']['Toys']}",
            f"Grooming Costs: ${self.progress['expense_breakdown']['Grooming']}",
            f"Vet Costs: ${self.progress['expense_breakdown']['Vet']}",
            f"Vet Visits: {self.progress['vet_visits']}",
            f"Care Actions: {self.progress['care_actions']}",
            f"Chores Completed: {self.progress['chores_completed']}",
        ]

    def draw_pet_display(self):
        panel = pygame.Rect(405, 118, 260, 308)
        pygame.draw.rect(self.ui.screen, PANEL, panel, border_radius=24)
        pygame.draw.rect(self.ui.screen, BLACK, panel, 2, border_radius=24)

        aura_color = self.get_status_color()
        aura_center = (panel.centerx - 8, panel.y + 110)
        pygame.draw.circle(self.ui.screen, aura_color, aura_center, 88)
        pygame.draw.circle(self.ui.screen, WHITE, aura_center, 76)

        cat_surface = self.pet_display_images[self.cat.cat_type]
        self.ui.screen.blit(cat_surface, cat_surface.get_rect(center=(panel.centerx - 8, panel.y + 110)))

        mood_badge = pygame.Rect(panel.x + 20, panel.bottom - 60, panel.width - 40, 40)
        pygame.draw.rect(self.ui.screen, self.get_status_color(), mood_badge, border_radius=12)
        pygame.draw.rect(self.ui.screen, BLACK, mood_badge, 2, border_radius=12)
        self.ui.draw_text(f"Mood: {self.get_mood()}", mood_badge.x + 16, mood_badge.y + 8)

    def handle_store_purchase(self, item_name):
        item_info = ITEM_DETAILS[item_name]
        if self.progress["money"] < item_info["price"]:
            self.error_sound.play()
            return "Insufficient funds for that purchase."

        self.play_click()
        self.progress["money"] -= item_info["price"]
        self.progress["total_spent"] += item_info["price"]
        self.progress["inventory"][item_name] += 1
        self.progress["expense_breakdown"][item_info["category"]] += item_info["price"]
        return ""

    def attempt_action(self, action_name):
        if action_name == "feed":
            if self.progress["inventory"]["Meowmunch"] <= 0:
                self.error_sound.play()
                return "Buy Meowmunch before feeding."
            self.play_click()
            self.progress["inventory"]["Meowmunch"] -= 1
            self.cat.feed()
            self.progress["care_actions"] += 1
            return "Your cat enjoyed a meal."

        if action_name == "play":
            if self.progress["inventory"]["Purrplay"] <= 0:
                self.error_sound.play()
                return "Buy Purrplay before playing."
            self.play_click()
            self.progress["inventory"]["Purrplay"] -= 1
            self.cat.play()
            self.progress["care_actions"] += 1
            return "Playtime boosted happiness."

        if action_name == "rest":
            self.play_click()
            self.cat.rest()
            self.progress["care_actions"] += 1
            return "Your cat curled up for a nap."

        if action_name == "clean":
            if self.progress["inventory"]["Furbath"] <= 0:
                self.error_sound.play()
                return "Buy Furbath before cleaning."
            self.play_click()
            self.progress["inventory"]["Furbath"] -= 1
            self.cat.clean()
            self.progress["care_actions"] += 1
            return "Bath time restored cleanliness."

        return ""

    def perform_vet_visit(self):
        if self.progress["money"] < VET_COST:
            self.error_sound.play()
            return "You need more money for a vet visit."

        self.play_click()
        self.progress["money"] -= VET_COST
        self.progress["total_spent"] += VET_COST
        self.progress["expense_breakdown"]["Vet"] += VET_COST
        self.progress["vet_visits"] += 1
        self.cat.vet_visit()
        return f"The vet restored {VET_HEAL} health for ${VET_COST}."

    def spawn_chore_state(self, chore_id, rect):
        if chore_id == "trash":
            items = []
            for _ in range(5):
                x = rect.x + 90 + random.randint(0, rect.width - 180)
                y = rect.y + 130 + random.randint(0, rect.height - 240)
                items.append({"x": x, "y": y, "collected": False})
            return {"items": items, "reward": 10}

        if chore_id == "laundry":
            play_area = pygame.Rect(rect.x + 40, rect.y + 112, rect.width - 228, rect.height - 160)
            bin_rect = pygame.Rect(rect.right - 178, rect.y + 128, 136, rect.height - 188)
            clothing_colors = [
                (224, 143, 143),
                (132, 178, 224),
                (241, 205, 121),
                (167, 204, 146),
                (204, 164, 224),
                (244, 170, 122),
                (146, 214, 207),
                (232, 185, 214),
            ]
            items = []
            item_size = (54, 38)
            max_x = play_area.right - item_size[0]
            max_y = play_area.bottom - item_size[1]

            for index in range(8):
                item_rect = None
                for _ in range(40):
                    candidate = pygame.Rect(
                        random.randint(play_area.x, max_x),
                        random.randint(play_area.y, max_y),
                        item_size[0],
                        item_size[1],
                    )
                    if all(not candidate.inflate(12, 12).colliderect(existing["rect"]) for existing in items):
                        item_rect = candidate
                        break
                if item_rect is None:
                    col = index % 4
                    row = index // 4
                    item_rect = pygame.Rect(play_area.x + col * 72, play_area.y + row * 74, item_size[0], item_size[1])
                items.append({"rect": item_rect, "sorted": False, "color": clothing_colors[index]})

            return {
                "items": items,
                "bin_rect": bin_rect,
                "play_area": play_area,
                "sorted_count": 0,
                "reward": 15,
            }

        if chore_id == "oven":
            state = {"results": [], "reward": 20, "has_started": False}
            self.setup_oven_round(state)
            return state

        return {}

    def handle_chore_click(self, click_pos, rect=None):
        chore_id = self.active_chore
        if chore_id == "trash":
            for trash_item in self.chore_state["items"]:
                if trash_item["collected"]:
                    continue
                trash_rect = pygame.Rect(trash_item["x"], trash_item["y"], 30, 30)
                if trash_rect.collidepoint(click_pos):
                    self.play_click()
                    trash_item["collected"] = True
                    if all(item["collected"] for item in self.chore_state["items"]):
                        return True, "Trash collected. Earned $10."
                    return False, ""

        if chore_id == "laundry":
            for index in range(len(self.chore_state["items"]) - 1, -1, -1):
                laundry_item = self.chore_state["items"][index]
                if laundry_item["sorted"]:
                    continue
                if laundry_item["rect"].collidepoint(click_pos):
                    self.play_click()
                    self.dragged_laundry_index = index
                    self.drag_offset = (
                        click_pos[0] - laundry_item["rect"].x,
                        click_pos[1] - laundry_item["rect"].y,
                    )
                    return False, ""

        if chore_id == "oven" and rect is not None:
            _, hold_rect = self.get_oven_layout(rect)
            if hold_rect.collidepoint(click_pos):
                self.play_click()
                self.chore_state["has_started"] = True
                self.chore_state["hold_active"] = True
            return False, ""

        return False, ""

    def update_laundry_drag(self, mouse_pos):
        if self.active_chore != "laundry" or self.dragged_laundry_index is None:
            return

        laundry_item = self.chore_state["items"][self.dragged_laundry_index]
        new_x = int(mouse_pos[0] - self.drag_offset[0])
        new_y = int(mouse_pos[1] - self.drag_offset[1])
        laundry_item["rect"].x = new_x
        laundry_item["rect"].y = new_y

    def finish_laundry_drag(self, mouse_pos):
        if self.active_chore != "laundry" or self.dragged_laundry_index is None:
            return False, ""

        laundry_item = self.chore_state["items"][self.dragged_laundry_index]
        bin_rect = self.chore_state["bin_rect"]
        completed = False
        message = ""

        if bin_rect.collidepoint(mouse_pos) or bin_rect.colliderect(laundry_item["rect"]):
            self.play_click()
            laundry_item["sorted"] = True
            sorted_slot = self.chore_state["sorted_count"]
            slot_col = sorted_slot % 2
            slot_row = sorted_slot // 2
            laundry_item["rect"].x = bin_rect.x + 10 + slot_col * 62
            laundry_item["rect"].y = bin_rect.y + 16 + slot_row * 50
            self.chore_state["sorted_count"] += 1
            if self.chore_state["sorted_count"] >= len(self.chore_state["items"]):
                completed = True
                message = "Laundry put away. Earned $15."

        self.dragged_laundry_index = None
        self.drag_offset = (0, 0)
        return completed, message

    def reset_chore_state(self):
        self.active_chore = None
        self.chore_state = {}
        self.dragged_laundry_index = None
        self.drag_offset = (0, 0)

    def should_show_overlay_status(self):
        return self.status_message not in {
            "",
            "Welcome to Feline Finances!",
            "Budget warning: you are running low on money.",
        }

    def should_show_store_status(self):
        return self.status_message == "Insufficient funds for that purchase."

    def draw_help_overlay(self):
        rect, _ = self.ui.draw_overlay_shell("Help", "Keep the cat alive by balancing care items, time, and money.")
        left_x = rect.x + 28
        right_x = rect.centerx + 10
        top_y = rect.y + 92

        left_lines = [
            "Feed uses Meowmunch and restores hunger.",
            "Play uses Purrplay and boosts happiness.",
            "Rest restores energy for free.",
            "Clean uses Furbath and raises cleanliness.",
            "Health is separate and only the vet can restore it.",
            "If any stat reaches 0, your cat dies and you must restart.",
        ]
        right_lines = [
            "Whiskermart sells care supplies.",
            f"Vet visits cost ${VET_COST} and restore {VET_HEAL} health.",
            "The Taskboard earns money through small chores.",
            "The Report card summarizes spending and progress.",
            f"Try to save ${SAVE_GOAL} while keeping every stat above zero.",
            "Press ESC or Back to return one screen at a time.",
        ]

        self.ui.draw_text("Core Systems", left_x, top_y)
        current_y = top_y + 32
        for line in left_lines:
            current_y = self.ui.draw_wrapped_text(line, left_x, current_y, rect.width // 2 - 50, font=self.ui.small_font)

        self.ui.draw_text("Budgeting Tips", right_x, top_y)
        current_y = top_y + 32
        for line in right_lines:
            current_y = self.ui.draw_wrapped_text(line, right_x, current_y, rect.width // 2 - 50, font=self.ui.small_font)

    def draw_delete_save_overlay(self):
        rect, _ = self.ui.draw_overlay_shell("Delete Save Data", "This wipes the current pet and starts over from the setup screen.")

        card_rect = pygame.Rect(rect.x + 36, rect.y + 104, rect.width - 72, rect.height - 170)
        pygame.draw.rect(self.ui.screen, PANEL, card_rect, border_radius=18)
        pygame.draw.rect(self.ui.screen, BLACK, card_rect, 2, border_radius=18)

        self.ui.draw_wrapped_text(
            "This action permanently deletes the saved pet, money, inventory, progress, and report history stored in the save file. Use this when you want a completely fresh run.",
            card_rect.x + 24,
            card_rect.y + 26,
            card_rect.width - 48,
            font=self.ui.small_font,
        )
        self.ui.draw_text("Current Pet", card_rect.x + 24, card_rect.y + 128)
        self.ui.draw_text(self.cat.name, card_rect.x + 24, card_rect.y + 162, font=self.ui.small_font)

        confirm_rect = pygame.Rect(card_rect.x + 24, card_rect.bottom - 72, 220, 46)
        cancel_rect = pygame.Rect(card_rect.right - 244, card_rect.bottom - 72, 220, 46)
        self.ui.draw_button(confirm_rect, "Delete Save", fill_color=RED, text_color=WHITE)
        self.ui.draw_button(cancel_rect, "Cancel")

    def draw_report_overlay(self):
        rect, _ = self.ui.draw_overlay_shell("Care Report", "A quick summary of the current run.")

        card_left = pygame.Rect(rect.x + 28, rect.y + 90, rect.width // 2 - 40, rect.height - 120)
        card_right = pygame.Rect(rect.centerx + 10, rect.y + 90, rect.width // 2 - 38, rect.height - 120)

        for card in (card_left, card_right):
            pygame.draw.rect(self.ui.screen, PANEL, card, border_radius=18)
            pygame.draw.rect(self.ui.screen, BLACK, card, 2, border_radius=18)

        self.ui.draw_text("Current Snapshot", card_left.x + 18, card_left.y + 16)
        report_y = card_left.y + 56
        for line in self.get_report_lines():
            self.ui.draw_text(line, card_left.x + 18, report_y, font=self.snapshot_font)
            report_y += 22

        self.ui.draw_text("Achievements", card_right.x + 18, card_right.y + 16)
        if self.progress["achievements"]:
            badge_y = card_right.y + 56
            for achievement in self.progress["achievements"]:
                badge_rect = pygame.Rect(card_right.x + 18, badge_y, card_right.width - 36, 34)
                pygame.draw.rect(self.ui.screen, GOLD, badge_rect, border_radius=12)
                pygame.draw.rect(self.ui.screen, BLACK, badge_rect, 2, border_radius=12)
                self.ui.draw_text(achievement, badge_rect.x + 14, badge_rect.y + 5, font=self.ui.small_font)
                badge_y += 44
        else:
            self.ui.draw_wrapped_text("No badges yet. Strong routines, chores, and vet care will unlock them.", card_right.x + 18, card_right.y + 56, card_right.width - 36, font=self.ui.small_font)

        tips_y = card_right.bottom - 118
        self.ui.draw_text("Next Goal", card_right.x + 18, tips_y)
        self.ui.draw_wrapped_text(
            "Aim to keep every stat above 60 and reach the savings goal while minimizing vet emergencies.",
            card_right.x + 18,
            tips_y + 30,
            card_right.width - 36,
            font=self.ui.small_font,
        )

    def draw_inventory_overlay(self):
        rect, _ = self.ui.draw_overlay_shell("Inventory", "Current care supplies available for your cat.")
        card_rect = pygame.Rect(rect.x + 34, rect.y + 100, rect.width - 68, rect.height - 116)
        pygame.draw.rect(self.ui.screen, PANEL, card_rect, border_radius=18)
        pygame.draw.rect(self.ui.screen, BLACK, card_rect, 2, border_radius=18)

        items = [
            ("Food", "Meowmunch", "Used when you feed your cat."),
            ("Toys", "Purrplay", "Used when you play with your cat."),
            ("Bath", "Furbath", "Used when you clean your cat."),
        ]

        row_y = card_rect.y + 28
        for label, item_name, description in items:
            row_rect = pygame.Rect(card_rect.x + 20, row_y, card_rect.width - 40, 82)
            pygame.draw.rect(self.ui.screen, COZY, row_rect, border_radius=16)
            pygame.draw.rect(self.ui.screen, BLACK, row_rect, 2, border_radius=16)
            self.ui.draw_text(f"{label}: {item_name}", row_rect.x + 18, row_rect.y + 14)
            self.ui.draw_text(f"Owned: {self.progress['inventory'][item_name]}", row_rect.right - 120, row_rect.y + 14, font=self.ui.small_font)
            self.ui.draw_wrapped_text(description, row_rect.x + 18, row_rect.y + 42, row_rect.width - 36, font=self.ui.small_font)
            row_y += 98

    def draw_menu_overlay(self):
        rect, _ = self.ui.draw_overlay_shell("Menu", "Open help, badges, the care report, or delete the current save.")

        option_rects = [
            (pygame.Rect(rect.x + 60, rect.y + 120, rect.width - 120, 56), "Help"),
            (pygame.Rect(rect.x + 60, rect.y + 190, rect.width - 120, 56), "Badges"),
            (pygame.Rect(rect.x + 60, rect.y + 260, rect.width - 120, 56), "Care Report"),
            (pygame.Rect(rect.x + 60, rect.y + 330, rect.width - 120, 56), "Delete Save"),
        ]

        for button_rect, label in option_rects:
            fill_color = RED if label == "Delete Save" else None
            text_color = WHITE if label == "Delete Save" else BLACK
            self.ui.draw_button(button_rect, label, fill_color=fill_color, text_color=text_color)

    def draw_badges_overlay(self):
        rect, _ = self.ui.draw_overlay_shell("Badges", "Locked badges stay grey until their achievement is earned.")
        badges = self.get_badge_catalog()
        unlocked = set(self.progress["achievements"])
        positions = [
            pygame.Rect(rect.x + 34, rect.y + 100, rect.width // 2 - 50, 132),
            pygame.Rect(rect.centerx + 16, rect.y + 100, rect.width // 2 - 50, 132),
            pygame.Rect(rect.x + 34, rect.y + 246, rect.width // 2 - 50, 132),
            pygame.Rect(rect.centerx + 16, rect.y + 246, rect.width // 2 - 50, 132),
        ]

        for badge, badge_rect in zip(badges, positions):
            is_unlocked = badge["name"] in unlocked
            fill_color = badge["color"] if is_unlocked else (170, 170, 170)
            accent_color = WHITE if is_unlocked else (120, 120, 120)

            pygame.draw.rect(self.ui.screen, fill_color, badge_rect, border_radius=18)
            pygame.draw.rect(self.ui.screen, BLACK, badge_rect, 2, border_radius=18)

            emblem_rect = pygame.Rect(badge_rect.x + 16, badge_rect.y + 18, 58, 58)
            pygame.draw.ellipse(self.ui.screen, accent_color, emblem_rect)
            pygame.draw.ellipse(self.ui.screen, BLACK, emblem_rect, 2)
            self.ui.draw_text("★", emblem_rect.x + 18, emblem_rect.y + 10, font=self.ui.big_font)

            title_color = BLACK if is_unlocked else WHITE
            self.ui.draw_text(badge["name"], badge_rect.x + 90, badge_rect.y + 18, color=title_color, font=self.ui.small_font)
            self.ui.draw_wrapped_text(
                badge["description"],
                badge_rect.x + 90,
                badge_rect.y + 46,
                badge_rect.width - 112,
                color=title_color,
                font=self.badge_font,
                line_gap=1,
            )

            status_rect = pygame.Rect(badge_rect.x + 16, badge_rect.bottom - 32, 110, 22)
            status_fill = COZY if is_unlocked else (135, 135, 135)
            pygame.draw.rect(self.ui.screen, status_fill, status_rect, border_radius=10)
            pygame.draw.rect(self.ui.screen, BLACK, status_rect, 2, border_radius=10)
            self.ui.draw_text("Unlocked" if is_unlocked else "Locked", status_rect.x + 14, status_rect.y + 1, font=self.ui.small_font)

    def draw_vet_overlay(self):
        rect, _ = self.ui.draw_overlay_shell("Neighborhood Vet")

        info_card = pygame.Rect(rect.x + 28, rect.y + 78, rect.width - 56, rect.height - 128)
        pygame.draw.rect(self.ui.screen, PANEL, info_card, border_radius=18)
        pygame.draw.rect(self.ui.screen, BLACK, info_card, 2, border_radius=18)

        self.ui.draw_text(f"Current Health: {self.cat.health}", info_card.x + 20, info_card.y + 20)
        self.ui.draw_text(f"Vet Cost: ${VET_COST}", info_card.x + 20, info_card.y + 56)
        self.ui.draw_text(f"Money Available: ${self.progress['money']}", info_card.x + 20, info_card.y + 92)
        self.ui.draw_text(f"Vet Visits So Far: {self.progress['vet_visits']}", info_card.x + 20, info_card.y + 128)

        self.ui.draw_wrapped_text(
            "Low hunger, happiness, energy, and cleanliness now drain health over time. A vet visit restores health, but it costs money and should be planned for.",
            info_card.x + 20,
            info_card.y + 178,
            info_card.width - 40,
            font=self.ui.small_font,
        )

        visit_rect = pygame.Rect(info_card.x + 20, info_card.bottom - 70, 210, 46)
        self.ui.draw_button(visit_rect, f"Visit Vet (${VET_COST})")

    def draw_store_overlay(self):
        rect, _ = self.ui.draw_overlay_shell("Whiskermart", "Buy supplies before your cat runs out of care items.")

        item_y = rect.y + 104
        for item in STORE_ITEMS:
            item_rect = pygame.Rect(rect.x + 34, item_y, rect.width - 68, 76)
            self.ui.draw_button(item_rect, f"{item['name']} - ${item['price']}")
            self.ui.draw_text(item["description"], item_rect.x + 16, item_rect.y + 44, font=self.ui.small_font)
            item_y += 94

        if self.should_show_store_status():
            color = RED if "Insufficient" in self.status_message else BLACK
            self.ui.draw_wrapped_text(self.status_message, rect.x + 34, rect.bottom - 104, rect.width - 68, color=color, font=self.ui.small_font)

        self.ui.draw_text(f"Money: ${self.progress['money']}", rect.x + 34, rect.bottom - 72)

    def draw_chore_overlay(self):
        subtitle = "Earn money to cover food, toys, grooming, and vet care." if not self.active_chore else ""
        rect, _ = self.ui.draw_overlay_shell("The Taskboard", subtitle)

        if not self.active_chore:
            chores = self.get_chore_catalog()
            for index, (label, _, reward_text) in enumerate(chores):
                row_rect = pygame.Rect(rect.x + 50, rect.y + 120 + index * 90, rect.width - 100, 62)
                self.ui.draw_button(row_rect, f"{label} - {reward_text}")
            return

        self.ui.draw_text(
            {
                "trash": "Take Out The Trash",
                "laundry": "Put Away Laundry",
                "oven": "Perfect Bake",
            }[self.active_chore],
            rect.x + 20,
            rect.y + 54,
        )

        if self.active_chore == "trash":
            collected = sum(1 for item in self.chore_state["items"] if item["collected"])
            self.ui.draw_text(f"Click every trash pile. Progress: {collected}/5", rect.x + 50, rect.y + 108, font=self.ui.small_font)
            for trash_item in self.chore_state["items"]:
                if trash_item["collected"]:
                    continue
                trash_rect = pygame.Rect(trash_item["x"], trash_item["y"], 30, 30)
                pygame.draw.rect(self.ui.screen, (139, 90, 43), trash_rect, border_radius=5)
                pygame.draw.rect(self.ui.screen, BLACK, trash_rect, 2, border_radius=5)

        if self.active_chore == "laundry":
            sorted_count = self.chore_state["sorted_count"]
            bin_rect = self.chore_state["bin_rect"]
            self.ui.draw_text(f"Drag all 8 laundry items into the bin. Progress: {sorted_count}/8", rect.x + 50, rect.y + 108, font=self.ui.small_font)

            pygame.draw.rect(self.ui.screen, (225, 229, 235), bin_rect, border_radius=16)
            pygame.draw.rect(self.ui.screen, BLACK, bin_rect, 2, border_radius=16)
            lid_rect = pygame.Rect(bin_rect.x - 6, bin_rect.y - 10, bin_rect.width + 12, 16)
            pygame.draw.rect(self.ui.screen, (190, 196, 205), lid_rect, border_radius=10)
            pygame.draw.rect(self.ui.screen, BLACK, lid_rect, 2, border_radius=10)

            for index, laundry_item in enumerate(self.chore_state["items"]):
                item_rect = laundry_item["rect"]
                shadow_rect = pygame.Rect(item_rect.x + 2, item_rect.y + 2, item_rect.width, item_rect.height)
                pygame.draw.rect(self.ui.screen, (150, 150, 150), shadow_rect, border_radius=10)
                pygame.draw.rect(self.ui.screen, laundry_item["color"], item_rect, border_radius=10)
                pygame.draw.rect(self.ui.screen, BLACK, item_rect, 2, border_radius=10)
                pygame.draw.line(self.ui.screen, WHITE, (item_rect.x + 8, item_rect.y + 10), (item_rect.right - 8, item_rect.y + 10), 2)
                pygame.draw.line(self.ui.screen, WHITE, (item_rect.x + 12, item_rect.centery), (item_rect.right - 12, item_rect.centery), 2)
                if index == self.dragged_laundry_index:
                    pygame.draw.rect(self.ui.screen, GOLD, item_rect, 3, border_radius=10)

        if self.active_chore == "oven":
            gauge_rect, hold_rect = self.get_oven_layout(rect)
            results = self.chore_state["results"]
            success_count = sum(result == "success" for result in results)
            current_round = len(results) + 1

            self.ui.draw_text("Hold the button and finish in green. Get 4 of 6 right.", rect.x + 48, rect.y + 104, font=self.ui.small_font)

            block_y = rect.y + 138
            for index in range(6):
                block_rect = pygame.Rect(rect.x + 54 + index * 66, block_y, 48, 24)
                if index < len(results):
                    result = results[index]
                    if result == "success":
                        fill = BUTTON
                        label = "OK"
                    elif result == "undercooked":
                        fill = (237, 184, 184)
                        label = "LOW"
                    else:
                        fill = RED
                        label = "HOT"
                else:
                    fill = (216, 210, 202)
                    label = str(index + 1)
                pygame.draw.rect(self.ui.screen, fill, block_rect, border_radius=10)
                pygame.draw.rect(self.ui.screen, BLACK, block_rect, 2, border_radius=10)
                self.ui.draw_text(label, block_rect.x + 8, block_rect.y + 2, font=self.ui.small_font)

            self.ui.draw_text(f"Round {current_round}/6", rect.x + 470, block_y + 0, font=self.ui.small_font)
            self.ui.draw_text(f"Good bakes: {success_count}/4 needed", rect.x + 470, block_y + 24, font=self.ui.small_font)

            left_rect = pygame.Rect(gauge_rect.x, gauge_rect.y, int(gauge_rect.width * self.oven_undercooked_limit), gauge_rect.height)
            safe_rect = pygame.Rect(gauge_rect.x + int(gauge_rect.width * self.oven_safe_min), gauge_rect.y, int(gauge_rect.width * (self.oven_safe_max - self.oven_safe_min)), gauge_rect.height)
            right_rect = pygame.Rect(gauge_rect.x + int(gauge_rect.width * self.oven_burned_limit), gauge_rect.y, gauge_rect.right - (gauge_rect.x + int(gauge_rect.width * self.oven_burned_limit)), gauge_rect.height)

            pygame.draw.rect(self.ui.screen, (237, 184, 184), left_rect, border_radius=18)
            pygame.draw.rect(self.ui.screen, (247, 220, 176), pygame.Rect(left_rect.right, gauge_rect.y, safe_rect.x - left_rect.right, gauge_rect.height))
            pygame.draw.rect(self.ui.screen, BUTTON, safe_rect, border_radius=18)
            pygame.draw.rect(self.ui.screen, (243, 202, 147), pygame.Rect(safe_rect.right, gauge_rect.y, right_rect.x - safe_rect.right, gauge_rect.height))
            pygame.draw.rect(self.ui.screen, RED, right_rect, border_radius=18)
            pygame.draw.rect(self.ui.screen, BLACK, gauge_rect, 2, border_radius=18)

            pointer_x = gauge_rect.x + int(self.chore_state["pointer"] * gauge_rect.width)
            pygame.draw.line(self.ui.screen, BLACK, (pointer_x, gauge_rect.y - 10), (pointer_x, gauge_rect.bottom + 10), 4)
            pygame.draw.circle(self.ui.screen, GOLD if self.chore_state["hold_active"] else WHITE, (pointer_x, gauge_rect.centery), 12)
            pygame.draw.circle(self.ui.screen, BLACK, (pointer_x, gauge_rect.centery), 12, 2)

            self.ui.draw_text("Cool", gauge_rect.x + 16, gauge_rect.y + 20, font=self.ui.small_font)
            self.ui.draw_text("Good", safe_rect.x + 18, gauge_rect.y + 20, font=self.ui.small_font)
            self.ui.draw_text("Hot", right_rect.x + 30, gauge_rect.y + 20, color=WHITE, font=self.ui.small_font)

            timer_rect = pygame.Rect(gauge_rect.x, gauge_rect.bottom + 28, gauge_rect.width, 18)
            self.ui.draw_text("Time left", timer_rect.x, timer_rect.y - 24, font=self.ui.small_font)
            self.ui.draw_stat_bar(timer_rect.x, timer_rect.y, timer_rect.width, timer_rect.height, self.chore_state["round_timer"], self.oven_round_duration, BLUE)
            if not self.chore_state.get("has_started", False):
                self.ui.draw_text("Press Hold Heat to start", timer_rect.x + 210, timer_rect.y - 24, font=self.ui.small_font)

            hold_color = GOLD if self.chore_state["hold_active"] else BUTTON
            self.ui.draw_button(hold_rect, "Hold Heat", fill_color=hold_color)

        if self.should_show_overlay_status():
            color = RED if "Wrong" in self.status_message else BLACK
            self.ui.draw_wrapped_text(self.status_message, rect.x + 50, rect.bottom - 70, rect.width - 100, color=color, font=self.ui.small_font)

    def draw_game_over_overlay(self):
        rect = pygame.Rect(160, 140, 580, 300)
        self.ui.overlay_active = True
        dim_surf = pygame.Surface((WIDTH, HEIGHT))
        dim_surf.set_alpha(140)
        dim_surf.fill(BLACK)
        self.ui.screen.blit(dim_surf, (0, 0))

        pygame.draw.rect(self.ui.screen, COZY, rect, border_radius=18)
        pygame.draw.rect(self.ui.screen, BLACK, rect, 3, border_radius=18)
        self.ui.draw_text(f"Your Cat {self.cat.name} Has Died", rect.x + 26, rect.y + 24, color=RED, font=self.ui.big_font)
        self.ui.draw_wrapped_text(
            f"The {self.dead_reason} stat reached zero.",
            rect.x + 28,
            rect.y + 88,
            rect.width - 56,
        )
        self.ui.draw_wrapped_text(
            "In real life, pets rely on steady food, rest, play, cleanliness, and medical care to stay well.",
            rect.x + 28,
            rect.y + 136,
            rect.width - 56,
            font=self.ui.small_font,
        )

        restart_rect = pygame.Rect(rect.x + 60, rect.bottom - 86, 200, 46)
        quit_rect = pygame.Rect(rect.right - 260, rect.bottom - 86, 200, 46)
        self.ui.draw_button(restart_rect, "Restart Game", fill_color=RED, text_color=WHITE)
        self.ui.draw_button(quit_rect, "Quit", fill_color=BUTTON)

    def handle_overlay_click(self, click_pos):
        rect = self.ui.overlay_rect()
        back_rect = pygame.Rect(rect.right - 110, rect.y + 16, 90, 36)

        if self.active_overlay in {"help", "report", "inventory", "badges"}:
            if back_rect.collidepoint(click_pos):
                self.play_click()
                self.close_current_overlay()
            return True

        if self.active_overlay == "menu":
            help_rect = pygame.Rect(rect.x + 60, rect.y + 120, rect.width - 120, 56)
            badges_rect = pygame.Rect(rect.x + 60, rect.y + 190, rect.width - 120, 56)
            report_rect = pygame.Rect(rect.x + 60, rect.y + 260, rect.width - 120, 56)
            delete_rect = pygame.Rect(rect.x + 60, rect.y + 330, rect.width - 120, 56)
            if back_rect.collidepoint(click_pos):
                self.play_click()
                self.close_current_overlay()
            elif help_rect.collidepoint(click_pos):
                self.play_click()
                self.open_overlay("help")
            elif badges_rect.collidepoint(click_pos):
                self.play_click()
                self.unlock_achievements()
                self.open_overlay("badges")
            elif report_rect.collidepoint(click_pos):
                self.play_click()
                self.unlock_achievements()
                self.open_overlay("report")
            elif delete_rect.collidepoint(click_pos):
                self.play_click()
                self.open_overlay("delete_save")
            return True

        if self.active_overlay == "delete_save":
            card_rect = pygame.Rect(rect.x + 36, rect.y + 104, rect.width - 72, rect.height - 170)
            confirm_rect = pygame.Rect(card_rect.x + 24, card_rect.bottom - 72, 220, 46)
            cancel_rect = pygame.Rect(card_rect.right - 244, card_rect.bottom - 72, 220, 46)
            if back_rect.collidepoint(click_pos) or cancel_rect.collidepoint(click_pos):
                self.play_click()
                self.close_current_overlay()
            elif confirm_rect.collidepoint(click_pos):
                self.play_click()
                reset_save_file()
                self.cat, self.progress = self.start_new_game()
                self.clear_overlays()
                self.time_passed = 0
                self.autosave_timer = 0
                self.dead_reason = ""
                self.status_message = "Save deleted. A fresh new cat is ready."
                self.status_timer = 3500
            return True

        if self.active_overlay == "vet":
            visit_rect = pygame.Rect(rect.x + 48, rect.bottom - 116, 210, 46)
            if back_rect.collidepoint(click_pos):
                self.play_click()
                self.close_current_overlay()
            elif visit_rect.collidepoint(click_pos):
                self.status_message = self.perform_vet_visit()
                self.status_timer = 2800
            return True

        if self.active_overlay == "store":
            if back_rect.collidepoint(click_pos):
                self.play_click()
                self.close_current_overlay()
            else:
                item_y = rect.y + 104
                for item in STORE_ITEMS:
                    item_rect = pygame.Rect(rect.x + 34, item_y, rect.width - 68, 76)
                    if item_rect.collidepoint(click_pos):
                        self.status_message = self.handle_store_purchase(item["name"])
                        self.status_timer = 2600
                    item_y += 94
            return True

        if self.active_overlay == "chore":
            if back_rect.collidepoint(click_pos):
                self.play_click()
                self.handle_overlay_back()
                return True

            if not self.active_chore:
                chore_rows = [
                    (pygame.Rect(rect.x + 50, rect.y + 120, rect.width - 100, 62), "trash"),
                    (pygame.Rect(rect.x + 50, rect.y + 210, rect.width - 100, 62), "laundry"),
                    (pygame.Rect(rect.x + 50, rect.y + 300, rect.width - 100, 62), "oven"),
                ]
                for chore_rect, chore_id in chore_rows:
                    if chore_rect.collidepoint(click_pos):
                        self.play_click()
                        self.active_chore = chore_id
                        self.chore_state = self.spawn_chore_state(chore_id, rect)
                        self.dragged_laundry_index = None
                        self.drag_offset = (0, 0)
                        self.status_message = ""
                return True

            completed, chore_message = self.handle_chore_click(click_pos, rect)
            if chore_message:
                self.status_message = chore_message
                self.status_timer = 2600
            if completed:
                reward = self.chore_state["reward"]
                self.progress["money"] += reward
                self.progress["total_earned"] += reward
                self.progress["chores_completed"] += 1
                self.reset_chore_state()
            return True

        return False

    def handle_restart_click(self, click_pos):
        restart_rect = pygame.Rect(220, 354, 200, 46)
        quit_rect = pygame.Rect(480, 354, 200, 46)
        if restart_rect.collidepoint(click_pos):
            self.play_click()
            reset_save_file()
            self.cat, self.progress = self.start_new_game()
            self.clear_overlays()
            self.time_passed = 0
            self.autosave_timer = 0
            self.dead_reason = ""
            self.status_message = "A new cat has arrived. Keep every stat above zero."
            self.status_timer = 3500
        elif quit_rect.collidepoint(click_pos):
            self.running = False

    def handle_main_click(self, click_pos):
        if self.feed_btn.collidepoint(click_pos):
            self.status_message = self.attempt_action("feed")
            self.status_timer = 2400
        elif self.play_btn.collidepoint(click_pos):
            self.status_message = self.attempt_action("play")
            self.status_timer = 2400
        elif self.rest_btn.collidepoint(click_pos):
            self.status_message = self.attempt_action("rest")
            self.status_timer = 2400
        elif self.clean_btn.collidepoint(click_pos):
            self.status_message = self.attempt_action("clean")
            self.status_timer = 2400
        elif self.inventory_btn.collidepoint(click_pos):
            self.play_click()
            self.open_overlay("inventory")
        elif self.menu_btn.collidepoint(click_pos):
            self.play_click()
            self.open_overlay("menu")
        elif self.vet_btn.collidepoint(click_pos):
            self.play_click()
            self.open_overlay("vet")
        elif self.store_btn.collidepoint(click_pos):
            self.play_click()
            self.open_overlay("store")
        elif self.chore_btn.collidepoint(click_pos):
            self.play_click()
            self.reset_chore_state()
            self.open_overlay("chore")

    def process_death(self):
        if not self.dead_reason:
            dead_stat = self.cat.dead_stat()
            if dead_stat:
                self.dead_reason = dead_stat.capitalize()
                self.status_message = f"Game over: {self.dead_reason} hit zero."
                reset_save_file()

    def process_time_step(self):
        while self.time_passed >= TIME_STEP_MS and not self.dead_reason:
            self.cat.apply_time_passage()
            self.unlock_achievements()
            self.time_passed -= TIME_STEP_MS
            if self.progress["money"] < 10:
                self.status_message = "Budget warning: you are running low on money."
                self.status_timer = 2400
            self.process_death()

    def draw_main_ui(self):
        panel_x = 50
        panel_y = 140
        panel_spacing = 35
        bar_width = 200
        bar_height = 20

        stats = [
            ("Hunger", self.cat.hunger, (255, 100, 100)),
            ("Happiness", self.cat.happiness, (255, 255, 100)),
            ("Energy", self.cat.energy, (100, 255, 100)),
            ("Cleanliness", self.cat.cleanliness, (100, 200, 255)),
            ("Health", self.cat.health, (255, 150, 255)),
        ]

        self.ui.draw_text(f"{self.cat.name} the {self.cat.cat_type} Cat", 50, 30, font=self.ui.big_font)
        self.ui.draw_text(f"Personality: {self.cat.personality}", 50, 70)
        self.ui.draw_text(f"Mood: {self.get_mood()}", 50, 100, color=self.get_status_color())

        for index, (label, value, color) in enumerate(stats):
            y = panel_y + index * panel_spacing
            self.ui.draw_text(label, panel_x, y)
            self.ui.draw_stat_bar(panel_x + 120, y, bar_width, bar_height, value, 100, color)

        self.draw_pet_display()

        right_x = 700
        self.ui.draw_text(f"Money: ${self.progress['money']}", right_x, 50)
        self.ui.draw_text(f"Total Earned: ${self.progress['total_earned']}", right_x, 80)
        self.ui.draw_text(f"Total Spent: ${self.progress['total_spent']}", right_x, 110)
        self.ui.draw_text(f"Savings Goal: ${SAVE_GOAL}", right_x, 140)
        hover_enabled = self.active_overlay is None
        self.ui.draw_button(self.feed_btn, "Feed", check_hover=hover_enabled)
        self.ui.draw_button(self.play_btn, "Play", check_hover=hover_enabled)
        self.ui.draw_button(self.rest_btn, "Rest", check_hover=hover_enabled)
        self.ui.draw_button(self.clean_btn, "Clean", check_hover=hover_enabled)
        self.ui.draw_button(self.menu_btn, "Menu", check_hover=hover_enabled)
        self.ui.draw_button(self.inventory_btn, "Inventory", check_hover=hover_enabled)
        self.ui.draw_button(self.vet_btn, "Visit Vet", check_hover=hover_enabled)
        self.ui.draw_button(self.store_btn, "Whiskermart", check_hover=hover_enabled)
        self.ui.draw_button(self.chore_btn, "The Taskboard", check_hover=hover_enabled)

        if self.status_timer > 0 and self.status_message:
            banner_rect = pygame.Rect(40, HEIGHT - 48, WIDTH - 80, 34)
            pygame.draw.rect(self.ui.screen, PANEL, banner_rect, border_radius=12)
            pygame.draw.rect(self.ui.screen, BLACK, banner_rect, 2, border_radius=12)
            self.ui.draw_text(self.status_message, banner_rect.x + 12, banner_rect.y + 5, font=self.ui.small_font)

        if self.badge_timer > 0 and self.badge_message:
            badge_rect = pygame.Rect(50, 452, 460, 36)
            pygame.draw.rect(self.ui.screen, GOLD, badge_rect, border_radius=12)
            pygame.draw.rect(self.ui.screen, BLACK, badge_rect, 2, border_radius=12)
            self.ui.draw_text(self.badge_message, badge_rect.x + 12, badge_rect.y + 6, font=self.ui.small_font)

    def draw_active_overlay(self):
        if self.active_overlay == "help":
            self.draw_help_overlay()
        elif self.active_overlay == "inventory":
            self.draw_inventory_overlay()
        elif self.active_overlay == "menu":
            self.draw_menu_overlay()
        elif self.active_overlay == "badges":
            self.draw_badges_overlay()
        elif self.active_overlay == "delete_save":
            self.draw_delete_save_overlay()
        elif self.active_overlay == "report":
            self.unlock_achievements()
            self.draw_report_overlay()
        elif self.active_overlay == "vet":
            self.draw_vet_overlay()
        elif self.active_overlay == "store":
            self.draw_store_overlay()
        elif self.active_overlay == "chore":
            self.draw_chore_overlay()

    def run(self):
        if not self.show_title_screen():
            pygame.quit()
            sys.exit()

        self.cat, self.progress = self.load_or_create_game()
        self.status_message = self.progress.get("last_status", "")

        while self.running:
            dt = self.ui.clock.tick(60)
            self.time_passed += dt
            self.autosave_timer += dt
            self.status_timer = max(0, self.status_timer - dt)
            self.badge_timer = max(0, self.badge_timer - dt)

            while self.autosave_timer >= AUTOSAVE_INTERVAL and not self.dead_reason:
                self.progress["last_status"] = self.status_message
                save_game(self.cat, self.progress)
                self.autosave_timer -= AUTOSAVE_INTERVAL

            self.ui.screen.fill(COZY)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if not self.dead_reason:
                        self.progress["last_status"] = self.status_message
                        save_game(self.cat, self.progress)
                    self.running = False

                if event.type == pygame.VIDEORESIZE:
                    self.ui.window = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.ui.update_render_metrics(event.w, event.h)

                if event.type == pygame.WINDOWSIZECHANGED:
                    self.ui.update_render_metrics(event.x, event.y)

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not self.dead_reason:
                    self.handle_overlay_back()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    click_pos = self.ui.window_to_game_pos(event.pos)
                    if click_pos is None:
                        continue

                    if self.dead_reason:
                        self.handle_restart_click(click_pos)
                        continue

                    if self.active_overlay and self.handle_overlay_click(click_pos):
                        continue

                    self.handle_main_click(click_pos)

                if event.type == pygame.MOUSEMOTION:
                    mouse_pos = self.ui.window_to_game_pos(event.pos)
                    if mouse_pos is not None:
                        self.update_laundry_drag(mouse_pos)

                if event.type == pygame.MOUSEBUTTONUP:
                    if self.active_chore == "oven" and self.chore_state:
                        self.chore_state["hold_active"] = False
                    mouse_pos = self.ui.window_to_game_pos(event.pos)
                    if mouse_pos is not None:
                        completed, chore_message = self.finish_laundry_drag(mouse_pos)
                        if chore_message:
                            self.status_message = chore_message
                            self.status_timer = 2600
                        if completed:
                            reward = self.chore_state["reward"]
                            self.progress["money"] += reward
                            self.progress["total_earned"] += reward
                            self.progress["chores_completed"] += 1
                            self.reset_chore_state()

            completed, chore_message = self.update_active_chore(dt)
            if chore_message:
                self.status_message = chore_message
                self.status_timer = 2600
            if completed:
                reward = self.chore_state["reward"]
                self.progress["money"] += reward
                self.progress["total_earned"] += reward
                self.progress["chores_completed"] += 1
                self.reset_chore_state()

            self.process_death()
            self.process_time_step()
            self.draw_main_ui()
            self.draw_active_overlay()
            if self.dead_reason:
                self.draw_game_over_overlay()
            self.ui.present_frame()

        pygame.quit()
        sys.exit()


def run():
    Game().run()