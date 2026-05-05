"""Lightweight particle system for visual feedback."""

from dataclasses import dataclass, field
from random import uniform
import math
import pygame


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    lifetime: float
    max_lifetime: float
    color: tuple
    size: float = 3.0


class ParticleEmitter:
    def __init__(self):
        self.particles: list[Particle] = []

    def emit(
        self,
        x: float,
        y: float,
        count: int = 10,
        color: tuple = (255, 200, 50),
        lifetime: float = 1.0,
        speed: float = 50.0,
    ):
        for _ in range(count):
            angle = uniform(0, math.tau)
            spd = uniform(0, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=vx,
                    vy=vy,
                    lifetime=lifetime,
                    max_lifetime=lifetime,
                    color=color,
                    size=uniform(2, 5),
                )
            )

    def update(self, dt: float):
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.lifetime -= dt
        self.particles = [p for p in self.particles if p.lifetime > 0]

    def draw(self, surface: pygame.Surface):
        for p in self.particles:
            alpha = max(0, int(255 * (p.lifetime / p.max_lifetime)))
            color_with_alpha = (*p.color[:3], alpha)
            temp_surf = pygame.Surface((p.size * 2, p.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                temp_surf, color_with_alpha, (int(p.size), int(p.size)), int(p.size)
            )
            surface.blit(
                temp_surf,
                (int(p.x - p.size), int(p.y - p.size)),
            )
