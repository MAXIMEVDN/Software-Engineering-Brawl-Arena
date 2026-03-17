# Platform - een vloer waarop characters kunnen staan.
#
# Characters landen alleen op de bovenkant (passthrough van onder).

import pygame

from config import Colors


class Platform:
    # Een platform waarop characters kunnen lopen en staan.

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

    def draw(self, screen, camera_offset=(0, 0)):
        # Teken het platform met een lichte bovenkant en donkere onderkant.
        draw_x = self.x - camera_offset[0]
        draw_y = self.y - camera_offset[1]

        # Platformlichaam
        pygame.draw.rect(screen, self.color, (draw_x, draw_y, self.width, self.height))

        # Lichte bovenkant
        highlight_color = tuple(min(c + 30, 255) for c in self.color)
        pygame.draw.rect(screen, highlight_color, (draw_x, draw_y, self.width, 4))

        # Donkere onderkant
        shadow_color = tuple(max(c - 30, 0) for c in self.color)
        pygame.draw.rect(screen, shadow_color, (draw_x, draw_y + self.height - 4, self.width, 4))

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
