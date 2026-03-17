"""
Network module - Client-side netwerk communicatie en lobby discovery.
"""

import pickle
import socket
import threading
import time
from typing import Any, Optional, List, Dict

from config import (
    SERVER_IP,
    SERVER_PORT,
    DISCOVERY_PORT,
    BUFFER_SIZE,
    CONNECTION_TIMEOUT,
    DISCOVERY_TIMEOUT,
    DISCOVERY_TOKEN,
)


class Network:

    def __init__(self, server_ip: str = None):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(CONNECTION_TIMEOUT)

        self.server = server_ip or SERVER_IP
        self.port = SERVER_PORT
        self.addr = (self.server, self.port)

        self.player_id: Optional[int] = None
        self.connected = False
        self._lock = threading.Lock()

    def connect(self, password: str) -> bool:
        try:
            self.client.connect(self.addr)
            self.client.sendall(pickle.dumps({
                "type": "join_lobby",
                "data": {"password": password},
            }))

            data = self.client.recv(BUFFER_SIZE)
            response = pickle.loads(data)
            if not response.get("ok"):
                print(response.get("error", "Verbinding geweigerd"))
                self.client.close()
                return False

            self.player_id = response["player_id"]
            self.connected = True
            print(f"Verbonden met server als Player {self.player_id}")
            return True

        except socket.timeout:
            print("Verbinding timeout - server niet bereikbaar")
            return False
        except socket.error as exc:
            print(f"Verbindingsfout: {exc}")
            return False
        except Exception as exc:
            print(f"Onverwachte fout bij verbinden: {exc}")
            return False

    def send(self, data: Any) -> Optional[Any]:
        if not self.connected:
            return None

        with self._lock:
            try:
                self.client.sendall(pickle.dumps(data))
                response = self.client.recv(BUFFER_SIZE)
                return pickle.loads(response)
            except socket.timeout:
                print("Timeout bij communicatie met server")
                return None
            except socket.error as exc:
                print(f"Socket error: {exc}")
                self.connected = False
                return None
            except Exception as exc:
                print(f"Fout bij verzenden: {exc}")
                return None

    def disconnect(self) -> None:
        self.connected = False
        try:
            self.client.close()
        except OSError:
            pass

    def is_connected(self) -> bool:
        return self.connected

    def get_player_id(self) -> Optional[int]:
        return self.player_id


def discover_lobbies(timeout: float = DISCOVERY_TIMEOUT) -> List[Dict[str, Any]]:
    request = {
        "token": DISCOVERY_TOKEN,
        "type": "discover_lobbies",
    }
    discovered = {}

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.2)

    end_time = time.time() + timeout
    try:
        sock.sendto(pickle.dumps(request), ("255.255.255.255", DISCOVERY_PORT))

        while time.time() < end_time:
            try:
                payload, addr = sock.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                continue

            response = pickle.loads(payload)
            if response.get("token") != DISCOVERY_TOKEN:
                continue

            lobby = response.get("lobby")
            if not lobby:
                continue

            lobby["ip"] = lobby.get("ip") or addr[0]
            discovered[lobby["ip"]] = lobby
    except OSError:
        return []
    finally:
        sock.close()

    return sorted(discovered.values(), key=lambda lobby: lobby.get("ip", ""))
