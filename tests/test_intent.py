import pytest

from core.events import EventType, LiveEvent
from game.engine import GameEngine
from game.entities import Enemy

CONFIG = {
    "game": {
        "max_hp": 100,
        "initial_hp": 100,
        "initial_speed": 220,
        "xp_per_level": 100,
        "xp_level_step": 25,
        "base_enemy_damage": 5,
        "intent_half_life": 1.5,
        "intent_accel": 1800.0,
        "intent_max_speed": 420.0,
        "intent_friction": 6.0,
    },
    "limits": {"max_enemies": 10},
}


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def avanca(self, dt: float) -> None:
        self.t += dt


def _engine(relogio=None):
    return GameEngine(CONFIG, now_fn=relogio or Relogio())


def test_sem_comando_o_personagem_nao_dispara():
    e = _engine()
    x0 = e.state.character.x
    for _ in range(10):
        e.update(1 / 60)
    assert abs(e.state.character.x - x0) < 1.0


def test_comando_move_o_personagem_para_a_direita():
    e = _engine()
    x0 = e.state.character.x
    e.steer(+1)
    for _ in range(60):
        e.update(1 / 60)
    assert e.state.character.x > x0


def test_comando_move_para_a_esquerda():
    e = _engine()
    x0 = e.state.character.x
    e.steer(-1)
    for _ in range(60):
        e.update(1 / 60)
    assert e.state.character.x < x0


def test_personagem_acelera_em_vez_de_teleportar():
    e = _engine()
    x0 = e.state.character.x
    e.steer(+1)
    e.update(1 / 60)
    # Um unico frame nao pode jogar o personagem do outro lado da tela.
    assert e.state.character.x - x0 < 30.0


def test_intencoes_opostas_se_cancelam():
    e = _engine()
    e.steer(+1)
    e.steer(-1)
    assert abs(e.intent()) < 0.5


def test_intencao_decai_com_o_tempo():
    relogio = Relogio()
    e = _engine(relogio)
    e.steer(+1)
    forte = abs(e.intent())
    relogio.avanca(3.0)
    for _ in range(10):
        e.update(1 / 60)
    assert abs(e.intent()) < forte


def test_intencao_nao_explode_com_spam_de_comentarios():
    e = _engine()
    for _ in range(500):
        e.steer(+1)
    assert abs(e.intent()) <= 3.0


def test_personagem_nao_sai_da_tela():
    e = _engine()
    e.steer(+1)
    for _ in range(600):
        e.update(1 / 60)
    assert e.state.character.x <= 1080
    e.steer(-1)
    for _ in range(600):
        e.update(1 / 60)
    assert e.state.character.x >= 0


def test_inimigo_desce_em_direcao_ao_personagem():
    e = _engine()
    e.state.enemies.append(Enemy(x=540.0, y=100.0))
    y0 = e.state.enemies[0].y
    e.update(1 / 60)
    assert e.state.enemies[0].y > y0


def test_inimigo_que_alcanca_causa_dano_e_some():
    e = _engine()
    alvo = e.state.character
    e.state.enemies.append(Enemy(x=alvo.x, y=alvo.y + 10.0))
    e.update(1 / 60)
    assert e.state.hp < 100
    assert len(e.state.enemies) == 0


def test_escudo_bloqueia_dano_de_contato():
    e = _engine()
    e.apply_action("shield", {"duration": 5}, LiveEvent(type=EventType.GIFT))
    alvo = e.state.character
    e.state.enemies.append(Enemy(x=alvo.x, y=alvo.y + 10.0))
    e.update(1 / 60)
    assert e.state.hp == 100


def test_pulo_afeta_o_y_offset_e_volta_ao_chao():
    relogio = Relogio()
    e = _engine(relogio)
    e.apply_action("jump", {"duration": 0.8}, LiveEvent(type=EventType.GIFT))
    for _ in range(10):
        relogio.avanca(1 / 60)
        e.update(1 / 60)
    assert e.state.character.y_offset > 0
    relogio.avanca(2.0)
    e.update(1 / 60)
    assert e.state.character.y_offset == 0.0


def test_boss_recebe_dano_e_morre():
    e = _engine()
    boss = e.spawn_boss()
    boss.hp = 1
    e.apply_action("damage", {"amount": 50}, LiveEvent(type=EventType.GIFT))
    e.update(1 / 60)
    assert e.state.boss is None or not e.state.boss.is_alive()


def test_update_com_dt_grande_nao_quebra():
    e = _engine()
    e.steer(+1)
    e.update(5.0)  # uma pausa longa nao pode explodir a simulacao
    assert 0 <= e.state.character.x <= 1080


def _par(velocidade_extra=None, subir_de_nivel=False):
    """(motor, relogio) com o MESMO relogio nos dois."""
    relogio = Relogio()
    e = _engine(relogio)
    if velocidade_extra is not None:
        e.grant_speed(velocidade_extra, 30.0)
    if subir_de_nivel:
        e.add_xp(e.xp_para_subir(1))
    return e, relogio


def _vx_em_regime(e, relogio, passos=45):
    """Velocidade do personagem depois de acelerar ate estabilizar.

    Fica dentro do `intent_half_life` (1.5s) e longe da parede: assim a
    medida isola a velocidade, sem a intencao decair nem o personagem
    bater na borda e zerar o `vx`.
    """
    e.steer(+1)
    for _ in range(passos):
        e.update(1 / 60)
        relogio.avanca(1 / 60)
    return e.state.character.vx


def test_presente_de_velocidade_acelera_o_personagem():
    # O `speed` era placebo: `state.speed` era escrito e nunca lido, entao
    # o presente nao mudava nada na tela.
    e_lento, r1 = _par()
    base = _vx_em_regime(e_lento, r1)

    e_rapido, r2 = _par(velocidade_extra=150)
    rapido = _vx_em_regime(e_rapido, r2)

    assert base > 0
    assert rapido > base * 1.2


def test_o_bonus_de_velocidade_nao_deixa_marca():
    expirado, r1 = _par(velocidade_extra=150)
    r1.avanca(60.0)  # o efeito expira
    depois = _vx_em_regime(expirado, r1)

    limpo, r2 = _par()
    assert depois == pytest.approx(_vx_em_regime(limpo, r2), rel=0.02)


def test_subir_de_nivel_deixa_o_personagem_mais_rapido():
    e, r1 = _par()
    antes = _vx_em_regime(e, r1)

    subiu, r2 = _par(subir_de_nivel=True)
    depois = _vx_em_regime(subiu, r2)

    assert subiu.state.level == 2
    assert depois > antes


def test_o_bonus_de_velocidade_expira():
    e, relogio = _par(velocidade_extra=150)
    assert e.state.speed > e.state.base_speed
    relogio.avanca(60.0)
    e.update(1 / 60)
    assert e.state.speed == e.state.base_speed
