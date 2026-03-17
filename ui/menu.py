import os

import pygame

from config import Colors, SCREEN_WIDTH, SCREEN_HEIGHT

try:
    from PIL import Image
except ImportError:
    Image = None


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

    MENU_BG_PATH = "assets/backgrounds/homepage background/Free-Mountain-Backgrounds-Pixel-Art5.png"
    MENU_TITLE_PATH = "assets/backgrounds/homepage background/text-1773773015478.png"
    KNIGHT_GIF_PATH = "assets/sprites/homepage knight gif/14693.gif"
    KNIGHT_FRAME_DIR = "assets/sprites/homepage knight gif/14693"
    TITLE_ACCENT_COLOR = (247, 233, 214)

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
        self.background = self._load_background(self.MENU_BG_PATH)
        self.title_image = self._load_title_image()
        self.knight_frames = self._load_knight_frames()
        self.knight_frame_index = 0
        self.knight_frame_timer = 0
        self.knight_frame_duration = 10

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

    def _resolve_path(self, relative_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, relative_path)

    def _load_background(self, relative_path):
        full_path = self._resolve_path(relative_path)
        if not os.path.exists(full_path):
            return None

        try:
            image = pygame.image.load(full_path).convert()
        except pygame.error:
            return None

        image_ratio = image.get_width() / max(1, image.get_height())
        target_ratio = SCREEN_WIDTH / SCREEN_HEIGHT

        if image_ratio > target_ratio:
            scaled_height = SCREEN_HEIGHT
            scaled_width = int(scaled_height * image_ratio)
        else:
            scaled_width = SCREEN_WIDTH
            scaled_height = int(scaled_width / max(image_ratio, 0.001))

        scaled = pygame.transform.scale(image, (scaled_width, scaled_height))
        crop_x = max(0, (scaled_width - SCREEN_WIDTH) // 2)
        crop_y = max(0, (scaled_height - SCREEN_HEIGHT) // 2)
        return scaled.subsurface((crop_x, crop_y, SCREEN_WIDTH, SCREEN_HEIGHT)).copy()

    def _load_single_surface(self, full_path):
        try:
            return pygame.image.load(full_path).convert_alpha()
        except pygame.error:
            return None

    def _load_title_image(self):
        full_path = self._resolve_path(self.MENU_TITLE_PATH)
        if not os.path.exists(full_path):
            return None

        title_surface = self._load_single_surface(full_path)
        if not title_surface:
            return None

        max_width = 520
        scale = min(1.0, max_width / max(1, title_surface.get_width()))
        scaled_size = (
            max(1, int(title_surface.get_width() * scale)),
            max(1, int(title_surface.get_height() * scale)),
        )
        return pygame.transform.scale(title_surface, scaled_size)

    def _load_frames_from_directory(self, directory_path):
        if not os.path.isdir(directory_path):
            return []

        frame_paths = sorted(
            os.path.join(directory_path, name)
            for name in os.listdir(directory_path)
            if name.lower().endswith((".png", ".webp", ".bmp"))
        )
        return [frame for path in frame_paths if (frame := self._load_single_surface(path))]

    def _load_gif_frames(self, full_path):
        if Image is None or not os.path.exists(full_path):
            return []

        frames = []
        try:
            with Image.open(full_path) as gif:
                frame_count = getattr(gif, "n_frames", 1)
                for frame_index in range(frame_count):
                    gif.seek(frame_index)
                    frame_rgba = gif.convert("RGBA")
                    surface = pygame.image.fromstring(frame_rgba.tobytes(), frame_rgba.size, "RGBA").convert_alpha()
                    frames.append(surface)
        except Exception:
            return []
        return frames

    def _load_knight_frames(self):
        gif_full_path = self._resolve_path(self.KNIGHT_GIF_PATH)
        frame_dir = self._resolve_path(self.KNIGHT_FRAME_DIR)

        frames = self._load_gif_frames(gif_full_path)
        if not frames:
            frames = self._load_frames_from_directory(frame_dir)
        if not frames and os.path.exists(gif_full_path):
            single_frame = self._load_single_surface(gif_full_path)
            if single_frame:
                frames = [single_frame]

        if not frames:
            return []

        scaled_frames = []
        target_height = 230
        for frame in frames:
            scale = target_height / max(1, frame.get_height())
            scaled_width = max(1, int(frame.get_width() * scale))
            scaled_frames.append(pygame.transform.scale(frame, (scaled_width, target_height)))
        return scaled_frames

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

    def animate(self):
        if len(self.knight_frames) <= 1:
            return

        self.knight_frame_timer += 1
        if self.knight_frame_timer >= self.knight_frame_duration:
            self.knight_frame_timer = 0
            self.knight_frame_index = (self.knight_frame_index + 1) % len(self.knight_frames)

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
        self._draw_scene_background()
        if self.state != "welcome":
            self._draw_background_panels()
        self._draw_title()

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

    def _draw_scene_background(self):
        if self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill(Colors.BG_COLOR)

        sky_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        sky_overlay.fill((18, 24, 40, 54))
        self.screen.blit(sky_overlay, (0, 0))

        if self.knight_frames:
            knight = self.knight_frames[self.knight_frame_index]
            knight_rect = knight.get_rect(bottomleft=(78, SCREEN_HEIGHT - 42))
            self.screen.blit(knight, knight_rect)

    def _draw_title(self):
        title_position = (SCREEN_WIDTH // 2, 118)
        if self.title_image:
            title_rect = self.title_image.get_rect(center=title_position)
            self.screen.blit(self.title_image, title_rect)
            return

        title_shadow = self.title_font.render("Brawl Arena", True, (18, 24, 38))
        title = self.title_font.render("Brawl Arena", True, Colors.WHITE)
        self.screen.blit(title_shadow, title_shadow.get_rect(center=(title_position[0] + 3, title_position[1] + 3)))
        self.screen.blit(title, title.get_rect(center=title_position))

    def _draw_background_panels(self):
        panel = pygame.Rect(140, 170, SCREEN_WIDTH - 280, SCREEN_HEIGHT - 240)
        panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(panel_surface, (20, 24, 34, 120), panel_surface.get_rect(), border_radius=28)
        pygame.draw.rect(panel_surface, (155, 165, 202, 170), panel_surface.get_rect(), 2, border_radius=28)
        self.screen.blit(panel_surface, panel.topleft)

    def _draw_welcome(self):
        subtitle = self.subtitle_font.render("Een snelle arena fighter voor jullie lobby", True, self.TITLE_ACCENT_COLOR)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 200)))
        prompt = self.body_font.render("Press ENTER to start", True, self.TITLE_ACCENT_COLOR)
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, 238)))

    def _draw_mode_select(self):
        subtitle = self.subtitle_font.render("Kies hoe je de lobby wilt openen", True, self.TITLE_ACCENT_COLOR)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        for button in self.mode_buttons:
            button.draw(self.screen)

    def _draw_host_setup(self):
        label = self.subtitle_font.render("Start een host lobby", True, Colors.WHITE)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        hint = self.small_font.render("Deel daarna alleen jouw IP met de andere speler.", True, Colors.GRAY)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 312)))
        for button in self.host_buttons:
            button.draw(self.screen)

    def _draw_join_setup(self):
        label = self.subtitle_font.render("Join met host IP", True, Colors.WHITE)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        self.join_ip_input.draw(self.screen)
        for button in self.join_buttons:
            button.draw(self.screen)

    def _draw_host_waiting(self):
        label = self.subtitle_font.render("Lobby geopend", True, Colors.WHITE)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        info = self.body_font.render(self.info_message, True, Colors.LIGHT_GRAY)
        self.screen.blit(info, info.get_rect(center=(SCREEN_WIDTH // 2, 300)))
        hint = self.body_font.render("Zodra minstens 2 spelers binnen zijn begint de 30s statfase automatisch.", True, Colors.WHITE)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 352)))
        for button in self.wait_buttons:
            button.draw(self.screen)
