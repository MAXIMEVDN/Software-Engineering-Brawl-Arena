import pygame

from config import Colors, SCREEN_WIDTH, SCREEN_HEIGHT, BUILD_STAT_NAMES, STAT_POINT_BUDGET


STAT_DISPLAY = {
    "power": {"label": "Power", "color": (218, 90, 90)},
    "defense": {"label": "Defense", "color": (92, 178, 118)},
    "mobility": {"label": "Mobility", "color": (98, 148, 226)},
    "knockback": {"label": "Knockback", "color": (230, 168, 74)},
    "range": {"label": "Range", "color": (180, 112, 220)},
}


class StatControl:

    def __init__(self, stat_name, x, y, width=720, height=64):
        self.stat_name = stat_name
        self.meta = STAT_DISPLAY[stat_name]
        self.rect = pygame.Rect(x, y, width, height)
        self.minus_rect = pygame.Rect(x + width - 128, y + 12, 40, 40)
        self.plus_rect = pygame.Rect(x + width - 56, y + 12, 40, 40)
        self.bar_rect = pygame.Rect(x + 200, y + 23, 260, 18)
        self.font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 22)

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None
        if self.minus_rect.collidepoint(event.pos):
            return -1
        if self.plus_rect.collidepoint(event.pos):
            return 1
        return None

    def draw(self, screen, value, max_fill):
        pygame.draw.rect(screen, (36, 40, 50), self.rect, border_radius=14)
        pygame.draw.rect(screen, (86, 92, 110), self.rect, 2, border_radius=14)

        icon_rect = pygame.Rect(self.rect.left + 16, self.rect.top + 12, 40, 40)
        pygame.draw.rect(screen, self.meta["color"], icon_rect, border_radius=10)

        label = self.font.render(self.meta["label"], True, Colors.WHITE)
        screen.blit(label, (self.rect.left + 72, self.rect.top + 10))
        value_text = self.small_font.render(f"{value} pts", True, Colors.LIGHT_GRAY)
        screen.blit(value_text, (self.rect.left + 72, self.rect.top + 34))

        pygame.draw.rect(screen, Colors.DARK_GRAY, self.bar_rect, border_radius=9)
        fill_width = int(self.bar_rect.width * (value / max_fill)) if max_fill > 0 else 0
        fill_rect = pygame.Rect(self.bar_rect.left, self.bar_rect.top, fill_width, self.bar_rect.height)
        pygame.draw.rect(screen, self.meta["color"], fill_rect, border_radius=9)

        for symbol, rect in (("-", self.minus_rect), ("+", self.plus_rect)):
            pygame.draw.rect(screen, (72, 78, 92), rect, border_radius=10)
            pygame.draw.rect(screen, Colors.WHITE, rect, 2, border_radius=10)
            surface = self.font.render(symbol, True, Colors.WHITE)
            screen.blit(surface, surface.get_rect(center=rect.center))


class CharacterSelect:

    def __init__(self, screen):
        self.screen = screen
        self.title_font = pygame.font.Font(None, 64)
        self.font = pygame.font.Font(None, 34)
        self.small_font = pygame.font.Font(None, 24)
        self.controls = []
        self._create_controls()
        self.reset()

    def _create_controls(self):
        start_x = 280
        start_y = 190
        spacing = 78
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

    def sync(self, stats, locked, budget):
        self.local_stats = dict(stats)
        self.points_left = max(0, budget - sum(self.local_stats.values()))
        self.confirmed = locked

    def handle_event(self, event):
        if self.confirmed:
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.lock_requested = True
            return

        for control in self.controls:
            delta = control.handle_event(event)
            if delta is None:
                continue

            stat_name = control.stat_name
            current = self.local_stats[stat_name]

            if delta > 0 and self.points_left > 0:
                self.local_stats[stat_name] = current + 1
                self.points_left -= 1
                self.changed = True
            elif delta < 0 and current > 0:
                self.local_stats[stat_name] = current - 1
                self.points_left += 1
                self.changed = True
            break

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
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 74)))

        timer_text = self.font.render(f"{remaining_seconds}s", True, Colors.ORANGE)
        self.screen.blit(timer_text, timer_text.get_rect(center=(SCREEN_WIDTH // 2, 126)))

        points_text = self.font.render(f"Points left: {self.points_left}", True, Colors.WHITE)
        self.screen.blit(points_text, points_text.get_rect(center=(SCREEN_WIDTH // 2, 154)))

        for control in self.controls:
            control.draw(self.screen, self.local_stats[control.stat_name], STAT_POINT_BUDGET)

        footer = f"Locked players: {locked_count}/{player_count} | ENTER when ready"
        if self.confirmed:
            footer = f"Build locked | Waiting for others: {locked_count}/{player_count}"

        footer_surface = self.small_font.render(footer, True, Colors.LIGHT_GRAY)
        self.screen.blit(footer_surface, footer_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 44)))
