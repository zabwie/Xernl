@echo off
echo Building main.py into executable...

REM Install PyInstaller if not already installed
pip install pyinstaller

REM Build the executable
pyinstaller --onefile --noconsole --name Xernl main.py

echo Build complete!
echo Executable created in dist\Xernl.exe
pause 