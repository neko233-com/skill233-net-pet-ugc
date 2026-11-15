import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "skin_tool.py"
FILES = ("hair.png", "body.png", "left.png", "right.png", "head.png", "ahoge.png")


class SkinToolTest(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, encoding="utf-8")

    def test_prepare_validate_and_reject_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layers = root / "layers"
            layers.mkdir()
            for name in FILES:
                Image.new("RGBA", (64, 80), (0, 0, 0, 0)).save(layers / name)
            target = root / "作品"
            result = self.run_tool("prepare", "--layers", layers, "--output", target, "--name", "测试")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["size"], [64, 80])
            preview = root / "preview.png"
            result = self.run_tool("validate", target, "--preview", preview)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(preview.is_file())
            self.assertNotEqual(self.run_tool("validate", target, "--preview", target / "body.png").returncode, 0)
            self.assertNotEqual(self.run_tool("prepare", "--layers", layers, "--output", target, "--name", "x").returncode, 0)
            manifest = json.loads((target / "skin.json").read_text(encoding="utf-8"))
            manifest["leftPivotX"] = 2
            (target / "skin.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertNotEqual(self.run_tool("validate", target).returncode, 0)
            manifest["leftPivotX"] = .3
            (target / "skin.json").write_text(json.dumps(manifest), encoding="utf-8")
            Image.new("RGBA", (65, 80)).save(target / "left.png")
            self.assertNotEqual(self.run_tool("validate", target).returncode, 0)

    def test_version_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in FILES[:4]:
                Image.new("RGBA", (64, 64), (30, 40, 50, 128)).save(root / name)
            (root / "skin.json").write_text('{"version":1,"name":"old"}', encoding="utf-8")
            result = self.run_tool("validate", root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["version"], 1)

    def test_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in FILES[:4]:
                Image.new("RGBA", (64, 64), (30, 40, 50, 128)).save(root / name)
            path = root / "skin.json"
            manifest = {"version": 1, "name": "OC", "characterId": "oc-moon", "seriesId": "winter-collection"}
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(self.run_tool("validate", root).returncode, 0)
            for bad in (None, " bad", "bad\nseries", "x" * 41):
                manifest["seriesId"] = bad
                path.write_text(json.dumps(manifest), encoding="utf-8")
                self.assertNotEqual(self.run_tool("validate", root).returncode, 0)

    def test_shipped_examples(self):
        assets = TOOL.parents[1] / "assets"
        for name in ("example-skin", "sunny", "starlight"):
            result = self.run_tool("validate", assets / name)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["version"], 2)

    def test_extended_layers_and_pressed_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in FILES:
                Image.new('RGBA', (64, 64), (0, 0, 0, 0)).save(root / name)
            Image.new('RGBA', (64, 64), (255, 0, 0, 255)).save(root / 'body.png')
            Image.new('RGBA', (64, 64), (0, 255, 0, 255)).save(root / 'tail.png')
            Image.new('RGBA', (64, 64), (0, 0, 255, 255)).save(root / 'left-pressed.png')
            (root / 'skin.json').write_text(json.dumps({'version':3,'name':'extended','tail':True,'leftPressed':True}), encoding='utf-8')
            preview = root.parent / (root.name + '-preview.png')
            result = self.run_tool('validate', root, '--preview', preview)
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(preview) as image: self.assertEqual(image.getpixel((32,32)), (255,0,0,255))
            preview.unlink()
            (root / 'tail.png').unlink()
            self.assertNotEqual(self.run_tool('validate', root).returncode, 0)


if __name__ == "__main__":
    unittest.main()
