//
//  OpenRouterModels.swift
//  Generated on 2026-04-18 02:15:04
//
//  Free vision models: 7
//  Cheap vision models: 0
//  Free text-only models: 0
//

import Foundation

enum OpenRouterModel: String, CaseIterable {
    // Default model (paid)
    case defaultModel = "anthropic/claude-sonnet-4.6"

    // Vision models (free or very cheap)
    case google_gemma_4_26b_a4b_it_free = "google/gemma-4-26b-a4b-it:free"
    case google_gemma_4_31b_it_free = "google/gemma-4-31b-it:free"
    case openrouter_free = "openrouter/free"
    case moonshotai_kimi_k2_5 = "moonshotai/kimi-k2.5"
    case nvidia_nemotron_nano_12b_v2_vl_free = "nvidia/nemotron-nano-12b-v2-vl:free"
    case meta_llama_llama_guard_4_12b_free = "meta-llama/llama-guard-4-12b:free"
    case google_gemma_3_4b_it_free = "google/gemma-3-4b-it:free"

    var displayName: String {
        switch self {
        case .defaultModel:
            return "Anthropic: Claude Sonnet 4.6 (Default - Paid)"
        case .google_gemma_4_26b_a4b_it_free:
            return "Google: Gemma 4 26B A4B  (free) (FREE)"
        case .google_gemma_4_31b_it_free:
            return "Google: Gemma 4 31B (free) (FREE)"
        case .openrouter_free:
            return "Free Models Router (FREE)"
        case .moonshotai_kimi_k2_5:
            return "MoonshotAI: Kimi K2.5 (FREE)"
        case .nvidia_nemotron_nano_12b_v2_vl_free:
            return "NVIDIA: Nemotron Nano 12B 2 VL (free) (FREE)"
        case .meta_llama_llama_guard_4_12b_free:
            return "Meta: Llama Guard 4 12B (free) (FREE)"
        case .google_gemma_3_4b_it_free:
            return "Google: Gemma 3 4B (free) (FREE)"
        }
    }

    var maxCompletionTokens: Int {
        switch self {
        case .defaultModel:
            return 128000
        case .google_gemma_4_26b_a4b_it_free:
            return 32768
        case .google_gemma_4_31b_it_free:
            return 32768
        case .openrouter_free:
            return 60
        case .moonshotai_kimi_k2_5:
            return 60
        case .nvidia_nemotron_nano_12b_v2_vl_free:
            return 128000
        case .meta_llama_llama_guard_4_12b_free:
            return 65000
        case .google_gemma_3_4b_it_free:
            return 8192
        }
    }

    var isVisionCapable: Bool {
        return true  // All models in this enum support vision
    }

    var isFree: Bool {
        switch self {
        case .defaultModel:
            return false
        case .google_gemma_4_26b_a4b_it_free:
            return true
        case .google_gemma_4_31b_it_free:
            return true
        case .openrouter_free:
            return true
        case .moonshotai_kimi_k2_5:
            return true
        case .nvidia_nemotron_nano_12b_v2_vl_free:
            return true
        case .meta_llama_llama_guard_4_12b_free:
            return true
        case .google_gemma_3_4b_it_free:
            return true
        }
    }

    var estimatedCostPer1KTokens: Double {
        switch self {
        case .defaultModel:
            return 0.018
        case .google_gemma_4_26b_a4b_it_free:
            return 0.0
        case .google_gemma_4_31b_it_free:
            return 0.0
        case .openrouter_free:
            return 0.0
        case .moonshotai_kimi_k2_5:
            return 0.0
        case .nvidia_nemotron_nano_12b_v2_vl_free:
            return 0.0
        case .meta_llama_llama_guard_4_12b_free:
            return 0.0
        case .google_gemma_3_4b_it_free:
            return 0.0
        }
    }
}
