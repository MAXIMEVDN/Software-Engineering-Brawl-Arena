"""
Game Server - Centrale multiplayer server.
"""

import pickle
import socket
import sys
import threading
import time
from _thread import start_new_thread
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict

from config import (
    BUFFER_SIZE,
    FPS,
    MAX_PLAYERS,
    SERVER_PORT,
)
from game_state import GameState
from systems.collision import CollisionSystem


@dataclass
class PlayerInputState:
    left: bool = False
    right: bool = False
    jump: bool = False
    dash: bool = False
    light_attack: bool = False
    heavy_attack: bool = False
    special_attack: bool = False

    def update_from_payload(self, payload: Dict[str, Any]) -> None:
        self.left = bool(payload.get("left", False))
        self.right = bool(payload.get("right", False))
        self.jump = self.jump or bool(payload.get("jump", False))
        self.dash = self.dash or bool(payload.get("dash", False))
        self.light_attack = self.light_attack or bool(payload.get("light_attack", False))
        self.heavy_attack = self.heavy_attack or bool(payload.get("heavy_attack", False))
        self.special_attack = self.special_attack or bool(payload.get("special_attack", False))

    def consume_for_tick(self) -> Dict[str, bool]:
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

    def __init__(self, ip: str = "", port: int = SERVER_PORT):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.ip = ip
        self.port = port
        self.game_state = GameState()
        self.connections: Dict[int, socket.socket] = {}
        self.input_states: Dict[int, PlayerInputState] = {}
        self.state_lock = Lock()
        self.collision = CollisionSystem()
        self.running = True
        self.tick_interval = 1.0 / FPS

        try:
            self.socket.bind((ip, port))
        except socket.error as exc:
            print(f"Kon niet binden aan port {port}: {exc}")
            sys.exit(1)

        self.socket.listen(MAX_PLAYERS)
        self.game_thread = threading.Thread(target=self._game_loop, daemon=True)

        print(f"Server gestart op port {port}")

    def start(self) -> None:
        self.game_thread.start()

        while self.running:
            try:
                conn, addr = self.socket.accept()
                print(f"Nieuwe verbinding van {addr}")
                player_id = self._perform_handshake(conn)
                if player_id is None:
                    conn.close()
                    continue
                print(f"Speler {player_id} toegelaten tot lobby")
                start_new_thread(self._handle_client, (conn, player_id))
            except socket.error as exc:
                if self.running:
                    print(f"Socket error: {exc}")
                break
            except KeyboardInterrupt:
                break

        self.shutdown()

    def _perform_handshake(self, conn: socket.socket):
        try:
            data = conn.recv(BUFFER_SIZE)
            message = pickle.loads(data)
            if message.get("type") != "join_lobby":
                conn.sendall(pickle.dumps({"ok": False, "error": "Ongeldige lobby handshake"}))
                return None

            with self.state_lock:
                if self.game_state.phase != "lobby":
                    conn.sendall(pickle.dumps({"ok": False, "error": "Lobby accepteert geen nieuwe spelers"}))
                    return None

                player_id = self.game_state.add_player()
                if player_id is None:
                    conn.sendall(pickle.dumps({"ok": False, "error": "Lobby zit vol"}))
                    return None

                if self.game_state.active_player_count() >= 2:
                    self.game_state.start_stat_selection()

                self.connections[player_id] = conn
                self.input_states[player_id] = PlayerInputState()

                conn.sendall(pickle.dumps({
                    "ok": True,
                    "player_id": player_id,
                    "game_state": self.game_state.to_dict(),
                }))

            return player_id
        except Exception as exc:
            print(f"Handshake mislukt: {exc}")
            return None

    def _handle_client(self, conn: socket.socket, player_id: int) -> None:
        while self.running:
            try:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    break

                message = pickle.loads(data)
                response = self._process_message(player_id, message)
                conn.sendall(pickle.dumps(response))
            except socket.error:
                break
            except Exception as exc:
                print(f"Error voor speler {player_id}: {exc}")
                break

        with self.state_lock:
            self.game_state.remove_player(player_id)
            self.connections.pop(player_id, None)
            self.input_states.pop(player_id, None)
            if self.game_state.active_player_count() < 2 and self.game_state.phase == "stat_select":
                self.game_state.phase = "lobby"
                self.game_state.stat_select_remaining_frames = 0

        try:
            conn.close()
        except OSError:
            pass

    def _process_message(self, player_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        msg_type = message.get("type", "")
        data = message.get("data", {})

        with self.state_lock:
            if msg_type == "input":
                self._handle_player_input(player_id, data)
            elif msg_type == "get_state":
                pass
            elif msg_type == "set_stats":
                self.game_state.select_stats(player_id, data.get("stats", {}))
            elif msg_type == "lock_stats":
                self.game_state.lock_stats(player_id)

            return {
                "type": "state",
                "game_state": self.game_state.to_dict(),
            }

    def _handle_player_input(self, player_id: int, input_data: Dict[str, Any]) -> None:
        payload = input_data.get("input_state", {})
        player_input = self.input_states.setdefault(player_id, PlayerInputState())
        player_input.update_from_payload(payload)

    def _game_loop(self) -> None:
        while self.running:
            frame_start = time.perf_counter()

            with self.state_lock:
                if self.game_state.phase == "playing":
                    self._tick_game()
                else:
                    self.game_state.update()

            elapsed = time.perf_counter() - frame_start
            sleep_time = self.tick_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _tick_game(self) -> None:
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

    def shutdown(self) -> None:
        self.running = False
        for conn in list(self.connections.values()):
            try:
                conn.close()
            except OSError:
                pass
        try:
            self.socket.close()
        except OSError:
            pass


def main() -> None:
    port = SERVER_PORT

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        else:
            i += 1

    server = GameServer(port=port)
    server.start()


if __name__ == "__main__":
    main()
