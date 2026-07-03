namespace WindowLayoutManager.Models;

public sealed class Layout
{
    public string Name { get; set; } = string.Empty;

    public List<WindowSlot> Windows { get; set; } = new();

    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
}
