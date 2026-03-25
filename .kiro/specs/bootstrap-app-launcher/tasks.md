# Implementation Plan: bootstrap-app-launcher

## Overview

Implement a single-file native Windows C application (`bootstrap/launcher.c`) compiled to `launcher.exe` via gcc/mingw. The implementation proceeds in layers: data structures → conda resolution → process management → Win32 UI → build system → tests.

## Tasks

- [x] 1. Create project skeleton and data structures
  - Create `bootstrap/launcher.c` with includes, `App_Entry` and `Process_Record` struct definitions, and the static `app_entries[]` array with all four managed apps
  - Define all window layout constants (`WINDOW_WIDTH`, `WINDOW_HEIGHT`, `ROW_HEIGHT`, etc.) and control ID macros (`ID_START`, `ID_STOP`, `ID_STATUS`)
  - Declare global arrays `process_records[]`, `hwnd_start[]`, `hwnd_stop[]`, `hwnd_status[]`
  - _Requirements: 1.1, 1.2, 1.3, 6.5_

- [x] 2. Implement conda resolution and command-line builder
  - [x] 2.1 Implement `find_conda()` — check `CONDA_EXE` env var, then `PATH`, then four hardcoded fallback paths; return 0 on success with path in out buffer, non-zero on failure
    - _Requirements: 2.1, 2.2_

  - [ ]* 2.2 Write property test for `find_conda()` search order (Property 2)
    - **Property 2: Conda search returns first found location**
    - **Validates: Requirements 2.1**

  - [x] 2.3 Implement `build_conda_cmdline()` — construct `"<conda_exe>" run -n vibevoice python "<abs_script>"` and set `cwd_out` to workspace root joined with `subdir` (or workspace root when `subdir` is empty)
    - _Requirements: 2.3, 2.4_

  - [ ]* 2.4 Write property test for `build_conda_cmdline()` command structure (Property 3)
    - **Property 3: Conda command line contains required components**
    - **Validates: Requirements 2.3**

  - [ ]* 2.5 Write property test for `build_conda_cmdline()` working directory (Property 4)
    - **Property 4: Conda working directory matches app subdirectory**
    - **Validates: Requirements 2.4**

  - [ ]* 2.6 Write property test for script path resolution (Property 1)
    - **Property 1: Script path resolution is relative to workspace root**
    - **Validates: Requirements 1.2**

- [ ] 3. Checkpoint — Ensure conda logic unit tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement process manager
  - [x] 4.1 Implement `start_app(int index)` — call `build_conda_cmdline()`, call `CreateProcess` with `CREATE_NO_WINDOW`, fill `process_records[index]`; on failure show `MessageBox` with `GetLastError()` description and leave record zeroed
    - _Requirements: 3.1, 3.2, 3.4_

  - [ ]* 4.2 Write property test for `start_app()` post-condition on success (Property 5)
    - **Property 5: Process record reflects running state after successful start**
    - **Validates: Requirements 3.2, 3.3**

  - [x] 4.3 Implement `stop_app(int index)` — send graceful signal, wait up to 3 s via `WaitForSingleObject(hProcess, 3000)`, forcefully call `TerminateProcess` on timeout, then `CloseHandle` and zero the record
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 4.4 Implement `poll_processes()` — iterate all records, call `WaitForSingleObject(hProcess, 0)`, on `WAIT_OBJECT_0` close handle, zero record, and call `update_ui()`
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 4.5 Write property test for process record cleared after stop/exit (Property 6)
    - **Property 6: Process record is cleared and UI shows stopped after process ends**
    - **Validates: Requirements 4.2, 4.4, 5.2**

  - [x] 4.6 Implement `kill_all()` — iterate all records with non-NULL `hProcess`, call `TerminateProcess` + `CloseHandle`, zero each record
    - _Requirements: 6.4_

  - [ ]* 4.7 Write property test for `kill_all()` clears all records (Property 7)
    - **Property 7: All process records are cleared on window close**
    - **Validates: Requirements 6.4**

- [ ] 5. Checkpoint — Ensure process manager tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Win32 UI
  - [x] 6.1 Implement `update_ui(int index)` — enable/disable Start and Stop buttons and invalidate the status indicator rect based on `process_records[index].hProcess`
    - _Requirements: 3.3, 4.4, 5.3_

  - [x] 6.2 Implement window creation in `WinMain` — `RegisterClassEx`, `CreateWindowEx`, create per-row static label, status indicator, Start button, and Stop button for each app entry
    - _Requirements: 6.1, 6.2, 6.5_

  - [x] 6.3 Implement `WndProc` — handle `WM_CREATE` (set 500 ms timer), `WM_COMMAND` (route Start/Stop button clicks to `start_app`/`stop_app`), `WM_TIMER` (call `poll_processes`), `WM_PAINT` (draw colored status rectangles), `WM_DESTROY` (call `kill_all`, `PostQuitMessage`)
    - _Requirements: 3.1, 4.1, 5.1, 6.3, 6.4_

  - [x] 6.4 Implement workspace root resolution in `WinMain` using `GetModuleFileName` + path trimming to locate the workspace root relative to the executable
    - _Requirements: 1.2, 7.3_

- [ ] 7. Checkpoint — Verify UI compiles and window opens correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Create build system
  - [x] 8.1 Create `bootstrap/build.bat` with `gcc -o launcher.exe launcher.c -mwindows -luser32 -lgdi32 -lkernel32`
    - _Requirements: 7.1, 7.5_

  - [x] 8.2 Create `bootstrap/Makefile` with a `launcher.exe: launcher.c` rule using the same gcc command
    - _Requirements: 7.5_

- [-] 9. Create test harness
  - [-] 9.1 Create `bootstrap/test_launcher.c` with a minimal C test harness (assert-based or greatest framework); include all unit test cases: app registry count and paths, `find_conda()` error when absent, `find_conda()` priority with `CONDA_EXE` set, `build_conda_cmdline()` output, timer interval constant ≤ 1000 ms, window dimension constants
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 5.1, 6.5_

  - [ ]* 9.2 Add property-based test loop for Property 1 (script path resolution) to `test_launcher.c`
    - **Property 1: Script path resolution is relative to workspace root**
    - **Validates: Requirements 1.2**

  - [ ]* 9.3 Add property-based test loop for Property 2 (conda search order) to `test_launcher.c`
    - **Property 2: Conda search returns first found location**
    - **Validates: Requirements 2.1**

  - [ ]* 9.4 Add property-based test loop for Property 3 (cmdline structure) to `test_launcher.c`
    - **Property 3: Conda command line contains required components**
    - **Validates: Requirements 2.3**

  - [ ]* 9.5 Add property-based test loop for Property 4 (cwd output) to `test_launcher.c`
    - **Property 4: Conda working directory matches app subdirectory**
    - **Validates: Requirements 2.4**

  - [-] 9.6 Add test build rule to `bootstrap/Makefile` and `bootstrap/build.bat`: `gcc -o test_launcher.exe test_launcher.c -lkernel32`
    - _Requirements: 7.1_

- [ ] 10. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- All property tests should run a minimum of 100 iterations with randomized inputs
- Property test functions must include the comment tag: `// Feature: bootstrap-app-launcher, Property <N>: <text>`
- The test binary must NOT link `-mwindows` so it runs as a console application
- `launcher.c` must compile cleanly with no warnings under `-Wall`
