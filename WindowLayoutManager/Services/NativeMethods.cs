using System.Runtime.InteropServices;

namespace WindowLayoutManager.Services;

internal static class NativeMethods
{
    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int x, int y, int width, int height, bool repaint);
}
