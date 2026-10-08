from core.events import EventType, LiveEvent
from core.ratelimit import RateLimiter
from core.rules import RuleEngine, normalize
from game.engine import GameEngine


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def avanca(self, dt: float) -> None:
        self.t += dt


def _config(regras: dict) -> dict:
    base = {"gifts": [], "comments": [], "likes": [], "follows": [], "shares": []}
    base.update(regras)
    return {
        "app": {"window_width": 1080, "feed_size": 6},
        "game": {
            "max_hp": 100, "initial_hp": 100, "initial_speed": 220,
            "xp_per_level": 100, "xp_level_step": 25, "base_enemy_damage": 5,
        },
        "limits": {"max_enemies": 10, "action_budget": {"spawn_enemy": 2.0}},
        "rules": base,
    }


def _montar(regras: dict, relogio=None):
    relogio = relogio or Relogio()
    cfg = _config(regras)
    game = GameEngine(cfg, now_fn=relogio)
    limiter = RateLimiter(action_budget=cfg["limits"]["action_budget"], now_fn=relogio)
    return RuleEngine(cfg, game, limiter), game, relogio


def test_normalize_remove_acento_e_caixa():
    assert normalize("CORREÇÃO") == "correcao"
    assert normalize("  Corre  ") == "corre"


def test_comentario_dispara_acao():
    engine, game, _ = _montar({"comments": [{"contains": "corre", "action": "run", "duration": 3}]})
    engine.process(LiveEvent(type=EventType.COMMENT, username="maria", text="corre"))
    assert game.state.effects.active("run")


def test_comentario_com_emoji_e_caixa_ainda_casa():
    engine, game, _ = _montar({"comments": [{"contains": "corre", "action": "run", "duration": 3}]})
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="CORRE!!! 🏃"))
    assert game.state.effects.active("run")


def test_comentario_acentuado_casa_regra_sem_acento():
    engine, game, _ = _montar({"comments": [{"contains": "corre", "action": "run", "duration": 3}]})
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="corré"))
    assert game.state.effects.active("run")


def test_comentario_sem_regra_nao_faz_nada():
    engine, game, _ = _montar({"comments": []})
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="oi"))
    assert game.state.xp == 0


def test_comentario_de_direita_empurra_a_intencao():
    engine, game, _ = _montar(
        {"comments": [{"contains": "direita", "action": "steer", "amount": 1}]}
    )
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="direita"))
    assert game.intent() > 0


def test_comentario_de_esquerda_empurra_para_o_outro_lado():
    engine, game, _ = _montar(
        {"comments": [{"contains": "esquerda", "action": "steer", "amount": -1}]}
    )
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="esquerda"))
    assert game.intent() < 0


def test_horda_de_direita_nao_estoura_a_intencao():
    engine, game, _ = _montar(
        {"comments": [{"contains": "direita", "action": "steer", "amount": 1, "per_user_cooldown": 0}]}
    )
    for i in range(500):
        engine.process(LiveEvent(type=EventType.COMMENT, username=f"u{i}", text="direita"))
    assert abs(game.intent()) <= 3.0


def test_presente_por_nome():
    engine, game, _ = _montar({"gifts": [{"gift": "Rose", "action": "xp", "xp": 5}]})
    engine.process(LiveEvent(type=EventType.GIFT, username="joao", gift_name="Rose"))
    assert game.state.xp == 5


def test_presente_por_id_quando_o_nome_nao_bate():
    engine, game, _ = _montar({"gifts": [{"gift": "Rose", "gift_id": "5655", "action": "xp", "xp": 7}]})
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Outro", gift_id="5655"))
    assert game.state.xp == 7


def test_presente_desconhecido_e_ignorado_em_silencio():
    engine, game, _ = _montar({"gifts": [{"gift": "Rose", "action": "xp", "xp": 5}]})
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Foguete"))
    assert game.state.xp == 0
    assert game.state.announcements.active() == []


def test_presente_sem_nome_nem_id_e_ignorado():
    engine, game, _ = _montar({"gifts": [{"gift": "Rose", "action": "xp", "xp": 5}]})
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="", gift_id=None))
    assert game.state.xp == 0


def test_min_quantity_bloqueia_abaixo_do_limite():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "xp", "xp": 5, "min_quantity": 10}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=9))
    assert game.state.xp == 0


def test_min_quantity_libera_no_limite():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "xp", "xp": 5, "min_quantity": 10}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=10))
    # `min_quantity` e um portao, nao um multiplicador: escalar pelo
    # quantity exige `scale_with_quantity` (ver test_scale_with_quantity_*).
    assert game.state.xp == 5


def test_scale_with_quantity_multiplica():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "xp", "xp": 5,
                    "scale_with_quantity": True, "max_multiplier": 10}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=4))
    assert game.state.xp == 20


def test_scale_with_quantity_respeita_o_teto():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "xp", "xp": 5,
                    "scale_with_quantity": True, "max_multiplier": 3}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=100))
    assert game.state.xp == 15


def test_scale_with_quantity_sem_teto_nao_escala():
    # A config.json exige o teto; isto e a rede de seguranca para uma regra
    # que chegue por outro caminho.
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "xp", "xp": 5, "scale_with_quantity": True}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=100))
    assert game.state.xp == 5


def test_sem_scale_quantity_o_valor_e_unico():
    engine, game, _ = _montar({"gifts": [{"gift": "Rose", "action": "xp", "xp": 5}]})
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=4))
    assert game.state.xp == 5


def test_max_multiplier_limita_o_estouro():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "xp", "xp": 5,
                    "scale_with_quantity": True, "max_multiplier": 10}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose", quantity=500))
    assert game.state.xp == 50


def test_cooldown_de_presente_bloqueia_repeticao():
    engine, game, relogio = _montar(
        {"gifts": [{"gift": "Rose", "action": "spawn_enemy", "amount": 1, "cooldown": 2.0}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose"))
    engine.process(LiveEvent(type=EventType.GIFT, username="j", gift_name="Rose"))
    assert len(game.state.enemies) == 1


def test_cooldown_por_usuario_nao_puniu_outro_usuario():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Rose", "action": "spawn_enemy", "amount": 1, "per_user_cooldown": 5.0}]}
    )
    engine.process(LiveEvent(type=EventType.GIFT, username="joao", gift_name="Rose"))
    engine.process(LiveEvent(type=EventType.GIFT, username="maria", gift_name="Rose"))
    assert len(game.state.enemies) == 2


def test_orcamento_global_segura_rajada_de_usuarios_diferentes():
    engine, game, _ = _montar(
        {"gifts": [{"gift": "Cap", "action": "spawn_enemy", "amount": 1, "per_user_cooldown": 0}]}
    )
    for i in range(50):
        engine.process(LiveEvent(type=EventType.GIFT, username=f"u{i}", gift_name="Cap"))
    assert len(game.state.enemies) == 2  # action_budget["spawn_enemy"] == 2.0


def test_like_milestones_disparam_exatamente_uma_vez_cada():
    engine, game, _ = _montar({"likes": [{"every": 100, "action": "xp", "xp": 20}]})
    engine.process(LiveEvent(type=EventType.LIKE, username="a", like_delta=90, like_total=90))
    assert game.state.xp == 0
    engine.process(LiveEvent(type=EventType.LIKE, username="a", like_delta=260, like_total=350))
    assert game.state.xp == 60  # 100, 200 e 300


def test_repetir_o_mesmo_total_nao_dispara_de_novo():
    engine, game, _ = _montar({"likes": [{"every": 100, "action": "xp", "xp": 20}]})
    engine.process(LiveEvent(type=EventType.LIKE, username="a", like_delta=100, like_total=100))
    assert game.state.xp == 20
    engine.process(LiveEvent(type=EventType.LIKE, username="a", like_delta=0, like_total=100))
    assert game.state.xp == 20


def test_total_que_regride_e_ignorado():
    engine, game, _ = _montar({"likes": [{"every": 100, "action": "xp", "xp": 20}]})
    engine.process(LiveEvent(type=EventType.LIKE, username="a", like_delta=300, like_total=300))
    assert game.state.xp == 60
    engine.process(LiveEvent(type=EventType.LIKE, username="a", like_delta=0, like_total=50))
    assert game.state.xp == 60


def test_milestone_com_cooldown_nao_e_engolido():
    # Regressao: o cooldown da regra nao pode descartar o 2o milestone.
    engine, game, _ = _montar(
        {"likes": [{"every": 100, "action": "xp", "xp": 20, "cooldown": 5.0}]}
    )
    engine.process(LiveEvent(type=EventType.LIKE, username="a", like_delta=300, like_total=300))
    assert game.state.xp == 60


def test_like_sem_usuario_nao_quebra():
    engine, game, _ = _montar({"likes": [{"every": 100, "action": "xp", "xp": 20}]})
    engine.process(LiveEvent(type=EventType.LIKE, username="", like_delta=150, like_total=150))
    assert game.state.xp == 20


def test_follow_da_xp():
    engine, game, _ = _montar({"follows": [{"action": "xp", "xp": 15}]})
    engine.process(LiveEvent(type=EventType.FOLLOW, username="carlos"))
    assert game.state.xp == 15


def test_share_da_xp():
    engine, game, _ = _montar({"shares": [{"action": "xp", "xp": 10}]})
    engine.process(LiveEvent(type=EventType.SHARE, username="lucas"))
    assert game.state.xp == 10


def test_evento_de_sistema_nao_faz_nada():
    engine, game, _ = _montar({"follows": [{"action": "xp", "xp": 15}]})
    engine.process(LiveEvent(type=EventType.SYSTEM, text="connected"))
    assert game.state.xp == 0


def test_erro_em_uma_regra_nao_derruba_o_processamento():
    engine, game, _ = _montar({"comments": [{"contains": "x", "action": "xp", "xp": "nao e numero"}]})
    engine.process(LiveEvent(type=EventType.COMMENT, username="m", text="x"))
    # Nao levantou; o loop do jogo continua.
    assert game.state.level == 1


def test_likes_sao_contados_uma_vez_por_evento():
    # Uma rajada que cruza tres marcos chamava apply_action tres vezes e o
    # HUD mostrava 900 likes para um evento de 300.
    engine, game, _ = _montar({"likes": [{"every": 100, "action": "xp", "xp": 20}]})
    engine.process(
        LiveEvent(type=EventType.LIKE, username="m", like_total=300, like_delta=300)
    )
    assert game.state.total_likes == 300
    assert game.state.xp == 60  # tres marcos, 20 XP cada


def test_likes_mostram_o_total_da_live_e_nao_encolhem():
    engine, game, _ = _montar({"likes": [{"every": 100, "action": "xp", "xp": 20}]})
    for total in (100, 200, 300, 250):
        engine.process(LiveEvent(type=EventType.LIKE, username="m", like_total=total))
    assert game.state.total_likes == 300
