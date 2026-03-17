"""
Network module - Client-side netwerk communicatie.
"""

import pickle
import socket
import threading
from typing import Any, Optional

from config import SERVER_IP, SERVER_PORT, BUFFER_SIZE, CONNECTION_TIMEOUT


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

    def connect(self) -> bool:
        try:
            self.client.connect(self.addr)
            self.client.sendall(pickle.dumps({"type": "join_lobby", "data": {}}))

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
