param(
  [Parameter(Mandatory = $true)]
  [string]$BrandDir,

  [Parameter(Mandatory = $true)]
  [string]$BrandSlug
)

$ErrorActionPreference = "Stop"

$brand = Resolve-Path -LiteralPath $BrandDir
$workspaceRoot = Resolve-Path -LiteralPath "C:\Users\home\Documents\detailpages"
if (-not $brand.Path.StartsWith($workspaceRoot.Path)) {
  throw "BrandDir must stay inside the detailpages workspace."
}

$manifestPath = Join-Path $brand.Path "manifest.csv"
$sourceDir = Join-Path $brand.Path "08-reference-uncategorized"
$exportRoot = Join-Path $brand.Path "90-classified-normalized"
$catalogPath = Join-Path $exportRoot "catalog.csv"

$categorySlugs = @{
  "01-exterior-signage" = "exterior_signage"
  "02-interior-seating" = "interior_seating"
  "03-counter-kiosk-order" = "counter_kiosk_order"
  "04-kitchen-equipment" = "kitchen_equipment"
  "05-food-drink-menu" = "food_drink_menu"
  "06-menu-promotion" = "menu_promotion"
  "07-street-trade-area" = "street_trade_area"
  "09-caution-unusable" = "caution_unusable"
}

$manifest = Import-Csv -LiteralPath $manifestPath |
  Where-Object { $_.status -eq "classified" -and $categorySlugs.ContainsKey($_.category) } |
  Sort-Object category,copied_filename

$counts = @{}
$catalog = New-Object System.Collections.Generic.List[object]

foreach ($item in $manifest) {
  $category = $item.category
  $slug = $categorySlugs[$category]
  if (-not $counts.ContainsKey($category)) {
    $counts[$category] = 0
  }
  $counts[$category] += 1

  $source = Join-Path $sourceDir $item.copied_filename
  if (-not (Test-Path -LiteralPath $source)) {
    throw "Missing copied source file: $source"
  }

  $ext = [System.IO.Path]::GetExtension($item.copied_filename).ToLowerInvariant()
  if ($ext -eq ".jpeg") { $ext = ".jpg" }
  $normalizedName = "{0}_{1}_{2:D3}{3}" -f $BrandSlug, $slug, $counts[$category], $ext
  $categoryDir = Join-Path $exportRoot $category
  New-Item -ItemType Directory -Force -Path $categoryDir | Out-Null
  $dest = Join-Path $categoryDir $normalizedName
  Copy-Item -LiteralPath $source -Destination $dest -Force

  $catalog.Add([PSCustomObject]@{
    brand = $BrandSlug
    category = $category
    normalized_filename = $normalizedName
    normalized_path = $dest
    source_copy_filename = $item.copied_filename
    original_source_path = $item.source_path
    notes = $item.notes
  })
}

New-Item -ItemType Directory -Force -Path $exportRoot | Out-Null
$catalog | Export-Csv -LiteralPath $catalogPath -NoTypeInformation -Encoding UTF8

[PSCustomObject]@{
  Brand = $BrandSlug
  ExportRoot = $exportRoot
  Classified = $catalog.Count
  Catalog = $catalogPath
}
