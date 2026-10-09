"""Helper to download a Vosk speech recognition model.

Usage:
    python download_vosk_model.py small-en-us-0.15
    python download_vosk_model.py small-vn-0.4
"""

import os
import sys
import zipfile
import urllib.request
import shutil

MODEL_URLS = {
    "small-en-us-0.15": "https://alphacephei.com/kaldi/models/vosk-model-small-en-us-0.15.zip",
    "small-vn-0.4": "https://alphacephei.com/kaldi/models/vosk-model-small-vn-0.4.zip",
    "large-en-us-0.22": "https://alphacephei.com/kaldi/models/vosk-model-large-en-us-0.22.zip",
}

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def download_model(model_name):
    url = MODEL_URLS.get(model_name)
    if not url:
        print(f"Unknown model: {model_name}. Available: {', '.join(MODEL_URLS)}")
        return False

    target_dir = os.path.join(PROJECT_ROOT, f"vosk-model-{model_name}")
    if os.path.isdir(target_dir) and os.listdir(target_dir):
        print(f"Model already exists at {target_dir}")
        return True

    zip_path = os.path.join(PROJECT_ROOT, f"{model_name}.zip")
    print(f"Downloading {url} ...")
    try:
        urllib.request.urlretrieve(url, zip_path)
    except Exception as exc:
        print(f"Download failed: {exc}")
        return False

    print(f"Extracting to {PROJECT_ROOT} ...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        root = os.path.realpath(PROJECT_ROOT)
        for member in zf.infolist():
            destination = os.path.realpath(os.path.join(root, member.filename))
            if os.path.commonpath((root, destination)) != root:
                raise ValueError(f"Unsafe path in model archive: {member.filename}")
        zf.extractall(root)

    os.remove(zip_path)
    print(f"Done. Model ready at {target_dir}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_vosk_model.py <model-name>")
        sys.exit(1)
    download_model(sys.argv[1])
