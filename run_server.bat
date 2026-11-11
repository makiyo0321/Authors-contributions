@echo off
cd /d "%~dp0"
python author_contributions.py
if errorlevel 1 pause
