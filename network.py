"""
Network module - Client-side netwerk communicatie.

Dit module bevat de Network class die de verbinding met
de game server beheert.
"""

import socket
import pickle
from typing import Any, Optional
import threading

from config import SERVER_IP, SERVER_PORT, BUFFER_SIZE, CONNECTION_TIMEOUT


class Network:
    """
    Client-side netwerk handler.
    
    Beheert de socket verbinding met de server en
    handelt data verzending/ontvangst af.
    
    Attributes:
        client: Socket object
        server: Server IP adres
        port: Server port
        addr: Server address tuple
        player_id: Toegewezen player ID van server
        connected: Verbindingsstatus
    """
    
    def __init__(self, server_ip: str = None):
        """
        Initialiseer network client.
        
        Args:
            server_ip: IP adres van server (default uit config)
        """
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(CONNECTION_TIMEOUT)
        
        self.server = server_ip or SERVER_IP
        self.port = SERVER_PORT
        self.addr = (self.server, self.port)
        
        self.player_id: Optional[int] = None
        self.connected = False
        self._lock = threading.Lock()
    
    def connect(self) -> bool:
        """
        Verbind met de game server.
        
        Returns:
            True als verbinding succesvol, False anders
        """
        try:
            self.client.connect(self.addr)
            
            # Ontvang player ID van server
            data = self.client.recv(BUFFER_SIZE)
            self.player_id = pickle.loads(data)
            
            self.connected = True
            print(f"Verbonden met server als Player {self.player_id}")
            return True
            
        except socket.timeout:
            print("Verbinding timeout - server niet bereikbaar")
            return False
        except socket.error as e:
            print(f"Verbindingsfout: {e}")
            return False
        except Exception as e:
            print(f"Onverwachte fout bij verbinden: {e}")
            return False
    
    def send(self, data: Any) -> Optional[Any]:
        """
        Stuur data naar server en ontvang response.
        
        Args:
            data: Data om te sturen (wordt gepickled)
            
        Returns:
            Response data van server, of None bij fout
        """
        if not self.connected:
            return None
        
        with self._lock:
            try:
                # Stuur data
                self.client.sendall(pickle.dumps(data))
                
                # Ontvang response
                response = self.client.recv(BUFFER_SIZE)
                return pickle.loads(response)
                
            except socket.timeout:
                print("Timeout bij communicatie met server")
                return None
            except socket.error as e:
                print(f"Socket error: {e}")
                self.connected = False
                return None
            except Exception as e:
                print(f"Fout bij verzenden: {e}")
                return None
    
    def send_no_response(self, data: Any) -> bool:
        """
        Stuur data naar server zonder op response te wachten.
        
        Args:
            data: Data om te sturen
            
        Returns:
            True als verzonden, False bij fout
        """
        if not self.connected:
            return False
        
        with self._lock:
            try:
                self.client.sendall(pickle.dumps(data))
                return True
            except socket.error as e:
                print(f"Fout bij verzenden: {e}")
                self.connected = False
                return False
    
    def receive(self) -> Optional[Any]:
        """
        Ontvang data van server (blocking).
        
        Returns:
            Ontvangen data, of None bij fout
        """
        if not self.connected:
            return None
        
        try:
            data = self.client.recv(BUFFER_SIZE)
            if data:
                return pickle.loads(data)
            return None
        except socket.timeout:
            return None
        except socket.error as e:
            print(f"Fout bij ontvangen: {e}")
            self.connected = False
            return None
    
    def disconnect(self) -> None:
        """Verbreek verbinding met server."""
        self.connected = False
        try:
            self.client.close()
        except:
            pass
        print("Verbinding met server verbroken")
    
    def is_connected(self) -> bool:
        """
        Check of verbinding actief is.
        
        Returns:
            True als verbonden
        """
        return self.connected
    
    def get_player_id(self) -> Optional[int]:
        """
        Haal player ID op.
        
        Returns:
            Player ID of None als niet verbonden
        """
        return self.player_id


class NetworkMessage:
    """
    Helper class voor netwerk berichten.
    
    Standaardiseert het formaat van berichten tussen
    client en server.
    """
    
    # Message types
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PLAYER_INPUT = "input"
    GAME_STATE = "state"
    CHARACTER_SELECT = "char_select"
    READY = "ready"
    CHAT = "chat"
    
    def __init__(self, msg_type: str, data: Any = None, player_id: int = None):
        """
        Maak een nieuw netwerk bericht.
        
        Args:
            msg_type: Type bericht
            data: Bericht data
            player_id: Afzender ID
        """
        self.type = msg_type
        self.data = data
        self.player_id = player_id
    
    def to_dict(self) -> dict:
        """Converteer naar dictionary."""
        return {
            "type": self.type,
            "data": self.data,
            "player_id": self.player_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'NetworkMessage':
        """Maak bericht van dictionary."""
        return cls(
            msg_type=data["type"],
            data=data.get("data"),
            player_id=data.get("player_id"),
        )
