# Character Select - keuzemenu voor het selecteren van een character.
#
# Spelers kiezen hier hun character voordat de match begint.
# Navigeren met pijltjestoetsen of muis, bevestigen met Enter/Spatie.

import pygame

from config import Colors, SCREEN_WIDTH, SCREEN_HEIGHT


class CharacterOption:
    # Eén selecteerbaar character in het keuzemenu.

    def __init__(self, name, description, color, stats, x, y):
        self.name = name
        self.description = description
        self.color = color
        self.stats = stats          # {"speed": 5, "power": 7, "defense": 6}
        self.rect = pygame.Rect(x - 100, y - 120, 200, 240)
        self.selected = False
        self.hovered = False

    def draw(self, screen, font, small_font):
        # Teken de character-optie met preview, naam, beschrijving en stats.

        # Achtergrond
        bg_color = (60, 65, 75) if self.hovered else (45, 50, 60)
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=12)

        # Rand (gekleurd als geselecteerd of gehoverd)
        border_color = self.color if (self.selected or self.hovered) else Colors.GRAY
        border_width = 3 if self.selected else 2
        pygame.draw.rect(screen, border_color, self.rect, border_width, border_radius=12)

        # Character-preview (gekleurde rechthoek als placeholder)
        preview_rect = pygame.Rect(self.rect.centerx - 40, self.rect.top + 20, 80, 80)
        pygame.draw.rect(screen, self.color, preview_rect, border_radius=8)

        # Naam
        name_surface = font.render(self.name, True, Colors.WHITE)
        screen.blit(name_surface, name_surface.get_rect(
            center=(self.rect.centerx, self.rect.top + 120)))

        # Beschrijving
        desc_surface = small_font.render(self.description, True, Colors.GRAY)
        screen.blit(desc_surface, desc_surface.get_rect(
            center=(self.rect.centerx, self.rect.top + 145)))

        # Statbalkjes
        self._draw_stats(screen, small_font)

    def _draw_stats(self, screen, font):
        # Teken een balkje per stat.
        stat_y = self.rect.top + 165
        bar_width = 80
        bar_height = 8

        for stat_name, stat_value in self.stats.items():
            # Naam van de stat
            label = font.render(stat_name.capitalize(), True, Colors.LIGHT_GRAY)
            screen.blit(label, (self.rect.left + 15, stat_y))

            # Leeg balkje
            bar_rect = pygame.Rect(self.rect.right - bar_width - 15, stat_y + 2, bar_width, bar_height)
            pygame.draw.rect(screen, Colors.DARK_GRAY, bar_rect, border_radius=2)

            # Gevuld gedeelte
            fill_width = int((stat_value / 10) * bar_width)
            fill_rect = pygame.Rect(bar_rect.left, bar_rect.top, fill_width, bar_height)
            pygame.draw.rect(screen, self.color, fill_rect, border_radius=2)

            stat_y += 18


class CharacterSelect:
    # Het character-selectiescherm.

    def __init__(self, screen):
        self.screen = screen
        self.selected_index = 0
        self.confirmed = False
        self.selected_character = None

        self.title_font = pygame.font.Font(None, 56)
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 22)

        self._create_characters()

    def _create_characters(self):
        # Maak de drie character-opties aan.
        spacing = SCREEN_WIDTH // 4
        y = SCREEN_HEIGHT // 2

        self.characters = [
            CharacterOption(
                name="Warrior",
                description="Balanced fighter",
                color=(220, 80, 80),
                stats={"speed": 5, "power": 7, "defense": 6},
                x=spacing, y=y
            ),
            CharacterOption(
                name="Mage",
                description="Ranged spellcaster",
                color=(80, 120, 220),
                stats={"speed": 6, "power": 8, "defense": 3},
                x=spacing * 2, y=y
            ),
            CharacterOption(
                name="Ninja",
                description="Fast & agile",
                color=(80, 200, 120),
                stats={"speed": 9, "power": 5, "defense": 4},
                x=spacing * 3, y=y
            ),
        ]

        self.characters[0].selected = True

    def handle_event(self, event):
        # Verwerk navigatie en bevestiging.
        if self.confirmed:
            return

        if event.type == pygame.MOUSEMOTION:
            for char in self.characters:
                char.hovered = char.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for i, char in enumerate(self.characters):
                    if char.rect.collidepoint(event.pos):
                        self._select(i)
                        break

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._select((self.selected_index - 1) % len(self.characters))
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._select((self.selected_index + 1) % len(self.characters))
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._confirm()

    def _select(self, index):
        # Selecteer een character op basis van index.
        for char in self.characters:
            char.selected = False
        self.selected_index = index
        self.characters[index].selected = True

    def _confirm(self):
        # Bevestig de keuze.
        self.confirmed = True
        self.selected_character = self.characters[self.selected_index].name

    def get_selected(self):
        # Geeft de naam van het gekozen character terug als bevestigd, anders None.
        return self.selected_character if self.confirmed else None

    def reset(self):
        # Reset de selectie voor een nieuwe ronde.
        self.confirmed = False
        self.selected_character = None

    def draw(self):
        # Teken het character-selectiescherm.
        self.screen.fill(Colors.BG_COLOR)

        title = self.title_font.render("SELECT YOUR FIGHTER", True, Colors.WHITE)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 80)))

        for char in self.characters:
            char.draw(self.screen, self.font, self.small_font)

        if not self.confirmed:
            hint = "← → to select | ENTER to confirm"
        else:
            hint = f"Selected: {self.selected_character} | Waiting for other players..."

        hint_surface = self.font.render(hint, True, Colors.GRAY)
        self.screen.blit(hint_surface, hint_surface.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60)))
