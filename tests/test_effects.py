from game.effects import AnnouncementQueue, EffectSet


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def avanca(self, dt: float) -> None:
        self.t += dt


def test_efeito_esta_ativo_enquanto_dentro_da_duracao():
    r = Relogio()
    e = EffectSet(now_fn=r)
    e.activate("shield", 5.0)
    assert e.active("shield")
    r.avanca(5.1)
    assert not e.active("shield")


def test_efeito_nao_ativado_esta_inativo():
    assert not EffectSet(now_fn=Relogio()).active("shield")


def test_duracao_empilha_pelo_maior_fim_nao_soma():
    r = Relogio()
    e = EffectSet(now_fn=r)
    e.activate("shield", 5.0)
    r.avanca(1.0)
    e.activate("shield", 5.0)  # termina em 6.0, nao em 7.0
    r.avanca(5.5)
    assert not e.active("shield")
    r.avanca(0.6)
    assert not e.active("shield")


def test_reativar_estende_se_o_novo_fim_for_maior():
    r = Relogio()
    e = EffectSet(now_fn=r)
    e.activate("shield", 1.0)
    e.activate("shield", 10.0)
    r.avanca(5.0)
    assert e.active("shield")


def test_remaining_diminui_com_o_tempo():
    r = Relogio()
    e = EffectSet(now_fn=r)
    e.activate("rage", 10.0)
    r.avanca(4.0)
    assert 5.9 < e.remaining("rage") < 6.1


def test_expire_remove_efeitos_vencidos():
    r = Relogio()
    e = EffectSet(now_fn=r)
    e.activate("jump", 1.0)
    r.avanca(2.0)
    e.expire()
    assert e.remaining("jump") == 0.0


def test_anuncio_fica_ativo_ate_o_ttl():
    r = Relogio()
    q = AnnouncementQueue(now_fn=r)
    q.push(kind="gift", actor="Joao", text="mandou Rose", detail="+5 XP", ttl=4.0)
    assert len(q.active()) == 1
    r.avanca(4.1)
    assert q.active() == []


def test_anuncio_expira_sozinho_sem_chamada_explicita():
    r = Relogio()
    q = AnnouncementQueue(now_fn=r)
    q.push(kind="gift", actor="Joao", text="mandou Rose", ttl=1.0)
    r.avanca(5.0)
    q.push(kind="gift", actor="Maria", text="mandou GG", ttl=1.0)
    assert [a.actor for a in q.active()] == ["Maria"]


def test_fila_de_anuncios_respeita_o_tamanho_maximo():
    q = AnnouncementQueue(now_fn=Relogio(), max_size=3)
    for i in range(10):
        q.push(kind="gift", actor=f"u{i}", text="x", ttl=100.0)
    assert len(q.active()) == 3


def test_fila_de_anuncios_mantem_os_mais_recentes():
    q = AnnouncementQueue(now_fn=Relogio(), max_size=2)
    for nome in ("a", "b", "c", "d"):
        q.push(kind="gift", actor=nome, text="x", ttl=100.0)
    assert [a.actor for a in q.active()] == ["c", "d"]


def test_anuncio_big_e_marcado():
    q = AnnouncementQueue(now_fn=Relogio())
    q.push(kind="levelup", actor="", text="LEVEL UP!", big=True, ttl=3.0)
    assert q.active()[0].big is True
