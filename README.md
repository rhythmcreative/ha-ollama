<h1 align="center">Ollama for Home Assistant (with Smart Gatekeeper)</h1>

<div align="center">

<p><i>Enhanced official Ollama conversation integration with built-in, sub-100ms pre-flight intent verification and noise filtering.</i></p>

[![Home Assistant](https://img.shields.io/badge/Home_Assistant-41BDF5?style=for-the-badge&logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange?style=for-the-badge&logo=hacs&logoColor=white)](https://hacs.xyz/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com/)
[![Gemma](https://img.shields.io/badge/Model-Gemma_2:2B-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/gemma)
[![Active](https://img.shields.io/badge/Status-Active-2EA44F?style=for-the-badge)](#)
[![Latency](https://img.shields.io/badge/Latency-<100ms-blueviolet?style=for-the-badge)](#)

</div>

## About

This repository is a drop-in enhancement of the **official Home Assistant Ollama integration** (`homeassistant.components.ollama`). It adds native **Gatekeeper Pre-Flight Verification** directly into Ollama's configuration and conversation platform.

Instead of running an external proxy or intermediate conversation agent, the Ollama conversation agent itself inspects incoming speech using a fast, compact model (`gemma2:2b`) in **<100ms** before assembling large LLM prompts, executing expensive tools (Wikipedia, Weather, Web Search, Entity Control), or running heavy models (e.g. `gemma4:12b`, `llama3:70b`, `qwen2.5:32b`).

## Pipeline Comparison

| Scenario | Standard Official Ollama | Ollama with Gatekeeper |
| :--- | :--- | :--- |
| **TV / Radio Dialogue** | Wakes heavy 12B+ model; triggers tool calls; speaks awkward answers | **Silently discarded in ~130ms**; no speech, zero GPU load |
| **Room Background Chatter** | Often answers unintended questions or says *"Sorry, I didn't understand"* | **Ignored silently**; satellite quietly returns to sleep |
| **Micro-sounds / Acoustic Noise** | Sends single-word noise ("eh", "ah") to the LLM | **Filtered instantly (0ms)** via local regex heuristics |
| **Valid Voice Commands** | Directly invokes heavy LLM (~1.5s - 4s) | **Approved in ~98ms**, seamlessly executed with all tools |
| **Tool Execution** | Gathers and executes tools on false alarms | **Only triggers tools** on confirmed genuine intent |

## Quick Start

### 1. Installation via HACS (Recommended)

1. Open **HACS** in your Home Assistant instance.
2. Click the three dots in the top right corner → **Custom repositories**.
3. Add the repository URL:
   ```text
   https://github.com/rhythmcreative/ha-ollama
   ```
4. Set Type to **Integration** and click **Add**.
5. Find **Ollama (with Gatekeeper)** in the integration list and click **Download**.
6. Restart Home Assistant Core.

### 2. Configuration

1. In Home Assistant, go to **Settings** → **Devices & Services** → **Ollama**.
2. Click **Configure** on your active Conversation Agent (e.g. `4skl/gemma4-12b-mtp:latest`).
3. Toggle **Enable Gatekeeper Pre-Verification** (`enable_gatekeeper`).
4. Select your **Gatekeeper Verifier Model** (recommended: `gemma2:2b`).
5. Keep **Silent Discard on False Alarms** and **Fast Heuristic Noise Filtering** enabled.
6. Click **Submit**.

## How It Works

### 1. Integrated Pre-Flight Intent Classifier
When user speech arrives at `conversation.ollama_conversation`, Gatekeeper intercepts the utterance before any LLM system prompt formatting or tool retrieval occurs. It uses the existing Ollama client to run an instant classification:

```text
User Speech ──► [STT Engine] ──► [Ollama Conversation Agent]
                                            │
                          ┌─────────────────┴─────────────────┐
                          ▼                                   ▼
              [Noise / TV Dialogue: "NO"]            [Valid Intent: "SI"]
                          │                                   │
                 Silent Discard (<130ms)               Native LLM Execution
                (No speech, zero GPU load)          (Gemma 12B + Wikipedia/Weather)
```

### 2. Sub-Millisecond Heuristic Fast Filter
A local in-memory heuristic pass discards empty tokens, single-character acoustic noise, and common vocal fillers (e.g. *"eh"*, *"ah"*, *"mmm"*) in **0 milliseconds**.

### 3. Silent False-Alarm Dismissal
Accidental utterances (TV audio, radio, chatter) return an immediate `action_done` response with empty speech, smoothly putting voice satellites back to sleep without waking the household.

### 4. 100% Native Tool Execution
Real smart home queries (*"enciende la luz"*, *"qué tiempo hace en Madrid"*) proceed normally through the official Home Assistant LLM context pipeline, executing all exposed tools and entities.

## Configuration Options

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `enable_gatekeeper` | Boolean | `false` | Enable fast pre-flight intent classification with a small model (<100ms). |
| `gatekeeper_model` | String | `gemma2:2b` | Lightweight model used to classify queries. |
| `gatekeeper_silent` | Boolean | `true` | Silently dismiss accidental triggers (TV audio, chatter) with zero speech. |
| `gatekeeper_heuristics` | Boolean | `true` | Instantly filter out 1-letter sounds and vocal fillers in 0ms. |
| `gatekeeper_prompt` | Template | *(Built-in)* | System prompt instructing the verifier model. |

## Repository Structure

```text
ha-ollama/
├── hacs.json                                    # HACS integration metadata
├── README.md                                    # Project documentation
└── custom_components/
    └── ollama/
        ├── __init__.py                          # Ollama integration lifecycle
        ├── manifest.json                        # Home Assistant manifest (domain: ollama)
        ├── const.py                             # Configuration constants & defaults
        ├── config_flow.py                       # Native UI options & subentry flow
        ├── conversation.py                      # Pre-flight gatekeeper & conversation entity
        ├── entity.py                            # Base LLM entity & tool invocation
        ├── models.py                            # Model definitions
        ├── ai_task.py                           # AI task platform
        ├── strings.json                         # UI string localization
        └── translations/                        # 35+ localized languages
```

## Requirements

* **Home Assistant:** 2024.1.0 or newer.
* **Ollama Server:** Local or networked Ollama instance.
* **Models:**
  * **Primary Model:** Any instruction model (e.g. `4skl/gemma4-12b-mtp:latest`, `llama3.1:8b`).
  * **Gatekeeper Model:** `gemma2:2b` (recommended), `qwen2.5:1.5b`.

```bash
# Pull the recommended Gatekeeper model
ollama pull gemma2:2b
```

## Disclaimer

This project is a community enhancement based on the official Home Assistant Ollama integration and is not officially affiliated with Nabu Casa.

<div align="center">

<p>Made with ❤️ from rhythmcreative.</p>

</div>
