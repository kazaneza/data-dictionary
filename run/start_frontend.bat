@echo off
echo %date% %time% Frontend starting >> C:\Users\gkazaneza\Desktop\frontend_log.txt 2>&1
:loop
cd /d "C:\Users\gkazaneza\Desktop\data_dictionary"
"C:\Program Files\nodejs\npm.cmd" run dev >> C:\Users\gkazaneza\Desktop\frontend_log.txt 2>&1
echo %date% %time% Frontend crashed, restarting... >> C:\Users\gkazaneza\Desktop\frontend_log.txt 2>&1
timeout /t 5
goto loop