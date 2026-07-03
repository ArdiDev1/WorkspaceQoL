using System.IO;
using System.Text.Json;
using WindowLayoutManager.Models;

namespace WindowLayoutManager.Services;

public sealed class LayoutStorageService
{
    private readonly string _directoryPath;
    private readonly string _filePath;

    public LayoutStorageService()
    {
        _directoryPath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "WindowLayoutManager");

        _filePath = Path.Combine(_directoryPath, "layouts.json");

        Directory.CreateDirectory(_directoryPath);
    }

    public List<Layout> LoadLayouts()
    {
        if (!File.Exists(_filePath))
        {
            return new List<Layout>();
        }

        var raw = File.ReadAllText(_filePath);
        return string.IsNullOrWhiteSpace(raw)
            ? new List<Layout>()
            : JsonSerializer.Deserialize<List<Layout>>(raw) ?? new List<Layout>();
    }

    public void SaveLayout(Layout layout)
    {
        var layouts = LoadLayouts();
        var existingIndex = layouts.FindIndex(item => string.Equals(item.Name, layout.Name, StringComparison.OrdinalIgnoreCase));

        if (existingIndex >= 0)
        {
            layouts[existingIndex] = layout;
        }
        else
        {
            layouts.Add(layout);
        }

        var options = new System.Text.Json.JsonSerializerOptions { WriteIndented = true };
        File.WriteAllText(_filePath, System.Text.Json.JsonSerializer.Serialize(layouts, options));
    }

    public void DeleteLayout(string name)
    {
        var layouts = LoadLayouts();
        layouts.RemoveAll(item => string.Equals(item.Name, name, StringComparison.OrdinalIgnoreCase));

        var options = new System.Text.Json.JsonSerializerOptions { WriteIndented = true };
        File.WriteAllText(_filePath, System.Text.Json.JsonSerializer.Serialize(layouts, options));
    }
}
