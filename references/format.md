# Layered skin format

All PNG files use the same 64–2048 pixel canvas, share exactly the same dimensions, and are at most 8 MiB each. Use transparency around each part. Composite order is hair, body, left arm, right arm, head, ahoge. Body excludes head and arms in v2; paint hidden shoulder/neck areas to avoid gaps during rotations. Left and right mean the named image files and pivot assignments, so check the actual appearance rather than assuming screen versus character handedness.

The UTF-8 `skin.json` is at most 16 KiB. Name is nonblank and at most 40 UTF-16 code units. Pivots are finite normalized coordinates in [0,1], measured from the canvas top-left. These values are starting points only:

Optional `characterId` and `seriesId` identify an OC and its collection. Supply both together, or omit both for an unclassified legacy work. Each is a nonblank, trimmed string of at most 40 UTF-16 units without control characters. Keep these identifiers stable across variants and shared ZIPs. In the desktop editor, open “角色与系列” to set or clear them. The library groups works by character and then series; legacy works appear under the unclassified group.

```json
{"version":2,"name":"我的伙伴","leftPivotX":0.32,"armPivotY":0.68,"rightPivotX":0.68,"rightArmPivotY":0.68,"hairPivotX":0.5,"hairPivotY":0.22,"headPivotX":0.5,"headPivotY":0.56,"ahogePivotX":0.5,"ahogePivotY":0.14}
```

Version 1 has `hair.png`, `body.png`, `left.png`, `right.png`; the head is part of body and both arms use `armPivotY`. Version 2 adds separate head and ahoge and `rightArmPivotY`. Do not blindly turn a v1 package into v2 without reconstructing the overlapping art.

Version 3 keeps all six v2 base images. Optional full-canvas images are enabled individually by boolean fields: `tail` for `tail.png`, `wings` for `wings.png`, `accessory` for `accessory.png`, `leftPressed` for `left-pressed.png`, and `rightPressed` for `right-pressed.png`. Tail and wings are behind the body; accessory is in front. The pressed hands replace their normal counterparts during typing pulses. Optional normalized pivots are `tailPivotX/Y`, `wingsPivotX/Y`, and `accessoryPivotX/Y`. Omit disabled images and flags. Keep all images aligned and visually verify neutral and pressed poses; the runtime performs small rigid transforms rather than arbitrary skeletal animation.

Workflow: establish the design and rights; create or select each independent layer; keep original sources; run `prepare`; tune pivots; run `validate` with a preview outside the package; inspect edges, placement, pose and transparency; import and inspect the animated character if available. A blank or fully opaque layer is a warning, not necessarily an invalid file. The local application verifies decoding again and remains authoritative. Its in-app editor also permits adjusting pivots and saving a draft. Work is local only. Twenty active library entries are retained; successful import can retire the earliest entry to `_retired`.

The three examples in `assets/example-skin`, `assets/sunny`, and `assets/starlight` use the same schema as user works. `scripts/make_demo_art.py` regenerates the latter two from original vector-like drawing primitives in a new output folder. The editor ships authenticated encrypted copies; the submodule provides the editable PNGs to agents.
