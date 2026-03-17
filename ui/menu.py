import pygame

from config import Colors, SCREEN_WIDTH, SCREEN_HEIGHT


class Button:

    def __init__(self, x, y, width, height, text, callback=None, font_size=32):
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.text = text
        self.callback = callback
        self.hovered = False
        self.font = pygame.font.Font(None, font_size)
        self.color_normal = (70, 80, 90)
        self.color_hover = (105, 120, 145)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered:
            if self.callback:
                self.callback()
            return True
        return False

    def draw(self, screen):
        color = self.color_hover if self.hovered else self.color_normal
        pygame.draw.rect(screen, color, self.rect, border_radius=12)
        pygame.draw.rect(screen, Colors.WHITE, self.rect, 2, border_radius=12)
        text_surface = self.font.render(self.text, True, Colors.WHITE)
        screen.blit(text_surface, text_surface.get_rect(center=self.rect.center))


class TextInput:

    def __init__(self, x, y, width, height, placeholder="", font_size=28):
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.text = ""
        self.placeholder = placeholder
        self.active = False
        self.font = pygame.font.Font(None, font_size)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            elif event.unicode.isprintable():
                self.text += event.unicode

    def draw(self, screen):
        border_color = Colors.WHITE if self.active else Colors.GRAY
        pygame.draw.rect(screen, (32, 36, 44), self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        value = self.text if self.text else self.placeholder
        color = Colors.WHITE if self.text else Colors.GRAY
        surface = self.font.render(value, True, color)
        screen.blit(surface, surface.get_rect(midleft=(self.rect.left + 12, self.rect.centery)))


class MainMenu:

    def __init__(self, screen):
        self.screen = screen
        self.state = "welcome"
        self.result = None
        self.error_message = ""
        self.info_message = ""

        self.title_font = pygame.font.Font(None, 88)
        self.subtitle_font = pygame.font.Font(None, 36)
        self.body_font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)

        self.join_ip_input = TextInput(SCREEN_WIDTH // 2, 360, 360, 48, "Host IP (bijv. 192.168.1.42)")

        self._create_buttons()

    def _create_buttons(self):
        center_x = SCREEN_WIDTH // 2
        self.mode_buttons = [
            Button(center_x, 330, 260, 56, "Host Game", self._show_host_setup),
            Button(center_x, 408, 260, 56, "Join Game", self._show_join_setup),
            Button(center_x, 486, 260, 56, "Local Game", self._on_local_game),
        ]

        self.host_buttons = [
            Button(center_x, 390, 240, 52, "Start Host", self._on_create_lobby),
            Button(center_x, 458, 180, 44, "Back", self._on_back_to_mode),
        ]

        self.join_buttons = [
            Button(center_x, 480, 220, 48, "Join Lobby", self._on_join_lobby),
            Button(center_x, 542, 180, 40, "Back", self._on_back_to_mode),
        ]

        self.wait_buttons = [
            Button(center_x, 610, 180, 44, "Cancel", self._on_cancel_waiting),
        ]

    def _show_host_setup(self):
        self.state = "host_setup"
        self.result = None
        self.error_message = ""

    def _show_join_setup(self):
        self.state = "join_setup"
        self.result = None
        self.error_message = ""

    def _on_back_to_mode(self):
        self.state = "mode_select"
        self.result = None
        self.error_message = ""
        self.info_message = ""

    def _on_create_lobby(self):
        self.result = {"action": "host"}

    def _on_join_lobby(self):
        ip = self.join_ip_input.text.strip()
        if not ip:
            self.error_message = "Voer het host IP in."
            return
        self.result = {"action": "join", "ip": ip}

    def _on_local_game(self):
        self.result = {"action": "local"}

    def _on_cancel_waiting(self):
        self.result = {"action": "cancel_waiting"}

    def set_waiting_view(self, player_count, host_ip=""):
        self.state = "host_waiting"
        ip_part = f" | IP: {host_ip}" if host_ip else ""
        self.info_message = f"Lobby live{ip_part} | Players: {player_count}/4"
        self.result = None

    def set_error(self, message):
        self.error_message = message

    def handle_event(self, event):
        if self.state == "welcome":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.state = "mode_select"
        elif self.state == "mode_select":
            for button in self.mode_buttons:
                button.handle_event(event)
        elif self.state == "host_setup":
            for button in self.host_buttons:
                button.handle_event(event)
        elif self.state == "join_setup":
            self.join_ip_input.handle_event(event)
            for button in self.join_buttons:
                button.handle_event(event)
        elif self.state == "host_waiting":
            for button in self.wait_buttons:
                button.handle_event(event)

    def update(self):
        result = self.result
        self.result = None
        return result

    def draw(self):
        self.screen.fill(Colors.BG_COLOR)
        self._draw_background_panels()

        title = self.title_font.render("BRAWL ARENA", True, Colors.WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 110)))

        if self.state == "welcome":
            self._draw_welcome()
        elif self.state == "mode_select":
            self._draw_mode_select()
        elif self.state == "host_setup":
            self._draw_host_setup()
        elif self.state == "join_setup":
            self._draw_join_setup()
        elif self.state == "host_waiting":
            self._draw_host_waiting()

        if self.error_message:
            surface = self.body_font.render(self.error_message, True, Colors.RED)
            self.screen.blit(surface, surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 32)))

    def _draw_background_panels(self):
        panel = pygame.Rect(140, 170, SCREEN_WIDTH - 280, SCREEN_HEIGHT - 240)
        pygame.draw.rect(self.screen, (28, 32, 40), panel, border_radius=24)
        pygame.draw.rect(self.screen, (72, 78, 95), panel, 2, border_radius=24)

    def _draw_welcome(self):
        subtitle = self.subtitle_font.render("Een snelle arena fighter voor jullie lobby", True, Colors.LIGHT_GRAY)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 250)))
        prompt = self.body_font.render("Press ENTER to start", True, Colors.WHITE)
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, 420)))

    def _draw_mode_select(self):
        subtitle = self.subtitle_font.render("Kies hoe je de lobby wilt openen", True, Colors.LIGHT_GRAY)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 250)))
        for button in self.mode_buttons:
            button.draw(self.screen)

    def _draw_host_setup(self):
        label = self.subtitle_font.render("Start een host lobby", True, Colors.WHITE)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 250)))
        hint = self.small_font.render("Deel daarna alleen jouw IP met de andere speler.", True, Colors.GRAY)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 350)))
        for button in self.host_buttons:
            button.draw(self.screen)

    def _draw_join_setup(self):
        label = self.subtitle_font.render("Join met host IP", True, Colors.WHITE)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 270)))
        self.join_ip_input.draw(self.screen)
        for button in self.join_buttons:
            button.draw(self.screen)

    def _draw_host_waiting(self):
        label = self.subtitle_font.render("Lobby geopend", True, Colors.WHITE)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 250)))
        info = self.body_font.render(self.info_message, True, Colors.LIGHT_GRAY)
        self.screen.blit(info, info.get_rect(center=(SCREEN_WIDTH // 2, 330)))
        hint = self.body_font.render("Zodra minstens 2 spelers binnen zijn begint de 30s statfase automatisch.", True, Colors.WHITE)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 390)))
        for button in self.wait_buttons:
            button.draw(self.screen)
