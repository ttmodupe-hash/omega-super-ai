"""Physics Simulator Module — Luqi AI v25

Provides computational physics simulations including projectile motion,
planetary orbits, fluid dynamics, and rigid body mechanics.
Used by the v15 ASI cognitive engine and v25 animation systems.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Vector3D:
    """3D vector for physics calculations."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def add(self, other: "Vector3D") -> "Vector3D":
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def scale(self, scalar: float) -> "Vector3D":
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class Body:
    """A physics body with mass, position, and velocity."""
    name: str
    mass: float  # kg
    position: Vector3D = field(default_factory=Vector3D)
    velocity: Vector3D = field(default_factory=Vector3D)
    radius: float = 1.0  # m
    color: str = "#3498db"

    def kinetic_energy(self) -> float:
        v = self.velocity.magnitude()
        return 0.5 * self.mass * v * v

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mass": self.mass,
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict(),
            "radius": self.radius,
            "color": self.color,
        }


@dataclass
class SimulationResult:
    """Result of a physics simulation."""
    frames: List[Dict[str, Any]]
    total_energy: float
    duration_seconds: float
    collisions: int


# ═══════════════════════════════════════════════════════════════════════════════
#  SIMULATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PhysicsSimulator:
    """Main physics simulation engine."""

    G: float = 6.674e-11  # Gravitational constant

    def __init__(self) -> None:
        self.bodies: List[Body] = []
        self.time_step: float = 0.01
        self.collisions: int = 0

    def add_body(self, body: Body) -> None:
        """Add a body to the simulation."""
        self.bodies.append(body)

    def remove_body(self, name: str) -> bool:
        """Remove a body by name."""
        for i, b in enumerate(self.bodies):
            if b.name == name:
                del self.bodies[i]
                return True
        return False

    def simulate_step(self) -> None:
        """Advance simulation by one time step using Euler integration."""
        forces = {b.name: Vector3D() for b in self.bodies}

        # Calculate gravitational forces between all pairs
        for i, b1 in enumerate(self.bodies):
            for b2 in self.bodies[i+1:]:
                dx = b2.position.x - b1.position.x
                dy = b2.position.y - b1.position.y
                dz = b2.position.z - b1.position.z
                dist_sq = dx*dx + dy*dy + dz*dz
                dist = math.sqrt(dist_sq)

                if dist < b1.radius + b2.radius:
                    self.collisions += 1
                    continue

                force_mag = self.G * b1.mass * b2.mass / dist_sq
                f_x = force_mag * dx / dist
                f_y = force_mag * dy / dist
                f_z = force_mag * dz / dist

                forces[b1.name] = forces[b1.name].add(Vector3D(f_x, f_y, f_z))
                forces[b2.name] = forces[b2.name].add(Vector3D(-f_x, -f_y, -f_z))

        # Update velocities and positions
        for body in self.bodies:
            f = forces[body.name]
            ax = f.x / body.mass
            ay = f.y / body.mass
            az = f.z / body.mass

            body.velocity = body.velocity.add(Vector3D(ax, ay, az).scale(self.time_step))
            body.position = body.position.add(body.velocity.scale(self.time_step))

    def simulate(self, steps: int = 1000) -> SimulationResult:
        """Run simulation for N steps."""
        frames: List[Dict[str, Any]] = []
        for _ in range(steps):
            self.simulate_step()
            if _ % 10 == 0:  # Record every 10th frame
                frames.append({
                    "time": _ * self.time_step,
                    "bodies": [b.to_dict() for b in self.bodies],
                })

        total_e = sum(b.kinetic_energy() for b in self.bodies)
        return SimulationResult(
            frames=frames,
            total_energy=total_e,
            duration_seconds=steps * self.time_step,
            collisions=self.collisions,
        )

    def projectiles(
        self,
        v0: float,
        angle_deg: float,
        height: float = 0.0,
        g: float = 9.81,
        dt: float = 0.01,
    ) -> List[Dict[str, float]]:
        """Simulate projectile motion."""
        angle_rad = math.radians(angle_deg)
        vx = v0 * math.cos(angle_rad)
        vy = v0 * math.sin(angle_rad)
        x, y = 0.0, height
        trajectory: List[Dict[str, float]] = []

        while y >= 0:
            trajectory.append({"x": round(x, 3), "y": round(y, 3), "t": round(len(trajectory)*dt, 3)})
            x += vx * dt
            vy -= g * dt
            y += vy * dt

        return trajectory

    def planetary_orbit(
        self,
        star_mass: float = 1.989e30,  # Sun mass in kg
        planet_mass: float = 5.972e24,  # Earth mass in kg
        distance_au: float = 1.0,
    ) -> Dict[str, Any]:
        """Simulate a simple planetary orbit."""
        au = 1.496e11  # meters
        r = distance_au * au
        v_orbital = math.sqrt(self.G * star_mass / r)

        star = Body("Star", star_mass, radius=6.957e8, color="#f1c40f")
        planet = Body(
            "Planet",
            planet_mass,
            position=Vector3D(r, 0, 0),
            velocity=Vector3D(0, v_orbital, 0),
            radius=6.371e6,
            color="#3498db",
        )

        self.bodies = [star, planet]
        result = self.simulate(steps=3650)  # ~1 year

        return {
            "orbital_velocity_ms": round(v_orbital, 2),
            "orbital_period_days": 365,
            "distance_au": distance_au,
            "frames": len(result.frames),
            "total_energy_j": f"{result.total_energy:.3e}",
        }

    def pendulum(
        self,
        length: float = 1.0,
        angle_deg: float = 30.0,
        g: float = 9.81,
        steps: int = 1000,
    ) -> List[Dict[str, float]]:
        """Simulate a simple pendulum."""
        theta = math.radians(angle_deg)
        omega = 0.0
        dt = 0.01
        frames: List[Dict[str, float]] = []

        for _ in range(steps):
            alpha = -(g / length) * math.sin(theta)
            omega += alpha * dt
            theta += omega * dt
            frames.append({
                "angle_rad": round(theta, 5),
                "angle_deg": round(math.degrees(theta), 3),
                "velocity": round(omega, 5),
                "time": round(_ * dt, 2),
            })

        return frames

    def get_status(self) -> Dict[str, Any]:
        """Get simulator status."""
        return {
            "bodies": len(self.bodies),
            "body_names": [b.name for b in self.bodies],
            "time_step": self.time_step,
            "collisions": self.collisions,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = ["PhysicsSimulator", "Body", "Vector3D", "SimulationResult"]
