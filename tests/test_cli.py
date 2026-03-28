import sys
sys.path.insert(0, "/Users/jangis/Code/pii-tool")
import pytest
from unittest.mock import patch
import json
from kvkk_pii.cli import main


def run_cli(*args):
    with patch("sys.argv", ["kvkk-pii", *args]):
        try:
            main()
            return 0
        except SystemExit as e:
            return e.code


def test_version(capsys):
    run_cli("version")
    out = capsys.readouterr().out
    assert "0.1." in out


def test_scan_text(capsys):
    run_cli("scan", "TC: 10000000146")
    out = capsys.readouterr().out
    assert "TC_KIMLIK" in out


def test_scan_json(capsys):
    run_cli("scan", "--format", "json", "TC: 10000000146")
    out = capsys.readouterr().out
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["type"] == "TC_KIMLIK"


def test_scan_no_pii(capsys):
    run_cli("scan", "Merhaba dünya")
    out = capsys.readouterr().out
    assert "bulunamad" in out


def test_anonymize(capsys):
    run_cli("anonymize", "TC: 10000000146")
    out = capsys.readouterr().out
    assert "10000000146" not in out
    assert "[TC_KIMLIK]" in out


def test_scan_stdin(capsys, monkeypatch):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("ali@test.com"))
    run_cli("scan")
    out = capsys.readouterr().out
    assert "EMAIL" in out
