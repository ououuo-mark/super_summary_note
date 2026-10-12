@echo off
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON_EXE=%SCRIPT_DIR%python_env\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Python not found!
    pause
    exit /b 1
)

echo Server is starting...
echo.

start /B "" "%PYTHON_EXE%" "%SCRIPT_DIR%web_server.py"

timeout /t 3 /nobreak >nul

echo Opening browser...
start http://127.0.0.1:8000/

echo.
echo Server is running. Close this window to stop the server.
echo.

:loop
timeout /t 1 /nobreak >nul
goto loop