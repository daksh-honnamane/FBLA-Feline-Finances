import pygame

from core.config import CAPTION, CAT_TYPES, asset_path


def load_assets():
    click_sounds = [pygame.mixer.Sound(asset_path("sounds", f"click_00{i}.ogg")) for i in range(1, 6)]
    error_sound = pygame.mixer.Sound(asset_path("sounds", "error_005.ogg"))
    cat_images = {
        cat_type: pygame.image.load(asset_path("cats", f"{cat_type.lower()}.png"))
        for cat_type in CAT_TYPES
    }
    icon = pygame.image.load(asset_path("ui", "icon.png"))
    title_images = {
        "small": pygame.image.load(asset_path("ui", "title_small.png")),
        "big": pygame.image.load(asset_path("ui", "title_big.png")),
    }

    pygame.display.set_caption(CAPTION)
    pygame.display.set_icon(icon)

    return {
        "click_sounds": click_sounds,
        "error_sound": error_sound,
        "cat_images": cat_images,
        "icon": icon,
        "title_images": title_images,
    }