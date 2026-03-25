# Requirements Document

## Introduction

A standalone bootstrap application located in the `bootstrap` folder that provides a minimal native Windows UI for launching and stopping the four Python applications in the ai-tts workspace. All apps run under the `vibevoice` conda environment. The launcher tracks processes it starts so it can kill them on demand. The launcher is a native Windows executable (`bootstrap/launcher.exe`) compiled from C using gcc/mingw — it requires no Python or any other runtime to run. The UI is built directly on the Win32 API in C with no GUI framework dependencies.

## Glossary

- **Launcher**: The bootstrap application (`bootstrap/launcher.exe`), a native Windows executable compiled from C source (`bootstrap/launcher.c`) using gcc/mingw.
- **App_Entry**: A named, configurable record describing one managed application (name, script path, working directory), stored as a C struct.
- **Process_Record**: An in-memory C struct associating an App_Entry with its running Win32 process handle (`HANDLE`) and process ID.
- **vibevoice**: The conda environment used to run all managed applications.
- **Conda_Activator**: The component (implemented as C functions) responsible for constructing the correct command line that activates the `vibevoice` environment and then runs a target Python script.
- **Win32_Window**: The native Windows GUI window created via Win32 API calls (`CreateWindowEx`, `RegisterClassEx`, etc.) directly in C, without any GUI framework or runtime dependency.
- **Status_Indicator**: A per-app visual element in the Win32_Window that shows whether the app is running or stopped.

## Requirements

### Requirement 1: Application Registry

**User Story:** As a developer, I want all four managed apps defined in one place, so that adding or changing an app requires editing only a single location.

#### Acceptance Criteria

1. THE Launcher SHALL define an App_Entry for each of the following applications: `main_new.py` (root), `Recite/app.py`, `PDFReader/main.py`, and `QuickTranslate/main.py`.
2. THE Launcher SHALL store the workspace root path so that all App_Entry script paths are resolved relative to it.
3. WHEN the App_Entry list is modified, THE Launcher SHALL reflect the changes without requiring modifications to any other part of the code.

---

### Requirement 2: Conda Environment Activation

**User Story:** As a developer, I want the launcher to activate the `vibevoice` conda environment before running any app, so that all dependencies are available.

#### Conda_Activator SHALL construct a command that:

#### Acceptance Criteria

1. THE Conda_Activator SHALL locate the `conda` executable by searching `CONDA_EXE` environment variable, then `PATH`, then common default installation paths (`%USERPROFILE%\miniconda3`, `%USERPROFILE%\anaconda3`, `%PROGRAMDATA%\miniconda3`, `%PROGRAMDATA%\anaconda3`).
2. WHEN a conda executable is not found, THE Conda_Activator SHALL raise a descriptive error identifying the search paths that were checked.
3. THE Conda_Activator SHALL construct a command equivalent to `conda run -n vibevoice python <script>` to execute a target script inside the environment.
4. THE Conda_Activator SHALL pass the working directory of the target script as the `cwd` for the spawned process.

---

### Requirement 3: Start Application

**User Story:** As a user, I want to start any managed app from the launcher UI, so that I don't need to open a terminal.

#### Acceptance Criteria

1. WHEN the user activates the Start control for an App_Entry, THE Launcher SHALL spawn the corresponding process using `CreateProcess` with the Conda_Activator command line.
2. WHEN a process is successfully spawned, THE Launcher SHALL create a Process_Record holding the Win32 `HANDLE` and update the Status_Indicator for that app to "running".
3. WHILE an app's Process_Record exists and the process has not exited, THE Launcher SHALL disable the Start control and enable the Stop control for that app.
4. IF the process fails to spawn (e.g., file not found, permission error), THEN THE Launcher SHALL display a descriptive error message via a Win32 message box and leave the Status_Indicator as "stopped".

---

### Requirement 4: Stop Application

**User Story:** As a user, I want to stop a running app from the launcher UI, so that I can shut it down without hunting for its window or process.

#### Acceptance Criteria

1. WHEN the user activates the Stop control for an App_Entry, THE Launcher SHALL terminate the associated Process_Record's process and all of its child processes using `TerminateProcess` and Win32 job objects or process tree enumeration.
2. WHEN a process is successfully terminated, THE Launcher SHALL close the Win32 `HANDLE`, remove the Process_Record, and update the Status_Indicator for that app to "stopped".
3. IF the process does not terminate within 3 seconds of a graceful stop signal, THEN THE Launcher SHALL forcefully kill the process via `TerminateProcess`.
4. WHILE no Process_Record exists for an app, THE Launcher SHALL disable the Stop control for that app.

---

### Requirement 5: Process Status Polling

**User Story:** As a user, I want the launcher to detect when an app exits on its own, so that the UI stays accurate without manual refresh.

#### Acceptance Criteria

1. THE Launcher SHALL poll all active Process_Records at a regular interval not exceeding 1000 ms using `WaitForSingleObject` with a zero timeout or a dedicated Win32 timer (`SetTimer`).
2. WHEN a polled process is found to have exited, THE Launcher SHALL close the Win32 `HANDLE`, remove its Process_Record, and update the Status_Indicator to "stopped".
3. THE Launcher SHALL update the Start and Stop controls to reflect the current process state after each poll cycle.

---

### Requirement 6: Native Windows UI

**User Story:** As a developer, I want the launcher UI built with the Windows API directly in C, so that the bootstrap has zero runtime dependencies.

#### Acceptance Criteria

1. THE Win32_Window SHALL be created using Win32 API calls (`RegisterClassEx`, `CreateWindowEx`, `CreateWindow`) linked directly against `user32.lib` and `gdi32.lib` — no Python, no ctypes, no third-party GUI framework.
2. THE Win32_Window SHALL display one row per App_Entry containing: the app name, a Status_Indicator, a Start button, and a Stop button.
3. THE Win32_Window SHALL remain responsive (process the Windows message loop via `GetMessage`/`DispatchMessage`) while managed processes are running.
4. WHEN the Win32_Window is closed, THE Launcher SHALL terminate all running Process_Records before exiting.
5. THE Win32_Window SHALL have a fixed, appropriately sized layout that does not require resizing to use.

---

### Requirement 7: Launcher Entry Point and Build

**User Story:** As a developer, I want a single native executable in the `bootstrap` folder built from C source, so that the launcher can be started with one command and requires no runtime to be installed.

#### Acceptance Criteria

1. THE Launcher SHALL be a compiled native Windows executable (`bootstrap/launcher.exe`) built from `bootstrap/launcher.c` using gcc/mingw (e.g., `x86_64-w64-mingw32-gcc` or `gcc` from a mingw-w64 toolchain).
2. THE Launcher SHALL require no Python installation, no conda environment, and no other runtime to execute — only the standard Windows system DLLs (`kernel32.dll`, `user32.dll`, `gdi32.dll`).
3. THE Launcher SHALL be runnable via `bootstrap\launcher.exe` from the workspace root without any additional configuration.
4. THE Launcher source (`bootstrap/launcher.c`) SHALL use Win32 API functions directly (e.g., `CreateProcess`, `TerminateProcess`, `CreateWindowEx`) with no intermediary language bindings.
5. THE Launcher repository SHALL include a `bootstrap/Makefile` (or `bootstrap/build.bat`) that compiles `launcher.c` into `launcher.exe` with a single command (e.g., `make -C bootstrap` or `build.bat`).
6. WHEN the compiled `launcher.exe` is executed, THE Launcher SHALL open the Win32_Window immediately without requiring additional configuration.
