import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import os
import shutil

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

    def test_press_poses_match_hand_layer_order_and_fall_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'skin'
            root.mkdir()
            for name in FILES:
                Image.new('RGBA', (64, 64), (0, 0, 0, 0)).save(root / name)
            for name, color, box in (
                ('left.png', 'green', (0, 0, 31, 63)),
                ('right.png', 'yellow', (32, 0, 63, 63)),
                ('left-pressed.png', 'blue', (0, 0, 31, 63)),
                ('right-pressed.png', 'magenta', (32, 0, 63, 63)),
                # The head must remain above either hand pose.
                ('head.png', 'red', (12, 12, 20, 20)),
            ):
                image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                from PIL import ImageDraw
                ImageDraw.Draw(image).rectangle(box, fill=color)
                image.save(root / name)
            manifest = {'version': 3, 'name': 'poses', 'leftPressed': True, 'rightPressed': True}
            (root / 'skin.json').write_text(json.dumps(manifest), encoding='utf-8')
            expected = {
                'neutral': ((0,128,0,255), (255,255,0,255)),
                'left-pressed': ((0,0,255,255), (255,255,0,255)),
                'right-pressed': ((0,128,0,255), (255,0,255,255)),
                'both-pressed': ((0,0,255,255), (255,0,255,255)),
            }
            ps_names = {'neutral':'Neutral','left-pressed':'LeftPressed','right-pressed':'RightPressed','both-pressed':'BothPressed'}
            pwsh = shutil.which('pwsh') or (str(Path.home() / '.dotnet/tools/pwsh.exe') if os.name == 'nt' else None)
            for pose, colors in expected.items():
                preview = Path(tmp) / (pose + '-python.png')
                result = self.run_tool('validate', root, '--preview', preview, '--pose', pose)
                self.assertEqual(result.returncode, 0, result.stderr)
                with Image.open(preview) as image:
                    self.assertEqual((image.getpixel((8, 32)), image.getpixel((48, 32))), colors)
                    self.assertEqual(image.getpixel((16, 16)), (255,0,0,255))
                if pwsh and os.name == 'nt':
                    ps_preview = Path(tmp) / (pose + '-powershell.png')
                    result = subprocess.run([pwsh, '-NoProfile', '-File', str(TOOL.with_suffix('.ps1')), '-Action', 'Validate', '-Folder', str(root), '-Preview', str(ps_preview), '-Pose', ps_names[pose]], capture_output=True, text=True, encoding='utf-8')
                    self.assertEqual(result.returncode, 0, result.stderr)
                    with Image.open(ps_preview) as image:
                        self.assertEqual((image.getpixel((8, 32)), image.getpixel((48, 32))), colors)
                        self.assertEqual(image.getpixel((16, 16)), (255,0,0,255))
            manifest['leftPressed'] = False
            (root / 'skin.json').write_text(json.dumps(manifest), encoding='utf-8')
            preview = Path(tmp) / 'fallback.png'
            self.assertEqual(self.run_tool('validate', root, '--preview', preview, '--pose', 'both-pressed').returncode, 0)
            with Image.open(preview) as image: self.assertEqual(image.getpixel((8,32)), (0,128,0,255))
            if pwsh and os.name == 'nt':
                ps_preview = Path(tmp) / 'fallback-powershell.png'
                result = subprocess.run([pwsh, '-NoProfile', '-File', str(TOOL.with_suffix('.ps1')), '-Action', 'Validate', '-Folder', str(root), '-Preview', str(ps_preview), '-Pose', 'BothPressed'], capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stderr)
                with Image.open(ps_preview) as image: self.assertEqual(image.getpixel((8,32)), (0,128,0,255))

    def test_extra_pivots_are_checked_for_every_manifest_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in FILES:
                Image.new('RGBA', (64, 64)).save(root / name)
            pwsh = shutil.which('pwsh') or (str(Path.home() / '.dotnet/tools/pwsh.exe') if os.name == 'nt' else None)
            for version in (1, 2, 3):
                (root / 'skin.json').write_text(json.dumps({'version':version,'name':'OC','tailPivotX':2}), encoding='utf-8')
                self.assertNotEqual(self.run_tool('validate', root).returncode, 0)
                if pwsh and os.name == 'nt':
                    result = subprocess.run([pwsh, '-NoProfile', '-File', str(TOOL.with_suffix('.ps1')), '-Action', 'Validate', '-Folder', str(root)], capture_output=True, text=True, encoding='utf-8')
                    self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
