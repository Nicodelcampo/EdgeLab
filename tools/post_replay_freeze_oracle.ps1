# tools/post_replay_freeze_oracle.ps1
# Script PowerShell estrictamente read-only para ejecutar INMEDIATAMENTE después de cerrar NT8.
# NO usa Python. NO abre la base de datos con ningún conector SQLite.
# Captura bytes físicos, calcula SHA-256, crea copia de preservación, marca Read-Only y genera manifiesto JSON inicial.

param(
    [string]$DbPath = "data\nt8_oracles\hft_zones_nq_v2_native_termination_fresh.sqlite",
    [string]$PreservationDir = "data\nt8_oracles\preservation"
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "EdgeLab — Captura y Congelamiento Físico del Oracle HFT V2 NT8" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Resolver ruta absoluta
$repoRoot = (Get-Item -Path $PSScriptRoot).Parent.FullName
$targetFile = Join-Path $repoRoot $DbPath

Write-Host "[1/6] Comprobando existencia del archivo exportado..."
if (-not (Test-Path -LiteralPath $targetFile)) {
    Write-Host "ERROR: No se encontró el archivo exportado por NT8:" -ForegroundColor Red
    Write-Host "       $targetFile" -ForegroundColor Yellow
    Write-Host "Verifique que NinjaTrader 8 haya completado el replay y cerrado el archivo." -ForegroundColor Yellow
    exit 1
}

# 2. Verificar que no esté bloqueado (NT8 debe estar cerrado)
Write-Host "[2/6] Verificando que el archivo no esté bloqueado..."
try {
    $fileStream = [System.IO.File]::Open($targetFile, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    $fileStream.Close()
} catch {
    Write-Host "ERROR: El archivo sigue bloqueado por otro proceso (posiblemente NinjaTrader 8 sigue abierto)." -ForegroundColor Red
    Write-Host "       Cierre NinjaTrader 8 por completo antes de continuar." -ForegroundColor Yellow
    exit 2
}

# 3. Registrar bytes físicos
Write-Host "[3/6] Registrando tamaño físico en bytes..."
$item = Get-Item -LiteralPath $targetFile
$fileSize = $item.Length
if ($fileSize -le 0) {
    Write-Host "ERROR: El archivo SQLite está vacío (0 bytes)." -ForegroundColor Red
    exit 3
}
Write-Host "       Tamaño: $fileSize bytes ($([Math]::Round($fileSize / 1MB, 2)) MB)" -ForegroundColor Green

# 4. Calcular SHA-256 inicial inmediatamente después del cierre de NT8
Write-Host "[4/6] Calculando SHA-256 físico del SQLite original..."
$hashResult = Get-FileHash -LiteralPath $targetFile -Algorithm SHA256
$originalSha256 = $hashResult.Hash.ToLower()
Write-Host "       SHA-256: $originalSha256" -ForegroundColor Yellow

# 5. Copiar a ubicación de preservación
Write-Host "[5/6] Creando copia de preservación..."
$targetPreservationDir = Join-Path $repoRoot $PreservationDir
if (-not (Test-Path -LiteralPath $targetPreservationDir)) {
    New-Item -ItemType Directory -Path $targetPreservationDir -Force | Out-Null
}
$timestampStr = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$preservationFileName = "$([System.IO.Path]::GetFileNameWithoutExtension($targetFile))_preserved_$timestampStr.sqlite"
$preservationPath = Join-Path $targetPreservationDir $preservationFileName

Copy-Item -LiteralPath $targetFile -Destination $preservationPath -Force
$preservationHashResult = Get-FileHash -LiteralPath $preservationPath -Algorithm SHA256
$preservationSha256 = $preservationHashResult.Hash.ToLower()

if ($originalSha256 -ne $preservationSha256) {
    Write-Host "FATAL: El hash de la copia de preservación no coincide con el original." -ForegroundColor Red
    exit 4
}
Write-Host "       Preservado en: $preservationPath" -ForegroundColor Green
Write-Host "       Hash copia:    $preservationSha256 (MATCH EXACTO)" -ForegroundColor Green

# 6. Marcar original como sólo lectura y generar manifiesto inicial
Write-Host "[6/6] Marcando original como solo lectura y emitiendo manifiesto físico..."
try {
    $item.IsReadOnly = $true
    Write-Host "       Atributo Read-Only activado en el archivo original." -ForegroundColor Green
} catch {
    Write-Host "       AVISO: No se pudo asignar flag ReadOnly en el sistema de archivos." -ForegroundColor DarkYellow
}

$manifest = [ordered]@{
    manifest_format = "edgelab_physical_oracle_preflight_v1"
    created_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    oracle_file_name = [System.IO.Path]::GetFileName($targetFile)
    oracle_relative_path = $DbPath
    file_size_bytes = $fileSize
    sha256 = $originalSha256
    preservation_copy_path = "$PreservationDir\$preservationFileName"
    preservation_sha256 = $preservationSha256
    is_read_only = $item.IsReadOnly
    python_writes_after_export = $false
    holdout_accessed = $false
    provenance_status = "PRESERVED_BEFORE_PYTHON_ACCESS"
}

$manifestJsonPath = [System.IO.Path]::ChangeExtension($targetFile, ".preflight_manifest.json")
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestJsonPath -Encoding utf8

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "CAPTURA COMPLETADA CON ÉXITO" -ForegroundColor Green
Write-Host "Archivo:     $targetFile" -ForegroundColor White
Write-Host "Tamaño:      $fileSize bytes" -ForegroundColor White
Write-Host "SHA-256:     $originalSha256" -ForegroundColor Yellow
Write-Host "Manifiesto:  $manifestJsonPath" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan
