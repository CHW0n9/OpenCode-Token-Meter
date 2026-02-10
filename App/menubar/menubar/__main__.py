"""
Main entry point for OpenCode Token Meter menubar app
with single instance detection using file-based PID lock.
"""
import sys
import os
import time
import json
import atexit
import subprocess
import tempfile
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

# Import for paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "agent"))
from agent.config import BASE_DIR

# Lock file for single instance detection
LOCK_FILE = os.path.join(BASE_DIR, "app.lock")
SHUTDOWN_TIMEOUT = 5  # Seconds to wait for old instance to shut down


class SingleInstanceManager:
    """Manages single instance detection using file-based PID lock."""
    
    def __init__(self):
        self.lock_file = LOCK_FILE
        self.have_lock = False
    
    def _read_lock(self):
        """Read PID from lock file. Returns (pid, timestamp) or (None, None)."""
        try:
            if os.path.exists(self.lock_file):
                with open(self.lock_file, 'r') as f:
                    data = json.load(f)
                    return data.get('pid'), data.get('timestamp', 0)
        except (json.JSONDecodeError, IOError, OSError):
            pass
        return None, None
    
    def _write_lock(self):
        """Write current PID to lock file."""
        try:
            os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
            with open(self.lock_file, 'w') as f:
                json.dump({
                    'pid': os.getpid(),
                    'timestamp': time.time()
                }, f)
            self.have_lock = True
            return True
        except (IOError, OSError) as e:
            print(f"Failed to write lock file: {e}")
            return False
    
    def _is_process_running(self, pid):
        """Check if a process with given PID is running."""
        if pid is None:
            return False
        
        try:
            if sys.platform == 'win32':
                # Windows: Use tasklist to check if PID exists
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                # If process exists, tasklist returns info about it
                # If not, it returns "INFO: No tasks are running..."
                return str(pid) in result.stdout
            else:
                # Unix: Send signal 0 to check if process exists
                os.kill(pid, 0)
                return True
        except Exception:
            return False
    
    def _terminate_process(self, pid):
        """Attempt to terminate a process by PID."""
        if pid is None:
            return False
        
        try:
            if sys.platform == 'win32':
                # Use taskkill to terminate the process
                result = subprocess.run(
                    ['taskkill', '/PID', str(pid), '/F'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return result.returncode == 0
            else:
                # Unix: Send SIGTERM
                import signal
                os.kill(pid, signal.SIGTERM)
                return True
        except (OSError, subprocess.SubprocessError) as e:
            print(f"Failed to terminate process {pid}: {e}")
            return False
    
    def try_acquire_lock(self):
        """
        Try to acquire the single instance lock.
        Returns True if another instance is running, False if lock acquired.
        """
        pid, timestamp = self._read_lock()
        
        if pid is not None:
            # Check if the process is actually running
            if self._is_process_running(pid):
                # Check if it's not our own PID (shouldn't happen, but safety check)
                if pid != os.getpid():
                    return True  # Another instance is running
            
            # Stale lock file - process not running, clean it up
            print(f"Stale lock file found (PID {pid} not running), cleaning up...")
            try:
                os.remove(self.lock_file)
            except OSError:
                pass
        
        # Acquire lock
        return not self._write_lock()
    
    def get_running_pid(self):
        """Get the PID of the running instance."""
        pid, _ = self._read_lock()
        return pid
    
    def terminate_existing_instance(self):
        """Terminate the existing instance and wait for it to shut down."""
        pid = self.get_running_pid()
        if pid is None:
            return True
        
        print(f"Terminating existing instance (PID {pid})...")
        
        # Send terminate signal
        self._terminate_process(pid)
        
        # Wait for process to exit
        start_time = time.time()
        while time.time() - start_time < SHUTDOWN_TIMEOUT:
            if not self._is_process_running(pid):
                print("Existing instance has terminated")
                # Clean up lock file
                try:
                    os.remove(self.lock_file)
                except OSError:
                    pass
                return True
            time.sleep(0.5)
        
        print("Timeout waiting for existing instance to terminate")
        return False
    
    def release_lock(self):
        """Release the lock by removing the lock file."""
        if self.have_lock:
            try:
                os.remove(self.lock_file)
                self.have_lock = False
            except OSError:
                pass


def show_restart_dialog():
    """Show dialog asking if user wants to restart the app."""
    msg = QMessageBox()
    msg.setWindowTitle("OpenCode Token Meter")
    msg.setText("OpenCode Token Meter is already running.")
    msg.setInformativeText("Do you want to restart the application?")
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg.setDefaultButton(QMessageBox.StandardButton.No)
    msg.setIcon(QMessageBox.Icon.Question)
    
    # Make it stay on top
    msg.setWindowFlags(msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    
    return msg.exec() == QMessageBox.StandardButton.Yes


def main():
    """Main entry point with single instance check."""
    # Ensure logs directory exists early
    log_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "OpenCode Token Meter")
    os.makedirs(log_dir, exist_ok=True)
    app_log_path = os.path.join(log_dir, "app.log")

    # Redirect stdout and stderr to a log file for better debugging on Windows
    # Use 'a' to append to existing logs. We try-except in case of locking.
    try:
        log_file = open(app_log_path, "a", encoding="utf-8", buffering=1) # Line buffered
        sys.stdout = log_file
        sys.stderr = log_file
        print(f"\n--- App Start: {time.ctime()} ---")
    except Exception as e:
        # If we can't open the log, we just continue with console output
        print(f"Warning: Could not redirect output to {app_log_path}: {e}")

    print(f"Working Directory: {os.getcwd()}")
    print(f"Executable: {sys.executable}")
    print(f"Arguments: {sys.argv}")

    if sys.platform == 'win32':
        try:
            import faulthandler
            crash_log = os.path.join(log_dir, "menubar_crash.log")
            faulthandler.enable(open(crash_log, "a", encoding="utf-8"))
            print(f"[Windows] Crash log enabled: {crash_log}")
        except Exception as e:
            print(f"[Windows] Failed to enable crash log: {e}")

    # Set Windows App User Model ID (AUMID) for proper notification icons
    if sys.platform == 'win32':
        try:
            import ctypes
            from ctypes import wintypes
            import winreg
            
            app_id = "OpenCode.TokenMeter"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            print(f"[Windows] Set App User Model ID: {app_id}")
            
            # Find icon path
            icon_path = None
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, 'resources', 'AppIcon.ico')
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                icon_path = os.path.join(script_dir, '..', 'resources', 'AppIcon.ico')
            
            if icon_path and os.path.exists(icon_path):
                icon_path = os.path.abspath(icon_path).replace('/', '\\')
                print(f"[Windows] Found icon for registry: {icon_path}")
                
                # Register the icon in Windows registry
                reg_path = f"Software\\Classes\\AppUserModelId\\{app_id}"
                try:
                    # Use KEY_ALL_ACCESS to ensure we have permissions
                    key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_ALL_ACCESS)
                    winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "OpenCode Token Meter")
                    winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, icon_path)
                    winreg.SetValueEx(key, "IconPath", 0, winreg.REG_SZ, icon_path)
                    winreg.SetValueEx(key, "ShowInSettings", 0, winreg.REG_DWORD, 1)
                    winreg.CloseKey(key)
                    print(f"[Windows] Successfully registered icon in registry")
                except Exception as e:
                    print(f"[Windows] Failed to register icon in registry: {e}")

                # Ensure Start Menu shortcut with AUMID
                # try:
                #     start_menu_dir = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")
                #     shortcut_path = os.path.join(start_menu_dir, "OpenCode Token Meter.lnk")
                #     
                #     exe_path = os.path.abspath(sys.executable).replace('/', '\\')
                #     # If running as python.exe, we might want the script instead
                #     if "python.exe" in exe_path.lower() or "pythonw.exe" in exe_path.lower():
                #         target_path = os.path.abspath(sys.argv[0]).replace('/', '\\')
                #         work_dir = os.path.dirname(target_path)
                #     else:
                #         target_path = exe_path
                #         work_dir = os.path.dirname(exe_path)
                # 
                #     print(f"[Windows] Shortcut target: {target_path}")
                #     
                #     script = f"""
                # $shell = New-Object -ComObject WScript.Shell
                # $shortcut = $shell.CreateShortcut('{shortcut_path}')
                # $shortcut.TargetPath = '{target_path}'
                # $shortcut.WorkingDirectory = '{work_dir}'
                # $shortcut.IconLocation = '{icon_path}'
                # $shortcut.Save()
                # $shell = New-Object -ComObject Shell.Application
                # $folder = $shell.Namespace('{start_menu_dir}')
                # $item = $folder.ParseName('OpenCode Token Meter.lnk')
                # $item.ExtendedProperty('System.AppUserModel.ID') = '{app_id}'
                # """
                #     ps_script_path = os.path.join(tempfile.gettempdir(), "opencode_shortcut_v2.ps1")
                #     with open(ps_script_path, "w", encoding="utf-8") as f:
                #         f.write(script)
                #     
                #     result = subprocess.run(
                #         ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_script_path],
                #         capture_output=True,
                #         text=True,
                #         creationflags=subprocess.CREATE_NO_WINDOW
                #     )
                #     if result.returncode == 0:
                #         print("[Windows] Start Menu shortcut ensured with AUMID via PowerShell")
                #     else:
                #         print(f"[Windows] PowerShell shortcut error: {result.stderr}")
                # except Exception as e:
                #     print(f"[Windows] Failed to create Start Menu shortcut: {e}")
                pass
            else:
                print(f"[Windows] Icon file NOT FOUND at: {icon_path}")
        except Exception as e:
            print(f"[Windows] Global AUMID setup error: {e}")
    
    # Create QApplication AFTER setting AUMID
    app = QApplication(sys.argv)

    app.setQuitOnLastWindowClosed(False)  # Keep running even when windows are closed

    # Set application display name for better UX
    app.setApplicationName("OpenCode Token Meter")
    app.setApplicationDisplayName("OpenCode Token Meter")
    app.setOrganizationName("OpenCode")
    
    # Initialize single instance manager
    manager = SingleInstanceManager()
    
    # Check if another instance is running
    is_running = manager.try_acquire_lock()
    
    if is_running:
        # Another instance is running - show dialog
        result = show_restart_dialog()
        
        if result:
            # User wants to restart - terminate old instance
            print("User requested restart, terminating existing instance...")
            
            if manager.terminate_existing_instance():
                # Try to acquire lock again
                time.sleep(0.5)  # Small delay to ensure lock file is released
                
                if manager.try_acquire_lock():
                    # Still can't get lock
                    QMessageBox.warning(
                        None, 
                        "OpenCode Token Meter",
                        "Could not restart the application.\nPlease try again."
                    )
                    sys.exit(1)
                else:
                    print("Successfully acquired lock, starting app...")
            else:
                QMessageBox.warning(
                    None, 
                    "OpenCode Token Meter",
                    "Old instance did not shut down in time.\nPlease close it manually and try again."
                )
                sys.exit(1)
        else:
            # User chose not to restart, just exit
            sys.exit(0)
    
    # Import app module here to avoid loading it when we might exit early
    from menubar.app import OpenCodeTokenMeter
    
    # Create main app window
    window = OpenCodeTokenMeter()
    
    # Register cleanup on exit
    atexit.register(manager.release_lock)
    
    # Run the application
    exit_code = app.exec()
    
    # Cleanup
    manager.release_lock()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
