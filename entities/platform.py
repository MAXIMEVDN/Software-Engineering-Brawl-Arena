# Platform - een vloer waarop characters kunnen staan.
#
# Characters landen alleen op de bovenkant (passthrough van onder).

import os

import pygame

from config import Colors


class Platform:
    # Een platform waarop characters kunnen lopen en staan.
    _base_tile = None
    _tile_load_attempted = False
    _surface_cache = {}

    def __init__(self, x, y, width, height, color=None, is_passthrough=True):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color or Colors.PLATFORM_COLOR
        self.is_passthrough = is_passthrough  # Je kunt er van onder doorheen springen

    def get_rect(self):
        # Geef de collision-rechthoek terug.
        return pygame.Rect(self.x, self.y, self.width, self.height)

    @staticmethod
    def _mix_color(base_color, target_color, factor):
        factor = max(0.0, min(1.0, factor))
        return tuple(
            int(base_color[index] + (target_color[index] - base_color[index]) * factor)
            for index in range(3)
        )

    @classmethod
    def _get_base_tile(cls):
        if cls._tile_load_attempted:
            return cls._base_tile

        cls._tile_load_attempted = True
        tile_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "tilesets",
            "craftpix_platformer",
            "1 Tiles",
            "Tile_32.png",
        )

        if not os.path.exists(tile_path):
            cls._base_tile = None
            return None

        try:
            cls._base_tile = pygame.image.load(tile_path).convert_alpha()
        except pygame.error:
            cls._base_tile = None
        return cls._base_tile

    def _build_surface(self):
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        base_tile = self._get_base_tile()

        if base_tile is not None:
            tile_width = min(32, self.width)
            full_tile = pygame.transform.scale(base_tile, (tile_width, self.height))

            for tile_x in range(0, self.width, tile_width):
                segment_width = min(tile_width, self.width - tile_x)
                if segment_width == tile_width:
                    surface.blit(full_tile, (tile_x, 0))
                else:
                    partial_tile = pygame.transform.scale(base_tile, (segment_width, self.height))
                    surface.blit(partial_tile, (tile_x, 0))

            # Color-wash the prototype tile so it matches the arena better and the debug numbers fade back.
            tint_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            tint_overlay.fill((*self.color, 150))
            surface.blit(tint_overlay, (0, 0))

            mute_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            mute_overlay.fill((*self._mix_color(self.color, (255, 255, 255), 0.12), 85))
            surface.blit(mute_overlay, (0, 0))
        else:
            surface.fill(self.color)

        outline_color = self._mix_color(self.color, (0, 0, 0), 0.72)
        highlight_color = self._mix_color(self.color, (255, 255, 255), 0.38)
        mid_color = self._mix_color(self.color, (255, 255, 255), 0.15)
        shadow_color = self._mix_color(self.color, (0, 0, 0), 0.42)

        pygame.draw.rect(surface, outline_color, (0, 0, self.width, self.height), 2)
        pygame.draw.rect(surface, highlight_color, (2, 0, max(0, self.width - 4), max(3, self.height // 5)))
        pygame.draw.line(
            surface,
            mid_color,
            (2, max(2, self.height // 2)),
            (max(2, self.width - 3), max(2, self.height // 2)),
            1,
        )
        pygame.draw.rect(
            surface,
            shadow_color,
            (2, max(0, self.height - max(4, self.height // 4)), max(0, self.width - 4), max(4, self.height // 4)),
        )

        return surface

    def _get_surface(self):
        cache_key = (self.width, self.height, tuple(self.color))
        cached_surface = self._surface_cache.get(cache_key)
        if cached_surface is None:
            cached_surface = self._build_surface()
            self._surface_cache[cache_key] = cached_surface
        return cached_surface

    def draw(self, screen, camera_offset=(0, 0)):
        # Teken het platform met een tiled prototype-look en extra contrast tegen de arena-backgrounds.
        draw_x = self.x - camera_offset[0]
        draw_y = self.y - camera_offset[1]

        shadow_color = self._mix_color(self.color, (0, 0, 0), 0.82)
        pygame.draw.rect(screen, shadow_color, (draw_x - 2, draw_y + 3, self.width + 4, self.height + 2))
        screen.blit(self._get_surface(), (draw_x, draw_y))

    def to_dict(self):
        # Zet het platform om naar een dictionary (voor netwerkverzending).
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "is_passthrough": self.is_passthrough,
        }

    @classmethod
    def from_tuple(cls, data):
        # Maak een Platform van een tuple (x, y, width, height).
        return cls(data[0], data[1], data[2], data[3])
