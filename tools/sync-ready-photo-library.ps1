param(
  [string]$LibraryRoot = "C:\Users\home\Documents\detailpages\franchise-photo-library",
  [string]$ReadyRoot = "C:\Users\home\Documents\detailpages\franchise-photo-library\_ready-for-detail-page"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Resolve-Path -LiteralPath "C:\Users\home\Documents\detailpages"
$library = Resolve-Path -LiteralPath $LibraryRoot

if (-not $library.Path.StartsWith($workspaceRoot.Path)) {
  throw "LibraryRoot must stay inside the detailpages workspace."
}

New-Item -ItemType Directory -Force -Path $ReadyRoot | Out-Null
$ready = Resolve-Path -LiteralPath $ReadyRoot
if (-not $ready.Path.StartsWith($workspaceRoot.Path)) {
  throw "ReadyRoot must stay inside the detailpages workspace."
}
if ([System.IO.Path]::GetFileName($ready.Path) -ne "_ready-for-detail-page") {
  throw "ReadyRoot must be the generated _ready-for-detail-page folder."
}

Get-ChildItem -LiteralPath $ready.Path -Force | Remove-Item -Recurse -Force

$brandOrder = @(
  @{ Slug = "megacoffee"; Display = "01_megacoffee" },
  @{ Slug = "subway"; Display = "02_subway" },
  @{ Slug = "lotteria"; Display = "03_lotteria" },
  @{ Slug = "composecoffee"; Display = "04_composecoffee" },
  @{ Slug = "woozoo-coffee"; Display = "05_woozoo-coffee" },
  @{ Slug = "twosome-place"; Display = "06_twosome-place" },
  @{ Slug = "baskin-robbins"; Display = "07_baskin-robbins" },
  @{ Slug = "paris-baguette"; Display = "08_paris-baguette" },
  @{ Slug = "paikdabang"; Display = "09_paikdabang" }
)

$categoryMap = @{
  "01-exterior-signage" = "01_exterior_signage"
  "02-interior-seating" = "02_interior_seating"
  "03-counter-kiosk-order" = "03_counter_kiosk_order"
  "04-kitchen-equipment" = "04_kitchen_equipment"
  "05-food-drink-menu" = "05_food_drink_menu"
  "06-menu-promotion" = "06_menu_promotion"
  "07-street-trade-area" = "07_street_trade_area"
  "08-reference-uncategorized" = "98_original_copy_reference"
  "09-caution-unusable" = "99_review_needed"
}

$categoryOrder = @(
  "01-exterior-signage",
  "02-interior-seating",
  "03-counter-kiosk-order",
  "04-kitchen-equipment",
  "05-food-drink-menu",
  "06-menu-promotion",
  "07-street-trade-area",
  "08-reference-uncategorized",
  "09-caution-unusable"
)

$imageExtensions = @(".jpg", ".jpeg", ".png", ".webp", ".bmp")
$summaryRows = New-Object System.Collections.Generic.List[object]

function Get-ImageExtension([string]$Path) {
  $ext = [System.IO.Path]::GetExtension($Path)
  if ([string]::IsNullOrWhiteSpace($ext)) {
    return ".jpg"
  }
  return $ext.ToLowerInvariant()
}

foreach ($brandInfo in $brandOrder) {
  $slug = $brandInfo.Slug
  $display = $brandInfo.Display
  $brandDir = Join-Path $library.Path $slug
  $manifestPath = Join-Path $brandDir "manifest.csv"
  $readyBrandDir = Join-Path $ready.Path $display

  New-Item -ItemType Directory -Force -Path $readyBrandDir | Out-Null
  foreach ($category in $categoryOrder) {
    New-Item -ItemType Directory -Force -Path (Join-Path $readyBrandDir $categoryMap[$category]) | Out-Null
  }

  if (-not (Test-Path -LiteralPath $manifestPath)) {
    $summaryRows.Add([PSCustomObject]@{
      brand = $display
      manifest_rows = 0
      classified = 0
      review_needed = 0
      copied_to_ready = 0
      note = "manifest missing"
    })
    continue
  }

  $manifest = Import-Csv -LiteralPath $manifestPath
  $categoryCounters = @{}
  foreach ($category in $categoryOrder) {
    $categoryCounters[$category] = 0
  }

  $copiedCount = 0
  $classifiedCount = 0
  $reviewCount = 0
  $catalogRows = New-Object System.Collections.Generic.List[object]

  foreach ($item in $manifest) {
    $category = $item.category
    if ([string]::IsNullOrWhiteSpace($category) -or -not $categoryMap.ContainsKey($category)) {
      $category = "09-caution-unusable"
    }

    if ($item.status -ne "classified" -and $category -eq "08-reference-uncategorized") {
      $category = "09-caution-unusable"
    }

    if ($item.status -eq "classified") {
      $classifiedCount += 1
    } else {
      $reviewCount += 1
    }

    $sourceCandidates = @()

    if (-not [string]::IsNullOrWhiteSpace($item.working_path)) {
      $sourceCandidates += Get-Item -LiteralPath $item.working_path -ErrorAction SilentlyContinue
    }

    $fallback = Join-Path (Join-Path $brandDir "08-reference-uncategorized") $item.copied_filename
    $sourceCandidates += Get-Item -LiteralPath $fallback -ErrorAction SilentlyContinue

    $sourceFile = $sourceCandidates |
      Where-Object { $_ -and $_.PSIsContainer -eq $false -and ($imageExtensions -contains $_.Extension.ToLowerInvariant()) } |
      Select-Object -First 1

    if (-not $sourceFile) {
      continue
    }

    $categoryCounters[$category] += 1
    $targetCategoryName = $categoryMap[$category]
    $targetCategoryDir = Join-Path $readyBrandDir $targetCategoryName
    $targetName = "{0}_{1}_{2:D3}{3}" -f $display, $targetCategoryName, $categoryCounters[$category], (Get-ImageExtension $sourceFile.FullName)
    $targetPath = Join-Path $targetCategoryDir $targetName

    Copy-Item -LiteralPath $sourceFile.FullName -Destination $targetPath -Force
    $copiedCount += 1

    $catalogRows.Add([PSCustomObject]@{
      brand = $display
      category = $targetCategoryName
      ready_file = $targetPath
      source_copy = $sourceFile.FullName
      original_source = $item.source_path
      status = $item.status
      notes = $item.notes
    })
  }

  $catalogRows | Export-Csv -LiteralPath (Join-Path $readyBrandDir "catalog.csv") -NoTypeInformation -Encoding UTF8

  $readme = @()
  $readme += "# $display photo library"
  $readme += ""
  $readme += "- This is the unified viewing folder for detail page work."
  $readme += "- Original source files were not modified."
  $readme += "- Use exterior, interior, counter, and food/menu folders first when building detail pages."
  $readme += "- Check 99_review_needed before final use because it may include unclear, private, or not-yet-classified photos."
  $readme += ""
  $readme += "## Counts by folder"
  foreach ($category in $categoryOrder) {
    $folder = $categoryMap[$category]
    $count = (Get-ChildItem -LiteralPath (Join-Path $readyBrandDir $folder) -File -ErrorAction SilentlyContinue |
      Where-Object { $imageExtensions -contains $_.Extension.ToLowerInvariant() } |
      Measure-Object).Count
    $readme += "- ${folder}: $count"
  }
  $readme | Set-Content -LiteralPath (Join-Path $readyBrandDir "README.md") -Encoding UTF8

  $summaryRows.Add([PSCustomObject]@{
    brand = $display
    manifest_rows = $manifest.Count
    classified = $classifiedCount
    review_needed = $reviewCount
    copied_to_ready = $copiedCount
    note = ""
  })
}

$summaryRows | Export-Csv -LiteralPath (Join-Path $ready.Path "00_overall_status.csv") -NoTypeInformation -Encoding UTF8

$overall = @()
$overall += "# Unified franchise photo library status"
$overall += ""
$overall += "- Root: $($ready.Path)"
$overall += "- Original files were not modified."
$overall += "- Every brand uses the same folder names and order."
$overall += ""
$overall += "## Brand progress"
foreach ($row in $summaryRows) {
  $overall += "- $($row.brand): total $($row.manifest_rows), classified $($row.classified), review_needed $($row.review_needed), copied_to_ready $($row.copied_to_ready)"
}
$overall | Set-Content -LiteralPath (Join-Path $ready.Path "README.md") -Encoding UTF8

$summaryRows
