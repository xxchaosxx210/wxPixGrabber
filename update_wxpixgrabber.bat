@echo off
title Update wxPixGrabber - improvements
cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
    echo.
    echo Git was not found on this PC.
    echo Install Git for Windows and run this file again.
    echo.
    pause
    exit /b 1
)

echo.
echo Updating wxPixGrabber improvements branch...
echo.

git fetch origin improvements
if errorlevel 1 (
    echo.
    echo Could not fetch the improvements branch.
    echo.
    pause
    exit /b 1
)

git switch improvements
if errorlevel 1 (
    echo.
    echo Could not switch to the improvements branch.
    echo Run "git status" and check for local changes.
    echo.
    pause
    exit /b 1
)

git pull --ff-only origin improvements
if errorlevel 1 (
    echo.
    echo Update failed. No files were intentionally overwritten.
    echo Run "git status" to check the repository state.
    echo.
    pause
    exit /b 1
)

echo.
echo wxPixGrabber improvements is up to date.
echo.

echo Launching wxPixGrabber...
start "" cmd /k ".\.venv\Scripts\activate & python main.py"
exit /b 0
