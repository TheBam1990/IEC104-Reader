@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto failed
call .venv\Scripts\activate.bat
if errorlevel 1 goto failed
python -m pip install --upgrade pip
if errorlevel 1 goto failed
python -m pip install -r requirements-build.txt
if errorlevel 1 goto failed
python -m unittest discover -s tests -v
if errorlevel 1 goto failed
python -m PyInstaller --clean --noconfirm IEC104-Reader.spec
if errorlevel 1 goto failed
python tools\package_windows.py
if errorlevel 1 goto failed
echo.
echo Fertig: dist\IEC104-Reader\IEC104-Reader.exe
echo Den gesamten Programmordner behalten, nicht nur die EXE kopieren.
pause
exit /b 0
:failed
echo Build fehlgeschlagen. Es wurde kein neues Paket freigegeben.
pause
exit /b 1
