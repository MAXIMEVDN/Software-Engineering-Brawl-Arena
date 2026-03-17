# Effects System - visuele effecten (particles en screen shake).
#
# Particles ontstaan bij treffers.
# Screen shake geeft feedback bij harde klappen.

import pygame
import random
import math

from config import Colors, EffectSettings


class Particle:
    # Een klein deeltje dat kort zichtbaar is na een treffer.

    def __init__(self, x, y, vel_x, vel_y, lifetime, color, size=4):
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        self.size = size

    def update(self):
        # Beweeg het particle en verlaag de levensduur.
        # Geeft True terug als het particle nog leeft.
        self.x += self.vel_x
        self.y += self.vel_y
        self.vel_y += 0.2   # Zwaartekracht
        self.vel_x *= 0.98  # Luchtweerstand
        self.lifetime -= 1
        return self.lifetime > 0

    def draw(self, screen, camera_offset=(0, 0)):
        # Teken het particle (wordt doorzichtiger naarmate het ouder wordt).
        fade = self.lifetime / self.max_lifetime
        size = max(1, int(self.size * fade))
        color = tuple(int(c * fade) for c in self.color)

        draw_x = int(self.x - camera_offset[0])
        draw_y = int(self.y - camera_offset[1])
        pygame.draw.circle(screen, color, (draw_x, draw_y), size)


class ScreenShake:
    # Schudt het scherm kort na een harde klap.

    def __init__(self):
        self.intensity = 0
        self.duration = 0

    def trigger(self, intensity, duration):
        # Start een screen shake (sterkere shake overschrijft zwakkere).
        if intensity > self.intensity or self.duration <= 0:
            self.intensity = intensity
            self.duration = duration

    def update(self):
        # Bereken de offset voor dit frame. Geeft (offset_x, offset_y) terug.
        if self.duration <= 0:
            return (0, 0)

        progress = self.duration / EffectSettings.SCREEN_SHAKE_DURATION
        current_intensity = self.intensity * progress

        offset_x = random.uniform(-current_intensity, current_intensity)
        offset_y = random.uniform(-current_intensity, current_intensity)
        self.duration -= 1

        return (offset_x, offset_y)


class EffectsSystem:
    # Beheert alle visuele effecten tegelijk.

    def __init__(self):
        self.particles = []
        self.screen_shake = ScreenShake()
        self.trails = []        # Dash-nasleep
        self.max_particles = 120
        self.max_trails = 40

    def update(self):
        # Update alle effecten en geeft de screen-shake-offset terug.
        self.particles = [p for p in self.particles if p.update()]

        # Update trails: verlaag levensduur en pas doorzichtigheid aan
        self.trails = [t for t in self.trails if t["lifetime"] > 0]
        for trail in self.trails:
            trail["lifetime"] -= 1
            trail["alpha"] = int(255 * (trail["lifetime"] / trail["max_lifetime"]))

        return self.screen_shake.update()

    def process_hit_events(self, events):
        # Verwerk treffer-events en spawn de bijbehorende effecten.
        for event in events:
            if event["type"] == "hit":
                self.spawn_hit_particles(event["x"], event["y"], event["knockback"])
                shake_intensity = min(event["knockback"] * 0.5, EffectSettings.SCREEN_SHAKE_INTENSITY)
                self.screen_shake.trigger(shake_intensity, EffectSettings.SCREEN_SHAKE_DURATION)

    def spawn_hit_particles(self, x, y, intensity=1.0):
        # Spawn particles op de treffer-locatie.
        hit_colors = [
            (255, 255, 200),
            (255, 200, 100),
            (255, 150, 50),
            (255, 255, 255),
        ]

        num_particles = int(EffectSettings.PARTICLE_COUNT * min(intensity / 5, 2))

        for _ in range(num_particles):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, EffectSettings.PARTICLE_SPEED * intensity / 3)

            particle = Particle(
                x=x + random.uniform(-10, 10),
                y=y + random.uniform(-10, 10),
                vel_x=math.cos(angle) * speed,
                vel_y=math.sin(angle) * speed,
                lifetime=EffectSettings.PARTICLE_LIFETIME + random.randint(-5, 5),
                color=random.choice(hit_colors),
                size=random.randint(3, 6)
            )
            self.particles.append(particle)

        # Houd het aantal particles beperkt
        if len(self.particles) > self.max_particles:
            self.particles = self.particles[-self.max_particles:]

    def add_trail(self, x, y, width, height, color):
        # Voeg een dash-trail toe op de opgegeven positie.
        self.trails.append({
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "color": color,
            "lifetime": EffectSettings.TRAIL_LENGTH,
            "max_lifetime": EffectSettings.TRAIL_LENGTH,
            "alpha": 255
        })

        if len(self.trails) > self.max_trails:
            self.trails = self.trails[-self.max_trails:]

    def draw(self, screen, camera_offset=(0, 0)):
        # Teken alle effecten.
        for trail in self.trails:
            fade = max(0.2, trail["alpha"] / 255)
            color = tuple(int(c * fade) for c in trail["color"])
            pygame.draw.rect(
                screen,
                color,
                pygame.Rect(
                    trail["x"] - camera_offset[0],
                    trail["y"] - camera_offset[1],
                    trail["width"],
                    trail["height"],
                ),
            )

        for particle in self.particles:
            particle.draw(screen, camera_offset)
