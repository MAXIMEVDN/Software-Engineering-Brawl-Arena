import os

import pygame


_SPRITE_RENDER_SIZE = 192  # Pixels to render each sprite frame (square)
_shared_sprites = None     # Raw scaled frames, loaded once and shared per process
_fireball_frames = None    # Animated GIF frames for the fireball projectile

_NON_LOOPING_STATES = frozenset({
    "jump_stationary", "jump_moving", "double_jump",
    "landing", "landing_impact",
    "punch1", "kick", "special", "jump_strike",
    "crouch",
    "ultimate_fireball", "ultimate_teleport", "ultimate_wind_power",
    "ultimate_knockback", "ultimate_magic_shield",
})

_PLAYER_TINT_COLORS = [
    (255, 55, 55),
    (55, 55, 255),
    (55, 210, 55),
    (255, 215, 30),
]

_OUTLINE_OFFSETS = ((0, -2), (0, 2), (-2, 0), (2, 0))


def load_fireball_gif():
    """Load and cache the fireball projectile frames from the GIF asset."""
    global _fireball_frames
    if _fireball_frames is not None:
        return
    try:
        from PIL import Image
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "assets", "sprites", "attacks", "fireball_1.gif")
        gif = Image.open(path)
        frames = []
        for i in range(gif.n_frames):
            gif.seek(i)
            frame_rgba = gif.convert("RGBA")
            raw = frame_rgba.tobytes()
            surface = pygame.image.fromstring(raw, frame_rgba.size, "RGBA").convert_alpha()
            frames.append(surface)
        _fireball_frames = frames
    except Exception:
        _fireball_frames = []


def get_fireball_frames():
    """Return the cached fireball frames, loading them on first use."""
    load_fireball_gif()
    return _fireball_frames or []


def apply_tint(surface, tint_color):
    """Tint a sprite toward the player's color while keeping shading visible."""
    tinted = surface.copy()
    tinted.fill(tint_color, special_flags=pygame.BLEND_MULT)
    tinted.fill((55, 55, 55), special_flags=pygame.BLEND_ADD)
    return tinted


def make_silhouette(surface, outline_color):
    """Create a solid silhouette version of a sprite for outline rendering."""
    sil = surface.copy()
    sil.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MIN)
    sil.fill((*outline_color, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return sil
