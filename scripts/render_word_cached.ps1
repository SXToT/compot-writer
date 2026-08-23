param(
    [Parameter(Mandatory = $true)][string]$InputDocx,
    [Parameter(Mandatory = $true)][string]$OutputPdf,
    [string]$CacheFile = ""
)

$ErrorActionPreference = "Stop"
$inputPath = [System.IO.Path]::GetFullPath($InputDocx)
$outputPath = [System.IO.Path]::GetFullPath($OutputPdf)
if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
    throw "Input DOCX not found: $inputPath"
}

if ([string]::IsNullOrWhiteSpace($CacheFile)) {
    $cachePath = "$outputPath.sha256"
}
else {
    $cachePath = [System.IO.Path]::GetFullPath($CacheFile)
}

$hash = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash
if ((Test-Path -LiteralPath $outputPath -PathType Leaf) -and (Test-Path -LiteralPath $cachePath -PathType Leaf)) {
    $cachedHash = (Get-Content -LiteralPath $cachePath -Raw).Trim()
    if ($cachedHash -eq $hash) {
        [pscustomobject]@{
            OutputPdf = $outputPath
            CacheHit = $true
            Sha256 = $hash
        } | ConvertTo-Json
        exit 0
    }
}

$renderScript = Join-Path $PSScriptRoot "render_word.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $renderScript -InputDocx $inputPath -OutputPdf $outputPath
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
$cacheDirectory = [System.IO.Path]::GetDirectoryName($cachePath)
if (-not (Test-Path -LiteralPath $cacheDirectory)) {
    New-Item -ItemType Directory -Path $cacheDirectory | Out-Null
}
[System.IO.File]::WriteAllText($cachePath, $hash, [System.Text.UTF8Encoding]::new($false))
[pscustomobject]@{
    OutputPdf = $outputPath
    CacheHit = $false
    Sha256 = $hash
} | ConvertTo-Json
