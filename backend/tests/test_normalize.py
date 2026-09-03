import pytest

from app.normalize import normalize_identifier


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("https://t.me/Acid_Burn/", "acid_burn"),
        ("@Acid_Burn", "acid_burn"),
        ("tg://resolve?domain=Acid_Burn", "acid_burn"),
        ("mailto:Broker@XMPP.is", "broker@xmpp.is"),
        ("xmpp:dealer@jabber.ru?message", "dealer@jabber.ru"),
        ("  EXPLOIT.IN/profile/1337 ", "exploit.in/profile/1337"),
        ("https://xss.is/members/88213/", "xss.is/members/88213"),
        ("Broker@jabber.ru", "broker@jabber.ru"),
        ("PlainHandle", "plainhandle"),
        ("", ""),
    ],
)
def test_normalize_identifier(raw, expected):
    assert normalize_identifier(raw) == expected
