from core.ratelimit import RateLimiter


class Relogio:
    """Relogio controlado para testar tempo sem dormir."""

    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def avanca(self, dt: float) -> None:
        self.t += dt


def test_cooldown_de_regra_bloqueia_dentro_da_janela():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    assert rl.allow_rule("gift:Rose", cooldown=2.0, actor="joao", per_user_cooldown=0.0)
    relogio.avanca(1.0)
    assert not rl.allow_rule("gift:Rose", cooldown=2.0, actor="joao", per_user_cooldown=0.0)


def test_cooldown_de_regra_libera_depois():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    rl.allow_rule("gift:Rose", 2.0, "joao", 0.0)
    relogio.avanca(2.1)
    assert rl.allow_rule("gift:Rose", 2.0, "joao", 0.0)


def test_cooldown_por_usuario_nao_afeta_outro_usuario():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    assert rl.allow_rule("gift:Rose", 0.0, "joao", per_user_cooldown=5.0)
    # Maria nao pode ser punida pelo spam do Joao.
    assert rl.allow_rule("gift:Rose", 0.0, "maria", per_user_cooldown=5.0)


def test_cooldown_por_usuario_bloqueia_o_mesmo_usuario():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    rl.allow_rule("gift:Rose", 0.0, "joao", 5.0)
    assert not rl.allow_rule("gift:Rose", 0.0, "joao", 5.0)


def test_ator_vazio_nao_compartilha_balde_com_outro_vazio():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    assert rl.allow_rule("comment:direita", 0.0, "", 1.0)
    assert rl.allow_rule("comment:direita", 0.0, "", 1.0)


def test_orcamento_global_limita_rajada():
    relogio = Relogio()
    rl = RateLimiter(action_budget={"spawn_enemy": 3.0}, now_fn=relogio)
    permitidos = sum(1 for _ in range(50) if rl.allow_action("spawn_enemy"))
    assert permitidos == 3


def test_orcamento_global_recarrega_com_o_tempo():
    relogio = Relogio()
    rl = RateLimiter(action_budget={"spawn_enemy": 3.0}, now_fn=relogio)
    for _ in range(3):
        rl.allow_action("spawn_enemy")
    assert not rl.allow_action("spawn_enemy")
    relogio.avanca(1.1)
    assert rl.allow_action("spawn_enemy")


def test_acao_sem_orcamento_configurado_e_sempre_permitida():
    rl = RateLimiter(action_budget={"spawn_enemy": 1.0}, now_fn=Relogio())
    assert all(rl.allow_action("xp") for _ in range(100))


def test_rajada_de_50_da_mesma_regra_nao_trava():
    relogio = Relogio()
    rl = RateLimiter(now_fn=relogio)
    permitidos = sum(
        1 for n in range(50) if rl.allow_rule("gift:Cap", 2.0, f"u{n}", 0.0)
    )
    assert permitidos == 1
