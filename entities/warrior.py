# Warrior - gebalanceerde melee-fighter.
#
# Gemiddelde snelheid, gemiddelde knockback-weerstand, sterke melee-aanvallen.
# Aanvallen:
#   Light   - Quick Punch  (snel, weinig schade)
#   Heavy   - Power Kick   (langzaam, veel schade en knockback)
#   Special - Spinning Slash (grote hitbox, diagonaal omhoog)

from entities.base_character import BaseCharacter
from config import AttackData


class Warrior(BaseCharacter):
    """Default playable fighter used in the current game flow."""

    def __init__(self, x, y, player_id):
        super().__init__(x, y, player_id)

        # Warrior-specifieke stats
        self.walk_speed = 5
        self.run_speed = 8
        self.jump_power = -13
        self.weight = 1.0  # Normale knockback-weerstand

    def get_character_name(self):
        """Return the display name shown in the HUD."""
        return "Warrior"

    def light_attack(self):
        """Create the warrior's quick jab attack."""
        # Snelle punch: weinig schade, snel herstel, goed als combo-starter.
        return self._create_attack(
            name="Quick Punch",
            damage=AttackData.LIGHT["damage"],
            knockback_base=AttackData.LIGHT["knockback_base"],
            knockback_scaling=AttackData.LIGHT["knockback_scaling"],
            knockback_angle=45,
            startup_frames=AttackData.LIGHT["startup_frames"],
            active_frames=AttackData.LIGHT["active_frames"],
            recovery_frames=AttackData.LIGHT["recovery_frames"],
            hitbox_width=AttackData.LIGHT["width"],
            hitbox_height=AttackData.LIGHT["height"],
            hitbox_offset_x=5,
            hitbox_offset_y=5,
        )

    def heavy_attack(self):
        """Create the warrior's slower high-knockback kick."""
        # Krachtige kick: veel schade en knockback, maar traag.
        return self._create_attack(
            name="Power Kick",
            damage=AttackData.HEAVY["damage"],
            knockback_base=AttackData.HEAVY["knockback_base"] + 2,  # Extra knockback
            knockback_scaling=AttackData.HEAVY["knockback_scaling"],
            knockback_angle=30,
            startup_frames=AttackData.HEAVY["startup_frames"],
            active_frames=AttackData.HEAVY["active_frames"],
            recovery_frames=AttackData.HEAVY["recovery_frames"],
            hitbox_width=AttackData.HEAVY["width"],
            hitbox_height=AttackData.HEAVY["height"],
            hitbox_offset_x=10,
            hitbox_offset_y=20,
        )

    def special_attack(self):
        """Create the warrior's wide spinning slash attack."""
        # Spinning Slash: grote hitbox, raakt aan beide kanten, schiet omhoog.
        return self._create_attack(
            name="Spinning Slash",
            damage=AttackData.SPECIAL["damage"] + 2,
            knockback_base=AttackData.SPECIAL["knockback_base"],
            knockback_scaling=AttackData.SPECIAL["knockback_scaling"],
            knockback_angle=60,
            startup_frames=AttackData.SPECIAL["startup_frames"] + 2,
            active_frames=AttackData.SPECIAL["active_frames"] + 3,
            recovery_frames=AttackData.SPECIAL["recovery_frames"] + 2,
            hitbox_width=AttackData.SPECIAL["width"] + 20,   # Bredere hitbox
            hitbox_height=AttackData.SPECIAL["height"] + 20,
            hitbox_offset_x=-10,  # Gecentreerd rondom de character
            hitbox_offset_y=0,
        )
