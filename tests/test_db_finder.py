"""Tests for Apple Mail database finder."""

from apple_mail.db_finder import find_mail_db


def test_env_override(tmp_path, monkeypatch):
    db = tmp_path / "Envelope Index"
    db.touch()
    monkeypatch.setenv("MAIL_DB", str(db))
    assert find_mail_db() == str(db)


def test_env_override_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("MAIL_DB", str(tmp_path / "nope"))
    try:
        find_mail_db()
        assert False, "Should have raised"
    except FileNotFoundError:
        pass


def test_auto_detect(tmp_path, monkeypatch):
    v9 = tmp_path / "V9" / "MailData"
    v9.mkdir(parents=True)
    (v9 / "Envelope Index").touch()

    v10 = tmp_path / "V10" / "MailData"
    v10.mkdir(parents=True)
    (v10 / "Envelope Index").touch()

    monkeypatch.delenv("MAIL_DB", raising=False)
    result = find_mail_db(mail_dir=str(tmp_path))
    assert "V10" in result


def test_auto_detect_no_versions(tmp_path, monkeypatch):
    monkeypatch.delenv("MAIL_DB", raising=False)
    try:
        find_mail_db(mail_dir=str(tmp_path))
        assert False, "Should have raised"
    except FileNotFoundError:
        pass
