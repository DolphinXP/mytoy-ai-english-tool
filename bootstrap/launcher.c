/*
 * launcher.c — Bootstrap App Launcher
 * Native Win32 C app. No Python required to run the launcher itself.
 *
 * Build: gcc -o launcher.exe launcher.c -mwindows -luser32 -lgdi32 -lkernel32 -lshell32 -Wall
 */

#include <windows.h>
#include <shellapi.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* -------------------------------------------------------------------------
 * Data Structures
 * ---------------------------------------------------------------------- */

typedef struct {
    char name[64];
    char script[256];   /* relative to workspace root */
    char subdir[256];   /* working dir relative to workspace root */
} App_Entry;

typedef struct {
    HANDLE hProcess;    /* NULL = not running */
    DWORD  pid;
} Process_Record;

/* -------------------------------------------------------------------------
 * App Registry — edit only this array to add/change apps
 * ---------------------------------------------------------------------- */

static App_Entry app_entries[] = {
    { "VibeVoice Main",  "main_new.py",             ""               },
    { "Recite",          "Recite\\app.py",           "Recite"         },
    { "PDF Reader",      "PDFReader\\main.py",       "PDFReader"      },
    { "Quick Translate", "QuickTranslate\\main.py",  "QuickTranslate" },
};

#define APP_COUNT ((int)(sizeof(app_entries) / sizeof(app_entries[0])))

/* -------------------------------------------------------------------------
 * Layout & Timer Constants
 * ---------------------------------------------------------------------- */

#define WINDOW_WIDTH   420
#define WINDOW_HEIGHT  (60 + APP_COUNT * 50)
#define ROW_HEIGHT     50
#define POLL_INTERVAL  500

/* -------------------------------------------------------------------------
 * Tray Constants
 * ---------------------------------------------------------------------- */

#define TRAY_ICON_ID   1
#define WM_TRAYICON    (WM_USER + 1)
#define IDM_SHOW       2001
#define IDM_EXIT       2002

/* -------------------------------------------------------------------------
 * Control ID Macros
 * ---------------------------------------------------------------------- */

#define ID_START(i)   (100 + (i)*4 + 0)
#define ID_STOP(i)    (100 + (i)*4 + 1)
#define ID_STATUS(i)  (100 + (i)*4 + 2)

/* -------------------------------------------------------------------------
 * Globals
 * ---------------------------------------------------------------------- */

static Process_Record  process_records[APP_COUNT];
static HWND            hwnd_start[APP_COUNT];
static HWND            hwnd_stop[APP_COUNT];
static HWND            hwnd_status[APP_COUNT];
static char            workspace_root[MAX_PATH];
static NOTIFYICONDATAA g_nid;
static BOOL            g_tray_added = FALSE;
static HICON           g_hIcon      = NULL;

/* -------------------------------------------------------------------------
 * Forward Declarations
 * ---------------------------------------------------------------------- */

int  find_conda(char *out_path, size_t out_size);
void build_conda_cmdline(const char *root, const App_Entry *entry,
                         char *cmdline_out, size_t cmdline_size,
                         char *cwd_out,     size_t cwd_size);
int  start_app(int index);
void stop_app(int index);
void poll_processes(void);
void kill_all(void);
void update_ui(int index);
void tray_add(HWND hwnd);
void tray_remove(void);
void tray_show_menu(HWND hwnd);
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);

/* -------------------------------------------------------------------------
 * find_conda
 * ---------------------------------------------------------------------- */

int find_conda(char *out_path, size_t out_size)
{
    char buf[MAX_PATH];

    /* 1. CONDA_EXE env var */
    if (GetEnvironmentVariableA("CONDA_EXE", buf, sizeof(buf)) > 0)
        if (GetFileAttributesA(buf) != INVALID_FILE_ATTRIBUTES) {
            strncpy(out_path, buf, out_size - 1);
            out_path[out_size - 1] = '\0';
            return 0;
        }

    /* 2. PATH */
    {
        char path_env[32768];
        if (GetEnvironmentVariableA("PATH", path_env, sizeof(path_env)) > 0) {
            char *ctx = NULL;
            char *dir = strtok_s(path_env, ";", &ctx);
            while (dir) {
                int n = snprintf(buf, sizeof(buf), "%s\\conda.exe", dir);
                if (n > 0 && (size_t)n < sizeof(buf) &&
                    GetFileAttributesA(buf) != INVALID_FILE_ATTRIBUTES) {
                    strncpy(out_path, buf, out_size - 1);
                    out_path[out_size - 1] = '\0';
                    return 0;
                }
                dir = strtok_s(NULL, ";", &ctx);
            }
        }
    }

    /* 3. Fallback install paths */
    {
        char up[MAX_PATH] = "";
        char pd[MAX_PATH] = "";
        GetEnvironmentVariableA("USERPROFILE", up, sizeof(up));
        GetEnvironmentVariableA("PROGRAMDATA", pd, sizeof(pd));
        const char *bases[4][2] = {
            {up, "miniconda3"}, {up, "anaconda3"},
            {pd, "miniconda3"}, {pd, "anaconda3"}
        };
        for (int i = 0; i < 4; i++) {
            if (!bases[i][0][0]) continue;
            int n = snprintf(buf, sizeof(buf), "%s\\%s\\Scripts\\conda.exe",
                             bases[i][0], bases[i][1]);
            if (n > 0 && (size_t)n < sizeof(buf) &&
                GetFileAttributesA(buf) != INVALID_FILE_ATTRIBUTES) {
                strncpy(out_path, buf, out_size - 1);
                out_path[out_size - 1] = '\0';
                return 0;
            }
        }
    }
    return 1;
}

/* -------------------------------------------------------------------------
 * build_conda_cmdline
 * ---------------------------------------------------------------------- */

void build_conda_cmdline(const char *root, const App_Entry *entry,
                         char *cmdline_out, size_t cmdline_size,
                         char *cwd_out,     size_t cwd_size)
{
    char conda_exe[MAX_PATH];
    char abs_script[MAX_PATH];

    if (find_conda(conda_exe, sizeof(conda_exe)) != 0)
        strncpy(conda_exe, "conda", sizeof(conda_exe) - 1);

    snprintf(abs_script, sizeof(abs_script), "%s\\%s", root, entry->script);
    snprintf(cmdline_out, cmdline_size,
             "\"%s\" run --no-capture-output -n vibevoice python \"%s\"",
             conda_exe, abs_script);

    if (entry->subdir[0])
        snprintf(cwd_out, cwd_size, "%s\\%s", root, entry->subdir);
    else {
        strncpy(cwd_out, root, cwd_size - 1);
        cwd_out[cwd_size - 1] = '\0';
    }
}

/* -------------------------------------------------------------------------
 * start_app
 * ---------------------------------------------------------------------- */

int start_app(int index)
{
    char conda_exe[MAX_PATH];
    char cmdline[1024];
    char cwd[MAX_PATH];
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    if (find_conda(conda_exe, sizeof(conda_exe)) != 0) {
        MessageBoxA(NULL,
            "Could not find conda.\nSet CONDA_EXE or add conda to PATH.",
            "Launcher Error", MB_OK | MB_ICONERROR);
        return 1;
    }

    build_conda_cmdline(workspace_root, &app_entries[index],
                        cmdline, sizeof(cmdline), cwd, sizeof(cwd));

    memset(&si, 0, sizeof(si));
    si.cb = sizeof(si);
    memset(&pi, 0, sizeof(pi));

    if (!CreateProcessA(NULL, cmdline, NULL, NULL, FALSE,
                        CREATE_NO_WINDOW, NULL, cwd, &si, &pi)) {
        char msg[512];
        FormatMessageA(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
                       NULL, GetLastError(), 0, msg, sizeof(msg), NULL);
        MessageBoxA(NULL, msg, "Launcher Error", MB_OK | MB_ICONERROR);
        return 1;
    }

    process_records[index].hProcess = pi.hProcess;
    process_records[index].pid      = pi.dwProcessId;
    CloseHandle(pi.hThread);
    update_ui(index);
    return 0;
}

/* -------------------------------------------------------------------------
 * stop_app — kills the full process tree via taskkill /F /T
 * ---------------------------------------------------------------------- */

void stop_app(int index)
{
    HANDLE hProcess = process_records[index].hProcess;
    DWORD  pid      = process_records[index].pid;

    if (!hProcess) return;

    /* Kill entire tree — conda spawns a child python process */
    if (pid) {
        char cmd[64];
        STARTUPINFOA si;
        PROCESS_INFORMATION pi;
        snprintf(cmd, sizeof(cmd), "taskkill /F /T /PID %lu", (unsigned long)pid);
        memset(&si, 0, sizeof(si));
        si.cb = sizeof(si);
        memset(&pi, 0, sizeof(pi));
        if (CreateProcessA(NULL, cmd, NULL, NULL, FALSE,
                           CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
            WaitForSingleObject(pi.hProcess, 5000);
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }
    }

    /* Also terminate the handle we hold directly */
    TerminateProcess(hProcess, 0);
    WaitForSingleObject(hProcess, 3000);
    CloseHandle(hProcess);

    process_records[index].hProcess = NULL;
    process_records[index].pid      = 0;
    update_ui(index);
}

/* -------------------------------------------------------------------------
 * poll_processes
 * ---------------------------------------------------------------------- */

void poll_processes(void)
{
    for (int i = 0; i < APP_COUNT; i++) {
        if (!process_records[i].hProcess) continue;
        if (WaitForSingleObject(process_records[i].hProcess, 0) == WAIT_OBJECT_0) {
            CloseHandle(process_records[i].hProcess);
            process_records[i].hProcess = NULL;
            process_records[i].pid      = 0;
            update_ui(i);
        }
    }
}

/* -------------------------------------------------------------------------
 * kill_all
 * ---------------------------------------------------------------------- */

void kill_all(void)
{
    for (int i = 0; i < APP_COUNT; i++) {
        if (!process_records[i].hProcess) continue;
        if (process_records[i].pid) {
            char cmd[64];
            STARTUPINFOA si;
            PROCESS_INFORMATION pi;
            snprintf(cmd, sizeof(cmd), "taskkill /F /T /PID %lu",
                     (unsigned long)process_records[i].pid);
            memset(&si, 0, sizeof(si));
            si.cb = sizeof(si);
            memset(&pi, 0, sizeof(pi));
            if (CreateProcessA(NULL, cmd, NULL, NULL, FALSE,
                               CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
                WaitForSingleObject(pi.hProcess, 3000);
                CloseHandle(pi.hProcess);
                CloseHandle(pi.hThread);
            }
        }
        TerminateProcess(process_records[i].hProcess, 0);
        CloseHandle(process_records[i].hProcess);
        process_records[i].hProcess = NULL;
        process_records[i].pid      = 0;
    }
}

/* -------------------------------------------------------------------------
 * update_ui
 * ---------------------------------------------------------------------- */

void update_ui(int index)
{
    BOOL running = (process_records[index].hProcess != NULL);
    EnableWindow(hwnd_start[index], !running);
    EnableWindow(hwnd_stop[index],   running);
    InvalidateRect(hwnd_status[index], NULL, TRUE);
}

/* -------------------------------------------------------------------------
 * Tray helpers
 * ---------------------------------------------------------------------- */

void tray_add(HWND hwnd)
{
    memset(&g_nid, 0, sizeof(g_nid));
    g_nid.cbSize           = sizeof(g_nid);
    g_nid.hWnd             = hwnd;
    g_nid.uID              = TRAY_ICON_ID;
    g_nid.uFlags           = NIF_ICON | NIF_MESSAGE | NIF_TIP;
    g_nid.uCallbackMessage = WM_TRAYICON;
    g_nid.hIcon            = g_hIcon ? g_hIcon : LoadIcon(NULL, IDI_APPLICATION);
    strncpy(g_nid.szTip, "AI-TTS Launcher", sizeof(g_nid.szTip) - 1);
    Shell_NotifyIconA(NIM_ADD, &g_nid);
    g_tray_added = TRUE;
}

void tray_remove(void)
{
    if (g_tray_added) {
        Shell_NotifyIconA(NIM_DELETE, &g_nid);
        g_tray_added = FALSE;
    }
}

void tray_show_menu(HWND hwnd)
{
    POINT pt;
    HMENU hMenu = CreatePopupMenu();
    GetCursorPos(&pt);
    AppendMenuA(hMenu, MF_STRING,    IDM_SHOW, "Show");
    AppendMenuA(hMenu, MF_SEPARATOR, 0,        NULL);
    AppendMenuA(hMenu, MF_STRING,    IDM_EXIT, "Exit");
    SetForegroundWindow(hwnd);
    TrackPopupMenu(hMenu, TPM_BOTTOMALIGN | TPM_LEFTALIGN,
                   pt.x, pt.y, 0, hwnd, NULL);
    DestroyMenu(hMenu);
}

/* -------------------------------------------------------------------------
 * WndProc
 * ---------------------------------------------------------------------- */

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    HINSTANCE hInst = GetModuleHandle(NULL);

    switch (msg) {

    case WM_CREATE:
        SetTimer(hwnd, 1, POLL_INTERVAL, NULL);
        tray_add(hwnd);
        for (int i = 0; i < APP_COUNT; i++) {
            int y = 10 + i * ROW_HEIGHT;
            CreateWindowExA(0, "STATIC", app_entries[i].name,
                WS_CHILD | WS_VISIBLE | SS_LEFT,
                10, y + 15, 150, 20, hwnd, NULL, hInst, NULL);
            hwnd_status[i] = CreateWindowExA(0, "STATIC", "",
                WS_CHILD | WS_VISIBLE | SS_OWNERDRAW,
                165, y + 12, 20, 20,
                hwnd, (HMENU)(UINT_PTR)ID_STATUS(i), hInst, NULL);
            hwnd_start[i] = CreateWindowExA(0, "BUTTON", "Start",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                195, y + 10, 80, 26,
                hwnd, (HMENU)(UINT_PTR)ID_START(i), hInst, NULL);
            hwnd_stop[i] = CreateWindowExA(0, "BUTTON", "Stop",
                WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON,
                285, y + 10, 80, 26,
                hwnd, (HMENU)(UINT_PTR)ID_STOP(i), hInst, NULL);
            update_ui(i);
        }
        return 0;

    case WM_COMMAND: {
        int id = LOWORD(wParam);
        if (id == IDM_SHOW) {
            ShowWindow(hwnd, SW_RESTORE);
            SetForegroundWindow(hwnd);
            return 0;
        }
        if (id == IDM_EXIT) {
            tray_remove();
            kill_all();
            DestroyWindow(hwnd);
            return 0;
        }
        for (int i = 0; i < APP_COUNT; i++) {
            if (id == ID_START(i)) { start_app(i); break; }
            if (id == ID_STOP(i))  { stop_app(i);  break; }
        }
        return 0;
    }

    case WM_TIMER:
        poll_processes();
        return 0;

    case WM_DRAWITEM: {
        DRAWITEMSTRUCT *dis = (DRAWITEMSTRUCT *)lParam;
        for (int i = 0; i < APP_COUNT; i++) {
            if ((int)dis->CtlID == ID_STATUS(i)) {
                COLORREF c = process_records[i].hProcess
                             ? RGB(0, 200, 0) : RGB(200, 0, 0);
                HBRUSH hb = CreateSolidBrush(c);
                FillRect(dis->hDC, &dis->rcItem, hb);
                DeleteObject(hb);
                break;
            }
        }
        return TRUE;
    }

    case WM_TRAYICON:
        if (lParam == WM_RBUTTONUP)
            tray_show_menu(hwnd);
        else if (lParam == WM_LBUTTONDBLCLK) {
            ShowWindow(hwnd, SW_RESTORE);
            SetForegroundWindow(hwnd);
        }
        return 0;

    case WM_CLOSE:
        /* Hide to tray — do NOT destroy */
        ShowWindow(hwnd, SW_HIDE);
        return 0;

    case WM_DESTROY:
        tray_remove();
        kill_all();
        PostQuitMessage(0);
        return 0;

    default:
        return DefWindowProcA(hwnd, msg, wParam, lParam);
    }
}

/* -------------------------------------------------------------------------
 * WinMain
 * ---------------------------------------------------------------------- */

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance,
                   LPSTR lpCmdLine, int nCmdShow)
{
    (void)hPrevInstance;
    (void)lpCmdLine;

    /* Resolve workspace root: exe lives at <root>\bootstrap\launcher.exe */
    {
        char exe_path[MAX_PATH];
        char *sep;
        GetModuleFileNameA(NULL, exe_path, MAX_PATH);
        sep = strrchr(exe_path, '\\'); if (sep) *sep = '\0'; /* strip filename  */
        sep = strrchr(exe_path, '\\'); if (sep) *sep = '\0'; /* strip bootstrap */
        strncpy(workspace_root, exe_path, MAX_PATH - 1);
        workspace_root[MAX_PATH - 1] = '\0';
    }

    /* Load icon from launch.ico next to the exe */
    {
        char exe_dir[MAX_PATH];
        char ico_path[MAX_PATH + 16]; /* extra room for "launch.ico" */
        char *sep;
        GetModuleFileNameA(NULL, exe_dir, MAX_PATH);
        sep = strrchr(exe_dir, '\\');
        if (sep) {
            *(sep + 1) = '\0';
            snprintf(ico_path, sizeof(ico_path), "%slaunch.ico", exe_dir);
        } else {
            strncpy(ico_path, "launch.ico", sizeof(ico_path) - 1);
            ico_path[sizeof(ico_path) - 1] = '\0';
        }
        g_hIcon = (HICON)LoadImageA(NULL, ico_path, IMAGE_ICON, 0, 0,
                                    LR_LOADFROMFILE | LR_DEFAULTSIZE | LR_SHARED);
        if (!g_hIcon)
            g_hIcon = LoadIcon(NULL, IDI_APPLICATION);
    }

    /* Register window class */
    {
        WNDCLASSEXA wc;
        memset(&wc, 0, sizeof(wc));
        wc.cbSize        = sizeof(wc);
        wc.style         = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc   = WndProc;
        wc.hInstance     = hInstance;
        wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1);
        wc.lpszClassName = "LauncherClass";
        wc.hCursor       = LoadCursor(NULL, IDC_ARROW);
        wc.hIcon         = g_hIcon;
        wc.hIconSm       = (HICON)LoadImageA(NULL, IDI_APPLICATION,
                                              IMAGE_ICON, 16, 16, LR_SHARED);
        RegisterClassExA(&wc);
    }

    /* Create window — WS_EX_TOPMOST keeps it always on top */
    HWND hwnd = CreateWindowExA(
        WS_EX_TOPMOST,
        "LauncherClass",
        "AI-TTS Launcher",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT,
        WINDOW_WIDTH, WINDOW_HEIGHT,
        NULL, NULL, hInstance, NULL);

    ShowWindow(hwnd, nCmdShow);
    UpdateWindow(hwnd);

    MSG msg;
    while (GetMessageA(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
    return (int)msg.wParam;
}
