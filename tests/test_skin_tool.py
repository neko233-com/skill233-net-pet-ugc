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


if __name__ == "__main__":
    unittest.main()
