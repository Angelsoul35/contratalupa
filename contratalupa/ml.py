"""An offline, data-driven clause-type classifier (TF-IDF + linear model).

Contratalupa classifies clauses with an LLM when one is reachable and with
keyword heuristics when none is. This module adds a third, trainable path: a
TF-IDF vectoriser feeding a multinomial logistic-regression classifier, learned
from labelled clauses. It runs offline with no API key, reports calibrated class
probabilities for ranking, and is the component evaluated on the real LEDGAR
dataset in :mod:`contratalupa.real_benchmark`.

The vectoriser turns each clause into a sparse bag of unigrams and bigrams
weighted by TF-IDF; the linear model learns one weight vector per clause type.
Both live in one scikit-learn :class:`~sklearn.pipeline.Pipeline` so that fitting
and prediction share exactly the same text transformation, which keeps the
evaluation leakage-free: the vectoriser is only ever fit on training folds.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

#: Regularisation strength selected by cross-validation (see real_benchmark).
#: Larger C means weaker L2 regularisation. Cross-validated macro-F1 is flat
#: across C on the vendored LEDGAR subset (within one fold standard deviation),
#: so this is the parsimonious choice: near-peak cross-validation with the
#: smallest train -> CV gap, rather than a higher C that only memorises training.
DEFAULT_C = 2.0


class ClauseClassifier:
    """A trainable clause-type classifier: TF-IDF features + logistic regression.

    The API mirrors the scikit-learn estimator convention the rest of the ML
    ecosystem expects -- ``fit``, ``predict``, ``predict_proba`` -- but accepts
    and returns plain Python lists so it composes with the project's list-based
    clause handling.
    """

    def __init__(
        self,
        *,
        C: float = DEFAULT_C,
        ngram_range: tuple[int, int] = (1, 2),
        min_df: int = 2,
        max_features: int = 20000,
        max_iter: int = 1000,
        random_state: int = 42,
    ) -> None:
        self.C = C
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_features = max_features
        self.max_iter = max_iter
        self.random_state = random_state
        self.pipeline = self.build_pipeline(
            C=C,
            ngram_range=ngram_range,
            min_df=min_df,
            max_features=max_features,
            max_iter=max_iter,
            random_state=random_state,
        )

    @staticmethod
    def build_pipeline(
        *,
        C: float = DEFAULT_C,
        ngram_range: tuple[int, int] = (1, 2),
        min_df: int = 2,
        max_features: int = 20000,
        max_iter: int = 1000,
        random_state: int = 42,
    ) -> Pipeline:
        """Build the underlying scikit-learn pipeline (a fresh, unfitted estimator)."""
        return Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        sublinear_tf=True,
                        ngram_range=ngram_range,
                        min_df=min_df,
                        max_features=max_features,
                        strip_accents="unicode",
                        lowercase=True,
                        stop_words="english",
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        C=C,
                        max_iter=max_iter,
                        random_state=random_state,
                    ),
                ),
            ]
        )

    def fit(self, texts: Iterable[str], labels: Iterable[str]) -> ClauseClassifier:
        """Fit the vectoriser and classifier on labelled clauses; return self."""
        self.pipeline.fit(list(texts), list(labels))
        return self

    def predict(self, texts: Sequence[str]) -> list[str]:
        """Predict a clause type for each text."""
        return list(self.pipeline.predict(list(texts)))

    def predict_proba(self, texts: Sequence[str]) -> np.ndarray:
        """Return per-class probabilities, column-aligned with :attr:`classes_`."""
        return self.pipeline.predict_proba(list(texts))

    @property
    def classes_(self) -> list[str]:
        """The clause types the model was trained on, in probability-column order."""
        return list(self.pipeline.named_steps["clf"].classes_)
