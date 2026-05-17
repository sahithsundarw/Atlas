# Atlas startup script for Windows PowerShell
# Run from the travel-assistant directory

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $dir

Write-Host "Starting Atlas backend on http://localhost:8000 ..."
$backend = Start-Process -NoNewWindow -PassThru python -ArgumentList "-m uvicorn api:app --port 8000 --workers 1"

Start-Sleep -Seconds 2

Write-Host "Starting Atlas frontend on http://localhost:3000 ..."
$frontend = Start-Process -NoNewWindow -PassThru python -ArgumentList "-m http.server 3000"

Start-Sleep -Seconds 1
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "  Atlas frontend → http://localhost:3000"
Write-Host "  Atlas backend  → http://localhost:8000/health"
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers."

try {
    Wait-Process -Id $backend.Id
} finally {
    Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue
    Write-Host "Stopped."
}
