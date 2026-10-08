import logging
import random
import time
from typing import Callable

from core.events import EventType, LiveEvent
from game.actions import ACTION_REGISTRY
from game.effects import AnnouncementQueue, EffectSet
from game.entities import Boss, Enemy
from game.state import GameState

logger = logging.getLogger(__name__)

ANUNCIO_TTL = 4.0


class GameEngine:
    """Regras do jogo, sem qualquer dependencia do Pygame.

    Esta e a parte que sobrevive se a renderizacao for trocada por
    navegador, Unity ou Godot.
    """

    def __init__(self, config: dict, now_fn: Callable[[], float] = time.monotonic):
        cfg = config["game"]
        limites = config.get("limits", {})

        self._now = now_fn
        self.xp_per_level = int(cfg.get("xp_per_level", 100))
        self.xp_level_step = int(cfg.get("xp_level_step", 25))
        self.base_enemy_damage = int(cfg.get("base_enemy_damage", 5))
        self.max_enemies = int(limites.get("max_enemies", 40))
        self.intent_half_life = float(cfg.get("intent_half_life", 1.5))
        self.intent_accel = float(cfg.get("intent_accel", 1800.0))
        self.intent_max_speed = float(cfg.get("intent_max_speed", 420.0))
        self.intent_friction = float(cfg.get("intent_friction", 6.0))

        estado = GameState(
            hp=int(cfg.get("initial_hp", 100)),
            max_hp=int(cfg.get("max_hp", 100)),
            xp=int(cfg.get("initial_xp", 0)),
            level=int(cfg.get("initial_level", 1)),
            speed=float(cfg.get("initial_speed", 220)),
            base_speed=float(cfg.get("initial_speed", 220)),
        )
        estado.effects = EffectSet(now_fn=now_fn)
        estado.announcements = AnnouncementQueue(
            now_fn=now_fn, max_size=int(config.get("app", {}).get("feed_size", 6)) + 2
        )
        self.state = estado

        # Intencao de direcao vinda dos comentarios (Task 9 completa o movimento).
        self._intent = 0.0
        self._intent_until = 0.0

        # Bonus de velocidade concedido por presente. Vale so enquanto o
        # efeito "speed" estiver ativo: o `duration` do presente e o prazo.
        self._speed_bonus = 0.0

    # ---------- experiencia ----------

    def xp_para_subir(self, level: int) -> int:
        """Custo crescente: 100, 125, 150, ..."""
        return self.xp_per_level + (level - 1) * self.xp_level_step

    def add_xp(self, amount: int) -> None:
        if amount <= 0:
            return
        self.state.xp += amount
        while self.state.xp >= self.xp_para_subir(self.state.level):
            self.state.xp -= self.xp_para_subir(self.state.level)
            self.state.level += 1
            self.state.max_hp += 10
            self.state.hp = self.state.max_hp
            self.state.base_speed += 5
            self.state.speed = self.state.base_speed + self._speed_bonus
            self.state.announcements.push(
                kind="levelup",
                actor="",
                text="LEVEL UP!",
                detail=f"Nivel {self.state.level}",
                icon="*",
                ttl=3.0,
                big=True,
            )
            logger.info("LEVEL UP | nivel=%s", self.state.level)

    # ---------- dano e cura ----------

    def heal(self, amount: int) -> int:
        antes = self.state.hp
        self.state.hp = min(self.state.max_hp, self.state.hp + max(0, amount))
        return self.state.hp - antes

    def damage(self, amount: int) -> None:
        if self.state.effects.active("shield"):
            self.state.effects.activate("shield_hit", 0.3)
            return
        if self.state.effects.active("mega"):
            return  # mega evento torna o personagem invulneravel
        self.state.hp = max(0, self.state.hp - max(0, amount))
        if self.state.hp == 0:
            self._respawn()

    def _respawn(self) -> None:
        self.state.hp = self.state.max_hp
        self.state.xp = max(0, self.state.xp - 25)
        self.state.enemies.clear()
        self.state.boss = None
        self.state.announcements.push(
            kind="system",
            actor="",
            text="O personagem caiu!",
            detail="Renascendo",
            ttl=3.0,
            big=True,
        )

    # ---------- entidades ----------

    def spawn_enemy(self, count: int) -> int:
        """Cria inimigos ate o teto. Retorna quantos foram criados."""
        espaco = self.max_enemies - len(self.state.enemies)
        criar = max(0, min(count, espaco))
        for _ in range(criar):
            self.state.enemies.append(
                Enemy(
                    x=random.uniform(80.0, 1000.0),
                    y=random.uniform(-120.0, 120.0),
                )
            )
        return criar

    def spawn_boss(self) -> Boss:
        if self.state.boss is not None and self.state.boss.is_alive():
            return self.state.boss
        hp = 300 + self.state.level * 50
        boss = Boss(x=540.0, y=200.0, hp=hp, max_hp=hp)
        self.state.boss = boss
        self.state.announcements.push(
            kind="boss",
            actor="",
            text="CHEFÃO!",
            detail="Derrote para ganhar XP",
            ttl=5.0,
            big=True,
        )
        return boss

    # ---------- velocidade ----------

    def grant_speed(self, amount: float, duration: float) -> None:
        """Bonus temporario de velocidade. O prazo e o efeito 'speed'."""
        self._speed_bonus = max(self._speed_bonus, float(amount))
        self.state.effects.activate("speed", duration)
        self.state.speed = self.state.base_speed + self._speed_bonus

    def _atualizar_velocidade(self) -> None:
        if self.state.effects.active("speed"):
            self.state.speed = self.state.base_speed + self._speed_bonus
        else:
            self._speed_bonus = 0.0
            self.state.speed = self.state.base_speed

    # ---------- intencao de direcao (Task 9 completa o movimento) ----------

    def steer(self, direction: float) -> None:
        """Comentario de direcao. `direction` em [-1, +1]."""
        d = max(-1.0, min(1.0, float(direction)))
        self._intent = max(-3.0, min(3.0, self._intent + d))
        self._intent_until = self._now() + self.intent_half_life

    def intent(self) -> float:
        return self._intent

    # ---------- ciclo ----------

    def update(self, dt: float) -> None:
        self.state.effects.expire()
        self.state.announcements.expire()
        self._atualizar_velocidade()
        self.state.intent_display = self._intent

    # ---------- despacho ----------

    def apply_action(self, action: str, payload: dict, event: LiveEvent) -> None:
        try:
            self._contabilizar(event)
            handler = ACTION_REGISTRY.get(action)
            if handler is None:
                logger.warning("Acao desconhecida: %s", action)
                return
            handler(self, payload, event)
        except Exception:
            # Uma acao com defeito nao pode derrubar o loop do jogo.
            logger.exception("Erro aplicando acao %s", action)

    def _contabilizar(self, event: LiveEvent) -> None:
        if event.type == EventType.GIFT:
            self.state.total_gifts += max(1, event.quantity)
        elif event.type == EventType.FOLLOW:
            self.state.total_followers += 1
        elif event.type == EventType.SHARE:
            self.state.total_shares += 1
        elif event.type == EventType.LIKE:
            self.state.total_likes += max(1, event.like_delta or 1)
