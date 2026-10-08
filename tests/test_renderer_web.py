"""Testes do renderer 3D — so o que quebraria o jogo de verdade.

Tres coisas podem dar errado aqui sem que nada acuse:

1. o retrato publicar algo que o navegador nao consegue ler (nao for JSON
   puro, ou vier com o personagem fora da area de jogo);
2. o servidor entregar um arquivo que nao devia — travessia de caminho;
3. `publicar()` travar o laco do jogo esperando um cliente que nao existe.

O desenho em si (luz, sombra, animacao) nao da para testar sem navegador;
isso fica na verificacao manual.
"""

import json
import time
import urllib.error
import urllib.request

import pytest

from core.events import EventType, LiveEvent
from game.engine import GameEngine
from renderer_web.servidor import ServidorWeb, pasta_web
from renderer_web.snapshot import snapshot


@pytest.fixture
def config():
    return json.loads(pasta_web().parent.joinpath("config.json").read_text(encoding="utf-8"))


@pytest.fixture
def servidor():
    with ServidorWeb(porta=0, taxa=30.0) as s:
        yield s


# --------------------------------------------------------------- o retrato


def test_retrato_e_json_puro(config):
    """O navegador so entende JSON. Qualquer objeto do pygame aqui derruba tudo."""
    jogo = GameEngine(config)
    jogo.spawn_enemy(3)
    jogo.spawn_boss()

    texto = json.dumps(snapshot(jogo.state, time.monotonic()))

    assert len(texto) > 100
    assert json.loads(texto)["enemies"]


def test_retrato_traz_o_que_o_navegador_desenha(config):
    jogo = GameEngine(config)
    jogo.spawn_enemy(2)
    jogo.apply_action("shield", {"duration": 5}, LiveEvent(type=EventType.GIFT))

    retrato = snapshot(jogo.state, time.monotonic(), fila=7)

    assert len(retrato["enemies"]) == 2
    assert "shield" in retrato["effects"]
    assert retrato["status"]["fila"] == 7
    # As coordenadas vao em unidades do jogo, como `GameState.to_dict()` ja
    # entregava: quem converte para o mundo 3D e o renderer.
    assert 0 <= retrato["character"]["x"] <= 1080


def test_retrato_aguenta_estado_cru_sem_efeitos_nem_avisos(config):
    """`GameState()` montado a mao (ferramentas, testes) nao tem esses campos."""
    retrato = snapshot(GameEngine(config).state, time.monotonic())

    assert retrato["effects"] == {}
    assert retrato["announcements"] == []


# --------------------------------------------------------------- o servidor


def test_serve_a_pagina(servidor):
    with urllib.request.urlopen(f"http://127.0.0.1:{servidor.porta}/", timeout=5) as r:
        assert r.status == 200
        assert 'id="arena"' in r.read().decode("utf-8")


@pytest.mark.parametrize("perigoso", ["/../config.json", "/vendor/../../config.json"])
def test_recusa_travessia_de_caminho(servidor, perigoso):
    """O servidor entrega a pasta `web/`, e so ela."""
    with pytest.raises(urllib.error.HTTPError) as erro:
        urllib.request.urlopen(f"http://127.0.0.1:{servidor.porta}{perigoso}", timeout=5)

    assert erro.value.code == 404


def test_modo_web_nao_carrega_pygame():
    """`--web` nao desenha nada com pygame, entao nao pode carregar pygame.

    Com o import no topo do `main.py` ele acontecia sempre — e importar
    pygame abre o SDL. O modo web exigia ambiente grafico sem usar nenhum:
    servidor remoto ou sessao SSH quebravam sem motivo. Roda num processo
    separado porque o proprio pytest ja carregou pygame pelos outros testes.
    """
    import subprocess
    import sys

    saida = subprocess.run(
        [sys.executable, "-c", "import sys, main; print('pygame' in sys.modules)"],
        cwd=pasta_web().parent, capture_output=True, text=True, timeout=60,
    )

    assert saida.stdout.strip() == "False", saida.stderr[-500:]


def test_fechar_o_jogo_nao_espera_navegador(servidor):
    """Apertar ESC tem que fechar na hora, mesmo com conexao pendurada.

    O navegador segura conexoes HTTP abertas para reusar (keep-alive e o
    padrao do HTTP/1.1). Com o `close_timeout` padrao do websockets, o
    `shutdown()` esperava 10 s por elas — ou seja, dez segundos de jogo
    travado toda vez que o streamer apertava ESC.
    """
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{servidor.porta}/nao-existe.js", timeout=5)
    except urllib.error.HTTPError as erro:
        pendurada = erro  # de proposito: ninguem fecha nem le o corpo

    assert pendurada.code == 404
    inicio = time.monotonic()
    servidor.parar()
    gasto = time.monotonic() - inicio

    assert gasto < 3.0, f"fechar levou {gasto:.1f}s"


def test_publicar_nao_espera_cliente(servidor):
    """O laco do jogo publica 20x por segundo e nao pode travar num socket.

    Sem esta garantia, um cliente lento (celular no 3G) trava o jogo
    inteiro — o `publicar()` so guarda o ultimo retrato e quem escreve no
    socket e outra thread.
    """
    inicio = time.monotonic()
    for _ in range(200):
        servidor.publicar({"n": 1})
    gasto = time.monotonic() - inicio

    assert gasto < 0.2, f"200 publicacoes levaram {gasto:.3f}s"
