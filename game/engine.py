import logging
import random
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Enemy:
    x: float
    y: float
    hp: int = 30
    speed: float = 70.0


@dataclass
class GameState:
    hp: int = 100
    max_hp: int = 100
    xp: int = 0
    level: int = 1
    speed: float = 220.0
    base_speed: float = 220.0
    running_until: float = 0.0
    jumping_until: float = 0.0
    shield_until: float = 0.0
    rage_until: float = 0.0
    mega_until: float = 0.0
    enemies: list[Enemy] = field(default_factory=list)
    total_gifts: int = 0
    total_followers: int = 0
    total_shares: int = 0
    total_likes: int = 0


class GameEngine:
    """
    Regras do jogo sem qualquer dependência do Pygame.
    Essa é a parte que pode continuar existindo caso a renderização
    seja trocada por OBS, navegador, Unity, etc.
    """

    def __init__(self, config: dict):
        game_cfg = config["game"]
        self.xp_per_level = int(game_cfg.get("xp_per_level", 100))
        self.base_enemy_damage = int(game_cfg.get("base_enemy_damage", 5))
        self.state = GameState(
            hp=int(game_cfg.get("initial_hp", 100)),
            max_hp=int(game_cfg.get("max_hp", 100)),
            xp=int(game_cfg.get("initial_xp", 0)),
            level=int(game_cfg.get("initial_level", 1)),
            speed=float(game_cfg.get("initial_speed", 220)),
            base_speed=float(game_cfg.get("initial_speed", 220)),
        )
        self.character_x = 200.0
        self.character_y = 0.0
        self.recent_events: list[str] = []

    def add_recent(self, message: str):
        self.recent_events.insert(0, message)
        del self.recent_events[15:]

    def apply_action(self, action: str, payload: dict, event):
        now = time.monotonic()
        amount = int(payload.get("amount", 1))
        duration = float(payload.get("duration", 0))
        xp = int(payload.get("xp", 0))

        if action == "xp":
            self.add_xp(xp)
            self.add_recent(f"{event.actor()} -> +{xp} XP")

        elif action == "heal":
            old = self.state.hp
            self.state.hp = min(self.state.max_hp, self.state.hp + amount)
            self.add_recent(f"{event.actor()} -> cura +{self.state.hp - old}")

        elif action == "damage":
            self.damage(amount)
            self.add_recent(f"{event.actor()} -> dano {amount}")

        elif action == "damage_all":
            for enemy in self.state.enemies:
                enemy.hp -= amount
            self.state.enemies = [e for e in self.state.enemies if e.hp > 0]
            self.add_recent(f"{event.actor()} -> dano em área {amount}")

        elif action == "run":
            self.state.running_until = max(self.state.running_until, now + duration)
            self.add_recent(f"{event.actor()} -> CORRENDO")

        elif action == "jump":
            self.state.jumping_until = max(self.state.jumping_until, now + duration)
            self.add_recent(f"{event.actor()} -> PULO")

        elif action == "speed":
            self.state.speed = max(self.state.speed, self.state.base_speed + amount)
            self.state.running_until = max(self.state.running_until, now + duration)
            self.add_recent(f"{event.actor()} -> velocidade +{amount}")

        elif action == "shield":
            self.state.shield_until = max(self.state.shield_until, now + duration)
            self.add_recent(f"{event.actor()} -> ESCUDO")

        elif action == "rage":
            self.state.rage_until = max(self.state.rage_until, now + duration)
            self.add_recent(f"{event.actor()} -> FÚRIA")

        elif action == "mega":
            self.state.mega_until = max(self.state.mega_until, now + duration)
            self.state.running_until = max(self.state.running_until, now + duration)
            self.add_xp(100)
            self.add_recent(f"{event.actor()} -> EVENTO MEGA!")

        elif action == "spawn_enemy":
            for _ in range(max(1, amount)):
                self.state.enemies.append(
                    Enemy(
                        x=random.randint(850, 1150),
                        y=random.randint(360, 560),
                    )
                )
            self.add_recent(f"{event.actor()} -> +{max(1, amount)} inimigo(s)")

        else:
            logger.warning("Ação desconhecida: %s", action)
            self.add_recent(f"Ação desconhecida: {action}")

        # Contadores gerais.
        if event.type == "gift":
            self.state.total_gifts += max(1, event.quantity)
        elif event.type == "follow":
            self.state.total_followers += 1
        elif event.type == "share":
            self.state.total_shares += 1
        elif event.type == "like":
            self.state.total_likes += max(1, event.like_count or event.quantity)

    def add_xp(self, amount: int):
        if amount <= 0:
            return
        self.state.xp += amount
        while self.state.xp >= self.xp_per_level:
            self.state.xp -= self.xp_per_level
            self.state.level += 1
            self.state.max_hp += 10
            self.state.hp = self.state.max_hp
            self.add_recent(f"LEVEL UP! Nível {self.state.level}")

    def damage(self, amount: int):
        now = time.monotonic()
        if now < self.state.shield_until:
            self.add_recent("Escudo bloqueou dano")
            return

        multiplier = 2 if now < self.state.rage_until else 1
        final_damage = amount * multiplier
        self.state.hp = max(0, self.state.hp - final_damage)

        if self.state.hp == 0:
            self.state.hp = self.state.max_hp
            self.state.xp = max(0, self.state.xp - 25)
            self.add_recent("Personagem derrotado! Respawn.")

    def update(self, dt: float):
        now = time.monotonic()

        if now >= self.state.running_until:
            self.state.speed = self.state.base_speed

        # Movimento visual do personagem.
        movement_speed = self.state.speed
        if now < self.state.rage_until:
            movement_speed *= 1.35
        if now < self.state.mega_until:
            movement_speed *= 1.8

        self.character_x += movement_speed * dt
        if self.character_x > 700:
            self.character_x = 180

        # Salto visual simples.
        if now < self.state.jumping_until:
            phase = (now * 8) % 3.14159
            self.character_y = abs(__import__("math").sin(phase)) * 120
        else:
            self.character_y = 0

        # Inimigos caminham para o personagem.
        for enemy in self.state.enemies:
            enemy.x -= enemy.speed * dt
            if enemy.x < self.character_x + 40:
                self.damage(self.base_enemy_damage)
                enemy.hp = 0

        self.state.enemies = [e for e in self.state.enemies if e.hp > 0]
