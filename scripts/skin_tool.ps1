#Requires -Version 7.0
<# Offline Windows alternative to skin_tool.py. Uses .NET's Windows image
   decoder; it does not download Python packages or modify source artwork. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Prepare','Validate')][string]$Action,
    [string]$Layers,
    [string]$Output,
    [string]$Name,
    [string]$Folder,
    [string]$Preview
)
$ErrorActionPreference = 'Stop'
if (-not $IsWindows) { throw 'This offline alternative requires Windows and PowerShell 7.' }
Add-Type -AssemblyName System.Drawing
$partsV1 = @('hair.png','body.png','left.png','right.png')
$partsV2 = @($partsV1) + @('head.png','ahoge.png')
$pivots = @('leftPivotX','rightPivotX','armPivotY','rightArmPivotY','hairPivotX','hairPivotY','headPivotX','headPivotY','ahogePivotX','ahogePivotY')
function Read-Limited([string]$Path, [int]$Limit) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.PSIsContainer -or $item.Length -le 0 -or $item.Length -gt $Limit -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "文件不存在、为空、过大或为链接：$Path" }
    return ,([IO.File]::ReadAllBytes($item.FullName))
}
function Inspect-Skin([string]$Directory, [string]$PreviewPath) {
    $dir = (Resolve-Path -LiteralPath $Directory -ErrorAction Stop).Path
    $dirItem = Get-Item -LiteralPath $dir -Force
    if (-not $dirItem.PSIsContainer -or ($dirItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw '皮肤目录无效或为链接。' }
    $raw = Read-Limited (Join-Path $dir 'skin.json') 16384
    $json = [Text.UTF8Encoding]::new($false, $true).GetString($raw) | ConvertFrom-Json -AsHashtable
    if ($null -eq $json -or $json.version -is [bool] -or $json.version -isnot [ValueType] -or $json.version -notin @(1,2)) { throw '版本必须为 1 或 2。' }
    if ($json.name -isnot [string] -or [string]::IsNullOrWhiteSpace($json.name) -or $json.name.Length -gt 40) { throw '名称不能为空且不得超过 40 个 UTF-16 单元。' }
    foreach ($key in $pivots) {
        if (-not $json.ContainsKey($key)) { continue }
        $value = $json[$key]
        if ($value -is [bool] -or $value -isnot [ValueType]) { throw "关节坐标无效：$key" }
        try { $number = [double]$value } catch { throw "关节坐标无效：$key" }
        if ([double]::IsNaN($number) -or [double]::IsInfinity($number) -or $number -lt 0 -or $number -gt 1) { throw "关节坐标超出 0–1：$key" }
    }
    $names = if ($json.version -eq 1) { $partsV1 } else { $partsV2 }
    $width = 0; $height = 0; $composite = $null; $graphics = $null
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
                    if ($PreviewPath) {
                        if ($null -eq $composite) { $composite = [Drawing.Bitmap]::new($width, $height, [Drawing.Imaging.PixelFormat]::Format32bppArgb); $graphics = [Drawing.Graphics]::FromImage($composite) }
                        $graphics.DrawImage($image, 0, 0, $width, $height)
                    }
                } finally { $image.Dispose() }
            } finally { $stream.Dispose() }
        }
        if ($PreviewPath) {
            $fileStream = [IO.File]::Open($previewFull, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
            try { $composite.Save($fileStream, [Drawing.Imaging.ImageFormat]::Png) } finally { $fileStream.Dispose() }
        }
        [pscustomobject]@{ ok=$true; name=$json.name; version=[int]$json.version; width=$width; height=$height; preview=$PreviewPath; note='透明度和动作质量需人工检查。' }
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
        [ordered]@{version=2;name=$Name;leftPivotX=.32;armPivotY=.68;rightPivotX=.68;rightArmPivotY=.68;hairPivotX=.5;hairPivotY=.22;headPivotX=.5;headPivotY=.56;ahogePivotX=.5;ahogePivotY=.14} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $staging 'skin.json') -Encoding utf8NoBOM
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
} else {
    if (-not $Folder) { throw 'Validate 需要 -Folder。' }
    Inspect-Skin $Folder $Preview
}
