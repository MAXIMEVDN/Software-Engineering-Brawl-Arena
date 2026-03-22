from config import Colors, ULTIMATE_SHOP_INDEX
from entities.attack import Attack, Projectile


class BaseCharacterStateMixin:
    """Serialize and restore character state for multiplayer sync."""

    def get_state(self):
        """Convert the runtime state into a plain dictionary."""
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
            "teleport_anim_timer": self.teleport_anim_timer,
            "teleport_origin_x": self.teleport_origin_x,
            "teleport_origin_y": self.teleport_origin_y,
            "teleport_origin_timer": self.teleport_origin_timer,
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
        """Restore a dictionary produced by get_state()."""
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
        self.teleport_anim_timer = state.get("teleport_anim_timer", 0)
        self.teleport_origin_x = state.get("teleport_origin_x", 0)
        self.teleport_origin_y = state.get("teleport_origin_y", 0)
        self.teleport_origin_timer = state.get("teleport_origin_timer", 0)
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
