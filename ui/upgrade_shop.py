import pygame

from config import ATTACK_SHOP_ITEMS, BUILD_STAT_NAMES, Colors, SCREEN_HEIGHT, SCREEN_WIDTH
from ui.character_select import STAT_DISPLAY


class StatUpgradeCard:

    def __init__(self, stat_name, x, y, width=520, height=72):
        self.stat_name = stat_name
        self.meta = STAT_DISPLAY[stat_name]
        self.rect = pygame.Rect(x, y, width, height)
        self.button_rect = pygame.Rect(x + width - 88, y + 16, 56, 40)
        self.label_font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button_rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, screen, value, coins):
        next_cost = value + 1
        affordable = coins >= next_cost
        bar_max = max(10, value + 2)

        pygame.draw.rect(screen, (36, 40, 50), self.rect, border_radius=16)
        pygame.draw.rect(screen, (88, 94, 110), self.rect, 2, border_radius=16)

        icon_rect = pygame.Rect(self.rect.left + 16, self.rect.top + 16, 40, 40)
        pygame.draw.rect(screen, self.meta["color"], icon_rect, border_radius=12)

        label = self.label_font.render(self.meta["label"], True, Colors.WHITE)
        screen.blit(label, (self.rect.left + 72, self.rect.top + 12))

        detail = self.small_font.render(f"Level {value} | Next costs {next_cost} coins", True, Colors.LIGHT_GRAY)
        screen.blit(detail, (self.rect.left + 72, self.rect.top + 40))

        bar_rect = pygame.Rect(self.rect.left + 250, self.rect.top + 26, 140, 18)
        pygame.draw.rect(screen, Colors.DARK_GRAY, bar_rect, border_radius=9)
        fill_width = int(bar_rect.width * min(1.0, value / bar_max))
        if fill_width > 0:
            fill_rect = pygame.Rect(bar_rect.left, bar_rect.top, fill_width, bar_rect.height)
            pygame.draw.rect(screen, self.meta["color"], fill_rect, border_radius=9)

        button_color = (92, 168, 112) if affordable else (80, 84, 92)
        pygame.draw.rect(screen, button_color, self.button_rect, border_radius=12)
        pygame.draw.rect(screen, Colors.WHITE, self.button_rect, 2, border_radius=12)
        plus_surface = self.label_font.render("+", True, Colors.WHITE)
        screen.blit(plus_surface, plus_surface.get_rect(center=self.button_rect.center))


class AttackOfferCard:

    def __init__(self, offer, x, y, width=520, height=86):
        self.offer = offer
        self.rect = pygame.Rect(x, y, width, height)
        self.button_rect = pygame.Rect(x + width - 118, y + 20, 92, 46)
        self.title_font = pygame.font.Font(None, 30)
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 22)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button_rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, screen, player):
        owned = self.offer["id"] in player.owned_attack_ids
        equipped = player.equipped_attacks.get(self.offer["slot"]) == self.offer["id"]
        affordable = player.coins >= self.offer["cost"]

        pygame.draw.rect(screen, (36, 40, 50), self.rect, border_radius=16)
        pygame.draw.rect(screen, (88, 94, 110), self.rect, 2, border_radius=16)

        title = self.title_font.render(self.offer["name"], True, Colors.WHITE)
        screen.blit(title, (self.rect.left + 18, self.rect.top + 12))

        meta = f"{self.offer['slot'].title()} | {self.offer['focus']} | {self.offer['cost']} coins"
        meta_surface = self.small_font.render(meta, True, Colors.ORANGE)
        screen.blit(meta_surface, (self.rect.left + 18, self.rect.top + 40))

        description = self.font.render(self.offer["description"], True, Colors.LIGHT_GRAY)
        screen.blit(description, (self.rect.left + 18, self.rect.top + 60))

        if equipped:
            button_text = "Equipped"
            button_color = (74, 140, 98)
        elif owned:
            button_text = "Equip"
            button_color = (74, 106, 152)
        else:
            button_text = "Buy"
            button_color = (184, 118, 54) if affordable else (80, 84, 92)

        pygame.draw.rect(screen, button_color, self.button_rect, border_radius=12)
        pygame.draw.rect(screen, Colors.WHITE, self.button_rect, 2, border_radius=12)
        text_surface = self.font.render(button_text, True, Colors.WHITE)
        screen.blit(text_surface, text_surface.get_rect(center=self.button_rect.center))


class RoundUpgradeShop:

    def __init__(self, screen):
        self.screen = screen
        self.title_font = pygame.font.Font(None, 58)
        self.header_font = pygame.font.Font(None, 34)
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)

        self.stat_cards = []
        self.attack_cards = []
        self._create_cards()

    def _create_cards(self):
        left_x = 56
        right_x = 704
        stat_y = 170
        attack_y = 170
        stat_spacing = 84
        attack_spacing = 94

        self.stat_cards = [
            StatUpgradeCard(stat_name, left_x, stat_y + (index * stat_spacing))
            for index, stat_name in enumerate(BUILD_STAT_NAMES)
        ]
        self.attack_cards = [
            AttackOfferCard(offer, right_x, attack_y + (index * attack_spacing))
            for index, offer in enumerate(ATTACK_SHOP_ITEMS)
        ]

    def handle_event(self, event, player):
        for card in self.stat_cards:
            if card.handle_event(event):
                return {"type": "upgrade_stat", "stat_name": card.stat_name}

        for card in self.attack_cards:
            if not card.handle_event(event):
                continue

            attack_id = card.offer["id"]
            if attack_id in player.owned_attack_ids:
                if player.equipped_attacks.get(card.offer["slot"]) == attack_id:
                    return None
                return {"type": "equip_attack", "attack_id": attack_id}
            return {"type": "buy_attack", "attack_id": attack_id}

        return None

    def draw(self, player, remaining_seconds, current_round, upcoming_round, is_final_round, player_count, ready_count):
        self.screen.fill((26, 29, 36))

        title = self.title_font.render("ROUND UPGRADE SHOP", True, Colors.WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 52)))

        subtitle = self.font.render(
            f"Round {current_round} complete | Next up: Round {upcoming_round}",
            True,
            Colors.LIGHT_GRAY,
        )
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 92)))

        timer_text = self.header_font.render(f"{remaining_seconds}s", True, Colors.ORANGE)
        self.screen.blit(timer_text, timer_text.get_rect(center=(SCREEN_WIDTH // 2, 126)))

        coins_text = self.header_font.render(f"Coins: {player.coins}", True, Colors.YELLOW)
        self.screen.blit(coins_text, (56, 112))

        phase_label = "Final round comes next" if is_final_round else "Spend coins before the next round starts"
        phase_surface = self.small_font.render(phase_label, True, Colors.LIGHT_GRAY)
        self.screen.blit(phase_surface, (704, 116))

        ready_label = self.small_font.render(f"Ready players: {ready_count}/{player_count}", True, Colors.WHITE)
        self.screen.blit(ready_label, ready_label.get_rect(topright=(SCREEN_WIDTH - 56, 26)))

        left_title = self.header_font.render("Stats", True, Colors.WHITE)
        self.screen.blit(left_title, (56, 142))

        right_title = self.header_font.render("Attacks", True, Colors.WHITE)
        self.screen.blit(right_title, (704, 142))

        for card in self.stat_cards:
            card.draw(self.screen, player.build_stats.get(card.stat_name, 0), player.coins)

        for card in self.attack_cards:
            card.draw(self.screen, player)

        if player.ready:
            footer = f"You are ready | Waiting for others: {ready_count}/{player_count}"
            footer_color = Colors.GREEN
        else:
            footer = "Press ENTER when you're done shopping | Stat upgrades cost 1, 2, 3, 4, 5..."
            footer_color = Colors.LIGHT_GRAY

        footer_surface = self.small_font.render(footer, True, footer_color)
        self.screen.blit(footer_surface, footer_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)))

        if player.ready:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 14, 20, 75))
            self.screen.blit(overlay, (0, 0))

            ready_surface = self.header_font.render("READY", True, footer_color)
            self.screen.blit(ready_surface, ready_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 62)))
