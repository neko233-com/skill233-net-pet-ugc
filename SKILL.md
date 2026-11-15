---
name: skill233-net-pet-ugc
description: Create, check, preview, and import local layered dsdoll (formerly Net Pet) character skins. Use for dsdoll UGC creation or adaptation, not general image editing.
---

# Net Pet UGC

The product is now named dsdoll. The skill and repository retain their existing Net Pet identifiers for compatibility.

Create a character from permitted artwork or produce original artwork with the available image tools. Establish the requested appearance and use independently painted layers on one shared transparent canvas. Repair overlaps at shoulders and neck; do not imply that slicing a flat picture produces a production-ready rig. Confirm the composite and movement visually. The runtime performs small rigid rotations, not skeletal animation.

For a new six-layer skin, supply aligned `hair.png`, `body.png`, `left.png`, `right.png`, `head.png`, `ahoge.png` and `skin.json`. Read [the format and workflow](references/format.md) for the schema, layer order, pivots, practical checks, and v1 compatibility. On Windows, the following offline alternative uses PowerShell 7 and Windows .NET image decoding; it does not need Python, Pillow or network access. The output and preview must be new paths and the output's parent must exist. Never represent a static preview as motion validation.

```powershell
pwsh -NoProfile -File <skill>/scripts/skin_tool.ps1 -Action Prepare -Layers <layer-directory> -Output <new-directory> -Name "伙伴"
pwsh -NoProfile -File <skill>/scripts/skin_tool.ps1 -Action Validate -Folder <new-directory> -Preview <new-preview.png>
```

Alternatively, `scripts/skin_tool.py` supports Python 3 with Pillow where those are already installed:

```powershell
python <skill>/scripts/skin_tool.py prepare --layers <layer-directory> --output <new-directory> --name "伙伴"
python <skill>/scripts/skin_tool.py validate <new-directory> --preview <preview.png>
```

Review the Windows tool's warnings for sampled transparency and possible empty layers; sparse samples can miss small details, and intentionally transparent layers are valid. The Python validator inspects the full alpha channel. Adjust pivots in `skin.json` to the actual artwork, revalidate, inspect the composite, and test movement in Net Pet where available. Preserve source layers. A successful format check does not establish visual quality or rights to the art. Deliver the folder and preview; clearly report any untested motion or import.

Version 3 retains the six base layers and supports optional `tail.png`, `wings.png`, `accessory.png`, `left-pressed.png`, and `right-pressed.png`, enabled by boolean manifest fields `tail`, `wings`, `accessory`, `leftPressed`, and `rightPressed`. The first two render behind the body and gently sway; the accessory renders in front. Pressed-hand art replaces the corresponding hand during a typing pulse. Each layer still shares the full transparent canvas; this is a layered rig, not arbitrary bones or a timeline. The editor's “扩展图层” page can add these files. Check both neutral and pressed art for seamless shoulder overlap.

`assets/example-skin/`, `assets/sunny/`, and `assets/starlight/` are original six-layer examples that can be validated or imported directly. The desktop editor also contains these examples; open “示例作品”, choose one, adjust it, and save a new work. They demonstrate alignment and pivots; tailor artwork and joints to the user's character rather than presenting an example as their custom design.

In the desktop library, select a work and open “管理作品” to edit it, export it to a new directory, or move it to the recoverable archive. Saving an edit preserves the active entry and archives its previous revision. The archive can restore or export works; restoring to a full library may retire its oldest active work. Existing v1 four-layer works remain v1 when edited because their face is painted into the body. Exported folders contain `skin.json` and all required PNGs and can be imported again.

For local sharing, the desktop library can save a flat ZIP; the recipient imports the ZIP locally. No upload occurs. To create a share from a validated folder with PowerShell 7, use a new destination and include only the manifest and version-specific PNGs at the ZIP root. Do not extract an untrusted ZIP with general-purpose archive tools; use the application's bounded, validated ZIP importer.

```powershell
$folder = 'D:\作品\皮肤'; $zip = 'D:\作品\分享.zip'
& '<skill>/scripts/skin_tool.ps1' -Action Validate -Folder $folder
if (Test-Path -LiteralPath $zip) { throw 'Destination already exists' }
$manifest = Get-Content -LiteralPath (Join-Path $folder 'skin.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$names = @('skin.json','hair.png','body.png','left.png','right.png')
if ($manifest.version -ge 2) { $names += @('head.png','ahoge.png') }
if ($manifest.version -eq 3) {
    if ($manifest.tail) { $names += 'tail.png' }; if ($manifest.wings) { $names += 'wings.png' }; if ($manifest.accessory) { $names += 'accessory.png' }
    if ($manifest.leftPressed) { $names += 'left-pressed.png' }; if ($manifest.rightPressed) { $names += 'right-pressed.png' }
}
Compress-Archive -LiteralPath @($names | ForEach-Object { Join-Path $folder $_ }) -DestinationPath $zip
```

When the user requests import, run the installed application's `tools/ugc/import-skin.ps1` with PowerShell 7 and `-Manifest <absolute path to skin.json or ZIP>` while Net Pet is running normally. Locate the actual installation folder; do not assume a user-data path. Successful import equips the skin and the local ten-slot library moves the oldest entry into `_retired` if full. On timeout, inspect the printed request ID and result file before retrying. This is local UGC, not online publishing or Steam Workshop.

When explicitly asked to animate the running local pet, the installed client also accepts `-Action Typing -Count 4` (1–8). This sends no OS keystrokes and gives no currency; it respects the user's animation setting. Preview mode does not process requests. An acknowledgement means accepted, not that the animation has finished.
