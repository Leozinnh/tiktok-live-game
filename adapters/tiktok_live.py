import asyncio
import logging
import threading
import time
from typing import Callable

from core.events import LiveEvent

logger = logging.getLogger(__name__)


class TikTokLiveAdapter:
    """
    Adaptador da integração externa.

    IMPORTANTE:
    TikTokLive é uma biblioteca não oficial que consome o Webcast interno
    do TikTok. O restante do sistema não conhece TikTokLive diretamente.
    """

    def __init__(
        self,
        username: str,
        event_sink: Callable[[LiveEvent], None],
        reconnect_seconds: int = 5,
        fetch_gift_info: bool = True,
    ):
        self.username = username.lstrip("@")
        self.event_sink = event_sink
        self.reconnect_seconds = reconnect_seconds
        self.fetch_gift_info = fetch_gift_info

        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._thread_main,
            name="tiktok-live",
            daemon=True,
        )

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=3)

    def _thread_main(self):
        asyncio.run(self._run_forever())

    async def _run_forever(self):
        from TikTokLive import TikTokLiveClient
        from TikTokLive.events import (
            CommentEvent,
            ConnectEvent,
            DisconnectEvent,
            FollowEvent,
            GiftEvent,
            LikeEvent,
            ShareEvent,
        )

        while not self._stop.is_set():
            client = None

            try:
                client = TikTokLiveClient(unique_id=self.username)

                @client.on(ConnectEvent)
                async def on_connect(event):
                    logger.info(
                        "Conectado à LIVE @%s | room_id=%s",
                        self.username,
                        getattr(client, "room_id", None),
                    )
                    self._emit(
                        LiveEvent(
                            type="system",
                            text="connected",
                            raw=event,
                        )
                    )

                @client.on(DisconnectEvent)
                async def on_disconnect(event):
                    logger.warning("WebSocket TikTok desconectado.")

                @client.on(CommentEvent)
                async def on_comment(event):
                    user = getattr(event, "user", None)
                    self._emit(
                        LiveEvent(
                            type="comment",
                            username=self._user_id(user),
                            display_name=self._display_name(user),
                            text=str(getattr(event, "comment", "") or ""),
                            raw=event,
                        )
                    )

                @client.on(GiftEvent)
                async def on_gift(event):
                    # Ignora eventos intermediários de streak.
                    # O evento final informa a contagem consolidada.
                    if getattr(event, "streaking", False):
                        return

                    gift = getattr(event, "gift", None)
                    if gift is None:
                        return

                    user = getattr(event, "user", None)
                    quantity = int(
                        getattr(event, "repeat_count", 1)
                        or getattr(event, "count", 1)
                        or 1
                    )

                    gift_name = str(getattr(gift, "name", "") or "")
                    gift_id = getattr(gift, "id", None)

                    self._emit(
                        LiveEvent(
                            type="gift",
                            username=self._user_id(user),
                            display_name=self._display_name(user),
                            gift_name=gift_name,
                            gift_id=str(gift_id) if gift_id is not None else None,
                            quantity=quantity,
                            raw=event,
                        )
                    )

                @client.on(LikeEvent)
                async def on_like(event):
                    user = getattr(event, "user", None)
                    count = int(
                        getattr(event, "like_count", 0)
                        or getattr(event, "count", 0)
                        or 1
                    )

                    self._emit(
                        LiveEvent(
                            type="like",
                            username=self._user_id(user),
                            display_name=self._display_name(user),
                            like_count=count,
                            quantity=count,
                            raw=event,
                        )
                    )

                @client.on(FollowEvent)
                async def on_follow(event):
                    user = getattr(event, "user", None)
                    self._emit(
                        LiveEvent(
                            type="follow",
                            username=self._user_id(user),
                            display_name=self._display_name(user),
                            raw=event,
                        )
                    )

                @client.on(ShareEvent)
                async def on_share(event):
                    user = getattr(event, "user", None)
                    self._emit(
                        LiveEvent(
                            type="share",
                            username=self._user_id(user),
                            display_name=self._display_name(user),
                            raw=event,
                        )
                    )

                # run() bloqueia esta thread até a conexão terminar.
                # Quando cair, o while externo cria uma nova conexão.
                client.run(
                    fetch_gift_info=self.fetch_gift_info,
                    fetch_room_info=False,
                    fetch_live_check=True,
                )

            except Exception:
                logger.exception(
                    "Erro na conexão TikTok. Tentando novamente em %ss.",
                    self.reconnect_seconds,
                )

            finally:
                if client is not None:
                    try:
                        # close() é async; como já estamos no loop asyncio,
                        # encerramos de forma segura.
                        await client.close()
                    except Exception:
                        pass

            if not self._stop.is_set():
                await asyncio.sleep(self.reconnect_seconds)

    def _emit(self, event: LiveEvent):
        try:
            self.event_sink(event)
        except Exception:
            logger.exception("Erro enviando evento para a fila.")

    @staticmethod
    def _user_id(user) -> str:
        if user is None:
            return ""
        return str(
            getattr(user, "unique_id", None)
            or getattr(user, "user_id", None)
            or ""
        )

    @staticmethod
    def _display_name(user) -> str:
        if user is None:
            return ""
        return str(
            getattr(user, "nickname", None)
            or getattr(user, "display_name", None)
            or getattr(user, "unique_id", None)
            or ""
        )
