# Menu - het hoofdmenu van de game.
#
# Bevat opties voor:
#   Host Game  - start een server en verbind als host
#   Join Game  - voer een IP in en verbind
#   Local Test - speel lokaal zonder netwerk
#   Quit       - sluit het programma af

import pygame

from config import Colors, SCREEN_WIDTH, SCREEN_HEIGHT


class Button:
    # Een klikbare knop in het menu.

    def __init__(self, x, y, width, height, text, callback=None, font_size=32):
        # x en y zijn het middelpunt van de knop
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.text = text
        self.callback = callback
        self.hovered = False
        self.font = pygame.font.Font(None, font_size)

        self.color_normal = (70, 80, 90)
        self.color_hover = (90, 100, 120)

    def handle_event(self, event):
        # Verwerk een event. Geeft True terug als de knop geklikt is.
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.hovered:
                if self.callback:
                    self.callback()
                return True

        return False

    def draw(self, screen):
        # Teken de knop (lichter als de muis eroverheen gaat).
        color = self.color_hover if self.hovered else self.color_normal
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, Colors.WHITE, self.rect, 2, border_radius=8)

        text_surface = self.font.render(self.text, True, Colors.WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)


class TextInput:
    # Een tekstveld voor het invoeren van een IP-adres.

    def __init__(self, x, y, width, height, placeholder="", font_size=28):
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.text = ""
        self.placeholder = placeholder
        self.active = False    # True als het veld de focus heeft
        self.font = pygame.font.Font(None, font_size)

    def handle_event(self, event):
        # Verwerk een event (klikken om te activeren, typen om tekst in te voeren).
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
        # Teken het tekstveld.
        border_color = Colors.WHITE if self.active else Colors.GRAY
        pygame.draw.rect(screen, (40, 44, 52), self.rect, border_radius=4)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=4)

        # Toon de ingevoerde tekst of de placeholder
        display_text = self.text if self.text else self.placeholder
        text_color = Colors.WHITE if self.text else Colors.GRAY
        text_surface = self.font.render(display_text, True, text_color)
        text_rect = text_surface.get_rect(midleft=(self.rect.left + 10, self.rect.centery))
        screen.blit(text_surface, text_rect)

        # Toon een cursor als het veld actief is
        if self.active:
            cursor_x = text_rect.right + 2
            pygame.draw.line(screen, Colors.WHITE,
                             (cursor_x, self.rect.top + 8),
                             (cursor_x, self.rect.bottom - 8), 2)


class MainMenu:
    # Het hoofdmenu van de game.

    def __init__(self, screen):
        self.screen = screen
        self.state = "main"     # "main" of "join"
        self.result = None      # Wordt ingesteld als een actie gekozen wordt

        self.title_font = pygame.font.Font(None, 72)
        self.subtitle_font = pygame.font.Font(None, 36)

        self._create_buttons()

    def _create_buttons(self):
        # Maak alle knoppen aan.
        center_x = SCREEN_WIDTH // 2

        self.buttons = [
            Button(center_x, 300, 250, 50, "Host Game", self._on_host),
            Button(center_x, 370, 250, 50, "Join Game", self._on_join),
            Button(center_x, 440, 250, 50, "Local Test", self._on_local),
            Button(center_x, 510, 250, 50, "Quit", self._on_quit),
        ]

        self.server_ip_input = TextInput(
            center_x, 370, 300, 40,
            placeholder="Server IP (bijv. 192.168.1.100)"
        )

        self.join_buttons = [
            Button(center_x, 440, 150, 40, "Connect", self._on_connect),
            Button(center_x, 500, 150, 40, "Back", self._on_back),
        ]

    def _on_host(self):
        self.result = {"action": "host"}

    def _on_join(self):
        self.state = "join"

    def _on_local(self):
        self.result = {"action": "local"}

    def _on_quit(self):
        self.result = {"action": "quit"}

    def _on_connect(self):
        ip = self.server_ip_input.text.strip()
        if ip:
            self.result = {"action": "join", "ip": ip}

    def _on_back(self):
        self.state = "main"

    def handle_event(self, event):
        # Stuur het event door naar de juiste knoppen.
        if self.state == "main":
            for button in self.buttons:
                button.handle_event(event)
        elif self.state == "join":
            self.server_ip_input.handle_event(event)
            for button in self.join_buttons:
                button.handle_event(event)

    def update(self):
        # Geeft het resultaat terug als een actie gekozen is, anders None.
        return self.result

    def draw(self):
        # Teken het menu.
        self.screen.fill(Colors.BG_COLOR)

        # Titel
        title = self.title_font.render("BRAWL ARENA", True, Colors.WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 120)))

        subtitle = self.subtitle_font.render("Platform Fighter", True, Colors.GRAY)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 170)))

        if self.state == "main":
            for button in self.buttons:
                button.draw(self.screen)

        elif self.state == "join":
            label = self.subtitle_font.render("Enter Server IP:", True, Colors.WHITE)
            self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 320)))
            self.server_ip_input.draw(self.screen)
            for button in self.join_buttons:
                button.draw(self.screen)
