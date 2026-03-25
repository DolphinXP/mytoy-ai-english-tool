all: launcher.exe

launcher.exe: launcher.c
	gcc -o launcher.exe launcher.c -mwindows -luser32 -lgdi32 -lkernel32 -lshell32 -Wall

clean:
	del /f launcher.exe
