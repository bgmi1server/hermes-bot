@echo off
setlocal

echo Activating virtual environment...
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo Failed to activate virtual environment.
    pause
    exit /b %ERRORLEVEL%
)

echo Starting bot...
set PYTHONUNBUFFERED=1
python bot.py
if %ERRORLEVEL% neq 0 (
    echo Bot exited with an error.
    pause
    exit /b %ERRORLEVEL%
)

pause
