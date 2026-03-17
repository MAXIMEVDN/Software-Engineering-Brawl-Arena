import pygame

from config import Colors, SCREEN_WIDTH, SCREEN_HEIGHT, BUILD_STAT_NAMES, STAT_POINT_BUDGET
from ui.title_text import get_ui_font, render_fit_text


STAT_DISPLAY = {
    "power": {"label": "Power", "color": (218, 90, 90)},
    "defense": {"label": "Defense", "color": (92, 178, 118)},
    "mobility": {"label": "Mobility", "color": (98, 148, 226)},
    "knockback": {"label": "Knockback", "color": (230, 168, 74)},
    "range": {"label": "Range", "color": (180, 112, 220)},
}


class StatControl:

    def __init__(self, stat_name, x, y, width=970, height=82):
        self.stat_name = stat_name
        self.meta = STAT_DISPLAY[stat_name]
        self.rect = pygame.Rect(x, y, width, height)
        self.plus_rect = pygame.Rect(x + width - 150, y + 14, 54, 54)
        self.minus_rect = pygame.Rect(x + width - 78, y + 14, 54, 54)
        self.bar_rect = pygame.Rect(x + 380, y + 32, 370, 18)
        self.font = get_ui_font(24)
        self.small_font = get_ui_font(16)

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        if self.minus_rect.collidepoint(event.pos):
            return -1
        if self.plus_rect.collidepoint(event.pos):
            return 1
        return None

    def draw(self, screen, value, max_fill, selected=False, selected_button="plus"):
        pygame.draw.rect(screen, (36, 40, 50), self.rect, border_radius=14)
        border_color = Colors.ORANGE if selected else (86, 92, 110)
        pygame.draw.rect(screen, border_color, self.rect, 3 if selected else 2, border_radius=14)

        icon_rect = pygame.Rect(self.rect.left + 20, self.rect.top + 16, 48, 48)
        pygame.draw.rect(screen, self.meta["color"], icon_rect, border_radius=10)

        label = render_fit_text(self.meta["label"], Colors.WHITE, 240, 24, 16)
        screen.blit(label, (self.rect.left + 98, self.rect.top + 14))
        value_text = self.small_font.render(f"{value} pts", True, Colors.LIGHT_GRAY)
        screen.blit(value_text, (self.rect.left + 98, self.rect.top + 46))

        pygame.draw.rect(screen, Colors.DARK_GRAY, self.bar_rect, border_radius=9)
        fill_width = int(self.bar_rect.width * (value / max_fill)) if max_fill > 0 else 0
        if fill_width > 0:
            fill_rect = pygame.Rect(self.bar_rect.left, self.bar_rect.top, fill_width, self.bar_rect.height)
            pygame.draw.rect(screen, self.meta["color"], fill_rect, border_radius=9)

        for symbol, rect, button_name in (("+", self.plus_rect, "plus"), ("-", self.minus_rect, "minus")):
            pygame.draw.rect(screen, (72, 78, 92), rect, border_radius=10)
            outline = Colors.ORANGE if selected and selected_button == button_name else Colors.WHITE
            pygame.draw.rect(screen, outline, rect, 3 if selected and selected_button == button_name else 2, border_radius=10)
            surface = self.font.render(symbol, True, Colors.WHITE)
            screen.blit(surface, surface.get_rect(center=rect.center))


class CharacterSelect:

    def __init__(self, screen):
        self.screen = screen
        self.title_font = get_ui_font(52)
        self.font = get_ui_font(24)
        self.small_font = get_ui_font(16)
        self.ready_rect = pygame.Rect(SCREEN_WIDTH // 2 - 132, SCREEN_HEIGHT - 112, 264, 38)
        self.controls = []
        self._create_controls()
        self.reset()

    def _create_controls(self):
        start_x = 155
        start_y = 150
        spacing = 84
        self.controls = [
            StatControl(stat_name, start_x, start_y + (index * spacing))
            for index, stat_name in enumerate(BUILD_STAT_NAMES)
        ]

    def reset(self):
        self.local_stats = {stat_name: 0 for stat_name in BUILD_STAT_NAMES}
        self.points_left = STAT_POINT_BUDGET
        self.confirmed = False
        self.lock_requested = False
        self.changed = False
        self.selected_index = 0
        self.selected_button = "plus"
        self.selected_section = "stats"

    def sync(self, stats, locked, budget):
        self.local_stats = dict(stats)
        self.points_left = max(0, budget - sum(self.local_stats.values()))
        self.confirmed = locked

    def handle_event(self, event):
        if self.confirmed:
            return

        if event.type == pygame.MOUSEMOTION:
            self._sync_selection_from_mouse(event.pos)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.ready_rect.collidepoint(event.pos):
            self.selected_section = "ready"
            self.lock_requested = True
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_w, pygame.K_UP):
                if self.selected_section == "ready":
                    self.selected_section = "stats"
                    self.selected_index = len(self.controls) - 1
                else:
                    self.selected_index = (self.selected_index - 1) % len(self.controls)
                return
            if event.key in (pygame.K_s, pygame.K_DOWN):
                if self.selected_section == "stats" and self.selected_index == len(self.controls) - 1:
                    self.selected_section = "ready"
                elif self.selected_section == "stats":
                    self.selected_index = (self.selected_index + 1) % len(self.controls)
                else:
                    self.selected_section = "stats"
                    self.selected_index = 0
                return
            if event.key in (pygame.K_a, pygame.K_LEFT):
                if self.selected_section == "stats":
                    self.selected_button = "plus"
                return
            if event.key in (pygame.K_d, pygame.K_RIGHT):
                if self.selected_section == "stats":
                    self.selected_button = "minus"
                return
            if event.key == pygame.K_RETURN:
                if self.selected_section == "ready":
                    self.lock_requested = True
                else:
                    delta = 1 if self.selected_button == "plus" else -1
                    self._apply_delta(self.controls[self.selected_index].stat_name, delta)
                return

        for control in self.controls:
            delta = control.handle_event(event)
            if delta is None:
                continue

            self.selected_index = self.controls.index(control)
            self.selected_section = "stats"
            self.selected_button = "plus" if delta > 0 else "minus"
            self._apply_delta(control.stat_name, delta)
            break

    def _sync_selection_from_mouse(self, mouse_pos):
        if self.ready_rect.collidepoint(mouse_pos):
            self.selected_section = "ready"
            return

        for index, control in enumerate(self.controls):
            if control.minus_rect.collidepoint(mouse_pos):
                self.selected_section = "stats"
                self.selected_index = index
                self.selected_button = "minus"
                return
            if control.plus_rect.collidepoint(mouse_pos):
                self.selected_section = "stats"
                self.selected_index = index
                self.selected_button = "plus"
                return
            if control.rect.collidepoint(mouse_pos):
                self.selected_section = "stats"
                self.selected_index = index
                return

    def _apply_delta(self, stat_name, delta):
        current = self.local_stats[stat_name]
        if delta > 0 and self.points_left > 0:
            self.local_stats[stat_name] = current + 1
            self.points_left -= 1
            self.changed = True
        elif delta < 0 and current > 0:
            self.local_stats[stat_name] = current - 1
            self.points_left += 1
            self.changed = True

    def consume_pending_stats(self):
        if not self.changed:
            return None
        self.changed = False
        return dict(self.local_stats)

    def consume_lock_request(self):
        if not self.lock_requested:
            return False
        self.lock_requested = False
        return True

    def draw(self, remaining_seconds, player_count, locked_count):
        self.screen.fill(Colors.BG_COLOR)

        title = self.title_font.render("BUILD YOUR FIGHTER", True, Colors.WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 56)))

        timer_text = self.font.render(f"{remaining_seconds}s", True, Colors.ORANGE)
        self.screen.blit(timer_text, timer_text.get_rect(center=(SCREEN_WIDTH // 2, 102)))

        points_text = self.font.render(f"Points left: {self.points_left}", True, Colors.WHITE)
        self.screen.blit(points_text, points_text.get_rect(center=(SCREEN_WIDTH // 2, 132)))

        for control in self.controls:
            control.draw(
                self.screen,
                self.local_stats[control.stat_name],
                STAT_POINT_BUDGET,
                selected=not self.confirmed and self.selected_section == "stats" and self.controls.index(control) == self.selected_index,
                selected_button=self.selected_button,
            )

        ready_color = (74, 140, 98) if not self.confirmed else (56, 90, 66)
        pygame.draw.rect(self.screen, ready_color, self.ready_rect, border_radius=12)
        ready_outline = Colors.ORANGE if self.selected_section == "ready" and not self.confirmed else Colors.WHITE
        pygame.draw.rect(self.screen, ready_outline, self.ready_rect, 3 if self.selected_section == "ready" and not self.confirmed else 2, border_radius=12)
        ready_surface = self.small_font.render("READY", True, Colors.WHITE)
        self.screen.blit(ready_surface, ready_surface.get_rect(center=self.ready_rect.center))

        footer = f"Ready: {locked_count}/{player_count}"
        hint = "W/S move | A/D choose minus-plus | Enter apply or ready"
        if self.confirmed:
            footer = f"Ready: {locked_count}/{player_count}"
            hint = "Build locked, waiting for the others"

        footer_surface = self.small_font.render(footer, True, Colors.LIGHT_GRAY)
        self.screen.blit(footer_surface, footer_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50)))
        hint_surface = self.small_font.render(hint, True, Colors.LIGHT_GRAY)
        self.screen.blit(hint_surface, hint_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 28)))
