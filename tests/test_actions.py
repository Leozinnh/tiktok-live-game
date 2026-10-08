from core.events import EventType, LiveEvent
from game.actions import known_actions
from game.engine import GameEngine

CONFIG = {
    "game": {
        "max_hp": 100,
        "initial_hp": 100,
        "initial_speed": 220,
        "xp_per_level": 100,
        "xp_level_step": 25,
        "base_enemy_damage": 5,
    },
    "limits": {"max_enemies": 5},
}


def _evento(tipo=EventType.GIFT, **kw):
    return LiveEvent(type=tipo, username="joao", **kw)


def test_todas_as_acoes_do_contrato_existem():
    esperadas = {
        "xp", "heal", "damage", "run", "jump", "speed",
        "shield", "rage", "spawn_enemy", "special", "boss", "mega",
    }
    assert esperadas <= known_actions()


def test_acao_xp():
    e = GameEngine(CONFIG)
    e.apply_action("xp", {"xp": 40}, _evento())
    assert e.state.xp == 40


def test_acao_heal_nao_passa_do_maximo():
    e = GameEngine(CONFIG)
    e.damage(50)
    e.apply_action("heal", {"amount": 999}, _evento())
    assert e.state.hp == e.state.max_hp


def test_acao_damage():
    e = GameEngine(CONFIG)
    e.apply_action("damage", {"amount": 25}, _evento())
    assert e.state.hp == 75


def test_acao_shield_bloqueia_dano():
    e = GameEngine(CONFIG)
    e.apply_action("shield", {"duration": 5}, _evento())
    e.damage(30)
    assert e.state.hp == 100


def test_acao_spawn_enemy_cria_inimigos():
    e = GameEngine(CONFIG)
    e.apply_action("spawn_enemy", {"amount": 3}, _evento())
    assert len(e.state.enemies) == 3


def test_spawn_enemy_respeita_o_teto_de_entidades():
    e = GameEngine(CONFIG)  # max_enemies = 5
    e.apply_action("spawn_enemy", {"amount": 500}, _evento())
    assert len(e.state.enemies) == 5


def test_teto_de_entidades_vale_entre_chamadas():
    e = GameEngine(CONFIG)
    for _ in range(20):
        e.apply_action("spawn_enemy", {"amount": 2}, _evento())
    assert len(e.state.enemies) <= 5


def test_acao_boss_cria_um_boss():
    e = GameEngine(CONFIG)
    e.apply_action("boss", {}, _evento())
    assert e.state.boss is not None
    assert e.state.boss.hp > 0


def test_boss_nao_duplica_se_um_ja_existe():
    e = GameEngine(CONFIG)
    e.apply_action("boss", {}, _evento())
    primeiro = e.state.boss
    e.apply_action("boss", {}, _evento())
    assert e.state.boss is primeiro


def test_acao_mega_empurra_anuncio_grande():
    e = GameEngine(CONFIG)
    e.apply_action("mega", {"duration": 8}, _evento())
    assert any(a.big for a in e.state.announcements.active())


def test_acao_especial_empurra_anuncio():
    e = GameEngine(CONFIG)
    e.apply_action("special", {"duration": 5}, _evento())
    assert any(a.kind == "special" for a in e.state.announcements.active())


def test_acao_desconhecida_nao_levanta_excecao():
    e = GameEngine(CONFIG)
    e.apply_action("nao_existe", {}, _evento())  # nao pode quebrar o loop


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def avanca(self, dt: float) -> None:
        self.t += dt


def test_bonus_de_velocidade_expira_junto_com_o_efeito():
    r = Relogio()
    e = GameEngine(CONFIG, now_fn=r)
    base = e.state.base_speed
    e.apply_action("speed", {"amount": 100, "duration": 2}, _evento())
    assert e.state.speed == base + 100
    r.avanca(3.0)
    e.update(0.0)
    assert e.state.speed == base


def test_contadores_por_tipo_de_evento():
    e = GameEngine(CONFIG)
    e.apply_action("xp", {"xp": 1}, _evento(EventType.GIFT, quantity=3))
    e.apply_action("xp", {"xp": 1}, _evento(EventType.FOLLOW))
    e.apply_action("xp", {"xp": 1}, _evento(EventType.SHARE))
    e.apply_action("xp", {"xp": 1}, _evento(EventType.LIKE, like_delta=7))
    assert e.state.total_gifts == 3
    assert e.state.total_followers == 1
    assert e.state.total_shares == 1
    assert e.state.total_likes == 7
