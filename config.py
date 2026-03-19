# Configuratie - alle instellingen voor de game.

SERVER_IP = "172.20.208.1"
SERVER_PORT = 5555
DISCOVERY_PORT = 5556
DISCOVERY_TOKEN = "BRAWL_ARENA_DISCOVERY_V1"
MAX_PLAYERS = 4

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GAME_TITLE = "Brawl Arena"

PRELIMINARY_ROUNDS = 5
PRELIMINARY_ROUND_DURATION = 45 * FPS
FINAL_ROUND_STOCKS = 5
INFINITE_STOCKS = -1
COINS_PER_KILL = 1
COINS_PER_ROUND = 5
COINS_LOST_ON_DEATH = 1
MAP_COIN_VALUE = 1
MAP_COIN_RADIUS = 12
MAP_COIN_SPAWN_INTERVAL = 5 * FPS
MAX_MAP_COINS = 5


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
        "height": 22,
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


# Sprite sheet configuratie
SPRITE_CONFIG = {
    "default": {
        # Grounded movement
        "idle": {
            "file": "Idle_Stand.png",
            "frames": 1,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 8,
        },
        "walk": {
            "file": "Walking.png",
            "frames": 12,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 5,
        },
        "run": {
            "file": "Running.png",
            "frames": 12,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 4,
        },
        "speed_run": {
            "file": "Speed_Boost_Running.png",
            "frames": 12,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
        },
        # Jump states — each triggered by a different jump condition
        "jump_stationary": {
            "file": "Side_Jump.png",
            "frames": 10,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 4,
        },
        "jump_moving": {
            "file": "Jumping.png",
            "frames": 10,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 4,
        },
        "double_jump": {
            "file": "Double_Jump.png",
            "frames": 11,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 4,
        },
        # Knockback — Falling.png is ONLY for knockback, not normal falling
        "hurt": {
            "file": "Falling.png",
            "frames": 11,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
        },
        # Landing animations
        "landing": {
            "file": "Landing.png",
            "frames": 6,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 4,
        },
        "landing_impact": {
            "file": "Landing with Impact.png",
            "frames": 13,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
        },
        # Dash
        "dash": {
            "file": "Roll.png",
            "frames": 9,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
        },
        # Attacks
        "punch1": {
            "file": "Punch_1.png",
            "folder": "attacks",
            "frames": 5,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
        },
        "kick": {
            "file": "Power_Strike.png",
            "folder": "attacks",
            "frames": 11,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
            "render_offset_x": 33,  # Karakter staat ~33px links in het sprite sheet t.o.v. idle
        },
        "special": {
            "file": "Kick.png",
            "folder": "attacks",
            "frames": 5,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
            "penultimate_hold": 10,  # Extra frames vasthouden op de trappose (frame 3)
        },
        # Crouch (S / Arrow Down op de grond)
        "crouch": {
            "file": "Crouch.png",
            "frames": 3,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 5,
        },
        # Light attack in de lucht
        "jump_strike": {
            "file": "Jump witn Strike.png",
            "frames": 3,
            "frame_width": 128,
            "frame_height": 128,
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
DISCOVERY_TIMEOUT = 1.0  # seconds
STAT_SELECT_SECONDS = 30
INTERMISSION_SECONDS = 30
ROUND_END_DURATION = int(1.5 * FPS)
STAT_POINT_BUDGET = 10

BUILD_STAT_NAMES = ["power", "defense", "mobility", "knockback", "range"]
DEFAULT_BUILD_STATS = {name: 0 for name in BUILD_STAT_NAMES}

ATTACK_SHOP_ITEMS = [
    {
        "id": "piercing_jab",
        "slot": "light",
        "name": "Piercing Jab",
        "cost": 4,
        "focus": "Range",
        "description": "Longer poke with safer spacing.",
        "damage": 9,
        "knockback_base": 3.5,
        "knockback_scaling": 0.09,
        "knockback_angle": 38,
        "startup_frames": 4,
        "active_frames": 4,
        "recovery_frames": 8,
        "hitbox_width": 72,
        "hitbox_height": 22,
        "hitbox_offset_x": 14,
        "hitbox_offset_y": 5,
    },
    {
        "id": "crusher_elbow",
        "slot": "light",
        "name": "Crusher Elbow",
        "cost": 5,
        "focus": "Damage",
        "description": "Short reach but much heavier hit.",
        "damage": 12,
        "knockback_base": 4.2,
        "knockback_scaling": 0.1,
        "knockback_angle": 45,
        "startup_frames": 5,
        "active_frames": 3,
        "recovery_frames": 10,
        "hitbox_width": 44,
        "hitbox_height": 22,
        "hitbox_offset_x": 6,
        "hitbox_offset_y": 5,
    },
    {
        "id": "sweep_lunge",
        "slot": "heavy",
        "name": "Sweep Lunge",
        "cost": 6,
        "focus": "Range",
        "description": "Heavy slash that reaches far forward.",
        "damage": 14,
        "knockback_base": 6.5,
        "knockback_scaling": 0.12,
        "knockback_angle": 28,
        "startup_frames": 7,
        "active_frames": 6,
        "recovery_frames": 14,
        "hitbox_width": 82,
        "hitbox_height": 34,
        "hitbox_offset_x": 18,
        "hitbox_offset_y": 22,
    },
    {
        "id": "meteor_kick",
        "slot": "heavy",
        "name": "Meteor Kick",
        "cost": 7,
        "focus": "Knockback",
        "description": "Big launcher built to finish stocks.",
        "damage": 16,
        "knockback_base": 9,
        "knockback_scaling": 0.15,
        "knockback_angle": 24,
        "startup_frames": 9,
        "active_frames": 4,
        "recovery_frames": 16,
        "hitbox_width": 58,
        "hitbox_height": 40,
        "hitbox_offset_x": 12,
        "hitbox_offset_y": 20,
    },
    {
        "id": "skybreaker_spin",
        "slot": "special",
        "name": "Skybreaker Spin",
        "cost": 8,
        "focus": "Damage + Range",
        "description": "Wide spinning special with stronger launch.",
        "damage": 15,
        "knockback_base": 7,
        "knockback_scaling": 0.13,
        "knockback_angle": 62,
        "startup_frames": 6,
        "active_frames": 8,
        "recovery_frames": 14,
        "hitbox_width": 78,
        "hitbox_height": 58,
        "hitbox_offset_x": -8,
        "hitbox_offset_y": 0,
    },
]
ATTACK_SHOP_INDEX = {item["id"]: item for item in ATTACK_SHOP_ITEMS}

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
