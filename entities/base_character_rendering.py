import os

import pygame

from config import Colors, SPRITE_CONFIG, STAT_POINT_BUDGET, ULTIMATE_SHOP_INDEX
from entities.base_character_shared import (
    _NON_LOOPING_STATES,
    _OUTLINE_OFFSETS,
    _PLAYER_TINT_COLORS,
    _SPRITE_RENDER_SIZE,
    apply_tint,
    get_fireball_frames,
    make_silhouette,
)
import entities.base_character_shared as shared


class BaseCharacterRenderingMixin:
    """Animation and drawing helpers for BaseCharacter."""

    def _update_animation_state(self):
        """Choose the current animation based on movement and combat state."""
        if self.absorbed_by_id is not None:
            self.state = "idle"
        elif self.ultimate_cast_timer > 0 or self.parry_active_timer > 0:
            uid = self.casting_ultimate_id
            if uid == "fireball":
                self.state = "ultimate_fireball"
            elif uid == "invisibility":
                self.state = "ultimate_wind_power"
            elif uid == "grab":
                self.state = "ultimate_knockback"
            else:
                self.state = "ultimate_magic_shield"
        elif self.teleport_anim_timer > 0:
            self.state = "ultimate_teleport"
        elif not self.active_attack:
            just_landed = self.on_ground and not self.prev_on_ground

            if self.hitstun > 0:
                if not self.on_ground:
                    self.state = "hurt"
                elif just_landed and self.state == "hurt":
                    self.state = "landing_impact"
                    self.landing_timer = 0
                elif self.state == "landing_impact":
                    cfg = SPRITE_CONFIG["default"].get("landing_impact", {})
                    total = cfg.get("frames", 13) * cfg.get("animation_speed", 3)
                    if self.landing_timer >= total:
                        self.state = "idle"
                    else:
                        self.landing_timer += 1
            elif self.state == "landing_impact":
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
                if self.jump_type == "double":
                    self.state = "double_jump"
                elif self.jump_type == "moving":
                    self.state = "jump_moving"
                else:
                    self.state = "jump_stationary"
            else:
                if just_landed and self.state in ("jump_stationary", "jump_moving", "double_jump", "jump_strike"):
                    self.state = "landing"
                    self.landing_timer = 0
                    self.jump_type = "stationary"
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

        if self.state != self._prev_state:
            self.animation_timer = 0
            self._prev_state = self.state
        else:
            self.animation_timer += 1

        config = SPRITE_CONFIG.get("default", {}).get(self.state, {})
        num_frames = config.get("frames", 4)
        speed = config.get("animation_speed", 5)

        if self.state in _NON_LOOPING_STATES:
            penultimate_hold = config.get("penultimate_hold", 0)
            if penultimate_hold > 0 and num_frames >= 2:
                normal_time = (num_frames - 2) * speed
                penultimate_time = speed + penultimate_hold
                if self.animation_timer < normal_time:
                    self.animation_frame = self.animation_timer // speed
                elif self.animation_timer < normal_time + penultimate_time:
                    self.animation_frame = num_frames - 2
                else:
                    self.animation_frame = num_frames - 1
            else:
                self.animation_frame = min(self.animation_timer // speed, num_frames - 1)
        else:
            self.animation_frame = (self.animation_timer // speed) % num_frames

    def _load_sprites(self):
        """Load shared sprite sheets once, then cache tinted copies per player."""
        if shared._shared_sprites is None:
            from systems.animation import AnimationSystem
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sprites_path = os.path.join(root_dir, "assets", "sprites")
            anim_sys = AnimationSystem(sprites_path)
            raw = anim_sys.load_character_sprites("default")
            size = _SPRITE_RENDER_SIZE
            shared._shared_sprites = {
                anim_name: [pygame.transform.scale(f, (size, size)) for f in frames]
                for anim_name, frames in raw.items()
            }

        tint = _PLAYER_TINT_COLORS[self.player_id % len(_PLAYER_TINT_COLORS)]
        outline_color = tuple(max(10, int(c * 0.35)) for c in tint)
        self.sprites = {}
        self.outline_sprites = {}
        for anim_name, frames in shared._shared_sprites.items():
            tinted = [apply_tint(f, tint) for f in frames]
            flipped = [pygame.transform.flip(f, True, False) for f in tinted]
            self.sprites[anim_name] = {True: tinted, False: flipped}

            outlined = [make_silhouette(f, outline_color) for f in frames]
            outlined_flipped = [pygame.transform.flip(f, True, False) for f in outlined]
            self.outline_sprites[anim_name] = {True: outlined, False: outlined_flipped}
        self.sprites_loaded = True

    def _get_current_sprite_frame(self):
        """Return the current sprite frame for the active animation state."""
        anim = self.sprites.get(self.state) or self.sprites.get("idle")
        if not anim:
            return None
        frames = anim[self.facing_right]
        return frames[self.animation_frame % len(frames)]

    def draw(self, screen, camera_offset=(0, 0), viewer_player_id=None):
        """Draw the character, its preview markers and active projectile."""
        draw_x = self.x - camera_offset[0]
        draw_y = self.y - camera_offset[1]

        if not self.sprites_loaded:
            self._load_sprites()

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
                raw_offset_y = anim_cfg.get("render_offset_y", 0)
                scale = size / anim_cfg.get("frame_width", 128)
                direction = 1 if self.facing_right else -1
                sprite_x = draw_x + (self.width - size) // 2 + int(raw_offset * scale * direction)
                sprite_y = draw_y + self.height - size + int(raw_offset_y * scale)

                outline_anim = self.outline_sprites.get(self.state) or self.outline_sprites.get("idle")
                if outline_anim:
                    outline_frame = outline_anim[self.facing_right][self.animation_frame % len(outline_anim[self.facing_right])]
                    for ox, oy in _OUTLINE_OFFSETS:
                        screen.blit(outline_frame, (sprite_x + ox, sprite_y + oy))

                screen.blit(frame, (sprite_x, sprite_y))

                if self.teleport_origin_timer > 0:
                    origin_sx = self.teleport_origin_x - camera_offset[0] + (self.width - size) // 2 + int(raw_offset * scale * direction)
                    origin_sy = self.teleport_origin_y - camera_offset[1] + self.height - size + int(raw_offset_y * scale)
                    alpha = int(255 * self.teleport_origin_timer / max(self.teleport_anim_timer, 1))
                    ghost = frame.copy()
                    ghost.set_alpha(alpha)
                    screen.blit(ghost, (origin_sx, origin_sy))
        else:
            pygame.draw.rect(screen, self.color, (draw_x, draw_y, self.width, self.height))
            indicator_x = draw_x + (self.width - 10) if self.facing_right else draw_x
            pygame.draw.rect(screen, Colors.WHITE, (indicator_x, draw_y + 10, 10, 10))

        if self.ultimate_preview_active and self.teleport_glow_color:
            preview_rect = self._get_teleport_preview_rect(camera_offset)
            if preview_rect:
                pygame.draw.rect(screen, self.teleport_glow_color, preview_rect, 2, border_radius=10)
        elif (self.parry_active_timer > 0 or self.casting_ultimate_id == "parry_counter") and self.teleport_glow_color:
            glow_rect = pygame.Rect(draw_x - 8, draw_y - 8, self.width + 16, self.height + 16)
            glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            glow_surface.fill((*self.teleport_glow_color, 70))
            screen.blit(glow_surface, glow_rect.topleft)
            pygame.draw.rect(screen, self.teleport_glow_color, glow_rect, 2, border_radius=12)

        if self.active_attack and self.active_attack.is_active:
            hitbox = self.active_attack.hitbox
            pygame.draw.rect(
                screen,
                (255, 0, 0, 128),
                (hitbox.x - camera_offset[0], hitbox.y - camera_offset[1], hitbox.width, hitbox.height),
                2,
            )
        if self.active_ultimate_projectile and self.active_ultimate_projectile.is_active:
            hitbox = self.active_ultimate_projectile.hitbox
            fireball_frames = get_fireball_frames()
            if fireball_frames:
                proj = self.active_ultimate_projectile
                elapsed = ULTIMATE_SHOP_INDEX["fireball"]["projectile_lifetime"] - proj.lifetime
                frame_idx = (elapsed // 4) % len(fireball_frames)
                gif_frame = fireball_frames[frame_idx]
                size = max(hitbox.width, hitbox.height) * 2
                scaled = pygame.transform.scale(gif_frame, (size, size))
                if not self.active_ultimate_projectile.vel_x > 0:
                    scaled = pygame.transform.flip(scaled, True, False)
                draw_rect = scaled.get_rect(center=(
                    int(hitbox.x + hitbox.width / 2 - camera_offset[0]),
                    int(hitbox.y + hitbox.height / 2 - camera_offset[1]),
                ))
                screen.blit(scaled, draw_rect)
            else:
                pygame.draw.rect(
                    screen,
                    (255, 140, 0),
                    (hitbox.x - camera_offset[0], hitbox.y - camera_offset[1], hitbox.width, hitbox.height),
                    2,
                )
