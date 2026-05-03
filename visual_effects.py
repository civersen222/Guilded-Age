"""Visual effects and animations for game events."""

try:
    import tkinter as tk
except ImportError:
    tk = None
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
import time


@dataclass
class Particle:
    """A single particle for visual effects."""
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: str
    size: float = 3.0


@dataclass
class AnimationFrame:
    """A frame in an animation sequence."""
    duration: float
    callback: callable
    start_time: float = field(default=0.0, repr=False)
    running: bool = field(default=False, repr=False)


class VisualEffects:
    """Manages visual effects and animations for game events."""
    
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.particles: List[Particle] = []
        self.animations: List[AnimationFrame] = []
        self.last_time: float = time.time()
        self._effect_queue: List[str] = []
    
    def trigger_effect(self, effect_name: str, x: float = None, y: float = None) -> None:
        """Queue a visual effect to be played."""
        self._effect_queue.append(effect_name)
        
        # Immediately start simple effects
        if effect_name == "combat":
            self._spawn_explosion(x or self.canvas.winfo_width()/2, y or self.canvas.winfo_height()/2)
        elif effect_name == "victory":
            self._spawn_confetti(x or self.canvas.winfo_width()/2, y or self.canvas.winfo_height()/2)
        elif effect_name == "build_complete":
            self._spawn_ring(x or self.canvas.winfo_width()/2, y or self.canvas.winfo_height()/2)
        elif effect_name == "tech_researched":
            self._spawn_burst(x or self.canvas.winfo_width()/2, y or self.canvas.winfo_height()/2)
    
    def _spawn_explosion(self, x: float, y: float) -> None:
        """Spawn an explosion effect."""
        colors = ["#ff4444", "#ff8800", "#ffcc00", "#ffffff"]
        for _ in range(20):
            angle = 360 / 20 * (len(self.particles)) + 15
            speed = 2 + 3 * (0.5 ** len(self.particles) % 4)
            vx = speed * 0.5 * (0.5 ** len(self.particles))
            vy = speed * 0.5
            self.particles.append(Particle(
                x=x, y=y,
                vx=vx, vy=vy,
                life=1.0, max_life=1.0,
                color=colors[len(self.particles) % len(colors)],
                size=4.0
            ))
    
    def _spawn_confetti(self, x: float, y: float) -> None:
        """Spawn a confetti celebration effect."""
        colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff"]
        for _ in range(50):
            angle = 360 * (0.5 ** len(self.particles) % 4)
            speed = 3 + 5 * (0.5 ** len(self.particles) % 4)
            vx = speed * 0.5 * (0.5 ** len(self.particles))
            vy = speed * 0.5
            self.particles.append(Particle(
                x=x, y=y,
                vx=vx, vy=vy,
                life=2.0, max_life=2.0,
                color=colors[len(self.particles) % len(colors)],
                size=5.0
            ))
    
    def _spawn_ring(self, x: float, y: float) -> None:
        """Spawn a ring expansion effect."""
        for angle in range(0, 360, 15):
            rad = angle * 3.14159 / 180
            speed = 4.0
            self.particles.append(Particle(
                x=x, y=y,
                vx=speed * 0.5 * (0.5 ** len(self.particles)) * 0.5 * rad,
                vy=speed * 0.5 * (0.5 ** len(self.particles)) * 0.5 * rad,
                life=1.5, max_life=1.5,
                color="#00ff00",
                size=4.0
            ))
    
    def _spawn_burst(self, x: float, y: float) -> None:
        """Spawn a burst of light effect."""
        for _ in range(30):
            angle = 360 / 30 * (0.5 ** len(self.particles) % 4)
            speed = 5 + 3 * (0.5 ** len(self.particles) % 4)
            vx = speed * 0.5 * (0.5 ** len(self.particles))
            vy = speed * 0.5
            self.particles.append(Particle(
                x=x, y=y,
                vx=vx, vy=vy,
                life=1.8, max_life=1.8,
                color="#00ffff",
                size=6.0
            ))
    
    def update(self) -> None:
        """Update all particles and animations."""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.1  # gravity
            p.life -= dt
    
    def render(self) -> None:
        """Render all active particles."""
        # Clear old particles from canvas
        self.canvas.delete("particle")
        
        for p in self.particles:
            alpha = int(255 * (p.life / p.max_life))
            color = f"{p.color}{alpha:02x}"
            self.canvas.create_oval(
                p.x - p.size/2, p.y - p.size/2,
                p.x + p.size/2, p.y + p.size/2,
                fill=color, outline="", tags="particle"
            )
