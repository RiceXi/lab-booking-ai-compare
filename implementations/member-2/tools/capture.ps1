# Dev helper: capture a window (identified by process id) and save it as PNG.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File tools\capture.ps1 -Out "docs\screenshots\main-window.png" -Tab equipment
#
# NOTE: this file must stay pure ASCII. Windows PowerShell 5.1 reads .ps1 files
# as ANSI unless they carry a UTF-8 BOM, so non-ASCII literals would break parsing.
# The window is located by process id instead of by (non-ASCII) window title.

param(
    [Parameter(Mandatory = $true)][string]$Out,
    [int]$WaitSeconds = 4,
    [string]$WorkDir = "D:\lab-booking-ai-compare\implementations\member-2",
    [string]$Tab = "equipment",
    [double]$Seconds = 12
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing

$csharp = @"
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Runtime.InteropServices;

public class WindowCapture {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }

    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")]
    private static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")]
    private static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint flags);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    public static IntPtr FindByProcess(int targetPid) {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            if (pid == (uint)targetPid && IsWindowVisible(hWnd)) {
                RECT r;
                GetWindowRect(hWnd, out r);
                if ((r.Right - r.Left) > 200 && (r.Bottom - r.Top) > 200) { found = hWnd; return false; }
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }

    public static bool Capture(IntPtr hwnd, string path) {
        RECT rect;
        if (!GetWindowRect(hwnd, out rect)) return false;
        int width = rect.Right - rect.Left;
        int height = rect.Bottom - rect.Top;
        if (width <= 0 || height <= 0) return false;
        using (Bitmap bitmap = new Bitmap(width, height))
        using (Graphics graphics = Graphics.FromImage(bitmap)) {
            IntPtr hdc = graphics.GetHdc();
            PrintWindow(hwnd, hdc, 2); // 2 = PW_RENDERFULLCONTENT
            graphics.ReleaseHdc(hdc);
            bitmap.Save(path, System.Drawing.Imaging.ImageFormat.Png);
        }
        return true;
    }
}
"@

Add-Type -TypeDefinition $csharp -ReferencedAssemblies System.Drawing

$proc = Start-Process -FilePath 'python' -ArgumentList "tools\screenshot.py --tab $Tab --seconds $Seconds" `
    -WorkingDirectory $WorkDir -WindowStyle Hidden -PassThru
Start-Sleep -Seconds $WaitSeconds

$hwnd = [WindowCapture]::FindByProcess($proc.Id)
if ($hwnd -eq [IntPtr]::Zero) {
    Write-Error "window not found for pid $($proc.Id)"
}
[WindowCapture]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 800

$dir = Split-Path -Parent $Out
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

$ok = [WindowCapture]::Capture($hwnd, $Out)
$proc.WaitForExit(20000) | Out-Null
if ($ok) {
    $item = Get-Item $Out
    Write-Output ("saved: {0} ({1} bytes)" -f $item.FullName, $item.Length)
} else {
    Write-Error "capture failed"
}
