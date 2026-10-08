from core.events import EventType, LiveEvent


def test_actor_prefere_display_name():
    e = LiveEvent(type=EventType.GIFT, username="joao123", display_name="João")
    assert e.actor() == "João"


def test_actor_cai_para_username():
    e = LiveEvent(type=EventType.GIFT, username="joao123")
    assert e.actor() == "joao123"


def test_actor_sem_nada_nao_retorna_none_como_texto():
    e = LiveEvent(type=EventType.LIKE)
    assert e.actor() == "desconhecido"
    assert "None" not in e.actor()


def test_like_sem_usuario_nao_quebra():
    # O TikTok limita likes por usuario; depois disso event.user pode vir None.
    e = LiveEvent(type=EventType.LIKE, like_delta=3, like_total=120)
    assert e.actor() == "desconhecido"
    assert e.like_total == 120


def test_tipo_e_comparavel_com_string():
    assert LiveEvent(type=EventType.GIFT).type == "gift"
