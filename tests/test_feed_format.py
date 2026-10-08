from game.effects import Announcement
from ui.feed import formatar_anuncio


def test_anuncio_de_presente_tem_icone_e_autor():
    a = Announcement(kind="gift", actor="João", text="mandou Rose", detail="+5 XP")
    icone, linha = formatar_anuncio(a)
    assert icone
    assert "João" in linha


def test_anuncio_nunca_mostra_none():
    a = Announcement(kind="gift", actor="", text="", detail="")
    _, linha = formatar_anuncio(a)
    assert "None" not in linha


def test_anuncio_de_follow_usa_o_icone_certo():
    icone, _ = formatar_anuncio(Announcement(kind="follow", actor="Carlos", text="seguiu"))
    assert icone != formatar_anuncio(Announcement(kind="gift", actor="X", text="y"))[0]


def test_linha_do_feed_e_truncada_para_caber():
    a = Announcement(kind="comment", actor="A" * 60, text="B" * 200)
    _, linha = formatar_anuncio(a, largura_max=40)
    assert len(linha) <= 40


def test_kind_desconhecido_nao_quebra():
    icone, linha = formatar_anuncio(Announcement(kind="zzz", actor="Ana", text="algo"))
    assert icone is not None
    assert linha
