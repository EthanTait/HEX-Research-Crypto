# one self-contained report: the milestone markdown with every figure embedded as base64 (no pandoc needed).
# figures come from output/figures (made by the other scripts); the png copies in reports/ are not kept.
# usage: python python/scripts/build_report.py [--keep-png]
import argparse
import base64
import re
import shutil
import sys
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from notset.config import ROOT, paths  # noqa: E402

REPORT = ROOT / "reports" / "milestones" / "milestone-1"
MD = REPORT / "milestone-1.md"
FIG = paths()["output"] / "figures"
# figure names cited in the report -> file in output/figures (the two headline plots have report names)
ALIASES = {"final_desk_v1": "desk2_walk_forward_chosen"}


def embed(md):
    # replace every figures/<name>.png reference with an inline <img> carrying the png as a data uri
    missing = []

    def repl(m):
        name = m.group(1)
        src = FIG / f"{ALIASES.get(name, name)}.png"
        if not src.exists():
            missing.append(name)
            return f"`figures/{name}.png (missing)`"
        b64 = base64.b64encode(src.read_bytes()).decode()
        return f'\n\n<img src="data:image/png;base64,{b64}" alt="{name}" style="max-width:100%">\n\n'

    out = re.sub(r"`figures/([a-z0-9_]+)\.png`", repl, md)
    return out, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-png", action="store_true", help="leave the png copies in reports/.../figures")
    a = ap.parse_args()
    md = MD.read_text()
    body, missing = embed(md)
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_markdown_cell(body))
    exporter = HTMLExporter(template_name="lab", exclude_input_prompt=True, exclude_output_prompt=True)
    html, _ = exporter.from_notebook_node(nb)
    html = html.replace("<title>Notebook</title>", "<title>HEX Research, Milestone 1</title>")
    (REPORT / "milestone-1.html").write_text(html)
    print(f"wrote {REPORT / 'milestone-1.html'} ({len(html) / 1e6:.1f} MB), missing figures: {missing or 'none'}")
    if not a.keep_png and (REPORT / "figures").exists():
        shutil.rmtree(REPORT / "figures")
        print("removed reports/.../figures (regenerate with the scripts in section 8, then rerun this)")


if __name__ == "__main__":
    main()
