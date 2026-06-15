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

$manifestPath = Join-Path $brand.Path "manifest.csv"
if (-not (Test-Path -LiteralPath $manifestPath)) {
  throw "Missing manifest: $manifestPath"
}

$updates = Import-Csv -LiteralPath $ClassificationCsv
$manifest = Import-Csv -LiteralPath $manifestPath
$seqMap = @{}

foreach ($item in $manifest) {
  if ($item.copied_filename -match '-(\d{4})-') {
    $seqMap[[int]$matches[1]] = $item
  }
}

foreach ($row in $updates) {
  $seq = [int]$row.seq
  if (-not $seqMap.ContainsKey($seq)) {
    throw "No manifest item found for sequence: $seq"
  }

  $item = $seqMap[$seq]
  $item.status = "classified"
  $item.category = $row.category
  $item.notes = $row.notes
  $item.working_path = Join-Path (Join-Path $brand.Path $row.category) $item.copied_filename
}

$manifest | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8
$updates | Group-Object category | Sort-Object Name | Select-Object Name,Count
