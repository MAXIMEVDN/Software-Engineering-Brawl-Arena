import pygame

from config import ATTACK_SHOP_ITEMS, BUILD_STAT_NAMES, Colors, SCREEN_HEIGHT, SCREEN_WIDTH
from ui.character_select import STAT_DISPLAY, _load_tinted_icon
from ui.title_text import get_ui_font, render_fit_text


def _lighten(color, factor=0.35):
    return tuple(min(255, int(channel + ((255 - channel) * factor))) for channel in color)


class StatUpgradeCard:

    def __init__(self, stat_name, x, y, width=520, height=76):
        self.stat_name = stat_name
        self.meta = STAT_DISPLAY[stat_name]
        self.rect = pygame.Rect(x, y, width, height)
        self.plus_rect = pygame.Rect(x + width - 112, y + 20, 38, 34)
        self.minus_rect = pygame.Rect(x + width - 62, y + 20, 38, 34)
        self.bar_rect = pygame.Rect(x + 250, y + 28, self.plus_rect.left - (x + 250) - 16, 18)
        self.label_font = get_ui_font(22)
        self.small_font = get_ui_font(16)
        self.icon = _load_tinted_icon(self.meta["icon"], self.meta["color"], size=40)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.minus_rect.collidepoint(event.pos):
                return "minus"
            if self.plus_rect.collidepoint(event.pos):
                return "plus"
        return False

    def draw(self, screen, value, added_this_round, coins, selected=False, selected_button=None):
        next_cost = value + 1
        previous_value = max(0, value - added_this_round)
        affordable = coins >= next_cost
        bar_max = max(10, value + 2)

        pygame.draw.rect(screen, (36, 40, 50), self.rect, border_radius=16)
        border_color = Colors.ORANGE if selected else (88, 94, 110)
        pygame.draw.rect(screen, border_color, self.rect, 3 if selected else 2, border_radius=16)

        icon_rect = pygame.Rect(self.rect.left + 16, self.rect.top + 16, 40, 40)
        if self.icon:
            screen.blit(self.icon, icon_rect)
        else:
            pygame.draw.rect(screen, self.meta["color"], icon_rect, border_radius=12)

        label = render_fit_text(self.meta["label"], Colors.WHITE, 150, 22, 14)
        screen.blit(label, (self.rect.left + 72, self.rect.top + 12))

        detail_text = f"Lv {value} | Cost {next_cost}"
        if added_this_round > 0:
            detail_text = f"Lv {previous_value}  +{added_this_round} this round"
        detail = render_fit_text(detail_text, Colors.LIGHT_GRAY, 190, 16, 12)
        screen.blit(detail, (self.rect.left + 72, self.rect.top + 40))

        pygame.draw.rect(screen, Colors.DARK_GRAY, self.bar_rect, border_radius=9)
        base_fill_width = int(self.bar_rect.width * min(1.0, previous_value / bar_max))
        total_fill_width = int(self.bar_rect.width * min(1.0, value / bar_max))
        if total_fill_width > 0:
            total_rect = pygame.Rect(self.bar_rect.left, self.bar_rect.top, total_fill_width, self.bar_rect.height)
            pygame.draw.rect(screen, _lighten(self.meta["color"]), total_rect, border_radius=9)
        if base_fill_width > 0:
            base_rect = pygame.Rect(self.bar_rect.left, self.bar_rect.top, base_fill_width, self.bar_rect.height)
            right_radius = 9 if base_fill_width >= total_fill_width else 0
            pygame.draw.rect(
                screen,
                self.meta["color"],
                base_rect,
                border_top_left_radius=9,
                border_bottom_left_radius=9,
                border_top_right_radius=right_radius,
                border_bottom_right_radius=right_radius,
            )

        minus_enabled = added_this_round > 0
        controls = (
            ("+", self.plus_rect, affordable, "plus"),
            ("-", self.minus_rect, minus_enabled, "minus"),
        )
        for symbol, rect, enabled, button_name in controls:
            button_color = (92, 168, 112) if enabled else (80, 84, 92)
            pygame.draw.rect(screen, button_color, rect, border_radius=12)
            outline = Colors.ORANGE if selected and selected_button == button_name else Colors.WHITE
            pygame.draw.rect(screen, outline, rect, 3 if selected and selected_button == button_name else 2, border_radius=12)
            surface = self.label_font.render(symbol, True, Colors.WHITE)
            screen.blit(surface, surface.get_rect(center=rect.center))


class AttackOfferCard:

    def __init__(self, offer, x, y, width=520, height=86):
        self.offer = offer
        self.rect = pygame.Rect(x, y, width, height)
        self.button_rect = pygame.Rect(x + width - 118, y + 20, 92, 46)
        self.title_font = get_ui_font(20)
        self.font = get_ui_font(15)
        self.small_font = get_ui_font(14)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button_rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, screen, player, selected=False):
        owned = self.offer["id"] in player.owned_attack_ids
        equipped = player.equipped_attacks.get(self.offer["slot"]) == self.offer["id"]
        affordable = player.coins >= self.offer["cost"]

        pygame.draw.rect(screen, (36, 40, 50), self.rect, border_radius=16)
        border_color = Colors.ORANGE if selected else (88, 94, 110)
        pygame.draw.rect(screen, border_color, self.rect, 3 if selected else 2, border_radius=16)

        title = render_fit_text(self.offer["name"], Colors.WHITE, 300, 20, 12)
        screen.blit(title, (self.rect.left + 18, self.rect.top + 12))

        meta = f"{self.offer['slot'].title()} | {self.offer['focus']} | {self.offer['cost']} coins"
        meta_surface = render_fit_text(meta, Colors.ORANGE, 300, 14, 10)
        screen.blit(meta_surface, (self.rect.left + 18, self.rect.top + 40))

        description = render_fit_text(self.offer["description"], Colors.LIGHT_GRAY, 300, 15, 10)
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
        text_surface = render_fit_text(button_text, Colors.WHITE, self.button_rect.width - 8, 15, 11)
        screen.blit(text_surface, text_surface.get_rect(center=self.button_rect.center))


class RoundUpgradeShop:

    def __init__(self, screen):
        self.screen = screen
        self.title_font = get_ui_font(40)
        self.header_font = get_ui_font(22)
        self.font = get_ui_font(18)
        self.small_font = get_ui_font(14)

        self.stat_cards = []
        self.attack_cards = []
        self.ready_rect = pygame.Rect(SCREEN_WIDTH // 2 - 140, SCREEN_HEIGHT - 68, 280, 42)
        self.selected_section = "stats"
        self.selected_stat_index = 0
        self.selected_stat_focus = "plus"
        self.selected_attack_index = 0
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
        if event.type == pygame.MOUSEMOTION:
            self._sync_selection_from_mouse(event.pos)
            return None

        if event.type == pygame.KEYDOWN:
            return self._handle_keyboard_navigation(event, player)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.ready_rect.collidepoint(event.pos):
            self.selected_section = "ready"
            return {"type": "ready_for_round"}

        for card in self.stat_cards:
            action = card.handle_event(event)
            if action == "minus":
                self.selected_section = "stats"
                self.selected_stat_index = self.stat_cards.index(card)
                self.selected_stat_focus = "minus"
                return {"type": "downgrade_stat", "stat_name": card.stat_name}
            if action == "plus":
                self.selected_section = "stats"
                self.selected_stat_index = self.stat_cards.index(card)
                self.selected_stat_focus = "plus"
                return {"type": "upgrade_stat", "stat_name": card.stat_name}

        for card in self.attack_cards:
            if not card.handle_event(event):
                continue
            self.selected_section = "attacks"
            self.selected_attack_index = self.attack_cards.index(card)

            attack_id = card.offer["id"]
            if attack_id in player.owned_attack_ids:
                if player.equipped_attacks.get(card.offer["slot"]) == attack_id:
                    return None
                return {"type": "equip_attack", "attack_id": attack_id}
            return {"type": "buy_attack", "attack_id": attack_id}

        return None

    def _sync_selection_from_mouse(self, mouse_pos):
        if self.ready_rect.collidepoint(mouse_pos):
            self.selected_section = "ready"
            return

        for index, card in enumerate(self.stat_cards):
            if card.minus_rect.collidepoint(mouse_pos):
                self.selected_section = "stats"
                self.selected_stat_index = index
                self.selected_stat_focus = "minus"
                return
            if card.plus_rect.collidepoint(mouse_pos):
                self.selected_section = "stats"
                self.selected_stat_index = index
                self.selected_stat_focus = "plus"
                return
            if card.rect.collidepoint(mouse_pos):
                self.selected_section = "stats"
                self.selected_stat_index = index
                self.selected_stat_focus = "plus"
                return

        for index, card in enumerate(self.attack_cards):
            if card.rect.collidepoint(mouse_pos):
                self.selected_section = "attacks"
                self.selected_attack_index = index
                return

    def _handle_keyboard_navigation(self, event, player):
        if event.key in (pygame.K_w, pygame.K_UP):
            if self.selected_section == "stats":
                if self.selected_stat_index > 0:
                    self.selected_stat_index -= 1
                else:
                    self.selected_section = "ready"
            elif self.selected_section == "attacks":
                if self.selected_attack_index > 0:
                    self.selected_attack_index -= 1
                else:
                    self.selected_section = "stats"
                    self.selected_stat_index = self.selected_attack_index
                    self.selected_stat_focus = "plus"
            elif self.selected_section == "ready":
                self.selected_section = "stats"
                self.selected_stat_index = len(self.stat_cards) - 1
                self.selected_stat_focus = "plus"
            return None

        if event.key in (pygame.K_s, pygame.K_DOWN):
            if self.selected_section == "stats":
                if self.selected_stat_index < len(self.stat_cards) - 1:
                    self.selected_stat_index += 1
                else:
                    self.selected_section = "ready"
            elif self.selected_section == "attacks":
                if self.selected_attack_index < len(self.attack_cards) - 1:
                    self.selected_attack_index += 1
                else:
                    self.selected_section = "ready"
            elif self.selected_section == "ready":
                self.selected_section = "attacks"
                self.selected_attack_index = 0
            return None

        if event.key in (pygame.K_a, pygame.K_LEFT):
            if self.selected_section == "stats":
                if self.selected_stat_focus == "minus":
                    self.selected_stat_focus = "plus"
                else:
                    self.selected_section = "attacks"
                    self.selected_attack_index = self.selected_stat_index
            elif self.selected_section == "attacks":
                self.selected_section = "stats"
                self.selected_stat_index = self.selected_attack_index
                self.selected_stat_focus = "minus"
            elif self.selected_section == "ready":
                self.selected_section = "stats"
                self.selected_stat_index = len(self.stat_cards) - 1
                self.selected_stat_focus = "plus"
            return None

        if event.key in (pygame.K_d, pygame.K_RIGHT):
            if self.selected_section == "stats":
                if self.selected_stat_focus == "plus":
                    self.selected_stat_focus = "minus"
                else:
                    self.selected_section = "attacks"
                    self.selected_attack_index = self.selected_stat_index
            elif self.selected_section == "attacks":
                self.selected_section = "stats"
                self.selected_stat_index = self.selected_attack_index
                self.selected_stat_focus = "plus"
            elif self.selected_section == "ready":
                self.selected_section = "attacks"
                self.selected_attack_index = len(self.attack_cards) - 1
            return None

        if event.key == pygame.K_RETURN:
            if self.selected_section == "stats":
                action_type = "upgrade_stat" if self.selected_stat_focus == "plus" else "downgrade_stat"
                return {"type": action_type, "stat_name": self.stat_cards[self.selected_stat_index].stat_name}
            if self.selected_section == "attacks":
                attack_id = self.attack_cards[self.selected_attack_index].offer["id"]
                if attack_id in player.owned_attack_ids:
                    if player.equipped_attacks.get(self.attack_cards[self.selected_attack_index].offer["slot"]) == attack_id:
                        return None
                    return {"type": "equip_attack", "attack_id": attack_id}
                return {"type": "buy_attack", "attack_id": attack_id}
            if self.selected_section == "ready":
                return {"type": "ready_for_round"}
        return None

    def draw(self, player, remaining_seconds, current_round, upcoming_round, is_final_round, player_count, ready_count):
        self.screen.fill((26, 29, 36))

        title = self.title_font.render("ROUND UPGRADE SHOP", True, Colors.WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 52)))

        subtitle = render_fit_text(
            f"Round {current_round} complete | Next: Round {upcoming_round}",
            Colors.LIGHT_GRAY,
            SCREEN_WIDTH - 120,
            18,
            12,
        )
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 92)))

        timer_text = self.header_font.render(f"{remaining_seconds}s", True, Colors.ORANGE)
        self.screen.blit(timer_text, timer_text.get_rect(center=(SCREEN_WIDTH // 2, 126)))

        coins_text = self.header_font.render(f"Coins: {player.coins}", True, Colors.YELLOW)
        self.screen.blit(coins_text, (56, 112))

        phase_label = "Final round is next" if is_final_round else "Spend coins before the next round"
        phase_surface = render_fit_text(phase_label, Colors.LIGHT_GRAY, 360, 14, 10)
        self.screen.blit(phase_surface, (704, 116))

        ready_label = self.small_font.render(f"Ready players: {ready_count}/{player_count}", True, Colors.WHITE)
        self.screen.blit(ready_label, ready_label.get_rect(topright=(SCREEN_WIDTH - 56, 26)))

        left_title = self.header_font.render("Stats", True, Colors.WHITE)
        self.screen.blit(left_title, (56, 142))

        right_title = self.header_font.render("Attacks", True, Colors.WHITE)
        self.screen.blit(right_title, (704, 142))

        for card in self.stat_cards:
            card.draw(
                self.screen,
                player.build_stats.get(card.stat_name, 0),
                player.round_stat_upgrades.get(card.stat_name, 0),
                player.coins,
                selected=self.selected_section == "stats" and self.stat_cards.index(card) == self.selected_stat_index,
                selected_button=self.selected_stat_focus if self.selected_stat_focus in ("minus", "plus") else None,
            )

        for card in self.attack_cards:
            card.draw(
                self.screen,
                player,
                selected=self.selected_section == "attacks" and self.attack_cards.index(card) == self.selected_attack_index,
            )

        pygame.draw.rect(self.screen, (74, 140, 98), self.ready_rect, border_radius=12)
        ready_border = Colors.ORANGE if self.selected_section == "ready" and not player.ready else Colors.WHITE
        pygame.draw.rect(self.screen, ready_border, self.ready_rect, 3 if self.selected_section == "ready" and not player.ready else 2, border_radius=12)
        ready_label = self.font.render("READY UP", True, Colors.WHITE)
        self.screen.blit(ready_label, ready_label.get_rect(center=self.ready_rect.center))

        if player.ready:
            footer = f"You are ready | Waiting for others: {ready_count}/{player_count}"
            footer_color = Colors.GREEN
        else:
            footer = "W/S move | A/D change | Enter confirm | Mouse also works"
            footer_color = Colors.LIGHT_GRAY

        footer_surface = render_fit_text(footer, footer_color, SCREEN_WIDTH - 80, 14, 10)
        self.screen.blit(footer_surface, footer_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 16)))

        if player.ready:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 14, 20, 75))
            self.screen.blit(overlay, (0, 0))

            ready_surface = self.header_font.render("READY", True, footer_color)
            self.screen.blit(ready_surface, ready_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 62)))
