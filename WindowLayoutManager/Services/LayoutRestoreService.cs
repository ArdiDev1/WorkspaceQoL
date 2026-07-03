using WindowLayoutManager.Models;

namespace WindowLayoutManager.Services;

public sealed class LayoutRestoreService
{
    public void Restore(Layout layout)
    {
        foreach (var slot in layout.Windows)
        {
            if (slot.WindowHandle != IntPtr.Zero)
            {
                NativeMethods.MoveWindow(slot.WindowHandle, slot.X, slot.Y, slot.Width, slot.Height, true);
            }
        }
    }
}
