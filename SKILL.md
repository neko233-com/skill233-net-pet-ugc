---
name: skill233-net-pet-ugc
description: Create, validate, and import local layered character skins for the Net Pet desktop pet. Use when a user wants to make or adapt a Net Pet UGC skin.
---

# Net Pet UGC skins

Create a local layered skin from artwork the user may use. Establish the character, intended appearance, and available source images; use appropriate image-generation or art tools when creation is requested. Keep layers aligned on one transparent canvas and visually inspect the composite and joints. Do not claim that a flattened character has automatically become a clean rig: shoulders need overlap and reconstruction, not rectangular crops.

The current Net Pet implementation uses version 2 `skin.json` plus `hair.png`, `body.png`, `left.png`, `right.png`, `head.png`, and `ahoge.png`. Every PNG must have the same dimensions, each side 64–2048 pixels, and each file at most 8 MiB. Hair sits behind the body; body excludes head, arms, and ahoge. Layer rotation is rigid and subtle, not skeletal animation. The manifest is UTF-8, at most 16 KiB; `name` must be nonempty and at most 40 characters. Pivot coordinates are finite numbers in [0,1], normalized from the top-left of the canvas. Adapt pivots to the actual artwork:

```json
{"version":2,"name":"My companion","leftPivotX":0.32,"armPivotY":0.68,"rightPivotX":0.68,"rightArmPivotY":0.68,"hairPivotX":0.5,"hairPivotY":0.22,"headPivotX":0.5,"headPivotY":0.56,"ahogePivotX":0.5,"ahogePivotY":0.14}
```

Version 1 accepts only hair, body, left and right, with head on the body and a shared armPivotY. Prefer version 2 for new work. Before delivery inspect all layers, canvas dimensions, alignment, transparency and the composite; verify the app's current documentation and implementation if available, since this feature may change. Test motion in the application when possible; report if unavailable.

For local import, run the installed `tools/ugc/import-skin.ps1` with PowerShell 7 and `-Manifest <absolute path to skin.json>` while Net Pet is running normally. Find the actual installation directory rather than assuming it. The importer writes a local request and awaits a result; on timeout inspect the reported request ID and result before retrying. Import changes the local library, whose ten-item limit retires the oldest entry on a successful import; preserve source artwork. Alternatively deliver the folder for manual import. This is local UGC, not Steam Workshop or online publishing.
