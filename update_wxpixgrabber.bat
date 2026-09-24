@echo off
title Update wxPixGrabber - pixhost-fix
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
echo Updating wxPixGrabber pixhost-fix branch...
echo.

git fetch origin pixhost-fix
if errorlevel 1 (
    echo.
    echo Could not fetch the pixhost-fix branch.
    echo.
    pause
    exit /b 1
)

git switch pixhost-fix
if errorlevel 1 (
    echo.
    echo Could not switch to the pixhost-fix branch.
    echo Run "git status" and check for local changes.
    echo.
    pause
    exit /b 1
)

git pull --ff-only origin pixhost-fix
if errorlevel 1 (
    echo.
    echo Update failed. No files were intentionally overwritten.
    echo Run "git status" to check the repository state.
    echo.
    pause
    exit /b 1
)

echo.
echo wxPixGrabber pixhost-fix is up to date.
echo.
pause
