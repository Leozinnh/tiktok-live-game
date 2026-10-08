import time

from adapters.simulated import SimulatedAdapter, parse_command, run_burst
from core.event_queue import EventQueue
from core.events import EventType

CONFIG = {"tiktok": {"username": "@teste"}, "app": {"queue_max_size": 100}}


def _q():
    return EventQueue(maxsize=1000)


def test_parse_gift_por_nome():
    e = parse_command("Rose")
    assert e.type == EventType.GIFT
    assert e.gift_name == "Rose"
    assert e.quantity == 1


def test_parse_gift_com_quantidade():
    e = parse_command("Rose 10")
    assert e.gift_name == "Rose"
    assert e.quantity == 10


def test_parse_comentario_com_aspas():
    e = parse_command('"corre"')
    assert e.type == EventType.COMMENT
    assert e.text == "corre"


def test_parse_comentario_com_prefixo():
    e = parse_command("corre")
    assert e.type == EventType.COMMENT
    assert e.text == "corre"


def test_parse_follow():
    assert parse_command("follow").type == EventType.FOLLOW


def test_parse_share():
    assert parse_command("share").type == EventType.SHARE


def test_parse_like_com_contador():
    e = parse_command("like 100")
    assert e.type == EventType.LIKE
    assert e.like_delta == 100
    assert e.like_total == 100


def test_parse_like_acumula_entre_comandos():
    q = _q()
    a = SimulatedAdapter(q, CONFIG)
    a.handle_line("like 100")
    a.handle_line("like 50")
    eventos = [q.get_nowait() for _ in range(2)]
    assert eventos[0].like_total == 100
    assert eventos[1].like_total == 150
    assert eventos[1].like_delta == 50


def test_parse_user_troca_o_autor():
    e = parse_command("user joao Rose")
    assert e.username == "joao"
    assert e.gift_name == "Rose"


def test_parse_help_retorna_none():
    assert parse_command("help") is None


def test_parse_vazio_retorna_none():
    assert parse_command("") is None
    assert parse_command("   ") is None


def test_parse_desconhecido_vira_comentario():
    e = parse_command("bom dia galera")
    assert e.type == EventType.COMMENT
    assert e.text == "bom dia galera"


def test_adapter_escreve_na_fila():
    q = _q()
    a = SimulatedAdapter(q, CONFIG)
    a.handle_line("follow")
    assert q.get_nowait().type == EventType.FOLLOW


def test_burst_nao_bloqueia_e_respeita_o_limite_da_fila():
    q = EventQueue(maxsize=50)
    run_burst(q, CONFIG, count=500)
    assert q.size() <= 50
    assert q.dropped > 0


def test_adapter_start_e_stop_sem_travar():
    q = _q()
    a = SimulatedAdapter(q, CONFIG, interactive=False)
    a.start()
    time.sleep(0.05)
    a.stop()
    assert not a.status.connected


def test_status_reflete_o_estado():
    a = SimulatedAdapter(_q(), CONFIG, interactive=False)
    assert not a.status.connected
