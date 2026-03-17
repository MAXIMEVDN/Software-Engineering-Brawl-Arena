import pygame
import os


TITLE_TEXT_COLOR = (247, 233, 214)
TITLE_SHADOW_COLOR = (60, 34, 34)
TITLE_OUTLINE_COLOR = (0, 0, 0)
_TITLE_FONT_CACHE = {}
_TITLE_FONT_NAMES = [
    "pressstart2p",
    "prstartk",
    "upheavtt",
    "consolas",
    "couriernew",
    "lucidaconsole",
]
_BUNDLED_FONT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "fonts",
    "determination.ttf",
)


def get_title_style_font(size):
    font = _TITLE_FONT_CACHE.get(size)
    if font is not None:
        return font

    font_path = _BUNDLED_FONT_PATH if os.path.exists(_BUNDLED_FONT_PATH) else None
    if font_path is None:
        for font_name in _TITLE_FONT_NAMES:
            font_path = pygame.font.match_font(font_name, bold=True)
            if font_path:
                break

    if font_path:
        font = pygame.font.Font(font_path, size)
    else:
        font = pygame.font.Font(None, size)
        font.set_bold(True)

    _TITLE_FONT_CACHE[size] = font
    return font


def draw_title_style_text(
    screen,
    text,
    center,
    size,
    text_color=TITLE_TEXT_COLOR,
    shadow_color=TITLE_SHADOW_COLOR,
    outline_color=TITLE_OUTLINE_COLOR,
    shadow_offset=(6, 6),
    outline_width=2,
):
    font = get_title_style_font(size)

    shadow_surface = font.render(text, False, shadow_color)
    shadow_rect = shadow_surface.get_rect(center=(center[0] + shadow_offset[0], center[1] + shadow_offset[1]))
    screen.blit(shadow_surface, shadow_rect)

    if outline_width > 0:
        outline_surface = font.render(text, False, outline_color)
        for offset_x in range(-outline_width, outline_width + 1):
            for offset_y in range(-outline_width, outline_width + 1):
                if offset_x == 0 and offset_y == 0:
                    continue
                outline_rect = outline_surface.get_rect(center=(center[0] + offset_x, center[1] + offset_y))
                screen.blit(outline_surface, outline_rect)

    text_surface = font.render(text, False, text_color)
    text_rect = text_surface.get_rect(center=center)
    screen.blit(text_surface, text_rect)
    return text_rect
