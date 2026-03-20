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


def _make_stage_theme(
    sky_top,
    sky_bottom,
    haze,
    glow,
    sun,
    silhouette,
    platform_color,
    accent,
):
    return {
        "sky_top": sky_top,
        "sky_bottom": sky_bottom,
        "haze": haze,
        "glow": glow,
        "sun": sun,
        "silhouette": silhouette,
        "platform_color": platform_color,
        "accent": accent,
    }


def _spawn_on_platform(platform, y_offset=10):
    x, y, width, _ = platform
    return (
        int(x + ((width - CharacterStats.WIDTH) / 2)),
        int(y - CharacterStats.HEIGHT - y_offset),
    )


SKY_RUINS_PLATFORMS = [
    (80, 590, 300, 30),
    (450, 590, 380, 30),
    (900, 590, 300, 30),
    (180, 430, 180, 22),
    (920, 430, 180, 22),
    (550, 300, 180, 20),
]

TWIN_FORGE_PLATFORMS = [
    (110, 585, 240, 30),
    (930, 585, 240, 30),
    (435, 520, 410, 26),
    (250, 385, 190, 22),
    (840, 385, 190, 22),
    (545, 260, 190, 20),
    (80, 260, 140, 18),
    (1060, 260, 140, 18),
]

CROSSWIND_DECK_PLATFORMS = [
    (120, 560, 220, 26),
    (380, 500, 180, 22),
    (610, 410, 200, 20),
    (870, 300, 190, 20),
    (1030, 190, 140, 18),
    (250, 330, 120, 18),
]

CRIMSON_STEPS_PLATFORMS = [
    (60, 600, 250, 28),
    (360, 520, 220, 24),
    (620, 440, 220, 24),
    (890, 360, 220, 24),
    (170, 390, 170, 20),
    (500, 300, 170, 20),
    (980, 520, 170, 20),
]

NEBULA_SPINE_PLATFORMS = [
    (260, 610, 240, 24),
    (780, 610, 240, 24),
    (545, 560, 190, 24),
    (390, 445, 120, 20),
    (770, 445, 120, 20),
    (560, 340, 160, 20),
    (435, 225, 110, 18),
    (735, 225, 110, 18),
    (590, 115, 100, 16),
]

ECLIPSE_THRONE_PLATFORMS = [
    (350, 600, 580, 30),
    (120, 500, 220, 22),
    (940, 500, 220, 22),
    (255, 360, 190, 20),
    (835, 360, 190, 20),
    (525, 255, 230, 22),
    (560, 135, 160, 18),
    (595, 60, 90, 14),
]


ROUND_STAGE_LAYOUTS = [
    {
        "id": "sky_ruins",
        "name": "Sky Ruins",
        "background_path": "assets/backgrounds/Round 1.png",
        "platforms": SKY_RUINS_PLATFORMS,
        "spawn_positions": [
            _spawn_on_platform(SKY_RUINS_PLATFORMS[0]),
            _spawn_on_platform(SKY_RUINS_PLATFORMS[2]),
            _spawn_on_platform(SKY_RUINS_PLATFORMS[3]),
            _spawn_on_platform(SKY_RUINS_PLATFORMS[4]),
        ],
        "theme": _make_stage_theme(
            (68, 104, 150),
            (188, 214, 255),
            (214, 237, 255),
            (255, 245, 214),
            (255, 235, 160),
            (60, 80, 110),
            (122, 94, 63),
            (255, 224, 122),
        ),
    },
    {
        "id": "twin_forge",
        "name": "Twin Forge",
        "background_path": "assets/backgrounds/Round 2.png",
        "platforms": TWIN_FORGE_PLATFORMS,
        "spawn_positions": [
            _spawn_on_platform(TWIN_FORGE_PLATFORMS[0]),
            _spawn_on_platform(TWIN_FORGE_PLATFORMS[1]),
            _spawn_on_platform(TWIN_FORGE_PLATFORMS[3]),
            _spawn_on_platform(TWIN_FORGE_PLATFORMS[4]),
        ],
        "theme": _make_stage_theme(
            (88, 36, 26),
            (230, 120, 78),
            (255, 170, 96),
            (255, 206, 140),
            (255, 195, 78),
            (73, 29, 22),
            (90, 124, 145),
            (255, 228, 128),
        ),
    },
    {
        "id": "crosswind_deck",
        "name": "Crosswind Deck",
        "background_path": "assets/backgrounds/Round 3.png",
        "platforms": CROSSWIND_DECK_PLATFORMS,
        "spawn_positions": [
            (206, 486),
            (446, 426),
            (686, 336),
            (286, 256),
        ],
        "theme": _make_stage_theme(
            (24, 64, 94),
            (111, 190, 214),
            (185, 229, 238),
            (198, 255, 250),
            (155, 248, 255),
            (22, 55, 74),
            (78, 118, 101),
            (164, 249, 255),
        ),
    },
    {
        "id": "crimson_steps",
        "name": "Crimson Steps",
        "background_path": "assets/backgrounds/Round 4 (Make sure good size).png",
        "platforms": CRIMSON_STEPS_PLATFORMS,
        "spawn_positions": [
            _spawn_on_platform(CRIMSON_STEPS_PLATFORMS[0]),
            _spawn_on_platform(CRIMSON_STEPS_PLATFORMS[1]),
            _spawn_on_platform(CRIMSON_STEPS_PLATFORMS[2]),
            _spawn_on_platform(CRIMSON_STEPS_PLATFORMS[3]),
        ],
        "theme": _make_stage_theme(
            (54, 26, 46),
            (172, 78, 118),
            (238, 154, 173),
            (255, 182, 196),
            (255, 214, 176),
            (56, 25, 44),
            (74, 97, 132),
            (255, 221, 154),
        ),
    },
    {
        "id": "nebula_spine",
        "name": "Nebula Spine",
        "background_path": "assets/backgrounds/Round 5.png",
        "platforms": NEBULA_SPINE_PLATFORMS,
        "spawn_positions": [
            _spawn_on_platform(NEBULA_SPINE_PLATFORMS[0]),
            _spawn_on_platform(NEBULA_SPINE_PLATFORMS[1]),
            _spawn_on_platform(NEBULA_SPINE_PLATFORMS[3]),
            _spawn_on_platform(NEBULA_SPINE_PLATFORMS[4]),
        ],
        "theme": _make_stage_theme(
            (19, 22, 64),
            (84, 84, 176),
            (168, 155, 255),
            (180, 234, 255),
            (159, 194, 255),
            (30, 23, 73),
            (108, 90, 118),
            (196, 233, 255),
        ),
    },
]

FINAL_ROUND_STAGE = {
    "id": "eclipse_throne",
    "name": "Eclipse Throne",
    "background_path": "assets/backgrounds/Final Round.png",
    "platforms": ECLIPSE_THRONE_PLATFORMS,
    "spawn_positions": [
        _spawn_on_platform(ECLIPSE_THRONE_PLATFORMS[1]),
        _spawn_on_platform(ECLIPSE_THRONE_PLATFORMS[2]),
        _spawn_on_platform(ECLIPSE_THRONE_PLATFORMS[3]),
        _spawn_on_platform(ECLIPSE_THRONE_PLATFORMS[4]),
    ],
    "theme": _make_stage_theme(
        (14, 10, 32),
        (78, 42, 82),
        (178, 95, 98),
        (255, 175, 122),
        (255, 214, 134),
        (23, 14, 37),
        (146, 84, 95),
        (255, 224, 150),
    ),
}


def get_stage_definition(round_number, is_final_round=False):
    if is_final_round:
        return FINAL_ROUND_STAGE

    index = max(0, int(round_number) - 1)
    if not ROUND_STAGE_LAYOUTS:
        return FINAL_ROUND_STAGE
    return ROUND_STAGE_LAYOUTS[index % len(ROUND_STAGE_LAYOUTS)]


STAGE_PLATFORMS = get_stage_definition(1)["platforms"]

# Kill boundaries (als speler hier buiten komt = dood)
KILL_BOUNDARY = {
    "left": -200,
    "right": SCREEN_WIDTH + 200,
    "top": -300,
    "bottom": SCREEN_HEIGHT + 200,
}

# Spawn positions voor spelers
SPAWN_POSITIONS = get_stage_definition(1)["spawn_positions"]


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
        # Ultimate animations
        "ultimate_fireball": {
            "file": "Fire_Kick.png",
            "folder": "attacks",
            "frames": 11,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
        },
        "ultimate_teleport": {
            "file": "Teleport.png",
            "folder": "attacks",
            "frames": 17,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
            "render_offset_y": 20,
        },
        "ultimate_wind_power": {
            "file": "Wind_Power.png",
            "folder": "attacks",
            "frames": 6,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
        },
        "ultimate_knockback": {
            "file": "Knockback.png",
            "folder": "attacks",
            "frames": 8,
            "frame_width": 128,
            "frame_height": 128,
            "animation_speed": 3,
        },
        "ultimate_magic_shield": {
            "file": "Magic_Shield.png",
            "folder": "attacks",
            "frames": 12,
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

ULTIMATE_SHOP_ITEMS = [
    {
        "id": "teleportation",
        "name": "Teleportation",
        "cost": 9,
        "focus": "Mobility",
        "description": "Preview a blink, then teleport on release.",
        "cast_frames": 18,
        "cooldown_frames": 4 * FPS,
        "distance": 400,
        "glow_color": (90, 220, 255),
    },
    {
        "id": "fireball",
        "name": "Fireball",
        "cost": 8,
        "focus": "Projectile",
        "description": "Launch a fast fireball straight ahead.",
        "cast_frames": 33,
        "cooldown_frames": 6 * FPS,
        "damage": 16,
        "knockback_base": 6.0,
        "knockback_scaling": 0.11,
        "knockback_angle": 28,
        "projectile_speed": 10,
        "projectile_lifetime": 70,
        "hitbox_width": 46,
        "hitbox_height": 30,
        "spawn_offset_x": 20,
        "spawn_offset_y": -15,
        "launch_at_remaining_frames": 22,
        "glow_color": (255, 130, 40),
    },
    {
        "id": "invisibility",
        "name": "Invisibility",
        "cost": 13,
        "focus": "Stealth",
        "description": "Vanish until time runs out or you strike.",
        "cast_frames": 18,
        "duration_frames": 5 * FPS,
        "cooldown_frames": 8 * FPS,
        "attack_damage_multiplier": 1.5,
        "glow_color": (180, 180, 200),
    },
    {
        "id": "grab",
        "name": "Grab",
        "cost": 12,
        "focus": "Control",
        "description": "Absorb a foe, then spit them out hard.",
        "cast_frames": 12,
        "cooldown_frames": 7 * FPS,
        "active_frames": 3,
        "recovery_frames": 18,
        "hitbox_width": 54,
        "hitbox_height": 34,
        "hitbox_offset_x": 10,
        "hitbox_offset_y": 12,
        "hold_frames": 2 * FPS,
        "throw_knockback_base": 14.0,
        "throw_knockback_scaling": 0.14,
        "throw_angle": 42,
        "glow_color": (120, 255, 160),
    },
    {
        "id": "parry_counter",
        "name": "Parry Counter",
        "cost": 10,
        "focus": "Defense",
        "description": "Bubble parry that explodes on contact.",
        "cast_frames": 6,
        "parry_frames": 16,
        "recovery_frames": 20,
        "cooldown_frames": 7 * FPS,
        "miss_cooldown_frames": int(1.5 * FPS),
        "counter_damage": 16,
        "counter_knockback_base": 13.0,
        "counter_knockback_scaling": 0.16,
        "counter_knockback_angle": 52,
        "counter_hitbox_width": 152,
        "counter_hitbox_height": 124,
        "glow_color": (120, 220, 255),
    },
]
ULTIMATE_SHOP_INDEX = {item["id"]: item for item in ULTIMATE_SHOP_ITEMS}

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
    "ultimate_ability": [pygame.K_u],
    "dash": [pygame.K_LSHIFT, pygame.K_RSHIFT],
}
