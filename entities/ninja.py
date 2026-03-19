# Ninja - snelle combo-fighter.
#
# Snelste character, triple jump, snellere dash.
# Individuele aanvallen zijn zwakker, maar kunnen snel herhaald worden.
# Aanvallen:
#   Light   - Rapid Strike  (extreem snel, weinig schade)
#   Heavy   - Diving Kick   (diagonale kick, groot verticaal bereik)
#   Special - Shadow Strike (snelle dash-aanval met snelheidsboost)

from entities.base_character import BaseCharacter
from config import AttackData


class Ninja(BaseCharacter):

    def __init__(self, x, y, player_id):
        super().__init__(x, y, player_id)

        # Ninja-specifieke stats
        self.walk_speed = 7
        self.run_speed = 11
        self.jump_power = -15      # Hoogste sprong
        self.double_jump_power = -14
        self.max_jumps = 3         # Triple jump!
        self.jumps_remaining = self.max_jumps

        self.dash_speed = 18       # Snellere dash
        self.dash_duration = 6
        self.dash_cooldown = 20    # Kortere cooldown

        self.weight = 0.7          # Zeer licht = veel knockback ontvangen

    def get_character_name(self):
        return "Ninja"

    def light_attack(self):
        # Rapid Strike: extreem snel, weinig schade, snel herstel voor combo's.
        return self._create_attack(
            name="Rapid Strike",
            damage=AttackData.LIGHT["damage"] - 2,
            knockback_base=AttackData.LIGHT["knockback_base"] - 1,
            knockback_scaling=AttackData.LIGHT["knockback_scaling"] - 0.02,
            knockback_angle=40,
            startup_frames=AttackData.LIGHT["startup_frames"] - 1,
            active_frames=AttackData.LIGHT["active_frames"] - 1,
            recovery_frames=AttackData.LIGHT["recovery_frames"] - 3,
            hitbox_width=35,
            hitbox_height=22,
            hitbox_offset_x=5,
            hitbox_offset_y=5,
        )

    def heavy_attack(self):
        # Diving Kick: diagonale trap, groot verticaal bereik voor luchtaanvallen.
        return self._create_attack(
            name="Diving Kick",
            damage=AttackData.HEAVY["damage"] - 2,
            knockback_base=AttackData.HEAVY["knockback_base"],
            knockback_scaling=AttackData.HEAVY["knockback_scaling"],
            knockback_angle=25,
            startup_frames=AttackData.HEAVY["startup_frames"] - 2,
            active_frames=AttackData.HEAVY["active_frames"] + 2,
            recovery_frames=AttackData.HEAVY["recovery_frames"] - 2,
            hitbox_width=45,
            hitbox_height=50,   # Groot verticaal bereik
            hitbox_offset_x=5,
            hitbox_offset_y=5,
        )

    def special_attack(self):
        # Shadow Strike: dash-aanval die ook een snelheidsboost geeft.
        attack = self._create_attack(
            name="Shadow Strike",
            damage=AttackData.SPECIAL["damage"],
            knockback_base=AttackData.SPECIAL["knockback_base"] + 2,
            knockback_scaling=AttackData.SPECIAL["knockback_scaling"],
            knockback_angle=35,
            startup_frames=AttackData.SPECIAL["startup_frames"] - 2,
            active_frames=AttackData.SPECIAL["active_frames"] + 4,
            recovery_frames=AttackData.SPECIAL["recovery_frames"] - 3,
            hitbox_width=60,
            hitbox_height=40,
            hitbox_offset_x=10,
            hitbox_offset_y=10,
        )

        # Shadow Strike geeft ook een snelheidsboost vooruit
        direction = 1 if self.facing_right else -1
        self.vel_x = 12 * direction

        return attack
