import json

from core.events import EventType, LiveEvent
from core.logging_setup import EventJournal, setup_logging


def test_setup_cria_o_arquivo_de_log(tmp_path):
    logger = setup_logging(log_dir=tmp_path)
    logger.info("teste")
    for h in logger.handlers:
        h.flush()
    assert (tmp_path / "app.log").exists()


def test_log_usa_formato_com_hora_entre_colchetes(tmp_path):
    logger = setup_logging(log_dir=tmp_path)
    logger.info("GIFT user=joao gift=Rose quantity=1")
    for h in logger.handlers:
        h.flush()
    conteudo = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "GIFT user=joao gift=Rose quantity=1" in conteudo
    assert conteudo.strip().startswith("[")


def test_setup_e_idempotente(tmp_path):
    a = setup_logging(log_dir=tmp_path)
    b = setup_logging(log_dir=tmp_path)
    assert a is b
    assert len(a.handlers) <= 2  # nao acumula handler a cada chamada


def test_journal_grava_jsonl(tmp_path):
    caminho = tmp_path / "events.jsonl"
    j = EventJournal(caminho)
    j.record(LiveEvent(type=EventType.FOLLOW, username="carlos", display_name="Carlos"))
    j.close()
    linha = caminho.read_text(encoding="utf-8").strip()
    dado = json.loads(linha)
    assert dado["type"] == "follow"
    assert dado["username"] == "carlos"
    assert "timestamp" in dado


def test_journal_grava_share_com_horario(tmp_path):
    caminho = tmp_path / "events.jsonl"
    j = EventJournal(caminho)
    j.record(LiveEvent(type=EventType.SHARE, username="lucas"))
    j.record(LiveEvent(type=EventType.GIFT, username="joao", gift_name="Rose", quantity=2))
    j.close()
    linhas = [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines()]
    assert [l["type"] for l in linhas] == ["share", "gift"]
    assert linhas[1]["gift_name"] == "Rose"


def test_journal_ignora_evento_de_sistema(tmp_path):
    caminho = tmp_path / "events.jsonl"
    j = EventJournal(caminho)
    j.record(LiveEvent(type=EventType.SYSTEM, text="connected"))
    j.close()
    assert caminho.read_text(encoding="utf-8").strip() == ""


def test_journal_nao_quebra_se_o_diretorio_sumir(tmp_path):
    caminho = tmp_path / "sub" / "events.jsonl"
    j = EventJournal(caminho)
    j.record(LiveEvent(type=EventType.FOLLOW, username="a"))
    j.close()  # nao pode levantar
