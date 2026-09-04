@echo off
echo ============================================
echo  Sticky Note Generator - Launching UI
echo ============================================
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" -m streamlit run app.py
) else (
    python -m streamlit run app.py
)
pause