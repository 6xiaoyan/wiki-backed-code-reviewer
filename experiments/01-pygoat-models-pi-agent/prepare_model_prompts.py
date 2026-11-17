"""Prepare identical group-A protocols with separate labels/output directories."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent
MODELS = (
    ("minimax-m3.1-flash", "MiniMax M3.1 Flash", "https://www.minimax.io/blog/minimax-m31f"),
    ("glm-5.3-flash", "GLM-5.3-Flash", "https://z.ai/blog/glm-5.3-flash"),
    ("qwen-3.8-flash-next", "Qwen3.8-Flash-Next", None),
)
CONFIGURED_ENDPOINTS = {
    "minimax-m3.1-flash": ("minimax-cn", "MiniMax-M3.1-Flash"),
    "glm-5.3-flash": ("lenovo-token-hub", "GLM-5.3-Flash"),
    "qwen-3.8-flash-next": ("lenovo-token-hub", "Qwen3.8-Flash-Next"),
}
TEMPLATE_OUTPUT = (
    "D:/ai_share/langgraph/wiki-backed-code-reviewer/experiments/"
    "01-pygoat-models-pi-agent/group-a-no-rules/runs/<MODEL_LABEL>/<RUN_ID>/"
)


def main() -> None:
    template = (EXPERIMENT / "PROMPT_A.md").read_text(encoding="utf-8")
    if template.count("MODEL_LABEL = model-a") != 1 or template.count(TEMPLATE_OUTPUT) != 1:
        raise RuntimeError("Review the common template before generating prompts")
    template_hash = hashlib.sha256(template.encode()).hexdigest()
    plan_path = EXPERIMENT / "model-plan.json"
    previous = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    previous_models = {m["model_label"]: m for m in previous.get("models", [])}
    models = []
    for label, display, reference in MODELS:
        model_dir = EXPERIMENT / "group-a-no-rules" / label
        output = model_dir / "runs" / "r01"
        output.mkdir(parents=True, exist_ok=True)
        output_text = output.as_posix() + "/"
        prompt = template.replace("MODEL_LABEL = model-a", f"MODEL_LABEL = {label}")
        prompt = prompt.replace(TEMPLATE_OUTPUT, output_text)
        normalized = prompt.replace(f"MODEL_LABEL = {label}", "MODEL_LABEL = model-a")
        normalized = normalized.replace(output_text, TEMPLATE_OUTPUT)
        if normalized != template:
            raise AssertionError("Model-specific protocol drift")
        prompt_path = model_dir / "PROMPT.md"
        if prompt_path.exists():
            if prompt_path.read_text(encoding="utf-8") != prompt:
                raise RuntimeError(f"Existing prompt differs; refusing to overwrite {prompt_path}")
        else:
            prompt_path.write_bytes(prompt.encode("utf-8"))
        (model_dir / "runs" / ".gitkeep").touch(exist_ok=True)
        model = {
            "model_label": label,
            "planned_display_name": display,
            "actual_provider": None,
            "actual_model_id": None,
            "actual_model_revision": None,
            "pi_version": None,
            "reasoning_configuration": None,
            "model_reference": reference,
            "prompt_file": prompt_path.relative_to(EXPERIMENT).as_posix(),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "run_id": "r01",
            "output_directory": str(output),
        }
        for key in ("actual_provider", "actual_model_id", "actual_model_revision", "pi_version", "reasoning_configuration"):
            model[key] = previous_models.get(label, {}).get(key)
        model["configured_provider"], model["configured_model_id"] = CONFIGURED_ENDPOINTS[label]
        model["configuration_note"] = "Endpoint configuration is not proof of the model actually used in a run; verify from session logs."
        models.append(model)
    active_labels = {m["model_label"] for m in models}
    retired = {m["model_label"]: m for m in previous.get("retired_models", [])}
    for label, model in previous_models.items():
        if label not in active_labels:
            retired[label] = {**model, "retired_reason": "Replaced by Qwen3.8-Flash-Next at the user's request; existing files retained."}
    plan = {
        "experiment_id": "01-pygoat-models-pi-agent",
        "group": "A-no-extra-rules",
        "harness": "pi-agent",
        "common_prompt_sha256": template_hash,
        "only_prompt_differences": ["MODEL_LABEL value", "output directory"],
        "operator_notes": [
            "MiniMax's verified coding model name is M3.1 Flash; the requested H3.1 Flash label was not used.",
            "Display names/folder labels are not verified API model IDs. Fill actual IDs/revisions from pi/provider logs.",
            "Qwen3.8-Flash-Next replaces DeepSeek in the active A-group comparison. Existing DeepSeek prompts/results are retained as historical material.",
            "Configured GLM and Qwen IDs were checked in local pi model configuration. Confirm the actual models and thinking settings from each run's logs.",
            "This generator does not modify provider credentials or run models. Existing prompts must match the common protocol to be reused.",
        ],
        "models": models,
        "retired_models": list(retired.values()),
    }
    plan_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for model in models:
        print(model["prompt_file"])
        print(model["output_directory"])


if __name__ == "__main__":
    main()
