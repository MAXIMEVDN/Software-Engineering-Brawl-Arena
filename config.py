# Configuratie - alle instellingen voor de game.

SERVER_IP = "172.20.208.1"
SERVER_PORT = 5555
MAX_PLAYERS = 4

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GAME_TITLE = "Brawl Arena"


class Colors:
    # Alle kleuren die in de game gebruikt worden (RGB).

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (255, 50, 50)
    GREEN = (50, 255, 50)
    BLUE = (50, 100, 255)
    YELLOW = (255, 255, 50)
    ORANGE = (255, 165, 0)
    PURPLE = (150, 50, 255)
    CYAN = (50, 255, 255)
    GRAY = (128, 128, 128)
    DARK_GRAY = (64, 64, 64)
    LIGHT_GRAY = (192, 192, 192)
    
    # Player colors
    PLAYER_COLORS = [
        (255, 100, 100),  # Player 1 - Rood
        (100, 100, 255),  # Player 2 - Blauw
        (100, 255, 100),  # Player 3 - Groen
        (255, 255, 100),  # Player 4 - Geel
    ]
    
    # Background
    BG_COLOR = (40, 44, 52)
    PLATFORM_COLOR = (80, 85, 95)


GRAVITY = 0.6
MAX_FALL_SPEED = 15
GROUND_FRICTION = 0.85
AIR_FRICTION = 0.95


class CharacterStats:
    # Standaard stats voor alle characters. Subclasses kunnen deze overschrijven.

    # Movement
    WALK_SPEED = 5
    RUN_SPEED = 8
    JUMP_POWER = -14
    DOUBLE_JUMP_POWER = -12
    MAX_JUMPS = 2
    DASH_SPEED = 15
    DASH_DURATION = 8  # frames
    DASH_COOLDOWN = 30  # frames
    
    # Combat
    MAX_HEALTH = 100
    ATTACK_COOLDOWN = 20  # frames
    
    # Hitbox
    WIDTH = 48
    HEIGHT = 64


class AttackData:
    # Standaard aanvalswaarden per type (light, heavy, special).

    LIGHT = {
        "damage": 8,
        "knockback_base": 3,
        "knockback_scaling": 0.08,
        "startup_frames": 3,
        "active_frames": 4,
        "recovery_frames": 8,
        "range": 50,
        "width": 40,
        "height": 30,
    }
    
    HEAVY = {
        "damage": 15,
        "knockback_base": 6,
        "knockback_scaling": 0.12,
        "startup_frames": 8,
        "active_frames": 5,
        "recovery_frames": 15,
        "range": 60,
        "width": 50,
        "height": 40,
    }
    
    SPECIAL = {
        "damage": 12,
        "knockback_base": 5,
        "knockback_scaling": 0.1,
        "startup_frames": 5,
        "active_frames": 6,
        "recovery_frames": 12,
        "range": 70,
        "width": 45,
        "height": 35,
    }


# Platforms: (x, y, width, height)
STAGE_PLATFORMS = [
    # Main platform (ground)
    (240, 550, 800, 40),
    
    # Side platforms
    (100, 420, 200, 25),
    (980, 420, 200, 25),
    
    # Top platforms
    (340, 300, 180, 25),
    (760, 300, 180, 25),
    
    # Center top platform
    (540, 180, 200, 25),
]

# Kill boundaries (als speler hier buiten komt = dood)
KILL_BOUNDARY = {
    "left": -200,
    "right": SCREEN_WIDTH + 200,
    "top": -300,
    "bottom": SCREEN_HEIGHT + 200,
}

# Spawn positions voor spelers
SPAWN_POSITIONS = [
    (400, 450),   # Player 1
    (880, 450),   # Player 2
    (300, 200),   # Player 3
    (980, 200),   # Player 4
]


# Sprite sheet configuratie (placeholder voor custom sprites)
SPRITE_CONFIG = {
    "default": {
        "idle": {
            "frames": 4,
            "frame_width": 64,
            "frame_height": 64,
            "animation_speed": 8,  # frames per sprite frame
        },
        "run": {
            "frames": 6,
            "frame_width": 64,
            "frame_height": 64,
            "animation_speed": 5,
        },
        "jump": {
            "frames": 2,
            "frame_width": 64,
            "frame_height": 64,
            "animation_speed": 6,
        },
        "fall": {
            "frames": 2,
            "frame_width": 64,
            "frame_height": 64,
            "animation_speed": 6,
        },
        "punch1": {
            "frames": 6,
            "frame_width": 64,
            "frame_height": 64,
            "animation_speed": 3,
        },
        "punch2": {
            "frames": 6,
            "frame_width": 64,
            "frame_height": 64,
            "animation_speed": 3,
        },
        "kick": {
            "frames": 6,
            "frame_width": 64,
            "frame_height": 64,
            "animation_speed": 3,
        },
        "jump_kick": {
            "frames": 6,
            "frame_width": 64,
            "frame_height": 64,
            "animation_speed": 3,
        },
        "special": {
            "frames": 6,
            "frame_width": 64,
            "frame_height": 64,
            "animation_speed": 3,
        },
    }
}


class EffectSettings:
    # Instellingen voor visuele effecten.

    # Screen shake
    SCREEN_SHAKE_INTENSITY = 8
    SCREEN_SHAKE_DURATION = 10  # frames
    
    # Hit particles
    PARTICLE_COUNT = 10
    PARTICLE_SPEED = 5
    PARTICLE_LIFETIME = 20  # frames
    
    # Trail effect
    TRAIL_LENGTH = 5
    TRAIL_FADE_SPEED = 50  # alpha decrease per frame


NETWORK_TICK_RATE = 60  # Updates per second
BUFFER_SIZE = 4096
CONNECTION_TIMEOUT = 5.0  # seconds

import pygame

CONTROLS = {
    "left": [pygame.K_a, pygame.K_LEFT],
    "right": [pygame.K_d, pygame.K_RIGHT],
    "up": [pygame.K_w, pygame.K_UP],
    "down": [pygame.K_s, pygame.K_DOWN],
    "jump": [pygame.K_w, pygame.K_SPACE, pygame.K_UP],
    "light_attack": [pygame.K_j],
    "heavy_attack": [pygame.K_k],
    "special_attack": [pygame.K_l],
    "dash": [pygame.K_LSHIFT, pygame.K_RSHIFT],
}
