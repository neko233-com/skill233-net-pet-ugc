#!/usr/bin/env python3
"""Prepare and inspect a Net Pet layered skin; never alter source artwork."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: python -m pip install Pillow")

V1 = ("hair.png", "body.png", "left.png", "right.png")
V2 = V1 + ("head.png", "ahoge.png")
PIVOTS = {"leftPivotX": .32, "rightPivotX": .68, "armPivotY": .68,
          "rightArmPivotY": .68, "hairPivotX": .5, "hairPivotY": .22,
          "headPivotX": .5, "headPivotY": .56, "ahogePivotX": .5, "ahogePivotY": .14}


def inspect(folder):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("skin directory missing or is a symlink")
    manifest = folder / "skin.json"
    if manifest.is_symlink() or not manifest.is_file() or not 0 < manifest.stat().st_size <= 16384:
        raise ValueError("skin.json missing, linked, empty, or over 16 KiB")
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] not in (1, 2):
        raise ValueError("version must be 1 or 2")
    name = data.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.encode("utf-16-le")) // 2 > 40:
        raise ValueError("name must be nonempty and at most 40 UTF-16 units")
    for key in PIVOTS:
        value = data.get(key, PIVOTS[key])
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"invalid pivot {key}")
    size = None
    images = []
    warnings = []
    for name in V2 if data["version"] == 2 else V1:
        file = folder / name
        if file.is_symlink() or not file.is_file() or not 0 < file.stat().st_size <= 8 * 1024 * 1024:
            raise ValueError(f"{name}: missing, linked, empty, or over 8 MiB")
        with Image.open(file) as img:
            if img.format != "PNG":
                raise ValueError(f"{name}: expected PNG")
            if not (64 <= img.width <= 2048 and 64 <= img.height <= 2048):
                raise ValueError(f"{name}: dimensions must be 64–2048")
            if size is not None and img.size != size:
                raise ValueError(f"{name}: canvas dimensions differ")
            size = img.size
            rgba = img.convert("RGBA")
            extrema = rgba.getchannel("A").getextrema()
            if extrema == (0, 0):
                warnings.append(f"{name}: fully transparent")
            elif extrema == (255, 255):
                warnings.append(f"{name}: fully opaque")
            images.append(rgba)
    return data, size, images, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("folder", type=Path)
    validate.add_argument("--preview", type=Path, help="new static composite PNG outside the skin directory")
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--layers", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--name", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("output already exists")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".netpet-skin-", dir=args.output.parent) as temp:
                draft = Path(temp) / "skin"
                draft.mkdir()
                for name in V2:
                    source = args.layers / name
                    if source.is_symlink() or not source.is_file():
                        raise ValueError(f"{name}: missing or linked source")
                    shutil.copyfile(source, draft / name)
                (draft / "skin.json").write_text(json.dumps({"version": 2, "name": args.name, **PIVOTS}, ensure_ascii=False, indent=2), encoding="utf-8")
                inspect(draft)
                os.rename(draft, args.output)
            folder = args.output
        else:
            folder = args.folder
        data, size, layers, warnings = inspect(folder)
        if args.command == "validate" and args.preview:
            preview = args.preview.resolve()
            if preview == folder.resolve() or folder.resolve() in preview.parents:
                raise ValueError("preview must be outside the skin directory")
            composite = Image.new("RGBA", size)
            for layer in layers:
                composite.alpha_composite(layer)
            with open(preview, "xb") as output:
                composite.save(output, format="PNG")
        print(json.dumps({"ok": True, "name": data["name"], "version": data["version"], "size": size, "warnings": warnings}, ensure_ascii=False))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"skin error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
