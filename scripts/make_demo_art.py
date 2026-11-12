#!/usr/bin/env python3
"""Draw two original aligned example characters; output folders must be new."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw


def make(root, ident, name, hair, shirt, accent, ears):
    folder = root / ident
    folder.mkdir(parents=True, exist_ok=False)
    def layer(file, draw):
        image = Image.new("RGBA", (256, 256))
        draw(ImageDraw.Draw(image))
        image.save(folder / (file + ".png"))
    ink = "#303550"
    skin = "#f7ceb6"
    def back(d):
        d.ellipse((48, 25, 208, 195), fill=hair, outline=ink, width=5)
        d.rounded_rectangle((50, 90, 206, 214), 35, fill=hair, outline=ink, width=5)
        if ears:
            d.polygon([(52, 64), (50, 18), (94, 45)], fill=hair, outline=ink, width=5)
            d.polygon([(162, 45), (206, 18), (204, 64)], fill=hair, outline=ink, width=5)
    def body(d):
        d.rounded_rectangle((78, 158, 178, 241), 25, fill=shirt, outline=ink, width=5)
        d.polygon([(102, 159), (128, 184), (154, 159)], fill="#f6f5ef")
        d.ellipse((118, 185, 138, 205), fill=accent)
    def arm(d, left):
        x = 49 if left else 159
        d.rounded_rectangle((x, 164, x + 48, 219), 18, fill=shirt, outline=ink, width=5)
        x = 46 if left else 174
        d.ellipse((x, 204, x + 36, 236), fill=skin, outline="#795857", width=4)
    def head(d):
        d.ellipse((65, 46, 191, 174), fill=skin, outline="#795857", width=5)
        d.pieslice((60, 28, 196, 144), 180, 355, fill=hair, outline=ink, width=5)
        d.ellipse((90, 100, 105, 124), fill=ink)
        d.ellipse((151, 100, 166, 124), fill=ink)
        d.arc((112, 117, 144, 144), 0, 180, fill="#a05e60", width=3)
        d.ellipse((74, 126, 97, 136), fill="#edaaaa")
        d.ellipse((159, 126, 182, 136), fill="#edaaaa")
        d.ellipse((145, 57, 163, 75), fill=accent)
    def ahoge(d):
        d.arc((115, 6, 160, 56), 185, 310, fill=ink, width=9)
        d.arc((116, 7, 160, 55), 185, 310, fill=accent, width=5)
    for file, draw in (("hair", back), ("body", body), ("left", lambda d: arm(d, True)),
                       ("right", lambda d: arm(d, False)), ("head", head), ("ahoge", ahoge)):
        layer(file, draw)
    data = {"version": 2, "name": name, "leftPivotX": .32, "armPivotY": .68,
            "rightPivotX": .68, "rightArmPivotY": .68, "hairPivotX": .5, "hairPivotY": .22,
            "headPivotX": .5, "headPivotY": .56, "ahogePivotX": .5, "ahogePivotY": .14}
    (folder / "skin.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    make(args.output, "sunny", "暖阳伙伴", "#c87a4d", "#e7b46e", "#f9e27b", True)
    make(args.output, "starlight", "星光伙伴", "#7765a3", "#5f94ae", "#f4d77f", False)
