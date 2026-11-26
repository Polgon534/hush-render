# SUBIR-A-GITHUB.ps1 - Sube esta carpeta (hush-render) a GitHub. La primera vez crea el repositorio; despues solo actualiza.
# Uso (PowerShell):  cd D:\SHORTS-PROYECTO\shorts-proyecto\_github\hush-render ; powershell -ExecutionPolicy Bypass -File .\SUBIR-A-GITHUB.ps1
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
New-Item -ItemType Directory -Force -Path ".github\workflows" | Out-Null
Copy-Item -Force "_workflow\satisfy.yml" ".github\workflows\satisfy.yml"
if (-not (Test-Path ".git")) {
    git init -q
    git branch -M main
}
git add -A
git -c user.name="Pol" -c user.email="pol@users.noreply.github.com" commit -q -m "hush-render: actualizacion desde el PC" 2>$null
$remoto = (git remote) -contains "origin"
if (-not $remoto) {
    $ErrorActionPreference = "Continue"
    $existe = $false; try { gh repo view Polgon534/hush-render 2>$null | Out-Null; $existe = ($LASTEXITCODE -eq 0) } catch { }
    if (-not $existe) {
        gh repo create Polgon534/hush-render --public --source . --remote origin --push
    } else {
        git remote add origin https://github.com/Polgon534/hush-render.git
        git push -u origin main
    }
} else {
    $ErrorActionPreference = "Continue"
    git pull --rebase -q origin main   # GitHub guarda cada noche los registros: primero se traen
    git push -u origin main
}
Write-Host "Listo: https://github.com/Polgon534/hush-render" -ForegroundColor Green
