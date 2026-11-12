---
name: skill233-net-pet-ugc
description: Create, check, preview, and import local layered Net Pet character skins. Use for Net Pet UGC creation or adaptation, not general image editing.
---

# Net Pet UGC

Create a character from permitted artwork or produce original artwork with the available image tools. Establish the requested appearance and use independently painted layers on one shared transparent canvas. Repair overlaps at shoulders and neck; do not imply that slicing a flat picture produces a production-ready rig. Confirm the composite and movement visually. The runtime performs small rigid rotations, not skeletal animation.

For a new six-layer skin, supply aligned `hair.png`, `body.png`, `left.png`, `right.png`, `head.png`, `ahoge.png` and `skin.json`. Read [the format and workflow](references/format.md) for the schema, layer order, pivots, practical checks, and v1 compatibility. Use `scripts/skin_tool.py` to prepare a new package from independently drawn PNGs, validate it, and generate a static composite. This script needs Python 3 and Pillow; if unavailable, tell the user how to install Pillow or use an equivalent tool. Never represent its static preview as motion validation.

```powershell
python <skill>/scripts/skin_tool.py prepare --layers <layer-directory> --output <new-directory> --name "伙伴"
python <skill>/scripts/skin_tool.py validate <new-directory> --preview <preview.png>
```

Adjust pivots in `skin.json` to the actual artwork, revalidate, inspect the composite, and test movement in Net Pet where available. Preserve source layers. A successful format check does not establish visual quality or rights to the art. Deliver the folder and preview; clearly report any untested motion or import.

`assets/example-skin/`, `assets/sunny/`, and `assets/starlight/` are original six-layer examples that can be validated or imported directly. The desktop editor also contains these examples; open “示例作品”, choose one, adjust it, and save a new work. They demonstrate alignment and pivots; tailor artwork and joints to the user's character rather than presenting an example as their custom design.

In the desktop library, select a work and open “管理作品” to edit it, export it to a new directory, or move it to the recoverable archive. Saving an edit preserves the active entry and archives its previous revision. The archive can restore or export works; restoring to a full library may retire its oldest active work. Existing v1 four-layer works remain v1 when edited because their face is painted into the body. Exported folders contain `skin.json` and all required PNGs and can be imported again.

When the user requests import, run the installed application's `tools/ugc/import-skin.ps1` with PowerShell 7 and `-Manifest <absolute path to skin.json>` while Net Pet is running normally. Locate the actual installation folder; do not assume a user-data path. Successful import equips the skin and the local ten-slot library moves the oldest entry into `_retired` if full. On timeout, inspect the printed request ID and result file before retrying. This is local UGC, not online publishing or Steam Workshop.
