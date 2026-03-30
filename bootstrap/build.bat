@echo off
cd /d %~dp0

echo Building launcher.exe...
gcc -o launcher.exe launcher.c -mwindows -luser32 -lgdi32 -lkernel32 -lshell32 -Wall
if %ERRORLEVEL% == 0 (
    echo launcher.exe built successfully.
) else (
    echo ERROR: Failed to build launcher.exe.
    exit /b %ERRORLEVEL%
)
