# Mage - ranged spellcaster.
#
# Snel en licht (dus meer knockback), maar zwakkere melee.
# Aanvallen:
#   Light   - Magic Bolt   (ranged, hitbox op afstand)
#   Heavy   - Staff Swing  (melee, lange staff)
#   Special - Arcane Blast (groot explosie-gebied, langzame charge)

from entities.base_character import BaseCharacter
from entities.attack import Attack, Projectile
from config import AttackData


class Mage(BaseCharacter):

    def __init__(self, x, y, player_id):
        super().__init__(x, y, player_id)

        # Mage-specifieke stats
        self.walk_speed = 6
        self.run_speed = 9
        self.jump_power = -14      # Hogere sprong
        self.double_jump_power = -13
        self.weight = 0.8          # Licht = meer knockback ontvangen

    def get_character_name(self):
        return "Mage"

    def light_attack(self):
        # Magic Bolt: ranged aanval, hitbox op afstand van de character.
        attack = Attack(
            name="Magic Bolt",
            damage=AttackData.LIGHT["damage"] - 1,
            knockback_base=AttackData.LIGHT["knockback_base"],
            knockback_scaling=AttackData.LIGHT["knockback_scaling"],
            knockback_angle=35,
            startup_frames=AttackData.LIGHT["startup_frames"] + 1,
            active_frames=AttackData.LIGHT["active_frames"] + 2,
            recovery_frames=AttackData.LIGHT["recovery_frames"],
            hitbox_width=30,
            hitbox_height=20,
            hitbox_offset_x=40,  # Ver voor de character
            hitbox_offset_y=20,
        )
        attack.owner_id = self.player_id
        return attack

    def heavy_attack(self):
        # Staff Swing: melee met de staff, langere hitbox maar minder schade.
        attack = Attack(
            name="Staff Swing",
            damage=AttackData.HEAVY["damage"] - 3,
            knockback_base=AttackData.HEAVY["knockback_base"],
            knockback_scaling=AttackData.HEAVY["knockback_scaling"] - 0.02,
            knockback_angle=50,
            startup_frames=AttackData.HEAVY["startup_frames"] - 1,
            active_frames=AttackData.HEAVY["active_frames"],
            recovery_frames=AttackData.HEAVY["recovery_frames"] + 2,
            hitbox_width=55,   # Lange staff
            hitbox_height=25,
            hitbox_offset_x=0,
            hitbox_offset_y=20,
        )
        attack.owner_id = self.player_id
        return attack

    def special_attack(self):
        # Arcane Blast: grote explosie, veel schade en knockback, maar traag.
        attack = Attack(
            name="Arcane Blast",
            damage=AttackData.SPECIAL["damage"] + 5,
            knockback_base=AttackData.SPECIAL["knockback_base"] + 3,
            knockback_scaling=AttackData.SPECIAL["knockback_scaling"] + 0.03,
            knockback_angle=70,   # Sterk omhoog
            startup_frames=AttackData.SPECIAL["startup_frames"] + 5,
            active_frames=AttackData.SPECIAL["active_frames"],
            recovery_frames=AttackData.SPECIAL["recovery_frames"] + 5,
            hitbox_width=80,   # Grote explosie-hitbox
            hitbox_height=60,
            hitbox_offset_x=20,
            hitbox_offset_y=-10,
        )
        attack.owner_id = self.player_id
        return attack
