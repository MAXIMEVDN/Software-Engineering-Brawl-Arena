# Base Character - de basisklasse voor alle speelbare characters.
#
# Warrior erft van deze class en vult de drie attack-methodes zelf in.

import math

import pygame

from config import (
    AIR_FRICTION,
    CharacterStats,
    Colors,
    CONTROLS,
    GROUND_FRICTION,
    GRAVITY,
    KILL_BOUNDARY,
    MAX_FALL_SPEED,
    ULTIMATE_SHOP_INDEX,
)
from entities.attack import Attack
from entities.base_character_rendering import BaseCharacterRenderingMixin
from entities.base_character_state import BaseCharacterStateMixin
from entities.base_character_ultimates import BaseCharacterUltimatesMixin


class BaseCharacter(BaseCharacterUltimatesMixin, BaseCharacterRenderingMixin, BaseCharacterStateMixin):
    """Shared base class for all playable characters.

    The subclass only provides the actual attacks and display name.
    This class handles movement, damage, cooldowns and general state.
    """

    def __init__(self, x, y, player_id):
        self.x = x
        self.y = y
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.player_id = player_id

        self.width = CharacterStats.WIDTH
        self.height = CharacterStats.HEIGHT
        self.respawn_position = (x, y)

        self.walk_speed = CharacterStats.WALK_SPEED
        self.run_speed = CharacterStats.RUN_SPEED
        self.jump_power = CharacterStats.JUMP_POWER
        self.double_jump_power = CharacterStats.DOUBLE_JUMP_POWER
        self.max_jumps = CharacterStats.MAX_JUMPS
        self.dash_speed = CharacterStats.DASH_SPEED
        self.dash_duration = CharacterStats.DASH_DURATION
        self.dash_cooldown = CharacterStats.DASH_COOLDOWN

        self.damage_percent = 0.0
        self.stocks = 3
        self.attack_cooldown = 0
        self.hitstun = 0
        self.invincible = 0

        self.on_ground = False
        self.jumps_remaining = self.max_jumps
        self.facing_right = True
        self.is_dashing = False
        self.dash_frames = 0
        self.dash_cooldown_timer = 0
        self.is_crouching = False

        self.state = "idle"
        self.animation_frame = 0
        self.animation_timer = 0
        self.jump_type = "stationary"
        self.prev_on_ground = False
        self.landing_timer = 0

        self.active_attack = None
        self.attack_frame = 0
        self.last_attacker_id = None
        self.last_attacker_timer = 0
        self.gameplay_events = []

        self.color = Colors.PLAYER_COLORS[player_id % len(Colors.PLAYER_COLORS)]
        self.sprites = {}
        self.outline_sprites = {}
        self.sprites_loaded = False
        self._prev_state = "idle"

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
        self.teleport_anim_timer = 0
        self.teleport_origin_x = 0
        self.teleport_origin_y = 0
        self.teleport_origin_timer = 0
        self.active_ultimate_projectile = None
        self.invisible_timer = 0
        self.grabbed_target_id = None
        self.grab_hold_timer = 0
        self.absorbed_by_id = None
        self._grabbed_target_ref = None
        self.parry_active_timer = 0
        self.parry_recovery_timer = 0

    def light_attack(self):
        """Return the subclass-specific light attack."""
        raise NotImplementedError("Subclass moet light_attack() implementeren")

    def heavy_attack(self):
        """Return the subclass-specific heavy attack."""
        raise NotImplementedError("Subclass moet heavy_attack() implementeren")

    def special_attack(self):
        """Return the subclass-specific special attack."""
        raise NotImplementedError("Subclass moet special_attack() implementeren")

    def get_character_name(self):
        """Return the subclass-specific character display name."""
        raise NotImplementedError("Subclass moet get_character_name() implementeren")

    def set_build_stats(self, stats):
        """Store the chosen build stats and immediately apply their bonuses."""
        for stat_name in self.build_stats:
            self.build_stats[stat_name] = max(0, int(stats.get(stat_name, self.build_stats[stat_name])))
        self._apply_build_modifiers()

    def set_equipped_ultimate(self, ultimate_id):
        """Equip a valid ultimate id and clear stale previews when it changes."""
        self.equipped_ultimate_id = ultimate_id if ultimate_id in ULTIMATE_SHOP_INDEX else None
        if self.pending_ultimate_id != self.equipped_ultimate_id:
            self.cancel_ultimate_preview()

    def _apply_build_modifiers(self):
        """Translate build points into movement-related values."""
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
        """Scale base damage with the current power stat."""
        return damage + (0.8 * self.build_stats["power"])

    def _scale_knockback(self, knockback_base, knockback_scaling):
        """Scale knockback values with the current knockback stat."""
        knockback_points = self.build_stats["knockback"]
        base_bonus = 0.6 * knockback_points
        scaling_bonus = 0.015 * knockback_points
        return knockback_base + base_bonus, knockback_scaling + scaling_bonus

    def _scale_attack_range(self, hitbox_width, hitbox_height, hitbox_offset_x, hitbox_offset_y):
        """Scale hitbox size and offset with the current range stat."""
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
        """Create an Attack after applying the current build modifiers."""
        scaled_knockback_base, scaled_knockback_scaling = self._scale_knockback(knockback_base, knockback_scaling)
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
        """Advance the character by one frame.

        This updates timers first, then movement/physics, then active combat state.
        """
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
            if self.active_ultimate_projectile:
                self._update_ultimate_projectile()
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
        """Apply gravity unless the character is grounded or dashing."""
        if not self.on_ground and not self.is_dashing:
            self.vel_y += GRAVITY
            if self.vel_y > MAX_FALL_SPEED:
                self.vel_y = MAX_FALL_SPEED

    def _apply_friction(self):
        """Reduce horizontal speed using ground or air friction."""
        if self.is_dashing:
            return
        self.vel_x *= GROUND_FRICTION if self.on_ground else AIR_FRICTION
        if abs(self.vel_x) < 0.5:
            self.vel_x = 0

    def _update_timers(self):
        """Tick down the frame-based timers used by movement and abilities."""
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
        if self.teleport_anim_timer > 0:
            self.teleport_anim_timer -= 1
        if self.teleport_origin_timer > 0:
            self.teleport_origin_timer -= 1
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
        """Land on any platform top crossed during this frame."""
        self.on_ground = False
        for platform in platforms:
            if self._collides_with_platform(platform) and self.vel_y >= 0:
                self.y = platform.y - self.height
                self.vel_y = 0
                self.on_ground = True
                self.jumps_remaining = self.max_jumps

    def _collides_with_platform(self, platform):
        """Return whether the character crosses the top of a platform."""
        char_bottom = self.y + self.height
        char_prev_bottom = char_bottom - self.vel_y
        return (
            self.x + self.width > platform.x
            and self.x < platform.x + platform.width
            and char_prev_bottom <= platform.y
            and char_bottom >= platform.y
        )

    def _check_boundaries(self):
        """Kill the character if it leaves the arena bounds."""
        if (
            self.x < KILL_BOUNDARY["left"]
            or self.x > KILL_BOUNDARY["right"]
            or self.y < KILL_BOUNDARY["top"]
            or self.y > KILL_BOUNDARY["bottom"]
        ):
            self.die()

    def handle_input(self, keys):
        """Handle held movement keys for the local player."""
        if self.hitstun > 0 or self.ultimate_cast_timer > 0 or self.absorbed_by_id is not None or self.parry_active_timer > 0 or self.parry_recovery_timer > 0:
            return None

        self.is_crouching = self.on_ground and any(keys[k] for k in CONTROLS["down"])
        if self.ultimate_preview_active:
            self.pending_ultimate_direction = self._get_direction_from_keys(keys)

        if not self.active_attack and not self.is_crouching:
            if any(keys[k] for k in CONTROLS["left"]):
                self.move_left()
            elif any(keys[k] for k in CONTROLS["right"]):
                self.move_right()
        return None

    def handle_key_down(self, key):
        """Handle one key press for jumps, attacks and ultimates."""
        if self.hitstun > 0 or self.absorbed_by_id is not None or self.parry_active_timer > 0 or self.parry_recovery_timer > 0:
            return None

        if key in CONTROLS["ultimate_ability"]:
            if self.equipped_ultimate_id == "teleportation":
                return self.start_ultimate_preview(self._get_direction_from_keys(pygame.key.get_pressed()))
            return self.activate_ultimate()

        if self.ultimate_preview_active or self.ultimate_cast_timer > 0:
            return None

        if key in CONTROLS["jump"]:
            self.jump()
        if key in CONTROLS["dash"]:
            self.dash()

        if self.attack_cooldown <= 0 and not self.active_attack:
            if key in CONTROLS["light_attack"]:
                return self.start_attack("light")
            if key in CONTROLS["heavy_attack"]:
                return self.start_attack("heavy")
            if key in CONTROLS["special_attack"]:
                return self.start_attack("special")
        return None

    def handle_key_up(self, key):
        """Handle key releases that should end held ultimate inputs."""
        if key in CONTROLS["ultimate_ability"]:
            return self.release_ultimate()
        return None

    def apply_input_state(self, input_state):
        """Apply a network input snapshot from the server/client sync."""
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
        """Start moving left at walk speed when free to do so."""
        if not self.is_dashing and not self.active_attack:
            self.vel_x = -self.walk_speed
            self.facing_right = False

    def move_right(self):
        """Start moving right at walk speed when free to do so."""
        if not self.is_dashing and not self.active_attack:
            self.vel_x = self.walk_speed
            self.facing_right = True

    def jump(self):
        """Consume one jump and apply the correct jump force."""
        if self.jumps_remaining > 0 and not self.active_attack:
            if self.on_ground or self.jumps_remaining == self.max_jumps:
                self.jump_type = "moving" if abs(self.vel_x) > 0.5 else "stationary"
                self.vel_y = self.jump_power
            else:
                self.jump_type = "double"
                self.vel_y = self.double_jump_power
            self.jumps_remaining -= 1
            self.on_ground = False

    def dash(self):
        """Trigger a short horizontal dash if it is off cooldown."""
        if self.dash_cooldown_timer <= 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_frames = self.dash_duration
            self.dash_cooldown_timer = self.dash_cooldown
            direction = 1 if self.facing_right else -1
            self.vel_x = self.dash_speed * direction
            self.vel_y = 0

    def start_attack(self, attack_type):
        """Start one of the character's three normal attack types."""
        if (
            self.active_attack
            or self.attack_cooldown > 0
            or self.ultimate_preview_active
            or self.ultimate_cast_timer > 0
            or self.grabbed_target_id is not None
            or self.absorbed_by_id is not None
        ):
            return None

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
        """Resolve held local keys into a simple direction label."""
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
        """Resolve a synced input snapshot into a simple direction label."""
        if input_state.get("up"):
            return "up"
        if input_state.get("down"):
            return "down"
        if input_state.get("left"):
            return "left"
        if input_state.get("right"):
            return "right"
        return "right" if self.facing_right else "left"

    def _update_attack(self):
        """Move the current attack through startup, active and recovery frames."""
        if not self.active_attack:
            return

        self.attack_frame += 1
        total_frames = (
            self.active_attack.startup_frames
            + self.active_attack.active_frames
            + self.active_attack.recovery_frames
        )
        self.active_attack.update_position(self.x, self.y, self.facing_right, self.width)

        if self.attack_frame < self.active_attack.startup_frames:
            self.active_attack.is_active = False
        elif self.attack_frame < (self.active_attack.startup_frames + self.active_attack.active_frames):
            self.active_attack.is_active = True
        else:
            self.active_attack.is_active = False

        if self.attack_frame >= total_frames:
            if self.active_attack.effect_type == "grab":
                self.ultimate_cooldown_timer = ULTIMATE_SHOP_INDEX["grab"]["cooldown_frames"]
            self.active_attack = None
            self.attack_cooldown = CharacterStats.ATTACK_COOLDOWN

    def take_damage(self, damage, knockback_base, knockback_scaling, angle, attacker_x, attacker_id=None):
        """Apply damage and convert it into knockback and hitstun."""
        if self.invincible > 0:
            return

        self.damage_percent += damage
        if attacker_id is not None and attacker_id != self.player_id:
            self.last_attacker_id = attacker_id
            self.last_attacker_timer = 300

        defense_multiplier = max(0.55, 1.0 - (0.06 * self.build_stats["defense"]))
        knockback = (knockback_base + (self.damage_percent * knockback_scaling)) * defense_multiplier

        angle_rad = math.radians(angle)
        direction = -1 if attacker_x > self.x else 1
        self.vel_x = knockback * math.cos(angle_rad) * direction
        self.vel_y = -knockback * math.sin(angle_rad)

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
        """Consume a stock, emit a death event and respawn when possible."""
        killer_id = self.last_attacker_id if self.last_attacker_id != self.player_id else None
        self.gameplay_events.append({"type": "death", "player_id": self.player_id, "killer_id": killer_id})

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
        """Reset the character after losing a stock."""
        self.x, self.y = self.respawn_position
        self.vel_x = 0
        self.vel_y = 0
        self.damage_percent = 0
        self.hitstun = 0
        self.invincible = 120
        self.active_attack = None
        self.active_ultimate_projectile = None
        self._clear_grabbed_target()
        self.jumps_remaining = self.max_jumps
        self.last_attacker_id = None
        self.last_attacker_timer = 0
        self.jump_type = "stationary"
        self.landing_timer = 0
        self.on_ground = False
        self.prev_on_ground = False
        self.cancel_ultimate_preview()
        self.ultimate_cast_timer = 0
        self.casting_ultimate_id = None
        self.teleport_glow_color = None
        self.invisible_timer = 0
        self.absorbed_by_id = None
        self.parry_active_timer = 0
        self.parry_recovery_timer = 0

    def set_respawn_position(self, x, y):
        """Store the position used for future respawns."""
        self.respawn_position = (x, y)

    def consume_gameplay_events(self):
        """Return and clear queued gameplay events such as kills or deaths."""
        events = list(self.gameplay_events)
        self.gameplay_events.clear()
        return events

    def get_rect(self):
        """Return the current hurtbox rect, adjusted for crouch and grab states."""
        if self.absorbed_by_id is not None:
            return pygame.Rect(-10000, -10000, 0, 0)
        if self.is_crouching:
            crouch_height = self.height // 2
            return pygame.Rect(self.x, self.y + crouch_height, self.width, crouch_height)
        return pygame.Rect(self.x, self.y, self.width, self.height)
