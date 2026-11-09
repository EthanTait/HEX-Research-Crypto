# every run that produces a metric appends one line here, from code, failed and rejected ones too
import datetime as dt
import json
import subprocess

from ..config import ROOT

PATH = ROOT / "experiments" / "registry.jsonl"


def git_state():
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "python/notset"], cwd=ROOT, capture_output=True, text=True).stdout.strip() != ""
        return h or "none", dirty
    except Exception:
        return "none", True


def new_id(name):
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "_" + name


def append(line):
    h, dirty = git_state()
    line.setdefault("git_hash", h)
    line.setdefault("dirty", dirty)
    with open(PATH, "a") as f:
        f.write(json.dumps(line, default=float) + "\n")
    return line["run_id"]
