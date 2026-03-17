# Brawl Arena - Main Client

import pygame
import sys
import argparse
import os
import subprocess
import time

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE,
    Colors, CONTROLS, STAGE_PLATFORMS, SPAWN_POSITIONS, NETWORK_TICK_RATE
)
from network import Network
from game_state import GameState, CHARACTER_CLASSES
from entities.platform import Platform
from entities.warrior import Warrior
from entities.mage import Mage
from entities.ninja import Ninja
from systems.collision import CollisionSystem
from systems.effects import EffectsSystem
from ui.menu import MainMenu
from ui.hud import HUD
from ui.character_select import CharacterSelect


class Game:
    # Hoofdklasse van de game.
    # Beheert de game-loop, rendering en state-beheer.

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # Game-state
        self.state = "menu"        # "menu", "char_select", "playing", "game_over"
        self.network = None
        self.is_host = False
        self.is_local = False
        self.server_process = None

        # Lokale game-state
        self.game_state = GameState()
        self.local_player_id = 0
        self.local_character = None
        self.winner = None

        # Systemen
        self.collision = CollisionSystem()
        self.effects = EffectsSystem()

        # Platforms
        self.platforms = [Platform.from_tuple(p) for p in STAGE_PLATFORMS]

        # UI
        self.menu = MainMenu(self.screen)
        self.hud = HUD(self.screen)
        self.char_select = CharacterSelect(self.screen)

        # Camera
        self.camera_offset = (0, 0)
        self.last_network_sync = 0.0
        self.network_sync_interval = 1.0 / max(1, NETWORK_TICK_RATE)

        # Achtergrond
        self.background = self._load_background("assets/backgrounds/background_day.png")

        # Eenmalige acties die nog naar de server gestuurd moeten worden
        self.pending_network_actions = {
            "jump": False,
            "dash": False,
            "light_attack": False,
            "heavy_attack": False,
            "special_attack": False,
        }

    def run(self):
        # Hoofdgame-loop.
        while self.running:
            self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._render()
            pygame.display.flip()

        self._cleanup()

    def _handle_events(self):
        # Verwerk alle pygame-events.
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "playing":
                        self.state = "menu"
                        self._disconnect()
                    else:
                        self.running = False
                    return

            # Stuur het event door naar het juiste scherm
            if self.state == "menu":
                self._handle_menu_event(event)
            elif self.state == "char_select":
                self._handle_char_select_event(event)
            elif self.state == "playing":
                self._handle_game_event(event)
            elif self.state == "game_over":
                self._handle_game_over_event(event)

    def _handle_menu_event(self, event):
        self.menu.handle_event(event)

        result = self.menu.update()
        if result:
            action = result.get("action")
            if action == "quit":
                self.running = False
            elif action == "local":
                self._start_local_game()
            elif action == "host":
                self._start_host()
            elif action == "join":
                self._join_game(result.get("ip"))

    def _handle_char_select_event(self, event):
        self.char_select.handle_event(event)

        selected = self.char_select.get_selected()
        if selected:
            self._on_character_selected(selected)

    def _handle_game_event(self, event):
        if event.type == pygame.KEYDOWN:
            # R-toets = toggle ready (in lobby)
            if event.key == pygame.K_r:
                if self.game_state.phase == "lobby":
                    self._toggle_ready()
                return

            if self.is_local and self.local_character:
                # Lokale modus: stuur keypress direct naar character
                self.local_character.handle_key_down(event.key)
            else:
                # Netwerkmodus: sla eenmalige acties op voor verzending
                if event.key in CONTROLS["jump"]:
                    self.pending_network_actions["jump"] = True
                elif event.key in CONTROLS["dash"]:
                    self.pending_network_actions["dash"] = True
                elif event.key in CONTROLS["light_attack"]:
                    self.pending_network_actions["light_attack"] = True
                elif event.key in CONTROLS["heavy_attack"]:
                    self.pending_network_actions["heavy_attack"] = True
                elif event.key in CONTROLS["special_attack"]:
                    self.pending_network_actions["special_attack"] = True

    def _handle_game_over_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._restart_game()
            elif event.key == pygame.K_ESCAPE:
                self.state = "menu"
                self._disconnect()

    def _update(self):
        # Update het huidige scherm.
        if self.state == "playing":
            self._update_game()

    def _update_game(self):
        # Update de game-logica voor één frame.
        if self.game_state.phase != "playing":
            self.camera_offset = self.effects.update()
            if self.network and self.network.is_connected():
                self._sync_with_server()
            return

        if self.is_local:
            characters = self._get_all_characters()

            # Verwerk ingedrukte toetsen voor de lokale speler
            if self.local_character:
                keys = pygame.key.get_pressed()
                self.local_character.handle_input(keys)

            # Update physics voor alle characters
            for char in characters:
                char.update(self.platforms)

            # Detecteer treffers
            hit_events = self.collision.update(characters)
        else:
            characters = self._get_all_characters()
            hit_events = []

        # Verwerk visual effects (particles, screen shake)
        self.effects.process_hit_events(hit_events)
        self.camera_offset = self.effects.update()

        # Dash-trail effecten
        for char in self._get_all_characters():
            if char and char.is_dashing:
                self.effects.add_trail(char.x, char.y, char.width, char.height, char.color)

        # Laat de gedeelde GameState ook lokaal de rondes/finale beheren.
        if self.is_local:
            self.game_state.update()
            if self.game_state.phase == "game_over":
                self.state = "game_over"
                winner_id = self.game_state.winner
                winner_player = self.game_state.get_player(winner_id) if winner_id is not None else None
                self.winner = winner_player.character if winner_player else None

        # Synchroniseer met de server (netwerkmodus)
        if self.network and self.network.is_connected():
            self._sync_with_server()

    def _get_all_characters(self):
        # Geef alle actieve characters terug.
        if self.is_local:
            return [p.character for p in self.game_state.players.values() if p.character is not None]
        else:
            return self.game_state.get_characters()

    def _render(self):
        # Teken het huidige scherm.
        if self.state == "menu":
            self.menu.draw()
        elif self.state == "char_select":
            self.char_select.draw()
        elif self.state == "playing":
            self._render_game()
        elif self.state == "game_over":
            self._render_game()
            self._render_game_over()

    def _load_background(self, path):
        # Laad de achtergrondafbeelding en schaal deze naar schermgrootte.
        if not os.path.exists(path):
            return None

        try:
            image = pygame.image.load(path).convert()
        except pygame.error:
            return None

        return pygame.transform.scale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))

    def _render_game(self):
        # Teken het speelveld.
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(Colors.BG_COLOR)

        for platform in self.platforms:
            platform.draw(self.screen, self.camera_offset)

        self.effects.draw(self.screen, self.camera_offset)

        for character in self._get_all_characters():
            character.draw(self.screen, self.camera_offset)

        self.hud.draw(self._get_all_characters(), self.local_player_id, self.game_state)

        # Wachtinformatie tonen als de game nog niet begonnen is
        if self.game_state.phase == "lobby":
            connected = len(self.game_state.get_connected_players())
            ready = sum(1 for p in self.game_state.players.values() if p.ready)
            self.hud.draw_waiting(connected, ready)

    def _render_game_over(self):
        # Teken de game-over overlay met de naam van de winnaar.
        if self.game_state.winner is not None:
            winner_id = self.game_state.winner
            winner_player = self.game_state.get_player(winner_id)
            winner_color = (
                winner_player.character.color
                if winner_player and winner_player.character
                else Colors.GRAY
            )
            self.hud.draw_winner(f"Player {winner_id + 1}", winner_color)
        elif hasattr(self, 'winner') and self.winner:
            self.hud.draw_winner(f"Player {self.winner.player_id + 1}", self.winner.color)
        else:
            self.hud.draw_winner("DRAW", Colors.GRAY)


    def _start_local_game(self):
        # Start een lokale testgame (geen netwerk nodig).
        self.is_local = True
        self.is_host = True
        self.winner = None
        self.state = "char_select"

    def _start_host(self):
        # Start als host: start de server en verbind daarna als client.
        if not (self.server_process and self.server_process.poll() is None):
            server_script = os.path.join(os.path.dirname(__file__), "server.py")
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            try:
                self.server_process = subprocess.Popen(
                    [sys.executable, server_script],
                    cwd=os.path.dirname(server_script),
                    creationflags=creation_flags,
                )
                print("Server gestart, verbinden met localhost...")
            except Exception as exc:
                print(f"Kon server niet starten: {exc}")
                self.server_process = None

        # Probeer maximaal 10 keer te verbinden (server heeft even tijd nodig om op te starten)
        for _ in range(10):
            self.network = Network("127.0.0.1")
            if self.network.connect():
                self.local_player_id = self.network.get_player_id()
                self.is_local = False
                self.is_host = True
                self.state = "char_select"
                return
            time.sleep(0.3)

        print("Kon niet verbinden met de lokale server")
        self.network = None

    def _join_game(self, ip):
        # Verbind met een bestaande server.
        self.network = Network(ip)
        if self.network.connect():
            self.local_player_id = self.network.get_player_id()
            self.is_local = False
            self.state = "char_select"
            self._sync_with_server()
        else:
            print("Kon niet verbinden met server")
            self.network = None

    def _on_character_selected(self, character_type):
        # Verwerk de character-keuze.
        self.game_state.add_player(self.local_player_id)
        player = self.game_state.get_player(self.local_player_id)
        player.character_type = character_type

        if self.is_local:
            # Voeg een lokale tegenstander toe voor testing
            self._add_local_opponent(character_type)
            self.game_state.start_game()
            self._refresh_local_character_ref()
        else:
            # Stuur de keuze naar de server
            self.local_character = None
            player.character = None
            response = self.network.send({
                "type": "char_select",
                "data": {"character_type": character_type}
            })
            if response and "game_state" in response:
                self.game_state.from_dict(response["game_state"])
                self._refresh_local_character_ref()

        self.state = "playing"

    def _add_local_opponent(self, local_type):
        # Voeg een tweede speler toe voor lokale testing.
        opponent_id = 1
        spawn = SPAWN_POSITIONS[opponent_id]

        # Kies een ander character-type dan de speler
        all_types = ["Warrior", "Mage", "Ninja"]
        opponent_type = [t for t in all_types if t != local_type][0]

        char_class = CHARACTER_CLASSES.get(opponent_type, Mage)
        opponent = char_class(spawn[0], spawn[1], opponent_id)

        self.game_state.add_player(opponent_id)
        player = self.game_state.get_player(opponent_id)
        player.character = opponent
        player.character_type = opponent_type

    def _toggle_ready(self):
        # Wissel de ready-status van de lokale speler.
        player = self.game_state.get_player(self.local_player_id)
        if player:
            player.ready = not player.ready
            if self.network:
                response = self.network.send({
                    "type": "ready",
                    "data": {"ready": player.ready}
                })
                if response and "game_state" in response:
                    self.game_state.from_dict(response["game_state"])
                    self._refresh_local_character_ref()

    def _restart_game(self):
        # Herstart de game.
        self.winner = None
        if self.is_local:
            self.game_state.start_game()
            self._refresh_local_character_ref()
            self.state = "playing"
            return

        if self.network:
            response = self.network.send({"type": "restart_game", "data": {}})
            if response and "game_state" in response:
                self.game_state.from_dict(response["game_state"])
                self._refresh_local_character_ref()
                self.state = "playing"

    def _sync_with_server(self):
        # Synchroniseer de game-state met de server.
        if not self.network:
            return

        # Stuur niet vaker dan de sync-interval
        now = time.perf_counter()
        if now - self.last_network_sync < self.network_sync_interval:
            return
        self.last_network_sync = now

        # Bouw het te verzenden bericht op
        if self.game_state.phase == "playing":
            keys = pygame.key.get_pressed()
            input_payload = {
                "left": any(keys[k] for k in CONTROLS["left"]),
                "right": any(keys[k] for k in CONTROLS["right"]),
                "jump": self.pending_network_actions["jump"],
                "dash": self.pending_network_actions["dash"],
                "light_attack": self.pending_network_actions["light_attack"],
                "heavy_attack": self.pending_network_actions["heavy_attack"],
                "special_attack": self.pending_network_actions["special_attack"],
            }
            payload = {"type": "input", "data": {"input_state": input_payload}}
        else:
            input_payload = None
            payload = {"type": "get_state", "data": {}}

        response = self.network.send(payload)

        if response and "game_state" in response:
            self.game_state.from_dict(response["game_state"])
            self._refresh_local_character_ref()

            # Wis de eenmalige acties na verzending
            if input_payload is not None:
                for key in self.pending_network_actions:
                    self.pending_network_actions[key] = False

            # Wissel van scherm op basis van de server-state
            if self.game_state.phase == "game_over":
                self.state = "game_over"
            elif self.state == "game_over" and self.game_state.phase == "playing":
                self.state = "playing"
    def _refresh_local_character_ref(self):
        # Zorg dat local_character altijd wijst naar de gesynchroniseerde state.
        player = self.game_state.get_player(self.local_player_id)
        self.local_character = player.character if player else None

    def _disconnect(self):
        # Verbreek de netverkverbinding en reset de state.
        if self.network:
            self.network.disconnect()
            self.network = None

        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
        self.server_process = None

        self.game_state = GameState()
        self.local_character = None
        for key in self.pending_network_actions:
            self.pending_network_actions[key] = False
        self.last_network_sync = 0.0
        self.char_select.reset()
        self.menu = MainMenu(self.screen)

    def _cleanup(self):
        # Ruim alles op bij het afsluiten.
        self._disconnect()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Brawl Arena - Platform Fighter")
    parser.add_argument("--local", action="store_true", help="Start in lokale testmodus")
    parser.add_argument("--ip", type=str, help="Server IP om direct mee te verbinden")
    args = parser.parse_args()

    game = Game()

    if args.local:
        game._start_local_game()
    elif args.ip:
        game._join_game(args.ip)

    game.run()


if __name__ == "__main__":
    main()
