# Script de ejecucion continua para corrida de 65 sesiones H2 + Registro + Auto-suspension
Set-Location -Path $PSScriptRoot\..

$LogPath = "latest_logs\run_h2_65s.log"
"==================================================" | Out-File -FilePath $LogPath -Encoding utf8
"INICIO CORRIDA 65 SESIONES H2: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $LogPath -Append -Encoding utf8
"==================================================" | Out-File -FilePath $LogPath -Append -Encoding utf8

Write-Host "Iniciando corrida de 65 sesiones de H2..." -ForegroundColor Cyan

# 1. Ejecutar el runner de 65 sesiones
& .venv\Scripts\python.exe tools\rechazo_clusters_nq.py --sesiones 65 --desde "2026-03-23 22:00" --out data\nt8_oracles\rechazo_clusters_nq_65s.json 2>&1 | Tee-Object -FilePath $LogPath -Append

$RunnerExitCode = $LASTEXITCODE

if ($RunnerExitCode -eq 0 -and (Test-Path "data\nt8_oracles\rechazo_clusters_nq_65s.json")) {
    Write-Host "`nCorrida finalizada exitosamente. Ejecutando registro para Claude..." -ForegroundColor Green
    "REGISTRO AUTOMATICO: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $LogPath -Append -Encoding utf8
    
    # 2. Registrar resultados, actualizar handoff y commitear a git
    & .venv\Scripts\python.exe tools\registrar_resultado_h2_65s.py 2>&1 | Tee-Object -FilePath $LogPath -Append
    
    Write-Host "`nTodo registrado y commiteado. Procediendo a suspender el equipo en 15 segundos..." -ForegroundColor Yellow
    "SUSPENDIENDO EQUIPO: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $LogPath -Append -Encoding utf8
    
    Start-Sleep -Seconds 15
    
    # 3. Suspender la computadora
    rundll32.exe powrprof.dll,SetSuspendState 0,1,0
} else {
    Write-Host "`nERROR: El runner termino con codigo $RunnerExitCode o no genero el JSON esperado." -ForegroundColor Red
    "FALLO EN CORRIDA: Codigo $RunnerExitCode a las $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $LogPath -Append -Encoding utf8
}
