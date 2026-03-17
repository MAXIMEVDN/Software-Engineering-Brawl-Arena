# Base Character - de basisklasse voor alle speelbare characters.
#
# Warrior, Mage en Ninja erven allemaal van deze class.
# Ze overschrijven de drie attack-methodes met hun eigen aanvallen.

import math
import pygame

from config import (
    CharacterStats, Colors, GRAVITY, MAX_FALL_SPEED,
    GROUND_FRICTION, AIR_FRICTION, KILL_BOUNDARY, CONTROLS
)
from entities.attack import Attack


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

        # Animatiestatus
        self.state = "idle"
        self.animation_frame = 0
        self.animation_timer = 0

        # Actieve aanval
        self.active_attack = None
        self.attack_frame = 0

        # Kleur (voor het tekenen)
        self.color = Colors.PLAYER_COLORS[player_id % len(Colors.PLAYER_COLORS)]
        self.sprites = {}
        self.sprites_loaded = False

        # Build-stats voor de pre-game verdeling.
        self.build_stats = {
            "power": 0,
            "defense": 0,
            "mobility": 0,
            "knockback": 0,
            "range": 0,
        }

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

        if self.hitstun <= 0:
            self._apply_gravity()
            self._apply_friction()

        self.x += self.vel_x * dt
        self.y += self.vel_y * dt

        self._handle_platform_collision(platforms)
        self._check_boundaries()

        if self.active_attack:
            self._update_attack()

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

        # Stop bij een hele kleine snelheid
        if abs(self.vel_x) < 0.1:
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
        if self.is_dashing:
            self.dash_frames -= 1
            if self.dash_frames <= 0:
                self.is_dashing = False

    def _handle_platform_collision(self, platforms):
        # Controleer of de character op een platform landt.
        self.on_ground = False

        for platform in platforms:
            if self._collides_with_platform(platform):
                if self.vel_y > 0:
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
        # Verwerk ingedrukte toetsen (voor beweging links/rechts).
        if self.hitstun > 0:
            return None

        if not self.active_attack:
            if any(keys[k] for k in CONTROLS["left"]):
                self.move_left()
            elif any(keys[k] for k in CONTROLS["right"]):
                self.move_right()

        return None

    def handle_key_down(self, key):
        # Verwerk één toetsdruk (springen, dash, aanval).
        if self.hitstun > 0:
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

    def apply_input_state(self, input_state):
        # Verwerk input vanuit de server (netwerkmodus).
        if self.hitstun > 0:
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
            if self.on_ground:
                self.vel_y = self.jump_power
            else:
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
        if self.active_attack or self.attack_cooldown > 0:
            return None

        # Roep de juiste methode aan — dit is polymorfisme in actie!
        if attack_type == "light":
            self.active_attack = self.light_attack()
            self.state = "punch1"
        elif attack_type == "heavy":
            self.active_attack = self.heavy_attack()
            self.state = "kick"
        elif attack_type == "special":
            self.active_attack = self.special_attack()
            self.state = "special"
        else:
            return None

        self.attack_frame = 0
        return self.active_attack

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
            self.active_attack = None
            self.attack_cooldown = CharacterStats.ATTACK_COOLDOWN

    def take_damage(self, damage, knockback_base, knockback_scaling, angle, attacker_x):
        # Ontvang schade: verhoog damage% en vlieg weg (knockback).
        if self.invincible > 0:
            return

        self.damage_percent += damage

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

    def die(self):
        # Verlies een leven en respawn als er nog levens over zijn.
        if self.stocks < 0:
            self.respawn()
            return

        self.stocks -= 1
        if self.stocks > 0:
            self.respawn()

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
        self.jumps_remaining = self.max_jumps

    def _update_animation_state(self):
        # Bepaal welke animatie afgespeeld wordt op basis van wat de character doet.
        if self.active_attack:
            return  # Aanvalsanimatie heeft prioriteit

        if self.hitstun > 0:
            self.state = "hurt"
        elif self.is_dashing:
            self.state = "dash"
        elif not self.on_ground:
            if self.vel_y < 0:
                self.state = "jump"
            else:
                self.state = "fall"
        elif abs(self.vel_x) > 0.5:
            self.state = "run"
        else:
            self.state = "idle"

    def get_rect(self):
        # Geef de collision-rechthoek van de character terug.
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, screen, camera_offset=(0, 0)):
        # Teken de character op het scherm.
        draw_x = self.x - camera_offset[0]
        draw_y = self.y - camera_offset[1]

        # Flash wit tijdens onkwetsbaarheidsframes
        color = self.color
        if self.invincible > 0 and self.invincible % 10 < 5:
            color = Colors.WHITE

        if not self.sprites_loaded:
            pygame.draw.rect(screen, color, (draw_x, draw_y, self.width, self.height))

            # Kleine witte blok toont welke kant de character op kijkt
            indicator_x = draw_x + (self.width - 10) if self.facing_right else draw_x
            pygame.draw.rect(screen, Colors.WHITE, (indicator_x, draw_y + 10, 10, 10))

        # Teken de actieve hitbox (rood kader, voor debugging)
        if self.active_attack and self.active_attack.is_active:
            hitbox = self.active_attack.hitbox
            pygame.draw.rect(screen, (255, 0, 0, 128),
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
            "active_attack": self.active_attack.to_dict() if self.active_attack else None,
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
        self.on_ground = state["on_ground"]
        self.hitstun = state["hitstun"]
        self.invincible = state["invincible"]
        self.is_dashing = state.get("is_dashing", False)
        self.dash_frames = state.get("dash_frames", 0)
        self.dash_cooldown_timer = state.get("dash_cooldown_timer", 0)
        self.jumps_remaining = state.get("jumps_remaining", self.max_jumps)
        self.attack_cooldown = state.get("attack_cooldown", 0)
        self.attack_frame = state.get("attack_frame", 0)
        self.set_build_stats(state.get("build_stats", {}))

        attack_state = state.get("active_attack")
        self.active_attack = Attack.from_dict(attack_state) if attack_state else None
