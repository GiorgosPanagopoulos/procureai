from unittest.mock import MagicMock

import pytest
from llm.pricing import (
    COST_PER_CACHE_READ,
    COST_PER_CACHE_WRITE,
    COST_PER_INPUT_TOKEN,
    COST_PER_OUTPUT_TOKEN,
    _compute_cost,
    _UsageAccum,
)


def test_compute_cost_zero():
    assert _compute_cost(0, 0) == 0.0


def test_compute_cost_input_tokens():
    cost = _compute_cost(input_tokens=1_000_000, output_tokens=0)
    assert cost == pytest.approx(3.0)


def test_compute_cost_output_tokens():
    cost = _compute_cost(input_tokens=0, output_tokens=1_000_000)
    assert cost == pytest.approx(15.0)


def test_compute_cost_with_cache_tokens():
    cost = _compute_cost(
        input_tokens=0,
        output_tokens=0,
        cache_creation=1_000_000,
        cache_read=1_000_000,
    )
    assert cost == pytest.approx(3.75 + 0.30)


def test_usage_accum_initial_zeros():
    acc = _UsageAccum()
    assert acc.input_tokens == 0
    assert acc.output_tokens == 0
    assert acc.cache_creation == 0
    assert acc.cache_read == 0
    assert acc.tool_calls == 0


def test_usage_accum_to_dict_keys():
    acc = _UsageAccum()
    d = acc.to_dict()
    assert "input_tokens" in d
    assert "output_tokens" in d
    assert "cache_creation_tokens" in d
    assert "cache_read_tokens" in d
    assert "cost_usd" in d
    assert "tool_calls_count" in d


def test_usage_accum_add_anthropic():
    acc = _UsageAccum()
    usage = MagicMock()
    usage.input_tokens = 100
    usage.output_tokens = 50
    usage.cache_creation_input_tokens = 10
    usage.cache_read_input_tokens = 5
    acc.add_anthropic(usage)
    assert acc.input_tokens == 100
    assert acc.output_tokens == 50
    assert acc.cache_creation == 10
    assert acc.cache_read == 5


def test_usage_accum_cost_rounded_to_six():
    acc = _UsageAccum()
    acc.input_tokens = 1
    acc.output_tokens = 1
    d = acc.to_dict()
    assert isinstance(d["cost_usd"], float)
    assert d["cost_usd"] == round(d["cost_usd"], 6)


def test_pricing_constants_match_sonnet():
    assert COST_PER_INPUT_TOKEN == pytest.approx(3.00 / 1_000_000)
    assert COST_PER_OUTPUT_TOKEN == pytest.approx(15.00 / 1_000_000)
    assert COST_PER_CACHE_WRITE == pytest.approx(3.75 / 1_000_000)
    assert COST_PER_CACHE_READ == pytest.approx(0.30 / 1_000_000)
