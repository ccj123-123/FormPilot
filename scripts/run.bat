@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%" || goto :fail

set "REPO_ROOT=%PROJECT_ROOT%"
for %%I in ("%PROJECT_ROOT%\..") do if /I "%%~nxI"==".worktrees" for %%J in ("%%~fI\..") do set "REPO_ROOT=%%~fJ"
for /f "usebackq delims=" %%I in (`git -C "%PROJECT_ROOT%" rev-parse --git-common-dir 2^>nul`) do for %%J in ("%%I\..") do set "REPO_ROOT=%%~fJ"

set "FORMPILOT_TMP=%CD%\.tmp"
set "TEMP=%FORMPILOT_TMP%"
set "TMP=%FORMPILOT_TMP%"
set "GRADIO_TEMP_DIR=%FORMPILOT_TMP%\gradio"
set "GRADIO_ANALYTICS_ENABLED=False"
set "XDG_CACHE_HOME=%FORMPILOT_TMP%\cache"
set "HF_HOME=%FORMPILOT_TMP%\cache\huggingface"
set "MPLCONFIGDIR=%FORMPILOT_TMP%\cache\matplotlib"
set "PIP_CACHE_DIR=%FORMPILOT_TMP%\cache\pip"
set "PYTHONPYCACHEPREFIX=%FORMPILOT_TMP%\pycache"
if not exist "%FORMPILOT_TMP%" mkdir "%FORMPILOT_TMP%"
if not exist "%GRADIO_TEMP_DIR%" mkdir "%GRADIO_TEMP_DIR%"
if not exist "%XDG_CACHE_HOME%" mkdir "%XDG_CACHE_HOME%"

if not defined OPENSCAD_BIN (
    if exist "%REPO_ROOT%\.tools" for /r "%REPO_ROOT%\.tools" %%I in (openscad.com) do if exist "%%I" if not defined OPENSCAD_BIN set "OPENSCAD_BIN=%%~fI"
)
if not defined OPENSCAD_BIN (
    echo Portable OpenSCAD was not found under "%REPO_ROOT%\.tools". Set OPENSCAD_BIN to an OpenSCAD executable.
    goto :fail
)

if not exist ".venv\Scripts\activate.bat" goto :fail
call .venv\Scripts\activate.bat || goto :fail
python app.py || goto :fail
endlocal
exit /b 0

:fail
endlocal
exit /b 1
