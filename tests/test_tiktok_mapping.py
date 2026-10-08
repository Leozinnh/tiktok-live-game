from adapters.tiktok_live import evento_de_comentario, evento_de_like, evento_de_presente
from core.events import EventType


# Distingue "nao informado" de "explicitamente None", para que os dublês
# consigam representar os campos opcionais da biblioteca.
_VAZIO = object()


class UsuarioFalso:
    def __init__(self, unique_id="joao", nickname="João"):
        self.unique_id = unique_id
        self.nickname = nickname


class PresenteFalso:
    def __init__(self, name="Rose", gift_id="5655"):
        self.name = name
        self.id = gift_id


class ComentarioFalso:
    """Dublê do CommentEvent. Expõe `content`, que é o nome v3."""

    def __init__(self, content="corre", user=_VAZIO):
        self.content = content
        self.user = UsuarioFalso() if user is _VAZIO else user


class PresenteEventoFalso:
    """Dublê do GiftEvent.

    `streaking` é a propriedade real da biblioteca: `False` para presente
    não-streakable e `not repeat_end` caso contrário. O dublê reproduz essa
    relação em vez de aceitar os dois soltos, para que o teste não possa
    montar um estado que a biblioteca nunca produz.
    """

    def __init__(self, user=_VAZIO, gift=_VAZIO, repeat_count=1, streaking=False):
        self.user = UsuarioFalso() if user is _VAZIO else user
        self.gift = PresenteFalso() if gift is _VAZIO else gift
        self.repeat_count = repeat_count
        self.repeat_end = 0 if streaking else 1
        self.streaking = streaking


class LikeEventoFalso:
    def __init__(self, user=_VAZIO, count=1, total=1):
        self.user = UsuarioFalso() if user is _VAZIO else user
        self.count = count
        self.total = total


def test_comentario_usa_content_e_user():
    e = evento_de_comentario(ComentarioFalso(content="corre"))
    assert e.type == EventType.COMMENT
    assert e.text == "corre"
    assert e.username == "joao"
    assert e.display_name == "João"


def test_comentario_le_o_alias_legado_comment():
    class Antigo:
        comment = "pula"
        user = None

    assert evento_de_comentario(Antigo()).text == "pula"


def test_comentario_com_user_none_nao_quebra():
    e = evento_de_comentario(ComentarioFalso(user=None))
    assert e.username == ""
    assert e.actor() == "desconhecido"


def test_presente_streak_em_andamento_e_ignorado():
    assert evento_de_presente(PresenteEventoFalso(streaking=True, repeat_count=5)) is None


def test_presente_streak_final_traz_a_contagem_consolidada():
    e = evento_de_presente(PresenteEventoFalso(streaking=False, repeat_count=20))
    assert e is not None
    assert e.quantity == 20


def test_presente_traz_nome_e_id():
    e = evento_de_presente(PresenteEventoFalso(gift=PresenteFalso(name="Rose", gift_id="5655")))
    assert e.gift_name == "Rose"
    assert e.gift_id == "5655"


def test_presente_sem_gift_e_ignorado():
    assert evento_de_presente(PresenteEventoFalso(gift=None)) is None


def test_like_usa_count_como_delta_e_total_como_acumulado():
    e = evento_de_like(LikeEventoFalso(count=5, total=120), total_anterior=100)
    assert e.like_delta == 5
    assert e.like_total == 120


def test_like_sem_usuario_nao_quebra():
    e = evento_de_like(LikeEventoFalso(user=None, count=3, total=50), total_anterior=0)
    assert e.username == ""
    assert e.actor() == "desconhecido"
    assert e.like_total == 50


def test_like_com_total_menor_que_o_anterior_e_ignorado():
    e = evento_de_like(LikeEventoFalso(count=1, total=10), total_anterior=100)
    assert e.like_total == 100
    assert e.like_delta == 0
