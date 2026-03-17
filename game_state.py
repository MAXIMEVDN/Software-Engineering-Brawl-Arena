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
    ATTACK_SHOP_INDEX,
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
    coins: int = 0
    owned_attack_ids: List[str] = None
    equipped_attacks: Dict[str, Optional[str]] = None
    round_stat_upgrades: Dict[str, int] = None

    def __post_init__(self):
        if self.build_stats is None:
            self.build_stats = dict(DEFAULT_BUILD_STATS)
        if self.owned_attack_ids is None:
            self.owned_attack_ids = []
        if self.equipped_attacks is None:
            self.equipped_attacks = {
                "light": None,
                "heavy": None,
                "special": None,
            }
        if self.round_stat_upgrades is None:
            self.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}


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
        self.upgrade_shop_total_frames: int = INTERMISSION_SECONDS * FPS
        self.upgrade_shop_remaining_frames: int = 0
        self.round_end_total_frames: int = ROUND_END_DURATION
        self.round_end_remaining_frames: int = 0
        self.pending_round_transition: Optional[str] = None
        self.preliminary_rounds: int = PRELIMINARY_ROUNDS
        self.preliminary_round_duration: int = PRELIMINARY_ROUND_DURATION
        self.final_round_stocks: int = FINAL_ROUND_STOCKS
        self.is_final_round: bool = False
        self.map_coins: List[CoinPickup] = []
        self.coin_spawn_timer: int = 0
        self.next_coin_id: int = 1

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
            self.players[player_id].coins = 0
            self.players[player_id].owned_attack_ids = []
            self.players[player_id].equipped_attacks = {
                "light": None,
                "heavy": None,
                "special": None,
            }
            self.players[player_id].round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}
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

    def all_players_ready(self) -> bool:
        connected_players = self.get_connected_players()
        return bool(connected_players) and all(player.ready for player in connected_players)

    def start_stat_selection(self) -> None:
        self.phase = "stat_select"
        self.round_number = 1
        self.winner = None
        self.game_timer = 0
        self.is_final_round = False
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
            player.owned_attack_ids = []
            player.equipped_attacks = {
                "light": None,
                "heavy": None,
                "special": None,
            }
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}

    def start_game(self) -> None:
        self.phase = "playing"
        self.round_number = 1
        self.game_timer = 0
        self.winner = None
        self.stat_select_remaining_frames = 0
        self.upgrade_shop_remaining_frames = 0
        self.round_end_remaining_frames = 0
        self.pending_round_transition = None
        self.is_final_round = False
        self.stocks_per_player = INFINITE_STOCKS
        self._reset_map_coins()

        for i, player in enumerate(self.get_connected_players()):
            spawn = SPAWN_POSITIONS[i % len(SPAWN_POSITIONS)]
            player.character = Warrior(spawn[0], spawn[1], player.player_id)
            self._apply_player_build_to_character(player)
            player.character.stocks = self.stocks_per_player
            player.character.jumps_remaining = player.character.max_jumps
            player.ready = False
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}

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
        self.winner = None
        self.game_timer = 0
        self.round_end_remaining_frames = 0
        self._reset_map_coins()

        for i, player in enumerate(self.get_connected_players()):
            if not player.character:
                continue

            player.ready = False
            self._apply_player_build_to_character(player)
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
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}

    def _freeze_characters(self) -> None:
        for player in self.get_connected_players():
            if not player.character:
                continue
            player.character.vel_x = 0
            player.character.vel_y = 0
            player.character.hitstun = 0
            player.character.is_dashing = False
            player.character.dash_frames = 0
            player.character.active_attack = None
            player.character.attack_frame = 0

    def _start_round_end(self, transition: str) -> None:
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
        if not player.character:
            return
        player.character.set_build_stats(player.build_stats)
        player.character.set_equipped_attacks(player.equipped_attacks)

    def _start_upgrade_shop(self, transition: str) -> None:
        self.phase = "upgrade_shop"
        self.upgrade_shop_remaining_frames = self.upgrade_shop_total_frames
        self.round_end_remaining_frames = 0
        self.pending_round_transition = transition
        self._reset_map_coins()
        for player in self.get_connected_players():
            player.ready = False
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}

    def upgrade_stat(self, player_id: int, stat_name: str) -> bool:
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

    def buy_attack(self, player_id: int, attack_id: str) -> bool:
        player = self.players.get(player_id)
        offer = ATTACK_SHOP_INDEX.get(attack_id)
        if not player or not offer or self.phase != "upgrade_shop":
            return False
        if attack_id in player.owned_attack_ids or player.coins < offer["cost"]:
            return False

        player.coins -= offer["cost"]
        player.owned_attack_ids.append(attack_id)
        player.equipped_attacks[offer["slot"]] = attack_id
        self._apply_player_build_to_character(player)
        return True

    def equip_attack(self, player_id: int, attack_id: str) -> bool:
        player = self.players.get(player_id)
        offer = ATTACK_SHOP_INDEX.get(attack_id)
        if not player or not offer or self.phase != "upgrade_shop":
            return False
        if attack_id not in player.owned_attack_ids:
            return False

        player.equipped_attacks[offer["slot"]] = attack_id
        self._apply_player_build_to_character(player)
        return True

    def _reset_map_coins(self) -> None:
        self.map_coins = []
        self.coin_spawn_timer = 0
        self.next_coin_id = 1

    def _process_character_coin_events(self) -> None:
        for player in self.get_connected_players():
            if not player.character:
                continue

            for event in player.character.consume_gameplay_events():
                if event.get("type") != "death":
                    continue

                player.coins -= COINS_LOST_ON_DEATH
                killer_id = event.get("killer_id")
                killer = self.players.get(killer_id) if killer_id is not None else None
                if killer and killer.connected and killer.player_id != player.player_id:
                    killer.coins += COINS_PER_KILL

    def _collect_map_coins(self) -> None:
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
        if len(self.map_coins) >= MAX_MAP_COINS:
            return

        self.coin_spawn_timer += 1
        if self.coin_spawn_timer < MAP_COIN_SPAWN_INTERVAL:
            return

        self.coin_spawn_timer = 0
        self.map_coins.append(self._create_random_coin())

    def _create_random_coin(self) -> CoinPickup:
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
        for player in self.get_connected_players():
            player.coins += COINS_PER_ROUND

    def _advance_preliminary_round(self) -> None:
        self.round_number += 1
        self.phase = "playing"
        self.stocks_per_player = INFINITE_STOCKS
        self.reset_round()

    def _start_final_round(self) -> None:
        self.round_number = self.preliminary_rounds + 1
        self.phase = "playing"
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

    def get_upgrade_shop_seconds_remaining(self) -> int:
        return max(0, (self.upgrade_shop_remaining_frames + FPS - 1) // FPS)

    def to_dict(self) -> Dict[str, Any]:
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
            "players": {
                pid: {
                    "player_id": player.player_id,
                    "ready": player.ready,
                    "wins": player.wins,
                    "connected": player.connected,
                    "build_stats": dict(player.build_stats),
                    "stats_locked": player.stats_locked,
                    "coins": player.coins,
                    "owned_attack_ids": list(player.owned_attack_ids),
                    "equipped_attacks": dict(player.equipped_attacks),
                    "round_stat_upgrades": dict(player.round_stat_upgrades),
                    "character_state": player.character.get_state() if player.character else None,
                }
                for pid, player in self.players.items()
            },
            "map_coins": [coin.to_dict() for coin in self.map_coins],
            "coin_spawn_timer": self.coin_spawn_timer,
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
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
            player.owned_attack_ids = list(pdata.get("owned_attack_ids", []))
            player.equipped_attacks = {
                "light": None,
                "heavy": None,
                "special": None,
            }
            player.equipped_attacks.update(pdata.get("equipped_attacks", {}))
            player.round_stat_upgrades = {name: 0 for name in DEFAULT_BUILD_STATS}
            player.round_stat_upgrades.update(pdata.get("round_stat_upgrades", {}))

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
