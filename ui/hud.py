# HUD - in-game informatiescherm.
#
# Toont voor elke speler:
#   - Schadenpercentage (meer % = verder weggeslagen)
#   - Levens (stocks)
#   - Naam en character-type

import pygame

from config import Colors, SCREEN_HEIGHT, SCREEN_WIDTH, FPS
from ui.title_text import draw_title_style_text, get_ui_font, render_fit_text


class HUD:

    def __init__(self, screen):
        self.screen = screen
        self.font_large = get_ui_font(30)
        self.font_medium = get_ui_font(18)
        self.font_small = get_ui_font(14)

        self.hud_positions = [
            (148, SCREEN_HEIGHT - 72),
            (408, SCREEN_HEIGHT - 72),
            (668, SCREEN_HEIGHT - 72),
            (928, SCREEN_HEIGHT - 72),
        ]

    def draw(self, characters, local_player_id=0, game_state=None):
        for i, character in enumerate(characters):
            if i >= len(self.hud_positions):
                break
            pos = self.hud_positions[i]
            is_local = character.player_id == local_player_id
            self._draw_player_hud(character, pos, is_local, game_state)

        self._draw_controls_hint()
        if game_state is not None:
            self._draw_match_info(game_state)
            self._draw_round_end_countdown(game_state)

    def _draw_player_hud(self, character, pos, is_local, game_state):
        x, y = pos
        color = character.color

        box_rect = pygame.Rect(x - 92, y - 48, 184, 96)
        pygame.draw.rect(self.screen, (30, 30, 35), box_rect, border_radius=10)

        border_width = 3 if is_local else 2
        pygame.draw.rect(self.screen, color, box_rect, border_width, border_radius=10)

        name_text = f"P{character.player_id + 1} {character.get_character_name()}"
        name_surface = render_fit_text(name_text, Colors.WHITE, box_rect.width - 18, 16, 12)
        self.screen.blit(name_surface, name_surface.get_rect(center=(x, y - 28)))

        damage_color = self._get_damage_color(character.damage_percent)
        damage_text = f"{int(character.damage_percent)}%"
        damage_surface = self.font_large.render(damage_text, True, damage_color)
        self.screen.blit(damage_surface, damage_surface.get_rect(center=(x, y - 6)))

        coins_text = f"Coins: {self._get_player_coins(character.player_id, game_state)}"
        coins_surface = render_fit_text(coins_text, Colors.YELLOW, box_rect.width - 18, 16, 12)
        self.screen.blit(coins_surface, coins_surface.get_rect(center=(x, y + 20)))

        self._draw_stocks(x, y + 38, character.stocks, color)

    def _get_player_coins(self, player_id, game_state):
        if game_state is None:
            return 0

        player = game_state.get_player(player_id)
        if not player:
            return 0
        return player.coins

    def _draw_stocks(self, x, y, stocks, color):
        if stocks < 0:
            text = self.font_medium.render("INF", True, color)
            self.screen.blit(text, text.get_rect(center=(x, y)))
            return

        spacing = 14
        start_x = x - ((max(stocks, 1) - 1) * spacing) // 2

        for i in range(stocks):
            stock_x = start_x + i * spacing
            pygame.draw.circle(self.screen, color, (stock_x, y), 4)
            pygame.draw.circle(self.screen, Colors.WHITE, (stock_x, y), 4, 1)

    def _draw_match_info(self, game_state):
        if game_state.is_final_round:
            label = f"Final Round | Stocks: {game_state.final_round_stocks}"
        else:
            seconds_left = max(0, (game_state.preliminary_round_duration - game_state.game_timer) // FPS)
            label = (
                f"Round {game_state.round_number}/{game_state.preliminary_rounds}"
                f" | Infinite lives | {seconds_left}s"
            )

        surface = render_fit_text(label, Colors.WHITE, 380, 18, 14)
        self.screen.blit(surface, (18, 42))

    def _draw_round_end_countdown(self, game_state):
        if game_state.phase != "playing" or game_state.is_final_round:
            return

        remaining_frames = max(0, game_state.preliminary_round_duration - game_state.game_timer)
        if remaining_frames <= 0:
            return

        remaining_seconds = (remaining_frames + FPS - 1) // FPS
        if 1 <= remaining_seconds <= 5:
            self.draw_center_announcement(str(remaining_seconds), size=138)

    def _get_damage_color(self, damage):
        if damage < 50:
            return Colors.WHITE
        if damage < 100:
            factor = (damage - 50) / 50
            return (255, 255, int(255 * (1 - factor)))
        if damage < 150:
            factor = (damage - 100) / 50
            return (255, int(255 * (1 - factor)), 0)
        return (255, 50, 50)

    def _draw_controls_hint(self):
        controls = "WASD/Arrows Move  J Light  K Heavy  L Special  Shift Dash"
        surface = render_fit_text(controls, Colors.GRAY, SCREEN_WIDTH - 40, 18, 12)
        self.screen.blit(surface, surface.get_rect(center=(SCREEN_WIDTH // 2, 18)))

    def draw_winner(self, winner_name, winner_color):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        winner_text = f"{winner_name} WINS!"
        winner_surface = self.font_large.render(winner_text, True, winner_color)
        self.screen.blit(
            winner_surface,
            winner_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)),
        )

        hint_surface = self.font_medium.render("Press ESC to return to menu", True, Colors.WHITE)
        self.screen.blit(
            hint_surface,
            hint_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30)),
        )

    def draw_waiting(self, player_count, ready_count):
        text = f"Players: {player_count}/4 | Ready: {ready_count}/{player_count}"
        surface = render_fit_text(text, Colors.WHITE, SCREEN_WIDTH - 40, 22, 14)
        self.screen.blit(surface, surface.get_rect(center=(SCREEN_WIDTH // 2, 50)))

        hint = self.font_small.render("Press R when ready to start", True, Colors.GRAY)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 80)))

    def draw_center_announcement(self, text, size=96):
        draw_title_style_text(
            self.screen,
            text,
            (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2),
            size,
        )
