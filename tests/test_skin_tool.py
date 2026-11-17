import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import os
import shutil
import zipfile
import importlib.util
from types import SimpleNamespace
from unittest import mock

from PIL import Image

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "skin_tool.py"
FILES = ("hair.png", "body.png", "left.png", "right.png", "head.png", "ahoge.png")


class SkinToolTest(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, encoding="utf-8")

    def test_bom_and_integral_decimal_version_match_both_tools(self):
        pwsh = shutil.which('pwsh') or (str(Path.home() / '.dotnet/tools/pwsh.exe') if os.name == 'nt' else None)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skin = root / 'skin'
            skin.mkdir()
            for name in FILES:
                Image.new('RGBA', (64, 80), (0, 0, 0, 0)).save(skin / name)
            raw = b'\xef\xbb\xbf' + '{"version":2.0,"name":"作品"}'.encode('utf-8')
            (skin / 'skin.json').write_bytes(raw)
            runners = [False, True] if pwsh and os.name == 'nt' else [False]
            for powershell in runners:
                if powershell:
                    validate = subprocess.run([pwsh, '-NoProfile', '-File', str(TOOL.with_suffix('.ps1')), '-Action', 'Validate', '-Folder', str(skin)], capture_output=True, text=True, encoding='utf-8')
                    output = root / 'ps.zip'
                    share = subprocess.run([pwsh, '-NoProfile', '-File', str(TOOL.with_suffix('.ps1')), '-Action', 'Share', '-Folder', str(skin), '-Output', str(output)], capture_output=True, text=True, encoding='utf-8')
                else:
                    validate = self.run_tool('validate', skin)
                    output = root / 'py.zip'
                    share = self.run_tool('share', skin, '--output', output)
                self.assertEqual(validate.returncode, 0, validate.stderr)
                self.assertEqual(share.returncode, 0, share.stderr)
                with zipfile.ZipFile(output) as archive:
                    self.assertEqual(archive.read('skin.json'), raw)
            for value in ('2.5', 'true', '1e999'):
                (skin / 'skin.json').write_text('{"version":' + value + ',"name":"x"}', encoding='utf-8')
                self.assertNotEqual(self.run_tool('validate', skin).returncode, 0)
                if pwsh and os.name == 'nt':
                    invalid = subprocess.run([pwsh, '-NoProfile', '-File', str(TOOL.with_suffix('.ps1')), '-Action', 'Validate', '-Folder', str(skin)], capture_output=True, text=True, encoding='utf-8')
                    self.assertNotEqual(invalid.returncode, 0)

    def test_limited_read_rejects_growth_after_size_check(self):
        spec = importlib.util.spec_from_file_location("skin_tool_under_test", TOOL)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "growing.png"
            source.write_bytes(b"x" * 2048)
            actual = os.stat(source)
            stale = SimpleNamespace(st_mode=actual.st_mode, st_size=16,
                                    st_file_attributes=getattr(actual, "st_file_attributes", 0))
            with mock.patch.object(module.os, "fstat", return_value=stale):
                with self.assertRaisesRegex(ValueError, "changed while reading"):
                    module.read_limited(source, 1024)

    def test_share_all_versions_and_reject_invalid_or_existing_output(self):
        extras = ('tail.png', 'wings.png', 'accessory.png', 'left-pressed.png', 'right-pressed.png')
        pwsh = shutil.which('pwsh') or (str(Path.home() / '.dotnet/tools/pwsh.exe') if os.name == 'nt' else None)
        def share(folder, output, powershell):
            if powershell:
                return subprocess.run([pwsh, '-NoProfile', '-File', str(TOOL.with_suffix('.ps1')), '-Action', 'Share', '-Folder', str(folder), '-Output', str(output)], capture_output=True, text=True, encoding='utf-8')
            return self.run_tool('share', folder, '--output', output)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for version in (1, 2, 3):
                folder = root / f'skin-{version}'
                folder.mkdir()
                for index, name in enumerate((*FILES, *extras)):
                    Image.new('RGBA', (64, 80), (index, 40, 50, 128)).save(folder / name)
                manifest = {'version': version, 'name': '作品'}
                if version == 3:
                    manifest.update(tail=True, wings=True, accessory=True, leftPressed=True, rightPressed=True)
                (folder / 'skin.json').write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
                (folder / 'private-note.txt').write_text('do not share', encoding='utf-8')
                before = {p.name: p.read_bytes() for p in folder.iterdir()}
                expected = {'skin.json', *(FILES[:4] if version == 1 else FILES), *(extras if version == 3 else ())}
                for powershell in ([False, True] if pwsh and os.name == 'nt' else [False]):
                    label = 'ps' if powershell else 'py'
                    output = root / f'{version}-{label}.zip'
                    result = share(folder, output, powershell)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    with zipfile.ZipFile(output) as archive:
                        self.assertEqual(set(archive.namelist()), expected)
                        self.assertEqual(len(archive.namelist()), len(expected))
                        for name in expected:
                            self.assertEqual(archive.read(name), before[name])
                    original = output.read_bytes()
                    self.assertNotEqual(share(folder, output, powershell).returncode, 0)
                    self.assertEqual(output.read_bytes(), original)
                    self.assertNotEqual(share(folder, folder / 'inside.zip', powershell).returncode, 0)
                    self.assertFalse((folder / 'inside.zip').exists())
                self.assertEqual({p.name: p.read_bytes() for p in folder.iterdir()}, before)
            (folder / 'left.png').write_bytes(b'invalid image')
            for powershell in ([False, True] if pwsh and os.name == 'nt' else [False]):
                output = root / ('bad-ps.zip' if powershell else 'bad-py.zip')
                self.assertNotEqual(share(folder, output, powershell).returncode, 0)
                self.assertFalse(output.exists())
            self.assertFalse(list(root.glob('.netpet-share-*')))

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

    def test_prepare_preserves_optional_layers_without_touching_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            layers = root / 'layers'
            layers.mkdir()
            for name in (*FILES, 'tail.png', 'right-pressed.png'):
                Image.new('RGBA', (64, 64), (50, 80, 120, 128)).save(layers / name)
            source_files = {p.name: p.read_bytes() for p in layers.iterdir()}
            commands = [('python', None)]
            pwsh = shutil.which('pwsh') or (str(Path.home() / '.dotnet/tools/pwsh.exe') if os.name == 'nt' else None)
            if pwsh and os.name == 'nt': commands.append(('powershell', pwsh))
            for label, executable in commands:
                target = root / label
                if executable:
                    result = subprocess.run([executable, '-NoProfile', '-File', str(TOOL.with_suffix('.ps1')), '-Action', 'Prepare', '-Layers', str(layers), '-Output', str(target), '-Name', 'OC'], capture_output=True, text=True, encoding='utf-8')
                else:
                    result = self.run_tool('prepare', '--layers', layers, '--output', target, '--name', 'OC')
                self.assertEqual(result.returncode, 0, result.stderr)
                manifest = json.loads((target / 'skin.json').read_text(encoding='utf-8-sig'))
                self.assertEqual(manifest['version'], 3)
                self.assertTrue(manifest['tail'])
                self.assertTrue(manifest['rightPressed'])
                self.assertNotIn('wings', manifest)
                for name, contents in source_files.items(): self.assertEqual((target / name).read_bytes(), contents)
                self.assertEqual(self.run_tool('validate', target).returncode, 0)
            self.assertEqual({p.name: p.read_bytes() for p in layers.iterdir()}, source_files)
            (layers / 'wings.png').write_bytes(b'invalid')
            for label, executable in commands:
                target = root / ('invalid-' + label)
                if executable:
                    result = subprocess.run([executable, '-NoProfile', '-File', str(TOOL.with_suffix('.ps1')), '-Action', 'Prepare', '-Layers', str(layers), '-Output', str(target), '-Name', 'OC'], capture_output=True, text=True, encoding='utf-8')
                else:
                    result = self.run_tool('prepare', '--layers', layers, '--output', target, '--name', 'OC')
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(target.exists())

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
