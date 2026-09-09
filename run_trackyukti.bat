@echo off
title TRACK YUKTI - WCR Railway Block Planner
echo ======================================================================
echo Launching TRACK YUKTI -- AI-Powered Railway Block Planning ^& Optimization System
echo West Central Railway (WCR) - Jabalpur Division
echo ======================================================================
cd /d "%~dp0"
"%LOCALAPPDATA%\Programs\Python\Python311\python.exe" -m streamlit run app.py --server.port 8501
pause
