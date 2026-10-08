"""HTTP e WebSocket do renderer 3D.

Sobe em threads proprias, ao lado do loop do jogo. A regra que organiza
tudo aqui: **o loop do jogo nunca espera por soquete**.

`publicar()` e chamado a 60 quadros por segundo pelo loop e nao envia
nada — so guarda o ultimo retrato numa variavel, sob trava. Quem enxerga
a rede e uma thread separada, que acorda 20 vezes por segundo, pega o
retrato mais recente e escreve para os navegadores conectados.

A consequencia pratica: um navegador travado, uma aba em segundo plano ou
um cabo de rede puxado nao seguram o jogo. O retrato antigo e simplesmente
substituido pelo proximo — e um instantaneo, nao uma fila, entao nao ha
atraso acumulado: quando o navegador voltar, ele recebe o estado de AGORA,
nao os 400 quadros que perdeu.
"""

import json
import logging
import threading
import time
from http import HTTPStatus
from pathlib import Path

from websockets.datastructures import Headers
from websockets.http11 import Response
from websockets.sync.server import serve

logger = logging.getLogger(__name__)

# Tipos servidos pelo HTTP embutido. Sem isto o navegador recusa o modulo
# ES do Three.js, que exige `text/javascript`.
TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}

PADRAO = "application/octet-stream"


def pasta_web() -> Path:
    """A pasta `web/`, ao lado da raiz do projeto."""
    return Path(__file__).resolve().parent.parent / "web"


class ServidorWeb:
    """Serve `web/` por HTTP e publica retratos por WebSocket."""

    def __init__(
        self,
        pasta: Path | str | None = None,
        host: str = "127.0.0.1",
        porta: int = 8765,
        taxa: float = 20.0,
    ):
        self.pasta = Path(pasta) if pasta is not None else pasta_web()
        self.host = host
        self.porta = int(porta)
        self.taxa = max(1.0, float(taxa))

        self._ultimo: dict | None = None
        self._trava = threading.Lock()
        self._parar = threading.Event()
        self._servidor = None
        self._threads: list[threading.Thread] = []

    # ---------- API do loop do jogo ----------

    def publicar(self, dados: dict) -> None:
        """Guarda o retrato mais recente. Nao bloqueia e nao envia nada.

        Chamado 60 vezes por segundo: o retrato anterior e descartado sem
        cerimonia. Se o envio fosse feito aqui, um navegador lento viraria
        queda de FPS no jogo.
        """
        with self._trava:
            self._ultimo = dados

    def espectadores(self) -> int:
        """Quantos navegadores estao conectados agora."""
        if self._servidor is None:
            return 0
        return len(self._servidor.connections)

    # ---------- ciclo de vida ----------

    def iniciar(self) -> "ServidorWeb":
        self._servidor = serve(
            self._atender,
            self.host,
            self.porta,
            process_request=self._responder_http,
            # O padrao do websockets e 10 s: o `shutdown()` espera esse tempo
            # todo por qualquer conexao que o cliente nao fechou. Sao 10
            # segundos de espera ao apertar ESC por causa de um navegador
            # parado. Aqui a gente ja esta desligando — nao ha nada a
            # negociar com quem ficou.
            close_timeout=1,
        )
        # `porta=0` deixa o sistema escolher uma livre; descobrimos qual foi.
        self.porta = self._servidor.socket.getsockname()[1]

        for alvo, nome in (
            (self._servidor.serve_forever, "web-http"),
            (self._laco_de_envio, "web-envio"),
        ):
            thread = threading.Thread(target=alvo, name=nome, daemon=True)
            thread.start()
            self._threads.append(thread)

        logger.info(
            "Renderer web no ar | http://%s:%s/ | %s quadros/s",
            self.host,
            self.porta,
            int(self.taxa),
        )
        return self

    def parar(self) -> None:
        self._parar.set()
        if self._servidor is not None:
            # Fecha o soquete, derruba os navegadores e espera os handlers.
            self._servidor.shutdown()
            self._servidor = None
        for thread in self._threads:
            thread.join(timeout=2.0)
        self._threads.clear()

    def __enter__(self) -> "ServidorWeb":
        return self.iniciar()

    def __exit__(self, *_) -> None:
        self.parar()

    # ---------- HTTP ----------

    def _responder_http(self, conexao, requisicao):
        """Responde os arquivos. Devolver None entrega a conexao ao WebSocket."""
        caminho = requisicao.path.split("?", 1)[0]
        if caminho in {"/ws", "/ws/"}:
            return None
        if caminho in {"", "/"}:
            caminho = "/index.html"

        arquivo = self._resolver(caminho)
        if arquivo is None:
            return conexao.respond(HTTPStatus.NOT_FOUND, "nao encontrado")

        try:
            corpo = arquivo.read_bytes()
        except OSError as erro:
            logger.warning("Falha lendo %s: %s", arquivo, erro)
            return conexao.respond(HTTPStatus.INTERNAL_SERVER_ERROR, "erro de leitura")

        cabecalhos = Headers()
        cabecalhos["Content-Type"] = TIPOS.get(arquivo.suffix.lower(), PADRAO)
        cabecalhos["Content-Length"] = str(len(corpo))
        # Sem cache: o usuario edita o JS e recarrega a pagina durante a LIVE.
        # Um 304 teimoso aqui vira "minha mudanca nao aparece" por meia hora.
        cabecalhos["Cache-Control"] = "no-store, must-revalidate"
        # Sem keep-alive: sao seis arquivos pequenos servidos de localhost, e
        # a reutilizacao de conexao nao paga o preco. Em troca, o navegador
        # nao fica segurando soquete aberto — o que segurava o desligamento.
        cabecalhos["Connection"] = "close"
        return Response(HTTPStatus.OK, "OK", cabecalhos, corpo)

    def _resolver(self, caminho: str) -> Path | None:
        """Converte a URL em arquivo, recusando quem tenta sair da pasta."""
        relativo = caminho.lstrip("/")
        candidato = (self.pasta / relativo).resolve()
        raiz = self.pasta.resolve()
        if not candidato.is_file() or raiz not in candidato.parents:
            return None
        return candidato

    # ---------- WebSocket ----------

    def _atender(self, conexao) -> None:
        logger.info("Navegador conectado: %s", getattr(conexao, "remote_address", "?"))
        # Manda o estado atual na hora: sem isto a cena nasce vazia e so
        # aparece no proximo retrato, com o personagem pulando de lugar.
        with self._trava:
            atual = self._ultimo
        if atual is not None:
            try:
                conexao.send(json.dumps(atual))
            except Exception:
                logger.debug("Falha no retrato inicial", exc_info=True)
        try:
            # O navegador nao manda nada. Ler ate o fim e o que mantem a
            # conexao viva e detecta o fechamento da aba.
            for _ in conexao:
                pass
        except Exception:
            logger.debug("Conexao encerrada com erro", exc_info=True)
        finally:
            logger.info("Navegador desconectado")

    def _laco_de_envio(self) -> None:
        intervalo = 1.0 / self.taxa
        while not self._parar.is_set():
            inicio = time.monotonic()

            with self._trava:
                dados = self._ultimo
                self._ultimo = None

            if dados is not None and self._servidor is not None:
                try:
                    mensagem = json.dumps(dados)
                except (TypeError, ValueError):
                    logger.exception("Retrato nao serializavel; descartado")
                    mensagem = None
                if mensagem is not None:
                    for conexao in list(self._servidor.connections):
                        try:
                            conexao.send(mensagem)
                        except Exception:
                            # Um navegador morto nao pode derrubar o envio
                            # para os outros.
                            logger.debug("Falha enviando", exc_info=True)

            sobra = intervalo - (time.monotonic() - inicio)
            if sobra > 0:
                self._parar.wait(sobra)
