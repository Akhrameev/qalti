#!/usr/bin/env python3
"""
Script to fetch available models from OpenRouter API and generate Swift code.
Shows both free models and cheap vision models.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


def ensure_output_dir() -> Path:
    """Ensure output directory exists."""
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def fetch_models() -> list[dict[str, Any]]:
    """Fetch all models from OpenRouter API."""
    url = "https://openrouter.ai/api/v1/models"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.RequestException as e:
        print(f"Error fetching models: {e}")
        return []


def save_full_models_list(models: list[dict[str, Any]]) -> Path:
    """Save the complete models list for investigation."""
    output_dir = ensure_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"openrouter_models_full_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(
            {
                "fetched_at": datetime.now().isoformat(),
                "total_count": len(models),
                "models": models,
            },
            f,
            indent=2,
        )

    print(f"Full models list saved to: {filename}")
    return filename


def analyze_models(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Analyze models to understand their structure and find vision-capable ones."""
    print("\n=== MODEL ANALYSIS ===")

    if not models:
        return []

    # Check model structure
    print("Sample model structure:")
    sample = models[0]
    print(f"Keys: {list(sample.keys())}")

    # Check for vision indicators
    vision_indicators = []
    vision_keywords = ["vision", "multimodal", "image", "visual", "gpt-4v", "claude-3"]
    for model in models:
        model_id = model.get("id", "")
        model_name = model.get("name", "")
        pricing = model.get("pricing", {})
        try:
            prompt_cost = float(pricing.get("prompt") or 0)
            completion_cost = float(pricing.get("completion") or 0)
        except (ValueError, TypeError):
            prompt_cost = 0.0
            completion_cost = 0.0
        is_free = prompt_cost == 0.0
        architecture = model.get("architecture", {})
        modality = architecture.get("modality", "") if architecture else ""
        has_vision_keyword = any(
            keyword in model_id.lower() or keyword in model_name.lower()
            for keyword in vision_keywords
        )
        if (
            has_vision_keyword
            or "multimodal" in modality.lower()
            or "image" in modality.lower()
        ):
            vision_indicators.append(
                {
                    "id": model_id,
                    "name": model_name,
                    "modality": modality,
                    "prompt_cost": prompt_cost,
                    "completion_cost": completion_cost,
                    "is_free": is_free,
                    "architecture": architecture,
                }
            )
    print(f"Total models: {len(models)}")
    print(f"Models with vision keywords: {len(vision_indicators)}")
    if vision_indicators:
        print("\nVision-capable models found:")
        for i, model in enumerate(vision_indicators[:10]):
            print(f"  {i + 1}. {model['id']}")
            print(f"     Name: {model['name']}")
            print(f"     Modality: {model['modality']}")
            print(
                f"     Costs: prompt={model['prompt_cost']}, completion={model['completion_cost']}"
            )
            print(f"     Free: {model['is_free']}")
            print()
        if len(vision_indicators) > 10:
            print(f"     ... and {len(vision_indicators) - 10} more")
    return vision_indicators


def analyze_free_models(models: list[dict[str, Any]]):
    """Analyze truly free models (cost = 0)."""
    print("\n=== FREE MODELS ANALYSIS ===")

    free_models = []
    for model in models:
        pricing = model.get("pricing", {})
        try:
            prompt_cost = float(pricing.get("prompt") or 0)
        except (ValueError, TypeError):
            prompt_cost = 0.0

        is_free = prompt_cost == 0.0
        if is_free:
            architecture = model.get("architecture", {})
            modality = architecture.get("modality", "") if architecture else ""

            free_models.append(
                {
                    "id": model["id"],
                    "name": model.get("name", ""),
                    "modality": modality,
                    "description": model.get("description", ""),
                }
            )

    print(f"Found {len(free_models)} truly free models:")
    vision_free_count = 0
    for model in free_models:
        vision_capable = any(
            keyword in model["modality"].lower()
            for keyword in ["image", "multimodal", "vision"]
        )
        vision_str = " [VISION]" if vision_capable else ""
        if vision_capable:
            vision_free_count += 1
        print(f"  - {model['id']}{vision_str}")
        print(f"    Modality: {model['modality']}")
        if vision_capable:
            print("    ⭐ This model supports vision!")
        print()

    print(f"Free models with vision: {vision_free_count}")
    return free_models


def filter_models_by_category(
    models: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Filter models into categories: free vision, cheap vision, free text-only."""

    free_vision = []
    cheap_vision = []
    free_text_only = []

    print("\n=== FILTERING MODELS BY CATEGORY ===")

    for model in models:
        model_id = model.get("id", "")
        model_name = model.get("name", "")

        # Check pricing
        pricing = model.get("pricing", {})
        prompt_cost_str = pricing.get("prompt", "999")
        completion_cost_str = pricing.get("completion", "999")

        try:
            prompt_cost = float(prompt_cost_str) if prompt_cost_str is not None else 999
        except (ValueError, TypeError):
            prompt_cost = 999

        try:
            completion_cost = (
                float(completion_cost_str) if completion_cost_str is not None else 999
            )
        except (ValueError, TypeError):
            completion_cost = 999

        is_free = prompt_cost == 0
        is_cheap = prompt_cost < 0.01 and completion_cost < 0.01

        # Check for vision capabilities
        architecture = model.get("architecture", {})
        modality = architecture.get("modality", "") if architecture else ""

        vision_keywords = [
            "vision",
            "multimodal",
            "image",
            "visual",
            "gpt-4v",
            "claude-3",
            "llava",
            "gemini",
        ]
        has_vision_keyword = any(
            keyword in model_id.lower() or keyword in model_name.lower()
            for keyword in vision_keywords
        )

        supports_vision = (
            "image" in modality.lower()
            or "multimodal" in modality.lower()
            or has_vision_keyword
        )

        model_data = {
            "id": model["id"],
            "name": model.get("name", model["id"]),
            "description": model.get("description", ""),
            "prompt_cost": prompt_cost,
            "completion_cost": completion_cost,
            "context_length": model.get("context_length", 0),
            "max_completion_tokens": model.get("top_provider", {}).get(
                "max_completion_tokens"
            ),
            "modality": modality,
            "architecture": architecture,
        }

        if is_free and supports_vision:
            print(f"Found FREE vision model: {model_id}")
            free_vision.append(model_data)
        elif is_cheap and supports_vision:
            total_cost = prompt_cost + completion_cost
            print(
                f"Found CHEAP vision model: {model_id} (~${total_cost * 1000:.4f}/1K tokens)"
            )
            cheap_vision.append(model_data)
        elif is_free:
            free_text_only.append(model_data)

    return {
        "free_vision": free_vision,
        "cheap_vision": cheap_vision,
        "free_text_only": free_text_only,
    }


def select_suitable_models(
    categories: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Select suitable models: all free vision, plus cheapest paid vision if fewer than 5."""
    suitable = categories["free_vision"].copy()
    if len(suitable) < 5:
        cheap_sorted = sorted(
            categories["cheap_vision"],
            key=lambda x: x["prompt_cost"] + x["completion_cost"],
        )
        needed = min(10 - len(suitable), len(cheap_sorted))
        suitable.extend(cheap_sorted[:needed])
    return suitable


def to_swift_case_name(model_id: str, seen: dict[str, int]) -> str:
    name = (
        model_id.replace("/", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace(":", "_")
        .replace("+", "_plus")
    )
    if name[0].isdigit():
        name = "m_" + name
    if name in seen:
        seen[name] += 1
        name = f"{name}_{seen[name]}"
    else:
        seen[name] = 0
    return name


DEFAULT_MODEL_ID = "anthropic/claude-sonnet-4.6"


def find_model_data(
    models: list[dict[str, Any]], model_id: str
) -> dict[str, Any] | None:
    """Look up a model by ID in the raw API models list."""
    return next((m for m in models if m.get("id") == model_id), None)


def extract_model_cost(model: dict[str, Any]) -> float:
    """Return combined prompt+completion cost per 1K tokens from raw API model data."""
    pricing = model.get("pricing", {})
    try:
        prompt = float(pricing.get("prompt") or 0)
        completion = float(pricing.get("completion") or 0)
    except (ValueError, TypeError):
        return 0.0
    return round((prompt + completion) * 1000, 6)


def generate_swift_enum_with_categories(
    categories: dict[str, list[dict[str, Any]]],
    all_models: list[dict[str, Any]],
) -> str:
    """Generate Swift enum with different model categories."""

    suitable_models = select_suitable_models(categories)

    seen: dict[str, int] = {}
    case_names = [to_swift_case_name(model["id"], seen) for model in suitable_models]

    default_raw = find_model_data(all_models, DEFAULT_MODEL_ID)
    default_cost = extract_model_cost(default_raw) if default_raw else 0.0
    default_name = (
        default_raw.get("name", DEFAULT_MODEL_ID) if default_raw else DEFAULT_MODEL_ID
    )
    default_max_tokens = (
        ((default_raw.get("top_provider") or {}).get("max_completion_tokens") or 60)
        if default_raw
        else 60
    )

    swift_code = f"""//
//  OpenRouterModels.swift
//  Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
//
//  Free vision models: {len(categories["free_vision"])}
//  Cheap vision models: {len(categories["cheap_vision"])}
//  Free text-only models: {len(categories["free_text_only"])}
//

import Foundation

enum OpenRouterModel: String, CaseIterable {{
    // Default model (paid)
    case defaultModel = "{DEFAULT_MODEL_ID}"

    // Vision models (free or very cheap)
"""
    for model, case_name in zip(suitable_models, case_names, strict=True):
        swift_code += f'    case {case_name} = "{model["id"]}"\n'

    swift_code += f"""
    var displayName: String {{
        switch self {{
        case .defaultModel:
            return "{default_name} (Default - Paid)"
"""

    for model, case_name in zip(suitable_models, case_names, strict=True):
        cost_info = (
            "FREE"
            if model["prompt_cost"] == 0
            else f"~${(model['prompt_cost'] + model['completion_cost']) * 1000:.4f}/1K"
        )
        swift_code += f'        case .{case_name}:\n            return "{model["name"]} ({cost_info})"\n'

    swift_code += f"""        }}
    }}

    var maxCompletionTokens: Int {{
        switch self {{
        case .defaultModel:
            return {default_max_tokens}
"""

    for model, case_name in zip(suitable_models, case_names, strict=True):
        max_tokens = model.get("max_completion_tokens") or 60
        swift_code += f"        case .{case_name}:\n            return {max_tokens}\n"

    swift_code += """        }
    }

    var isVisionCapable: Bool {
        return true  // All models in this enum support vision
    }

    var isFree: Bool {
        switch self {
        case .defaultModel:
            return false
"""

    for model, case_name in zip(suitable_models, case_names, strict=True):
        is_free = model.get("prompt_cost", 0) == 0
        swift_code += (
            f"        case .{case_name}:\n            return {str(is_free).lower()}\n"
        )

    swift_code += f"""        }}
    }}

    var estimatedCostPer1KTokens: Double {{
        switch self {{
        case .defaultModel:
            return {default_cost}
"""

    for model, case_name in zip(suitable_models, case_names, strict=True):
        total_cost = (model["prompt_cost"] + model["completion_cost"]) * 1000
        swift_code += f"        case .{case_name}:\n            return {total_cost}\n"

    swift_code += """        }
    }
}
"""

    return swift_code


def save_categorized_data(categories: dict[str, list[dict[str, Any]]]):
    """Save categorized model data to output directory."""
    output_dir = ensure_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save categorized data
    categorized_file = output_dir / f"openrouter_models_categorized_{timestamp}.json"
    with open(categorized_file, "w") as f:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(),
                "categories": categories,
                "summary": {
                    "free_vision_count": len(categories["free_vision"]),
                    "cheap_vision_count": len(categories["cheap_vision"]),
                    "free_text_only_count": len(categories["free_text_only"]),
                },
            },
            f,
            indent=2,
        )
    print(f"Categorized model data saved: {categorized_file}")

    # Save just the suitable models for easier reference
    suitable_models = select_suitable_models(categories)

    suitable_file = output_dir / f"openrouter_suitable_models_{timestamp}.json"
    with open(suitable_file, "w") as f:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(),
                "suitable_models": suitable_models,
            },
            f,
            indent=2,
        )
    print(f"Suitable models saved: {suitable_file}")


def load_confirmed_vision_ids(availability_results_path: str) -> set[str]:
    """Load model IDs confirmed as vision-capable from a check_model_availability results file."""
    try:
        with open(availability_results_path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading availability results: {e}")
        return set()

    confirmed = {
        r["model_id"]
        for r in data.get("results", [])
        if r.get("available") and r.get("vision_capable")
    }
    print(
        f"Loaded {len(confirmed)} confirmed vision-capable models from availability results"
    )
    return confirmed


def filter_categories_by_availability(
    categories: dict[str, list[dict[str, Any]]],
    confirmed_ids: set[str],
) -> dict[str, list[dict[str, Any]]]:
    """Remove models not confirmed as available + vision-capable from categories."""
    filtered = {
        key: [m for m in models if m["id"] in confirmed_ids]
        for key, models in categories.items()
    }
    for key in ("free_vision", "cheap_vision"):
        removed = len(categories[key]) - len(filtered[key])
        if removed:
            print(f"  Removed {removed} unconfirmed models from {key}")
    return filtered


def main():
    parser = argparse.ArgumentParser(
        description="Fetch OpenRouter models and generate Swift enum"
    )
    parser.add_argument(
        "--availability-results",
        metavar="FILE",
        help="Path to model_availability_test JSON from check_model_availability.py; "
        "only models confirmed available+vision-capable will be included in Swift output",
    )
    args = parser.parse_args()

    print("Fetching OpenRouter models...")
    models = fetch_models()
    print(f"Found {len(models)} total models")

    if not models:
        print("No models fetched. Exiting.")
        return

    # Save full models list
    save_full_models_list(models)

    # Categorize models
    categories = filter_models_by_category(models)

    print("\n=== FINAL RESULTS ===")
    print(f"Free vision models: {len(categories['free_vision'])}")
    print(f"Cheap vision models: {len(categories['cheap_vision'])}")
    print(f"Free text-only models: {len(categories['free_text_only'])}")

    if args.availability_results:
        print("\n=== FILTERING BY AVAILABILITY RESULTS ===")
        confirmed_ids = load_confirmed_vision_ids(args.availability_results)
        if confirmed_ids:
            categories = filter_categories_by_availability(categories, confirmed_ids)
            print(
                f"Confirmed vision-capable models: {len(categories['free_vision'])} free, "
                f"{len(categories['cheap_vision'])} cheap"
            )
        else:
            print(
                "⚠️  No confirmed models found — generating Swift without availability filter"
            )

    if categories["free_vision"]:
        print("\n🎉 Free vision models found:")
        for model in categories["free_vision"]:
            print(f"  - {model['id']} ({model['name']})")
    else:
        print("\n⚠️ No free vision models found. Using cheapest vision models:")
        cheap_sorted = sorted(
            categories["cheap_vision"],
            key=lambda x: x["prompt_cost"] + x["completion_cost"],
        )
        for model in cheap_sorted[:5]:
            total_cost = model["prompt_cost"] + model["completion_cost"]
            print(f"  - {model['id']} (~${total_cost * 1000:.4f}/1K tokens)")

    # Generate Swift code
    swift_code = generate_swift_enum_with_categories(categories, models)

    # Save Swift file
    output_file = (
        Path(__file__).resolve().parent.parent
        / "xcodeproject/Qalti/Services/UIHelpers/OpenRouterModels.swift"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        f.write(swift_code)
    print(f"\nSwift enum generated: {output_file}")

    # Save categorized data
    save_categorized_data(categories)

    print("\nAll intermediate files saved to scripts/output/")


if __name__ == "__main__":
    main()
