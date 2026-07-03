using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using WindowLayoutManager.Models;

namespace WindowLayoutManager.Services;

public sealed class WindowEnumerationService
{
    public IReadOnlyList<WindowSlot> EnumerateWindows()
    {
        var windows = new List<WindowSlot>();

        User32.EnumWindows((hWnd, _) =>
        {
            if (User32.IsWindowVisible(hWnd))
            {
                var titleLength = User32.GetWindowTextLength(hWnd);
                var builder = new StringBuilder(titleLength + 1);
                User32.GetWindowText(hWnd, builder, builder.Capacity);

                var rect = new User32.RECT();
                User32.GetWindowRect(hWnd, out rect);

                User32.GetWindowThreadProcessId(hWnd, out var processId);
                var process = Process.GetProcessById((int)processId);

                windows.Add(new WindowSlot
                {
                    Title = builder.ToString(),
                    ProcessName = process.ProcessName,
                    ProcessId = (int)processId,
                    WindowHandle = hWnd,
                    X = rect.Left,
                    Y = rect.Top,
                    Width = rect.Right - rect.Left,
                    Height = rect.Bottom - rect.Top,
                    IsVisible = true,
                });
            }

            return true;
        }, IntPtr.Zero);

        return windows;
    }

    private static class User32
    {
        public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [DllImport("user32.dll")]
        public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);

        [DllImport("user32.dll")]
        public static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll")]
        public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int maxLength);

        [DllImport("user32.dll")]
        public static extern int GetWindowTextLength(IntPtr hWnd);

        [DllImport("user32.dll")]
        public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

        [StructLayout(LayoutKind.Sequential)]
        public struct RECT
        {
            public int Left;
            public int Top;
            public int Right;
            public int Bottom;
        }
    }
}
