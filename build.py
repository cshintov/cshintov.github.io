#!/usr/bin/env python3
"""Resume build — render data.yaml + src/shells/*.html.j2 → variants/*.html

Usage:
  python3 build.py          # render HTML
  python3 build.py --pdf    # render HTML, then WeasyPrint each variant to variants/pdf/<name>.pdf

Requires WeasyPrint (in .venv): uv pip install --python .venv/bin/python weasyprint pyyaml jinja2
Run via the venv directly:  .venv/bin/python build.py --pdf
"""
import argparse
import os
import sys
import time
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader, ChainableUndefined

ROOT = Path(__file__).parent
SRC = ROOT / "src"
SHELLS = SRC / "shells"
OUT = ROOT / "variants"
PDF_OUT = OUT / "pdf"

# Ensure WeasyPrint can find Homebrew's pango/cairo/glib on macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")
os.environ.setdefault("DYLD_FALLBACK_LIBRARY_PATH", "/opt/homebrew/lib")


def render_pdfs(rendered: list[str]) -> None:
    import weasyprint  # imported lazily so HTML-only builds don't need it

    PDF_OUT.mkdir(exist_ok=True)
    print(f"\nRendering PDFs via WeasyPrint {weasyprint.__version__}…")
    # CSS override: in PDF mode we want the .pdf branch active without JS.
    # The engineering-brief shell wraps PDF rules under `html.pdf` — this stylesheet
    # promotes them by mirroring the selector under plain html when WeasyPrint runs.
    pdf_override = weasyprint.CSS(string="html { /* WeasyPrint: .pdf rules below */ } ")
    for name in rendered:
        src = OUT / name
        if not src.exists():
            print(f"  ⚠ {name}: missing, skipping")
            continue
        dst = PDF_OUT / (Path(name).stem + ".pdf")
        try:
            weasyprint.HTML(filename=str(src)).write_pdf(
                str(dst),
                stylesheets=[pdf_override],
                presentational_hints=True,
            )
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            continue
        size_kb = dst.stat().st_size // 1024
        print(f"  ✓ {dst.relative_to(ROOT)}  ({size_kb} KB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true", help="after HTML build, render each variant to PDF via WeasyPrint")
    args = ap.parse_args()

    data = yaml.safe_load((SRC / "data.yaml").read_text())

    env = Environment(
        loader=FileSystemLoader(str(SHELLS)),
        autoescape=False,
        undefined=ChainableUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    OUT.mkdir(exist_ok=True)
    rendered = []

    for t in data["targets"]:
        shell, framing, out_name = t["shell"], t["framing"], t["out"]
        f = data["framings"][framing]
        template = env.get_template(f"{shell}.html.j2")
        html = template.render(
            person=data["person"],
            framings=data["framings"],
            framing=framing,
            f=f,
            tech_stack_common=data["tech_stack_common"],
            experience=data["experience"],
            projects=data["projects"],
        )
        (OUT / out_name).write_text(html)
        rendered.append(out_name)
        print(f"  ✓ {out_name}  ({shell} · {framing})")

    # Index: two-tab switcher (blockchain / platform)
    cache_bust = str(int(time.time()))
    index_tpl = env.get_template("index.html.j2")
    (OUT / "index.html").write_text(index_tpl.render(
        person=data["person"],
        targets=data["targets"],
        default_target=data["targets"][0]["out"],
        cache_bust=cache_bust,
    ))
    print(f"  ✓ index.html  (switcher · {len(data['targets'])} targets)")

    print(f"\nWrote {len(rendered) + 1} files to {OUT.relative_to(ROOT)}/")

    if args.pdf:
        render_pdfs(rendered)


if __name__ == "__main__":
    sys.exit(main())
