param(
  [Parameter(Mandatory = $true)]
  [string]$BrandDir,

  [Parameter(Mandatory = $true)]
  [string]$ClassificationCsv
)

$ErrorActionPreference = "Stop"

$brand = Resolve-Path -LiteralPath $BrandDir
$workspaceRoot = Resolve-Path -LiteralPath "C:\Users\home\Documents\detailpages"
if (-not $brand.Path.StartsWith($workspaceRoot.Path)) {
  throw "BrandDir must stay inside the detailpages workspace."
}

$uncategorized = Join-Path $brand.Path "08-reference-uncategorized"
$manifestPath = Join-Path $brand.Path "manifest.csv"
$rows = Import-Csv -LiteralPath $ClassificationCsv

foreach ($row in $rows) {
  $source = Join-Path $uncategorized $row.filename
  if (-not (Test-Path -LiteralPath $source)) {
    throw "Missing copied source file: $source"
  }

  $categoryDir = Join-Path $brand.Path $row.category
  if (-not (Test-Path -LiteralPath $categoryDir)) {
    throw "Missing category folder: $categoryDir"
  }

  $dest = Join-Path $categoryDir $row.filename
  if (-not (Test-Path -LiteralPath $dest)) {
    Copy-Item -LiteralPath $source -Destination $dest
  }
}

if (Test-Path -LiteralPath $manifestPath) {
  $manifest = Import-Csv -LiteralPath $manifestPath
  $map = @{}
  foreach ($row in $rows) {
    $map[$row.filename] = $row
  }

  $updated = foreach ($item in $manifest) {
    if ($map.ContainsKey($item.copied_filename)) {
      $item.status = "classified"
      $item.category = $map[$item.copied_filename].category
      $item.notes = $map[$item.copied_filename].notes
      $item.working_path = Join-Path (Join-Path $brand.Path $item.category) $item.copied_filename
    }
    $item
  }
  $updated | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8
}

$rows | Group-Object category | Sort-Object Name | Select-Object Name,Count
