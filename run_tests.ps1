# run_tests.ps1 — Run full test suite using the workspace venv
# Usage:  .\run_tests.ps1
#         .\run_tests.ps1 -File tests/test_models.py
#         .\run_tests.ps1 -k "G-01"

param(
    [string]$File  = "tests",
    [string]$k     = "",
    [switch]$Fast              # skip slow PDF tests
)

$python = "D:/OneDrive/Athiq/MSFT/Agents League/.venv/Scripts/python.exe"

$args = @("-m", "pytest", $File, "-v", "--tb=short")

if ($k) { $args += @("-k", $k) }
if ($Fast) { $args += @("--ignore=tests/test_pdf_generation.py") }

Write-Host ""
Write-Host "=== CertPrep Test Suite ===" -ForegroundColor Cyan
Write-Host "Python  : $python"
Write-Host "Running : $File"
if ($k) { Write-Host "Filter  : $k" }
Write-Host ""

& $python @args

$exit = $LASTEXITCODE
if ($exit -eq 0) {
    Write-Host ""
    Write-Host "ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "SOME TESTS FAILED (exit $exit)" -ForegroundColor Red
}
exit $exit
