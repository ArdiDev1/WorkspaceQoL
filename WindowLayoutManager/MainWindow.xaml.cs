using System.Windows;
using WindowLayoutManager.Models;
using WindowLayoutManager.Services;

namespace WindowLayoutManager;

public partial class MainWindow : Window
{
    private readonly LayoutStorageService _layoutStorageService = new();
    private readonly WindowEnumerationService _windowEnumerationService = new();
    private readonly LayoutRestoreService _layoutRestoreService = new();
    private readonly HotkeyService _hotkeyService = new();

    public MainWindow()
    {
        InitializeComponent();
        Loaded += MainWindow_Loaded;
    }

    private void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        RefreshLayouts();
    }

    private void RefreshLayouts()
    {
        layoutsListBox.ItemsSource = _layoutStorageService.LoadLayouts();
    }

    private void SaveLayoutButton_Click(object sender, RoutedEventArgs e)
    {
        var name = nameTextBox.Text.Trim();

        if (string.IsNullOrWhiteSpace(name))
        {
            MessageBox.Show("Please enter a layout name.", "Window Layout Manager", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        var layout = new Layout
        {
            Name = name,
            Windows = _windowEnumerationService.EnumerateWindows().ToList(),
        };

        _layoutStorageService.SaveLayout(layout);
        RefreshLayouts();
    }

    private void RestoreLayoutButton_Click(object sender, RoutedEventArgs e)
    {
        if (layoutsListBox.SelectedItem is Layout layout)
        {
            _layoutRestoreService.Restore(layout);
        }
    }

    private void DeleteLayoutButton_Click(object sender, RoutedEventArgs e)
    {
        if (layoutsListBox.SelectedItem is Layout layout)
        {
            _layoutStorageService.DeleteLayout(layout.Name);
            RefreshLayouts();
        }
    }

    private void SetHotkeyButton_Click(object sender, RoutedEventArgs e)
    {
        _hotkeyService.RegisterHotkey(1, 0, 0);
        _hotkeyService.TriggerHotkey(1);
        MessageBox.Show($"Hotkey placeholder set to: {hotkeyTextBox.Text}", "Window Layout Manager", MessageBoxButton.OK, MessageBoxImage.Information);
    }
}