import sys

import pygame

from core.config import BLACK, BLUE, BUTTON, BUTTON_HOVER, CAT_TYPES, COZY, HEIGHT, PANEL, PERSONALITIES, WIDTH


class UIContext:
    def __init__(self):
        self.window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        self.window_width, self.window_height = self.window.get_size()
        self.scale_factor = 1.0
        self.render_width = WIDTH
        self.render_height = HEIGHT
        self.render_offset_x = 0
        self.render_offset_y = 0
        self.overlay_active = False
        self.window_dim_surface = None
        self.window_dim_size = (0, 0)

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Comic Sans MS", 20)
        self.big_font = pygame.font.SysFont("Comic Sans MS", 32)
        self.small_font = pygame.font.SysFont("Comic Sans MS", 16)
        self.update_render_metrics(self.window_width, self.window_height)

    def update_render_metrics(self, new_width, new_height):
        self.window_width = max(1, new_width)
        self.window_height = max(1, new_height)
        self.scale_factor = min(self.window_width / WIDTH, self.window_height / HEIGHT)
        self.render_width = max(1, int(WIDTH * self.scale_factor))
        self.render_height = max(1, int(HEIGHT * self.scale_factor))
        self.render_offset_x = (self.window_width - self.render_width) // 2
        self.render_offset_y = (self.window_height - self.render_height) // 2

    def window_to_game_pos(self, window_pos):
        x = (window_pos[0] - self.render_offset_x) / self.scale_factor
        y = (window_pos[1] - self.render_offset_y) / self.scale_factor
        if 0 <= x <= WIDTH and 0 <= y <= HEIGHT:
            return x, y
        return None

    def get_game_mouse_pos(self):
        game_pos = self.window_to_game_pos(pygame.mouse.get_pos())
        if game_pos is None:
            return -9999, -9999
        return game_pos

    def present_frame(self):
        self.window.fill(COZY)
        if self.overlay_active:
            if self.window_dim_surface is None or self.window_dim_size != (self.window_width, self.window_height):
                self.window_dim_surface = pygame.Surface((self.window_width, self.window_height))
                self.window_dim_surface.set_alpha(120)
                self.window_dim_surface.fill(BLACK)
                self.window_dim_size = (self.window_width, self.window_height)
            self.window.blit(self.window_dim_surface, (0, 0))
        if self.render_width == WIDTH and self.render_height == HEIGHT:
            self.window.blit(self.screen, (self.render_offset_x, self.render_offset_y))
        else:
            scaled_surface = pygame.transform.smoothscale(self.screen, (self.render_width, self.render_height))
            self.window.blit(scaled_surface, (self.render_offset_x, self.render_offset_y))
        self.overlay_active = False
        pygame.display.flip()

    def draw_text(self, text, x, y, color=BLACK, font=None):
        active_font = font or self.font
        self.screen.blit(active_font.render(text, True, color), (x, y))

    def draw_wrapped_text(self, text, x, y, width, color=BLACK, font=None, line_gap=6):
        active_font = font or self.font
        words = text.split()
        line = ""
        line_y = y
        for word in words:
            test_line = f"{line} {word}".strip()
            if active_font.size(test_line)[0] <= width:
                line = test_line
            else:
                self.draw_text(line, x, line_y, color=color, font=active_font)
                line_y += active_font.get_linesize() + line_gap
                line = word
        if line:
            self.draw_text(line, x, line_y, color=color, font=active_font)
            line_y += active_font.get_linesize() + line_gap
        return line_y

    def draw_stat_bar(self, x, y, width, height, value, max_value, color):
        pygame.draw.rect(self.screen, (180, 180, 180), (x, y, width, height), border_radius=5)
        fill_width = int(width * (value / max_value))
        pygame.draw.rect(self.screen, color, (x, y, fill_width, height), border_radius=5)
        pygame.draw.rect(self.screen, BLACK, (x, y, width, height), 2, border_radius=5)

    def draw_button(self, rect, text, check_hover=True, fill_color=None, text_color=BLACK):
        mouse = self.get_game_mouse_pos()
        base_color = fill_color if fill_color is not None else BUTTON
        hover_color = BUTTON_HOVER if fill_color is None else fill_color
        color = hover_color if (check_hover and rect.collidepoint(mouse)) else base_color
        shadow_rect = pygame.Rect(rect.x + 3, rect.y + 3, rect.width, rect.height)
        pygame.draw.rect(self.screen, (150, 150, 150), shadow_rect, border_radius=10)
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, BLACK, rect, 2, border_radius=10)
        text_surf = self.font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)

    def overlay_rect(self):
        overlay_w = int(WIDTH * 0.72)
        overlay_h = int(HEIGHT * 0.74)
        overlay_x = (WIDTH - overlay_w) // 2
        overlay_y = (HEIGHT - overlay_h) // 2
        return pygame.Rect(overlay_x, overlay_y, overlay_w, overlay_h)

    def draw_overlay_shell(self, title, subtitle=""):
        rect = self.overlay_rect()
        self.overlay_active = True
        dim_surf = pygame.Surface((WIDTH, HEIGHT))
        dim_surf.set_alpha(120)
        dim_surf.fill(BLACK)
        self.screen.blit(dim_surf, (0, 0))

        shadow_rect = pygame.Rect(rect.x + 6, rect.y + 6, rect.width, rect.height)
        pygame.draw.rect(self.screen, (150, 150, 150), shadow_rect, border_radius=12)
        pygame.draw.rect(self.screen, COZY, rect, border_radius=12)
        pygame.draw.rect(self.screen, BLACK, rect, 2, border_radius=12)

        self.draw_text(title, rect.x + 20, rect.y + 12, font=self.big_font)
        if subtitle:
            self.draw_text(subtitle, rect.x + 20, rect.y + 54, font=self.small_font)

        back_rect = pygame.Rect(rect.right - 110, rect.y + 16, 90, 36)
        self.draw_button(back_rect, "Back")
        return rect, back_rect


def setup_screen(ui, click_player, cat_images):
    name = ""
    type_index = 0
    personality_index = 0
    name_active = True
    preview_images = {
        cat_type: pygame.transform.smoothscale(image, (155, 155))
        for cat_type, image in cat_images.items()
    }

    while True:
        ui.screen.fill(COZY)
        ui.draw_text("Create Your Cat", 50, 30, font=ui.big_font)
        ui.draw_text("Click through the options below to build your cat.", 50, 70)

        name_rect = pygame.Rect(50, 135, 470, 72)
        type_rect = pygame.Rect(50, 225, 470, 72)
        personality_rect = pygame.Rect(50, 315, 470, 72)
        start_rect = pygame.Rect(110, 425, 350, 56)

        type_left_rect = pygame.Rect(type_rect.x + 150, type_rect.y + 16, 46, 40)
        type_right_rect = pygame.Rect(type_rect.right - 66, type_rect.y + 16, 46, 40)
        personality_left_rect = pygame.Rect(personality_rect.x + 150, personality_rect.y + 16, 46, 40)
        personality_right_rect = pygame.Rect(personality_rect.right - 66, personality_rect.y + 16, 46, 40)

        for panel_rect in (name_rect, type_rect, personality_rect):
            pygame.draw.rect(ui.screen, PANEL, panel_rect, border_radius=20)
            pygame.draw.rect(ui.screen, BLUE if (panel_rect == name_rect and name_active) else BLACK, panel_rect, 2, border_radius=20)

        ui.draw_text("Name", name_rect.x + 18, name_rect.y + 12)
        display_name = name if name else "Click to type your cat's name"
        display_color = BLACK if name else (110, 110, 110)
        ui.draw_text(display_name, name_rect.x + 18, name_rect.y + 38, color=display_color, font=ui.small_font)
        if name_active and pygame.time.get_ticks() % 1000 < 500 and len(name) < 10:
            caret_x = name_rect.x + 18 + ui.small_font.size(display_name if name else "")[0] + 1
            pygame.draw.line(ui.screen, BLACK, (caret_x, name_rect.y + 39), (caret_x, name_rect.y + 59), 2)

        ui.draw_text("Cat Type", type_rect.x + 18, type_rect.y + 12)
        ui.draw_button(type_left_rect, "<")
        ui.draw_button(type_right_rect, ">")
        type_text = ui.font.render(CAT_TYPES[type_index], True, BLACK)
        type_center_x = (type_left_rect.right + type_right_rect.left) // 2
        type_text_rect = type_text.get_rect(center=(type_center_x, type_rect.y + 36))
        ui.screen.blit(type_text, type_text_rect)

        ui.draw_text("Personality", personality_rect.x + 18, personality_rect.y + 12)
        ui.draw_button(personality_left_rect, "<")
        ui.draw_button(personality_right_rect, ">")
        personality_text = ui.font.render(PERSONALITIES[personality_index], True, BLACK)
        personality_center_x = (personality_left_rect.right + personality_right_rect.left) // 2
        personality_text_rect = personality_text.get_rect(center=(personality_center_x, personality_rect.y + 36))
        ui.screen.blit(personality_text, personality_text_rect)

        start_color = BUTTON if name else (185, 185, 185)
        ui.draw_button(start_rect, "Start Game", fill_color=start_color, check_hover=bool(name))

        preview_rect = pygame.Rect(580, 132, 240, 220)
        pygame.draw.rect(ui.screen, PANEL, preview_rect, border_radius=20)
        pygame.draw.rect(ui.screen, BLACK, preview_rect, 2, border_radius=20)
        cat_image = preview_images[CAT_TYPES[type_index]]
        cat_rect = cat_image.get_rect(center=(preview_rect.centerx, preview_rect.y + 120))
        ui.screen.blit(cat_image, cat_rect)

        info_rect = pygame.Rect(preview_rect.x, preview_rect.bottom + 18, preview_rect.width, 132)
        pygame.draw.rect(ui.screen, PANEL, info_rect, border_radius=20)
        pygame.draw.rect(ui.screen, BLACK, info_rect, 2, border_radius=20)
        ui.draw_wrapped_text(
            "A healthy cat needs food, play, rest, baths, and enough budget for vet care.",
            info_rect.x + 18,
            info_rect.y + 16,
            info_rect.width - 36,
            font=ui.small_font,
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.VIDEORESIZE:
                ui.window = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                ui.update_render_metrics(event.w, event.h)

            if event.type == pygame.WINDOWSIZECHANGED:
                ui.update_render_metrics(event.x, event.y)

            if event.type == pygame.MOUSEBUTTONDOWN:
                click_pos = ui.window_to_game_pos(event.pos)
                if click_pos is None:
                    continue

                if name_rect.collidepoint(click_pos):
                    name_active = True
                    click_player()
                elif type_left_rect.collidepoint(click_pos):
                    type_index = (type_index - 1) % len(CAT_TYPES)
                    name_active = False
                    click_player()
                elif type_right_rect.collidepoint(click_pos):
                    type_index = (type_index + 1) % len(CAT_TYPES)
                    name_active = False
                    click_player()
                elif personality_left_rect.collidepoint(click_pos):
                    personality_index = (personality_index - 1) % len(PERSONALITIES)
                    name_active = False
                    click_player()
                elif personality_right_rect.collidepoint(click_pos):
                    personality_index = (personality_index + 1) % len(PERSONALITIES)
                    name_active = False
                    click_player()
                elif start_rect.collidepoint(click_pos) and name:
                    click_player()
                    pygame.time.delay(200)
                    return name, CAT_TYPES[type_index], PERSONALITIES[personality_index]
                else:
                    name_active = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and name:
                    click_player()
                    pygame.time.delay(200)
                    return name, CAT_TYPES[type_index], PERSONALITIES[personality_index]
                if name_active:
                    if event.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                        click_player()
                    elif event.unicode.isalpha() and len(name) < 10:
                        name += event.unicode
                        click_player()

        ui.present_frame()
        ui.clock.tick(60)