import platform
import os
import subprocess
import sys
import shutil
import winreg

def change_file_association(new_icon_path):
    system = platform.system()

    # Replace with the path to your icon file
    icon_path = os.path.abspath(new_icon_path)

    # Define the new file extension and description
    file_extension = ".sgworld"
    file_description = "SGWorld File"

    if system == 'Windows':
        change_windows_association(icon_path, file_extension, file_description)
    elif system == 'Linux':
        change_linux_association(icon_path, file_extension, file_description)
    elif system == 'Darwin':  # macOS
        change_macos_association(icon_path, file_extension, file_description)
    else:
        print(f"Unsupported operating system: {system}")
        sys.exit(1)

def change_windows_association(icon_path, file_extension, file_description):
    # Set up Registry keys for the new file extension
    with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, file_extension) as key:
        winreg.SetValue(key, "", winreg.REG_SZ, file_description)

    # Create a subkey for the file type
    with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{file_description}\\DefaultIcon") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, icon_path)

    # Set the file association
    with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{file_description}\\shell\\open\\command") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, f'"{os.path.abspath(sys.executable)}" "%1"')

    # Notify the shell of changes
    winreg.NotifyChangeEventLog(key, 0)

def change_linux_association(icon_path, file_extension, file_description):
    # Create a new .desktop file
    desktop_file_path = os.path.expanduser(f'~/.local/share/applications/{file_description}.desktop')
    with open(desktop_file_path, 'w') as f:
        f.write(f"[Desktop Entry]\n"
                f"Name={file_description}\n"
                f"Exec=/path/to/your/application %U\n"
                f"Icon={icon_path}\n"  # Corrected to use icon_path
                f"Terminal=false\n"
                f"Type=Application\n"
                f"MimeType=application/{file_extension}\n")

    # Update icon cache
    subprocess.run(['gtk-update-icon-cache', '--force', '--quiet', os.path.expanduser('~/.local/share/icons/hicolor')])

def change_macos_association(icon_path, file_extension, file_description):
    # Modify Info.plist file
    info_plist_path = '/path/to/YourApp.app/Contents/Info.plist'
    subprocess.run(['defaults', 'write', info_plist_path, 'CFBundleTypeName', file_description])
    subprocess.run(['defaults', 'write', info_plist_path, 'CFBundleTypeIconFile', icon_path])

if __name__ == "__main__":
    # Replace this with the actual path to your new icon file
    new_icon_path = '/path/to/new/icon.png'

    change_file_association(new_icon_path)

