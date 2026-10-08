from __future__ import annotations

import pytest

from contratalupa.llm.base import LLMError
from contratalupa.llm.cascade import CascadeLLM
from contratalupa.llm.factory import build_llm
from contratalupa.llm.fake import FailingLLM, FakeLLM


def test_fake_llm_returns_scripted_reply():
    result = FakeLLM("hello").complete("sys", "prompt")
    assert result.text == "hello"
    assert result.provider == "fake"


def test_cascade_falls_back_to_next_provider():
    cascade = CascadeLLM([FailingLLM("a"), FailingLLM("b"), FakeLLM("recovered")])
    result = cascade.complete("sys", "prompt")
    assert result.text == "recovered"


def test_cascade_raises_when_all_fail():
    cascade = CascadeLLM([FailingLLM("a"), FailingLLM("b")])
    with pytest.raises(LLMError):
        cascade.complete("sys", "prompt")


def test_cascade_requires_at_least_one_client():
    with pytest.raises(ValueError):
        CascadeLLM([])


def test_factory_builds_named_cascade():
    llm = build_llm("anthropic,openai,ollama")
    assert llm.model.startswith("cascade[")
    # A single provider returns that provider directly, not a cascade.
    single = build_llm("ollama")
    assert single.name == "ollama"


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError):
        build_llm("not-a-provider")
