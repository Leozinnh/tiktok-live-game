import logging
import unicodedata

from core.events import EventType, LiveEvent
from core.ratelimit import RateLimiter

logger = logging.getLogger(__name__)


def normalize(text: str) -> str:
    """Minusculo, sem acento e sem espaco nas pontas, para casar comandos."""
    texto = text or ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().strip()


class RuleEngine:
    """Traduz LiveEvent em acao do GameEngine.

    Regras novas entram no config.json. Acoes novas entram no registro de
    `game/actions.py`. A integracao com o TikTok nao precisa saber de nada disso.
    """

    def __init__(
        self,
        config: dict,
        game,
        limiter: RateLimiter | None = None,
        on_event=None,
    ):
        self.rules = config["rules"]
        self.game = game
        self.limiter = limiter or RateLimiter()
        self.on_event = on_event

        # Likes: a fonte da verdade e o total acumulado da sala, que so cresce.
        # Guardamos o maior total ja visto e o maior marco ja disparado por regra.
        self._like_max = 0
        self._like_ms: dict[int, int] = {}

    # ---------- entrada ----------

    def process(self, event: LiveEvent) -> None:
        try:
            if event.type == EventType.GIFT:
                self._gift(event)
            elif event.type == EventType.COMMENT:
                self._comment(event)
            elif event.type == EventType.LIKE:
                self._like(event)
            elif event.type == EventType.FOLLOW:
                self._simple("follows", event, "follow")
            elif event.type == EventType.SHARE:
                self._simple("shares", event, "share")
            else:
                logger.debug("Evento sem regra: %s", event.type)
        except Exception:
            # Uma regra mal configurada nao pode derrubar o loop do jogo.
            logger.exception("Erro processando evento %s", event.type)

        if self.on_event is not None:
            try:
                self.on_event(event)
            except Exception:
                logger.exception("Erro no gancho de log de evento")

    # ---------- presentes ----------

    def _gift(self, event: LiveEvent) -> None:
        nome = normalize(event.gift_name)
        for indice, rule in enumerate(self.rules.get("gifts", [])):
            nome_cfg = normalize(rule.get("gift", ""))
            id_cfg = rule.get("gift_id")

            casa_id = (
                id_cfg is not None
                and event.gift_id is not None
                and str(id_cfg) == str(event.gift_id)
            )
            casa_nome = bool(nome_cfg) and nome_cfg == nome

            if casa_id or casa_nome:
                self._run_action(rule, event, f"gift:{indice}:{nome_cfg or id_cfg}")
                return

    # ---------- comentarios ----------

    def _comment(self, event: LiveEvent) -> None:
        texto = normalize(event.text)
        if not texto:
            return
        for indice, rule in enumerate(self.rules.get("comments", [])):
            termo = normalize(rule.get("contains", ""))
            if termo and termo in texto:
                # Um comentario pode disparar varias regras diferentes.
                self._run_action(rule, event, f"comment:{indice}:{termo}")

    # ---------- likes ----------

    def _like(self, event: LiveEvent) -> None:
        total = max(self._like_max, int(event.like_total or 0))
        self._like_max = total

        for indice, rule in enumerate(self.rules.get("likes", [])):
            every = int(rule.get("every", 0))
            if every <= 0:
                continue

            marco_atual = total // every
            marco_anterior = self._like_ms.get(indice, 0)
            if marco_atual <= marco_anterior:
                continue

            disparos = marco_atual - marco_anterior
            self._like_ms[indice] = marco_atual

            # Cada marco cruzado dispara UMA vez. O cooldown da regra nao
            # participa desta decisao: se participasse, o segundo marco da
            # mesma rajada seria descartado em silencio.
            for _ in range(disparos):
                payload = self._payload(rule, event, multiplier=1)
                self.game.apply_action(rule["action"], payload, event)

            logger.info(
                "LIKE MILESTONE | total=%s | every=%s | disparos=%s",
                total,
                every,
                disparos,
            )

    # ---------- follow e share ----------

    def _simple(self, secao: str, event: LiveEvent, chave: str) -> None:
        for indice, rule in enumerate(self.rules.get(secao, [])):
            self._run_action(rule, event, f"{chave}:{indice}")

    # ---------- execucao ----------

    @staticmethod
    def _payload(rule: dict, event: LiveEvent, multiplier: int = 1) -> dict:
        payload = dict(rule)
        payload["amount"] = int(rule.get("amount", 1)) * multiplier
        payload["xp"] = int(rule.get("xp", 0)) * multiplier
        return payload

    def _run_action(self, rule: dict, event: LiveEvent, chave: str) -> None:
        acao = rule.get("action")
        if not acao:
            return

        if event.type == EventType.GIFT and not self._passa_min_quantity(rule, event):
            return

        permitido = self.limiter.allow_rule(
            rule_key=chave,
            cooldown=float(rule.get("cooldown", 0)),
            actor=event.actor(),
            per_user_cooldown=float(rule.get("per_user_cooldown", 0)),
        )
        if not permitido:
            return

        if not self.limiter.allow_action(acao):
            logger.debug("Orcamento global esgotado para a acao %s", acao)
            return

        multiplicador = self._multiplicador(rule, event)
        payload = self._payload(rule, event, multiplicador)
        self.game.apply_action(acao, payload, event)

        logger.info(
            "ACTION | usuario=%s | evento=%s | presente=%s | qtd=%s | acao=%s",
            event.actor(),
            event.type,
            event.gift_name,
            event.quantity,
            acao,
        )

    @staticmethod
    def _passa_min_quantity(rule: dict, event: LiveEvent) -> bool:
        minimo = int(rule.get("min_quantity", 1))
        return max(1, event.quantity) >= minimo

    @staticmethod
    def _multiplicador(rule: dict, event: LiveEvent) -> int:
        if not rule.get("scale_with_quantity"):
            return 1
        quantidade = max(1, event.quantity)
        teto = int(rule.get("max_multiplier", 0))
        if teto <= 0:
            # A validacao da config exige o teto quando ha escala por
            # quantidade. Chegar aqui e config fora do config.json: sem teto
            # nao escala, em vez de escalar sem limite.
            logger.warning(
                "Regra com scale_with_quantity sem max_multiplier: escala ignorada."
            )
            return 1
        return max(1, min(quantidade, teto))
