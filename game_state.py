"""
Game State - Centrale game state voor server en client.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from entities.base_character import BaseCharacter
from entities.platform import Platform
from entities.warrior import Warrior
from config import (
    DEFAULT_BUILD_STATS,
    FINAL_ROUND_STOCKS,
    FPS,
    INFINITE_STOCKS,
    MAX_PLAYERS,
    PRELIMINARY_ROUND_DURATION,
    PRELIMINARY_ROUNDS,
    SPAWN_POSITIONS,
    STAGE_PLATFORMS,
    STAT_POINT_BUDGET,
    STAT_SELECT_SECONDS,
)


@dataclass
class PlayerData:
    player_id: int
    character: Optional[BaseCharacter] = None
    ready: bool = False
    wins: int = 0
    connected: bool = True
    build_stats: Dict[str, int] = None
    stats_locked: bool = False

    def __post_init__(self):
        if self.build_stats is None:
            self.build_stats = dict(DEFAULT_BUILD_STATS)


class GameState:

    def __init__(self):
        self.players: Dict[int, PlayerData] = {}
        self.platforms: List[Platform] = self._create_platforms()
        self.phase: str = "lobby"
        self.round_number: int = 1
        self.winner: Optional[int] = None
        self.max_players: int = MAX_PLAYERS
        self.stocks_per_player: int = INFINITE_STOCKS
        self.game_timer: int = 0
        self.stat_point_budget: int = STAT_POINT_BUDGET
        self.stat_select_total_frames: int = STAT_SELECT_SECONDS * FPS
        self.stat_select_remaining_frames: int = 0
        self.preliminary_rounds: int = PRELIMINARY_ROUNDS
        self.preliminary_round_duration: int = PRELIMINARY_ROUND_DURATION
        self.final_round_stocks: int = FINAL_ROUND_STOCKS
        self.is_final_round: bool = False

    def _create_platforms(self) -> List[Platform]:
        return [Platform.from_tuple(p) for p in STAGE_PLATFORMS]

    def active_player_count(self) -> int:
        return len(self.get_connected_players())

    def _next_player_id(self) -> Optional[int]:
        active_ids = {player.player_id for player in self.get_connected_players()}
        for player_id in range(self.max_players):
            if player_id not in active_ids:
                return player_id
        return None

    def add_player(self, player_id: Optional[int] = None) -> Optional[int]:
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
            return player_id

        self.players[player_id] = PlayerData(player_id=player_id)
        return player_id

    def remove_player(self, player_id: int) -> None:
        if player_id in self.players:
            self.players[player_id].connected = False
            self.players[player_id].ready = False
            self.players[player_id].stats_locked = False

    def set_player_ready(self, player_id: int, ready: bool = True) -> None:
        if player_id in self.players:
            self.players[player_id].ready = ready

    def select_stats(self, player_id: int, stats: Dict[str, Any]) -> bool:
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
        player = self.players.get(player_id)
        if not player:
            return False
        player.stats_locked = True
        return True

    def all_players_locked(self) -> bool:
        connected_players = self.get_connected_players()
        return bool(connected_players) and all(player.stats_locked for player in connected_players)

    def start_stat_selection(self) -> None:
        self.phase = "stat_select"
        self.round_number = 1
        self.winner = None
        self.game_timer = 0
        self.is_final_round = False
        self.stocks_per_player = INFINITE_STOCKS
        self.stat_select_remaining_frames = self.stat_select_total_frames
        for player in self.get_connected_players():
            player.ready = False
            player.stats_locked = False
            player.character = None
            player.build_stats = dict(DEFAULT_BUILD_STATS)

    def start_game(self) -> None:
        self.phase = "playing"
        self.round_number = 1
        self.game_timer = 0
        self.winner = None
        self.stat_select_remaining_frames = 0
        self.is_final_round = False
        self.stocks_per_player = INFINITE_STOCKS

        for i, player in enumerate(self.get_connected_players()):
            spawn = SPAWN_POSITIONS[i % len(SPAWN_POSITIONS)]
            player.character = Warrior(spawn[0], spawn[1], player.player_id)
            player.character.set_build_stats(player.build_stats)
            player.character.stocks = self.stocks_per_player
            player.ready = False

    def update(self) -> List[dict]:
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

        if self.phase != "playing":
            return events

        self.game_timer += 1

        if not self.is_final_round:
            if self.game_timer >= self.preliminary_round_duration:
                if self.round_number < self.preliminary_rounds:
                    self._advance_preliminary_round()
                    events.append({"type": "round_advanced", "round_number": self.round_number})
                else:
                    self._start_final_round()
                    events.append({"type": "final_round_started", "round_number": self.round_number})
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
        self.winner = None
        self.game_timer = 0

        for i, player in enumerate(self.get_connected_players()):
            if not player.character:
                continue

            spawn = SPAWN_POSITIONS[i % len(SPAWN_POSITIONS)]
            player.character.x = spawn[0]
            player.character.y = spawn[1]
            player.character.vel_x = 0
            player.character.vel_y = 0
            player.character.damage_percent = 0
            player.character.stocks = self.stocks_per_player
            player.character.hitstun = 0
            player.character.invincible = 120
            player.character.active_attack = None
            player.character.is_dashing = False
            player.character.dash_frames = 0
            player.character.dash_cooldown_timer = 0
            player.character.jumps_remaining = player.character.max_jumps
            player.character.attack_cooldown = 0
            player.character.attack_frame = 0

    def _advance_preliminary_round(self) -> None:
        self.round_number += 1
        self.stocks_per_player = INFINITE_STOCKS
        self.reset_round()

    def _start_final_round(self) -> None:
        self.round_number = self.preliminary_rounds + 1
        self.is_final_round = True
        self.stocks_per_player = self.final_round_stocks
        self.reset_round()

    def get_connected_players(self) -> List[PlayerData]:
        return [player for player in self.players.values() if player.connected]

    def get_characters(self) -> List[BaseCharacter]:
        return [
            player.character for player in self.players.values()
            if player.connected and player.character is not None
        ]

    def get_player(self, player_id: int) -> Optional[PlayerData]:
        return self.players.get(player_id)

    def get_stat_select_seconds_remaining(self) -> int:
        return max(0, (self.stat_select_remaining_frames + FPS - 1) // FPS)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "round_number": self.round_number,
            "winner": self.winner,
            "game_timer": self.game_timer,
            "stat_point_budget": self.stat_point_budget,
            "stat_select_remaining_frames": self.stat_select_remaining_frames,
            "is_final_round": self.is_final_round,
            "preliminary_rounds": self.preliminary_rounds,
            "preliminary_round_duration": self.preliminary_round_duration,
            "final_round_stocks": self.final_round_stocks,
            "players": {
                pid: {
                    "player_id": player.player_id,
                    "ready": player.ready,
                    "wins": player.wins,
                    "connected": player.connected,
                    "build_stats": dict(player.build_stats),
                    "stats_locked": player.stats_locked,
                    "character_state": player.character.get_state() if player.character else None,
                }
                for pid, player in self.players.items()
            },
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        self.phase = data["phase"]
        self.round_number = data["round_number"]
        self.winner = data["winner"]
        self.game_timer = data["game_timer"]
        self.stat_point_budget = data.get("stat_point_budget", STAT_POINT_BUDGET)
        self.stat_select_remaining_frames = data.get("stat_select_remaining_frames", 0)
        self.is_final_round = data.get("is_final_round", False)
        self.preliminary_rounds = data.get("preliminary_rounds", PRELIMINARY_ROUNDS)
        self.preliminary_round_duration = data.get("preliminary_round_duration", PRELIMINARY_ROUND_DURATION)
        self.final_round_stocks = data.get("final_round_stocks", FINAL_ROUND_STOCKS)
        self.stocks_per_player = self.final_round_stocks if self.is_final_round else INFINITE_STOCKS

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

            if pdata["character_state"]:
                if player.character is None:
                    player.character = Warrior(0, 0, pid)
                player.character.set_build_stats(player.build_stats)
                player.character.set_state(pdata["character_state"])
            else:
                player.character = None

        for pid, player in self.players.items():
            if pid not in seen_player_ids:
                player.connected = False
