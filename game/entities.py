import math
from dataclasses import dataclass


@dataclass
class Enemy:
    """Inimigo comum. Desce em direcao ao personagem."""

    x: float
    y: float
    hp: int = 30
    speed: float = 70.0
    radius: float = 22.0

    def reached(self, alvo_x: float, alvo_y: float, raio: float = 30.0) -> bool:
        return math.dist((self.x, self.y), (alvo_x, alvo_y)) <= raio

    def is_alive(self) -> bool:
        return self.hp > 0


@dataclass
class Boss(Enemy):
    """Inimigo grande, com barra de HP propria. Invoca inimigos comuns."""

    hp: int = 500
    max_hp: int = 500
    speed: float = 35.0
    radius: float = 60.0
    summon_every: float = 3.0
    since_summon: float = 0.0

    def hp_fraction(self) -> float:
        if self.max_hp <= 0:
            return 0.0
        return max(0.0, min(1.0, self.hp / self.max_hp))


@dataclass
class Character:
    """O personagem controlado pelo publico."""

    x: float = 540.0
    y: float = 1400.0
    vx: float = 0.0
    y_offset: float = 0.0
    radius: float = 34.0
    facing: int = 1
