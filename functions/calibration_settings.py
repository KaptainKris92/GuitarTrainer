import json
from pathlib import Path


DEFAULT_INPUT_RMS_THRESHOLD = 0.01
SETTINGS_DIR = Path.home() / ".guitar_trainer"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


def _coerce_threshold(value):
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return DEFAULT_INPUT_RMS_THRESHOLD


def load_calibration_settings():
    if not SETTINGS_FILE.exists():
        return {"input_rms_threshold": DEFAULT_INPUT_RMS_THRESHOLD}

    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"input_rms_threshold": DEFAULT_INPUT_RMS_THRESHOLD}

    return {
        "input_rms_threshold": _coerce_threshold(
            payload.get("input_rms_threshold", DEFAULT_INPUT_RMS_THRESHOLD)
        )
    }


def save_calibration_settings(input_rms_threshold):
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"input_rms_threshold": _coerce_threshold(input_rms_threshold)}
    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
