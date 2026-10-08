"""Integracao real com a LIVE do TikTok.

Este e o UNICO modulo do projeto que importa a biblioteca `TikTokLive`.
Todo o resto conversa com `core.event_queue.EventQueue`.

A biblioteca e engenharia reversa do Webcast interno do TikTok: nao e API
oficial e pode quebrar sem aviso. Por isso a traducao evento-bruto ->
LiveEvent vive em funcoes puras, testaveis sem rede.
"""

import asyncio
import logging
import random
import threading
from typing import Any

from adapters.base import AdapterStatus
from core.event_queue import EventQueue
from core.events import EventType, LiveEvent

logger = logging.getLogger(__name__)

# A biblioteca NAO tem reconexao propria: `connect()` retorna quando a
# transmissao termina em paz e levanta quando cai. O cliente nao pode ser
# reutilizado depois disso, entao o laco externo cria um novo por tentativa.
BACKOFF_INICIAL = 5.0
BACKOFF_MAX = 60.0


# ---------------------------------------------------------------------------
# Traducao evento bruto -> LiveEvent. Funcoes puras: testaveis sem rede.
# ---------------------------------------------------------------------------


def _user_id(user: Any) -> str:
    if user is None:
        return ""
    return str(getattr(user, "unique_id", None) or getattr(user, "display_id", None) or "")


def _display_name(user: Any) -> str:
    if user is None:
        return ""
    return str(
        getattr(user, "nickname", None) or getattr(user, "display_name", None) or _user_id(user)
    )


def evento_de_comentario(obj: Any) -> LiveEvent:
    user = getattr(obj, "user", None)
    # A v3 renomeou `comment` para `content`; o alias antigo ainda existe.
    texto = getattr(obj, "content", None) or getattr(obj, "comment", "") or ""
    return LiveEvent(
        type=EventType.COMMENT,
        username=_user_id(user),
        display_name=_display_name(user),
        text=str(texto),
        raw=obj,
    )


def evento_de_presente(obj: Any) -> LiveEvent | None:
    """Traduz um GiftEvent. Retorna None para eventos que devem ser ignorados.

    `streaking` e propriedade da propria biblioteca: `False` para presente
    nao-streakable, e `not repeat_end` caso contrario. O evento FINAL de um
    streak chega com `streaking=False` e `repeat_count` consolidado; ignorar
    os intermediarios evita contar a mesma sequencia dezenas de vezes.

    Nao ha teste extra de "streakable": `streaking` ja cobre os dois casos.
    """
    gift = getattr(obj, "gift", None)
    if gift is None:
        return None

    if getattr(obj, "streaking", False):
        return None  # evento intermediario de streak

    user = getattr(obj, "user", None)
    quantidade = int(getattr(obj, "repeat_count", 1) or 1)
    gift_id = getattr(gift, "id", None) or getattr(obj, "gift_id", None)

    return LiveEvent(
        type=EventType.GIFT,
        username=_user_id(user),
        display_name=_display_name(user),
        gift_name=str(getattr(gift, "name", "") or getattr(gift, "gift_name", "") or ""),
        gift_id=str(gift_id) if gift_id is not None else None,
        quantity=max(1, quantidade),
        raw=obj,
    )


def evento_de_like(obj: Any, total_anterior: int = 0) -> LiveEvent | None:
    """Traduz um LikeEvent.

    `count` e o incremento do evento; `total` e o acumulado da sala. O TikTok
    agrupa curtidas, entao um evento nao e uma curtida. O total e monotono:
    um valor menor que o ja visto e descartado, porque a unica fonte da
    verdade e o acumulado da sala.

    `user` pode vir None: o TikTok para de mandar o autor depois de ~10-20
    curtidas do mesmo usuario, e o total continua subindo.
    """
    user = getattr(obj, "user", None)
    delta = max(0, int(getattr(obj, "count", 0) or 0))
    total = int(getattr(obj, "total", 0) or 0)

    if total < total_anterior:
        total = total_anterior
        delta = 0
    if total == 0 and delta == 0:
        return None

    return LiveEvent(
        type=EventType.LIKE,
        username=_user_id(user),
        display_name=_display_name(user),
        like_delta=delta,
        like_total=total,
        quantity=delta,
        raw=obj,
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class TikTokLiveAdapter:
    """Fonte de eventos real. Mesma fila, mesmas regras, mesmo jogo do modo teste."""

    def __init__(self, queue: EventQueue, config: dict):
        self.queue = queue
        cfg = config.get("tiktok", {})
        self.username = str(cfg.get("username", "")).lstrip("@")
        self.backoff_inicial = float(cfg.get("reconnect_seconds", BACKOFF_INICIAL))
        self.backoff_max = float(cfg.get("reconnect_max_seconds", BACKOFF_MAX))
        self.fetch_gift_info = bool(cfg.get("fetch_gift_info", True))

        self._status = AdapterStatus(connected=False, detail="iniciando")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._like_total = 0

    @property
    def status(self) -> AdapterStatus:
        return self._status

    def start(self) -> None:
        self._thread = threading.Thread(target=self._thread_main, name="tiktok", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run_forever())
        except Exception:
            logger.exception("Thread do TikTok encerrou com erro")

    async def _run_forever(self) -> None:
        from TikTokLive import TikTokLiveClient
        from TikTokLive.client.errors import (
            UserNotFoundError,
            UserOfflineError,
            WebcastBlockedError,
        )
        from TikTokLive.events import (
            CommentEvent,
            ConnectEvent,
            DisconnectEvent,
            FollowEvent,
            GiftEvent,
            LikeEvent,
            ShareEvent,
        )

        tentativa = 0
        backoff = self.backoff_inicial

        while not self._stop.is_set():
            client = None
            try:
                # Cliente NOVO a cada tentativa: o cliente nao e reutilizavel.
                client = TikTokLiveClient(unique_id=self.username)
                self._registrar_handlers(
                    client,
                    CommentEvent=CommentEvent,
                    ConnectEvent=ConnectEvent,
                    DisconnectEvent=DisconnectEvent,
                    FollowEvent=FollowEvent,
                    GiftEvent=GiftEvent,
                    LikeEvent=LikeEvent,
                    ShareEvent=ShareEvent,
                )

                logger.info("Conectando a LIVE @%s (tentativa %s)", self.username, tentativa + 1)
                self._status = AdapterStatus(
                    connected=False, detail="conectando", reconnects=tentativa
                )

                # `connect()` so retorna quando a transmissao termina ou cai.
                await client.connect(
                    fetch_gift_info=self.fetch_gift_info,
                    fetch_room_info=False,
                    fetch_live_check=True,
                )
                logger.info("A LIVE encerrou ou a conexao caiu de forma limpa.")
                tentativa = 0
                backoff = self.backoff_inicial

            except UserNotFoundError:
                logger.error(
                    "O usuario @%s nao existe. Corrija 'tiktok.username' no config.json.",
                    self.username,
                )
                self._status = AdapterStatus(connected=False, detail="usuario invalido")
                return  # nao adianta tentar de novo
            except UserOfflineError:
                logger.info(
                    "@%s nao esta ao vivo agora. Nova checagem em 30s.", self.username
                )
                self._status = AdapterStatus(connected=False, detail="fora do ar")
                await self._dormir(30.0)
                continue
            except WebcastBlockedError:
                logger.warning("O TikTok bloqueou o Webcast. Nova tentativa em 60s.")
                self._status = AdapterStatus(connected=False, detail="bloqueado")
                await self._dormir(60.0)
                continue
            except asyncio.CancelledError:
                break
            except Exception as erro:
                tentativa += 1
                espera = self._espera(backoff, tentativa)
                logger.warning(
                    "Falha na conexao (%s). Tentando de novo em %.1fs (tentativa %s).",
                    type(erro).__name__,
                    espera,
                    tentativa,
                )
                self._status = AdapterStatus(
                    connected=False, detail="reconectando", reconnects=tentativa
                )
                await self._dormir(espera)
                backoff = min(self.backoff_max, backoff * 2)
            finally:
                await self._descartar(client)

            if self._stop.is_set():
                break

        self._status = AdapterStatus(connected=False, detail="encerrado", reconnects=tentativa)

    async def _descartar(self, client: Any) -> None:
        """Desliga o websocket da tentativa que acabou.

        NAO usamos `close_client=True` nem `client.close()`: os dois chamam
        `_clean_tasks()`, que faz `self._asyncio_loop.run_until_complete(...)`.
        Como `_asyncio_loop` devolve o loop JA EM EXECUCAO quando existe um,
        isso levanta `RuntimeError: This event loop is already running`.
        `disconnect()` sozinho desliga o websocket sem passar por ali.
        """
        if client is None:
            return
        try:
            await client.disconnect()
        except Exception:
            logger.debug("Falha ao desconectar o cliente", exc_info=True)

    def _espera(self, backoff: float, tentativa: int) -> float:
        """Backoff exponencial com jitter, para nao reconectar em rebanho."""
        base = min(self.backoff_max, max(self.backoff_inicial, backoff))
        return base * (0.5 + random.random())

    async def _dormir(self, segundos: float) -> None:
        """Dorme em fatias curtas para que stop() responda rapido."""
        loop = asyncio.get_running_loop()
        fim = loop.time() + segundos
        while not self._stop.is_set():
            restante = fim - loop.time()
            if restante <= 0:
                return
            await asyncio.sleep(min(0.25, restante))

    def _registrar_handlers(self, client, **eventos) -> None:
        ConnectEvent = eventos["ConnectEvent"]
        DisconnectEvent = eventos["DisconnectEvent"]
        CommentEvent = eventos["CommentEvent"]
        GiftEvent = eventos["GiftEvent"]
        LikeEvent = eventos["LikeEvent"]
        FollowEvent = eventos["FollowEvent"]
        ShareEvent = eventos["ShareEvent"]

        @client.on(ConnectEvent)
        async def on_connect(event):
            logger.info("CONNECTED | @%s | room=%s", self.username, getattr(client, "room_id", "?"))
            self._status = AdapterStatus(connected=True, detail="ao vivo")
            self.queue.put(LiveEvent(type=EventType.SYSTEM, text="connected"))

        @client.on(DisconnectEvent)
        async def on_disconnect(event):
            logger.warning("DISCONNECTED | o websocket do TikTok caiu")
            self._status = AdapterStatus(connected=False, detail="desconectado")
            self.queue.put(LiveEvent(type=EventType.SYSTEM, text="disconnected"))

        @client.on(CommentEvent)
        async def on_comment(event):
            self.queue.put(evento_de_comentario(event))

        @client.on(GiftEvent)
        async def on_gift(event):
            traduzido = evento_de_presente(event)
            if traduzido is not None:
                self.queue.put(traduzido)

        @client.on(LikeEvent)
        async def on_like(event):
            traduzido = evento_de_like(event, total_anterior=self._like_total)
            if traduzido is not None:
                self._like_total = traduzido.like_total
                self.queue.put(traduzido)

        @client.on(FollowEvent)
        async def on_follow(event):
            user = getattr(event, "user", None)
            self.queue.put(
                LiveEvent(
                    type=EventType.FOLLOW,
                    username=_user_id(user),
                    display_name=_display_name(user),
                    raw=event,
                )
            )

        @client.on(ShareEvent)
        async def on_share(event):
            user = getattr(event, "user", None)
            self.queue.put(
                LiveEvent(
                    type=EventType.SHARE,
                    username=_user_id(user),
                    display_name=_display_name(user),
                    raw=event,
                )
            )
