"""Functional tests for the real-data (LEDGAR) benchmark.

Every test asserts a behaviour that would break if the thing it checks broke:
the loader returns the real vendored data with exact counts and classes; the
project's classifier beats the majority baseline on every held-out fold; the
fit is classified as well-fit; permuting the labels collapses the score to the
baseline; and the fetch path maps labels and paginates correctly behind a
monkeypatched ``urlopen`` with no network access.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
from collections import Counter

import numpy as np
import pytest

from contratalupa import real_benchmark, real_data
from contratalupa.ml import ClauseClassifier
from contratalupa.real_benchmark import CrossValResult, classify_fit, evaluate, format_report, main
from contratalupa.real_data import (
    DEFAULT_N_CLASSES,
    DEFAULT_PER_CLASS,
    fetch_ledgar,
    load_ledgar,
    refresh,
    save_ledgar,
)

# A sample of clause types that must be present in the vendored LEDGAR subset.
_EXPECTED_CLASSES = {"Governing Laws", "Notices", "Terminations"}


# --- loader -----------------------------------------------------------------
def test_load_ledgar_returns_the_real_balanced_subset():
    texts, labels, names = load_ledgar()
    assert len(texts) == len(labels) == DEFAULT_N_CLASSES * DEFAULT_PER_CLASS
    assert len(names) == DEFAULT_N_CLASSES
    assert _EXPECTED_CLASSES.issubset(set(names))
    # The subset is balanced: every clause type contributes the same count.
    counts = Counter(labels)
    assert set(counts.values()) == {DEFAULT_PER_CLASS}
    # Clauses are non-trivial, whitespace-normalised strings.
    assert all(isinstance(t, str) and len(t) > 10 for t in texts)
    assert all("\n" not in t and "  " not in t for t in texts)


# --- one shared benchmark run reused across the generalisation assertions ----
@pytest.fixture(scope="module")
def result():
    texts, labels, _ = load_ledgar()
    return evaluate(texts, labels)


def test_classifier_beats_majority_baseline_on_every_held_out_fold(result):
    # Cross-validation and the held-out test both clear the baseline by a wide margin.
    assert result.cv.macro_f1_mean > result.baseline_macro_f1 + 0.40
    assert result.test_macro_f1 > result.baseline_macro_f1 + 0.40
    assert result.test_accuracy > result.baseline_accuracy + 0.40
    # No single fold collapses to the baseline.
    assert min(result.cv.per_fold_macro_f1) > result.baseline_macro_f1 + 0.30


def test_fit_is_classified_well_fit(result):
    assert result.verdict == "well-fit"
    # Grounding: cross-validation and the held-out test agree, and the train->CV
    # macro-F1 gap stays within the band that reads as healthy generalisation.
    assert result.cv_test_f1_agreement <= 0.08
    assert result.train_cv_f1_gap <= 0.25


def test_shuffling_labels_collapses_score_to_baseline(result):
    # Destroying the text -> type mapping must erase the signal: the score drops
    # to the random floor (~1/n_classes), far below the real cross-validation score.
    assert result.shuffled_cv_macro_f1 < result.cv.macro_f1_mean * 0.25
    assert result.shuffled_cv_macro_f1 < 2.0 / result.n_classes


def test_classify_fit_covers_each_verdict():
    strong = CrossValResult(0.82, 0.02, 0.84, [0.80, 0.81, 0.82, 0.83, 0.84])
    assert classify_fit(strong, 0.97, 0.81, 0.01) == "well-fit"
    # High training score, weak and unstable CV that disagrees with the test -> overfit.
    weak_cv = CrossValResult(0.55, 0.09, 0.55, [0.40, 0.50, 0.55, 0.65, 0.65])
    assert classify_fit(weak_cv, 0.99, 0.70, 0.01) == "overfit"
    # Barely above the baseline -> underfit.
    floor = CrossValResult(0.05, 0.01, 0.10, [0.04, 0.05, 0.05, 0.05, 0.06])
    assert classify_fit(floor, 0.06, 0.05, 0.01) == "underfit"


# --- the trainable classifier ------------------------------------------------
def test_clause_classifier_predict_and_proba(result):
    texts, labels, names = load_ledgar()
    model = ClauseClassifier().fit(texts, labels)
    sample = texts[:5]
    preds = model.predict(sample)
    assert len(preds) == 5
    assert all(p in names for p in preds)
    proba = model.predict_proba(sample)
    assert proba.shape == (5, len(names))
    # Probabilities are a distribution and the argmax matches predict().
    np.testing.assert_allclose(proba.sum(axis=1), np.ones(5), atol=1e-6)
    assert model.classes_ == names
    argmax_labels = [model.classes_[i] for i in proba.argmax(axis=1)]
    assert argmax_labels == preds


# --- fetch path (monkeypatched urlopen, no network) --------------------------
def _page_payload(rows_pool, label_names, offset, length):
    page = rows_pool[offset : offset + length]
    return json.dumps(
        {
            "features": [
                {"name": "text", "type": {"dtype": "string", "_type": "Value"}},
                {"name": "label", "type": {"names": label_names, "_type": "ClassLabel"}},
            ],
            "rows": [{"row": {"text": t, "label": lab}} for (t, lab) in page],
        }
    ).encode("utf-8")


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._payload


def _make_fake_urlopen(rows_pool, label_names):
    def fake_urlopen(url, timeout=None):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        offset = int(query["offset"][0])
        length = int(query["length"][0])
        return _FakeResponse(_page_payload(rows_pool, label_names, offset, length))

    return fake_urlopen


def test_fetch_ledgar_maps_labels_and_balances(monkeypatch):
    label_names = ["Alpha", "Beta", "Gamma"]
    # Beta and Gamma are the two most frequent; Alpha is rare and must be dropped.
    rows_pool = (
        [("  beta   clause\ntext  ", 1)] * 6
        + [("gamma clause text", 2)] * 6
        + [("alpha clause text", 0)] * 2
    )
    monkeypatch.setattr(real_data, "urlopen", _make_fake_urlopen(rows_pool, label_names))

    texts, labels, names = fetch_ledgar(n_classes=2, per_class=3, max_scan_rows=1000)

    assert names == ["Beta", "Gamma"]
    assert Counter(labels) == {"Beta": 3, "Gamma": 3}
    assert "Alpha" not in labels
    # Whitespace is normalised on the way in.
    assert "  " not in texts[0] and "\n" not in texts[0]


def test_fetch_ledgar_retries_then_succeeds(monkeypatch):
    label_names = ["Alpha", "Beta"]
    rows_pool = [("alpha text", 0)] * 4 + [("beta text", 1)] * 4
    good = _make_fake_urlopen(rows_pool, label_names)
    calls = {"n": 0}

    def flaky(url, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("transient")
        return good(url, timeout=timeout)

    monkeypatch.setattr(real_data, "urlopen", flaky)
    monkeypatch.setattr(real_data.time, "sleep", lambda *_: None)

    texts, labels, names = fetch_ledgar(n_classes=2, per_class=3, max_scan_rows=1000)
    assert calls["n"] == 3  # two failures, then the retry succeeds
    assert Counter(labels) == {"Alpha": 3, "Beta": 3}


def test_fetch_ledgar_raises_after_exhausting_retries(monkeypatch):
    def always_fail(url, timeout=None):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(real_data, "urlopen", always_fail)
    monkeypatch.setattr(real_data.time, "sleep", lambda *_: None)

    with pytest.raises(RuntimeError, match="failed to fetch LEDGAR rows"):
        fetch_ledgar(n_classes=2, per_class=3, max_scan_rows=1000)


# --- save / load / refresh ---------------------------------------------------
def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "mini.jsonl.gz"
    texts = ["payment clause one", "notice clause two", "payment clause three"]
    labels = ["Payments", "Notices", "Payments"]
    save_ledgar(texts, labels, path)
    loaded_texts, loaded_labels, names = load_ledgar(path)
    assert loaded_texts == texts
    assert loaded_labels == labels
    assert names == ["Notices", "Payments"]


def test_load_ledgar_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="regenerate"):
        load_ledgar(tmp_path / "absent.jsonl.gz")


def test_refresh_writes_vendored_file(tmp_path, monkeypatch):
    path = tmp_path / "refreshed.jsonl.gz"
    monkeypatch.setattr(
        real_data,
        "fetch_ledgar",
        lambda n_classes, per_class: (["a clause", "b clause"], ["A", "B"], ["A", "B"]),
    )
    out = refresh(n_classes=2, per_class=1, path=path)
    assert out == path
    texts, labels, names = load_ledgar(path)
    assert labels == ["A", "B"]


# --- report rendering and the module entry point -----------------------------
def test_format_report_contains_the_numbers(result):
    report = format_report(result)
    assert "VERDICT" in report and result.verdict.upper() in report
    assert "macro-F1" in report
    assert "Shuffled-label control" in report
    assert f"{result.cv.macro_f1_mean:.3f}" in report


def test_main_prints_report(result, monkeypatch, capsys):
    # Reuse the already-computed result so main() does not refit the model.
    monkeypatch.setattr(real_benchmark, "evaluate", lambda *a, **k: result)
    returned = main()
    assert returned is result
    out = capsys.readouterr().out
    assert "real-data benchmark" in out
    assert "VERDICT" in out
