"""
Game State - Centrale game state voor server en client.
"""

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from entities.base_character import BaseCharacter
from entities.coin_pickup import CoinPickup
from entities.platform import Platform
from entities.warrior import Warrior
from config import (
    COINS_LOST_ON_DEATH,
    COINS_PER_KILL,
    COINS_PER_ROUND,
    DEFAULT_BUILD_STATS,
    FINAL_ROUND_STOCKS,
    FPS,
    INFINITE_STOCKS,
    MAP_COIN_RADIUS,
    MAP_COIN_SPAWN_INTERVAL,
    MAX_PLAYERS,
    MAX_MAP_COINS,
    MAP_COIN_VALUE,
    INTERMISSION_SECONDS,
    ROUND_END_DURATION,
    PRELIMINARY_ROUND_DURATION,
    PRELIMINARY_ROUNDS,
    SPAWN_POSITIONS,
    STAGE_PLATFORMS,
    STAT_POINT_BUDGET,
    STAT_SELECT_SECONDS,
    ULTIMATE_SHOP_INDEX,
    get_stage_definition,
)


@dataclass
class PlayerData:
    """Persistent per-player data shared across lobby, rounds and shops."""
    player_id: int
    character: Optional[BaseCharacter] = None
    ready: bool = False
    wins: int = 0
    connected: bool = True
    build_stats: Dict[str, int] = None
    stats_locked: bool = False
    coins: int = 0
    owned_ultimate_ids: List[str] = None
    equipped_ultimate_id: Optional[str] = None
    round_stat_upgrades: Dict[str, int] = None
    username: str = ""

    def __post_init__(self):
        """Fill mutable player defaults after dataclass construction."""
        if self.build_stats is None:
            self.build_stats = dict(DEFAULT_BUILD_STATS)
        if self.owned_ultimate_ids is None:
            self.owned_ultimate_ids = []
        if self.round_stat_upgrades is None:
            self.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}


class GameState:
    """Single source of truth for players, rounds and match progression."""

    def __init__(self):
        self.players: Dict[int, PlayerData] = {}
        self.phase: str = "lobby"
        self.round_number: int = 1
        self.winner: Optional[int] = None
        self.max_players: int = MAX_PLAYERS
        self.stocks_per_player: int = INFINITE_STOCKS
        self.game_timer: int = 0
        self.stat_point_budget: int = STAT_POINT_BUDGET
        self.stat_select_total_frames: int = STAT_SELECT_SECONDS * FPS
        self.stat_select_remaining_frames: int = 0
        self.upgrade_shop_total_frames: int = INTERMISSION_SECONDS * FPS
        self.upgrade_shop_remaining_frames: int = 0
        self.round_end_total_frames: int = ROUND_END_DURATION
        self.round_end_remaining_frames: int = 0
        self.pending_round_transition: Optional[str] = None
        self.preliminary_rounds: int = PRELIMINARY_ROUNDS
        self.preliminary_round_duration: int = PRELIMINARY_ROUND_DURATION
        self.final_round_stocks: int = FINAL_ROUND_STOCKS
        self.is_final_round: bool = False
        self.current_stage_id: str = ""
        self.current_stage_name: str = ""
        self.current_stage_background_path: Optional[str] = None
        self.current_stage_theme: Dict[str, Any] = {}
        self.spawn_positions: List[tuple[int, int]] = list(SPAWN_POSITIONS)
        self.platforms: List[Platform] = []
        self.map_coins: List[CoinPickup] = []
        self.coin_spawn_timer: int = 0
        self.next_coin_id: int = 1
        self._refresh_stage_layout()

    def _create_platforms(self, stage_definition: Optional[Dict[str, Any]] = None) -> List[Platform]:
        """Create platform objects for the currently active stage."""
        stage_definition = stage_definition or get_stage_definition(self.round_number, self.is_final_round)
        theme = stage_definition.get("theme", {})
        platform_color = theme.get("platform_color")
        platform_data = stage_definition.get("platforms", STAGE_PLATFORMS)
        return [
            Platform(platform[0], platform[1], platform[2], platform[3], color=platform_color)
            for platform in platform_data
        ]

    def _refresh_stage_layout(self) -> None:
        """Load the platforms, spawns and background for the current round."""
        stage_definition = get_stage_definition(self.round_number, self.is_final_round)
        self.current_stage_id = stage_definition.get("id", "default_stage")
        self.current_stage_name = stage_definition.get("name", f"Round {self.round_number}")
        self.current_stage_background_path = stage_definition.get("background_path")
        self.current_stage_theme = dict(stage_definition.get("theme", {}))
        self.spawn_positions = [
            (int(position[0]), int(position[1]))
            for position in stage_definition.get("spawn_positions", SPAWN_POSITIONS)
        ]
        self.platforms = self._create_platforms(stage_definition)

    def active_player_count(self) -> int:
        """Return the number of connected players."""
        return len(self.get_connected_players())

    def _next_player_id(self) -> Optional[int]:
        """Return the next available player slot or None when full."""
        active_ids = {player.player_id for player in self.get_connected_players()}
        for player_id in range(self.max_players):
            if player_id not in active_ids:
                return player_id
        return None

    def add_player(self, player_id: Optional[int] = None) -> Optional[int]:
        """Add a new player or reset an existing slot for reconnection."""
        if player_id is None:
            player_id = self._next_player_id()
        if player_id is None:
            return None

        if player_id in self.players:
            self.players[player_id].connected = True
            self.players[player_id].ready = False
            self.players[player_id].stats_locked = False
            self.players[player_id].build_stats = dict(DEFAULT_BUILD_STATS)
            self.players[player_id].character = None
            self.players[player_id].coins = 0
            self.players[player_id].owned_ultimate_ids = []
            self.players[player_id].equipped_ultimate_id = None
            self.players[player_id].round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}
            return player_id

        self.players[player_id] = PlayerData(player_id=player_id)
        return player_id

    def remove_player(self, player_id: int) -> None:
        """Mark a player as disconnected while keeping their slot data."""
        if player_id in self.players:
            self.players[player_id].connected = False
            self.players[player_id].ready = False
            self.players[player_id].stats_locked = False

    def set_player_ready(self, player_id: int, ready: bool = True) -> None:
        """Set whether a player is ready to advance from the current phase."""
        if player_id in self.players:
            self.players[player_id].ready = ready

    def select_stats(self, player_id: int, stats: Dict[str, Any]) -> bool:
        """Validate and store a player's selected build stats."""
        player = self.players.get(player_id)
        if not player or player.stats_locked:
            return False

        normalized = {}
        total = 0
        for stat_name in DEFAULT_BUILD_STATS:
            value = max(0, int(stats.get(stat_name, 0)))
            normalized[stat_name] = value
            total += value

        if total > self.stat_point_budget:
            return False

        player.build_stats = normalized
        return True

    def lock_stats(self, player_id: int) -> bool:
        """Lock in a player's chosen stats for this build phase."""
        player = self.players.get(player_id)
        if not player:
            return False
        player.stats_locked = True
        return True

    def all_players_locked(self) -> bool:
        """Return whether every connected player has locked their build."""
        connected_players = self.get_connected_players()
        return bool(connected_players) and all(player.stats_locked for player in connected_players)

    def all_players_ready(self) -> bool:
        """Return whether every connected player is marked ready."""
        connected_players = self.get_connected_players()
        return bool(connected_players) and all(player.ready for player in connected_players)

    def start_stat_selection(self) -> None:
        """Reset the match and move all connected players into the build phase."""
        self.phase = "stat_select"
        self.round_number = 1
        self.winner = None
        self.game_timer = 0
        self.is_final_round = False
        self._refresh_stage_layout()
        self.stocks_per_player = INFINITE_STOCKS
        self.stat_select_remaining_frames = self.stat_select_total_frames
        self.upgrade_shop_remaining_frames = 0
        self.round_end_remaining_frames = 0
        self.pending_round_transition = None
        self._reset_map_coins()
        for player in self.get_connected_players():
            player.ready = False
            player.stats_locked = False
            player.character = None
            player.build_stats = dict(DEFAULT_BUILD_STATS)
            player.coins = 0
            player.owned_ultimate_ids = []
            player.equipped_ultimate_id = None
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}

    def start_game(self) -> None:
        """Create the characters and start round 1."""
        self.phase = "playing"
        self.round_number = 1
        self.game_timer = 0
        self.winner = None
        self.stat_select_remaining_frames = 0
        self.upgrade_shop_remaining_frames = 0
        self.round_end_remaining_frames = 0
        self.pending_round_transition = None
        self.is_final_round = False
        self._refresh_stage_layout()
        self.stocks_per_player = INFINITE_STOCKS
        self._reset_map_coins()

        for i, player in enumerate(self.get_connected_players()):
            spawn = self.spawn_positions[i % len(self.spawn_positions)]
            player.character = Warrior(spawn[0], spawn[1], player.player_id)
            player.character.set_respawn_position(spawn[0], spawn[1])
            self._apply_player_build_to_character(player)
            player.character.stocks = self.stocks_per_player
            player.character.jumps_remaining = player.character.max_jumps
            player.ready = False
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}

    def update(self) -> List[dict]:
        """Advance the match state machine and return emitted events."""
        events = []

        if self.phase == "stat_select":
            if self.stat_select_remaining_frames > 0:
                self.stat_select_remaining_frames -= 1

            if self.stat_select_remaining_frames <= 0 or self.all_players_locked():
                if self.active_player_count() >= 2:
                    self.start_game()
                    events.append({"type": "game_started"})
                else:
                    self.phase = "lobby"

            return events

        if self.phase == "round_end":
            if self.round_end_remaining_frames > 0:
                self.round_end_remaining_frames -= 1

            if self.round_end_remaining_frames <= 0:
                transition = self.pending_round_transition
                self._start_upgrade_shop(transition or "preliminary")
                events.append({"type": "upgrade_shop_started", "round_number": self.round_number})

            return events

        if self.phase == "upgrade_shop":
            if self.upgrade_shop_remaining_frames > 0:
                self.upgrade_shop_remaining_frames -= 1

            if self.upgrade_shop_remaining_frames <= 0 or self.all_players_ready():
                transition = self.pending_round_transition
                self.pending_round_transition = None
                if transition == "final":
                    self._start_final_round()
                    events.append({"type": "final_round_started", "round_number": self.round_number})
                else:
                    self._advance_preliminary_round()
                    events.append({"type": "round_advanced", "round_number": self.round_number})

            return events

        if self.phase != "playing":
            return events

        self._process_character_coin_events()
        self._collect_map_coins()
        self._update_map_coin_spawns()
        self.game_timer += 1

        if not self.is_final_round:
            if self.game_timer >= self.preliminary_round_duration:
                self._award_round_coins()
                if self.round_number < self.preliminary_rounds:
                    self._start_round_end("preliminary")
                    events.append({"type": "round_ended", "round_number": self.round_number})
                else:
                    self._start_round_end("final")
                    events.append({"type": "round_ended", "round_number": self.round_number})
            return events

        alive_players = [
            player for player in self.players.values()
            if player.connected and player.character and player.character.stocks > 0
        ]

        if len(alive_players) <= 1 and len(self.get_connected_players()) >= 2:
            if alive_players:
                self.winner = alive_players[0].player_id
            self.phase = "game_over"
            events.append({"type": "game_over", "winner": self.winner})

        return events

    def reset_round(self) -> None:
        """Reset fighters, map state and timers for a fresh round start."""
        self.winner = None
        self.game_timer = 0
        self.round_end_remaining_frames = 0
        self._refresh_stage_layout()
        self._reset_map_coins()

        for i, player in enumerate(self.get_connected_players()):
            if not player.character:
                continue

            player.ready = False
            self._apply_player_build_to_character(player)
            spawn = self.spawn_positions[i % len(self.spawn_positions)]
            player.character.set_respawn_position(spawn[0], spawn[1])
            player.character.x = spawn[0]
            player.character.y = spawn[1]
            player.character.vel_x = 0
            player.character.vel_y = 0
            player.character.damage_percent = 0
            player.character.stocks = self.stocks_per_player
            player.character.hitstun = 0
            player.character.invincible = 120
            player.character.active_attack = None
            player.character.active_ultimate_projectile = None
            player.character.is_dashing = False
            player.character.dash_frames = 0
            player.character.dash_cooldown_timer = 0
            player.character.jumps_remaining = player.character.max_jumps
            player.character.attack_cooldown = 0
            player.character.attack_frame = 0
            player.character.ultimate_cooldown_timer = 0
            player.character.ultimate_cast_timer = 0
            player.character.casting_ultimate_id = None
            player.character.invisible_timer = 0
            player.character.grabbed_target_id = None
            player.character.grab_hold_timer = 0
            player.character.absorbed_by_id = None
            player.character._grabbed_target_ref = None
            player.character.parry_active_timer = 0
            player.character.parry_recovery_timer = 0
            player.character.cancel_ultimate_preview()
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}

    def _freeze_characters(self) -> None:
        """Stop character movement and clear active combat state between phases."""
        for player in self.get_connected_players():
            if not player.character:
                continue
            player.character.vel_x = 0
            player.character.vel_y = 0
            player.character.hitstun = 0
            player.character.is_dashing = False
            player.character.dash_frames = 0
            player.character.active_attack = None
            player.character.active_ultimate_projectile = None
            player.character.attack_frame = 0
            player.character.ultimate_cast_timer = 0
            player.character.casting_ultimate_id = None
            player.character.invisible_timer = 0
            player.character.grabbed_target_id = None
            player.character.grab_hold_timer = 0
            player.character.absorbed_by_id = None
            player.character._grabbed_target_ref = None
            player.character.parry_active_timer = 0
            player.character.parry_recovery_timer = 0
            player.character.cancel_ultimate_preview()

    def _start_round_end(self, transition: str) -> None:
        """Enter the round-end pause before the upgrade shop opens."""
        self.phase = "round_end"
        self.round_end_remaining_frames = self.round_end_total_frames
        self.upgrade_shop_remaining_frames = 0
        self.pending_round_transition = transition
        self._reset_map_coins()
        self._freeze_characters()
        for player in self.get_connected_players():
            player.ready = False
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}

    def _apply_player_build_to_character(self, player: PlayerData) -> None:
        """Apply stored build stats and the equipped ultimate to a character."""
        if not player.character:
            return
        player.character.set_build_stats(player.build_stats)
        player.character.set_equipped_ultimate(player.equipped_ultimate_id)

    def _start_upgrade_shop(self, transition: str) -> None:
        """Switch into the upgrade shop and reset per-round ready flags."""
        self.phase = "upgrade_shop"
        self.upgrade_shop_remaining_frames = self.upgrade_shop_total_frames
        self.round_end_remaining_frames = 0
        self.pending_round_transition = transition
        self._reset_map_coins()
        for player in self.get_connected_players():
            player.ready = False
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}

    def upgrade_stat(self, player_id: int, stat_name: str) -> bool:
        """Spend coins to upgrade a stat during the shop phase."""
        player = self.players.get(player_id)
        if not player or self.phase != "upgrade_shop" or stat_name not in DEFAULT_BUILD_STATS:
            return False

        current_value = player.build_stats.get(stat_name, 0)
        cost = current_value + 1
        if player.coins < cost:
            return False

        player.coins -= cost
        player.build_stats[stat_name] = current_value + 1
        player.round_stat_upgrades[stat_name] = player.round_stat_upgrades.get(stat_name, 0) + 1
        self._apply_player_build_to_character(player)
        return True

    def downgrade_stat(self, player_id: int, stat_name: str) -> bool:
        """Undo a same-round stat upgrade and refund its coin cost."""
        player = self.players.get(player_id)
        if not player or self.phase != "upgrade_shop" or stat_name not in DEFAULT_BUILD_STATS:
            return False

        if player.round_stat_upgrades.get(stat_name, 0) <= 0:
            return False

        current_value = player.build_stats.get(stat_name, 0)
        if current_value <= 0:
            return False

        refund = current_value
        player.coins += refund
        player.build_stats[stat_name] = current_value - 1
        player.round_stat_upgrades[stat_name] = max(0, player.round_stat_upgrades.get(stat_name, 0) - 1)
        self._apply_player_build_to_character(player)
        return True

    def buy_ultimate(self, player_id: int, ultimate_id: str) -> bool:
        """Purchase and equip a new ultimate during the shop phase."""
        player = self.players.get(player_id)
        offer = ULTIMATE_SHOP_INDEX.get(ultimate_id)
        if not player or not offer or self.phase != "upgrade_shop":
            return False
        if ultimate_id in player.owned_ultimate_ids or player.coins < offer["cost"]:
            return False

        player.coins -= offer["cost"]
        player.owned_ultimate_ids.append(ultimate_id)
        player.equipped_ultimate_id = ultimate_id
        self._apply_player_build_to_character(player)
        return True

    def equip_ultimate(self, player_id: int, ultimate_id: str) -> bool:
        """Equip an ultimate the player already owns."""
        player = self.players.get(player_id)
        offer = ULTIMATE_SHOP_INDEX.get(ultimate_id)
        if not player or not offer or self.phase != "upgrade_shop":
            return False
        if ultimate_id not in player.owned_ultimate_ids:
            return False

        player.equipped_ultimate_id = ultimate_id
        self._apply_player_build_to_character(player)
        return True

    def _reset_map_coins(self) -> None:
        """Clear all stage coins and reset the spawn timer state."""
        self.map_coins = []
        self.coin_spawn_timer = 0
        self.next_coin_id = 1

    def _process_character_coin_events(self) -> None:
        """Apply coin rewards and penalties from queued character events."""
        for player in self.get_connected_players():
            if not player.character:
                continue

            for event in player.character.consume_gameplay_events():
                if event.get("type") != "death":
                    continue

                player.coins = max(0, player.coins - COINS_LOST_ON_DEATH)
                killer_id = event.get("killer_id")
                killer = self.players.get(killer_id) if killer_id is not None else None
                if killer and killer.connected and killer.player_id != player.player_id:
                    killer.coins += COINS_PER_KILL

    def _collect_map_coins(self) -> None:
        """Award any spawned map coins collected by characters this frame."""
        remaining_coins = []
        for coin in self.map_coins:
            collected = False
            for player in self.get_connected_players():
                if not player.character:
                    continue
                if player.character.get_rect().colliderect(coin.get_rect()):
                    player.coins += coin.value
                    collected = True
                    break

            if not collected:
                remaining_coins.append(coin)

        self.map_coins = remaining_coins

    def _update_map_coin_spawns(self) -> None:
        """Spawn new map coins over time until the maximum is reached."""
        if len(self.map_coins) >= MAX_MAP_COINS:
            return

        self.coin_spawn_timer += 1
        if self.coin_spawn_timer < MAP_COIN_SPAWN_INTERVAL:
            return

        self.coin_spawn_timer = 0
        self.map_coins.append(self._create_random_coin())

    def _create_random_coin(self) -> CoinPickup:
        """Create a coin above a random platform with basic spacing rules."""
        radius = MAP_COIN_RADIUS

        for _ in range(12):
            platform = random.choice(self.platforms)
            min_x = int(platform.x + radius)
            max_x = int(platform.x + platform.width - radius)
            if min_x > max_x:
                continue

            x = random.randint(min_x, max_x)
            y = int(platform.y - radius - 8)
            if all(abs(existing.x - x) > radius * 3 or abs(existing.y - y) > radius * 3 for existing in self.map_coins):
                coin = CoinPickup(self.next_coin_id, x, y, MAP_COIN_VALUE, radius)
                self.next_coin_id += 1
                return coin

        fallback_coin = CoinPickup(self.next_coin_id, 640, 260, MAP_COIN_VALUE, radius)
        self.next_coin_id += 1
        return fallback_coin

    def _award_round_coins(self) -> None:
        """Grant the end-of-round coin reward to all connected players."""
        for player in self.get_connected_players():
            player.coins += COINS_PER_ROUND

    def _advance_preliminary_round(self) -> None:
        """Increment the round counter and start the next preliminary round."""
        self.round_number += 1
        self.phase = "playing"
        self.stocks_per_player = INFINITE_STOCKS
        self.reset_round()

    def _start_final_round(self) -> None:
        """Start the final stock-based round after preliminaries end."""
        self.round_number = self.preliminary_rounds + 1
        self.phase = "playing"
        self.is_final_round = True
        self.stocks_per_player = self.final_round_stocks
        self.reset_round()

    def get_connected_players(self) -> List[PlayerData]:
        """Return all player entries that are still connected."""
        return [player for player in self.players.values() if player.connected]

    def get_characters(self) -> List[BaseCharacter]:
        """Return connected character instances that currently exist."""
        return [
            player.character for player in self.players.values()
            if player.connected and player.character is not None
        ]

    def get_player(self, player_id: int) -> Optional[PlayerData]:
        """Look up one player's stored data by id."""
        return self.players.get(player_id)

    def set_player_username(self, player_id: int, username: str) -> None:
        """Store a clipped display name for one player."""
        player = self.players.get(player_id)
        if player:
            player.username = username[:20]

    def get_stat_select_seconds_remaining(self) -> int:
        """Return the remaining stat-selection time in whole seconds."""
        return max(0, (self.stat_select_remaining_frames + FPS - 1) // FPS)

    def get_upgrade_shop_seconds_remaining(self) -> int:
        """Return the remaining shop time in whole seconds."""
        return max(0, (self.upgrade_shop_remaining_frames + FPS - 1) // FPS)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full authoritative game state for network sync."""
        return {
            "phase": self.phase,
            "round_number": self.round_number,
            "winner": self.winner,
            "game_timer": self.game_timer,
            "stat_point_budget": self.stat_point_budget,
            "stat_select_remaining_frames": self.stat_select_remaining_frames,
            "upgrade_shop_remaining_frames": self.upgrade_shop_remaining_frames,
            "round_end_remaining_frames": self.round_end_remaining_frames,
            "pending_round_transition": self.pending_round_transition,
            "is_final_round": self.is_final_round,
            "preliminary_rounds": self.preliminary_rounds,
            "preliminary_round_duration": self.preliminary_round_duration,
            "final_round_stocks": self.final_round_stocks,
            "current_stage_id": self.current_stage_id,
            "current_stage_name": self.current_stage_name,
            "current_stage_background_path": self.current_stage_background_path,
            "players": {
                pid: {
                    "player_id": player.player_id,
                    "ready": player.ready,
                    "wins": player.wins,
                    "connected": player.connected,
                    "build_stats": dict(player.build_stats),
                    "stats_locked": player.stats_locked,
                    "coins": player.coins,
                    "owned_ultimate_ids": list(player.owned_ultimate_ids),
                    "equipped_ultimate_id": player.equipped_ultimate_id,
                    "round_stat_upgrades": dict(player.round_stat_upgrades),
                    "username": player.username,
                    "character_state": player.character.get_state() if player.character else None,
                }
                for pid, player in self.players.items()
            },
            "map_coins": [coin.to_dict() for coin in self.map_coins],
            "coin_spawn_timer": self.coin_spawn_timer,
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load a full game-state snapshot received from the server."""
        self.phase = data["phase"]
        self.round_number = data["round_number"]
        self.winner = data["winner"]
        self.game_timer = data["game_timer"]
        self.stat_point_budget = data.get("stat_point_budget", STAT_POINT_BUDGET)
        self.stat_select_remaining_frames = data.get("stat_select_remaining_frames", 0)
        self.upgrade_shop_remaining_frames = data.get("upgrade_shop_remaining_frames", 0)
        self.round_end_remaining_frames = data.get("round_end_remaining_frames", 0)
        self.pending_round_transition = data.get("pending_round_transition")
        self.is_final_round = data.get("is_final_round", False)
        self.preliminary_rounds = data.get("preliminary_rounds", PRELIMINARY_ROUNDS)
        self.preliminary_round_duration = data.get("preliminary_round_duration", PRELIMINARY_ROUND_DURATION)
        self.final_round_stocks = data.get("final_round_stocks", FINAL_ROUND_STOCKS)
        self._refresh_stage_layout()
        self.current_stage_background_path = data.get(
            "current_stage_background_path",
            self.current_stage_background_path,
        )
        self.stocks_per_player = self.final_round_stocks if self.is_final_round else INFINITE_STOCKS
        self.map_coins = [CoinPickup.from_dict(coin_data) for coin_data in data.get("map_coins", [])]
        self.coin_spawn_timer = data.get("coin_spawn_timer", 0)
        self.next_coin_id = max((coin.coin_id for coin in self.map_coins), default=0) + 1

        seen_player_ids = set()
        for pid_str, pdata in data["players"].items():
            pid = int(pid_str)
            seen_player_ids.add(pid)

            if pid not in self.players:
                self.players[pid] = PlayerData(player_id=pid)

            player = self.players[pid]
            player.ready = pdata["ready"]
            player.wins = pdata["wins"]
            player.connected = pdata["connected"]
            player.build_stats = dict(pdata.get("build_stats", DEFAULT_BUILD_STATS))
            player.stats_locked = pdata.get("stats_locked", False)
            player.coins = pdata.get("coins", 0)
            player.owned_ultimate_ids = list(pdata.get("owned_ultimate_ids", []))
            player.equipped_ultimate_id = pdata.get("equipped_ultimate_id")
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}
            player.round_stat_upgrades.update(pdata.get("round_stat_upgrades", {}))
            player.username = pdata.get("username", "")

            if pdata["character_state"]:
                if player.character is None:
                    player.character = Warrior(0, 0, pid)
                self._apply_player_build_to_character(player)
                player.character.set_state(pdata["character_state"])
            else:
                player.character = None

        for pid, player in self.players.items():
            if pid not in seen_player_ids:
                player.connected = False
