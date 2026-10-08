"""A area de jogo comeca abaixo do HUD.

O bug que estes testes travam: inimigos nasciam em y=-120..120 e o chefe em
y=200, ou seja, ATRAS do HUD (que vai ate y=320). O HUD ficava coberto por
sprites do jogo.
"""

from game.engine import GameEngine


def _engine(**app) -> GameEngine:
    config = {
        "app": {"window_width": 1080, "window_height": 1920, **app},
        "game": {"max_hp": 100, "initial_hp": 100, "initial_speed": 220},
        "limits": {"max_enemies": 40},
    }
    return GameEngine(config)


def test_o_topo_do_campo_vem_do_config():
    assert _engine(hud_height=400).topo == 400
    assert _engine().topo == 320


def test_inimigos_nascem_abaixo_do_hud():
    e = _engine(hud_height=320)
    assert e.spawn_enemy(20) == 20
    assert e.state.enemies
    for inimigo in e.state.enemies:
        assert inimigo.y - inimigo.radius >= e.topo


def test_o_chefe_nao_invade_o_hud():
    e = _engine(hud_height=320)
    boss = e.spawn_boss()
    assert boss.y + boss.radius <= e.altura
    assert boss.y - boss.radius >= e.topo


def test_o_campo_ainda_vai_ate_o_personagem():
    e = _engine(hud_height=320)
    assert e.topo < e.state.character.y
