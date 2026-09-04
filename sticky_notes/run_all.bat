@echo off
echo ============================================
echo  Sticky Note Generator - Full Pipeline
echo ============================================
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" run_all.py
) else (
    python run_all.py
)
echo.
echo ============================================
echo  Pipeline complete! Run the UI with:
echo  streamlit run app.py
echo ============================================
pause