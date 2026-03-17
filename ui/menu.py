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


class LobbyList:

    def __init__(self):
        self.font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)
        self.selected_index = 0
        self.rows = []

    def set_lobbies(self, lobbies):
        self.rows = lobbies
        if self.selected_index >= len(self.rows):
            self.selected_index = 0

    def get_selected(self):
        if not self.rows:
            return None
        return self.rows[self.selected_index]

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, (_, row_rect) in enumerate(self._iter_row_rects()):
                if row_rect.collidepoint(event.pos):
                    self.selected_index = index
                    break
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w) and self.rows:
                self.selected_index = (self.selected_index - 1) % len(self.rows)
            elif event.key in (pygame.K_DOWN, pygame.K_s) and self.rows:
                self.selected_index = (self.selected_index + 1) % len(self.rows)

    def _iter_row_rects(self):
        x = SCREEN_WIDTH // 2 - 220
        y = 250
        for index, lobby in enumerate(self.rows):
            rect = pygame.Rect(x, y + (index * 64), 440, 52)
            yield lobby, rect

    def draw(self, screen):
        for index, (lobby, rect) in enumerate(self._iter_row_rects()):
            selected = index == self.selected_index
            bg = (72, 88, 110) if selected else (44, 48, 58)
            border = Colors.WHITE if selected else Colors.GRAY
            pygame.draw.rect(screen, bg, rect, border_radius=10)
            pygame.draw.rect(screen, border, rect, 2, border_radius=10)

            title = f"Lobby {index + 1}  |  {lobby['player_count']}/{lobby['max_players']} spelers"
            ip_text = lobby.get("ip", "unknown")
            screen.blit(self.font.render(title, True, Colors.WHITE), (rect.left + 14, rect.top + 10))
            screen.blit(self.small_font.render(ip_text, True, Colors.LIGHT_GRAY), (rect.left + 14, rect.top + 30))


class MainMenu:

    def __init__(self, screen):
        self.screen = screen
        self.state = "welcome"
        self.result = None
        self.error_message = ""
        self.info_message = ""
        self.lobbies = []

        self.title_font = pygame.font.Font(None, 88)
        self.subtitle_font = pygame.font.Font(None, 36)
        self.body_font = pygame.font.Font(None, 28)
        self.small_font = pygame.font.Font(None, 22)

        self.password_input = TextInput(SCREEN_WIDTH // 2, 310, 340, 48, "Kies een wachtwoord")
        self.join_password_input = TextInput(SCREEN_WIDTH // 2, 560, 340, 48, "Voer lobby wachtwoord in")
        self.lobby_list = LobbyList()

        self._create_buttons()

    def _create_buttons(self):
        center_x = SCREEN_WIDTH // 2
        self.mode_buttons = [
            Button(center_x, 330, 260, 56, "Host Game", self._show_host_setup),
            Button(center_x, 408, 260, 56, "Join Game", self._show_join_setup),
            Button(center_x, 486, 260, 56, "Local Game", self._on_local_game),
        ]

        self.host_buttons = [
            Button(center_x, 390, 240, 52, "Create Lobby", self._on_create_lobby),
            Button(center_x, 458, 180, 44, "Back", self._on_back_to_mode),
        ]

        self.join_buttons = [
            Button(center_x - 110, 630, 180, 44, "Refresh", self._on_refresh_lobbies),
            Button(center_x + 110, 630, 180, 44, "Join Lobby", self._on_join_lobby),
            Button(center_x, 682, 180, 40, "Back", self._on_back_to_mode),
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
        password = self.password_input.text.strip()
        if not password:
            self.error_message = "Kies eerst een wachtwoord."
            return
        self.result = {"action": "host", "password": password}

    def _on_local_game(self):
        self.result = {"action": "local"}

    def _on_join_lobby(self):
        password = self.join_password_input.text.strip()
        lobby = self.lobby_list.get_selected()
        if not lobby:
            self.error_message = "Geen lobby geselecteerd."
            return
        if not password:
            self.error_message = "Voer het wachtwoord in."
            return
        self.result = {"action": "join", "password": password, "lobby": lobby}

    def _on_refresh_lobbies(self):
        self.result = {"action": "refresh_lobbies"}

    def _on_cancel_waiting(self):
        self.result = {"action": "cancel_waiting"}

    def set_lobbies(self, lobbies):
        self.lobbies = lobbies
        self.lobby_list.set_lobbies(lobbies)

    def set_waiting_view(self, password, player_count):
        self.state = "host_waiting"
        self.info_message = f"Lobby live. Wachtwoord: {password} | Players: {player_count}/4"
        self.result = None

    def set_error(self, message):
        self.error_message = message

    def clear_messages(self):
        self.error_message = ""
        self.info_message = ""

    def handle_event(self, event):
        if self.state == "welcome":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.state = "mode_select"
        elif self.state == "mode_select":
            for button in self.mode_buttons:
                button.handle_event(event)
        elif self.state == "host_setup":
            self.password_input.handle_event(event)
            for button in self.host_buttons:
                button.handle_event(event)
        elif self.state == "join_setup":
            self.join_password_input.handle_event(event)
            self.lobby_list.handle_event(event)
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
        label = self.subtitle_font.render("Maak een lobby wachtwoord aan", True, Colors.WHITE)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 250)))
        self.password_input.draw(self.screen)
        hint = self.small_font.render("Andere spelers hoeven straks alleen dit wachtwoord in te voeren.", True, Colors.GRAY)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 350)))
        for button in self.host_buttons:
            button.draw(self.screen)

    def _draw_join_setup(self):
        label = self.subtitle_font.render("Beschikbare lobbies op dit netwerk", True, Colors.WHITE)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 210)))
        if self.lobbies:
            self.lobby_list.draw(self.screen)
        else:
            empty = self.body_font.render("Nog geen lobbies gevonden. Gebruik Refresh.", True, Colors.GRAY)
            self.screen.blit(empty, empty.get_rect(center=(SCREEN_WIDTH // 2, 340)))

        self.join_password_input.draw(self.screen)
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
