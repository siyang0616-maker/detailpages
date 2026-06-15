param(
  [Parameter(Mandatory = $true)]
  [string]$SourceDir,

  [Parameter(Mandatory = $true)]
  [string]$BrandDir,

  [Parameter(Mandatory = $true)]
  [string]$BrandSlug
)

$ErrorActionPreference = "Stop"

$source = Resolve-Path -LiteralPath $SourceDir
$brand = $BrandDir
$uncategorized = Join-Path $brand "08-reference-uncategorized"
$manifest = Join-Path $brand "manifest.csv"
$categories = @(
  "01-exterior-signage",
  "02-interior-seating",
  "03-counter-kiosk-order",
  "04-kitchen-equipment",
  "05-food-drink-menu",
  "06-menu-promotion",
  "07-street-trade-area",
  "08-reference-uncategorized",
  "09-caution-unusable",
  "00-contact-sheets"
)

foreach ($category in $categories) {
  New-Item -ItemType Directory -Force -Path (Join-Path $brand $category) | Out-Null
}

$extensions = @(".jpg", ".jpeg", ".png", ".webp", ".bmp")
$files = Get-ChildItem -LiteralPath $source.Path -File |
  Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() } |
  Sort-Object Name

$rows = New-Object System.Collections.Generic.List[object]
$index = 1
foreach ($file in $files) {
  $safeOriginalName = $file.Name -replace '[^\p{L}\p{Nd}\.\-_ ]', '_'
  $copyName = "{0}-{1:D4}-{2}" -f $BrandSlug, $index, $safeOriginalName
  $destPath = Join-Path $uncategorized $copyName

  if (-not (Test-Path -LiteralPath $destPath)) {
    Copy-Item -LiteralPath $file.FullName -Destination $destPath
  }

  $rows.Add([PSCustomObject]@{
    brand = $BrandSlug
    status = "uncategorized"
    category = "08-reference-uncategorized"
    copied_filename = $copyName
    source_path = $file.FullName
    working_path = $destPath
    original_last_write_time = $file.LastWriteTime.ToString("s")
    original_size_bytes = $file.Length
    notes = ""
  })
  $index += 1
}

$rows | Export-Csv -LiteralPath $manifest -NoTypeInformation -Encoding UTF8

[PSCustomObject]@{
  Brand = $BrandSlug
  Source = $source.Path
  Destination = $brand
  Copied = $files.Count
  Manifest = $manifest
}
