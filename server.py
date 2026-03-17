"""
Game Server - Centrale multiplayer server.

Dit script draait de game server die meerdere clients
kan accepteren en de game state synchroniseert.

Usage:
    python server.py
    
De server print het IP-adres dat clients moeten gebruiken.
"""

import socket
from _thread import start_new_thread
import pickle
import sys
from typing import Dict, Any
from threading import Lock
from dataclasses import dataclass
import threading
import time

from game_state import GameState
from config import SERVER_PORT, BUFFER_SIZE, MAX_PLAYERS, FPS
from systems.collision import CollisionSystem


@dataclass
class PlayerInputState:
    """Laatst bekende input van een speler."""
    left: bool = False
    right: bool = False
    jump: bool = False
    dash: bool = False
    light_attack: bool = False
    heavy_attack: bool = False
    special_attack: bool = False
    
    def update_from_payload(self, payload: Dict[str, Any]) -> None:
        """Werk held inputs bij en latch one-shot actions tot de volgende tick."""
        self.left = bool(payload.get("left", False))
        self.right = bool(payload.get("right", False))
        self.jump = self.jump or bool(payload.get("jump", False))
        self.dash = self.dash or bool(payload.get("dash", False))
        self.light_attack = self.light_attack or bool(payload.get("light_attack", False))
        self.heavy_attack = self.heavy_attack or bool(payload.get("heavy_attack", False))
        self.special_attack = self.special_attack or bool(payload.get("special_attack", False))
    
    def consume_for_tick(self) -> Dict[str, bool]:
        """Geef huidige input voor een frame terug en clear one-shot actions."""
        current = {
            "left": self.left,
            "right": self.right,
            "jump": self.jump,
            "dash": self.dash,
            "light_attack": self.light_attack,
            "heavy_attack": self.heavy_attack,
            "special_attack": self.special_attack,
        }
        self.jump = False
        self.dash = False
        self.light_attack = False
        self.heavy_attack = False
        self.special_attack = False
        return current


class GameServer:
    """
    Multiplayer game server.
    
    Accepteert client verbindingen en synchroniseert
    de game state tussen alle spelers.
    
    Attributes:
        socket: Server socket
        game_state: De gedeelde game state
        player_count: Aantal verbonden spelers
        connections: Dictionary van player_id -> connection
    """
    
    def __init__(self, ip: str = "", port: int = SERVER_PORT):
        """
        Initialiseer de server.
        
        Args:
            ip: IP om op te luisteren ("" voor alle interfaces)
            port: Port nummer
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.ip = ip
        self.port = port
        self.game_state = GameState()
        self.player_count = 0
        self.connections: Dict[int, socket.socket] = {}
        self.state_lock = Lock()
        self.collision = CollisionSystem()
        self.input_states: Dict[int, PlayerInputState] = {}
        self.running = True
        self.tick_interval = 1.0 / FPS
        
        try:
            self.socket.bind((ip, port))
        except socket.error as e:
            print(f"Kon niet binden aan port {port}: {e}")
            sys.exit(1)
        
        self.socket.listen(MAX_PLAYERS)
        print(f"Server gestart op port {port}")
        print(f"Wacht op verbindingen...")
        print(f"\n{'='*50}")
        print(f"Deel dit IP-adres met andere spelers:")
        print(f"  {self._get_local_ip()}")
        print(f"{'='*50}\n")
    
    def _get_local_ip(self) -> str:
        """
        Haal het lokale IP-adres op.
        
        Returns:
            Lokaal IP-adres als string
        """
        try:
            # Maak een dummy verbinding om lokaal IP te vinden
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
    
    def start(self) -> None:
        """Start de server en accepteer verbindingen."""
        print("Server luistert naar verbindingen...")
        threading.Thread(target=self._game_loop, daemon=True).start()
        
        while True:
            try:
                conn, addr = self.socket.accept()
                print(f"\nNieuwe verbinding van {addr}")
                
                # Wijs player ID toe
                player_id = self.player_count
                self.player_count += 1
                self.connections[player_id] = conn
                
                # Voeg speler toe aan game state
                if self.game_state.add_player(player_id):
                    print(f"Speler {player_id} toegevoegd aan game")
                else:
                    print(f"Kon speler {player_id} niet toevoegen (vol?)")
                self.input_states[player_id] = PlayerInputState()
                
                # Stuur player ID naar client
                conn.sendall(pickle.dumps(player_id))
                
                # Start thread voor deze client
                start_new_thread(self._handle_client, (conn, player_id))
                
            except socket.error as e:
                print(f"Socket error: {e}")
                break
            except KeyboardInterrupt:
                print("\nServer gestopt")
                break
        
        self.shutdown()
    
    def _handle_client(self, conn: socket.socket, player_id: int) -> None:
        """
        Handle communicatie met een client.
        
        Args:
            conn: Socket verbinding
            player_id: ID van deze speler
        """
        print(f"Thread gestart voor speler {player_id}")
        
        while True:
            try:
                # Ontvang data van client
                data = conn.recv(BUFFER_SIZE)
                
                if not data:
                    print(f"Speler {player_id} heeft verbinding verbroken")
                    break
                
                # Verwerk het bericht
                message = pickle.loads(data)
                response = self._process_message(player_id, message)
                
                # Stuur response terug
                conn.sendall(pickle.dumps(response))
                
            except socket.error as e:
                print(f"Socket error voor speler {player_id}: {e}")
                break
            except Exception as e:
                print(f"Error voor speler {player_id}: {e}")
                break
        
        # Cleanup
        print(f"Speler {player_id} verwijderen...")
        with self.state_lock:
            self.game_state.remove_player(player_id)
            if player_id in self.connections:
                del self.connections[player_id]
            if player_id in self.input_states:
                del self.input_states[player_id]
        conn.close()
    
    def _process_message(self, player_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verwerk een bericht van een client.
        
        Args:
            player_id: ID van afzender
            message: Het bericht
            
        Returns:
            Response dictionary
        """
        msg_type = message.get("type", "")
        data = message.get("data", {})
        
        with self.state_lock:
            if msg_type == "input":
                # Bewaar laatste input van client; de game loop verwerkt dit.
                self._handle_player_input(player_id, data)
                
            elif msg_type == "char_select":
                # Character selectie
                char_type = data.get("character_type", "Warrior")
                self.game_state.select_character(player_id, char_type)
                
            elif msg_type == "ready":
                # Player ready toggle
                ready = data.get("ready", True)
                self.game_state.set_player_ready(player_id, ready)
                
                # Check of game kan starten
                if self.game_state.all_players_ready():
                    self.game_state.start_game()
                    print("Game gestart!")
                    
            elif msg_type == "get_state":
                # Client vraagt huidige state op
                pass
            
            return {
                "type": "state",
                "game_state": self.game_state.to_dict(),
            }
    
    def _handle_player_input(self, player_id: int, input_data: Dict[str, Any]) -> None:
        """
        Verwerk input van een speler.
        
        Args:
            player_id: Speler ID
            input_data: Input data (keys, actions)
        """
        payload = input_data.get("input_state", {})
        player_input = self.input_states.setdefault(player_id, PlayerInputState())
        player_input.update_from_payload(payload)
    
    def _game_loop(self) -> None:
        """Draai de game simulation op een vaste tick rate."""
        while self.running:
            frame_start = time.perf_counter()
            
            with self.state_lock:
                if self.game_state.phase == "playing":
                    self._tick_game()
            
            elapsed = time.perf_counter() - frame_start
            sleep_time = self.tick_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _tick_game(self) -> None:
        """Voer één server-authoritative game tick uit."""
        for player_id, player in self.game_state.players.items():
            if not player.connected or not player.character:
                continue
            
            input_state = self.input_states.setdefault(player_id, PlayerInputState())
            player.character.apply_input_state(input_state.consume_for_tick())
        
        characters = self.game_state.get_characters()
        for character in characters:
            character.update(self.game_state.platforms)
        
        self.collision.update(characters)
        self.game_state.update()
    
    def broadcast(self, message: Dict[str, Any], exclude: int = None) -> None:
        """
        Stuur bericht naar alle verbonden clients.
        
        Args:
            message: Bericht om te sturen
            exclude: Player ID om uit te sluiten (optioneel)
        """
        data = pickle.dumps(message)
        
        for player_id, conn in list(self.connections.items()):
            if player_id == exclude:
                continue
            try:
                conn.sendall(data)
            except socket.error:
                print(f"Kon niet naar speler {player_id} sturen")
    
    def shutdown(self) -> None:
        """Sluit de server netjes af."""
        print("Server afsluiten...")
        self.running = False
        
        for conn in self.connections.values():
            try:
                conn.close()
            except:
                pass
        
        self.socket.close()
        print("Server afgesloten")


def main():
    """Start de game server."""
    print("="*50)
    print("  BRAWL ARENA - Game Server")
    print("="*50)
    print()
    
    # Optioneel: custom port via command line
    port = SERVER_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Ongeldige port: {sys.argv[1]}")
            sys.exit(1)
    
    server = GameServer(port=port)
    server.start()


if __name__ == "__main__":
    main()
