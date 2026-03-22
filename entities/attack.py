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
    """Rectangle wrapper that represents the active area of an attack."""

    def __init__(self, x, y, width, height):
        """Store the hitbox position and size in world coordinates."""
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def get_rect(self):
        """Return the hitbox as a pygame Rect."""
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def collides_with(self, other):
        """Return whether this hitbox overlaps another hitbox-like object."""
        return self.get_rect().colliderect(other.get_rect())


class Attack:
    """Store the gameplay data and runtime state for one attack."""

    def __init__(self, name, damage, knockback_base, knockback_scaling,
                 knockback_angle, startup_frames, active_frames, recovery_frames,
                 hitbox_width, hitbox_height, hitbox_offset_x=0, hitbox_offset_y=0,
                 effect_type=None, hold_frames=0, throw_knockback_base=0.0,
                 throw_knockback_scaling=0.0, throw_angle=0, anchor_mode="facing"):
        """Create an attack definition with timing, hitbox and effect data."""
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
        self.effect_type = effect_type
        self.hold_frames = hold_frames
        self.throw_knockback_base = throw_knockback_base
        self.throw_knockback_scaling = throw_knockback_scaling
        self.throw_angle = throw_angle
        self.anchor_mode = anchor_mode

        # Runtime-staat
        self.hitbox = Hitbox(0, 0, hitbox_width, hitbox_height)
        self.is_active = False
        self.has_hit = set()  # Player IDs die al geraakt zijn (voorkom meerdere treffers)
        self.owner_id = None  # Wie deze aanval uitvoert

    def update_position(self, owner_x, owner_y, facing_right, owner_width):
        """Reposition the hitbox relative to the owning character."""
        if self.anchor_mode == "center":
            self.hitbox.x = owner_x + (owner_width - self.hitbox_width) / 2
            self.hitbox.y = owner_y + self.hitbox_offset_y
            return
        if facing_right:
            self.hitbox.x = owner_x + owner_width + self.hitbox_offset_x
        else:
            self.hitbox.x = owner_x - self.hitbox_width - self.hitbox_offset_x

        self.hitbox.y = owner_y + self.hitbox_offset_y

    def can_hit(self, target_id):
        """Return whether this attack may still damage the given target."""
        return (
            self.is_active and
            target_id != self.owner_id and
            target_id not in self.has_hit
        )

    def register_hit(self, target_id):
        """Mark a target as already hit so the attack does not hit twice."""
        self.has_hit.add(target_id)

    def get_total_frames(self):
        """Return the full attack duration across all phases."""
        return self.startup_frames + self.active_frames + self.recovery_frames

    def to_dict(self):
        """Serialize the attack so it can be synced over the network."""
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
            "effect_type": self.effect_type,
            "hold_frames": self.hold_frames,
            "throw_knockback_base": self.throw_knockback_base,
            "throw_knockback_scaling": self.throw_knockback_scaling,
            "throw_angle": self.throw_angle,
            "anchor_mode": self.anchor_mode,
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
        """Rebuild an attack instance from serialized network data."""
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
            effect_type=data.get("effect_type"),
            hold_frames=data.get("hold_frames", 0),
            throw_knockback_base=data.get("throw_knockback_base", 0.0),
            throw_knockback_scaling=data.get("throw_knockback_scaling", 0.0),
            throw_angle=data.get("throw_angle", 0),
            anchor_mode=data.get("anchor_mode", "facing"),
        )
        attack.is_active = data["is_active"]
        attack.hitbox.x = data["hitbox"]["x"]
        attack.hitbox.y = data["hitbox"]["y"]
        attack.has_hit = set(data["has_hit"])
        attack.owner_id = data["owner_id"]
        return attack


class Projectile(Attack):
    """Attack subtype that travels independently after being launched."""

    def __init__(self, name, damage, knockback_base, knockback_scaling,
                 knockback_angle, hitbox_width, hitbox_height,
                 speed, lifetime, gravity=False):
        """Create a projectile with travel speed, lifetime and optional gravity."""
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
        """Spawn the projectile at a position and send it left or right."""
        self.hitbox.x = x
        self.hitbox.y = y
        self.vel_x = self.speed if facing_right else -self.speed

    def update(self):
        """Move the projectile one frame and report whether it is still alive."""
        self.hitbox.x += self.vel_x
        self.hitbox.y += self.vel_y

        if self.has_gravity:
            self.vel_y += 0.5

        self.lifetime -= 1
        return self.lifetime > 0

    def to_dict(self):
        """Serialize the projectile, including its current velocity."""
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
        """Rebuild a projectile from serialized network state."""
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
