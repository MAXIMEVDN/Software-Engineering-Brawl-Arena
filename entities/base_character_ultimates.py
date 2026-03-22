import pygame

from config import Colors, SPRITE_CONFIG, ULTIMATE_SHOP_INDEX
from entities.attack import Attack, Projectile


class BaseCharacterUltimatesMixin:
    """Ability and ultimate logic shared by all characters."""

    def start_ultimate_preview(self, direction):
        """Start or update the teleport preview before the player confirms it."""
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
        """Clear any active teleport preview and its temporary state."""
        self.ultimate_preview_active = False
        self.pending_ultimate_id = None
        self.pending_ultimate_direction = None
        self.teleport_glow_color = None

    def activate_ultimate(self):
        """Begin the casting phase for non-teleport ultimates."""
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
        """Confirm and execute a teleport preview when possible."""
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
        """Advance the current ultimate cast and trigger its effect when ready."""
        if self.ultimate_cast_timer <= 0:
            return

        self.vel_x = 0
        self.vel_y = 0
        self.is_dashing = False
        self.dash_frames = 0
        self.ultimate_cast_timer -= 1

        fireball_cfg = ULTIMATE_SHOP_INDEX["fireball"]
        launch_at = fireball_cfg.get("launch_at_remaining_frames", 0)
        if self.casting_ultimate_id == "fireball" and self.ultimate_cast_timer == launch_at and self.active_ultimate_projectile is None:
            self._launch_fireball()
            self.ultimate_cooldown_timer = fireball_cfg["cooldown_frames"]

        if self.ultimate_cast_timer > 0:
            return

        if self.casting_ultimate_id == "invisibility":
            self._activate_invisibility()
        elif self.casting_ultimate_id == "grab":
            self._start_grab_attack()
        elif self.casting_ultimate_id == "parry_counter":
            self._start_parry_counter()

        self.casting_ultimate_id = None
        if not self.ultimate_preview_active and self.parry_active_timer <= 0:
            self.teleport_glow_color = None

    def _perform_teleportation(self):
        """Move the character in the chosen teleport direction and start VFX timers."""
        ultimate = ULTIMATE_SHOP_INDEX["teleportation"]
        distance = ultimate["distance"]
        direction = self.pending_ultimate_direction or ("right" if self.facing_right else "left")

        self.teleport_origin_x = self.x
        self.teleport_origin_y = self.y

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

        anim_cfg = SPRITE_CONFIG["default"].get("ultimate_teleport", {})
        speed = anim_cfg.get("animation_speed", 3)
        self.teleport_anim_timer = 15 * speed
        self.teleport_origin_timer = self.teleport_anim_timer

    def _launch_fireball(self):
        """Spawn the fireball projectile using current stat scaling."""
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
        """Start the invisibility duration timer."""
        self.invisible_timer = ULTIMATE_SHOP_INDEX["invisibility"]["duration_frames"]

    def end_invisibility(self, start_cooldown=False):
        """End invisibility and optionally start its cooldown."""
        was_invisible = self.invisible_timer > 0
        self.invisible_timer = 0
        if start_cooldown and was_invisible:
            self.ultimate_cooldown_timer = ULTIMATE_SHOP_INDEX["invisibility"]["cooldown_frames"]

    def _start_grab_attack(self):
        """Create the temporary grab hitbox after the cast completes."""
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
        """Arm the parry window for the configured duration."""
        ultimate = ULTIMATE_SHOP_INDEX["parry_counter"]
        self.parry_active_timer = ultimate["parry_frames"]
        self.parry_recovery_timer = 0
        self.state = "special"

    def try_parry_hit(self, attacker, attack):
        """Convert a successful parry into its counterattack state."""
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
        """Attach the target to this character until the grab is released."""
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
        """Keep the grabbed target attached until the hold ends."""
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
        """Throw the grabbed target and start the grab cooldown."""
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
        """Drop any stored grabbed-target reference without throwing it."""
        if self._grabbed_target_ref:
            self._grabbed_target_ref.absorbed_by_id = None
        self._grabbed_target_ref = None
        self.grabbed_target_id = None
        self.grab_hold_timer = 0

    def _update_ultimate_projectile(self):
        """Advance the active ultimate projectile and clear it when finished."""
        if not self.active_ultimate_projectile:
            return
        if not self.active_ultimate_projectile.update() or not self.active_ultimate_projectile.is_active:
            self.active_ultimate_projectile = None

    def _get_teleport_preview_rect(self, camera_offset):
        """Return the screen-space rect for the teleport preview ghost."""
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
