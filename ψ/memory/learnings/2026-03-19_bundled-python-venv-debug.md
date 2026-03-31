# Lesson: Bundled Python Applications Have Layered Environments

**Date**: 2026-03-19
**Source**: ComfyUI AMD AI Bundle troubleshooting

## The Pattern

When debugging bundled Python applications (like AMD AI Bundle, Anaconda, portable Python distributions), there are often multiple Python environments layered together:

1. **Embedded/system Python** — The base interpreter bundled with the app
2. **Virtual environment** — A venv that the launcher actually uses
3. **User site-packages** — The user's global Python packages

## The Trap

Fixing the wrong environment is a common mistake. The error might say "No module named X" but you need to know WHICH Python is actually running to install the module in the right place.

## The Fix

**Always check the launcher script first.** Look for:
- `.bat` files on Windows
- `.sh` shell scripts
- Desktop shortcuts or start menu entries
- The actual `python.exe` path being called

For AMD AI Bundle specifically:
```
C:\Users\...\AMD\ai_bundle\ComfyUI\Launch_ComfyUI.bat
```
This calls:
```
venv\Scripts\python.exe main.py
```

So packages must be installed in `venv\Lib\site-packages\`, not the embedded Python's site-packages.

## Workaround for Corrupted Pip

If the venv's pip is broken:
```powershell
& "path\to\embedded\python.exe" -m pip install --target="path\to\venv\Lib\site-packages" package_name
```

## Tags
- python
- debugging
- windows
- venv
- bundled-apps
- troubleshooting
