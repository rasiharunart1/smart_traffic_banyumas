@echo off
setlocal
set APPNAME=SmartTrafficCounter
set MAIN=modern_vehicle_counter.py

REM 1) Create/activate venv
if not exist .venv (
  echo [*] Creating virtual environment...
  py -3 -m venv .venv || python -m venv .venv
)
call .venv\Scripts\activate

REM 2) Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM 3) Build (onedir recommended for Torch/Ultralytics)
echo [*] Building onedir executable...
pyinstaller "%MAIN%" ^
  --name "%APPNAME%" ^
  --onedir ^
  --windowed ^
  --noconfirm ^
  --collect-all ultralytics ^
  --collect-all torch ^
  --collect-all torchvision ^
  --collect-all cv2 ^
  --collect-all PIL

REM 4) Copy model and settings into dist folder (optional)
if exist yolo11n.pt (
  copy /Y "yolo11n.pt" "dist\%APPNAME%\" >nul
)
if exist settings.json (
  copy /Y "settings.json" "dist\%APPNAME%\" >nul
)

echo.
echo [✓] Build complete:
echo     dist\%APPNAME%\%APPNAME%.exe
echo.
echo Tip: Ensure settings.json points to "yolo11n.pt" located next to the EXE.
pause