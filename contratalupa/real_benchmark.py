"""Benchmark the project's trainable clause classifier on real LEDGAR clauses.

Trains contratalupa's :class:`~contratalupa.ml.ClauseClassifier` on a balanced
subset of the real LEDGAR contract-clause dataset and measures how well it
generalises to clauses it was never fit on, using three complementary views:

1. stratified k-fold cross-validation on the training portion (mean macro-F1 and
   accuracy, plus the per-fold spread);
2. a held-out test split the model never sees while fitting;
3. the training-set score itself, so the train -> held-out gap is explicit.

Every score is compared against a most-frequent-class baseline. The fit is then
classified as well-fit / overfit / underfit from the train-test gap and the
agreement between cross-validation and the held-out test. Finally a shuffled-
label control re-runs cross-validation on permuted labels: when the mapping from
clause text to clause type is destroyed the score must collapse to the baseline,
which shows the model learns real clause structure rather than memorising noise.

Run it with ``python -m contratalupa.real_benchmark``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, train_test_split

from .ml import DEFAULT_C, ClauseClassifier
from .real_data import load_ledgar

# --- verdict thresholds (made explicit so the classification is auditable) ----
#: Cross-validated macro-F1 must clear this absolute floor to count as competent.
STRONG_MACRO_F1 = 0.50
#: ...and must beat the baseline macro-F1 by at least this margin.
BASELINE_MARGIN = 0.30
#: Per-fold macro-F1 spread allowed before the result is called unstable.
MAX_CV_STD = 0.05
#: Allowed disagreement between cross-validation and the held-out test.
MAX_CV_TEST_GAP = 0.08
#: Allowed train -> cross-validation macro-F1 gap before it reads as overfitting.
MAX_TRAIN_CV_GAP = 0.25


@dataclass
class CrossValResult:
    macro_f1_mean: float
    macro_f1_std: float
    accuracy_mean: float
    per_fold_macro_f1: list[float]


@dataclass
class BenchmarkResult:
    n_samples: int
    n_classes: int
    class_names: list[str]
    C: float
    cv: CrossValResult
    train_accuracy: float
    train_macro_f1: float
    test_accuracy: float
    test_macro_f1: float
    baseline_accuracy: float
    baseline_macro_f1: float
    shuffled_cv_macro_f1: float
    verdict: str

    @property
    def train_test_accuracy_gap(self) -> float:
        return self.train_accuracy - self.test_accuracy

    @property
    def train_cv_f1_gap(self) -> float:
        return self.train_macro_f1 - self.cv.macro_f1_mean

    @property
    def cv_test_f1_agreement(self) -> float:
        return abs(self.cv.macro_f1_mean - self.test_macro_f1)


def _cross_validate(
    texts: Sequence[str],
    labels: Sequence[str],
    *,
    C: float,
    folds: int = 5,
    random_state: int = 42,
) -> CrossValResult:
    """Stratified k-fold CV of the project's classifier; refit per fold, no leakage."""
    X = np.asarray(texts, dtype=object)
    y = np.asarray(labels)
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=random_state)
    fold_f1: list[float] = []
    fold_acc: list[float] = []
    for train_idx, val_idx in splitter.split(X, y):
        model = ClauseClassifier(C=C).fit(list(X[train_idx]), list(y[train_idx]))
        pred = model.predict(list(X[val_idx]))
        fold_f1.append(f1_score(y[val_idx], pred, average="macro", zero_division=0))
        fold_acc.append(accuracy_score(y[val_idx], pred))
    return CrossValResult(
        macro_f1_mean=float(np.mean(fold_f1)),
        macro_f1_std=float(np.std(fold_f1)),
        accuracy_mean=float(np.mean(fold_acc)),
        per_fold_macro_f1=[float(x) for x in fold_f1],
    )


def _baseline_scores(
    y_train: Sequence[str], y_test: Sequence[str]
) -> tuple[float, float]:
    """Most-frequent-class predictor scored on the held-out test (accuracy, macro-F1)."""
    majority = Counter(y_train).most_common(1)[0][0]
    pred = [majority] * len(y_test)
    acc = accuracy_score(y_test, pred)
    macro_f1 = f1_score(y_test, pred, average="macro", zero_division=0)
    return float(acc), float(macro_f1)


def _shuffled_cv_macro_f1(
    texts: Sequence[str],
    labels: Sequence[str],
    *,
    C: float,
    folds: int = 5,
    random_state: int = 42,
) -> float:
    """CV macro-F1 after permuting the labels: the signal must vanish to the floor."""
    rng = np.random.default_rng(random_state)
    shuffled = list(labels)
    rng.shuffle(shuffled)
    cv = _cross_validate(texts, shuffled, C=C, folds=folds, random_state=random_state)
    return cv.macro_f1_mean


def classify_fit(
    cv: CrossValResult,
    train_macro_f1: float,
    test_macro_f1: float,
    baseline_macro_f1: float,
) -> str:
    """Classify the fit as well-fit / overfit / underfit from the generalisation gap."""
    competent = (
        cv.macro_f1_mean >= STRONG_MACRO_F1
        and cv.macro_f1_mean >= baseline_macro_f1 + BASELINE_MARGIN
    )
    cv_test_gap = abs(cv.macro_f1_mean - test_macro_f1)
    stable = cv.macro_f1_std <= MAX_CV_STD and cv_test_gap <= MAX_CV_TEST_GAP
    small_gap = (train_macro_f1 - cv.macro_f1_mean) <= MAX_TRAIN_CV_GAP
    if not competent:
        return "underfit"
    if not (stable and small_gap):
        return "overfit"
    return "well-fit"


def evaluate(
    texts: Sequence[str],
    labels: Sequence[str],
    *,
    C: float = DEFAULT_C,
    folds: int = 5,
    test_size: float = 0.2,
    random_state: int = 42,
) -> BenchmarkResult:
    """Run the full evaluation and return a :class:`BenchmarkResult`."""
    class_names = sorted(set(labels))
    x_train, x_test, y_train, y_test = train_test_split(
        list(texts),
        list(labels),
        test_size=test_size,
        stratify=list(labels),
        random_state=random_state,
    )

    cv = _cross_validate(x_train, y_train, C=C, folds=folds, random_state=random_state)

    model = ClauseClassifier(C=C).fit(x_train, y_train)
    train_pred = model.predict(x_train)
    test_pred = model.predict(x_test)
    train_acc = accuracy_score(y_train, train_pred)
    train_f1 = f1_score(y_train, train_pred, average="macro", zero_division=0)
    test_acc = accuracy_score(y_test, test_pred)
    test_f1 = f1_score(y_test, test_pred, average="macro", zero_division=0)

    baseline_acc, baseline_f1 = _baseline_scores(y_train, y_test)
    shuffled_f1 = _shuffled_cv_macro_f1(
        x_train, y_train, C=C, folds=folds, random_state=random_state
    )

    verdict = classify_fit(cv, train_f1, test_f1, baseline_f1)

    return BenchmarkResult(
        n_samples=len(texts),
        n_classes=len(class_names),
        class_names=class_names,
        C=C,
        cv=cv,
        train_accuracy=float(train_acc),
        train_macro_f1=float(train_f1),
        test_accuracy=float(test_acc),
        test_macro_f1=float(test_f1),
        baseline_accuracy=baseline_acc,
        baseline_macro_f1=baseline_f1,
        shuffled_cv_macro_f1=shuffled_f1,
        verdict=verdict,
    )


def format_report(result: BenchmarkResult) -> str:
    """Render a readable benchmark report."""
    lines = [
        "=" * 68,
        "Contratalupa - real-data benchmark (LEDGAR contract clauses)",
        "=" * 68,
        f"dataset        : {result.n_samples} clauses, {result.n_classes} clause types (balanced)",
        f"model          : TF-IDF (1-2 grams) + logistic regression, C={result.C}",
        f"random baseline: {1.0 / result.n_classes:.3f} accuracy ({result.n_classes} classes)",
        "",
        "Cross-validation (stratified 5-fold, on the training split)",
        f"  macro-F1     : {result.cv.macro_f1_mean:.3f} +/- {result.cv.macro_f1_std:.3f}",
        f"  accuracy     : {result.cv.accuracy_mean:.3f}",
        f"  per fold F1  : {', '.join(f'{x:.3f}' for x in result.cv.per_fold_macro_f1)}",
        "",
        "Held-out test split (never seen while fitting)",
        f"  accuracy     : {result.test_accuracy:.3f}",
        f"  macro-F1     : {result.test_macro_f1:.3f}",
        "",
        "Training split (for the generalisation gap)",
        f"  accuracy     : {result.train_accuracy:.3f}",
        f"  macro-F1     : {result.train_macro_f1:.3f}",
        "",
        "Baselines (most-frequent class, on the held-out test)",
        f"  accuracy     : {result.baseline_accuracy:.3f}",
        f"  macro-F1     : {result.baseline_macro_f1:.3f}",
        "",
        "Generalisation",
        f"  train -> test accuracy gap : {result.train_test_accuracy_gap:+.3f}",
        f"  train -> CV macro-F1 gap   : {result.train_cv_f1_gap:+.3f}",
        f"  CV vs test macro-F1 agree  : {result.cv_test_f1_agreement:.3f} apart",
        "",
        "Shuffled-label control (labels permuted; signal must vanish)",
        f"  CV macro-F1  : {result.shuffled_cv_macro_f1:.3f}  "
        f"(vs real {result.cv.macro_f1_mean:.3f}, baseline {result.baseline_macro_f1:.3f})",
        "",
        f"VERDICT        : {result.verdict.upper()}",
        "=" * 68,
    ]
    return "\n".join(lines)


def main() -> BenchmarkResult:
    """Load the vendored LEDGAR subset, run the benchmark, and print the report."""
    texts, labels, _ = load_ledgar()
    result = evaluate(texts, labels)
    print(format_report(result))
    return result


if __name__ == "__main__":
    main()
