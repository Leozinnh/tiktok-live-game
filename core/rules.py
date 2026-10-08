import logging
import time
import unicodedata
from collections import defaultdict

from core.events import LiveEvent

logger = logging.getLogger(__name__)


def normalize(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


class RuleEngine:
    """
    Traduz LiveEvent -> ação do GameEngine.

    Novas regras são adicionadas no config.json.
    Novas ações são adicionadas no GameEngine, sem alterar a integração TikTok.
    """

    def __init__(self, config: dict, game):
        self.rules = config["rules"]
        self.game = game
        self.cooldowns = {}
        self.like_total = 0
        self.like_milestones = defaultdict(int)

    def process(self, event: LiveEvent):
        if event.type == "gift":
            self._gift(event)
        elif event.type == "comment":
            self._comment(event)
        elif event.type == "like":
            self._like(event)
        elif event.type == "follow":
            self._simple("follows", event)
        elif event.type == "share":
            self._simple("shares", event)
        else:
            logger.debug("Evento sem regra: %s", event.type)

    def _allowed(self, key: str, cooldown: float) -> bool:
        now = time.monotonic()
        last = self.cooldowns.get(key, 0.0)
        if now - last < cooldown:
            return False
        self.cooldowns[key] = now
        return True

    def _run_action(self, rule: dict, event: LiveEvent, multiplier: int = 1):
        action = rule.get("action", "")
        cooldown = float(rule.get("cooldown", 0))
        key = f"{event.type}:{rule.get('gift', rule.get('contains', action))}"

        if not self._allowed(key, cooldown):
            return

        payload = dict(rule)
        payload["amount"] = rule.get("amount", 1) * multiplier
        payload["xp"] = rule.get("xp", 0) * multiplier

        self.game.apply_action(action, payload, event)

        logger.info(
            "AÇÃO | usuário=%s | evento=%s | presente=%s | quantidade=%s | ação=%s",
            event.actor(),
            event.type,
            event.gift_name,
            event.quantity,
            action,
        )

    def _gift(self, event: LiveEvent):
        gift_name = normalize(event.gift_name)
        for rule in self.rules.get("gifts", []):
            configured_name = normalize(rule.get("gift", ""))

            id_match = (
                rule.get("gift_id") is not None
                and event.gift_id is not None
                and str(rule["gift_id"]) == str(event.gift_id)
            )

            name_match = configured_name and configured_name == gift_name

            if name_match or id_match:
                # Para streaks, a integração já entrega quantity/contagem.
                self._run_action(rule, event, max(1, event.quantity))
                return

    def _comment(self, event: LiveEvent):
        text = normalize(event.text)
        for rule in self.rules.get("comments", []):
            term = normalize(rule.get("contains", ""))
            if term and term in text:
                self._run_action(rule, event)
                # Um comentário pode disparar várias regras diferentes.
        return

    def _like(self, event: LiveEvent):
        amount = max(1, event.like_count or event.quantity or 1)
        old_total = self.like_total
        self.like_total += amount

        for index, rule in enumerate(self.rules.get("likes", [])):
            every = int(rule.get("every", 0))
            if every <= 0:
                continue

            old_milestone = old_total // every
            new_milestone = self.like_total // every

            for milestone in range(old_milestone + 1, new_milestone + 1):
                # Cooldown 0 permite que milestones distintos sejam processados.
                self._run_action(
                    rule,
                    event,
                    multiplier=1,
                )
                logger.info(
                    "LIKE MILESTONE | total=%s | milestone=%s | every=%s",
                    self.like_total,
                    milestone,
                    every,
                )

    def _simple(self, section: str, event: LiveEvent):
        for rule in self.rules.get(section, []):
            self._run_action(rule, event)
