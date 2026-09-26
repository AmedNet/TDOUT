#include <Windows.h>
#include <tlhelp32.h>

#ifndef WDA_NONE
#define WDA_NONE 0x00000000
#endif
#ifndef WDA_MONITOR
#define WDA_MONITOR 0x00000001
#endif
#ifndef WDA_EXCLUDEFROMCAPTURE
#define WDA_EXCLUDEFROMCAPTURE 0x00000011
#endif

typedef BOOL (WINAPI *PFN_SetWindowDisplayAffinity)(HWND, DWORD);

static PFN_SetWindowDisplayAffinity g_pSetAffinity = nullptr;
static DWORD g_targetAffinity = WDA_MONITOR;
static DWORD g_currentPid = 0;

// 判断是否为 Win10 2004 (Build 19041) 及以上系统
static BOOL IsWin10_2004_OrLater()
{
    HMODULE ntdll = GetModuleHandleW(L"ntdll.dll");
    if (!ntdll) return FALSE;

    typedef LONG (WINAPI *PFN_RtlGetVersion)(PRTL_OSVERSIONINFOW);
    PFN_RtlGetVersion rtlGetVersion =
        (PFN_RtlGetVersion)GetProcAddress(ntdll, "RtlGetVersion");
    if (!rtlGetVersion) return FALSE;

    RTL_OSVERSIONINFOW vi = {};
    vi.dwOSVersionInfoSize = sizeof(vi);
    if (rtlGetVersion(&vi) != 0) return FALSE;

    return (vi.dwMajorVersion > 10) ||
           (vi.dwMajorVersion == 10 && vi.dwBuildNumber >= 19041);
}

// 对目标窗口及其最顶层根窗口设置防捕获属性
static void ApplyAffinityToHwnd(HWND hWnd)
{
    if (!hWnd || !IsWindow(hWnd) || !g_pSetAffinity)
        return;

    DWORD pid = 0;
    GetWindowThreadProcessId(hWnd, &pid);
    if (pid != g_currentPid)
        return;

    // 先应用到当前句柄
    if (!g_pSetAffinity(hWnd, g_targetAffinity))
    {
        // 若目标标志失败，回退到通用标志 WDA_MONITOR (0x01)
        g_pSetAffinity(hWnd, WDA_MONITOR);
    }

    // 很多框架窗口有根级主窗口 (GA_ROOT)，SetWindowDisplayAffinity 专门作用于 Top-Level 窗口
    HWND hRoot = GetAncestor(hWnd, GA_ROOT);
    if (hRoot && hRoot != hWnd && IsWindow(hRoot))
    {
        DWORD rootPid = 0;
        GetWindowThreadProcessId(hRoot, &rootPid);
        if (rootPid == g_currentPid)
        {
            if (!g_pSetAffinity(hRoot, g_targetAffinity))
            {
                g_pSetAffinity(hRoot, WDA_MONITOR);
            }
        }
    }
}

// 顶级窗口枚举回调
static BOOL CALLBACK EnumWindowsCallback(HWND hWnd, LPARAM /*lParam*/)
{
    ApplyAffinityToHwnd(hWnd);
    return TRUE;
}

// 线程窗口枚举回调
static BOOL CALLBACK EnumThreadWndCallback(HWND hWnd, LPARAM /*lParam*/)
{
    ApplyAffinityToHwnd(hWnd);
    return TRUE;
}

// 执行全量窗口搜索与防录屏属性应用
static void ApplyAllProcessWindows()
{
    // 1. 枚举所有顶级窗口
    EnumWindows(EnumWindowsCallback, 0);

    // 2. 通过 Toolhelp32 快照遍历当前进程的所有线程，枚举其拥有的所有窗口
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (hSnapshot != INVALID_HANDLE_VALUE)
    {
        THREADENTRY32 te;
        te.dwSize = sizeof(THREADENTRY32);
        if (Thread32First(hSnapshot, &te))
        {
            do
            {
                if (te.th32OwnerProcessID == g_currentPid)
                {
                    EnumThreadWindows(te.th32ThreadID, EnumThreadWndCallback, 0);
                }
            } while (Thread32Next(hSnapshot, &te));
        }
        CloseHandle(hSnapshot);
    }
}

// 工作线程：执行并在短时间内循环巡检几秒，防止窗口处于创建中或被重建
static DWORD WINAPI WorkerThread(LPVOID)
{
    for (int i = 0; i < 5; ++i)
    {
        ApplyAllProcessWindows();
        Sleep(300);
    }
    return 0;
}

// 保持与原版兼容的导出函数，供远程线程或测试直接调用
extern "C" __declspec(dllexport) BOOL CALLBACK EnumWindowCallBack(HWND hWnd, LPARAM lParam)
{
    ApplyAffinityToHwnd(hWnd);
    return TRUE;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID /*lpReserved*/)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
        DisableThreadLibraryCalls(hModule);
        g_currentPid = GetCurrentProcessId();

        {
            HMODULE hUser32 = GetModuleHandleW(L"user32.dll");
            if (!hUser32)
                hUser32 = LoadLibraryW(L"user32.dll");

            if (hUser32)
            {
                g_pSetAffinity = (PFN_SetWindowDisplayAffinity)GetProcAddress(
                    hUser32, "SetWindowDisplayAffinity");
            }
        }

        g_targetAffinity = IsWin10_2004_OrLater()
            ? WDA_EXCLUDEFROMCAPTURE
            : WDA_MONITOR;

        // 1. 立即同步执行一次全量应用
        ApplyAllProcessWindows();

        // 2. 启动轻量级后台线程，持续短循环监控窗口创建
        CreateThread(nullptr, 0, WorkerThread, nullptr, 0, nullptr);
        break;

    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}
