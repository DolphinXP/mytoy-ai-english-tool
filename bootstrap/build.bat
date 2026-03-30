@echo off
cd /d %~dp0

echo Building launcher.exe...
:: Force the correct MinGW path to the front to avoid "DLL hell" (e.g., conflicts with Tesseract-OCR)
set "PATH=D:\msys64\mingw64\bin;C:\Windows\system32;C:\Windows;%PATH%"
gcc -o launcher.exe launcher.c -mwindows -luser32 -lgdi32 -lkernel32 -lshell32 -Wall
if %ERRORLEVEL% == 0 (
    echo launcher.exe built successfully.
) else (
    echo ERROR: Failed to build launcher.exe.
    exit /b %ERRORLEVEL%
)
