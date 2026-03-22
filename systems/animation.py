# Animation System - laadt sprite sheets en speelt animaties af.
#
# Als er geen sprite-bestanden gevonden worden, worden placeholder-
# rechthoeken gebruikt (zodat het spel altijd werkt).

import pygame
import os

from config import SPRITE_CONFIG


class AnimationSystem:
    """Load sprite frames and track per-player animation timers."""
    # Beheert het laden en afspelen van sprite-animaties.

    def __init__(self, sprites_path="assets/sprites"):
        self.sprites_path = sprites_path
        self.sprite_cache = {}      # Laad elke sprite slechts één keer
        self.animation_timers = {}  # player_id -> timer

    def load_character_sprites(self, character_name):
        """Load every configured animation strip for one character."""
        # Laad alle animatieframes voor een character.
        # Geeft een dictionary terug: animatienaam -> lijst van frames.
        if character_name in self.sprite_cache:
            return self.sprite_cache[character_name]

        sprites = {}
        config = SPRITE_CONFIG.get(character_name, SPRITE_CONFIG.get("default", {}))

        for anim_name, anim_config in config.items():
            folder = anim_config.get("folder", character_name)
            file_path = os.path.join(
                self.sprites_path,
                folder,
                anim_config.get("file", f"{anim_name}.png")
            )

            if os.path.exists(file_path):
                frames = self._load_sprite_sheet(
                    file_path,
                    anim_config["frames"],
                    anim_config["frame_width"],
                    anim_config["frame_height"]
                )
            else:
                # Geen bestand gevonden: gebruik placeholder-rechthoeken
                frames = self._create_placeholder_frames(
                    anim_config["frames"],
                    anim_config["frame_width"],
                    anim_config["frame_height"]
                )

            sprites[anim_name] = frames

        self.sprite_cache[character_name] = sprites
        return sprites

    def _load_sprite_sheet(self, path, num_frames, frame_width, frame_height):
        """Slice a sprite sheet into individual frame surfaces."""
        # Knip een sprite sheet op in losse frames.
        try:
            sheet = pygame.image.load(path).convert_alpha()
        except pygame.error:
            return self._create_placeholder_frames(num_frames, frame_width, frame_height)

        frames = []
        for i in range(num_frames):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), (i * frame_width, 0, frame_width, frame_height))
            frames.append(frame)

        return frames

    def _create_placeholder_frames(self, num_frames, width, height):
        """Create fallback placeholder frames when no sprite asset exists."""
        # Maak eenvoudige grijze rechthoeken als er geen sprite gevonden is.
        frames = []
        for i in range(num_frames):
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            shade = 100 + (i * 20) % 100
            pygame.draw.rect(surface, (shade, shade, shade, 200), (0, 0, width, height))
            pygame.draw.rect(surface, (200, 200, 200), (0, 0, width, height), 2)
            frames.append(surface)
        return frames

    def get_frame(self, character_name, animation_name, frame_index, facing_right=True):
        """Return one frame from an animation, flipped when facing left."""
        # Haal één animatieframe op voor een character.
        sprites = self.sprite_cache.get(character_name)
        if not sprites:
            sprites = self.load_character_sprites(character_name)

        animation = sprites.get(animation_name, sprites.get("idle"))
        if not animation:
            return None

        frame = animation[frame_index % len(animation)]

        # Spiegelen als de character naar links kijkt
        if not facing_right:
            frame = pygame.transform.flip(frame, True, False)

        return frame

    def update_animation(self, player_id, animation_name, animation_speed=5):
        """Advance and return the frame index for one player's animation."""
        # Update de animatietimer en geef de huidige frame-index terug.
        if player_id not in self.animation_timers:
            self.animation_timers[player_id] = 0

        self.animation_timers[player_id] += 1

        config = SPRITE_CONFIG.get("default", {}).get(animation_name, {})
        num_frames = config.get("frames", 4)
        speed = config.get("animation_speed", animation_speed)

        return (self.animation_timers[player_id] // speed) % num_frames

    def reset_animation(self, player_id):
        """Clear the stored animation timer for one player."""
        # Reset de animatietimer voor een speler.
        self.animation_timers[player_id] = 0
