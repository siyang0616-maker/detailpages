param(
  [string]$StrategySource = "C:\Users\home\Documents\detailpages\blog-writing-corpus\analysis\franchise-blog-and-ai-briefing-strategy.md",
  [string]$SkillDir = "C:\Users\home\.codex\skills\franchise-detail-page"
)

$ErrorActionPreference = "Stop"

$skill = Resolve-Path -LiteralPath $SkillDir
$source = Resolve-Path -LiteralPath $StrategySource
$skillMd = Join-Path $skill.Path "SKILL.md"
$references = Join-Path $skill.Path "references"
$targetReference = Join-Path $references "blog-writing-strategy.md"

if (-not (Test-Path -LiteralPath $skillMd)) {
  throw "Missing SKILL.md: $skillMd"
}
if (-not (Test-Path -LiteralPath $references)) {
  New-Item -ItemType Directory -Force -Path $references | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $skill.Path "SKILL.md.bak-$timestamp"
Copy-Item -LiteralPath $skillMd -Destination $backup
Copy-Item -LiteralPath $source.Path -Destination $targetReference -Force

$content = Get-Content -Raw -LiteralPath $skillMd
$marker = "## Blog Writing And AI Briefing Direction"
$section = @"

## Blog Writing And AI Briefing Direction

When the user asks to improve franchise blog writing, use previous Naver blog drafts, create blog-connected detail pages, or optimize direction for Naver search / AI briefing style discovery, read references/blog-writing-strategy.md before planning.

Use the user's existing blog drafts as reference material, not as a verbatim template. Preserve the practical consulting viewpoint, but improve structure with direct subheadings, first-answer openings, store-level checks, balanced risk notes, and fact-safe language.

Avoid generic greetings, pure brand praise, duplicated post structure, exaggerated success language, and unsupported claims. Prefer realistic advice, provided facts, "확인 필요" markers, and consumer-trust language that feels like field experience rather than an ad.
"@

if ($content -notlike "*$marker*") {
  Add-Content -LiteralPath $skillMd -Encoding UTF8 -Value $section
} else {
  $repaired = $content -replace "eferences/blog-writing-strategy\.md", "references/blog-writing-strategy.md"
  if ($repaired -ne $content) {
    Set-Content -LiteralPath $skillMd -Encoding UTF8 -Value $repaired
  }
}

[PSCustomObject]@{
  Skill = $skill.Path
  Backup = $backup
  Reference = $targetReference
  UpdatedSkill = $skillMd
}
