from core.event_queue import EventQueue
from core.events import EventType, LiveEvent


def _ev(n: int) -> LiveEvent:
    return LiveEvent(type=EventType.COMMENT, username=f"u{n}", text=str(n))


def test_put_e_get():
    q = EventQueue(maxsize=10)
    q.put(_ev(1))
    assert q.get_nowait().text == "1"


def test_get_vazio_retorna_none():
    assert EventQueue(maxsize=10).get_nowait() is None


def test_fila_cheia_descarta_o_mais_antigo():
    q = EventQueue(maxsize=3)
    for i in range(5):
        q.put(_ev(i))
    restantes = [q.get_nowait().text for _ in range(3)]
    assert restantes == ["2", "3", "4"]


def test_contador_de_descarte_e_exato():
    q = EventQueue(maxsize=3)
    for i in range(5):
        q.put(_ev(i))
    assert q.dropped == 2
    # `accepted` conta o que ENTROU na fila, inclusive o que depois foi
    # descartado para dar lugar a um evento mais novo.
    assert q.accepted == 5


def test_nunca_levanta_excecao_com_fila_cheia():
    q = EventQueue(maxsize=1)
    for i in range(100):
        q.put(_ev(i))  # nao pode levantar


def test_drain_respeita_o_limite():
    q = EventQueue(maxsize=100)
    for i in range(50):
        q.put(_ev(i))
    lote = q.drain(limit=20)
    assert len(lote) == 20
    assert q.size() == 30


def test_drain_pega_o_mais_antigo_primeiro():
    q = EventQueue(maxsize=100)
    for i in range(5):
        q.put(_ev(i))
    assert [e.text for e in q.drain(3)] == ["0", "1", "2"]
