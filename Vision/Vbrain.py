"""Local camera capture and image understanding through Ollama vision models."""

import base64
import json
import os
from pathlib import Path

import cv2
import requests


DEFAULT_VISION_MODEL = os.environ.get("ASTRA_VISION_MODEL", "gemma3:4b").strip()
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
VISION_TIMEOUT_SECONDS = float(os.environ.get("ASTRA_VISION_TIMEOUT", "45"))


def capture_image_and_save(image_path="captured_image.png"):
    device_setting = os.environ.get("ASTRA_CAMERA_INDEX", "0").strip()
    try:
        device_index = int(device_setting)
    except ValueError as exc:
        raise ValueError("ASTRA_CAMERA_INDEX must be an integer camera index.") from exc
    camera = cv2.VideoCapture(device_index)
    if not camera.isOpened():
        camera.release()
        return False
    try:
        captured, frame = camera.read()
        if not captured:
            return False
        target = Path(image_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        return bool(cv2.imwrite(str(target), frame))
    finally:
        camera.release()


def encode_image_to_base64(image_path):
    return base64.b64encode(Path(image_path).read_bytes()).decode("ascii")


def vision_brain(encoded_image, prompt="Describe the image and read any visible text.", model=None):
    if not encoded_image:
        raise ValueError("Image data is empty.")
    selected_model = model or DEFAULT_VISION_MODEL
    payload = {
        "model": selected_model,
        "messages": [{
            "role": "user",
            "content": str(prompt),
            "images": [encoded_image],
        }],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json=payload,
            timeout=(3, VISION_TIMEOUT_SECONDS),
        )
        response.raise_for_status()
        data = response.json()
        answer = data.get("message", {}).get("content", "").strip()
        if not answer:
            raise RuntimeError("The local vision model returned an empty response.")
        return answer
    except requests.RequestException as exc:
        detail = str(exc)
        if getattr(exc, "response", None) is not None and exc.response is not None:
            try:
                detail = exc.response.json().get("error", detail)
            except (ValueError, json.JSONDecodeError):
                pass
        raise RuntimeError(
            f"Local vision is unavailable for {selected_model}. Check Ollama and install the model. {detail}"
        ) from exc
