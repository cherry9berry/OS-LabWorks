#!/usr/bin/env python3
"""
Main commands:
- CD [path] - change directory
- DIR - list contents
- MKDIR <name> - create directory
- MKFILE <name> - create file
- MOUNT <source> <target> - mount real directory
- UMOUNT <path> - unmount directory
- RENAME <old> <new> - rename file
- DEL <file> - delete file
- COPY <file> <path> - copy file
- SAVE <filename> - save state
- LOAD <filename> - load state
- QUIT - exit interactive mode
"""

import sys
import os
from vfs_manager import VFSManager, VFSDebugger
from vfs_commands import CommandParser

def main():
    """
    Main function to handle command-line arguments or start interactive mode.
    """
    manager = VFSManager("root")
    
    if len(sys.argv) > 1 and sys.argv[1].lower() == '--test':
        run_tests(manager)
    else:
        manager.run()

def run_tests(manager):
    """
    Run basic tests for the virtual file system.
    """
    print("Running VFS tests")
    
    test_cases = [
        ("MKDIR test1", "Creating directory", lambda: manager.vfs.root.name_exists("test1", "root")),
        ("MKDIR test2", "Creating second directory", lambda: manager.vfs.root.name_exists("test2", "root")),
        ("CD test1", "Changing directory", lambda: manager.vfs.get_current_path() == "root/test1"),
        ("MKFILE file1.txt", "Creating file", lambda: manager.vfs.root.find_node("root/test1").name_exists("file1.txt", "root/test1")),
        ("MKFILE file2.txt", "Creating second file", lambda: manager.vfs.root.find_node("root/test1").name_exists("file2.txt", "root/test1")),
        ("DIR", "Listing contents", lambda: len(manager.vfs.list_directory()) == 2),
        ("CD ..", "Returning to parent directory", lambda: manager.vfs.get_current_path() == "root"),
        ("COPY test1/file1.txt test2", "Copying file", lambda: manager.vfs.root.find_node("root/test2").name_exists("file1.txt", "root/test2")),
        ("RENAME test1/file2.txt renamed.txt", "Renaming file", lambda: manager.vfs.root.find_node("root/test1").name_exists("renamed.txt", "root/test1") and not manager.vfs.root.find_node("root/test1").name_exists("file2.txt", "root/test1")),
        ("DEL test1/renamed.txt", "Deleting file", lambda: not manager.vfs.root.find_node("root/test1").name_exists("renamed.txt", "root/test1")),
        ("SAVE test_state.json", "Saving state", lambda: os.path.exists("test_state.json")),
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for command_str, description, check_func in test_cases:
        print(f"\nTest: {description}: {command_str}")
        
        command = CommandParser.parse(command_str)
        if command:
            try:
                manager.execute_command(command)
                if check_func():
                    success_count += 1
                    print("SUCCESS")
                else:
                    print("ERROR: Operation not performed correctly")
            except Exception as e:
                print(f"ERROR: {e}")
        else:
            print("ERROR: Invalid command")
    
    print("\nTest results")
    print(f"Successful: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("All tests passed successfully")
    else:
        print(f"Some tests failed: {total_count - success_count} errors")
    
    print("\nFinal VFS state")
    VFSDebugger.show_vfs_info(manager)

if __name__ == "__main__":
    main()