param(
  [string]$ManifestPath = "C:\Users\home\Documents\detailpages\blog-writing-corpus\compiled\blog-corpus-manifest.csv",
  [string]$ReadyRoot = "C:\Users\home\Documents\detailpages\franchise-photo-library\_ready-for-detail-page",
  [string]$OutputRoot = "C:\Users\home\Documents\detailpages\blog-writing-corpus\compiled\by-brand"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Resolve-Path -LiteralPath "C:\Users\home\Documents\detailpages"
$ready = Resolve-Path -LiteralPath $ReadyRoot
if (-not $ready.Path.StartsWith($workspaceRoot.Path)) {
  throw "ReadyRoot must stay inside the detailpages workspace."
}

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$output = Resolve-Path -LiteralPath $OutputRoot
if (-not $output.Path.StartsWith($workspaceRoot.Path)) {
  throw "OutputRoot must stay inside the detailpages workspace."
}

$brandMap = @(
  @{ Key = "메가커피"; Slug = "megacoffee"; Ready = "01_megacoffee" },
  @{ Key = "메가"; Slug = "megacoffee"; Ready = "01_megacoffee" },
  @{ Key = "써브웨이"; Slug = "subway"; Ready = "02_subway" },
  @{ Key = "서브웨이"; Slug = "subway"; Ready = "02_subway" },
  @{ Key = "롯데리아"; Slug = "lotteria"; Ready = "03_lotteria" },
  @{ Key = "컴포즈커피"; Slug = "composecoffee"; Ready = "04_composecoffee" },
  @{ Key = "컴포즈"; Slug = "composecoffee"; Ready = "04_composecoffee" },
  @{ Key = "우지커피"; Slug = "woozoo-coffee"; Ready = "05_woozoo-coffee" },
  @{ Key = "투썸플레이스"; Slug = "twosome-place"; Ready = "06_twosome-place" },
  @{ Key = "투썸"; Slug = "twosome-place"; Ready = "06_twosome-place" },
  @{ Key = "배스킨라빈스"; Slug = "baskin-robbins"; Ready = "07_baskin-robbins" },
  @{ Key = "베스킨라빈스"; Slug = "baskin-robbins"; Ready = "07_baskin-robbins" },
  @{ Key = "파리바게뜨"; Slug = "paris-baguette"; Ready = "08_paris-baguette" },
  @{ Key = "파리바게트"; Slug = "paris-baguette"; Ready = "08_paris-baguette" },
  @{ Key = "빽다방"; Slug = "paikdabang"; Ready = "09_paikdabang" }
)

function Read-TextFileSmart([string]$Path) {
  $bytes = [System.IO.File]::ReadAllBytes($Path)

  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    return [System.Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
  }

  if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
    return [System.Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
  }

  $utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
  try {
    return $utf8Strict.GetString($bytes)
  } catch {
    return [System.Text.Encoding]::GetEncoding(949).GetString($bytes)
  }
}

function Resolve-Brand($Text) {
  foreach ($brand in $brandMap) {
    if ($Text -like "*$($brand.Key)*") {
      return $brand
    }
  }
  return @{ Key = "unknown"; Slug = "unknown"; Ready = "_unknown" }
}

$rows = Import-Csv -LiteralPath $ManifestPath
$summary = New-Object System.Collections.Generic.List[object]
$brandGroups = @{}

foreach ($row in $rows) {
  $searchText = "$($row.original_path) $($row.parent_folder) $($row.file_name) $($row.first_nonempty_line)"
  $brand = Resolve-Brand $searchText
  $row | Add-Member -NotePropertyName brand_slug -NotePropertyValue $brand.Slug -Force
  $row | Add-Member -NotePropertyName ready_brand_folder -NotePropertyValue $brand.Ready -Force

  if (-not $brandGroups.ContainsKey($brand.Slug)) {
    $brandGroups[$brand.Slug] = New-Object System.Collections.Generic.List[object]
  }
  $brandGroups[$brand.Slug].Add($row)
}

foreach ($slug in ($brandGroups.Keys | Sort-Object)) {
  $items = $brandGroups[$slug] | Sort-Object {[int]$_.seq}
  $readyName = $items[0].ready_brand_folder

  $brandOutput = Join-Path $output.Path $slug
  New-Item -ItemType Directory -Force -Path $brandOutput | Out-Null

  $readyBlogDir = $null
  if ($readyName -ne "_unknown") {
    $readyBrandDir = Join-Path $ready.Path $readyName
    if (Test-Path -LiteralPath $readyBrandDir) {
      $readyBlogDir = Join-Path $readyBrandDir "00_blog_posts"
      if (Test-Path -LiteralPath $readyBlogDir) {
        Get-ChildItem -LiteralPath $readyBlogDir -Force | Remove-Item -Recurse -Force
      }
      New-Item -ItemType Directory -Force -Path $readyBlogDir | Out-Null
    }
  }

  $compiled = New-Object System.Collections.Generic.List[string]
  $compiled.Add("# Blog posts for $slug")
  $compiled.Add("")
  $compiled.Add("- Posts: $($items.Count)")
  $compiled.Add("")

  $localRows = New-Object System.Collections.Generic.List[object]
  $brandIndex = 1
  foreach ($item in $items) {
    $copyName = "{0}_{1:D3}_{2}" -f $slug, $brandIndex, ($item.file_name -replace '[\\/:*?"<>|]', '_')
    $brandCopyPath = Join-Path $brandOutput $copyName
    Copy-Item -LiteralPath $item.raw_copy_path -Destination $brandCopyPath -Force

    $readyCopyPath = ""
    if ($readyBlogDir) {
      $readyCopyPath = Join-Path $readyBlogDir $copyName
      Copy-Item -LiteralPath $item.raw_copy_path -Destination $readyCopyPath -Force
    }

    $text = Read-TextFileSmart $item.raw_copy_path
    $text = $text -replace "`r`n", "`n" -replace "`r", "`n"

    $compiled.Add("---")
    $compiled.Add("")
    $compiled.Add("## Post $brandIndex - $($item.file_name)")
    $compiled.Add("")
    $compiled.Add("- Original: $($item.original_path)")
    $compiled.Add("- Ready copy: $readyCopyPath")
    $compiled.Add("")
    $compiled.Add("----- BEGIN POST TEXT -----")
    $compiled.Add($text.Trim())
    $compiled.Add("----- END POST TEXT -----")
    $compiled.Add("")

    $localRows.Add([PSCustomObject]@{
      brand_slug = $slug
      seq_in_brand = $brandIndex
      corpus_seq = $item.seq
      file_name = $item.file_name
      original_path = $item.original_path
      brand_copy_path = $brandCopyPath
      ready_copy_path = $readyCopyPath
      char_count = $item.char_count
    })
    $brandIndex += 1
  }

  $compiledPath = Join-Path $brandOutput "all-posts-$slug.md"
  $manifestOut = Join-Path $brandOutput "manifest-$slug.csv"
  $compiled | Set-Content -LiteralPath $compiledPath -Encoding UTF8
  $localRows | Export-Csv -LiteralPath $manifestOut -NoTypeInformation -Encoding UTF8

  if ($readyBlogDir) {
    Copy-Item -LiteralPath $compiledPath -Destination (Join-Path $readyBlogDir "all-blog-posts.md") -Force
    Copy-Item -LiteralPath $manifestOut -Destination (Join-Path $readyBlogDir "manifest.csv") -Force
  }

  $summary.Add([PSCustomObject]@{
    brand_slug = $slug
    ready_folder = $readyName
    posts = $items.Count
    compiled = $compiledPath
    ready_blog_dir = $readyBlogDir
  })
}

$summaryPath = Join-Path $output.Path "brand-blog-summary.csv"
$summary | Export-Csv -LiteralPath $summaryPath -NoTypeInformation -Encoding UTF8
$summary
