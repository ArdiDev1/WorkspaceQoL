namespace WindowLayoutManager.Models;

public sealed class WindowSlot
{
    public string Title { get; set; } = string.Empty;

    public string ProcessName { get; set; } = string.Empty;

    public int ProcessId { get; set; }

    public IntPtr WindowHandle { get; set; }

    public int X { get; set; }

    public int Y { get; set; }

    public int Width { get; set; }

    public int Height { get; set; }

    public bool IsVisible { get; set; }
}
