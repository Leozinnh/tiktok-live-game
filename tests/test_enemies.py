"""Inimigos nao podem virar um bolo so.

O bug que estes testes travam: todo inimigo persegue o MESMO ponto — o
centro do personagem. Como nao ha nada que os separe, a distancia entre
eles tende a zero conforme se aproximam, e os nove viram um so. Medido
antes do conserto, o espalhamento em x caia de 679 unidades no nascimento
para 92 na chegada, com os sprites todos sobrepostos.

O publico via um inimigo em vez de nove — e o jogo ficava mais facil do
que o HUD dizia.
"""

import math
import random
from itertools import combinations

from game.engine import GameEngine
from game.entities import Enemy


def _engine(**game) -> GameEngine:
    config = {
        "app": {"window_width": 1080, "window_height": 1920},
        "game": {"max_hp": 100, "initial_hp": 100, "initial_speed": 220, **game},
        "limits": {"max_enemies": 40},
    }
    return GameEngine(config)


def test_dois_inimigos_no_mesmo_ponto_se_separam():
    """O caso extremo, sem sorteio: dois inimigos exatamente sobrepostos.

    Sem separacao nenhuma, os dois andam juntos para sempre — a distancia
    entre eles fica zero em todos os quadros seguintes.
    """
    e = _engine()
    e.state.enemies = [Enemy(x=500.0, y=900.0), Enemy(x=500.0, y=900.0)]

    for _ in range(30):
        e.update(1 / 60)

    a, b = e.state.enemies
    assert math.dist((a.x, a.y), (b.x, b.y)) >= Enemy.radius * 2 - 1.0


def test_inimigos_nunca_se_sobrepoem():
    """A separacao vale para o bando inteiro, em todos os quadros."""
    random.seed(20261008)  # `spawn_enemy` sorteia as posicoes iniciais
    e = _engine()
    e.spawn_enemy(9)
    e.update(1 / 60)  # o primeiro quadro ja resolve as sobreposicoes do sorteio

    for _ in range(60 * 14):
        e.update(1 / 60)
        vivos = e.state.enemies
        for a, b in combinations(vivos, 2):
            d = math.dist((a.x, a.y), (b.x, b.y))
            assert d >= Enemy.radius * 2 - 2.0, f"dois inimigos a {d:.1f} um do outro"


# Havia um terceiro teste aqui, medindo o diametro da nuvem na chegada. Ele
# foi removido porque NAO pegava o bug: sem separacao nenhuma ele passava,
# porque o espalhamento vertical (eles saem de distancias diferentes e
# chegam em instantes diferentes) ja era maior que o limite. Um teste que
# passa antes do conserto nao prova nada — e o de cima ja mede o que
# importa, a sobreposicao.
