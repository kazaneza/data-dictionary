@echo off
:loop
cd /d "C:\Users\gkazaneza\Desktop\data_dictionary\backend"
C:\Users\gkazaneza\myenv\Scripts\python.exe main.py >> C:\scripts\backend_log.txt 2>&1
echo %date% %time% Backend crashed, restarting... >> C:\scripts\backend_log.txt 2>&1
timeout /t 5
goto loop