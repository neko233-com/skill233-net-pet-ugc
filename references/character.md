# Local DIY characters

A character is an independent local identity with a stable 32-character lowercase hexadecimal ID, name, optional description and optional click and idle lines. Its own skin library uses the existing validated v1–v3 layered skin format. The local profile is encrypted; its manually shared ZIP contains a plaintext profile and the active skins, so do not put secrets in the shared fields. Archived skins and local skin notes are not included in a character ZIP. The recipient must import the ZIP locally. No artwork is automatically uploaded.

With current clients and the updated self-hosted Rust relay, a player's active DIY skin can appear to a peer who independently imports the identical skin or character package. Clients exchange a content fingerprint, not the artwork or character package; character profile text and dialogue are not synchronized. A peer without the matching work sees a built-in avatar and a missing-work notice. Steam carries the fingerprint but has not been verified with real Steam accounts. Do not claim that artworks are automatically uploaded or transferred.

On Windows with PowerShell 7, create a new package from zero to 20 existing skin folders. The output must be a new path outside all source folders; preserve the original artwork.

```powershell
$skill = '<installed skill directory>'
& (Join-Path $skill 'scripts/character_tool.ps1') -Name '月亮伙伴' `
  -Skins @('D:\作品\春装','D:\作品\冬装') -SelectedIndex 0 `
  -ClickLine '你好！' -IdleLine '休息一下吧。' -Output 'D:\作品\月亮伙伴.zip'
```

The command validates each skin with the offline skin tool and prints the character ID. It writes `character.json` plus sequential nested `skins/00.zip`, `skins/01.zip`, etc. The profile's `selectedIndex` is zero-based, or `-1` for a character without skins. The application validates the complete package before publishing it. An existing character ID is not overwritten by a new import; use the in-app editor for changes. Check the resulting character, outfit and animation in the running application; a valid package does not prove visual quality.

When explicitly requested, import and then optionally activate the character through the installed local Agent client:

```powershell
$installDir = (Get-ItemProperty 'HKLM:\Software\Neko233\NetPet').InstallDir
$client = Join-Path $installDir 'tools/ugc/import-skin.ps1'
& $client -Action CharacterImport -Manifest 'D:\作品\月亮伙伴.zip'
& $client -Action CharacterUse -CharacterId '<32-character ID from import receipt>'
```

Character import is idempotent for the same request ID; activation uses an at-most-once marker and may return `unknown` after interruption or an exception after dispatch. In that case inspect the actual desktop pet before sending a new activation request; do not retry automatically. A skin imported while a DIY character is active enters that character's own library; recovery does not re-import or re-equip it and returns `unknown` if the original library or selection changed. Select the original built-in character first to use the legacy library. Do not treat a character ID as a player authentication credential.
