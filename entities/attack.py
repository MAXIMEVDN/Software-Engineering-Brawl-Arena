# Attack en Hitbox classes.
#
# Een aanval heeft drie fasen:
#   1. Startup  - character bereidt aan, hitbox nog niet actief
#   2. Active   - hitbox is actief en kan schade doen
#   3. Recovery - aanval is voorbij, character herstelt
#
# Hitbox is de rechthoek waarbinnen de aanval raak is.

import pygame


class Hitbox:
    # Een rechthoek die bijhoudt waar een aanval raak kan zijn.

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def get_rect(self):
        # Geef de hitbox als pygame Rect terug.
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def collides_with(self, other):
        # Controleer of deze hitbox overlapt met een andere.
        return self.get_rect().colliderect(other.get_rect())


class Attack:
    # Eén aanval met alle bijbehorende eigenschappen.

    def __init__(self, name, damage, knockback_base, knockback_scaling,
                 knockback_angle, startup_frames, active_frames, recovery_frames,
                 hitbox_width, hitbox_height, hitbox_offset_x=0, hitbox_offset_y=0):
        self.name = name
        self.damage = damage
        self.knockback_base = knockback_base
        self.knockback_scaling = knockback_scaling
        self.knockback_angle = knockback_angle   # In graden (0 = horizontaal, 90 = omhoog)
        self.startup_frames = startup_frames
        self.active_frames = active_frames
        self.recovery_frames = recovery_frames

        # Afmetingen en positie van de hitbox
        self.hitbox_width = hitbox_width
        self.hitbox_height = hitbox_height
        self.hitbox_offset_x = hitbox_offset_x
        self.hitbox_offset_y = hitbox_offset_y

        # Runtime-staat
        self.hitbox = Hitbox(0, 0, hitbox_width, hitbox_height)
        self.is_active = False
        self.has_hit = set()  # Player IDs die al geraakt zijn (voorkom meerdere treffers)
        self.owner_id = None  # Wie deze aanval uitvoert

    def update_position(self, owner_x, owner_y, facing_right, owner_width):
        # Verplaats de hitbox mee met de character.
        if facing_right:
            self.hitbox.x = owner_x + owner_width + self.hitbox_offset_x
        else:
            self.hitbox.x = owner_x - self.hitbox_width - self.hitbox_offset_x

        self.hitbox.y = owner_y + self.hitbox_offset_y

    def can_hit(self, target_id):
        # Controleer of deze aanval het opgegeven target mag raken.
        return (
            self.is_active and
            target_id != self.owner_id and
            target_id not in self.has_hit
        )

    def register_hit(self, target_id):
        # Onthoud dat dit target al geraakt is (zodat het niet dubbel geraakt wordt).
        self.has_hit.add(target_id)

    def get_total_frames(self):
        # Totaal aantal frames van de aanval.
        return self.startup_frames + self.active_frames + self.recovery_frames

    def to_dict(self):
        # Zet de aanval om naar een dictionary (voor netwerkverzending).
        return {
            "name": self.name,
            "damage": self.damage,
            "knockback_base": self.knockback_base,
            "knockback_scaling": self.knockback_scaling,
            "knockback_angle": self.knockback_angle,
            "startup_frames": self.startup_frames,
            "active_frames": self.active_frames,
            "recovery_frames": self.recovery_frames,
            "hitbox_width": self.hitbox_width,
            "hitbox_height": self.hitbox_height,
            "hitbox_offset_x": self.hitbox_offset_x,
            "hitbox_offset_y": self.hitbox_offset_y,
            "is_active": self.is_active,
            "hitbox": {
                "x": self.hitbox.x,
                "y": self.hitbox.y,
                "width": self.hitbox.width,
                "height": self.hitbox.height,
            },
            "has_hit": list(self.has_hit),
            "owner_id": self.owner_id,
        }

    @classmethod
    def from_dict(cls, data):
        # Maak een Attack-object van een dictionary (ontvangen van netwerk).
        attack = cls(
            name=data["name"],
            damage=data["damage"],
            knockback_base=data["knockback_base"],
            knockback_scaling=data["knockback_scaling"],
            knockback_angle=data["knockback_angle"],
            startup_frames=data.get("startup_frames", 0),
            active_frames=data.get("active_frames", 0),
            recovery_frames=data.get("recovery_frames", 0),
            hitbox_width=data.get("hitbox_width", data["hitbox"]["width"]),
            hitbox_height=data.get("hitbox_height", data["hitbox"]["height"]),
            hitbox_offset_x=data.get("hitbox_offset_x", 0),
            hitbox_offset_y=data.get("hitbox_offset_y", 0),
        )
        attack.is_active = data["is_active"]
        attack.hitbox.x = data["hitbox"]["x"]
        attack.hitbox.y = data["hitbox"]["y"]
        attack.has_hit = set(data["has_hit"])
        attack.owner_id = data["owner_id"]
        return attack


class Projectile(Attack):
    # Een projectiel dat door de lucht vliegt.
    # Erft van Attack maar beweegt zelfstandig.

    def __init__(self, name, damage, knockback_base, knockback_scaling,
                 knockback_angle, hitbox_width, hitbox_height,
                 speed, lifetime, gravity=False):
        super().__init__(
            name=name,
            damage=damage,
            knockback_base=knockback_base,
            knockback_scaling=knockback_scaling,
            knockback_angle=knockback_angle,
            startup_frames=0,
            active_frames=lifetime,
            recovery_frames=0,
            hitbox_width=hitbox_width,
            hitbox_height=hitbox_height,
        )
        self.speed = speed
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.lifetime = lifetime
        self.has_gravity = gravity
        self.is_active = True

    def launch(self, x, y, facing_right):
        # Lanceer het projectiel vanuit een positie.
        self.hitbox.x = x
        self.hitbox.y = y
        self.vel_x = self.speed if facing_right else -self.speed

    def update(self):
        # Beweeg het projectiel en verlaag de levensduur.
        # Geeft True terug als het projectiel nog actief is, anders False.
        self.hitbox.x += self.vel_x
        self.hitbox.y += self.vel_y

        if self.has_gravity:
            self.vel_y += 0.5

        self.lifetime -= 1
        return self.lifetime > 0

    def to_dict(self):
        # Zet het projectiel om naar een dictionary (voor netwerkverzending).
        data = super().to_dict()
        data.update({
            "type": "projectile",
            "vel_x": self.vel_x,
            "vel_y": self.vel_y,
            "lifetime": self.lifetime,
        })
        return data

    @classmethod
    def from_dict(cls, data):
        projectile = cls(
            name=data["name"],
            damage=data["damage"],
            knockback_base=data["knockback_base"],
            knockback_scaling=data["knockback_scaling"],
            knockback_angle=data["knockback_angle"],
            hitbox_width=data.get("hitbox_width", data["hitbox"]["width"]),
            hitbox_height=data.get("hitbox_height", data["hitbox"]["height"]),
            speed=abs(data.get("vel_x", 0)),
            lifetime=data.get("lifetime", data.get("active_frames", 0)),
            gravity=bool(data.get("vel_y", 0)),
        )
        projectile.is_active = data["is_active"]
        projectile.hitbox.x = data["hitbox"]["x"]
        projectile.hitbox.y = data["hitbox"]["y"]
        projectile.has_hit = set(data["has_hit"])
        projectile.owner_id = data["owner_id"]
        projectile.vel_x = data.get("vel_x", 0)
        projectile.vel_y = data.get("vel_y", 0)
        projectile.lifetime = data.get("lifetime", projectile.lifetime)
        return projectile
