import json
import logging
import logging.handlers
from pathlib import Path

from core.events import EventType, LiveEvent

FORMATO = "[%(asctime)s] %(levelname)-7s %(name)s | %(message)s"
FORMATO_DATA = "%H:%M:%S"

TAMANHO_MAX = 5 * 1024 * 1024  # 5 MB
BACKUPS = 3

_RAIZ: logging.Logger | None = None
_DESTINO: Path | None = None


def _formatador() -> logging.Formatter:
    """Hora entre colchetes, sem data: uma LIVE nao dura dias."""
    return logging.Formatter(FORMATO, datefmt=FORMATO_DATA)


def setup_logging(
    log_dir: str | Path = "logs", level: int = logging.INFO
) -> logging.Logger:
    """Configura o log da aplicacao.

    Chamar de novo com o MESMO diretorio devolve o logger ja configurado,
    sem duplicar handlers. Chamar com outro diretorio reconfigura.
    """
    global _RAIZ, _DESTINO

    destino = Path(log_dir).resolve()
    if _RAIZ is not None and _DESTINO == destino:
        return _RAIZ

    if _RAIZ is not None:
        _fechar_handlers(_RAIZ)

    destino.mkdir(parents=True, exist_ok=True)

    arquivo = logging.handlers.RotatingFileHandler(
        destino / "app.log",
        maxBytes=TAMANHO_MAX,
        backupCount=BACKUPS,
        encoding="utf-8",
    )
    arquivo.setFormatter(_formatador())

    console = logging.StreamHandler()
    console.setFormatter(_formatador())

    raiz = logging.getLogger()
    raiz.setLevel(level)
    raiz.handlers.clear()
    raiz.addHandler(arquivo)
    raiz.addHandler(console)

    _RAIZ = raiz
    _DESTINO = destino
    return raiz


def _fechar_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        try:
            handler.close()
        except Exception:
            pass
        logger.removeHandler(handler)


class EventJournal:
    """Log estruturado em JSONL, para consulta posterior.

    Registra apenas eventos de audiencia: follow, share, gift, comment, like.
    """

    _IGNORADOS = {EventType.SYSTEM}

    def __init__(self, path: str | Path = "logs/events.jsonl"):
        self.path = Path(path)
        self._arquivo = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._arquivo = self.path.open("a", encoding="utf-8")
        except OSError:
            self._arquivo = None

    def record(self, event: LiveEvent) -> None:
        if self._arquivo is None or event.type in self._IGNORADOS:
            return
        linha = {
            "timestamp": event.timestamp.isoformat(),
            "type": event.type.value,
            "username": event.username,
            "display_name": event.display_name,
            "text": event.text,
            "gift_name": event.gift_name,
            "gift_id": event.gift_id,
            "quantity": event.quantity,
            "like_delta": event.like_delta,
            "like_total": event.like_total,
        }
        try:
            self._arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")
            self._arquivo.flush()
        except OSError:
            pass  # disco cheio nao pode derrubar a LIVE

    def close(self) -> None:
        if self._arquivo is not None:
            try:
                self._arquivo.close()
            except OSError:
                pass
            self._arquivo = None
