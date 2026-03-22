@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "VENV_DIR=%SCRIPT_DIR%\.venv"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%\requirements.txt"

call :find_host_python || exit /b 1

if not exist "%VENV_DIR%" (
    echo Creating virtual environment in %VENV_DIR%
    call :run_host_python -m venv "%VENV_DIR%" || exit /b 1
)

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
if not exist "%VENV_PYTHON%" set "VENV_PYTHON=%VENV_DIR%\Scripts\python"
if not exist "%VENV_PYTHON%" (
    echo Unable to locate the virtual environment Python interpreter.
    exit /b 1
)

"%VENV_PYTHON%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Bootstrapping pip in %VENV_DIR%
    "%VENV_PYTHON%" -m ensurepip --upgrade || exit /b 1
)

if exist "%REQUIREMENTS_FILE%" (
    set "CURRENT_HASH="
    set "PREVIOUS_HASH="
    call :get_file_hash "%REQUIREMENTS_FILE%" CURRENT_HASH || exit /b 1
    if exist "%VENV_DIR%\.requirements.sha256" set /p PREVIOUS_HASH=<"%VENV_DIR%\.requirements.sha256"
    if not "!CURRENT_HASH!"=="!PREVIOUS_HASH!" (
        echo Installing dependencies from %REQUIREMENTS_FILE%
        "%VENV_PYTHON%" -m pip install --upgrade pip || exit /b 1
        "%VENV_PYTHON%" -m pip install -r "%REQUIREMENTS_FILE%" || exit /b 1
        >"%VENV_DIR%\.requirements.sha256" echo(!CURRENT_HASH!
    )
)

"%VENV_PYTHON%" -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo Missing Python Tk support ^(`tkinter`^).
    echo Install the official CPython build from python.org, which includes Tk.
    echo Then recreate the virtual environment and rerun this launcher.
    exit /b 1
)

"%VENV_PYTHON%" "%SCRIPT_DIR%\src\waswv.py" %*
exit /b %errorlevel%

:find_host_python
py -3 -V >nul 2>&1
if not errorlevel 1 (
    set "HOST_PYTHON_CMD=py -3"
    exit /b 0
)

python -V >nul 2>&1
if not errorlevel 1 (
    set "HOST_PYTHON_CMD=python"
    exit /b 0
)

echo Python 3.12+ was not found on PATH.
echo Install Python from python.org or the Microsoft Store and rerun this launcher.
exit /b 1

:run_host_python
if "%HOST_PYTHON_CMD%"=="py -3" (
    py -3 %*
) else (
    %HOST_PYTHON_CMD% %*
)
exit /b %errorlevel%

:get_file_hash
set "WASWV_HASH_FILE=%~1"
set "HASH_VALUE="
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $env:WASWV_HASH_FILE; $hash.Hash.ToLower()"`) do set "HASH_VALUE=%%H"
if not defined HASH_VALUE exit /b 1
set "%~2=%HASH_VALUE%"
exit /b 0
