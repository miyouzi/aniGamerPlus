@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "EXE_OUT=aniGamerPlus.exe"
set "RELEASE_VERSION=v24.9"
set "ZIP_NAME=aniGamerPlus_%RELEASE_VERSION%_windows_64bit.zip"
set "PIPY="

echo [build_win10] Build Win10: %EXE_OUT% + dist\%ZIP_NAME%
echo [build_win10] cleaning build/dist contents, exe in project root ^(upstream CI distpath^)
taskkill /F /IM "%EXE_OUT%" /T >nul 2>&1

if not exist "build" mkdir "build" 2>nul
if not exist "dist" mkdir "dist" 2>nul
call :clean_dir_contents "build"
call :clean_dir_contents "dist"
if exist "%EXE_OUT%" (
  attrib -r "%EXE_OUT%" >nul 2>&1
  del /f /q "%EXE_OUT%" >nul 2>&1
)

if not exist "%CD%\Dashboard\static\img\aniGamerPlus.ico" (
  echo [build_win10] FAIL: missing Dashboard\static\img\aniGamerPlus.ico
  goto :end_fail
)

call :find_python
if errorlevel 1 goto :end_fail

echo [build_win10] using:
%PIPY% -c "import sys; print(sys.executable); print(sys.version)"

%PIPY% -c "import sys; assert sys.version_info>=(3,8), 'need_python38'" 2>nul
if errorlevel 1 (
  echo [build_win10] FAIL: need Python 3.8+
  goto :end_fail
)

echo [build_win10] pip install dependencies + pyinstaller
%PIPY% -m pip install -q --upgrade pip
if errorlevel 1 goto :pip_fail

%PIPY% -m pip install -q -r requirements.txt
if errorlevel 1 goto :pip_fail

%PIPY% -m pip install -q pyinstaller
if errorlevel 1 goto :pip_fail
goto :after_pip
:pip_fail
echo [build_win10] FAIL: pip install
goto :end_fail
:after_pip

echo [build_win10] PyInstaller ^(same flags as .github/workflows Release-build / Python-build^)
echo [build_win10] distpath: %CD%\ ^(add-data: %CD% ^; aniGamerPlus/^)
%PIPY% -m PyInstaller --noconfirm --distpath "%CD%" --onefile --console --icon "%CD%\Dashboard\static\img\aniGamerPlus.ico" --clean --add-data "%CD%;aniGamerPlus/" "%CD%\aniGamerPlus.py"
if errorlevel 1 (
  echo [build_win10] FAIL: PyInstaller
  goto :end_fail
)

if not exist "%EXE_OUT%" (
  echo [build_win10] FAIL: missing %EXE_OUT%
  goto :end_fail
)

if exist "dist\%ZIP_NAME%" del /f /q "dist\%ZIP_NAME%"

echo [build_win10] archiving ^(Release-build.yml file list: exe + Dashboard + samples + LICENSE + README^)

where 7z >nul 2>&1
if not errorlevel 1 (
  7z a -tzip "dist\%ZIP_NAME%" "%EXE_OUT%" Dashboard DanmuTemplate.ass config-sample.json sn_list-sample.txt LICENSE README.md
  if not errorlevel 1 if exist "dist\%ZIP_NAME%" goto :zip_ok
)

where tar >nul 2>&1
if not errorlevel 1 (
  tar -caf "dist\%ZIP_NAME%" "%EXE_OUT%" Dashboard DanmuTemplate.ass config-sample.json sn_list-sample.txt LICENSE README.md
  if not errorlevel 1 if exist "dist\%ZIP_NAME%" goto :zip_ok
)

powershell -NoProfile -Command "Compress-Archive -LiteralPath '%CD%\%EXE_OUT%','%CD%\Dashboard','%CD%\DanmuTemplate.ass','%CD%\config-sample.json','%CD%\sn_list-sample.txt','%CD%\LICENSE','%CD%\README.md' -DestinationPath '%CD%\dist\%ZIP_NAME%' -Force"
if errorlevel 1 (
  echo [build_win10] WARN: exe OK but zip failed^; install 7-Zip ^(7z^) or use Windows tar / PS 5+ Compress-Archive
  echo [build_win10] OK: %CD%\%EXE_OUT%
  goto :end_ok
)
if not exist "dist\%ZIP_NAME%" (
  echo [build_win10] WARN: exe OK but missing dist\%ZIP_NAME%
  echo [build_win10] OK: %CD%\%EXE_OUT%
  goto :end_ok
)

:zip_ok
echo [build_win10] OK: %CD%\%EXE_OUT%
echo [build_win10] OK: %CD%\dist\%ZIP_NAME%
goto :end_ok

:find_python
set "PIPY="
for %%V in (3.8 3.9 3.10 3.11 3.12 3.13 3.14) do (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -%%V -c "import sys; assert sys.version_info>=(3,8)" 2>nul
    if not errorlevel 1 (
      set "PIPY=py -%%V"
      goto :find_ok
    )
  )
)
where python >nul 2>&1
if not errorlevel 1 (
  python -c "import sys; assert sys.version_info>=(3,8)" 2>nul
  if not errorlevel 1 (
    set "PIPY=python"
    goto :find_ok
  )
)
where py >nul 2>&1
if not errorlevel 1 (
  py -c "import sys; assert sys.version_info>=(3,8)" 2>nul
  if not errorlevel 1 (
    set "PIPY=py"
    goto :find_ok
  )
)
echo [build_win10] FAIL: no Python 3.8+ ^(py launcher or python in PATH^)
exit /b 1
:find_ok
exit /b 0

:clean_dir_contents
set "TGT=%~1"
if not exist "%TGT%" exit /b 0
for /f "delims=" %%D in ('dir /b /ad "%TGT%" 2^>nul') do rd /s /q "%TGT%\%%D" 2>nul
del /f /q "%TGT%\*" 2>nul
exit /b 0

:end_fail
if /i "%~1"=="nopause" exit /b 1
echo.
pause
exit /b 1

:end_ok
if /i "%~1"=="nopause" exit /b 0
echo.
pause
exit /b 0
