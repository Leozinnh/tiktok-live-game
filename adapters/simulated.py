import logging
import random
import threading
import time

from adapters.base import AdapterStatus
from core.event_queue import EventQueue
from core.events import EventType, LiveEvent

logger = logging.getLogger(__name__)

PRESENTES_EXEMPLO = [
    "Rose",
    "Heart Me",
    "GG",
    "Finger Heart",
    "Ice Cream Cone",
    "Doughnut",
    "Perfume",
    "Cap",
    "Confetti",
    "TikTok",
    "Lion",
]
COMANDOS_EXEMPLO = ["corre", "pula", "direita", "esquerda", "xp"]

USUARIOS_EXEMPLO = ["joao", "maria", "pedro", "ana", "carlos", "lucas", "bia"]

_CONTROLE = {"help", "quit", "sair", "exit", "auto"}

AJUDA = """Comandos do modo teste:
  Rose                presente (o nome tem que existir no config.json)
  Rose 10             presente com quantidade 10
  GG                  outro presente
  corre               comentario
  "bom dia"           comentario entre aspas
  follow              novo seguidor
  share               compartilhamento
  like 100            cem curtidas
  user joao Rose      define o autor e envia
  auto                rajada aleatoria de eventos
  help                esta ajuda
  quit                sair"""


class SimulatedAdapter:
    """Adapter de teste. Escreve na MESMA fila que o adapter real.

    Nao ha conexao com o TikTok: os eventos sao digitados ou sorteados.
    Trocar de adapter nao muda regra, jogo nem renderer.
    """

    def __init__(
        self,
        queue: EventQueue,
        config: dict,
        interactive: bool = True,
    ):
        self.queue = queue
        self.config = config
        self.interactive = interactive

        self._status = AdapterStatus(connected=False, detail="modo teste")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        self._like_total = 0
        self._autor = random.choice(USUARIOS_EXEMPLO)

    @property
    def status(self) -> AdapterStatus:
        return self._status

    def start(self) -> None:
        self._status = AdapterStatus(connected=True, detail="modo teste")
        logger.info("Modo TESTE ativo. Nenhuma conexao com o TikTok.")
        if not self.interactive:
            # Sem terminal: nao abrir thread de leitura. `input()` num
            # processo sem stdin levantaria ou travaria em laco.
            return
        print(AJUDA)
        self._thread = threading.Thread(target=self._loop, name="simulado", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._status = AdapterStatus(connected=False, detail="encerrado")
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                linha = input()
            except (EOFError, KeyboardInterrupt):
                break
            except Exception:
                time.sleep(0.1)
                continue

            comando = linha.strip().lower()
            if comando in {"quit", "sair", "exit"}:
                self._stop.set()
                break
            if comando == "auto":
                run_burst(self.queue, self.config, count=50)
                continue
            if comando == "help":
                print(AJUDA)
                continue

            evento = self.handle_line(linha)
            if evento is None and linha.strip():
                print("Nao entendi. Digite 'help'.")

    # ---------- traducao de linha em evento ----------

    def handle_line(self, linha: str) -> LiveEvent | None:
        evento = parse_command(linha, autor=self._autor, like_total=self._like_total)
        if evento is None:
            return None

        if evento.type == EventType.LIKE:
            self._like_total = evento.like_total
        elif evento.username:
            self._autor = evento.username

        logger.info(
            "SIMULADO | tipo=%s | autor=%s | texto=%s | presente=%s | qtd=%s",
            evento.type.value,
            evento.actor(),
            evento.text,
            evento.gift_name,
            evento.quantity,
        )
        self.queue.put(evento)
        return evento


def _autor_do_evento(autor: str) -> str:
    return autor or "voce"


def parse_command(
    linha: str,
    autor: str = "voce",
    like_total: int = 0,
) -> LiveEvent | None:
    """Traduz uma linha digitada em LiveEvent.

    Retorna None para linhas vazias ou de controle (help/quit/auto).
    """
    texto = (linha or "").strip()
    if not texto:
        return None

    partes = texto.split()
    primeiro = partes[0].lower()

    if primeiro in _CONTROLE:
        return None

    if primeiro == "user" and len(partes) >= 2:
        novo_autor = partes[1]
        resto = " ".join(partes[2:]).strip()
        if not resto:
            return None
        return parse_command(resto, autor=novo_autor, like_total=like_total)

    quem = _autor_do_evento(autor)

    if primeiro == "follow":
        return LiveEvent(type=EventType.FOLLOW, username=quem, display_name=quem)

    if primeiro == "share":
        return LiveEvent(type=EventType.SHARE, username=quem, display_name=quem)

    if primeiro == "like":
        delta = 1
        if len(partes) >= 2:
            try:
                delta = max(1, int(partes[1]))
            except ValueError:
                delta = 1
        return LiveEvent(
            type=EventType.LIKE,
            username=quem,
            display_name=quem,
            like_delta=delta,
            like_total=like_total + delta,
            quantity=delta,
        )

    # Comentario entre aspas: o resto inteiro e o texto.
    if texto.startswith('"') and texto.endswith('"') and len(texto) > 1:
        return LiveEvent(type=EventType.COMMENT, username=quem, display_name=quem, text=texto[1:-1])

    # "NomeDoPresente [qtd]" quando a primeira palavra nao e um comando.
    # Duas palavras e o maximo: "bom dia galera" e comentario, nao presente.
    if primeiro not in COMANDOS_EXEMPLO and len(partes) <= 2:
        quantidade = 1
        if len(partes) == 2:
            try:
                quantidade = max(1, int(partes[1]))
            except ValueError:
                quantidade = 1  # "Rose muito" ainda e presente, sem quantidade
        return LiveEvent(
            type=EventType.GIFT,
            username=quem,
            display_name=quem,
            gift_name=partes[0],
            quantity=quantidade,
        )

    return LiveEvent(type=EventType.COMMENT, username=quem, display_name=quem, text=texto)


def run_burst(queue: EventQueue, config: dict, count: int = 500) -> None:
    """Rajada aleatoria. Existe para PROVAR o anti-spam: se travar, falhou."""
    total_likes = 0
    for _ in range(count):
        autor = random.choice(USUARIOS_EXEMPLO)
        escolha = random.random()

        if escolha < 0.45:
            evento = LiveEvent(
                type=EventType.GIFT,
                username=autor,
                display_name=autor,
                gift_name=random.choice(PRESENTES_EXEMPLO),
                quantity=random.choice([1, 1, 1, 5, 10, 100]),
            )
        elif escolha < 0.75:
            evento = LiveEvent(
                type=EventType.COMMENT,
                username=autor,
                display_name=autor,
                text=random.choice(COMANDOS_EXEMPLO),
            )
        elif escolha < 0.9:
            delta = random.randint(1, 20)
            total_likes += delta
            evento = LiveEvent(
                type=EventType.LIKE,
                username=autor,
                display_name=autor,
                like_delta=delta,
                like_total=total_likes,
            )
        elif escolha < 0.96:
            evento = LiveEvent(type=EventType.FOLLOW, username=autor, display_name=autor)
        else:
            evento = LiveEvent(type=EventType.SHARE, username=autor, display_name=autor)

        queue.put(evento)

    logger.info("Rajada de %s eventos enviada.", count)
