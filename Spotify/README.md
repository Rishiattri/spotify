# WFH Cross-Platform Automation

## Run

```bash
pip install -r requirements.txt
python app_modern.py
```

## Build a standalone executable (Windows)

```bash
build_modern.bat
```

Output: `dist\Spotify\Spotify.exe`

## Platforms

- Windows 10/11
- macOS Ventura/Sonoma/Sequoia (Intel + Apple Silicon)
- Ubuntu/Debian Linux

## macOS permissions

1. System Settings > Privacy & Security > Accessibility
2. Enable your terminal or Python app
3. If key simulation fails, also enable Input Monitoring

Fallback chain on macOS:
- `pyautogui` primary
- AppleScript keyboard fallback (`osascript`)
- `cliclick` mouse fallback if installed

Install `cliclick`:

```bash
brew install cliclick
```

## Ubuntu/Debian permissions and tools

Recommended packages:

```bash
sudo apt-get update
sudo apt-get install xdotool python3-xlib
```

Wayland fallback:
- install `ydotool`
- ensure `ydotoold` daemon is running

## Windows permissions

- Standard mode works with `pyautogui`
- Administrator mode is detected and logged
- If UAC prompts interrupt automation, relaunch terminal as Administrator

## Speed profiles

- Basic: 5-10s
- Medium: 3-7s
- High: 2-4s
- Ultra High: 1-2s

## Key simulation constraints

Only these keys are emitted directly:
- `Shift`
- `Ctrl`
- `Cmd` (macOS) or `Win` (Windows)
- `Page Up`
- `Page Down`
- `Tab`

## Notes

- Browser and VS Code actions use platform-specific shortcuts.
- Activity logs stream in real time in the GUI and are written to `wfh.log`.
- System tray support is enabled when `pystray` is available.
