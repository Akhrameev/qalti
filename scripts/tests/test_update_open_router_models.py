"""Unit tests for scripts/update_open_router_models.py.

Focused on pure data-transform functions and the Swift code generator.
No network calls; all OpenRouter payloads are inline fixtures.
"""

import sys
from pathlib import Path

# Make the parent scripts/ directory importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from update_open_router_models import (  # noqa: E402
    DEFAULT_MODEL_ID,
    extract_model_cost,
    filter_models_by_category,
    find_model_data,
    generate_swift_enum_with_categories,
    select_suitable_models,
    to_swift_case_name,
)

# ---------- Fixtures ----------


def _raw_model(
    model_id: str,
    *,
    prompt: str | None = "0",
    completion: str | None = "0",
    context_length: int | None = 128000,
    max_completion_tokens: int | None = 4096,
    modality: str = "text+image->text",
    name: str | None = None,
) -> dict:
    """Build a minimal OpenRouter-style raw model dict."""
    return {
        "id": model_id,
        "name": name or model_id,
        "description": "",
        "pricing": {"prompt": prompt, "completion": completion},
        "context_length": context_length,
        "top_provider": {"max_completion_tokens": max_completion_tokens},
        "architecture": {"modality": modality},
    }


def _default_model_raw(**overrides) -> dict:
    kwargs = {
        "prompt": "0.000003",
        "completion": "0.000015",
        "context_length": 1_000_000,
        "max_completion_tokens": 128_000,
    }
    kwargs.update(overrides)
    return _raw_model(DEFAULT_MODEL_ID, **kwargs)


# ---------- to_swift_case_name ----------


class TestToSwiftCaseName:
    def test_replaces_special_chars(self):
        seen: dict = {}
        assert (
            to_swift_case_name("google/gemma-3.4-it:free", seen)
            == "google_gemma_3_4_it_free"
        )

    def test_leading_digit_gets_prefix(self):
        seen: dict = {}
        assert to_swift_case_name("3lab/model", seen) == "m_3lab_model"

    def test_dedup_via_seen_dict(self):
        seen: dict = {}
        first = to_swift_case_name("a/b-c", seen)
        second = to_swift_case_name("a/b-c", seen)
        third = to_swift_case_name("a/b-c", seen)
        assert (first, second, third) == ("a_b_c", "a_b_c_1", "a_b_c_2")

    def test_plus_becomes_word(self):
        seen: dict = {}
        assert to_swift_case_name("foo/bar+exp", seen) == "foo_bar_plusexp"


# ---------- extract_model_cost ----------


class TestExtractModelCost:
    def test_sums_per_1k(self):
        m = {"pricing": {"prompt": "0.000003", "completion": "0.000015"}}
        # (0.000003 + 0.000015) * 1000 = 0.018
        assert extract_model_cost(m) == 0.018

    def test_missing_pricing_is_zero(self):
        assert extract_model_cost({}) == 0.0

    def test_null_fields_treated_as_zero(self):
        m = {"pricing": {"prompt": None, "completion": None}}
        assert extract_model_cost(m) == 0.0

    def test_garbage_returns_zero(self):
        m = {"pricing": {"prompt": "not-a-number", "completion": "0"}}
        assert extract_model_cost(m) == 0.0


# ---------- find_model_data ----------


class TestFindModelData:
    def test_hit(self):
        models = [_raw_model("a/b"), _raw_model("c/d")]
        assert find_model_data(models, "c/d")["id"] == "c/d"

    def test_miss(self):
        assert find_model_data([_raw_model("a/b")], "nope") is None


# ---------- filter_models_by_category ----------


class TestFilterModelsByCategory:
    def test_free_vision_classification(self):
        models = [_raw_model("google/gemma-vision:free", prompt="0", completion="0")]
        cats = filter_models_by_category(models)
        assert len(cats["free_vision"]) == 1
        assert cats["free_vision"][0]["id"] == "google/gemma-vision:free"
        assert cats["cheap_vision"] == []
        assert cats["free_text_only"] == []

    def test_cheap_vision_classification(self):
        # 0.000003 prompt + 0.000015 completion — both < 0.01 and > 0
        models = [
            _raw_model(
                "anthropic/claude-3-haiku", prompt="0.000003", completion="0.000015"
            )
        ]
        cats = filter_models_by_category(models)
        assert cats["free_vision"] == []
        assert len(cats["cheap_vision"]) == 1

    def test_expensive_model_excluded(self):
        models = [_raw_model("openai/gpt-99", prompt="0.05", completion="0.10")]
        cats = filter_models_by_category(models)
        assert cats == {"free_vision": [], "cheap_vision": [], "free_text_only": []}

    def test_free_text_only_classification(self):
        # No vision-related keywords or modality
        models = [
            _raw_model(
                "some-vendor/text-llm:free",
                prompt="0",
                completion="0",
                modality="text->text",
            )
        ]
        cats = filter_models_by_category(models)
        assert len(cats["free_text_only"]) == 1
        assert cats["free_vision"] == []

    def test_null_pricing_treated_as_expensive(self):
        models = [_raw_model("ghost/model", prompt=None, completion=None)]
        cats = filter_models_by_category(models)
        # null pricing falls through both is_free and is_cheap branches
        assert cats == {"free_vision": [], "cheap_vision": [], "free_text_only": []}

    def test_preserves_top_provider_max_completion_tokens_none(self):
        """Regression: the null max_completion_tokens must reach the generator unchanged
        — that's exactly the input that exposed the 60-token bug."""
        models = [
            _raw_model(
                "openrouter/free",
                prompt="0",
                completion="0",
                max_completion_tokens=None,
                context_length=200000,
            )
        ]
        cats = filter_models_by_category(models)
        m = cats["free_vision"][0]
        assert m["max_completion_tokens"] is None
        assert m["context_length"] == 200000


# ---------- select_suitable_models ----------


class TestSelectSuitableModels:
    def test_all_free_used_when_enough(self):
        free = [
            {"id": f"f/{i}", "prompt_cost": 0, "completion_cost": 0} for i in range(6)
        ]
        cats = {"free_vision": free, "cheap_vision": [], "free_text_only": []}
        out = select_suitable_models(cats)
        assert len(out) == 6

    def test_paid_topped_up_when_few_free(self):
        free = [{"id": "f/0", "prompt_cost": 0, "completion_cost": 0}]
        cheap = [
            {"id": f"c/{i}", "prompt_cost": i * 0.001, "completion_cost": 0}
            for i in range(20)
        ]
        cats = {"free_vision": free, "cheap_vision": cheap, "free_text_only": []}
        out = select_suitable_models(cats)
        # 1 free + 9 cheap (to reach 10), cheapest first
        assert len(out) == 10
        assert out[0]["id"] == "f/0"
        # First paid should be the cheapest (c/0)
        assert out[1]["id"] == "c/0"

    def test_no_topup_when_5_or_more(self):
        free = [
            {"id": f"f/{i}", "prompt_cost": 0, "completion_cost": 0} for i in range(5)
        ]
        cheap = [{"id": "c/0", "prompt_cost": 0.001, "completion_cost": 0}]
        cats = {"free_vision": free, "cheap_vision": cheap, "free_text_only": []}
        assert len(select_suitable_models(cats)) == 5


# ---------- generate_swift_enum_with_categories — bug-fix regression tests ----------


class TestGeneratorTokenFallback:
    """Regression tests for the bug where `top_provider.max_completion_tokens=None`
    produced `maxCompletionTokens: 60` in generated Swift."""

    def _generate(self, suitable_model_overrides, default_overrides=None):
        # filter_models_by_category puts max_completion_tokens at the top level
        # of the model dict — mirror that here.
        suitable_model = {
            "id": "openrouter/free",
            "name": "Free Models Router",
            "description": "",
            "prompt_cost": 0,
            "completion_cost": 0,
            "context_length": 200000,
            "max_completion_tokens": None,
            "modality": "text+image->text",
            "architecture": {},
            **suitable_model_overrides,
        }
        cats = {
            "free_vision": [suitable_model],
            "cheap_vision": [],
            "free_text_only": [],
        }
        default = _default_model_raw(**(default_overrides or {}))
        return generate_swift_enum_with_categories(cats, [default])

    def test_null_max_completion_falls_back_to_context_length(self):
        swift = self._generate({})
        # The bug was: `return 60` for openrouter/free.
        assert "return 60\n" not in swift
        # Now the fallback uses context_length.
        assert "return 200000\n" in swift

    def test_null_max_and_null_context_falls_back_to_4096(self):
        swift = self._generate({"context_length": None, "max_completion_tokens": None})
        assert "return 4096\n" in swift
        assert "return 60\n" not in swift

    def test_explicit_max_completion_tokens_wins(self):
        swift = self._generate(
            {"max_completion_tokens": 8192, "context_length": 200000}
        )
        assert "return 8192\n" in swift

    def test_default_model_uses_context_length_when_max_is_null(self):
        # default model with null max_completion_tokens should also fall back
        swift = self._generate({}, default_overrides={"max_completion_tokens": None})
        # default context_length is 1_000_000 from _default_model_raw
        assert "return 1000000\n" in swift

    def test_default_model_uses_4096_when_both_null(self):
        swift = self._generate(
            {},
            default_overrides={"max_completion_tokens": None, "context_length": None},
        )
        # 4096 appears at least once (for the default model)
        assert "return 4096\n" in swift


class TestGeneratorContextLength:
    """The new `contextLength` Swift property must be emitted."""

    def test_context_length_property_present(self):
        model = {
            "id": "openrouter/free",
            "name": "Free Models Router",
            "description": "",
            "prompt_cost": 0,
            "completion_cost": 0,
            "context_length": 200000,
            "max_completion_tokens": None,
            "modality": "text+image->text",
            "architecture": {},
        }
        cats = {"free_vision": [model], "cheap_vision": [], "free_text_only": []}
        swift = generate_swift_enum_with_categories(cats, [_default_model_raw()])

        assert "var contextLength: Int {" in swift
        # Default model context length: 1_000_000
        assert "return 1000000\n" in swift
        # Model context length: 200_000
        assert "return 200000\n" in swift

    def test_null_context_length_in_model_falls_back_to_4096(self):
        model = {
            "id": "weird/model",
            "name": "weird",
            "description": "",
            "prompt_cost": 0,
            "completion_cost": 0,
            "context_length": None,
            "max_completion_tokens": None,
            "modality": "text+image->text",
            "architecture": {},
        }
        cats = {"free_vision": [model], "cheap_vision": [], "free_text_only": []}
        swift = generate_swift_enum_with_categories(cats, [_default_model_raw()])
        # contextLength block should contain 4096 (for the weird model)
        # Split on `var contextLength` to isolate that block
        ctx_block = swift.split("var contextLength: Int {", 1)[1]
        assert "return 4096" in ctx_block


class TestGeneratedSwiftStructure:
    """Sanity checks that the generated Swift is syntactically plausible."""

    def test_contains_required_properties(self):
        model = {
            "id": "google/gemma-vision:free",
            "name": "Gemma Vision",
            "description": "",
            "prompt_cost": 0,
            "completion_cost": 0,
            "context_length": 32768,
            "max_completion_tokens": 32768,
            "modality": "text+image->text",
            "architecture": {},
        }
        cats = {"free_vision": [model], "cheap_vision": [], "free_text_only": []}
        swift = generate_swift_enum_with_categories(cats, [_default_model_raw()])

        assert "enum OpenRouterModel: String, CaseIterable {" in swift
        assert 'case defaultModel = "anthropic/claude-sonnet-4.6"' in swift
        assert "var displayName: String {" in swift
        assert "var maxCompletionTokens: Int {" in swift
        assert "var contextLength: Int {" in swift
        assert "var isVisionCapable: Bool {" in swift
        assert "var isFree: Bool {" in swift
        assert "var estimatedCostPer1KTokens: Double {" in swift
        # Braces balanced (smoke check)
        assert swift.count("{") == swift.count("}")
