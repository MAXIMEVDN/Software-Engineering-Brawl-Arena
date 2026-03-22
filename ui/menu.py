import os
import math

import pygame

from config import Colors, SCREEN_WIDTH, SCREEN_HEIGHT
from ui.title_text import draw_title_style_text, get_title_style_font, get_ui_font

try:
    from PIL import Image
except ImportError:
    Image = None


def _render_outlined_text(font, text, text_color, outline_color=(0, 0, 0), outline_width=2):
    base = font.render(text, True, text_color)
    if outline_width <= 0:
        return base

    surface = pygame.Surface(
        (base.get_width() + outline_width * 2, base.get_height() + outline_width * 2),
        pygame.SRCALPHA,
    )
    outline = font.render(text, True, outline_color)
    for offset_x in range(-outline_width, outline_width + 1):
        for offset_y in range(-outline_width, outline_width + 1):
            if offset_x == 0 and offset_y == 0:
                continue
            surface.blit(outline, (offset_x + outline_width, offset_y + outline_width))

    surface.blit(base, (outline_width, outline_width))
    return surface


class Button:

    def __init__(self, x, y, width, height, text, callback=None, font_size=32):
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.text = text
        self.callback = callback
        self.selected = False
        self.font = get_ui_font(font_size)
        self.color_normal = (70, 80, 90)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            if self.callback:
                self.callback()
            return True
        return False

    def draw(self, screen):
        pygame.draw.rect(screen, self.color_normal, self.rect, border_radius=12)
        border_color = Colors.ORANGE if self.selected else Colors.WHITE
        pygame.draw.rect(screen, border_color, self.rect, 3 if self.selected else 2, border_radius=12)
        text_surface = _render_outlined_text(self.font, self.text, Colors.WHITE, outline_width=2)
        screen.blit(text_surface, text_surface.get_rect(center=self.rect.center))


class TextInput:

    def __init__(self, x, y, width, height, placeholder="", font_size=28):
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.text = ""
        self.placeholder = placeholder
        self.active = False
        self.selected = False
        self.font = get_ui_font(font_size)

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
        border_color = Colors.ORANGE if self.selected else (Colors.WHITE if self.active else Colors.GRAY)
        pygame.draw.rect(screen, (32, 36, 44), self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 3 if self.selected else 2, border_radius=8)

        value = self.text if self.text else self.placeholder
        color = Colors.WHITE if self.text else Colors.GRAY
        surface = _render_outlined_text(self.font, value, color, outline_width=2)
        screen.blit(surface, surface.get_rect(midleft=(self.rect.left + 12, self.rect.centery)))


class MainMenu:

    MENU_BG_PATH = "assets/backgrounds/homepage background/Free-Mountain-Backgrounds-Pixel-Art5.png"
    MENU_TITLE_PATH = "assets/backgrounds/homepage background/text-1773773015478.png"
    KNIGHT_GIF_PATH = "assets/sprites/homepage knight gif/14693.gif"
    KNIGHT_FRAME_DIR = "assets/sprites/homepage knight gif/14693"
    TITLE_ACCENT_COLOR = (247, 233, 214)
    TITLE_MAIN_COLOR = (236, 214, 156)

    def __init__(self, screen):
        self.screen = screen
        self.state = "welcome"
        self.result = None
        self.error_message = ""
        self.info_message = ""

        self.title_font = get_ui_font(118)
        self.subtitle_font = get_ui_font(32)
        self.body_font = get_ui_font(28)
        self.small_font = get_ui_font(22)

        self.username_input = TextInput(SCREEN_WIDTH // 2, 272, 280, 44, "Username", font_size=26)
        self.join_ip_input = TextInput(SCREEN_WIDTH // 2, 360, 360, 48, "Host IP (e.g. 192.168.1.42)")
        self.background = self._load_background(self.MENU_BG_PATH)
        self.title_image = self._load_title_image()
        self.knight_frames = self._load_knight_frames()
        self.knight_frame_index = 0
        self.knight_frame_timer = 0
        self.knight_frame_duration = 10
        self.title_pulse_timer = 0.0
        self._title_base_surface = None
        self.selected_index = 0

        self._create_buttons()
        self._update_selection_state()

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

    def _get_title_surface(self):
        if self._title_base_surface is not None:
            return self._title_base_surface

        font = get_title_style_font(118)
        text_width, text_height = font.size("Brawl Arena")
        padding = 24
        surface = pygame.Surface((text_width + padding * 2, text_height + padding * 2), pygame.SRCALPHA)
        draw_title_style_text(
            surface,
            "Brawl Arena",
            (surface.get_width() // 2, surface.get_height() // 2),
            118,
            text_color=self.TITLE_MAIN_COLOR,
            shadow_color=(18, 24, 38),
            outline_color=(0, 0, 0),
            shadow_offset=(5, 5),
            outline_width=3,
        )
        self._title_base_surface = surface
        return surface

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
        self.selected_index = 0
        self._update_selection_state()

    def _show_join_setup(self):
        self.state = "join_setup"
        self.result = None
        self.error_message = ""
        self.selected_index = 0
        self.join_ip_input.active = True
        self._update_selection_state()

    def _on_back_to_mode(self):
        self.state = "mode_select"
        self.result = None
        self.error_message = ""
        self.info_message = ""
        self.selected_index = 0
        self.join_ip_input.active = False
        self._update_selection_state()

    def _on_create_lobby(self):
        self.result = {"action": "host", "username": self.username_input.text.strip()}

    def _on_join_lobby(self):
        ip = self.join_ip_input.text.strip()
        if not ip:
            self.error_message = "Enter the host IP."
            return
        self.result = {"action": "join", "ip": ip, "username": self.username_input.text.strip()}

    def _on_local_game(self):
        self.result = {"action": "local", "username": self.username_input.text.strip()}

    def _on_cancel_waiting(self):
        self.result = {"action": "cancel_waiting"}

    def set_waiting_view(self, player_count, host_ip=""):
        self.state = "host_waiting"
        ip_part = f" | IP: {host_ip}" if host_ip else ""
        self.info_message = f"Lobby live{ip_part} | Players: {player_count}/4"
        self.result = None
        self.selected_index = 0
        self._update_selection_state()

    def set_error(self, message):
        self.error_message = message

    def animate(self):
        self.title_pulse_timer += 0.03

        if len(self.knight_frames) <= 1:
            return

        self.knight_frame_timer += 1
        if self.knight_frame_timer >= self.knight_frame_duration:
            self.knight_frame_timer = 0
            self.knight_frame_index = (self.knight_frame_index + 1) % len(self.knight_frames)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self._sync_selection_from_mouse(event.pos)

        if self.state == "welcome":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.state = "mode_select"
                self.selected_index = 0
                self._update_selection_state()
        elif self.state == "mode_select":
            self.username_input.handle_event(event)
            if not self.username_input.active and self._handle_keyboard_navigation(event, len(self.mode_buttons)):
                return
            for button in self.mode_buttons:
                button.handle_event(event)
        elif self.state == "host_setup":
            self.username_input.handle_event(event)
            if not self.username_input.active and self._handle_keyboard_navigation(event, len(self.host_buttons)):
                return
            for button in self.host_buttons:
                button.handle_event(event)
        elif self.state == "join_setup":
            self.username_input.handle_event(event)
            self.join_ip_input.handle_event(event)
            if not self.username_input.active and not self.join_ip_input.active and self._handle_join_keyboard_navigation(event):
                return
            for button in self.join_buttons:
                button.handle_event(event)
        elif self.state == "host_waiting":
            if self._handle_keyboard_navigation(event, len(self.wait_buttons)):
                return
            for button in self.wait_buttons:
                button.handle_event(event)

    def _sync_selection_from_mouse(self, mouse_pos):
        if self.state == "mode_select":
            for index, button in enumerate(self.mode_buttons):
                if button.rect.collidepoint(mouse_pos):
                    self.selected_index = index
                    self._update_selection_state()
                    return
        elif self.state == "host_setup":
            for index, button in enumerate(self.host_buttons):
                if button.rect.collidepoint(mouse_pos):
                    self.selected_index = index
                    self._update_selection_state()
                    return
        elif self.state == "join_setup":
            if self.join_ip_input.rect.collidepoint(mouse_pos):
                self.selected_index = 0
                self._update_selection_state()
                return
            for index, button in enumerate(self.join_buttons, start=1):
                if button.rect.collidepoint(mouse_pos):
                    self.selected_index = index
                    self._update_selection_state()
                    return
        elif self.state == "host_waiting":
            for index, button in enumerate(self.wait_buttons):
                if button.rect.collidepoint(mouse_pos):
                    self.selected_index = index
                    self._update_selection_state()
                    return

        self._update_selection_state()

    def _handle_keyboard_navigation(self, event, button_count):
        if event.type != pygame.KEYDOWN:
            return False
        if event.key in (pygame.K_w, pygame.K_UP, pygame.K_a, pygame.K_LEFT):
            self.selected_index = (self.selected_index - 1) % button_count
            self._update_selection_state()
            return True
        if event.key in (pygame.K_s, pygame.K_DOWN, pygame.K_d, pygame.K_RIGHT):
            self.selected_index = (self.selected_index + 1) % button_count
            self._update_selection_state()
            return True
        if event.key == pygame.K_RETURN:
            self._activate_selected()
            return True
        return False

    def _handle_join_keyboard_navigation(self, event):
        if event.type != pygame.KEYDOWN:
            return False

        focus_count = 3
        if event.key in (pygame.K_w, pygame.K_UP, pygame.K_a, pygame.K_LEFT):
            self.selected_index = (self.selected_index - 1) % focus_count
            self.join_ip_input.active = self.selected_index == 0
            self._update_selection_state()
            return True
        if event.key in (pygame.K_s, pygame.K_DOWN, pygame.K_d, pygame.K_RIGHT):
            self.selected_index = (self.selected_index + 1) % focus_count
            self.join_ip_input.active = self.selected_index == 0
            self._update_selection_state()
            return True
        if event.key == pygame.K_RETURN:
            if self.selected_index == 0:
                self.join_ip_input.active = True
            elif self.selected_index == 1:
                self._on_join_lobby()
            else:
                self._on_back_to_mode()
            self._update_selection_state()
            return True
        return False

    def _activate_selected(self):
        if self.state == "mode_select":
            self.mode_buttons[self.selected_index].callback()
        elif self.state == "host_setup":
            self.host_buttons[self.selected_index].callback()
        elif self.state == "host_waiting":
            self.wait_buttons[self.selected_index].callback()

    def _update_selection_state(self):
        for button_group in (self.mode_buttons, self.host_buttons, self.join_buttons, self.wait_buttons):
            for button in button_group:
                button.selected = False

        self.join_ip_input.selected = self.state == "join_setup" and self.selected_index == 0

        if self.state == "mode_select" and self.mode_buttons:
            self.mode_buttons[self.selected_index % len(self.mode_buttons)].selected = True
        elif self.state == "host_setup" and self.host_buttons:
            self.host_buttons[self.selected_index % len(self.host_buttons)].selected = True
        elif self.state == "join_setup":
            if self.selected_index == 1 and self.join_buttons:
                self.join_buttons[0].selected = True
            elif self.selected_index == 2 and len(self.join_buttons) > 1:
                self.join_buttons[1].selected = True
        elif self.state == "host_waiting" and self.wait_buttons:
            self.wait_buttons[self.selected_index % len(self.wait_buttons)].selected = True

    def update(self):
        result = self.result
        self.result = None
        return result

    def draw(self):
        self._draw_scene_background()
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
            surface = _render_outlined_text(self.body_font, self.error_message, Colors.RED, outline_width=2)
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
        pulse_scale = 1.0
        if self.state == "welcome":
            pulse_scale += 0.03 * math.sin(self.title_pulse_timer)

        title_y = SCREEN_HEIGHT // 2 - 90 if self.state == "welcome" else 118
        title_surface = self._get_title_surface()
        scaled_width = max(1, int(title_surface.get_width() * pulse_scale))
        scaled_height = max(1, int(title_surface.get_height() * pulse_scale))
        scaled_surface = pygame.transform.smoothscale(title_surface, (scaled_width, scaled_height))
        title_rect = scaled_surface.get_rect(center=(SCREEN_WIDTH // 2, title_y))
        self.screen.blit(scaled_surface, title_rect)

    def _draw_welcome(self):
        subtitle = _render_outlined_text(self.subtitle_font, "A fast arena fighter for your lobby", self.TITLE_ACCENT_COLOR, outline_width=2)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 6)))
        prompt = _render_outlined_text(self.body_font, "Press ENTER to start", self.TITLE_ACCENT_COLOR, outline_width=2)
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 44)))

    def _draw_mode_select(self):
        subtitle = _render_outlined_text(self.subtitle_font, "Choose how you want to open the lobby", self.TITLE_ACCENT_COLOR, outline_width=2)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        self._draw_username_field()
        for button in self.mode_buttons:
            button.draw(self.screen)

    def _draw_host_setup(self):
        label = _render_outlined_text(self.subtitle_font, "Start a host lobby", Colors.WHITE, outline_width=2)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        self._draw_username_field()
        hint = _render_outlined_text(self.small_font, "Only share your IP with the other player afterwards.", Colors.GRAY, outline_width=2)
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 330)))
        for button in self.host_buttons:
            button.draw(self.screen)

    def _draw_join_setup(self):
        label = _render_outlined_text(self.subtitle_font, "Join with host IP", Colors.WHITE, outline_width=2)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        self._draw_username_field()
        self.join_ip_input.draw(self.screen)
        for button in self.join_buttons:
            button.draw(self.screen)

    def _draw_username_field(self):
        self.username_input.draw(self.screen)

    def _draw_host_waiting(self):
        label = _render_outlined_text(self.subtitle_font, "Lobby open", Colors.WHITE, outline_width=2)
        self.screen.blit(label, label.get_rect(center=(SCREEN_WIDTH // 2, 220)))
        info = _render_outlined_text(self.body_font, self.info_message, Colors.LIGHT_GRAY, outline_width=2)
        self.screen.blit(info, info.get_rect(center=(SCREEN_WIDTH // 2, 300)))
        hint = _render_outlined_text(
            self.body_font,
            "As soon as at least 2 players join, the 30s stat phase starts automatically.",
            Colors.WHITE,
            outline_width=2,
        )
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 352)))
        for button in self.wait_buttons:
            button.draw(self.screen)
