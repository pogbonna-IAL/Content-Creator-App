"""
Generate public/ brand assets from web-ui/brand-source/.

Required inputs (add these files, then run: npm run import-brand):
  - brand-source/logo-512.png   — square master logo (e.g. 512×512)
  - brand-source/favicon-64.png — favicon source (e.g. 64×64)

Outputs:
  - public/icon-512.png, icon-192.png, apple-touch-icon.png, logo.png
  - public/favicon.png, favicon.ico (multi-size)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image

WEB_UI = Path(__file__).resolve().parent.parent
BRAND = WEB_UI / "brand-source"
PUBLIC = WEB_UI / "public"


def main() -> None:
    logo_src = BRAND / "logo-512.png"
    fav_src = BRAND / "favicon-64.png"
    if not logo_src.is_file():
        print(f"Missing {logo_src.name}. Copy your 512px logo PNG there.", file=sys.stderr)
        sys.exit(1)
    if not fav_src.is_file():
        print(f"Missing {fav_src.name}. Copy your 64px favicon PNG there.", file=sys.stderr)
        sys.exit(1)

    PUBLIC.mkdir(parents=True, exist_ok=True)

    img512 = Image.open(logo_src).convert("RGBA")
    img512.save(PUBLIC / "icon-512.png", "PNG")
    img512.resize((192, 192), Image.Resampling.LANCZOS).save(PUBLIC / "icon-192.png", "PNG")
    img512.resize((180, 180), Image.Resampling.LANCZOS).save(PUBLIC / "apple-touch-icon.png", "PNG")
    img512.resize((256, 256), Image.Resampling.LANCZOS).save(PUBLIC / "logo.png", "PNG")

    img64 = Image.open(fav_src).convert("RGBA")
    img64.save(PUBLIC / "favicon.png", "PNG")

    sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
    icons = [img64.resize(s, Image.Resampling.LANCZOS) for s in sizes]
    icons[0].save(
        PUBLIC / "favicon.ico",
        format="ICO",
        sizes=[(i.width, i.height) for i in icons],
        append_images=icons[1:],
    )

    names = sorted(
        p.name
        for p in PUBLIC.iterdir()
        if p.suffix.lower() in (".png", ".ico") and p.name.startswith(("icon", "logo", "apple", "favicon"))
    )
    print("Updated:", ", ".join(names))


if __name__ == "__main__":
    main()
