# Brawl Arena - Main Client

import argparse
import os
import socket
import subprocess
import sys
import time

import pygame

from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    GAME_TITLE,
    Colors,
    CONTROLS,
    STAGE_PLATFORMS,
    NETWORK_TICK_RATE,
)
from entities.platform import Platform
from game_state import GameState
from network import Network
from systems.collision import CollisionSystem
from systems.effects import EffectsSystem
from ui.character_select import CharacterSelect
from ui.hud import HUD
from ui.menu import MainMenu
from ui.upgrade_shop import RoundUpgradeShop


class Game:

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)

        self.fullscreen = False
        self.screen = None
        self._apply_display_mode()
        self.clock = pygame.time.Clock()
        self.running = True

        self.state = "menu"
        self.network = None
        self.server_process = None
        self.host_ip = ""
        self.is_local = False

        self.game_state = GameState()
        self.local_player_id = None
        self.local_character = None

        self.collision = CollisionSystem()
        self.effects = EffectsSystem()
        self.platforms = [Platform.from_tuple(p) for p in STAGE_PLATFORMS]

        self.menu = MainMenu(self.screen)
        self.hud = HUD(self.screen)
        self.stat_select = CharacterSelect(self.screen)
        self.upgrade_shop = RoundUpgradeShop(self.screen)

        self.camera_offset = (0, 0)
        self.last_network_sync = 0.0
        self.network_sync_interval = 1.0 / max(1, NETWORK_TICK_RATE)

        self.background = self._load_background("assets/backgrounds/homepage background/Templebackground.jpg")
        self.mouse_capture_active = False
        self.pending_network_actions = {
            "jump": False,
            "dash": False,
            "light_attack": False,
            "heavy_attack": False,
            "special_attack": False,
        }

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._render()
            pygame.display.flip()

        self._cleanup()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "playing":
                self.mouse_capture_active = True

            if (
                (hasattr(pygame, "WINDOWFOCUSLOST") and event.type == pygame.WINDOWFOCUSLOST)
                or (
                    event.type == pygame.ACTIVEEVENT
                    and getattr(event, "gain", 1) == 0
                    and getattr(event, "state", 0) != 0
                )
            ):
                self.mouse_capture_active = False

            if event.type == pygame.KEYDOWN and (
                event.key == pygame.K_F11
                or (event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT))
            ):
                self._toggle_fullscreen()
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.fullscreen:
                    self._toggle_fullscreen()
                    continue

                if self.state in ("playing", "round_end", "stat_select", "upgrade_shop"):
                    self._return_to_menu()
                elif self.network:
                    self._return_to_menu()
                else:
                    self.running = False
                return

            if self.state == "menu":
                self._handle_menu_event(event)
            elif self.state == "stat_select":
                self._handle_stat_select_event(event)
            elif self.state == "upgrade_shop":
                self._handle_upgrade_shop_event(event)
            elif self.state == "playing":
                self._handle_game_event(event)
            elif self.state == "round_end":
                pass
            elif self.state == "game_over":
                self._handle_game_over_event(event)

    def _handle_menu_event(self, event):
        self.menu.handle_event(event)
        result = self.menu.update()
        if not result:
            return

        action = result.get("action")
        if action == "host":
            self._start_host()
        elif action == "join":
            self._join_lobby(result["ip"])
        elif action == "local":
            self._start_local_game()
        elif action == "cancel_waiting":
            self._return_to_menu()

    def _handle_stat_select_event(self, event):
        self.stat_select.handle_event(event)

        pending_stats = self.stat_select.consume_pending_stats()
        if pending_stats and self.is_local:
            self.game_state.select_stats(self.local_player_id, pending_stats)
        elif pending_stats and self.network:
            response = self.network.send({
                "type": "set_stats",
                "data": {"stats": pending_stats},
            })
            if response and "game_state" in response:
                self.game_state.from_dict(response["game_state"])
                self._refresh_local_character_ref()

        if self.stat_select.consume_lock_request():
            if self.is_local:
                self.game_state.lock_stats(self.local_player_id)
                self._finalize_local_stat_selection()
            elif self.network:
                response = self.network.send({"type": "lock_stats", "data": {}})
                if response and "game_state" in response:
                    self.game_state.from_dict(response["game_state"])
                    self._refresh_local_character_ref()

    def _handle_game_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.is_local and self.local_character:
            self.local_character.handle_key_down(event.key)
            return

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
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._return_to_menu()

    def _handle_upgrade_shop_event(self, event):
        player = self.game_state.get_player(self.local_player_id) if self.local_player_id is not None else None
        if not player:
            return

        if player.ready:
            return

        action = self.upgrade_shop.handle_event(event, player)
        if not action:
            return

        action_type = action["type"]
        if self.is_local:
            if action_type == "upgrade_stat":
                self.game_state.upgrade_stat(self.local_player_id, action["stat_name"])
            elif action_type == "downgrade_stat":
                self.game_state.downgrade_stat(self.local_player_id, action["stat_name"])
            elif action_type == "buy_attack":
                self.game_state.buy_attack(self.local_player_id, action["attack_id"])
            elif action_type == "equip_attack":
                self.game_state.equip_attack(self.local_player_id, action["attack_id"])
            elif action_type == "ready_for_round":
                self._submit_round_ready()
            self._refresh_local_character_ref()
            return

        if not self.network:
            return

        payload = {"type": action_type, "data": {}}
        if action_type in ("upgrade_stat", "downgrade_stat"):
            payload["data"]["stat_name"] = action["stat_name"]
        elif action_type in ("buy_attack", "equip_attack"):
            payload["data"]["attack_id"] = action["attack_id"]

        response = self.network.send(payload)
        if response and "game_state" in response:
            self.game_state.from_dict(response["game_state"])
            self._refresh_local_character_ref()

    def _update(self):
        if self.state == "menu":
            self.menu.animate()

        if self.network and self.network.is_connected():
            self._sync_with_server()

        if self.is_local and self.state == "stat_select":
            self._update_local_stat_select()
        elif self.is_local and self.state == "upgrade_shop":
            self._update_local_upgrade_shop()
        elif self.is_local and self.state == "round_end":
            self.game_state.update()

        if self.state == "playing":
            self._update_game()

        self._update_screen_from_phase()
        self._update_mouse_visibility()

    def _update_game(self):
        if self.game_state.phase != "playing":
            self.camera_offset = self.effects.update()
            return

        characters = self._get_all_characters()
        if self.is_local:
            if self.local_character:
                keys = pygame.key.get_pressed()
                self.local_character.handle_input(keys)
            for character in characters:
                character.update(self.platforms)
            hit_events = self.collision.update(characters)
            self.game_state.update()
        else:
            hit_events = []

        self.effects.process_hit_events(hit_events)
        self.camera_offset = self.effects.update()

        for char in characters:
            if char and char.is_dashing:
                self.effects.add_trail(char.x, char.y, char.width, char.height, char.color)

    def _render(self):
        if self.state == "menu":
            self.menu.draw()
        elif self.state == "stat_select":
            self._render_stat_select()
        elif self.state == "playing":
            self._render_game()
        elif self.state == "round_end":
            self._render_game()
            self.hud.draw_center_announcement("ROUND ENDED", size=92)
        elif self.state == "upgrade_shop":
            self._render_upgrade_shop()
        elif self.state == "game_over":
            self._render_game()
            self._render_game_over()

    def _load_background(self, path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, path)
        if not os.path.exists(full_path):
            return None

        try:
            image = pygame.image.load(full_path).convert()
        except pygame.error:
            return None

        return pygame.transform.scale(image, (SCREEN_WIDTH, SCREEN_HEIGHT))

    def _apply_display_mode(self):
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        self._refresh_ui_surfaces()

    def _refresh_ui_surfaces(self):
        for component_name in ("menu", "hud", "stat_select", "upgrade_shop"):
            component = getattr(self, component_name, None)
            if component is not None:
                component.screen = self.screen

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._apply_display_mode()

    def _update_mouse_visibility(self):
        if self.state != "playing":
            self.mouse_capture_active = False
            pygame.mouse.set_visible(True)
            return

        hide_mouse = self.mouse_capture_active and pygame.key.get_focused()
        pygame.mouse.set_visible(not hide_mouse)

    def _render_stat_select(self):
        player = self.game_state.get_player(self.local_player_id) if self.local_player_id is not None else None
        if player:
            self.stat_select.sync(player.build_stats, player.stats_locked, self.game_state.stat_point_budget)
        player_count = len(self.game_state.get_connected_players())
        locked_count = sum(1 for player in self.game_state.get_connected_players() if player.stats_locked)
        self.stat_select.draw(self.game_state.get_stat_select_seconds_remaining(), player_count, locked_count)

    def _render_game(self):
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(Colors.BG_COLOR)

        for platform in self.platforms:
            platform.draw(self.screen, self.camera_offset)

        for coin in self.game_state.map_coins:
            coin.draw(self.screen, self.camera_offset)

        self.effects.draw(self.screen, self.camera_offset)

        for character in self._get_all_characters():
            character.draw(self.screen, self.camera_offset)

        self.hud.draw(self._get_all_characters(), self.local_player_id or 0, self.game_state)

    def _render_upgrade_shop(self):
        player = self.game_state.get_player(self.local_player_id) if self.local_player_id is not None else None
        if not player:
            self.screen.fill(Colors.BG_COLOR)
            return

        upcoming_round = self.game_state.round_number + 1
        if self.game_state.pending_round_transition == "final":
            upcoming_round = self.game_state.preliminary_rounds + 1

        self.upgrade_shop.draw(
            player,
            self.game_state.get_upgrade_shop_seconds_remaining(),
            self.game_state.round_number,
            upcoming_round,
            self.game_state.pending_round_transition == "final",
            len(self.game_state.get_connected_players()),
            sum(1 for active_player in self.game_state.get_connected_players() if active_player.ready),
        )

    def _render_game_over(self):
        if self.game_state.winner is not None:
            winner_id = self.game_state.winner
            winner_player = self.game_state.get_player(winner_id)
            winner_color = (
                winner_player.character.color
                if winner_player and winner_player.character
                else Colors.GRAY
            )
            self.hud.draw_winner(f"Player {winner_id + 1}", winner_color)
        else:
            self.hud.draw_winner("DRAW", Colors.GRAY)

    def _get_all_characters(self):
        return self.game_state.get_characters()

    def _start_local_game(self):
        self._disconnect()
        self.is_local = True
        self.local_player_id = 0
        self.game_state.add_player(0)
        self.game_state.start_stat_selection()
        self.stat_select.reset()
        self.state = "stat_select"

    def _update_local_stat_select(self):
        player = self.game_state.get_player(self.local_player_id)
        if player and player.stats_locked:
            self._finalize_local_stat_selection()
            return

        if self.game_state.phase == "stat_select":
            self.game_state.update()
            if self.game_state.phase != "stat_select":
                self._finalize_local_stat_selection()

    def _update_local_upgrade_shop(self):
        if self.game_state.phase == "upgrade_shop":
            self._auto_ready_local_opponents()
            self.game_state.update()
            self._refresh_local_character_ref()

    def _finalize_local_stat_selection(self):
        player = self.game_state.get_player(self.local_player_id)
        if not player:
            return

        if self.game_state.phase != "playing":
            self._add_local_opponent()
            self.game_state.start_game()

        self.local_character = player.character
        self.state = "playing"

    def _add_local_opponent(self):
        opponent_id = 1
        self.game_state.add_player(opponent_id)
        opponent = self.game_state.get_player(opponent_id)
        if not opponent:
            return

        opponent.build_stats = {
            "power": 2,
            "defense": 2,
            "mobility": 2,
            "knockback": 2,
            "range": 2,
        }
        opponent.stats_locked = True

    def _start_host(self):
        self.host_ip = self._get_local_ip()
        if not (self.server_process and self.server_process.poll() is None):
            server_script = os.path.join(os.path.dirname(__file__), "server.py")
            creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            try:
                self.server_process = subprocess.Popen(
                    [sys.executable, server_script],
                    cwd=os.path.dirname(server_script),
                    creationflags=creation_flags,
                )
            except Exception as exc:
                self.menu.set_error(f"Kon server niet starten: {exc}")
                self.server_process = None
                return

        for _ in range(12):
            self.network = Network("127.0.0.1")
            if self.network.connect():
                self.local_player_id = self.network.get_player_id()
                self.menu.set_waiting_view(1, self.host_ip)
                self._sync_with_server(force=True)
                return
            time.sleep(0.25)

        self.menu.set_error("Kon niet verbinden met de lokale lobby.")
        self.network = None

    def _join_lobby(self, ip):
        self.network = Network(ip)
        if self.network.connect():
            self.local_player_id = self.network.get_player_id()
            self.menu.set_waiting_view(len(self.game_state.get_connected_players()), ip)
            self._sync_with_server(force=True)
        else:
            self.menu.set_error("Kon niet joinen. Controleer het IP-adres.")
            self.network = None

    def _update_screen_from_phase(self):
        if self.is_local:
            if self.game_state.phase == "stat_select":
                self.state = "stat_select"
            elif self.game_state.phase == "round_end":
                self.state = "round_end"
            elif self.game_state.phase == "upgrade_shop":
                self.state = "upgrade_shop"
            elif self.game_state.phase == "playing":
                self.state = "playing"
            elif self.game_state.phase == "game_over":
                self.state = "game_over"
            return

        if self.game_state.phase == "stat_select":
            self.state = "stat_select"
        elif self.game_state.phase == "round_end":
            self.state = "round_end"
        elif self.game_state.phase == "upgrade_shop":
            self.state = "upgrade_shop"
        elif self.game_state.phase == "playing":
            self.state = "playing"
        elif self.game_state.phase == "game_over":
            self.state = "game_over"
        elif self.network and self.network.is_connected():
            player_count = len(self.game_state.get_connected_players())
            self.menu.set_waiting_view(player_count, self.host_ip)
            self.state = "menu"

    def _sync_with_server(self, force=False):
        if not self.network:
            return

        now = time.perf_counter()
        if not force and now - self.last_network_sync < self.network_sync_interval:
            return
        self.last_network_sync = now

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
            if input_payload is not None:
                for key in self.pending_network_actions:
                    self.pending_network_actions[key] = False

    def _submit_round_ready(self):
        if self.local_player_id is None:
            return

        if self.is_local:
            self.game_state.set_player_ready(self.local_player_id, True)
            return

        if not self.network:
            return

        response = self.network.send({"type": "ready_for_round", "data": {}})
        if response and "game_state" in response:
            self.game_state.from_dict(response["game_state"])
            self._refresh_local_character_ref()

    def _auto_ready_local_opponents(self):
        for player in self.game_state.get_connected_players():
            if player.player_id == self.local_player_id:
                continue
            if not player.ready:
                self.game_state.set_player_ready(player.player_id, True)

    def _refresh_local_character_ref(self):
        player = self.game_state.get_player(self.local_player_id) if self.local_player_id is not None else None
        self.local_character = player.character if player else None

    def _get_local_ip(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            return ip
        except OSError:
            return "127.0.0.1"

    def _return_to_menu(self):
        self._disconnect()
        self.state = "menu"
        self.menu = MainMenu(self.screen)
        self.menu.state = "mode_select"

    def _disconnect(self):
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
        self.is_local = False
        self.local_player_id = None
        self.local_character = None
        self.host_ip = ""
        for key in self.pending_network_actions:
            self.pending_network_actions[key] = False
        self.last_network_sync = 0.0
        self.stat_select.reset()

    def _cleanup(self):
        self._disconnect()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Brawl Arena - Platform Fighter")
    args = parser.parse_args()
    _ = args

    game = Game()
    game.run()


if __name__ == "__main__":
    main()
