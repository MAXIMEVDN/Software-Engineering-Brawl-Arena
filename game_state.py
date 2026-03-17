"""
Game State - Centrale game state voor server en client.

Dit module bevat de GameState class die de volledige staat
van een game match beheert.
"""

from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass, field

from entities.base_character import BaseCharacter
from entities.warrior import Warrior
from entities.mage import Mage
from entities.ninja import Ninja
from entities.platform import Platform
from entities.attack import Attack
from config import (
    STAGE_PLATFORMS,
    SPAWN_POSITIONS,
    MAX_PLAYERS,
    PRELIMINARY_ROUNDS,
    PRELIMINARY_ROUND_DURATION,
    FINAL_ROUND_STOCKS,
    INFINITE_STOCKS,
)


# Character type mapping
CHARACTER_CLASSES: Dict[str, Type[BaseCharacter]] = {
    "Warrior": Warrior,
    "Mage": Mage,
    "Ninja": Ninja,
}


@dataclass
class PlayerData:
    """
    Data container voor een speler.
    
    Attributes:
        player_id: Unieke speler ID
        character: Het character object
        ready: Of speler ready is
        wins: Aantal gewonnen rondes
    """
    player_id: int
    character: Optional[BaseCharacter] = None
    character_type: str = "Warrior"
    ready: bool = False
    wins: int = 0
    connected: bool = True


class GameState:
    """
    Centrale game state manager.
    
    Beheert alle spelers, platforms, en game logica.
    Kan geserialiseerd worden voor netwerk transmissie.
    
    Attributes:
        players: Dictionary van player_id -> PlayerData
        platforms: Lijst van platforms
        phase: Huidige game fase ("lobby", "character_select", "playing", "game_over")
        round_number: Huidige ronde nummer
        winner: Player ID van winnaar (of None)
    """
    
    def __init__(self):
        """Initialiseer game state."""
        self.players: Dict[int, PlayerData] = {}
        self.platforms: List[Platform] = self._create_platforms()
        self.phase: str = "lobby"
        self.round_number: int = 1
        self.winner: Optional[int] = None
        self.max_players: int = MAX_PLAYERS
        self.stocks_per_player: int = INFINITE_STOCKS
        self.game_timer: int = 0  # Frames sinds game start
        self.preliminary_rounds: int = PRELIMINARY_ROUNDS
        self.preliminary_round_duration: int = PRELIMINARY_ROUND_DURATION
        self.final_round_stocks: int = FINAL_ROUND_STOCKS
        self.is_final_round: bool = False
    
    def _create_platforms(self) -> List[Platform]:
        """
        Maak de stage platforms.
        
        Returns:
            Lijst van Platform objecten
        """
        return [Platform.from_tuple(p) for p in STAGE_PLATFORMS]
    
    # =========================================================================
    # PLAYER MANAGEMENT
    # =========================================================================
    
    def add_player(self, player_id: int) -> bool:
        """
        Voeg een nieuwe speler toe.
        
        Args:
            player_id: ID voor nieuwe speler
            
        Returns:
            True als toegevoegd, False als vol
        """
        if len(self.players) >= self.max_players:
            return False
        
        if player_id in self.players:
            self.players[player_id].connected = True
            return True
        
        self.players[player_id] = PlayerData(player_id=player_id)
        return True
    
    def remove_player(self, player_id: int) -> None:
        """
        Verwijder een speler.
        
        Args:
            player_id: ID van speler om te verwijderen
        """
        if player_id in self.players:
            self.players[player_id].connected = False
    
    def select_character(self, player_id: int, character_type: str) -> bool:
        """
        Selecteer een character voor een speler.
        
        Args:
            player_id: Speler ID
            character_type: Type character ("Warrior", "Mage", "Ninja")
            
        Returns:
            True als geldig, False anders
        """
        if player_id not in self.players:
            return False
        
        if character_type not in CHARACTER_CLASSES:
            return False
        
        self.players[player_id].character_type = character_type
        return True
    
    def set_player_ready(self, player_id: int, ready: bool = True) -> None:
        """
        Zet ready status voor een speler.
        
        Args:
            player_id: Speler ID
            ready: Ready status
        """
        if player_id in self.players:
            self.players[player_id].ready = ready
    
    def all_players_ready(self) -> bool:
        """
        Check of alle spelers ready zijn.
        
        Returns:
            True als iedereen ready is
        """
        connected_players = [p for p in self.players.values() if p.connected]
        return len(connected_players) >= 2 and all(p.ready for p in connected_players)
    
    # =========================================================================
    # GAME FLOW
    # =========================================================================
    
    def start_game(self) -> None:
        """Start de game met geselecteerde characters."""
        self.phase = "playing"
        self.round_number = 1
        self.game_timer = 0
        self.winner = None
        self.is_final_round = False
        self.stocks_per_player = INFINITE_STOCKS
        
        # Spawn characters
        for i, (player_id, player_data) in enumerate(self.players.items()):
            if not player_data.connected:
                continue
            
            spawn = SPAWN_POSITIONS[i % len(SPAWN_POSITIONS)]
            char_class = CHARACTER_CLASSES.get(player_data.character_type, Warrior)
            player_data.character = char_class(spawn[0], spawn[1], player_id)
            player_data.character.stocks = self.stocks_per_player
            player_data.ready = False
    
    def update(self) -> List[dict]:
        """
        Update game state voor één frame.
        
        Returns:
            Lijst van events die optraden
        """
        if self.phase != "playing":
            return []
        
        events = []
        self.game_timer += 1
        
        # Check for winner
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
            p for p in self.players.values()
            if p.connected and p.character and p.character.stocks > 0
        ]

        if len(alive_players) <= 1 and len(self.get_connected_players()) >= 2:
            if alive_players:
                self.winner = alive_players[0].player_id
            self.phase = "game_over"
            events.append({"type": "game_over", "winner": self.winner})
        
        return events
    
    def reset_round(self) -> None:
        """Reset voor een nieuwe ronde."""
        self.winner = None
        self.game_timer = 0
        
        # Reset characters
        for i, player_data in enumerate(self.players.values()):
            if player_data.connected and player_data.character:
                spawn = SPAWN_POSITIONS[i % len(SPAWN_POSITIONS)]
                player_data.character.x = spawn[0]
                player_data.character.y = spawn[1]
                player_data.character.vel_x = 0
                player_data.character.vel_y = 0
                player_data.character.damage_percent = 0
                player_data.character.stocks = self.stocks_per_player
                player_data.character.hitstun = 0
                player_data.character.invincible = 120
                player_data.character.active_attack = None
                player_data.character.is_dashing = False
                player_data.character.dash_frames = 0
                player_data.character.dash_cooldown_timer = 0

    def _advance_preliminary_round(self) -> None:
        """Ga naar de volgende preliminary round."""
        self.round_number += 1
        self.stocks_per_player = INFINITE_STOCKS
        self.reset_round()

    def _start_final_round(self) -> None:
        """Start de finale waarin spelers beperkte levens hebben."""
        self.round_number = self.preliminary_rounds + 1
        self.is_final_round = True
        self.stocks_per_player = self.final_round_stocks
        self.reset_round()
    
    # =========================================================================
    # GETTERS
    # =========================================================================
    
    def get_connected_players(self) -> List[PlayerData]:
        """
        Haal alle verbonden spelers op.
        
        Returns:
            Lijst van PlayerData voor verbonden spelers
        """
        return [p for p in self.players.values() if p.connected]
    
    def get_characters(self) -> List[BaseCharacter]:
        """
        Haal alle actieve characters op.
        
        Returns:
            Lijst van character objecten
        """
        return [
            p.character for p in self.players.values()
            if p.connected and p.character is not None
        ]
    
    def get_player(self, player_id: int) -> Optional[PlayerData]:
        """
        Haal player data op.
        
        Args:
            player_id: Speler ID
            
        Returns:
            PlayerData of None
        """
        return self.players.get(player_id)
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialiseer game state naar dictionary.
        
        Returns:
            Dictionary met volledige game state
        """
        return {
            "phase": self.phase,
            "round_number": self.round_number,
            "winner": self.winner,
            "game_timer": self.game_timer,
            "is_final_round": self.is_final_round,
            "preliminary_rounds": self.preliminary_rounds,
            "preliminary_round_duration": self.preliminary_round_duration,
            "final_round_stocks": self.final_round_stocks,
            "players": {
                pid: {
                    "player_id": p.player_id,
                    "character_type": p.character_type,
                    "ready": p.ready,
                    "wins": p.wins,
                    "connected": p.connected,
                    "character_state": p.character.get_state() if p.character else None,
                }
                for pid, p in self.players.items()
            }
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Herstel game state van dictionary.
        
        Args:
            data: Dictionary met game state
        """
        self.phase = data["phase"]
        self.round_number = data["round_number"]
        self.winner = data["winner"]
        self.game_timer = data["game_timer"]
        self.is_final_round = data.get("is_final_round", False)
        self.preliminary_rounds = data.get("preliminary_rounds", PRELIMINARY_ROUNDS)
        self.preliminary_round_duration = data.get("preliminary_round_duration", PRELIMINARY_ROUND_DURATION)
        self.final_round_stocks = data.get("final_round_stocks", FINAL_ROUND_STOCKS)
        self.stocks_per_player = self.final_round_stocks if self.is_final_round else INFINITE_STOCKS
        
        for pid_str, pdata in data["players"].items():
            pid = int(pid_str)
            
            if pid not in self.players:
                self.players[pid] = PlayerData(player_id=pid)
            
            player = self.players[pid]
            player.character_type = pdata["character_type"]
            player.ready = pdata["ready"]
            player.wins = pdata["wins"]
            player.connected = pdata["connected"]
            
            if pdata["character_state"]:
                if player.character is None:
                    char_class = CHARACTER_CLASSES.get(player.character_type, Warrior)
                    player.character = char_class(0, 0, pid)
                player.character.set_state(pdata["character_state"])
