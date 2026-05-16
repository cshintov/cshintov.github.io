#!/usr/bin/env python3
"""Resume build — render data.yaml + src/shells/*.html.j2 → variants/*.html

Usage: python3 build.py
Edit src/data.yaml, then rerun.
"""
import sys
import time
from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader, ChainableUndefined

ROOT = Path(__file__).parent
SRC = ROOT / "src"
SHELLS = SRC / "shells"
OUT = ROOT / "variants"


def main() -> None:
    data = yaml.safe_load((SRC / "data.yaml").read_text())

    env = Environment(
        loader=FileSystemLoader(str(SHELLS)),
        autoescape=False,            # we emit pre-formatted HTML strings; the data file owns escaping
        undefined=ChainableUndefined,  # lenient: missing keys → empty, no errors
        trim_blocks=True,
        lstrip_blocks=True,
    )

    OUT.mkdir(exist_ok=True)
    rendered = []

    # Render each (shell, framing) target
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

    # Render the index — knows about both ported and static targets
    nav_groups = {
        "blockchain": [t for t in (data["targets"] + data["static_targets"]) if t["framing"] == "blockchain"],
        "platform":   [t for t in (data["targets"] + data["static_targets"]) if t["framing"] == "platform"],
    }
    # de-dup labels per row so the same shell-label doesn't appear twice within a framing
    seen = {fr: set() for fr in nav_groups}
    for fr, items in nav_groups.items():
        deduped = []
        for it in items:
            if it["out"] in seen[fr]:
                continue
            seen[fr].add(it["out"])
            deduped.append(it)
        nav_groups[fr] = deduped

    all_targets = [it for items in nav_groups.values() for it in items]
    default_target = all_targets[0]["out"]
    default_framing = "blockchain"

    cache_bust = str(int(time.time()))

    index_tpl = env.get_template("index.html.j2")
    (OUT / "index.html").write_text(index_tpl.render(
        person=data["person"],
        nav_groups=nav_groups,
        all_targets=all_targets,
        default_target=default_target,
        default_framing=default_framing,
        cache_bust=cache_bust,
    ))
    print(f"  ✓ index.html  (switcher · {len(all_targets)} targets)")

    print(f"\nWrote {len(rendered) + 1} files to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    sys.exit(main())
