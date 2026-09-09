@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%" || goto :fail

set "REPO_ROOT=%PROJECT_ROOT%"
for %%I in ("%PROJECT_ROOT%\..") do if /I "%%~nxI"==".worktrees" for %%J in ("%%~fI\..") do set "REPO_ROOT=%%~fJ"
for /f "usebackq delims=" %%I in (`git -C "%PROJECT_ROOT%" rev-parse --git-common-dir 2^>nul`) do for %%J in ("%%I\..") do set "REPO_ROOT=%%~fJ"

if not defined FORMPILOT_UV (
    if exist "%REPO_ROOT%\.tools\uv\uv.exe" set "FORMPILOT_UV=%REPO_ROOT%\.tools\uv\uv.exe"
)
set "UV_PYTHON_INSTALL_DIR=%REPO_ROOT%\.tools\python"
set "UV_CACHE_DIR=%REPO_ROOT%\.cache\uv"
set "FORMPILOT_TMP=%PROJECT_ROOT%\.tmp"
set "TEMP=%FORMPILOT_TMP%"
set "TMP=%FORMPILOT_TMP%"

if not exist "%FORMPILOT_UV%" (
    echo Portable uv was not found at "%FORMPILOT_UV%". Set FORMPILOT_UV to a uv executable.
    goto :fail
)
if not exist "%FORMPILOT_TMP%" mkdir "%FORMPILOT_TMP%" || goto :fail
if not exist "%UV_CACHE_DIR%" mkdir "%UV_CACHE_DIR%" || goto :fail

if defined FORMPILOT_PYTHON (
    call "%FORMPILOT_UV%" venv --python "%FORMPILOT_PYTHON%" .venv || goto :fail
) else (
    call "%FORMPILOT_UV%" venv --managed-python --python 3.11 .venv || goto :fail
)
if not exist ".venv\Scripts\activate.bat" goto :fail
call ".venv\Scripts\activate.bat" || goto :fail
call "%FORMPILOT_UV%" pip install -r requirements.txt || goto :fail
endlocal
exit /b 0

:fail
endlocal
exit /b 1
