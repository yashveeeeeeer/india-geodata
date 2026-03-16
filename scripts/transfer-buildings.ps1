<#
.SYNOPSIS
    Resumable building footprint transfer script.
    Transfers assets from ramSeraph/indian_buildings to yashveeeeeer/india-geodata.
    Validates file sizes, deletes corrupt uploads, retries with backoff.

.PARAMETER SourceTag
    Source release tag (urban, MSBI, GOBI-2023)

.PARAMETER DestTag
    Destination release tag (buildings/urban, buildings/microsoft, buildings/google)

.PARAMETER MaxRetries
    Max retry attempts per file (default 5)

.EXAMPLE
    .\transfer-buildings.ps1 -SourceTag "urban" -DestTag "buildings/urban"
    .\transfer-buildings.ps1 -SourceTag "MSBI" -DestTag "buildings/microsoft"
    .\transfer-buildings.ps1 -SourceTag "GOBI-2023" -DestTag "buildings/google"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$SourceTag,

    [Parameter(Mandatory=$true)]
    [string]$DestTag,

    [int]$MaxRetries = 5
)

$ErrorActionPreference = "Continue"
$srcRepo = "ramSeraph/indian_buildings"
$destRepo = "yashveeeeeer/india-geodata"
$tempDir = "temp_downloads"
$sizeTolerance = 0.01  # 1% tolerance for size comparison

if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir | Out-Null }

function Format-Size($bytes) {
    if ($bytes -ge 1GB) { return "$([math]::Round($bytes/1GB, 2)) GB" }
    if ($bytes -ge 1MB) { return "$([math]::Round($bytes/1MB, 1)) MB" }
    return "$([math]::Round($bytes/1KB, 1)) KB"
}

function Get-SourceAssets {
    $json = gh api "repos/$srcRepo/releases/tags/$SourceTag" --jq '[.assets[] | {name: .name, size: .size}]'
    return $json | ConvertFrom-Json
}

function Get-DestAssets {
    $releaseExists = gh api "repos/$destRepo/releases/tags/$DestTag" 2>&1
    if ($LASTEXITCODE -ne 0) { return @() }
    $json = gh api "repos/$destRepo/releases/tags/$DestTag" --jq '[.assets[] | {name: .name, size: .size, id: .id}]'
    return $json | ConvertFrom-Json
}

function Ensure-Release {
    $check = gh api "repos/$destRepo/releases/tags/$DestTag" 2>&1
    if ($LASTEXITCODE -ne 0) {
        $titles = @{
            "buildings/urban" = "Urban Buildings India"
            "buildings/microsoft" = "Microsoft Building Footprints India"
            "buildings/google" = "Google Open Buildings India"
        }
        $title = if ($titles.ContainsKey($DestTag)) { $titles[$DestTag] } else { $DestTag }
        Write-Host "Creating release '$DestTag'..."
        gh release create $DestTag --repo $destRepo --title $title --notes "Building footprints transferred from $srcRepo ($SourceTag)" 2>&1
    }
}

# --- MAIN ---
Write-Host "============================================="
Write-Host "  Building Transfer: $SourceTag -> $DestTag"
Write-Host "============================================="
Write-Host ""

Ensure-Release

Write-Host "Fetching asset lists..."
$srcAssets = Get-SourceAssets
$destAssets = Get-DestAssets

$srcTotal = ($srcAssets | Measure-Object -Property size -Sum).Sum
Write-Host "Source: $($srcAssets.Count) files, $(Format-Size $srcTotal)"

# Identify: missing, corrupt (wrong size), and OK
$toTransfer = @()
$toDelete = @()
$okCount = 0

foreach ($s in $srcAssets) {
    $d = $destAssets | Where-Object { $_.name -eq $s.name }
    if (-not $d) {
        $toTransfer += $s
    } elseif ([math]::Abs($d.size - $s.size) / $s.size -gt $sizeTolerance) {
        $toDelete += [PSCustomObject]@{ name = $d.name; id = $d.id; ourSize = $d.size; expectedSize = $s.size }
        $toTransfer += $s
    } else {
        $okCount++
    }
}

Write-Host "OK (correct size): $okCount"
Write-Host "Corrupt (wrong size): $($toDelete.Count)"
Write-Host "Missing: $($toTransfer.Count - $toDelete.Count)"
Write-Host "Total to transfer: $($toTransfer.Count)"
Write-Host ""

# Delete corrupt assets
if ($toDelete.Count -gt 0) {
    Write-Host "--- Deleting $($toDelete.Count) corrupt assets ---"
    foreach ($bad in $toDelete) {
        Write-Host "  Deleting $($bad.name) ($(Format-Size $bad.ourSize) instead of $(Format-Size $bad.expectedSize))..."
        gh api -X DELETE "repos/$destRepo/releases/assets/$($bad.id)" 2>&1 | Out-Null
    }
    Write-Host "  Deleted all corrupt assets."
    Write-Host ""
}

if ($toTransfer.Count -eq 0) {
    Write-Host "Nothing to transfer - all files are correct!"
    exit 0
}

# Sort by size (smallest first for quick progress)
$toTransfer = $toTransfer | Sort-Object size

$total = $toTransfer.Count
$succeeded = 0
$failed = @()
$transferredBytes = 0
$i = 0

Write-Host "--- Starting transfer of $total files ---"
Write-Host ""

foreach ($asset in $toTransfer) {
    $i++
    $name = $asset.name
    $expectedSize = $asset.size
    $localPath = Join-Path $tempDir $name
    $success = $false

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        $backoff = [math]::Min(30 * [math]::Pow(2, $attempt - 1), 300)

        Write-Host "[$i/$total] $name ($(Format-Size $expectedSize)) - attempt $attempt/$MaxRetries"

        # Clean up any leftover
        if (Test-Path $localPath) {
            Remove-Item $localPath -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }

        # Download
        Write-Host "  Downloading..."
        $dlResult = gh release download $SourceTag --repo $srcRepo --pattern $name --dir $tempDir --clobber 2>&1

        if (-not (Test-Path $localPath)) {
            Write-Host "  Download failed: $dlResult"
            Write-Host "  Waiting ${backoff}s..."
            Start-Sleep -Seconds $backoff
            continue
        }

        $actualSize = (Get-Item $localPath).Length
        Write-Host "  Downloaded: $(Format-Size $actualSize)"

        # Verify download size
        if ([math]::Abs($actualSize - $expectedSize) / $expectedSize -gt $sizeTolerance) {
            Write-Host "  SIZE MISMATCH: got $(Format-Size $actualSize), expected $(Format-Size $expectedSize)"
            Remove-Item $localPath -Force -ErrorAction SilentlyContinue
            Write-Host "  Waiting ${backoff}s..."
            Start-Sleep -Seconds $backoff
            continue
        }

        # Upload
        Write-Host "  Uploading..."
        $ulResult = gh release upload $DestTag $localPath --repo $destRepo 2>&1
        $ulStr = $ulResult | Out-String

        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Upload OK"
            Remove-Item $localPath -Force -ErrorAction SilentlyContinue
            $success = $true
            $succeeded++
            $transferredBytes += $actualSize
            break
        } elseif ($ulStr -match "already exists") {
            Write-Host "  Already exists (correct size) - skipping"
            Remove-Item $localPath -Force -ErrorAction SilentlyContinue
            $success = $true
            $succeeded++
            break
        } else {
            Write-Host "  Upload failed: $ulStr"
            Remove-Item $localPath -Force -ErrorAction SilentlyContinue
            Write-Host "  Waiting ${backoff}s..."
            Start-Sleep -Seconds $backoff
        }
    }

    if (-not $success) {
        Write-Host "  FAILED after $MaxRetries attempts"
        $failed += $name
    }
    Write-Host ""
}

# Final verification
Write-Host "============================================="
Write-Host "  Transfer Summary"
Write-Host "============================================="
Write-Host "Succeeded: $succeeded / $total"
Write-Host "Transferred: $(Format-Size $transferredBytes)"
if ($failed.Count -gt 0) {
    Write-Host "FAILED ($($failed.Count)):"
    $failed | ForEach-Object { Write-Host "  $_" }
}
Write-Host ""

# Verify final state
Write-Host "Running final verification..."
$finalSrc = Get-SourceAssets
$finalDest = Get-DestAssets
$mismatches = 0
foreach ($s in $finalSrc) {
    $d = $finalDest | Where-Object { $_.name -eq $s.name }
    if (-not $d) {
        Write-Host "  MISSING: $($s.name)"
        $mismatches++
    } elseif ([math]::Abs($d.size - $s.size) / $s.size -gt $sizeTolerance) {
        Write-Host "  CORRUPT: $($s.name) ($(Format-Size $d.size) vs $(Format-Size $s.size))"
        $mismatches++
    }
}

if ($mismatches -eq 0) {
    Write-Host "VERIFIED: All $($finalSrc.Count) files match! Transfer complete."
} else {
    Write-Host "WARNING: $mismatches files still need fixing. Re-run this script."
}
Write-Host "============================================="
