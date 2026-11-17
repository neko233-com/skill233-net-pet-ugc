#Requires -Version 7.0
<# Offline Windows alternative to skin_tool.py. Uses .NET's Windows image
   decoder; it does not download Python packages or modify source artwork. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Prepare','Validate','Share')][string]$Action,
    [string]$Layers,
    [string]$Output,
    [string]$Name,
    [string]$Folder,
    [string]$Preview,
    [switch]$ArmsInFront,
    [ValidateSet('Neutral','LeftPressed','RightPressed','BothPressed')][string]$Pose = 'Neutral'
)
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This offline alternative requires Windows and PowerShell 7.' }
Add-Type -AssemblyName System.Drawing
$partsV1 = @('hair.png','body.png','left.png','right.png')
$partsV2 = @($partsV1) + @('head.png','ahoge.png')
$extraParts = [ordered]@{ tail='tail.png'; wings='wings.png'; accessory='accessory.png'; leftPressed='left-pressed.png'; rightPressed='right-pressed.png' }
$pivots = @('leftPivotX','rightPivotX','armPivotY','rightArmPivotY','hairPivotX','hairPivotY','headPivotX','headPivotY','ahogePivotX','ahogePivotY','tailPivotX','tailPivotY','wingsPivotX','wingsPivotY','accessoryPivotX','accessoryPivotY')
function Read-Limited([string]$Path, [int]$Limit) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.PSIsContainer -or $item.Length -le 0 -or $item.Length -gt $Limit -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "文件不存在、为空、过大或为链接：$Path" }
    $stream = [IO.FileStream]::new($item.FullName, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    try {
        $length = $stream.Length
        if ($length -le 0 -or $length -gt $Limit) { throw "文件为空或过大：$Path" }
        $bytes = [byte[]]::new([int]$length); $offset = 0
        while ($offset -lt $bytes.Length) {
            $read = $stream.Read($bytes, $offset, $bytes.Length - $offset)
            if ($read -eq 0) { throw "文件读取期间发生变化：$Path" }
            $offset += $read
        }
        if ($stream.ReadByte() -ne -1) { throw "文件读取期间发生变化：$Path" }
        return ,$bytes
    } finally { $stream.Dispose() }
}
function Read-SkinManifest([byte[]]$Bytes) {
    $text = [Text.UTF8Encoding]::new($false, $true).GetString($Bytes)
    if ($text.Length -gt 0 -and $text[0] -eq [char]0xfeff) { $text = $text.Substring(1) }
    return $text | ConvertFrom-Json -AsHashtable
}
function Inspect-Skin([string]$Directory, [string]$PreviewPath) {
    $dir = (Resolve-Path -LiteralPath $Directory -ErrorAction Stop).Path
    $dirItem = Get-Item -LiteralPath $dir -Force
    if (-not $dirItem.PSIsContainer -or ($dirItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw '皮肤目录无效或为链接。' }
    $raw = Read-Limited (Join-Path $dir 'skin.json') 16384
    $json = Read-SkinManifest $raw
    if ($null -eq $json -or $json.version -is [bool] -or $json.version -isnot [ValueType] -or $json.version -notin @(1,2,3)) { throw '版本必须为 1、2 或 3。' }
    if ($json.name -isnot [string] -or [string]::IsNullOrWhiteSpace($json.name) -or $json.name.Length -gt 40) { throw '名称不能为空且不得超过 40 个 UTF-16 单元。' }
    if ($json.ContainsKey('armsInFront') -and $json.armsInFront -isnot [bool]) { throw 'armsInFront 必须为布尔值。' }
    if (($null -ne $json.characterId -and $json.characterId -cne '') -or ($null -ne $json.seriesId -and $json.seriesId -cne '')) {
        foreach ($value in @($json.characterId, $json.seriesId)) {
            if ($value -isnot [string] -or [string]::IsNullOrWhiteSpace($value) -or $value.Length -gt 40 -or $value -cne $value.Trim() -or $value -match '[\p{Cc}]') { throw 'characterId 和 seriesId 必须同时为有效标识。' }
        }
    }
    foreach ($key in $pivots) {
        if (-not $json.ContainsKey($key)) { continue }
        $value = $json[$key]
        if ($value -is [bool] -or $value -isnot [ValueType]) { throw "关节坐标无效：$key" }
        try { $number = [double]$value } catch { throw "关节坐标无效：$key" }
        if ([double]::IsNaN($number) -or [double]::IsInfinity($number) -or $number -lt 0 -or $number -gt 1) { throw "关节坐标超出 0–1：$key" }
    }
    $baseParts = if ($json.version -eq 1) { @($partsV1) } elseif ($json.armsInFront) { @('hair.png','body.png','head.png','ahoge.png','left.png','right.png') } else { @($partsV2) }
    $names = $baseParts
    if ($json.version -eq 3) {
        $extra = $extraParts
        foreach ($key in $extra.Keys) { if ($json.ContainsKey($key) -and $json[$key] -isnot [bool]) { throw "图层标志无效：$key" } }
        $back = @(); foreach ($key in @('tail','wings')) { if ($json[$key]) { $back += $extra[$key] } }
        $front = @(); foreach ($key in @('accessory','leftPressed','rightPressed')) { if ($json[$key]) { $front += $extra[$key] } }
        $names = $back + $baseParts + $front
    }
    $width = 0; $height = 0; $composite = $null; $graphics = $null
    $warnings = [Collections.Generic.List[string]]::new()
    try {
        if ($PreviewPath) {
            $previewFull = [IO.Path]::GetFullPath($PreviewPath)
            $dirPrefix = $dir.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
            if ($previewFull.StartsWith($dirPrefix, [StringComparison]::OrdinalIgnoreCase)) { throw '预览必须保存在作品文件夹之外。' }
        }
        foreach ($name in $names) {
            $file = Join-Path $dir $name
            $bytes = Read-Limited $file (8 * 1024 * 1024)
            if ($bytes.Length -lt 33 -or [BitConverter]::ToString($bytes,0,8) -ne '89-50-4E-47-0D-0A-1A-0A' -or [Text.Encoding]::ASCII.GetString($bytes,12,4) -ne 'IHDR') { throw "$name 不是有效 PNG。" }
            $w = $bytes[16]*16777216L + $bytes[17]*65536L + $bytes[18]*256L + $bytes[19]
            $h = $bytes[20]*16777216L + $bytes[21]*65536L + $bytes[22]*256L + $bytes[23]
            if ($w -lt 64 -or $h -lt 64 -or $w -gt 2048 -or $h -gt 2048 -or ($width -ne 0 -and ($w -ne $width -or $h -ne $height))) { throw "$name 画布不一致或超出 64–2048。" }
            $width = [int]$w; $height = [int]$h
            $stream = [IO.MemoryStream]::new($bytes, $false)
            try {
                $image = [Drawing.Image]::FromStream($stream, $true, $true)
                try {
                    if ($image.RawFormat.Guid -ne [Drawing.Imaging.ImageFormat]::Png.Guid -or $image.Width -ne $width -or $image.Height -ne $height) { throw "$name 解码失败。" }
                    # Sparse sampling is a useful diagnostic, not proof that a
                    # large image is empty; small opaque details can be missed.
                    $bitmap = [Drawing.Bitmap]::new($image)
                    try {
                        $hasAlpha = $false; $hasOpaque = $false
                        for ($sy = 0; $sy -lt 32; $sy++) { for ($sx = 0; $sx -lt 32; $sx++) {
                            $a = $bitmap.GetPixel([int](($width - 1) * $sx / 31), [int](($height - 1) * $sy / 31)).A
                            if ($a -gt 0) { $hasAlpha = $true }; if ($a -lt 255) { $hasOpaque = $true }
                        } }
                        if (-not $hasAlpha) { $warnings.Add("${name}: 采样未发现可见像素，可能为空或细节很小") }
                        elseif (-not $hasOpaque) { $warnings.Add("${name}: 采样未发现透明区域，请检查画布背景") }
                    } finally { $bitmap.Dispose() }
                    if ($PreviewPath -and $name -notin @('left-pressed.png','right-pressed.png')) {
                        if ($null -eq $composite) { $composite = [Drawing.Bitmap]::new($width, $height, [Drawing.Imaging.PixelFormat]::Format32bppArgb); $graphics = [Drawing.Graphics]::FromImage($composite) }
                        $pressed = if ($json.version -eq 3 -and $name -eq 'left.png' -and $json.leftPressed -and $Pose -in @('LeftPressed','BothPressed')) { 'left-pressed.png' }
                            elseif ($json.version -eq 3 -and $name -eq 'right.png' -and $json.rightPressed -and $Pose -in @('RightPressed','BothPressed')) { 'right-pressed.png' } else { $null }
                        if ($pressed) {
                            $pressedStream = [IO.MemoryStream]::new((Read-Limited (Join-Path $dir $pressed) (8 * 1024 * 1024)), $false)
                            try { $pressedImage = [Drawing.Image]::FromStream($pressedStream, $true, $true); try { $graphics.DrawImage($pressedImage, 0, 0, $width, $height) } finally { $pressedImage.Dispose() } }
                            finally { $pressedStream.Dispose() }
                        } else { $graphics.DrawImage($image, 0, 0, $width, $height) }
                    }
                } finally { $image.Dispose() }
            } finally { $stream.Dispose() }
        }
        if ($PreviewPath) {
            $fileStream = [IO.File]::Open($previewFull, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
            try { $composite.Save($fileStream, [Drawing.Imaging.ImageFormat]::Png) } finally { $fileStream.Dispose() }
        }
        [pscustomobject]@{ ok=$true; name=$json.name; version=[int]$json.version; width=$width; height=$height; preview=$PreviewPath; warnings=@($warnings); note='透明度为稀疏采样；遮挡、授权和动作质量需人工检查。' }
    } finally { if ($graphics) { $graphics.Dispose() }; if ($composite) { $composite.Dispose() } }
}
if ($Action -eq 'Prepare') {
    if (-not $Layers -or -not $Output -or [string]::IsNullOrWhiteSpace($Name) -or $Name.Length -gt 40) { throw 'Prepare 需要 -Layers、-Output 和不超过 40 单元的 -Name。' }
    $source = (Resolve-Path -LiteralPath $Layers -ErrorAction Stop).Path
    if ((Get-Item -LiteralPath $source -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw '图层目录不能是链接。' }
    $target = [IO.Path]::GetFullPath($Output).TrimEnd([IO.Path]::DirectorySeparatorChar)
    $parent = [IO.Path]::GetDirectoryName($target)
    if (-not $parent -or -not (Test-Path -LiteralPath $parent -PathType Container) -or (Test-Path -LiteralPath $target)) { throw '输出必须是父目录已存在的新文件夹。' }
    if ($Preview -and [IO.Path]::GetFullPath($Preview).StartsWith($target + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw '预览必须保存在作品文件夹之外。' }
    if ((Get-Item -LiteralPath $parent -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw '输出父目录不能是链接。' }
    $staging = Join-Path $parent ('.netpet-skin-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $staging | Out-Null
    try {
        foreach ($part in $partsV2) { [IO.File]::WriteAllBytes((Join-Path $staging $part), (Read-Limited (Join-Path $source $part) (8 * 1024 * 1024))) }
        $manifest = [ordered]@{version=2;name=$Name;leftPivotX=.32;armPivotY=.68;rightPivotX=.68;rightArmPivotY=.68;hairPivotX=.5;hairPivotY=.22;headPivotX=.5;headPivotY=.56;ahogePivotX=.5;ahogePivotY=.14}
        if ($ArmsInFront) { $manifest['armsInFront'] = $true }
        foreach ($flag in $extraParts.Keys) {
            $part = $extraParts[$flag]
            if ($null -ne (Get-Item -LiteralPath (Join-Path $source $part) -Force -ErrorAction SilentlyContinue)) {
                [IO.File]::WriteAllBytes((Join-Path $staging $part), (Read-Limited (Join-Path $source $part) (8 * 1024 * 1024)))
                $manifest.version = 3; $manifest[$flag] = $true
            }
        }
        $manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $staging 'skin.json') -Encoding utf8NoBOM
        Inspect-Skin $staging $null | Out-Null
        [IO.Directory]::Move($staging, $target)
    } finally {
        if (Test-Path -LiteralPath $staging -PathType Container) {
            $resolved = (Resolve-Path -LiteralPath $staging).Path
            if ([IO.Path]::GetDirectoryName($resolved) -ne $parent -or -not [IO.Path]::GetFileName($resolved).StartsWith('.netpet-skin-') -or ((Get-Item -LiteralPath $resolved -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw '拒绝清理不安全的临时目录。' }
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
    }
    Inspect-Skin $target $Preview
} elseif ($Action -eq 'Share') {
    if (-not $Folder -or -not $Output) { throw 'Share 需要 -Folder 和 -Output。' }
    $source = (Resolve-Path -LiteralPath $Folder -ErrorAction Stop).Path
    $sourceItem = Get-Item -LiteralPath $source -Force
    if (-not $sourceItem.PSIsContainer -or ($sourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw '皮肤目录无效或为链接。' }
    $target = [IO.Path]::GetFullPath($Output)
    $parent = [IO.Path]::GetDirectoryName($target)
    if ([IO.Path]::GetExtension($target) -ine '.zip' -or -not $parent -or -not (Test-Path -LiteralPath $parent -PathType Container) -or (Test-Path -LiteralPath $target)) { throw '分享路径必须是父目录已存在的新 ZIP 文件。' }
    if ($target.StartsWith($source.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw '分享文件必须保存在作品文件夹之外。' }
    if ((Get-Item -LiteralPath $parent -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw '输出父目录不能是链接。' }
    $staging = Join-Path $parent ('.netpet-share-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $staging | Out-Null
    try {
        $raw = Read-Limited (Join-Path $source 'skin.json') 16384
        $manifest = Read-SkinManifest $raw
        if ($null -eq $manifest -or $manifest.version -is [bool] -or $manifest.version -isnot [ValueType] -or $manifest.version -notin @(1,2,3)) { throw '版本必须为 1、2 或 3。' }
        $names = if ($manifest.version -eq 1) { @($partsV1) } else { @($partsV2) }
        if ($manifest.version -eq 3) { foreach ($flag in $extraParts.Keys) { if ($manifest[$flag]) { $names += $extraParts[$flag] } } }
        [IO.File]::WriteAllBytes((Join-Path $staging 'skin.json'), $raw)
        foreach ($name in $names) { [IO.File]::WriteAllBytes((Join-Path $staging $name), (Read-Limited (Join-Path $source $name) (8 * 1024 * 1024))) }
        $checked = Inspect-Skin $staging $null
        $temporary = Join-Path $staging 'share.tmp'
        $stream = [IO.File]::Open($temporary, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $archive = [IO.Compression.ZipArchive]::new($stream, [IO.Compression.ZipArchiveMode]::Create, $true)
            try {
                foreach ($name in (@('skin.json') + $names)) {
                    $entry = $archive.CreateEntry($name, [IO.Compression.CompressionLevel]::Optimal)
                    $entryStream = $entry.Open()
                    try { $limit = if ($name -eq 'skin.json') { 16384 } else { 8 * 1024 * 1024 }; $bytes = Read-Limited (Join-Path $staging $name) $limit; $entryStream.Write($bytes, 0, $bytes.Length) } finally { $entryStream.Dispose() }
                }
            } finally { $archive.Dispose() }
        } finally { $stream.Dispose() }
        [IO.File]::Move($temporary, $target)
        [pscustomobject]@{ ok=$true; name=$checked.name; version=$checked.version; zip=$target; warnings=$checked.warnings }
    } finally {
        if (Test-Path -LiteralPath $staging -PathType Container) {
            $resolved = (Resolve-Path -LiteralPath $staging).Path
            if ([IO.Path]::GetDirectoryName($resolved) -ne $parent -or -not [IO.Path]::GetFileName($resolved).StartsWith('.netpet-share-') -or ((Get-Item -LiteralPath $resolved -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw '拒绝清理不安全的临时目录。' }
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
    }
} else {
    if (-not $Folder) { throw 'Validate 需要 -Folder。' }
    Inspect-Skin $Folder $Preview
}
