# HUD - in-game informatiescherm.
#
# Toont voor elke speler:
#   - Schadenpercentage (meer % = verder weggeslagen)
#   - Levens (stocks)
#   - Naam en character-type

import pygame

from config import Colors, SCREEN_HEIGHT, SCREEN_WIDTH, FPS


class HUD:

    def __init__(self, screen):
        self.screen = screen
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)

        self.hud_positions = [
            (100, SCREEN_HEIGHT - 80),
            (350, SCREEN_HEIGHT - 80),
            (600, SCREEN_HEIGHT - 80),
            (850, SCREEN_HEIGHT - 80),
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

    def _draw_player_hud(self, character, pos, is_local, game_state):
        x, y = pos
        color = character.color

        box_rect = pygame.Rect(x - 90, y - 52, 180, 112)
        pygame.draw.rect(self.screen, (30, 30, 35), box_rect, border_radius=10)

        border_width = 3 if is_local else 1
        pygame.draw.rect(self.screen, color, box_rect, border_width, border_radius=10)

        name_text = f"P{character.player_id + 1}: {character.get_character_name()}"
        name_surface = self.font_small.render(name_text, True, Colors.WHITE)
        self.screen.blit(name_surface, name_surface.get_rect(center=(x, y - 20)))

        damage_color = self._get_damage_color(character.damage_percent)
        damage_text = f"{int(character.damage_percent)}%"
        damage_surface = self.font_large.render(damage_text, True, damage_color)
        self.screen.blit(damage_surface, damage_surface.get_rect(center=(x, y + 6)))

        coins_text = f"Coins: {self._get_player_coins(character.player_id, game_state)}"
        coins_surface = self.font_small.render(coins_text, True, Colors.YELLOW)
        self.screen.blit(coins_surface, coins_surface.get_rect(center=(x, y + 34)))

        self._draw_stocks(x, y + 56, character.stocks, color)

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

        spacing = 20
        start_x = x - (stocks * spacing) // 2

        for i in range(stocks):
            stock_x = start_x + i * spacing + 10
            pygame.draw.circle(self.screen, color, (stock_x, y), 6)
            pygame.draw.circle(self.screen, Colors.WHITE, (stock_x, y), 6, 1)

    def _draw_match_info(self, game_state):
        if game_state.is_final_round:
            label = f"Final Round | Stocks: {game_state.final_round_stocks}"
        else:
            seconds_left = max(0, (game_state.preliminary_round_duration - game_state.game_timer) // FPS)
            label = (
                f"Round {game_state.round_number}/{game_state.preliminary_rounds}"
                f" | Infinite lives | {seconds_left}s"
            )

        surface = self.font_small.render(label, True, Colors.WHITE)
        self.screen.blit(surface, (20, 20))

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
        controls = "Controls: WASD/Arrows = Move | J = Light | K = Heavy | L = Special | Shift = Dash"
        surface = self.font_small.render(controls, True, Colors.GRAY)
        self.screen.blit(surface, surface.get_rect(center=(SCREEN_WIDTH // 2, 20)))

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
        surface = self.font_medium.render(text, True, Colors.WHITE)
        self.screen.blit(surface, surface.get_rect(center=(SCREEN_WIDTH // 2, 50)))

        hint = self.font_small.render("Press R when ready to start", True, Colors.GRAY)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 80)))
