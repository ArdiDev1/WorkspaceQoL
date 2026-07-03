namespace WindowLayoutManager.Services;

public sealed class HotkeyService : IDisposable
{
    public event EventHandler<int>? HotkeyTriggered;

    public bool RegisterHotkey(int id, int modifiers, int key)
    {
        return true;
    }

    public void TriggerHotkey(int id)
    {
        HotkeyTriggered?.Invoke(this, id);
    }

    public void UnregisterHotkey(int id)
    {

    }

    public void Dispose()
    {
        
    }
}
