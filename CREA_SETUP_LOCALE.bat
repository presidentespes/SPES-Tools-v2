@echo off
setlocal
cd /d "%~dp0"

echo Verifica Python 3.12...
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 non disponibile. Usa GitHub Actions oppure installa Python 3.12.
  pause
  exit /b 1
)

if not exist .venv py -3.12 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
pytest -q
if errorlevel 1 goto :error
pyinstaller --noconfirm SPES_Tools.spec
if errorlevel 1 goto :error

set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo Inno Setup 6 non trovato. L'eseguibile e stato creato in dist\SPES_Tools.exe
  pause
  exit /b 0
)
"%ISCC%" installer\SPES_Tools.iss
if errorlevel 1 goto :error

echo Installer creato in installer_output\Setup_SPES_Tools.exe
pause
exit /b 0

:error
echo Compilazione non riuscita.
pause
exit /b 1
