@echo off
title SwitchNaija
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed on this computer.
  echo Install it from https://www.python.org/downloads/ and tick "Add Python to PATH", then double-click this file again.
  pause
  exit /b
)
echo Installing SwitchNaija (first time takes 2 to 3 minutes)...
python -m pip install -r requirements.txt
echo Starting the app. It will open in your browser at http://localhost:8501
python -m streamlit run app/streamlit_app.py
pause
