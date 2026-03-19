# Base Character - de basisklasse voor alle speelbare characters.
#
# Warrior, Mage en Ninja erven allemaal van deze class.
# Ze overschrijven de drie attack-methodes met hun eigen aanvallen.

import math
import os
import pygame

from config import (
    CharacterStats, Colors, GRAVITY, MAX_FALL_SPEED,
    GROUND_FRICTION, AIR_FRICTION, KILL_BOUNDARY, CONTROLS, SPRITE_CONFIG,
    STAT_POINT_BUDGET,
    ULTIMATE_SHOP_INDEX,
)
from entities.attack import Attack, Projectile


_SPRITE_RENDER_SIZE = 192  # Pixels to render each sprite frame (square)
_shared_sprites = None    # Raw scaled frames, loaded once and shared per process

# States whose animation plays once and holds on the last frame (no looping)
_NON_LOOPING_STATES = frozenset({
    "jump_stationary", "jump_moving", "double_jump",
    "landing", "landing_impact",
    "punch1", "kick", "special", "jump_strike",
    "crouch",
})

# Tint colors per player — saturated so BLEND_MULT produces vivid hues
_PLAYER_TINT_COLORS = [
    (255, 55, 55),   # P1 - vivid red
    (55, 55, 255),   # P2 - vivid blue
    (55, 210, 55),   # P3 - vivid green
    (255, 215, 30),  # P4 - vivid yellow
]


def _apply_tint(surface, tint_color):
    tinted = surface.copy()
    # BLEND_MULT colorises but darkens; BLEND_ADD recovers brightness
    tinted.fill(tint_color, special_flags=pygame.BLEND_MULT)
    tinted.fill((55, 55, 55), special_flags=pygame.BLEND_ADD)
    return tinted


def _make_silhouette(surface, outline_color):
    # Zet alle zichtbare pixels om naar outline_color, alpha blijft behouden.
    sil = surface.copy()
    sil.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MIN)  # RGB → 0, alpha intact
    sil.fill((*outline_color, 0), special_flags=pygame.BLEND_RGBA_ADD)  # kleur toevoegen
    return sil


_OUTLINE_OFFSETS = ((0, -2), (0, 2), (-2, 0), (2, 0))


class BaseCharacter:
    # Basisklasse voor alle characters.
    # Bevat beweging, physics, gevecht en netwerk-synchronisatie.
    # Subclasses MOETEN light_attack, heavy_attack, special_attack
    # en get_character_name implementeren.

    def __init__(self, x, y, player_id):
        # Positie en snelheid
        self.x = x
        self.y = y
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.player_id = player_id

        # Afmetingen
        self.width = CharacterStats.WIDTH
        self.height = CharacterStats.HEIGHT

        # Bewegingssnelheden (kunnen overschreven worden in subclass)
        self.walk_speed = CharacterStats.WALK_SPEED
        self.run_speed = CharacterStats.RUN_SPEED
        self.jump_power = CharacterStats.JUMP_POWER
        self.double_jump_power = CharacterStats.DOUBLE_JUMP_POWER
        self.max_jumps = CharacterStats.MAX_JUMPS
        self.dash_speed = CharacterStats.DASH_SPEED
        self.dash_duration = CharacterStats.DASH_DURATION
        self.dash_cooldown = CharacterStats.DASH_COOLDOWN

        # Gevecht
        self.damage_percent = 0.0  # Opgelopen schade (meer = verder weggeslagen)
        self.stocks = 3            # Aantal levens
        self.attack_cooldown = 0
        self.hitstun = 0           # Frames dat character niet kan bewegen na een treffer
        self.invincible = 0        # Onkwetsbaarheidsframes na respawn

        # Bewegingsstatus
        self.on_ground = False
        self.jumps_remaining = self.max_jumps
        self.facing_right = True
        self.is_dashing = False
        self.dash_frames = 0
        self.dash_cooldown_timer = 0
        self.is_crouching = False

        # Animatiestatus
        self.state = "idle"
        self.animation_frame = 0
        self.animation_timer = 0
        self.jump_type = "stationary"   # "stationary" | "moving" | "double"
        self.prev_on_ground = False     # on_ground van het vorige frame (voor landing-detectie)
        self.landing_timer = 0          # frames gespendeerd in landing/landing_impact

        # Actieve aanval
        self.active_attack = None
        self.attack_frame = 0
        self.last_attacker_id = None
        self.last_attacker_timer = 0
        self.gameplay_events = []

        # Kleur (voor het tekenen)
        self.color = Colors.PLAYER_COLORS[player_id % len(Colors.PLAYER_COLORS)]
        self.sprites = {}
        self.outline_sprites = {}
        self.sprites_loaded = False
        self._prev_state = "idle"

        # Build-stats voor de pre-game verdeling.
        self.build_stats = {
            "power": 0,
            "defense": 0,
            "mobility": 0,
            "knockback": 0,
            "range": 0,
        }
        self.equipped_ultimate_id = None
        self.ultimate_cooldown_timer = 0
        self.ultimate_preview_active = False
        self.ultimate_cast_timer = 0
        self.casting_ultimate_id = None
        self.pending_ultimate_id = None
        self.pending_ultimate_direction = None
        self.teleport_glow_color = None
        self.active_ultimate_projectile = None
        self.invisible_timer = 0
        self.grabbed_target_id = None
        self.grab_hold_timer = 0
        self.absorbed_by_id = None
        self._grabbed_target_ref = None
        self.parry_active_timer = 0
        self.parry_recovery_timer = 0

    def light_attack(self):
        # Geeft een Attack-object terug voor de lichte aanval.
        raise NotImplementedError("Subclass moet light_attack() implementeren")

    def heavy_attack(self):
        # Geeft een Attack-object terug voor de zware aanval.
        raise NotImplementedError("Subclass moet heavy_attack() implementeren")

    def special_attack(self):
        # Geeft een Attack-object terug voor de speciale aanval.
        raise NotImplementedError("Subclass moet special_attack() implementeren")

    def get_character_name(self):
        # Geeft de naam van dit character terug (bijv. "Warrior").
        raise NotImplementedError("Subclass moet get_character_name() implementeren")

    def set_build_stats(self, stats):
        # Sla build-stats op zodat beweging en aanvallen er direct mee kunnen schalen.
        for stat_name in self.build_stats:
            self.build_stats[stat_name] = max(0, int(stats.get(stat_name, self.build_stats[stat_name])))
        self._apply_build_modifiers()

    def set_equipped_ultimate(self, ultimate_id):
        self.equipped_ultimate_id = ultimate_id if ultimate_id in ULTIMATE_SHOP_INDEX else None
        if self.pending_ultimate_id != self.equipped_ultimate_id:
            self.cancel_ultimate_preview()

    def _apply_build_modifiers(self):
        # Vertaal build-stats naar movement- en combatmodifiers.
        mobility = self.build_stats["mobility"]
        self.walk_speed = CharacterStats.WALK_SPEED + (0.45 * mobility)
        self.run_speed = CharacterStats.RUN_SPEED + (0.7 * mobility)
        self.jump_power = CharacterStats.JUMP_POWER - (0.5 * mobility)
        self.double_jump_power = CharacterStats.DOUBLE_JUMP_POWER - (0.4 * mobility)
        self.dash_speed = CharacterStats.DASH_SPEED + (0.9 * mobility)
        self.dash_duration = CharacterStats.DASH_DURATION + (mobility // 3)
        self.dash_cooldown = max(10, CharacterStats.DASH_COOLDOWN - (2 * mobility))
        self.max_jumps = 3 if mobility >= 6 else CharacterStats.MAX_JUMPS
        self.jumps_remaining = min(self.jumps_remaining, self.max_jumps)

    def _scale_damage(self, damage):
        power_points = self.build_stats["power"]
        return damage + (0.8 * power_points)

    def _scale_knockback(self, knockback_base, knockback_scaling):
        # Knockback-punten versterken zowel basis- als scaling-knockback.
        knockback_points = self.build_stats["knockback"]
        base_bonus = 0.6 * knockback_points
        scaling_bonus = 0.015 * knockback_points
        return knockback_base + base_bonus, knockback_scaling + scaling_bonus

    def _scale_attack_range(self, hitbox_width, hitbox_height, hitbox_offset_x, hitbox_offset_y):
        # Range vergroot vooral het effectieve bereik van de hitbox.
        range_points = self.build_stats["range"]
        range_factor = 1.0 + (0.08 * range_points)

        scaled_width = max(1, int(round(hitbox_width * range_factor)))
        scaled_height = max(1, int(round(hitbox_height * (1.0 + 0.04 * range_points))))
        scaled_offset_x = int(round(hitbox_offset_x * range_factor))
        scaled_offset_y = int(round(hitbox_offset_y))
        return scaled_width, scaled_height, scaled_offset_x, scaled_offset_y

    def _create_attack(
        self,
        name,
        damage,
        knockback_base,
        knockback_scaling,
        knockback_angle,
        startup_frames,
        active_frames,
        recovery_frames,
        hitbox_width,
        hitbox_height,
        hitbox_offset_x=0,
        hitbox_offset_y=0,
    ):
        # Bouw een aanval op basis van de huidige build-stats.
        scaled_knockback_base, scaled_knockback_scaling = self._scale_knockback(
            knockback_base,
            knockback_scaling,
        )
        scaled_width, scaled_height, scaled_offset_x, scaled_offset_y = self._scale_attack_range(
            hitbox_width,
            hitbox_height,
            hitbox_offset_x,
            hitbox_offset_y,
        )

        attack = Attack(
            name=name,
            damage=self._scale_damage(damage),
            knockback_base=scaled_knockback_base,
            knockback_scaling=scaled_knockback_scaling,
            knockback_angle=knockback_angle,
            startup_frames=startup_frames,
            active_frames=active_frames,
            recovery_frames=recovery_frames,
            hitbox_width=scaled_width,
            hitbox_height=scaled_height,
            hitbox_offset_x=scaled_offset_x,
            hitbox_offset_y=scaled_offset_y,
        )
        attack.owner_id = self.player_id
        return attack

    def update(self, platforms, dt=1.0):
        # Update alles voor één frame: timers, physics, collision, aanval, animatie.
        self._update_timers()

        if self.absorbed_by_id is not None:
            self.vel_x = 0
            self.vel_y = 0
            self.active_attack = None
            self.active_ultimate_projectile = None
            self._update_animation_state()
            return

        if self.ultimate_cast_timer > 0:
            self._update_ultimate_cast()
            self._update_animation_state()
            return

        if self.hitstun <= 0:
            self._apply_gravity()
            self._apply_friction()

        self.x += self.vel_x * dt
        self.y += self.vel_y * dt

        self._handle_platform_collision(platforms)
        self._check_boundaries()

        if self.active_attack:
            self._update_attack()
        if self.active_ultimate_projectile:
            self._update_ultimate_projectile()
        if self.grabbed_target_id is not None:
            self._update_grab_hold()

        self._update_animation_state()

    def _apply_gravity(self):
        # Pas zwaartekracht toe (niet tijdens een dash).
        if not self.on_ground and not self.is_dashing:
            self.vel_y += GRAVITY
            if self.vel_y > MAX_FALL_SPEED:
                self.vel_y = MAX_FALL_SPEED

    def _apply_friction(self):
        # Vertraag de horizontale snelheid (meer wrijving op de grond dan in de lucht).
        if self.is_dashing:
            return

        if self.on_ground:
            self.vel_x *= GROUND_FRICTION
        else:
            self.vel_x *= AIR_FRICTION

        # Stop als snelheid onder de run-drempel valt zodat idle nooit flikkert
        if abs(self.vel_x) < 0.5:
            self.vel_x = 0

    def _update_timers(self):
        # Tel alle timers één frame omlaag.
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.hitstun > 0:
            self.hitstun -= 1
        if self.invincible > 0:
            self.invincible -= 1
        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= 1
        if self.ultimate_cooldown_timer > 0:
            self.ultimate_cooldown_timer -= 1
        if self.invisible_timer > 0:
            self.invisible_timer -= 1
            if self.invisible_timer <= 0:
                self.end_invisibility(start_cooldown=True)
        if self.grab_hold_timer > 0 and self.grabbed_target_id is not None:
            self.grab_hold_timer -= 1
        if self.parry_active_timer > 0:
            self.parry_active_timer -= 1
            if self.parry_active_timer <= 0 and self.parry_recovery_timer <= 0:
                self.ultimate_cooldown_timer = ULTIMATE_SHOP_INDEX["parry_counter"]["miss_cooldown_frames"]
                self.parry_recovery_timer = ULTIMATE_SHOP_INDEX["parry_counter"]["recovery_frames"]
        if self.parry_recovery_timer > 0:
            self.parry_recovery_timer -= 1
        if self.last_attacker_timer > 0:
            self.last_attacker_timer -= 1
            if self.last_attacker_timer <= 0:
                self.last_attacker_id = None
        if self.is_dashing:
            self.dash_frames -= 1
            if self.dash_frames <= 0:
                self.is_dashing = False

    def _handle_platform_collision(self, platforms):
        # Controleer of de character op een platform landt.
        self.on_ground = False

        for platform in platforms:
            if self._collides_with_platform(platform):
                if self.vel_y >= 0:
                    self.y = platform.y - self.height
                    self.vel_y = 0
                    self.on_ground = True
                    self.jumps_remaining = self.max_jumps

    def _collides_with_platform(self, platform):
        # Controleer of we van boven door het platform vallen (AABB collision).
        char_bottom = self.y + self.height
        char_prev_bottom = char_bottom - self.vel_y

        return (
            self.x + self.width > platform.x and
            self.x < platform.x + platform.width and
            char_prev_bottom <= platform.y and
            char_bottom >= platform.y
        )

    def _check_boundaries(self):
        # Als de character buiten het speelveld komt, verliest hij een leven.
        if (self.x < KILL_BOUNDARY["left"] or
                self.x > KILL_BOUNDARY["right"] or
                self.y < KILL_BOUNDARY["top"] or
                self.y > KILL_BOUNDARY["bottom"]):
            self.die()

    def handle_input(self, keys):
        # Verwerk ingedrukte toetsen (voor beweging links/rechts en crouch).
        if self.hitstun > 0 or self.ultimate_cast_timer > 0 or self.absorbed_by_id is not None or self.parry_active_timer > 0 or self.parry_recovery_timer > 0:
            return None

        crouching = self.on_ground and any(keys[k] for k in CONTROLS["down"])
        self.is_crouching = crouching

        if self.ultimate_preview_active:
            self.pending_ultimate_direction = self._get_direction_from_keys(keys)

        if not self.active_attack and not crouching:
            if any(keys[k] for k in CONTROLS["left"]):
                self.move_left()
            elif any(keys[k] for k in CONTROLS["right"]):
                self.move_right()

        return None

    def handle_key_down(self, key):
        # Verwerk één toetsdruk (springen, dash, aanval).
        if self.hitstun > 0 or self.absorbed_by_id is not None or self.parry_active_timer > 0 or self.parry_recovery_timer > 0:
            return None

        if key in CONTROLS["ultimate_ability"]:
            if self.equipped_ultimate_id == "teleportation":
                return self.start_ultimate_preview(self._get_direction_from_keys(pygame.key.get_pressed()))
            return self.activate_ultimate()

        if self.ultimate_preview_active:
            return None
        if self.ultimate_cast_timer > 0:
            return None

        if key in CONTROLS["jump"]:
            self.jump()

        if key in CONTROLS["dash"]:
            self.dash()

        if self.attack_cooldown <= 0 and not self.active_attack:
            if key in CONTROLS["light_attack"]:
                return self.start_attack("light")
            elif key in CONTROLS["heavy_attack"]:
                return self.start_attack("heavy")
            elif key in CONTROLS["special_attack"]:
                return self.start_attack("special")

        return None

    def handle_key_up(self, key):
        if key in CONTROLS["ultimate_ability"]:
            return self.release_ultimate()
        return None

    def apply_input_state(self, input_state):
        # Verwerk input vanuit de server (netwerkmodus).
        if self.hitstun > 0 or self.absorbed_by_id is not None or self.parry_active_timer > 0 or self.parry_recovery_timer > 0:
            return

        if input_state.get("ultimate_trigger"):
            if self.equipped_ultimate_id == "teleportation":
                self.start_ultimate_preview(self._get_direction_from_input_state(input_state))
            else:
                self.activate_ultimate()
        if input_state.get("ultimate_release"):
            self.release_ultimate()
        elif input_state.get("ultimate_preview"):
            self.start_ultimate_preview(self._get_direction_from_input_state(input_state))
        elif self.ultimate_preview_active:
            self.cancel_ultimate_preview()

        if self.ultimate_cast_timer > 0:
            return

        if not self.active_attack:
            if input_state.get("left"):
                self.move_left()
            elif input_state.get("right"):
                self.move_right()

        if input_state.get("jump"):
            self.jump()

        if input_state.get("dash"):
            self.dash()

        if self.attack_cooldown <= 0 and not self.active_attack:
            if input_state.get("light_attack"):
                self.start_attack("light")
            elif input_state.get("heavy_attack"):
                self.start_attack("heavy")
            elif input_state.get("special_attack"):
                self.start_attack("special")

    def move_left(self):
        if not self.is_dashing and not self.active_attack:
            self.vel_x = -self.walk_speed
            self.facing_right = False

    def move_right(self):
        if not self.is_dashing and not self.active_attack:
            self.vel_x = self.walk_speed
            self.facing_right = True

    def jump(self):
        # Spring als er nog sprongen over zijn.
        if self.jumps_remaining > 0 and not self.active_attack:
            if self.on_ground or self.jumps_remaining == self.max_jumps:
                # Eerste sprong (van de grond of na van platform af gelopen)
                self.jump_type = "moving" if abs(self.vel_x) > 0.5 else "stationary"
                self.vel_y = self.jump_power
            else:
                # Dubbele sprong
                self.jump_type = "double"
                self.vel_y = self.double_jump_power
            self.jumps_remaining -= 1
            self.on_ground = False

    def dash(self):
        # Dash snel vooruit als de cooldown voorbij is.
        if self.dash_cooldown_timer <= 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_frames = self.dash_duration
            self.dash_cooldown_timer = self.dash_cooldown
            direction = 1 if self.facing_right else -1
            self.vel_x = self.dash_speed * direction
            self.vel_y = 0

    def start_attack(self, attack_type):
        # Start een aanval van het opgegeven type ("light", "heavy" of "special").
        if (
            self.active_attack or
            self.attack_cooldown > 0 or
            self.ultimate_preview_active or
            self.ultimate_cast_timer > 0 or
            self.grabbed_target_id is not None or
            self.absorbed_by_id is not None
        ):
            return None

        # Roep de juiste methode aan — dit is polymorfisme in actie!
        if attack_type == "light":
            self.active_attack = self.light_attack()
            self.state = "jump_strike" if not self.on_ground else "punch1"
        elif attack_type == "heavy":
            self.active_attack = self.heavy_attack()
            self.state = "kick"
        elif attack_type == "special":
            self.active_attack = self.special_attack()
            self.state = "special"
        else:
            return None

        if self.invisible_timer > 0:
            self.active_attack.damage *= ULTIMATE_SHOP_INDEX["invisibility"]["attack_damage_multiplier"]
            self.end_invisibility(start_cooldown=True)

        self.attack_frame = 0
        return self.active_attack

    def _get_direction_from_keys(self, keys):
        if any(keys[k] for k in CONTROLS["up"]):
            return "up"
        if any(keys[k] for k in CONTROLS["down"]):
            return "down"
        if any(keys[k] for k in CONTROLS["left"]):
            return "left"
        if any(keys[k] for k in CONTROLS["right"]):
            return "right"
        return "right" if self.facing_right else "left"

    def _get_direction_from_input_state(self, input_state):
        if input_state.get("up"):
            return "up"
        if input_state.get("down"):
            return "down"
        if input_state.get("left"):
            return "left"
        if input_state.get("right"):
            return "right"
        return "right" if self.facing_right else "left"

    def start_ultimate_preview(self, direction):
        if self.ultimate_preview_active:
            self.pending_ultimate_direction = direction or self.pending_ultimate_direction
            return True
        if self.active_attack or self.attack_cooldown > 0 or self.ultimate_cast_timer > 0:
            return False
        if self.equipped_ultimate_id != "teleportation":
            return False
        if self.ultimate_cooldown_timer > 0:
            return False

        self.ultimate_preview_active = True
        self.pending_ultimate_id = self.equipped_ultimate_id
        self.pending_ultimate_direction = direction or ("right" if self.facing_right else "left")
        self.teleport_glow_color = ULTIMATE_SHOP_INDEX[self.equipped_ultimate_id].get("glow_color", Colors.CYAN)
        return True

    def cancel_ultimate_preview(self):
        self.ultimate_preview_active = False
        self.pending_ultimate_id = None
        self.pending_ultimate_direction = None
        self.teleport_glow_color = None

    def activate_ultimate(self):
        if self.ultimate_preview_active or self.ultimate_cast_timer > 0:
            return False
        if self.active_attack or self.attack_cooldown > 0:
            return False
        if self.equipped_ultimate_id not in ("fireball", "invisibility", "grab", "parry_counter"):
            return False
        if self.ultimate_cooldown_timer > 0:
            return False
        if self.invisible_timer > 0:
            return False
        if self.grabbed_target_id is not None or self.absorbed_by_id is not None:
            return False
        if self.equipped_ultimate_id == "grab" and not self.on_ground:
            return False

        ultimate = ULTIMATE_SHOP_INDEX[self.equipped_ultimate_id]
        self.ultimate_cast_timer = ultimate["cast_frames"]
        self.casting_ultimate_id = self.equipped_ultimate_id
        self.teleport_glow_color = ultimate.get("glow_color", Colors.ORANGE)
        self.vel_x = 0
        self.vel_y = 0
        self.is_dashing = False
        self.dash_frames = 0
        return True

    def release_ultimate(self):
        if not self.ultimate_preview_active or self.pending_ultimate_id != "teleportation":
            return False
        if self.active_attack or self.attack_cooldown > 0:
            self.cancel_ultimate_preview()
            return False

        self._perform_teleportation()
        self._check_boundaries()
        self.ultimate_cooldown_timer = ULTIMATE_SHOP_INDEX["teleportation"]["cooldown_frames"]
        self.cancel_ultimate_preview()
        return True

    def _update_ultimate_cast(self):
        if self.ultimate_cast_timer <= 0:
            return

        self.vel_x = 0
        self.vel_y = 0
        self.is_dashing = False
        self.dash_frames = 0
        self.ultimate_cast_timer -= 1
        if self.ultimate_cast_timer > 0:
            return

        if self.casting_ultimate_id == "fireball":
            self._launch_fireball()
            self.ultimate_cooldown_timer = ULTIMATE_SHOP_INDEX["fireball"]["cooldown_frames"]
        elif self.casting_ultimate_id == "invisibility":
            self._activate_invisibility()
        elif self.casting_ultimate_id == "grab":
            self._start_grab_attack()
        elif self.casting_ultimate_id == "parry_counter":
            self._start_parry_counter()

        self.casting_ultimate_id = None
        if not self.ultimate_preview_active and self.parry_active_timer <= 0:
            self.teleport_glow_color = None

    def _perform_teleportation(self):
        ultimate = ULTIMATE_SHOP_INDEX["teleportation"]
        distance = ultimate["distance"]
        direction = self.pending_ultimate_direction or ("right" if self.facing_right else "left")

        if direction == "up":
            self.y -= distance
        elif direction == "down":
            self.y += distance
        elif direction == "left":
            self.x -= distance
            self.facing_right = False
        else:
            self.x += distance
            self.facing_right = True

    def _launch_fireball(self):
        ultimate = ULTIMATE_SHOP_INDEX["fireball"]
        damage = self._scale_damage(ultimate["damage"])
        knockback_base, knockback_scaling = self._scale_knockback(
            ultimate["knockback_base"],
            ultimate["knockback_scaling"],
        )
        hitbox_width, hitbox_height, _, _ = self._scale_attack_range(
            ultimate["hitbox_width"],
            ultimate["hitbox_height"],
            0,
            0,
        )

        projectile = Projectile(
            name="Fireball",
            damage=damage,
            knockback_base=knockback_base,
            knockback_scaling=knockback_scaling,
            knockback_angle=ultimate["knockback_angle"],
            hitbox_width=hitbox_width,
            hitbox_height=hitbox_height,
            speed=ultimate["projectile_speed"],
            lifetime=ultimate["projectile_lifetime"],
        )
        projectile.owner_id = self.player_id
        spawn_x = self.x + self.width + ultimate["spawn_offset_x"] if self.facing_right else self.x - hitbox_width - ultimate["spawn_offset_x"]
        spawn_y = self.y + ultimate["spawn_offset_y"]
        projectile.launch(spawn_x, spawn_y, self.facing_right)
        self.active_ultimate_projectile = projectile

    def _activate_invisibility(self):
        self.invisible_timer = ULTIMATE_SHOP_INDEX["invisibility"]["duration_frames"]

    def end_invisibility(self, start_cooldown=False):
        was_invisible = self.invisible_timer > 0
        self.invisible_timer = 0
        if start_cooldown and was_invisible:
            self.ultimate_cooldown_timer = ULTIMATE_SHOP_INDEX["invisibility"]["cooldown_frames"]

    def _start_grab_attack(self):
        ultimate = ULTIMATE_SHOP_INDEX["grab"]
        hitbox_width, hitbox_height, hitbox_offset_x, hitbox_offset_y = self._scale_attack_range(
            ultimate["hitbox_width"],
            ultimate["hitbox_height"],
            ultimate["hitbox_offset_x"],
            ultimate["hitbox_offset_y"],
        )
        self.active_attack = Attack(
            name="Grab",
            damage=0,
            knockback_base=0,
            knockback_scaling=0,
            knockback_angle=0,
            startup_frames=0,
            active_frames=ultimate["active_frames"],
            recovery_frames=ultimate["recovery_frames"],
            hitbox_width=hitbox_width,
            hitbox_height=hitbox_height,
            hitbox_offset_x=hitbox_offset_x,
            hitbox_offset_y=hitbox_offset_y,
            effect_type="grab",
            hold_frames=ultimate["hold_frames"],
            throw_knockback_base=ultimate["throw_knockback_base"],
            throw_knockback_scaling=ultimate["throw_knockback_scaling"],
            throw_angle=ultimate["throw_angle"],
        )
        self.active_attack.owner_id = self.player_id
        self.attack_frame = 0
        self.state = "special"

    def _start_parry_counter(self):
        ultimate = ULTIMATE_SHOP_INDEX["parry_counter"]
        self.parry_active_timer = ultimate["parry_frames"]
        self.parry_recovery_timer = 0
        self.state = "special"

    def try_parry_hit(self, attacker, attack):
        if self.parry_active_timer <= 0:
            return False

        ultimate = ULTIMATE_SHOP_INDEX["parry_counter"]
        knockback_base, knockback_scaling = self._scale_knockback(
            ultimate["counter_knockback_base"],
            ultimate["counter_knockback_scaling"],
        )
        hitbox_width, hitbox_height, _, hitbox_offset_y = self._scale_attack_range(
            ultimate["counter_hitbox_width"],
            ultimate["counter_hitbox_height"],
            0,
            (self.height - ultimate["counter_hitbox_height"]) // 2,
        )
        self.parry_active_timer = 0
        self.parry_recovery_timer = 0
        self.ultimate_cooldown_timer = ultimate["cooldown_frames"]
        self.teleport_glow_color = None
        self.active_ultimate_projectile = None
        self.active_attack = Attack(
            name="Parry Counter",
            damage=self._scale_damage(ultimate["counter_damage"]),
            knockback_base=knockback_base,
            knockback_scaling=knockback_scaling,
            knockback_angle=ultimate["counter_knockback_angle"],
            startup_frames=0,
            active_frames=6,
            recovery_frames=ultimate["recovery_frames"],
            hitbox_width=hitbox_width,
            hitbox_height=hitbox_height,
            hitbox_offset_y=hitbox_offset_y,
            anchor_mode="center",
        )
        self.active_attack.owner_id = self.player_id
        self.attack_frame = 0
        self.state = "special"

        attack.is_active = False
        if hasattr(attack, "lifetime"):
            attack.lifetime = 0
        return True

    def handle_grab_hit(self, target, attack):
        if self.grabbed_target_id is not None or target.absorbed_by_id is not None:
            return

        self.grabbed_target_id = target.player_id
        self.grab_hold_timer = attack.hold_frames
        self._grabbed_target_ref = target
        target.absorbed_by_id = self.player_id
        target.vel_x = 0
        target.vel_y = 0
        target.active_attack = None
        target.active_ultimate_projectile = None
        target.cancel_ultimate_preview()
        target.ultimate_cast_timer = 0
        target.casting_ultimate_id = None
        target.teleport_glow_color = None
        target.end_invisibility(start_cooldown=False)
        attack.is_active = False
        self.active_attack = None

    def _update_grab_hold(self):
        target = self._grabbed_target_ref
        if not target or target.player_id != self.grabbed_target_id:
            self._clear_grabbed_target()
            return

        target.x = self.x
        target.y = self.y
        target.vel_x = 0
        target.vel_y = 0

        if self.grab_hold_timer <= 0:
            self._release_grabbed_target()

    def _release_grabbed_target(self):
        target = self._grabbed_target_ref
        if not target:
            self._clear_grabbed_target()
            return

        ultimate = ULTIMATE_SHOP_INDEX["grab"]
        target.absorbed_by_id = None
        target.x = self.x + (self.width + 12 if self.facing_right else -target.width - 12)
        target.y = self.y + 6
        target.take_damage(
            damage=0,
            knockback_base=ultimate["throw_knockback_base"],
            knockback_scaling=ultimate["throw_knockback_scaling"],
            angle=ultimate["throw_angle"],
            attacker_x=self.x,
            attacker_id=self.player_id,
        )
        self.ultimate_cooldown_timer = ultimate["cooldown_frames"]
        self._clear_grabbed_target()

    def _clear_grabbed_target(self):
        if self._grabbed_target_ref:
            self._grabbed_target_ref.absorbed_by_id = None
        self._grabbed_target_ref = None
        self.grabbed_target_id = None
        self.grab_hold_timer = 0

    def _update_ultimate_projectile(self):
        if not self.active_ultimate_projectile:
            return
        if not self.active_ultimate_projectile.update() or not self.active_ultimate_projectile.is_active:
            self.active_ultimate_projectile = None

    def _update_attack(self):
        # Werk de actieve aanval bij: startup → active → recovery.
        if not self.active_attack:
            return

        self.attack_frame += 1
        total_frames = (self.active_attack.startup_frames +
                        self.active_attack.active_frames +
                        self.active_attack.recovery_frames)

        # Verplaats de hitbox mee met de character
        self.active_attack.update_position(self.x, self.y, self.facing_right, self.width)

        # Bepaal in welke fase de aanval zit
        if self.attack_frame < self.active_attack.startup_frames:
            self.active_attack.is_active = False  # Opstartfase: nog geen hitbox
        elif self.attack_frame < (self.active_attack.startup_frames + self.active_attack.active_frames):
            self.active_attack.is_active = True   # Actiefase: hitbox aan
        else:
            self.active_attack.is_active = False  # Herstelfase: hitbox uit

        # Aanval is klaar
        if self.attack_frame >= total_frames:
            if self.active_attack.effect_type == "grab":
                self.ultimate_cooldown_timer = ULTIMATE_SHOP_INDEX["grab"]["cooldown_frames"]
            self.active_attack = None
            self.attack_cooldown = CharacterStats.ATTACK_COOLDOWN

    def take_damage(self, damage, knockback_base, knockback_scaling, angle, attacker_x, attacker_id=None):
        # Ontvang schade: verhoog damage% en vlieg weg (knockback).
        if self.invincible > 0:
            return

        self.damage_percent += damage
        if attacker_id is not None and attacker_id != self.player_id:
            self.last_attacker_id = attacker_id
            self.last_attacker_timer = 300

        # Knockback-formule: hoe meer schade, hoe verder weggeslagen
        defense_points = self.build_stats["defense"]
        defense_multiplier = max(0.55, 1.0 - (0.06 * defense_points))
        knockback = (knockback_base + (self.damage_percent * knockback_scaling)) * defense_multiplier

        angle_rad = math.radians(angle)
        direction = -1 if attacker_x > self.x else 1

        self.vel_x = knockback * math.cos(angle_rad) * direction
        self.vel_y = -knockback * math.sin(angle_rad)

        # Hitstun: tijdelijk niet kunnen bewegen
        self.hitstun = int(knockback * 2)
        self.active_attack = None
        self.cancel_ultimate_preview()
        self.ultimate_cast_timer = 0
        self.casting_ultimate_id = None
        self.teleport_glow_color = None
        self.parry_active_timer = 0
        self.parry_recovery_timer = 0
        self._clear_grabbed_target()

    def die(self):
        # Verlies een leven en respawn als er nog levens over zijn.
        killer_id = self.last_attacker_id if self.last_attacker_id != self.player_id else None
        self.gameplay_events.append({
            "type": "death",
            "player_id": self.player_id,
            "killer_id": killer_id,
        })

        if self.stocks < 0:
            self.respawn()
            return

        self.stocks -= 1
        if self.stocks > 0:
            self.respawn()
        else:
            self.last_attacker_id = None
            self.last_attacker_timer = 0

    def respawn(self):
        # Zet de character terug op de startpositie.
        from config import SPAWN_POSITIONS
        spawn = SPAWN_POSITIONS[self.player_id % len(SPAWN_POSITIONS)]
        self.x = spawn[0]
        self.y = spawn[1]
        self.vel_x = 0
        self.vel_y = 0
        self.damage_percent = 0
        self.hitstun = 0
        self.invincible = 120  # 2 seconden onkwetsbaar (120 frames bij 60 fps)
        self.active_attack = None
        self.active_ultimate_projectile = None
        self._clear_grabbed_target()
        self.jumps_remaining = self.max_jumps
        self.last_attacker_id = None
        self.last_attacker_timer = 0
        self.jump_type = "stationary"
        self.landing_timer = 0
        self.prev_on_ground = False
        self.cancel_ultimate_preview()
        self.ultimate_cast_timer = 0
        self.casting_ultimate_id = None
        self.teleport_glow_color = None
        self.invisible_timer = 0
        self.absorbed_by_id = None
        self.parry_active_timer = 0
        self.parry_recovery_timer = 0

    def consume_gameplay_events(self):
        events = list(self.gameplay_events)
        self.gameplay_events.clear()
        return events

    def _update_animation_state(self):
        # Bepaal welke animatie afgespeeld wordt op basis van wat de character doet.
        if self.absorbed_by_id is not None:
            self.state = "idle"
        elif self.ultimate_cast_timer > 0 or self.parry_active_timer > 0:
            self.state = "special"
        elif not self.active_attack:
            just_landed = self.on_ground and not self.prev_on_ground

            if self.hitstun > 0:
                if not self.on_ground:
                    # Knockback in de lucht → Falling.png
                    self.state = "hurt"
                elif just_landed and self.state == "hurt":
                    # Net geland vanuit knockback → zware landing
                    self.state = "landing_impact"
                    self.landing_timer = 0
                elif self.state == "landing_impact":
                    # Hitstun loopt nog terwijl landing_impact afspeelt
                    cfg = SPRITE_CONFIG["default"].get("landing_impact", {})
                    total = cfg.get("frames", 13) * cfg.get("animation_speed", 3)
                    if self.landing_timer >= total:
                        self.state = "idle"
                    else:
                        self.landing_timer += 1

            elif self.state == "landing_impact":
                # Hitstun voorbij maar animatie nog niet klaar
                cfg = SPRITE_CONFIG["default"].get("landing_impact", {})
                total = cfg.get("frames", 13) * cfg.get("animation_speed", 3)
                if self.landing_timer >= total:
                    self.state = "idle"
                else:
                    self.landing_timer += 1

            elif self.state == "landing":
                cfg = SPRITE_CONFIG["default"].get("landing", {})
                total = cfg.get("frames", 6) * cfg.get("animation_speed", 4)
                if self.landing_timer >= total:
                    self.state = "idle"
                else:
                    self.landing_timer += 1

            elif self.is_dashing:
                self.state = "dash"

            elif not self.on_ground:
                self.is_crouching = False
                # Eigen sprong — type werd ingesteld in jump()
                if self.jump_type == "double":
                    self.state = "double_jump"
                elif self.jump_type == "moving":
                    self.state = "jump_moving"
                else:
                    self.state = "jump_stationary"

            else:
                # Op de grond, geen hitstun, niet aan het dashen
                if just_landed and self.state in ("jump_stationary", "jump_moving", "double_jump", "jump_strike"):
                    # Normale landing na eigen sprong
                    self.state = "landing"
                    self.landing_timer = 0
                    self.jump_type = "stationary"  # reset voor volgende sprong
                elif self.is_crouching:
                    self.state = "crouch"
                elif abs(self.vel_x) > 0.5:
                    mobility = self.build_stats["mobility"]
                    if mobility >= STAT_POINT_BUDGET * 2 / 3:
                        self.state = "speed_run"
                    elif mobility >= STAT_POINT_BUDGET / 3:
                        self.state = "run"
                    else:
                        self.state = "walk"
                else:
                    self.state = "idle"

        self.prev_on_ground = self.on_ground

        # Reset timer wanneer de animatie verandert
        if self.state != self._prev_state:
            self.animation_timer = 0
            self._prev_state = self.state
        else:
            self.animation_timer += 1

        # Bereken het huidige frame-index
        config = SPRITE_CONFIG.get("default", {}).get(self.state, {})
        num_frames = config.get("frames", 4)
        speed = config.get("animation_speed", 5)

        if self.state in _NON_LOOPING_STATES:
            penultimate_hold = config.get("penultimate_hold", 0)
            if penultimate_hold > 0 and num_frames >= 2:
                # Alle frames t/m een-na-laatste lopen normaal;
                # daarna extra hold op een-na-laatste, dan pas het laatste frame.
                normal_time = (num_frames - 2) * speed
                penultimate_time = speed + penultimate_hold
                if self.animation_timer < normal_time:
                    self.animation_frame = self.animation_timer // speed
                elif self.animation_timer < normal_time + penultimate_time:
                    self.animation_frame = num_frames - 2
                else:
                    self.animation_frame = num_frames - 1
            else:
                # Niet-lopende animaties: vasthouden op het laatste frame
                self.animation_frame = min(self.animation_timer // speed, num_frames - 1)
        else:
            self.animation_frame = (self.animation_timer // speed) % num_frames

    def get_rect(self):
        # Geef de collision-rechthoek van de character terug.
        # Bij crouch alleen de onderste helft (om light attacks te ontwijken).
        if self.absorbed_by_id is not None:
            return pygame.Rect(-10000, -10000, 0, 0)
        if self.is_crouching:
            crouch_height = self.height // 2
            return pygame.Rect(self.x, self.y + crouch_height, self.width, crouch_height)
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def _load_sprites(self):
        global _shared_sprites
        if _shared_sprites is None:
            from systems.animation import AnimationSystem
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sprites_path = os.path.join(root_dir, "assets", "sprites")
            anim_sys = AnimationSystem(sprites_path)
            raw = anim_sys.load_character_sprites("default")
            size = _SPRITE_RENDER_SIZE
            _shared_sprites = {
                anim_name: [pygame.transform.scale(f, (size, size)) for f in frames]
                for anim_name, frames in raw.items()
            }
        # Apply player-specific color tint and pre-cache both directions so we
        # never call transform.flip() in the hot draw path.
        tint = _PLAYER_TINT_COLORS[self.player_id % len(_PLAYER_TINT_COLORS)]
        outline_color = tuple(max(10, int(c * 0.35)) for c in tint)
        self.sprites = {}
        self.outline_sprites = {}
        for anim_name, frames in _shared_sprites.items():
            tinted = [_apply_tint(f, tint) for f in frames]
            flipped = [pygame.transform.flip(f, True, False) for f in tinted]
            self.sprites[anim_name] = {True: tinted, False: flipped}

            outlined = [_make_silhouette(f, outline_color) for f in frames]
            outlined_flipped = [pygame.transform.flip(f, True, False) for f in outlined]
            self.outline_sprites[anim_name] = {True: outlined, False: outlined_flipped}
        self.sprites_loaded = True

    def _get_current_sprite_frame(self):
        anim = self.sprites.get(self.state) or self.sprites.get("idle")
        if not anim:
            return None
        frames = anim[self.facing_right]
        return frames[self.animation_frame % len(frames)]

    def draw(self, screen, camera_offset=(0, 0), viewer_player_id=None):
        # Teken de character op het scherm.
        draw_x = self.x - camera_offset[0]
        draw_y = self.y - camera_offset[1]

        # Laad sprites bij eerste draw-aanroep
        if not self.sprites_loaded:
            self._load_sprites()

        # Invincibility blink: sla elke andere periode over
        if self.invincible > 0 and self.invincible % 10 < 5:
            return

        if self.absorbed_by_id is not None or self.invisible_timer > 0:
            return

        if self.sprites_loaded:
            frame = self._get_current_sprite_frame()
            if frame:
                size = _SPRITE_RENDER_SIZE
                anim_cfg = SPRITE_CONFIG.get("default", {}).get(self.state, {})
                raw_offset = anim_cfg.get("render_offset_x", 0)
                scale = size / anim_cfg.get("frame_width", 128)
                direction = 1 if self.facing_right else -1
                sprite_x = draw_x + (self.width - size) // 2 + int(raw_offset * scale * direction)
                sprite_y = draw_y + self.height - size

                # Outline: donkere silhouet in spelerkleur, 4 richtingen 2px verschoven
                outline_anim = self.outline_sprites.get(self.state) or self.outline_sprites.get("idle")
                if outline_anim:
                    outline_frame = outline_anim[self.facing_right][self.animation_frame % len(outline_anim[self.facing_right])]
                    for ox, oy in _OUTLINE_OFFSETS:
                        screen.blit(outline_frame, (sprite_x + ox, sprite_y + oy))

                screen.blit(frame, (sprite_x, sprite_y))
        else:
            pygame.draw.rect(screen, self.color, (draw_x, draw_y, self.width, self.height))
            indicator_x = draw_x + (self.width - 10) if self.facing_right else draw_x
            pygame.draw.rect(screen, Colors.WHITE, (indicator_x, draw_y + 10, 10, 10))

        if self.ultimate_preview_active and self.teleport_glow_color:
            glow_rect = pygame.Rect(draw_x - 10, draw_y - 10, self.width + 20, self.height + 20)
            glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            glow_surface.fill((*self.teleport_glow_color, 60))
            screen.blit(glow_surface, glow_rect.topleft)
            pygame.draw.rect(screen, self.teleport_glow_color, glow_rect, 3, border_radius=12)
            preview_rect = self._get_teleport_preview_rect(camera_offset)
            if preview_rect:
                pygame.draw.rect(screen, self.teleport_glow_color, preview_rect, 2, border_radius=10)
        elif (self.ultimate_cast_timer > 0 or self.parry_active_timer > 0) and self.teleport_glow_color:
            glow_rect = pygame.Rect(draw_x - 8, draw_y - 8, self.width + 16, self.height + 16)
            glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            glow_surface.fill((*self.teleport_glow_color, 70))
            screen.blit(glow_surface, glow_rect.topleft)
            pygame.draw.rect(screen, self.teleport_glow_color, glow_rect, 2, border_radius=12)

        if self.parry_active_timer > 0:
            bubble_cfg = ULTIMATE_SHOP_INDEX["parry_counter"]
            radius = max(bubble_cfg["counter_hitbox_width"], bubble_cfg["counter_hitbox_height"]) // 2
            center = (int(draw_x + (self.width / 2)), int(draw_y + (self.height / 2)))
            bubble_surface = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(bubble_surface, (*bubble_cfg["glow_color"], 45), (radius + 4, radius + 4), radius)
            pygame.draw.circle(bubble_surface, (*bubble_cfg["glow_color"], 170), (radius + 4, radius + 4), radius, 3)
            screen.blit(bubble_surface, (center[0] - radius - 4, center[1] - radius - 4))

        if self.active_attack and self.active_attack.name == "Parry Counter" and self.active_attack.is_active:
            bubble_color = ULTIMATE_SHOP_INDEX["parry_counter"]["glow_color"]
            hitbox = self.active_attack.hitbox
            bubble_surface = pygame.Surface((int(hitbox.width) + 8, int(hitbox.height) + 8), pygame.SRCALPHA)
            pygame.draw.ellipse(bubble_surface, (*bubble_color, 85), bubble_surface.get_rect())
            pygame.draw.ellipse(bubble_surface, (*bubble_color, 210), bubble_surface.get_rect(), 4)
            screen.blit(
                bubble_surface,
                (int(hitbox.x - camera_offset[0]) - 4, int(hitbox.y - camera_offset[1]) - 4),
            )

        # Teken de actieve hitbox (rood kader, voor debugging)
        if self.active_attack and self.active_attack.is_active:
            hitbox = self.active_attack.hitbox
            pygame.draw.rect(screen, (255, 0, 0, 128),
                             (hitbox.x - camera_offset[0],
                              hitbox.y - camera_offset[1],
                              hitbox.width, hitbox.height), 2)
        if self.active_ultimate_projectile and self.active_ultimate_projectile.is_active:
            hitbox = self.active_ultimate_projectile.hitbox
            pygame.draw.rect(screen, (255, 140, 0),
                             (hitbox.x - camera_offset[0],
                              hitbox.y - camera_offset[1],
                              hitbox.width, hitbox.height), 2)

    def get_state(self):
        # Zet de character-state om naar een dictionary (voor netwerkverzending).
        return {
            "x": self.x,
            "y": self.y,
            "vel_x": self.vel_x,
            "vel_y": self.vel_y,
            "damage_percent": self.damage_percent,
            "stocks": self.stocks,
            "facing_right": self.facing_right,
            "state": self.state,
            "animation_frame": self.animation_frame,
            "animation_timer": self.animation_timer,
            "jump_type": self.jump_type,
            "landing_timer": self.landing_timer,
            "on_ground": self.on_ground,
            "hitstun": self.hitstun,
            "invincible": self.invincible,
            "is_dashing": self.is_dashing,
            "dash_frames": self.dash_frames,
            "dash_cooldown_timer": self.dash_cooldown_timer,
            "jumps_remaining": self.jumps_remaining,
            "attack_cooldown": self.attack_cooldown,
            "attack_frame": self.attack_frame,
            "character_type": self.get_character_name(),
            "build_stats": dict(self.build_stats),
            "equipped_ultimate_id": self.equipped_ultimate_id,
            "ultimate_cooldown_timer": self.ultimate_cooldown_timer,
            "ultimate_preview_active": self.ultimate_preview_active,
            "ultimate_cast_timer": self.ultimate_cast_timer,
            "casting_ultimate_id": self.casting_ultimate_id,
            "pending_ultimate_id": self.pending_ultimate_id,
            "pending_ultimate_direction": self.pending_ultimate_direction,
            "invisible_timer": self.invisible_timer,
            "grabbed_target_id": self.grabbed_target_id,
            "grab_hold_timer": self.grab_hold_timer,
            "absorbed_by_id": self.absorbed_by_id,
            "parry_active_timer": self.parry_active_timer,
            "parry_recovery_timer": self.parry_recovery_timer,
            "active_attack": self.active_attack.to_dict() if self.active_attack else None,
            "active_ultimate_projectile": self.active_ultimate_projectile.to_dict() if self.active_ultimate_projectile else None,
        }

    def set_state(self, state):
        # Herstel de character-state vanuit een dictionary (ontvangen van netwerk).
        self.x = state["x"]
        self.y = state["y"]
        self.vel_x = state["vel_x"]
        self.vel_y = state["vel_y"]
        self.damage_percent = state["damage_percent"]
        self.stocks = state["stocks"]
        self.facing_right = state["facing_right"]
        self.state = state["state"]
        self.animation_frame = state.get("animation_frame", 0)
        self.animation_timer = state.get("animation_timer", 0)
        self.jump_type = state.get("jump_type", "stationary")
        self.landing_timer = state.get("landing_timer", 0)
        self._prev_state = self.state
        self.on_ground = state["on_ground"]
        self.prev_on_ground = self.on_ground
        self.hitstun = state["hitstun"]
        self.invincible = state["invincible"]
        self.is_dashing = state.get("is_dashing", False)
        self.dash_frames = state.get("dash_frames", 0)
        self.dash_cooldown_timer = state.get("dash_cooldown_timer", 0)
        self.jumps_remaining = state.get("jumps_remaining", self.max_jumps)
        self.attack_cooldown = state.get("attack_cooldown", 0)
        self.attack_frame = state.get("attack_frame", 0)
        self.set_build_stats(state.get("build_stats", {}))
        self.set_equipped_ultimate(state.get("equipped_ultimate_id"))
        self.ultimate_cooldown_timer = state.get("ultimate_cooldown_timer", 0)
        self.ultimate_preview_active = state.get("ultimate_preview_active", False)
        self.ultimate_cast_timer = state.get("ultimate_cast_timer", 0)
        self.casting_ultimate_id = state.get("casting_ultimate_id")
        self.pending_ultimate_id = state.get("pending_ultimate_id")
        self.pending_ultimate_direction = state.get("pending_ultimate_direction")
        self.invisible_timer = state.get("invisible_timer", 0)
        self.grabbed_target_id = state.get("grabbed_target_id")
        self.grab_hold_timer = state.get("grab_hold_timer", 0)
        self.absorbed_by_id = state.get("absorbed_by_id")
        self.parry_active_timer = state.get("parry_active_timer", 0)
        self.parry_recovery_timer = state.get("parry_recovery_timer", 0)
        self._grabbed_target_ref = None
        if self.pending_ultimate_id == "teleportation":
            self.teleport_glow_color = ULTIMATE_SHOP_INDEX["teleportation"].get("glow_color", Colors.CYAN)
        elif self.casting_ultimate_id == "fireball":
            self.teleport_glow_color = ULTIMATE_SHOP_INDEX["fireball"].get("glow_color", Colors.ORANGE)
        elif self.casting_ultimate_id == "invisibility":
            self.teleport_glow_color = ULTIMATE_SHOP_INDEX["invisibility"].get("glow_color", Colors.LIGHT_GRAY)
        elif self.casting_ultimate_id == "grab":
            self.teleport_glow_color = ULTIMATE_SHOP_INDEX["grab"].get("glow_color", Colors.GREEN)
        elif self.parry_active_timer > 0 or self.casting_ultimate_id == "parry_counter":
            self.teleport_glow_color = ULTIMATE_SHOP_INDEX["parry_counter"].get("glow_color", Colors.CYAN)
        else:
            self.teleport_glow_color = None

        attack_state = state.get("active_attack")
        if attack_state and attack_state.get("type") == "projectile":
            self.active_attack = Projectile.from_dict(attack_state)
        else:
            self.active_attack = Attack.from_dict(attack_state) if attack_state else None
        projectile_state = state.get("active_ultimate_projectile")
        self.active_ultimate_projectile = Projectile.from_dict(projectile_state) if projectile_state else None
        self.last_attacker_id = None
        self.last_attacker_timer = 0
        self.gameplay_events = []

    def _get_teleport_preview_rect(self, camera_offset):
        if not self.ultimate_preview_active or self.pending_ultimate_id != "teleportation":
            return None

        preview_x = self.x
        preview_y = self.y
        distance = ULTIMATE_SHOP_INDEX["teleportation"]["distance"]
        direction = self.pending_ultimate_direction or ("right" if self.facing_right else "left")

        if direction == "up":
            preview_y -= distance
        elif direction == "down":
            preview_y += distance
        elif direction == "left":
            preview_x -= distance
        else:
            preview_x += distance

        return pygame.Rect(
            int(preview_x - camera_offset[0]),
            int(preview_y - camera_offset[1]),
            self.width,
            self.height,
        )
