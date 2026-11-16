#Requires -Version 7.0
<# Build a local, data-only dsdoll character ZIP from validated skin folders. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Name,
    [Parameter(Mandatory)][string]$Output,
    [string]$CharacterId,
    [string]$Description = '',
    [string]$ClickLine = '',
    [string]$IdleLine = '',
    [string[]]$Skins = @(),
    [int]$SelectedIndex = 0
)
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This tool requires Windows and PowerShell 7.' }
function Check-Text([string]$Value, [int]$Limit, [bool]$Required) {
    if ($null -eq $Value -or $Value.Length -gt $Limit -or ($Required -and ([string]::IsNullOrWhiteSpace($Value) -or $Value -cne $Value.Trim()))) { throw 'Invalid character text.' }
    foreach ($character in $Value.ToCharArray()) { if ([char]::IsControl($character)) { throw 'Character text must not contain control characters.' } }
    [void][Text.UTF8Encoding]::new($false, $true).GetByteCount($Value)
}
Check-Text $Name 40 $true; Check-Text $Description 240 $false; Check-Text $ClickLine 80 $false; Check-Text $IdleLine 80 $false
if (-not $CharacterId) { $CharacterId = [guid]::NewGuid().ToString('N') }
if ($CharacterId -cnotmatch '^[0-9a-f]{32}$') { throw 'CharacterId must be 32 lowercase hexadecimal characters.' }
if ($Skins.Count -gt 20) { throw 'A character package may contain at most 20 active skins.' }
if ($Skins.Count -eq 0) { $SelectedIndex = -1 }
elseif ($SelectedIndex -lt 0 -or $SelectedIndex -ge $Skins.Count) { throw 'SelectedIndex is outside the supplied skin list.' }
$target = [IO.Path]::GetFullPath($Output)
$parent = [IO.Path]::GetDirectoryName($target)
if (-not $parent -or -not [IO.Directory]::Exists($parent) -or [IO.File]::Exists($target) -or [IO.Directory]::Exists($target)) { throw 'Output must be a new file in an existing directory.' }
if ((Get-Item -LiteralPath $parent -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Output parent cannot be a link.' }
$skinFolders = @()
foreach ($skin in $Skins) {
    $folder = (Resolve-Path -LiteralPath $skin -ErrorAction Stop).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
    $item = Get-Item -LiteralPath $folder -Force
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Skin folders must be regular directories.' }
    if ($target.StartsWith($folder + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be outside the supplied skin folders.' }
    $skinFolders += $folder
}
$stage = Join-Path $parent ('.diy-character-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($stage)
try {
    $nested = @(); $expanded = 0L
    for ($index = 0; $index -lt $skinFolders.Count; $index++) {
        $path = Join-Path $stage ('skin-{0:D2}.zip' -f $index)
        & (Join-Path $PSScriptRoot 'skin_tool.ps1') -Action Share -Folder $skinFolders[$index] -Output $path | Out-Null
        $reader = [IO.Compression.ZipFile]::OpenRead($path)
        try { foreach ($entry in $reader.Entries) { $expanded += $entry.Length; if ($expanded -gt 256MB) { throw 'Character package expands beyond 256 MiB.' } } }
        finally { $reader.Dispose() }
        $nested += $path
    }
    $manifest = [ordered]@{ version=1; skinCount=$nested.Count; selectedIndex=$SelectedIndex; id=$CharacterId; name=$Name; description=$Description; clickLine=$ClickLine; idleLine=$IdleLine }
    $temporary = Join-Path $stage 'character.zip'
    $stream = [IO.File]::Open($temporary, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $archive = [IO.Compression.ZipArchive]::new($stream, [IO.Compression.ZipArchiveMode]::Create, $true)
        try {
            $entry = $archive.CreateEntry('character.json')
            $writer = [IO.StreamWriter]::new($entry.Open(), [Text.UTF8Encoding]::new($false))
            try { $writer.Write(($manifest | ConvertTo-Json -Compress)) } finally { $writer.Dispose() }
            for ($index = 0; $index -lt $nested.Count; $index++) {
                [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $nested[$index], ('skins/{0:D2}.zip' -f $index), [IO.Compression.CompressionLevel]::NoCompression)
            }
        } finally { $archive.Dispose() }
    } finally { $stream.Dispose() }
    if ((Get-Item -LiteralPath $temporary).Length -gt 256MB) { throw 'Character package exceeds 256 MiB.' }
    [IO.File]::Move($temporary, $target)
    [ordered]@{ ok=$true; characterId=$CharacterId; name=$Name; skins=$nested.Count; output=$target } | ConvertTo-Json -Compress
} finally {
    if ([IO.Directory]::Exists($stage)) {
        $resolved = (Resolve-Path -LiteralPath $stage).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
        if (-not [string]::Equals([IO.Path]::GetDirectoryName($resolved), $parent, [StringComparison]::OrdinalIgnoreCase) -or -not [IO.Path]::GetFileName($resolved).StartsWith('.diy-character-')) { throw 'Unsafe staging path; it was preserved.' }
        foreach ($item in Get-ChildItem -LiteralPath $resolved -Force) {
            if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or ($item.Name -ne 'character.zip' -and $item.Name -notmatch '^skin-\d{2}\.zip$')) { throw "Unknown staging item was preserved: $($item.FullName)" }
        }
        foreach ($item in Get-ChildItem -LiteralPath $resolved -Force) { Remove-Item -LiteralPath $item.FullName -Force }
        [IO.Directory]::Delete($resolved)
    }
}
