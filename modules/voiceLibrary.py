"""
Voice Library Module

Stores and manages cloned voice profiles.

A cloned voice captures a reference audio clip (recorded or imported) and
stores it under a display name. TTS engines that support audio-conditioned
voices (e.g. pocket_tts E2E-TTS) rebuild a voice prompt from the clip on demand.

Storage layout:
    storage/clones/voices.json   -> metadata index
    storage/clones/<name>.wav    -> raw audio clip
"""

import json
import os
import shutil
import time


CLONES_DIR = os.path.join("storage", "clones")
INDEX_FILE = "voices.json"


def _default_dir():
    return CLONES_DIR


class VoiceLibrary:
    def __init__(self, clones_dir=None):
        self.dir = clones_dir or _default_dir()
        os.makedirs(self.dir, exist_ok=True)
        self.index_path = os.path.join(self.dir, INDEX_FILE)
        self._clones = []
        self._load()

    # --- persistence ---
    def _load(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    self._clones = json.load(f)
            except Exception as e:
                print(f"[VoiceLibrary] could not load index: {e}")
                self._clones = []

    def _save(self):
        try:
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(self._clones, f, indent=4)
        except Exception as e:
            print(f"[VoiceLibrary] could not save index: {e}")

    # --- queries ---
    def list(self):
        return list(self._clones)

    def names(self):
        return [c["name"] for c in self._clones]

    def get(self, name):
        for c in self._clones:
            if c["name"] == name:
                return c
        return None

    def exists(self, name):
        return self.get(name) is not None

    # --- mutations ---
    def add(self, name, wav_path, source="import"):
        """Register a cloned voice from a wav clip."""
        os.makedirs(self.dir, exist_ok=True)
        wav_path = os.path.abspath(wav_path)
        if not os.path.exists(wav_path):
            raise FileNotFoundError(wav_path)

        entry = {
            "name": str(name).strip(),
            "path": wav_path,
            "source": source,
            "created": time.time(),
        }
        self._clones = [c for c in self._clones if c["name"] != entry["name"]]
        self._clones.append(entry)
        self._save()
        return entry

    def remove(self, name, delete_file=True):
        entry = self.get(name)
        if entry is None:
            return False
        self._clones = [c for c in self._clones if c["name"] != name]
        self._save()
        if delete_file and os.path.exists(entry["path"]):
            try:
                os.remove(entry["path"])
            except OSError as e:
                print(f"[VoiceLibrary] could not delete {entry['path']}: {e}")
        return True

    def clear(self):
        self._clones = []
        self._save()

    def source_wav(self, name):
        """Return the audio clip path for a cloned voice name, if any."""
        entry = self.get(name)
        return entry["path"] if entry else None


def copy_into_library(wav_path, name):
    """Copy an external wav into the clone library under `name`."""
    lib = VoiceLibrary()
    os.makedirs(lib.dir, exist_ok=True)
    dest = os.path.join(lib.dir, f"{name}.wav")
    shutil.copyfile(wav_path, dest)
    return lib.add(name, dest, source="import")