#!/usr/bin/env python3
"""Prepare and inspect a Net Pet layered skin; never alter source artwork."""
import argparse
import json
import unicodedata
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: python -m pip install Pillow")

V1 = ("hair.png", "body.png", "left.png", "right.png")
V2 = V1 + ("head.png", "ahoge.png")
EXTRAS = {"tail": "tail.png", "wings": "wings.png", "accessory": "accessory.png", "leftPressed": "left-pressed.png", "rightPressed": "right-pressed.png"}
PIVOTS = {"leftPivotX": .32, "rightPivotX": .68, "armPivotY": .68,
          "rightArmPivotY": .68, "hairPivotX": .5, "hairPivotY": .22,
          "headPivotX": .5, "headPivotY": .56, "ahogePivotX": .5, "ahogePivotY": .14}
EXTRA_PIVOTS = {"tailPivotX": .5, "tailPivotY": .75, "wingsPivotX": .5,
                "wingsPivotY": .55, "accessoryPivotX": .5, "accessoryPivotY": .5}


def inspect(folder):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("skin directory missing or is a symlink")
    manifest = folder / "skin.json"
    if manifest.is_symlink() or not manifest.is_file() or not 0 < manifest.stat().st_size <= 16384:
        raise ValueError("skin.json missing, linked, empty, or over 16 KiB")
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] not in (1, 2, 3):
        raise ValueError("version must be 1, 2 or 3")
    name = data.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.encode("utf-16-le")) // 2 > 40:
        raise ValueError("name must be nonempty and at most 40 UTF-16 units")
    if "armsInFront" in data and type(data["armsInFront"]) is not bool:
        raise ValueError("armsInFront must be a boolean")
    character, series = data.get("characterId"), data.get("seriesId")
    if character not in (None, "") or series not in (None, ""):
        for value in (character, series):
            if (not isinstance(value, str) or not value.strip() or value != value.strip()
                    or len(value.encode("utf-16-le")) // 2 > 40
                    or any(unicodedata.category(c) == "Cc" for c in value)):
                raise ValueError("characterId and seriesId must both be valid identifiers")
    for key, default in {**PIVOTS, **EXTRA_PIVOTS}.items():
        value = data.get(key, default)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"invalid pivot {key}")
    size = None
    images = []
    warnings = []
    names = V1 if data["version"] == 1 else V2
    if data["version"] == 3:
        for flag, file in EXTRAS.items():
            if flag in data and type(data[flag]) is not bool:
                raise ValueError(f"{flag} must be a boolean")
            if data.get(flag, False): names += (file,)
    for name in names:
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
    validate.add_argument("--pose", choices=("neutral", "left-pressed", "right-pressed", "both-pressed"), default="neutral", help="static hand pose for the preview")
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--layers", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--name", required=True)
    prepare.add_argument("--arms-in-front", action="store_true", help="draw arms in front of the head")
    share = sub.add_parser("share")
    share.add_argument("folder", type=Path)
    share.add_argument("--output", type=Path, required=True, help="new ZIP outside the skin directory")
    args = parser.parse_args()
    try:
        if args.command == "share":
            source, target = args.folder, args.output.absolute()
            if source.is_symlink() or not source.is_dir():
                raise ValueError("skin directory missing or is a symlink")
            if target.suffix.lower() != ".zip" or target.exists() or target.is_symlink() or not target.parent.is_dir() or target.parent.is_symlink():
                raise ValueError("output must be a new ZIP in an existing non-linked directory")
            if source.resolve() in target.resolve().parents:
                raise ValueError("output must be outside the skin directory")
            with tempfile.TemporaryDirectory(prefix=".netpet-share-", dir=target.parent) as temp:
                draft = Path(temp) / "skin"
                draft.mkdir()
                manifest_path = source / "skin.json"
                if manifest_path.is_symlink() or not manifest_path.is_file() or not 0 < manifest_path.stat().st_size <= 16384:
                    raise ValueError("skin.json missing, linked, empty, or over 16 KiB")
                raw = manifest_path.read_bytes()
                data = json.loads(raw.decode("utf-8-sig"))
                if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] not in (1, 2, 3):
                    raise ValueError("version must be 1, 2 or 3")
                names = list(V1 if data["version"] == 1 else V2)
                if data["version"] == 3:
                    names.extend(file for flag, file in EXTRAS.items() if data.get(flag, False))
                (draft / "skin.json").write_bytes(raw)
                for name in names:
                    path = source / name
                    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 8 * 1024 * 1024:
                        raise ValueError(f"{name}: missing, linked, empty, or over 8 MiB")
                    shutil.copyfile(path, draft / name)
                data, size, _, warnings = inspect(draft)
                temporary = Path(temp) / "share.tmp"
                with zipfile.ZipFile(temporary, "x", compression=zipfile.ZIP_DEFLATED) as archive:
                    for name in ["skin.json", *names]:
                        archive.write(draft / name, name)
                # Hard-link publication is atomic and never replaces an existing file.
                os.link(temporary, target)
            print(json.dumps({"ok": True, "name": data["name"], "version": data["version"], "zip": str(target), "size": size, "warnings": warnings}, ensure_ascii=False))
            return 0
        if args.command == "prepare":
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("output already exists")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".netpet-skin-", dir=args.output.parent) as temp:
                draft = Path(temp) / "skin"
                draft.mkdir()
                for name in V2:
                    source = args.layers / name
                    if source.is_symlink() or not source.is_file() or not 0 < source.stat().st_size <= 8 * 1024 * 1024:
                        raise ValueError(f"{name}: missing, linked, empty, or over 8 MiB")
                    shutil.copyfile(source, draft / name)
                enabled = {}
                for flag, name in EXTRAS.items():
                    source = args.layers / name
                    if source.is_symlink():
                        raise ValueError(f"{name}: linked source")
                    if source.exists():
                        if not source.is_file() or not 0 < source.stat().st_size <= 8 * 1024 * 1024:
                            raise ValueError(f"{name}: expected a nonempty file up to 8 MiB")
                        shutil.copyfile(source, draft / name)
                        enabled[flag] = True
                manifest = {"version": 3 if enabled else 2, "name": args.name, **PIVOTS, **enabled}
                if args.arms_in_front: manifest["armsInFront"] = True
                (draft / "skin.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
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
            names = list(V1 if data['version'] == 1 else V2)
            if data['version'] == 3: names += [file for flag, file in EXTRAS.items() if data.get(flag, False)]
            indexed = dict(zip(names, layers))
            order = ('tail.png','wings.png','hair.png','body.png','head.png','ahoge.png','left.png','right.png','accessory.png') if data.get('armsInFront', False) else ('tail.png','wings.png',*V1,'head.png','ahoge.png','accessory.png')
            for name in order:
                if name == 'left.png' and args.pose in ('left-pressed', 'both-pressed') and 'left-pressed.png' in indexed:
                    name = 'left-pressed.png'
                elif name == 'right.png' and args.pose in ('right-pressed', 'both-pressed') and 'right-pressed.png' in indexed:
                    name = 'right-pressed.png'
                if name in indexed: composite.alpha_composite(indexed[name])
            with open(preview, "xb") as output:
                composite.save(output, format="PNG")
        print(json.dumps({"ok": True, "name": data["name"], "version": data["version"], "size": size, "warnings": warnings}, ensure_ascii=False))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"skin error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
