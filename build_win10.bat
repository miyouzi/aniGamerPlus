@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "EXE_OUT=aniGamerPlus.exe"
set "DIST_DIR=dist"
set "DIST_EXE=%DIST_DIR%\%EXE_OUT%"
set "ZIP_NAME=aniGamerPlus_windows_x64.zip"
set "PIPY="

echo [build_win10] Win10 packaging: PyInstaller exe in %DIST_DIR%\ + Release-style zip [%ZIP_NAME%]
echo [build_win10] matches .github/workflows (Python-build / Release-build); exe not at repo root (暫時)
taskkill /F /IM "%EXE_OUT%" /T >nul 2>&1

if not exist "build" mkdir "build" 2>nul
call :clean_dir_contents "build"

if not exist "%DIST_DIR%\" mkdir "%DIST_DIR%" 2>nul
if exist "%DIST_EXE%" (
  attrib -r "%DIST_EXE%" >nul 2>&1
  del /f /q "%DIST_EXE%" >nul 2>&1
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

echo [build_win10] PyInstaller output: %DIST_EXE% (add-data: %CD% ^; aniGamerPlus/^)
REM Same onefile flags as CI: Release-build.yml / Python-build.yml (distpath = dist\)
%PIPY% -m PyInstaller --noconfirm --distpath "%CD%\%DIST_DIR%" --onefile --console --icon "%CD%\Dashboard\static\img\aniGamerPlus.ico" --clean --add-data "%CD%;aniGamerPlus/" "%CD%\aniGamerPlus.py"
if errorlevel 1 (
  echo [build_win10] FAIL: PyInstaller
  goto :end_fail
)

if not exist "%DIST_EXE%" (
  echo [build_win10] FAIL: missing %DIST_EXE%
  goto :end_fail
)

if exist "dist\%ZIP_NAME%" del /f /q "dist\%ZIP_NAME%"

echo [build_win10] archiving (Release-build.zip layout)
REM Flat zip: stage then pack (exe 在 dist\，避免 zip 內出現 dist\ 前綴)
set "ZIPST=%TEMP%\agp_release_%RANDOM%"
mkdir "%ZIPST%" 2>nul
copy /y "%DIST_EXE%" "%ZIPST%\%EXE_OUT%" >nul
if errorlevel 1 (
  echo [build_win10] FAIL: stage exe for zip
  rd /s /q "%ZIPST%" 2>nul
  goto :end_fail
)
xcopy "Dashboard" "%ZIPST%\Dashboard\" /E /I /Y /Q >nul
copy /y "DanmuTemplate.ass" "%ZIPST%\" >nul
copy /y "config-sample.json" "%ZIPST%\" >nul
copy /y "sn_list-sample.txt" "%ZIPST%\" >nul
copy /y "LICENSE" "%ZIPST%\" >nul
copy /y "README.md" "%ZIPST%\" >nul

where tar >nul 2>&1
if not errorlevel 1 (
  tar -caf "dist\%ZIP_NAME%" -C "%ZIPST%" . 2>nul
)
if exist "dist\%ZIP_NAME%" goto :zip_done_staging

powershell -NoProfile -Command "Get-ChildItem -LiteralPath '%ZIPST%' | Compress-Archive -DestinationPath '%CD%\dist\%ZIP_NAME%' -Force"
if errorlevel 1 (
  echo [build_win10] WARN: exe OK but zip failed; install tar or use PS 5+ Compress-Archive
  echo [build_win10] OK: %CD%\%DIST_EXE%
  rd /s /q "%ZIPST%" 2>nul
  goto :end_ok
)

:zip_done_staging
rd /s /q "%ZIPST%" 2>nul

if exist "dist\%ZIP_NAME%" goto :zip_ok

echo [build_win10] WARN: exe OK but missing dist\%ZIP_NAME%
echo [build_win10] OK: %CD%\%DIST_EXE%
goto :end_ok

:zip_ok
echo [build_win10] OK: %CD%\%DIST_EXE%
echo [build_win10] OK: %CD%\dist\%ZIP_NAME%
goto :end_ok

:find_python
set "PIPY="
for %%V in (3.9 3.8 3.11 3.10 3.12 3.13 3.14) do (
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
echo [build_win10] FAIL: no Python 3.8+ (py launcher or python in PATH)
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
