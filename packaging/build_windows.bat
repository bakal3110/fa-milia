@echo off
rem ================================================================
rem  Budowanie programu Fa milia dla Windows.
rem
rem  Wymagania: Python 3.12 lub nowszy z python.org
rem  (podczas instalacji zaznacz "Add python.exe to PATH").
rem
rem  Uzycie (dwuklik albo z wiersza polecen):
rem    build_windows.bat          - jeden plik: dist\Fa milia.exe
rem    build_windows.bat folder   - folder: dist\Fa milia\Fa milia.exe
rem ================================================================
setlocal
cd /d "%~dp0\.."

where py >nul 2>nul
if errorlevel 1 (
    echo Nie znaleziono Pythona. Zainstaluj Python 3.12+ ze strony python.org.
    pause
    exit /b 1
)

if not exist ".venv-win\Scripts\python.exe" (
    echo Tworze srodowisko wirtualne .venv-win ...
    py -3 -m venv .venv-win
    if errorlevel 1 goto error
)

echo Instaluje biblioteki (wymaga internetu tylko przy budowaniu) ...
".venv-win\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv-win\Scripts\python.exe" -m pip install --quiet -r requirements-dev.txt
if errorlevel 1 goto error

set FA_MILIA_ONEDIR=
if /I "%~1"=="folder" set FA_MILIA_ONEDIR=1

echo Buduje program ...
".venv-win\Scripts\pyinstaller.exe" --noconfirm --clean --distpath dist --workpath build packaging\fa-milia.spec
if errorlevel 1 goto error

echo.
echo Gotowe! Program jest w folderze "dist".
echo Dane programu beda zapisywane w folderze "Fa milia - dane" obok pliku .exe.
pause
exit /b 0

:error
echo.
echo Wystapil blad - przeczytaj komunikaty powyzej.
pause
exit /b 1
