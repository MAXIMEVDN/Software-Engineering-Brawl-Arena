# Physics System - past gravity en wrijving toe op characters.
#
# Let op: characters hebben hun eigen update()-methode die physics al
# verwerkt. Dit systeem kan gebruikt worden als alternatief.

from entities.base_character import BaseCharacter
from entities.platform import Platform
from config import GRAVITY, MAX_FALL_SPEED, GROUND_FRICTION, AIR_FRICTION


class PhysicsSystem:

    def __init__(self):
        self.gravity = GRAVITY
        self.max_fall_speed = MAX_FALL_SPEED
        self.ground_friction = GROUND_FRICTION
        self.air_friction = AIR_FRICTION

    def update(self, characters, platforms):
        # Update physics voor alle characters.
        for character in characters:
            self._apply_gravity(character)
            self._apply_friction(character)
            character.x += character.vel_x
            character.y += character.vel_y
            self._handle_platform_collision(character, platforms)

    def _apply_gravity(self, character):
        # Pas zwaartekracht toe.
        if not character.on_ground and not character.is_dashing:
            weight = getattr(character, 'weight', 1.0)
            character.vel_y += self.gravity * weight
            if character.vel_y > self.max_fall_speed:
                character.vel_y = self.max_fall_speed

    def _apply_friction(self, character):
        # Pas wrijving toe (meer op de grond dan in de lucht).
        if character.is_dashing:
            return

        if character.on_ground:
            character.vel_x *= self.ground_friction
        else:
            character.vel_x *= self.air_friction

        if abs(character.vel_x) < 0.1:
            character.vel_x = 0

    def _handle_platform_collision(self, character, platforms):
        # Laat de character landen op platforms.
        character.on_ground = False

        for platform in platforms:
            char_bottom = character.y + character.height
            char_prev_bottom = char_bottom - character.vel_y

            horizontal_overlap = (
                character.x + character.width > platform.x and
                character.x < platform.x + platform.width
            )
            falling_through = (
                char_prev_bottom <= platform.y and
                char_bottom >= platform.y and
                character.vel_y > 0
            )

            if horizontal_overlap and falling_through:
                character.y = platform.y - character.height
                character.vel_y = 0
                character.on_ground = True
                character.jumps_remaining = character.max_jumps
