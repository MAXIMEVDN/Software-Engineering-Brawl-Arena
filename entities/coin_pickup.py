import pygame

from config import Colors, MAP_COIN_RADIUS, MAP_COIN_VALUE


class CoinPickup:
    """Collectible world coin that can be serialized between server and client."""

    def __init__(self, coin_id, x, y, value=MAP_COIN_VALUE, radius=MAP_COIN_RADIUS):
        """Create one coin pickup at a world position."""
        self.coin_id = coin_id
        self.x = int(x)
        self.y = int(y)
        self.value = int(value)
        self.radius = int(radius)

    def get_rect(self):
        """Return the coin bounds used for collision checks."""
        diameter = self.radius * 2
        return pygame.Rect(self.x - self.radius, self.y - self.radius, diameter, diameter)

    def draw(self, screen, camera_offset=(0, 0)):
        """Draw the coin with a bright fill, rim and small highlight."""
        draw_x = self.x - camera_offset[0]
        draw_y = self.y - camera_offset[1]

        pygame.draw.circle(screen, Colors.YELLOW, (int(draw_x), int(draw_y)), self.radius)
        pygame.draw.circle(screen, Colors.ORANGE, (int(draw_x), int(draw_y)), self.radius, 3)
        pygame.draw.circle(
            screen,
            Colors.WHITE,
            (int(draw_x - (self.radius * 0.35)), int(draw_y - (self.radius * 0.35))),
            max(2, self.radius // 4),
        )

    def to_dict(self):
        """Serialize the coin so it can be synced over the network."""
        return {
            "coin_id": self.coin_id,
            "x": self.x,
            "y": self.y,
            "value": self.value,
            "radius": self.radius,
        }

    @classmethod
    def from_dict(cls, data):
        """Create a coin from serialized game-state data."""
        return cls(
            coin_id=data["coin_id"],
            x=data["x"],
            y=data["y"],
            value=data.get("value", MAP_COIN_VALUE),
            radius=data.get("radius", MAP_COIN_RADIUS),
        )
