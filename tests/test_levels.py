from game.engine import GameEngine

CONFIG = {
    "game": {
        "max_hp": 100,
        "initial_hp": 100,
        "initial_xp": 0,
        "initial_level": 1,
        "initial_speed": 220,
        "xp_per_level": 100,
        "xp_level_step": 25,
        "base_enemy_damage": 5,
    },
    "limits": {"max_enemies": 40},
}


def test_curva_de_xp_cresce_por_nivel():
    e = GameEngine(CONFIG)
    assert e.xp_para_subir(1) == 100
    assert e.xp_para_subir(2) == 125
    assert e.xp_para_subir(3) == 150


def test_xp_insuficiente_nao_sobe_de_nivel():
    e = GameEngine(CONFIG)
    e.add_xp(99)
    assert e.state.level == 1
    assert e.state.xp == 99


def test_xp_exato_sobe_de_nivel():
    e = GameEngine(CONFIG)
    e.add_xp(100)
    assert e.state.level == 2
    assert e.state.xp == 0


def test_xp_restante_e_carregado_para_o_proximo_nivel():
    e = GameEngine(CONFIG)
    e.add_xp(120)
    assert e.state.level == 2
    assert e.state.xp == 20


def test_um_presente_grande_sobe_varios_niveis():
    e = GameEngine(CONFIG)
    e.add_xp(100 + 125 + 150 + 10)
    assert e.state.level == 4
    assert e.state.xp == 10


def test_subir_de_nivel_aumenta_max_hp_e_cura():
    e = GameEngine(CONFIG)
    e.damage(50)
    e.add_xp(100)
    assert e.state.max_hp > 100
    assert e.state.hp == e.state.max_hp


def test_subir_de_nivel_empurra_anuncio():
    e = GameEngine(CONFIG)
    e.add_xp(100)
    kinds = [a.kind for a in e.state.announcements.active()]
    assert "levelup" in kinds
    assert any(a.big for a in e.state.announcements.active() if a.kind == "levelup")


def test_xp_zero_ou_negativo_nao_faz_nada():
    e = GameEngine(CONFIG)
    e.add_xp(0)
    e.add_xp(-50)
    assert e.state.xp == 0
    assert e.state.level == 1


def test_dano_reduz_hp():
    e = GameEngine(CONFIG)
    e.damage(30)
    assert e.state.hp == 70


def test_hp_nunca_fica_negativo():
    e = GameEngine(CONFIG)
    e.damage(9999)
    assert e.state.hp >= 0
