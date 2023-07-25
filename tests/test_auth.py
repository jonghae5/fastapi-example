from app.database.conn import db
from app.database.schema import Users


def test_registration(client, session):
    """
    레버 로그인
    :param client:
    :param session:
    :return:
    """
    user = dict(email="dhwhdgo5645@naver.com", pw="123", name="오종해", phone="01052780000")
    res = client.post("api/auth/register/email", json=user)
    res_body = res.json()
    print(res.json())
    assert res.status_code == 201
    assert "Authorization" in res_body


def test_registration_exist_email(client, session):
    """
    레버 로그인
    :param client:
    :param session:
    :return:
    """
    user = dict(email="dhwhdgo2368@gmail.com", pw="123", name="오종", phone="01099999999")
    db_user = Users.create(session=session, **user)
    session.commit()
    res = client.post("api/auth/register/email", json=user)
    res_body = res.json()
    assert res.status_code == 400
    assert 'EMAIL_EXISTS' == res_body["msg"]



# monkeypatch
# kakaotalk 같은 Token 발급