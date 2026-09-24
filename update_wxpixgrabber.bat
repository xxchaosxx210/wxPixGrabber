@echo off
title Update wxPixGrabber
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
echo Updating wxPixGrabber...
echo.

git pull --ff-only
if errorlevel 1 (
    echo.
    echo Update failed. No files were intentionally overwritten.
    echo Run "git status" to check the repository state.
    echo.
    pause
    exit /b 1
)

echo.
echo wxPixGrabber is up to date.
echo.
pause
