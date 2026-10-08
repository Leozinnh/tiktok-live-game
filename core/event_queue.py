import logging
import queue

from core.events import LiveEvent

logger = logging.getLogger(__name__)


class EventQueue:
    """
    Fila thread-safe.
    A integração TikTok escreve de uma thread/loop assíncrono,
    enquanto o Pygame consome na thread principal.
    """

    def __init__(self, maxsize: int = 5000):
        self._queue = queue.Queue(maxsize=maxsize)
        self.dropped = 0

    def put(self, event: LiveEvent):
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            # Mantém a fila viva em rajadas muito grandes.
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(event)
                self.dropped += 1
            except queue.Empty:
                self.dropped += 1
                logger.warning("Fila cheia; evento descartado.")

    def get_nowait(self):
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def size(self) -> int:
        return self._queue.qsize()
