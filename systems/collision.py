# Collision System - detecteert aanvallen die characters raken.
#
# Voor elke aanval die actief is, wordt gecheckt of hij een andere
# character raakt. Bij een treffer wordt schade en knockback toegepast.

import math

from entities.base_character import BaseCharacter


class CollisionSystem:

    def __init__(self):
        self.hit_events = []    # Lijst van treffer-events (voor effects)

    def update(self, characters):
        # Controleer alle actieve aanvallen op treffers.
        # Geeft een lijst van treffer-events terug.
        self.hit_events = []

        for attacker in characters:
            if attacker.active_attack and attacker.active_attack.is_active:
                self._check_attack_hits(attacker, characters)

        return self.hit_events

    def _check_attack_hits(self, attacker, all_characters):
        # Controleer of de aanval van attacker iemand raakt.
        attack = attacker.active_attack

        for target in all_characters:
            # Sla zichzelf en al geraakte targets over
            if not attack.can_hit(target.player_id):
                continue

            # Controleer of de hitbox de character overlapt
            attack_rect = attack.hitbox.get_rect()
            target_rect = target.get_rect()

            if attack_rect.colliderect(target_rect):
                self._apply_hit(attacker, target, attack)

    def _apply_hit(self, attacker, target, attack):
        # Registreer de treffer en pas schade en knockback toe.
        attack.register_hit(target.player_id)

        target.take_damage(
            damage=attack.damage,
            knockback_base=attack.knockback_base,
            knockback_scaling=attack.knockback_scaling,
            angle=attack.knockback_angle,
            attacker_x=attacker.x
        )

        # Maak een treffer-event aan voor visuele effecten
        hit_event = {
            "type": "hit",
            "attacker_id": attacker.player_id,
            "target_id": target.player_id,
            "x": (attacker.x + target.x) / 2,
            "y": (attacker.y + target.y) / 2,
            "damage": attack.damage,
            "knockback": attack.knockback_base + (target.damage_percent * attack.knockback_scaling),
        }
        self.hit_events.append(hit_event)

    def get_distance(self, char1, char2):
        # Bereken de afstand in pixels tussen twee characters.
        dx = char1.x - char2.x
        dy = char1.y - char2.y
        return math.sqrt(dx * dx + dy * dy)
