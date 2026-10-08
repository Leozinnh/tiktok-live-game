import json
import math

from game.entities import Boss, Character, Enemy
from game.state import GameState


def test_inimigo_dentro_do_raio_atinge_o_personagem():
    inimigo = Enemy(x=105.0, y=900.0)
    assert inimigo.reached(100.0, 900.0, raio=30.0)


def test_inimigo_longe_nao_atinge():
    assert not Enemy(x=500.0, y=900.0).reached(100.0, 900.0, raio=30.0)


def test_boss_comeca_com_hp_cheio_e_e_um_inimigo():
    boss = Boss(x=540.0, y=600.0, hp=500, max_hp=500)
    assert boss.is_alive()
    assert boss.hp_fraction() == 1.0
    assert isinstance(boss, Enemy)


def test_boss_meio_vivo():
    boss = Boss(x=0, y=0, hp=250, max_hp=500)
    assert math.isclose(boss.hp_fraction(), 0.5)


def test_boss_com_hp_zero_esta_morto():
    assert not Boss(x=0, y=0, hp=0, max_hp=500).is_alive()


def test_character_tem_estado_de_pulo():
    c = Character()
    assert c.y_offset == 0.0


def test_gamestate_to_dict_e_serializavel_em_json():
    estado = GameState()
    estado.enemies.append(Enemy(x=1.0, y=2.0))
    d = estado.to_dict()
    json.dumps(d)  # nao pode levantar
    assert d["hp"] == estado.hp
    assert len(d["enemies"]) == 1


def test_gamestate_to_dict_nao_expoe_objetos_do_pygame():
    d = GameState().to_dict()
    for chave, valor in d.items():
        assert not type(valor).__module__.startswith("pygame"), chave
