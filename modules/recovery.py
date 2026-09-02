"""Crash-recovery for active generations.

When a synthesis job starts we persist a small "job" file. As each text chunk
is committed to disk the completed count and status are updated in real time.
If the app crashes or is killed mid-generation, the job file plus the always-
valid partial WAV let the user resume the same generation after restarting.
"""

import json
import os
import time
import uuid


RECOVERY_DIR = os.path.join("storage", "recovery")


class GenerationJob:
    def __init__(self, job_id, chunks, voice, model, out_path,
                 completed=0, status="active", created=None, updated=None):
        self.job_id = job_id
        self.chunks = list(chunks)
        self.voice = voice
        self.model = model
        self.out_path = os.path.abspath(out_path)
        self.completed = int(completed)
        self.status = status
        self.created = created or time.time()
        self.updated = updated or self.created

    # --- persistence ---
    @property
    def path(self):
        return os.path.join(RECOVERY_DIR, f"{self.job_id}.json")

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "chunks": self.chunks,
            "voice": self.voice,
            "model": self.model,
            "out_path": self.out_path,
            "completed": self.completed,
            "status": self.status,
            "created": self.created,
            "updated": self.updated,
        }

    def save(self):
        os.makedirs(RECOVERY_DIR, exist_ok=True)
        self.updated = time.time()
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
            os.replace(tmp, self.path)
        except Exception as e:
            print(f"[Recovery] could not save job: {e}")

    def update(self, completed=None, status=None):
        if completed is not None:
            self.completed = int(completed)
        if status is not None:
            self.status = status
        self.save()
        return self

    def remove(self):
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
        except OSError as e:
            print(f"[Recovery] could not remove job file: {e}")

    # --- queries ---
    @classmethod
    def from_dict(cls, d):
        return cls(
            job_id=d["job_id"], chunks=d.get("chunks", []),
            voice=d.get("voice", ""), model=d.get("model", ""),
            out_path=d.get("out_path", ""), completed=d.get("completed", 0),
            status=d.get("status", "active"), created=d.get("created"),
            updated=d.get("updated"),
        )

    @classmethod
    def load(cls, job_id):
        p = os.path.join(RECOVERY_DIR, f"{job_id}.json")
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except Exception as e:
            print(f"[Recovery] could not read job {job_id}: {e}")
            return None

    @classmethod
    def active(cls):
        """Return all unfinished ('active') jobs, newest first."""
        jobs = []
        if os.path.isdir(RECOVERY_DIR):
            for fn in os.listdir(RECOVERY_DIR):
                if fn.endswith(".json"):
                    j = cls.load(fn[:-5])
                    if j is not None and j.status == "active" and j.completed < len(j.chunks):
                        jobs.append(j)
        jobs.sort(key=lambda j: j.updated, reverse=True)
        return jobs


def new_job(chunks, voice, model, out_path):
    """Create + persist an active job for a generation about to start."""
    return GenerationJob(
        job_id=uuid.uuid4().hex[:12],
        chunks=chunks, voice=voice, model=model, out_path=out_path,
        status="active",
    ).save() or None


def latest_active():
    jobs = GenerationJob.active()
    return jobs[0] if jobs else None
