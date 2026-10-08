import logging
import math
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
        # Velocidade do nivel 1, usada como referencia para transformar o
        # ganho de velocidade num fator: a escala de `state.speed` nao e a
        # mesma de `intent_max_speed`, entao ele entra como multiplicador.
        self._velocidade_inicial = max(1.0, float(cfg.get("initial_speed", 220)))
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

        # Limites da arena, em pixels logicos (o renderer so escala depois).
        self.largura = float(config.get("app", {}).get("window_width", 1080))
        self.altura = float(config.get("app", {}).get("window_height", 1920))
        # O HUD ocupa o topo da tela e e desenhado POR CIMA da arena. Nada
        # do mundo pode nascer acima daqui, senao o HUD fica coberto.
        self.topo = float(config.get("app", {}).get("hud_height", 320))

        self._jump_duration = 0.8
        # Um respawn limpa inimigos e boss; os laços de simulacao precisam
        # saber que isso aconteceu no meio do quadro para nao repovoar a lista.
        self._respawns = 0

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

    def attack(self, amount: int) -> None:
        """Dano vindo de um presente.

        Se ha um chefe na arena, o golpe vai nele — e assim que o publico
        derruba o chefe, ja que o personagem so anda e pula. Sem chefe, o
        alvo e o proprio personagem (presente troll).
        """
        boss = self.state.boss
        if boss is not None and boss.is_alive():
            boss.hp = max(0, boss.hp - max(0, int(amount)))
            return
        self.damage(amount)

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
        self._respawns += 1
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
            # Nascem logo abaixo do HUD. O HUD e desenhado por cima da
            # arena, entao um inimigo acima de `self.topo` fica escondido.
            self.state.enemies.append(
                Enemy(
                    x=random.uniform(80.0, 1000.0),
                    y=self.topo + Enemy.radius + random.uniform(0.0, 140.0),
                )
            )
        return criar

    def spawn_boss(self) -> Boss:
        if self.state.boss is not None and self.state.boss.is_alive():
            return self.state.boss
        hp = 300 + self.state.level * 50
        # Abaixo da barra de vida e do rotulo que a arena desenha no topo.
        boss = Boss(x=540.0, y=self.topo + 150.0, hp=hp, max_hp=hp)
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

    # ---------- salto ----------

    def jump(self, duration: float) -> None:
        self._jump_duration = max(0.05, float(duration))
        self.state.effects.activate("jump", self._jump_duration)

    # ---------- intencao de direcao ----------

    def steer(self, direction: float) -> None:
        """Comentario de direcao. `direction` em [-1, +1].

        A soma e limitada: 500 pessoas gritando 'direita' nao podem virar
        um vetor absurdo.
        """
        d = max(-1.0, min(1.0, float(direction)))
        self._intent = max(-3.0, min(3.0, self._intent + d))
        self._intent_until = self._now() + self.intent_half_life

    def intent(self) -> float:
        return self._intent

    def _decair_intencao(self, dt: float) -> None:
        if dt <= 0:
            return
        if self._now() >= self._intent_until:
            # Sem comando recente: decai ate zero.
            fator = 0.5 ** (dt / max(0.01, self.intent_half_life))
            self._intent *= fator
            if abs(self._intent) < 0.01:
                self._intent = 0.0

    def _fator_de_velocidade(self) -> float:
        """Quanto a velocidade atual acelera o personagem, sobre o inicial.

        `state.speed` e escrito pelo presente de velocidade e pelo level up.
        Sem esta leitura ele era escrito e nunca usado: os dois nao tinham
        efeito nenhum na tela.
        """
        return max(0.0, self.state.speed) / self._velocidade_inicial

    def _mover_personagem(self, dt: float) -> None:
        """Acelera na direcao da intencao, em vez de teleportar."""
        personagem = self.state.character
        fator = self._fator_de_velocidade()
        alvo = self._intent * self.intent_max_speed * fator
        diferenca = alvo - personagem.vx
        # O atrito e proporcional a `vx`, entao a velocidade de regime e
        # `accel / friction` — e nao o alvo. Escalar so o alvo nao mudaria
        # nada na tela: a aceleracao tem que escalar junto.
        passo = self.intent_accel * fator * dt
        personagem.vx += max(-passo, min(passo, diferenca))
        personagem.vx -= personagem.vx * min(1.0, self.intent_friction * dt)

        if abs(personagem.vx) < 1.0:
            personagem.vx = 0.0
            return

        personagem.x += personagem.vx * dt
        personagem.facing = 1 if personagem.vx >= 0 else -1

        margem = personagem.radius
        if personagem.x < margem:
            personagem.x = margem
            personagem.vx = 0.0
        elif personagem.x > self.largura - margem:
            personagem.x = self.largura - margem
            personagem.vx = 0.0

    def _animar_pulo(self) -> None:
        if not self.state.effects.active("jump"):
            self.state.character.y_offset = 0.0
            return
        restante = self.state.effects.remaining("jump")
        duracao = max(0.05, self._jump_duration)
        fase = 1.0 - (restante / duracao)
        self.state.character.y_offset = abs(math.sin(fase * math.pi)) * 150.0

    # ---------- inimigos ----------

    def _mover_inimigos(self, dt: float) -> None:
        alvo = self.state.character
        respawns = self._respawns
        vivos: list[Enemy] = []
        for inimigo in self.state.enemies:
            dx = alvo.x - inimigo.x
            dy = alvo.y - inimigo.y
            dist = math.hypot(dx, dy) or 1.0
            inimigo.x += (dx / dist) * inimigo.speed * dt
            inimigo.y += (dy / dist) * inimigo.speed * dt
            if inimigo.reached(alvo.x, alvo.y, raio=alvo.radius + 14.0):
                self.damage(self.base_enemy_damage)
                continue
            vivos.append(inimigo)
        if self._respawns != respawns:
            # O personagem caiu no meio do quadro: `_respawn` ja limpou a
            # lista, e repor `vivos` desfaria a limpeza.
            return
        self.state.enemies = vivos[: self.max_enemies]

    def _atualizar_boss(self, dt: float) -> None:
        boss = self.state.boss
        if boss is None:
            return
        if not boss.is_alive():
            self.add_xp(80 + self.state.level * 20)
            self.state.announcements.push(
                kind="boss",
                actor="",
                text="CHEFÃO DERROTADO",
                detail="+XP",
                ttl=4.0,
                big=True,
            )
            self.state.boss = None
            return

        alvo = self.state.character
        dx = alvo.x - boss.x
        dy = alvo.y - boss.y
        dist = math.hypot(dx, dy) or 1.0
        boss.x += (dx / dist) * boss.speed * dt
        boss.y += (dy / dist) * boss.speed * dt

        boss.since_summon += dt
        if boss.since_summon >= boss.summon_every:
            boss.since_summon = 0.0
            self.spawn_enemy(2)

        if boss.reached(alvo.x, alvo.y, raio=alvo.radius + boss.radius):
            self.damage(self.base_enemy_damage * 2)

    # ---------- ciclo ----------

    def update(self, dt: float) -> None:
        # Uma pausa longa (janela arrastada, GC) nao pode teleportar nada:
        # o passo e limitado antes de simular.
        dt = max(0.0, min(dt, 0.05))

        self._decair_intencao(dt)
        self._mover_personagem(dt)
        self._animar_pulo()
        self._mover_inimigos(dt)
        self._atualizar_boss(dt)
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
            # O contador da tela e o total acumulado da LIVE (`like_total`),
            # nao a soma dos incrementos: uma rajada que cruza varios marcos
            # chama `apply_action` uma vez por marco e inflava o numero
            # (300 likes viravam 900). `max` mantem o contador monotonico.
            # Sem `like_total` (adapter que so informa o incremento), soma o
            # delta.
            total = int(event.like_total or 0)
            if total:
                self.state.total_likes = max(self.state.total_likes, total)
            else:
                self.state.total_likes += max(0, int(event.like_delta or 0))
