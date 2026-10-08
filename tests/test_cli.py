from __future__ import annotations

from contratalupa import cli
from contratalupa.samples import SAMPLE_CONTRACT


def test_demo_runs(capsys):
    cli.demo()
    out = capsys.readouterr().out
    assert "overall risk: HIGH" in out
    assert "liability" in out
    assert "missing" in out.lower()


def test_analyze_file(tmp_path, capsys):
    path = tmp_path / "contract.txt"
    path.write_text(SAMPLE_CONTRACT, encoding="utf-8")
    cli.analyze_file(str(path))
    out = capsys.readouterr().out
    assert "overall risk" in out
    assert "liability" in out


def test_main_dispatches_demo(monkeypatch):
    called = {"demo": False}
    monkeypatch.setattr(cli, "demo", lambda: called.__setitem__("demo", True))
    monkeypatch.setattr("sys.argv", ["contratalupa", "demo"])
    cli.main()
    assert called["demo"] is True
