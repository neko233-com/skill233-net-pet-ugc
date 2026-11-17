---
name: skill233-net-pet-ugc
description: Create, check, preview, and locally import dsdoll DIY characters and layered skins. Use for dsdoll UGC creation or adaptation, not general image editing.
---

# Net Pet UGC

The product is now named dsdoll. The skill and repository retain their existing Net Pet identifiers for compatibility.

Create a character from permitted artwork or produce original artwork with the available image tools. Establish the requested appearance and use independently painted layers on one shared transparent canvas. Repair overlaps at shoulders and neck; do not imply that slicing a flat picture produces a production-ready rig. Confirm the composite and movement visually. The runtime performs small rigid rotations, not skeletal animation.

For a new six-layer skin, supply aligned `hair.png`, `body.png`, `left.png`, `right.png`, `head.png`, `ahoge.png` and `skin.json`. Read [the format and workflow](references/format.md) for the schema, layer order, pivots, practical checks, and v1 compatibility. On Windows, the following offline alternative uses PowerShell 7 and Windows .NET image decoding; it does not need Python, Pillow or network access. The output and preview must be new paths and the output's parent must exist. Never represent a static preview as motion validation.

```powershell
pwsh -NoProfile -File <skill>/scripts/skin_tool.ps1 -Action Prepare -Layers <layer-directory> -Output <new-directory> -Name "伙伴"
pwsh -NoProfile -File <skill>/scripts/skin_tool.ps1 -Action Validate -Folder <new-directory> -Preview <new-preview.png>
pwsh -NoProfile -File <skill>/scripts/skin_tool.ps1 -Action Validate -Folder <new-directory> -Preview <new-pressed-preview.png> -Pose BothPressed
```

Alternatively, `scripts/skin_tool.py` supports Python 3 with Pillow where those are already installed:

```powershell
python <skill>/scripts/skin_tool.py prepare --layers <layer-directory> --output <new-directory> --name "伙伴"
python <skill>/scripts/skin_tool.py validate <new-directory> --preview <preview.png>
python <skill>/scripts/skin_tool.py validate <new-directory> --preview <pressed-preview.png> --pose both-pressed
```

Review the Windows tool's warnings for sampled transparency and possible empty layers; sparse samples can miss small details, and intentionally transparent layers are valid. The Python validator inspects the full alpha channel. Adjust pivots in `skin.json` to the actual artwork, revalidate, inspect the composite, and test movement in Net Pet where available. Preserve source layers. A successful format check does not establish visual quality or rights to the art. Deliver the folder and preview; clearly report any untested motion or import.

Both `prepare` commands copy recognized optional v3 PNGs from the layer directory and set the matching flags automatically; with no optional PNGs they create v2. Invalid optional files cause preparation to fail before publishing the output. They do not modify the original artwork.

Version 3 retains the six base layers and supports optional `tail.png`, `wings.png`, `accessory.png`, `left-pressed.png`, and `right-pressed.png`, enabled by boolean manifest fields `tail`, `wings`, `accessory`, `leftPressed`, and `rightPressed`. The first two render behind the body and gently sway; the accessory renders in front. Pressed-hand art blends with the normal hand during a typing pulse. Each layer still shares the full transparent canvas; this is a layered rig, not arbitrary bones or a timeline. The editor's “扩展图层” page can add or remove these files, and its pivot selector adjusts tail, wings and accessory pivots. The PowerShell preview accepts `Neutral`, `LeftPressed`, `RightPressed` and `BothPressed`; the Python equivalents are `neutral`, `left-pressed`, `right-pressed` and `both-pressed`. Missing pressed art falls back to the normal hand. These are static composites without the runtime's rotation; inspect real animation separately. Check both neutral and pressed art for seamless shoulder overlap.

For v2/v3 art whose head covers the hands, set the optional boolean `armsInFront` to `true` or use the editor's hand-layer toggle. `Prepare` can set it with PowerShell `-ArmsInFront` or Python `--arms-in-front`. The validators and static previews use the same layer order. Hands must contain visible, independently separated pixels; a flattened body or empty hand layer cannot be automatically rigged. Check real keyboard and requested Agent typing with animation enabled.

`assets/example-skin/`, `assets/sunny/`, and `assets/starlight/` are original six-layer examples that can be validated or imported directly. The desktop editor also contains these examples; open “示例作品”, choose one, adjust it, and save a new work. They demonstrate alignment and pivots; tailor artwork and joints to the user's character rather than presenting an example as their custom design.

In the desktop library, select a work and open “管理作品” to edit it, export it to a new directory, or move it to the recoverable archive. Saving an edit preserves the active entry and archives its previous revision. The archive can restore or export works; restoring to a full library may retire its oldest active work. Existing v1 four-layer works remain v1 when edited because their face is painted into the body. Exported folders contain `skin.json` and all required PNGs and can be imported again.

For local sharing, the desktop library can save a flat ZIP; the recipient imports the ZIP locally. No upload occurs. The offline share command validates a staged copy and includes only the manifest and declared version-specific PNGs. It requires a new ZIP path outside the work folder, with an existing parent, and never overwrites an existing file. Do not extract an untrusted ZIP with general-purpose archive tools; use the application's bounded, validated ZIP importer.

```powershell
& '<skill>/scripts/skin_tool.ps1' -Action Share -Folder 'D:\作品\皮肤' -Output 'D:\作品\分享.zip'
```

With Python and Pillow installed, the equivalent is `python <skill>/scripts/skin_tool.py share <folder> --output <new.zip>`. It uses a same-volume hard link for atomic no-overwrite publication; a filesystem without hard-link support returns an error without creating the destination.

When the user requests import, run the installed application's `tools/ugc/import-skin.ps1` with PowerShell 7 and `-Manifest <absolute path to skin.json or ZIP>` while Net Pet is running normally. Locate the actual installation folder; do not assume a user-data path. Successful import equips the skin and the local twenty-slot library moves the oldest entry into `_retired` if full. On timeout, inspect the printed request ID and result file before retrying. This is local UGC, not online publishing or Steam Workshop.

For an independent DIY character with its own identity, short click and idle lines, and up to 20 active skins, use [the character package workflow](references/character.md). The desktop's “DIY 角色” tab manages these separately from the legacy skin library. Packages are local ZIP files; creating or importing one never uploads artwork. Character import and activation are separate local Agent actions.

When explicitly asked to animate the running local pet, the installed client also accepts `-Action Typing -Count 4` (1–8). This sends no OS keystrokes and gives no currency; it respects the user's animation setting. Preview mode does not process requests. An acknowledgement means accepted, not that the animation has finished. `unknown` can follow interruption or an exception after dispatch; the action may or may not have started. Check the actual pet before sending a new request and do not retry automatically. The client exits nonzero and identifies the request and receipt in this case.
