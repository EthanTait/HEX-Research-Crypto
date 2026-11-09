# experiment yaml + machine paths. nothing else in the package reads files directly
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

LEADERS = ["BTCUSDT", "ETHUSDT"]
FOLLOWERS = ["SOLUSDT", "XRPUSDT", "DOGEUSDT"]
SYMS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
BARS_PER_DAY = 1440
MIN_PER_YEAR = 525_600  # 24/7 market


def paths():
    cfg = yaml.safe_load((ROOT / "config" / "local.yaml").read_text())["paths"]
    return {k: (Path(v) if Path(v).is_absolute() else ROOT / v) for k, v in cfg.items()}


def load(name):
    return yaml.safe_load((ROOT / "config" / f"{name}.yaml").read_text())
