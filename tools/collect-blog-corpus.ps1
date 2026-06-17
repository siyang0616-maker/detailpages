param(
  [Parameter(Mandatory = $true)]
  [string]$SourceDir,

  [string]$CorpusDir = "C:\Users\home\Documents\detailpages\blog-writing-corpus",

  [string]$SourceLabel = "private-blog-review"
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Resolve-Path -LiteralPath "C:\Users\home\Documents\detailpages"
$source = Resolve-Path -LiteralPath $SourceDir

New-Item -ItemType Directory -Force -Path $CorpusDir | Out-Null
$corpus = Resolve-Path -LiteralPath $CorpusDir
if (-not $corpus.Path.StartsWith($workspaceRoot.Path)) {
  throw "CorpusDir must stay inside the detailpages workspace."
}

$rawDir = Join-Path $corpus.Path "raw-copies"
$compiledDir = Join-Path $corpus.Path "compiled"
$analysisDir = Join-Path $corpus.Path "analysis"
New-Item -ItemType Directory -Force -Path $rawDir, $compiledDir, $analysisDir | Out-Null

function Get-SafeName([string]$Name) {
  $safe = $Name -replace '[\\/:*?"<>|]', '_'
  $safe = $safe -replace '\s+', ' '
  return $safe.Trim()
}

function Read-TextFileSmart([string]$Path) {
  $bytes = [System.IO.File]::ReadAllBytes($Path)

  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    return [System.Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
  }

  if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
    return [System.Text.Encoding]::Unicode.GetString($bytes, 2, $bytes.Length - 2)
  }

  if ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) {
    return [System.Text.Encoding]::BigEndianUnicode.GetString($bytes, 2, $bytes.Length - 2)
  }

  $utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
  try {
    return $utf8Strict.GetString($bytes)
  } catch {
    $cp949 = [System.Text.Encoding]::GetEncoding(949)
    return $cp949.GetString($bytes)
  }
}

$txtFiles = Get-ChildItem -LiteralPath $source.Path -Recurse -File |
  Where-Object { $_.Extension.ToLowerInvariant() -eq ".txt" } |
  Sort-Object FullName

$rows = New-Object System.Collections.Generic.List[object]
$compiled = New-Object System.Collections.Generic.List[string]
$compiled.Add("# Blog writing corpus")
$compiled.Add("")
$compiled.Add("- Source label: $SourceLabel")
$compiled.Add("- Source folder: $($source.Path)")
$compiled.Add("- Created at: $((Get-Date).ToString('s'))")
$compiled.Add("- Original files were not modified.")
$compiled.Add("")

$index = 1
foreach ($file in $txtFiles) {
  $relative = $file.FullName.Substring($source.Path.Length).TrimStart('\')
  $parentName = Split-Path -Leaf (Split-Path -Parent $file.FullName)
  $safeParent = Get-SafeName $parentName
  $safeFile = Get-SafeName $file.Name
  $copyName = "{0:D3}_{1}__{2}" -f $index, $safeParent, $safeFile
  $copyPath = Join-Path $rawDir $copyName

  Copy-Item -LiteralPath $file.FullName -Destination $copyPath -Force

  $text = Read-TextFileSmart $file.FullName
  $normalizedText = $text -replace "`r`n", "`n" -replace "`r", "`n"
  $nonEmptyLines = $normalizedText -split "`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
  $firstLine = ""
  if ($nonEmptyLines.Count -gt 0) {
    $firstLine = $nonEmptyLines[0].Trim()
  }
  $charCount = $normalizedText.Length
  $lineCount = ($normalizedText -split "`n").Count

  $rows.Add([PSCustomObject]@{
    seq = $index
    source_label = $SourceLabel
    original_path = $file.FullName
    relative_path = $relative
    raw_copy_path = $copyPath
    parent_folder = $parentName
    file_name = $file.Name
    first_nonempty_line = $firstLine
    char_count = $charCount
    line_count = $lineCount
    original_last_write_time = $file.LastWriteTime.ToString("s")
    original_size_bytes = $file.Length
  })

  $compiled.Add("---")
  $compiled.Add("")
  $postNumber = "{0:D3}" -f $index
  $compiled.Add("## Post ${postNumber}: $safeFile")
  $compiled.Add("")
  $compiled.Add(("- Original path: {0}" -f $file.FullName))
  $compiled.Add(("- Parent folder: {0}" -f $parentName))
  $compiled.Add(("- Characters: {0}" -f $charCount))
  $compiled.Add("")
  $compiled.Add("----- BEGIN POST TEXT -----")
  $compiled.Add($normalizedText.Trim())
  $compiled.Add("----- END POST TEXT -----")
  $compiled.Add("")

  $index += 1
}

$manifestPath = Join-Path $compiledDir "blog-corpus-manifest.csv"
$compiledPath = Join-Path $compiledDir "all-blog-posts.md"
$statsPath = Join-Path $analysisDir "corpus-stats.md"

$rows | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8
$compiled | Set-Content -LiteralPath $compiledPath -Encoding UTF8

$totalChars = ($rows | Measure-Object -Property char_count -Sum).Sum
$avgChars = 0
if ($rows.Count -gt 0) {
  $avgChars = [math]::Round($totalChars / $rows.Count, 1)
}

$stats = @()
$stats += "# Blog corpus stats"
$stats += ""
$stats += "- Source label: $SourceLabel"
$stats += "- Text files: $($rows.Count)"
$stats += "- Total characters: $totalChars"
$stats += "- Average characters: $avgChars"
$stats += "- Manifest: $manifestPath"
$stats += "- Compiled markdown: $compiledPath"
$stats += ""
$stats += "## Files"
foreach ($row in $rows) {
  $stats += ("- {0}. {1} ({2} chars)" -f $row.seq, $row.file_name, $row.char_count)
}
$stats | Set-Content -LiteralPath $statsPath -Encoding UTF8

[PSCustomObject]@{
  Source = $source.Path
  TextFiles = $rows.Count
  RawCopies = $rawDir
  Manifest = $manifestPath
  Compiled = $compiledPath
  Stats = $statsPath
}
