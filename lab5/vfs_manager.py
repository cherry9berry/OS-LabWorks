from typing import Optional
from vfs_core import VirtualFileSystem
from vfs_commands import Command, CommandParser

class VFSManager:
    """
    Manager for the virtual file system.
    Handles commands and manages state.
    """
    
    def __init__(self, root_name: str = "root"):
        self.vfs = VirtualFileSystem(root_name)
        self.is_running = False
        
    def get_prompt(self) -> str:
        """
        Get the prompt for interactive mode.
        
        Returns:
            Prompt string with current path.
        """
        return f"{self.vfs.get_current_path()}> "
        
    def run(self) -> None:
        """
        Start interactive mode for command input.
        """
        self.is_running = True
        print("Virtual File System.")
        
        while self.is_running:
            command_str = input(self.get_prompt()).strip()
            command = CommandParser.parse(command_str)
            
            if command:
                if command.command in ["QUIT", "EXIT"]:
                    self.is_running = False
                else:
                    self.execute_command(command)
            else:
                print("Error: Invalid command. Type QUIT to exit.")
                
    def execute_command(self, command: Command) -> None:
        """
        Execute a command.
        
        Args:
            command: Command object to execute.
        """
        if not command:
            return
            
        try:
            method_name = f"_cmd_{command.command.lower()}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                method(command.args)
            else:
                print(f"Error: Unknown command '{command.command}'")
        except Exception as e:
            print(f"Error executing command: {e}")
            
    def _cmd_cd(self, args) -> None:
        """
        Execute CD command.
        
        Args:
            args: List of arguments.
        """
        path = args[0] if args else None
        if self.vfs.change_directory(path):
            if path:
                print(f"Changed directory to: {path}")
        else:
            if path:
                print(f"Error: Directory '{path}' not found")
            else:
                print("Error: Cannot move above root directory")
        print()
        
    def _cmd_dir(self, args) -> None:
        """
        Execute DIR command.
        
        Args:
            args: List of arguments.
        """
        print("Current directory contents:")
        children = self.vfs.list_directory()
        
        if not children:
            print("  (empty)")
        else:
            for child in children:
                if child.is_dir:
                    print(f"  [{child.name}]/")
                else:
                    print(f"  {child.name}")
        print()
        
    def _cmd_mkdir(self, args) -> None:
        """
        Execute MKDIR command.
        
        Args:
            args: List of arguments.
        """
        if not args:
            print("Error: Specify directory name")
            print()
            return
            
        dir_name = args[0]
        if self.vfs.create_directory(dir_name):
            print(f"Directory '{dir_name}' created")
        else:
            print(f"Error: Could not create directory '{dir_name}'")
        print()
        
    def _cmd_mkfile(self, args) -> None:
        """
        Execute MKFILE command.
        
        Args:
            args: List of arguments.
        """
        if not args:
            print("Error: Specify file name")
            print()
            return
            
        file_name = args[0]
        if self.vfs.create_file(file_name):
            print(f"File '{file_name}' created")
        else:
            print(f"Error: Could not create file '{file_name}'")
        print()
        
    def _cmd_mount(self, args) -> None:
        """
        Execute MOUNT command.
        
        Args:
            args: List of arguments.
        """
        if len(args) < 2:
            print("Error: Specify source and target")
            print()
            return
            
        source, target = args
        if self.vfs.mount_directory(source, target):
            print(f"Directory '{source}' mounted as '{target}'")
        else:
            print(f"Error mounting '{source}' to '{target}'")
        print()
        
    def _cmd_umount(self, args) -> None:
        """
        Execute UMOUNT command.
        
        Args:
            args: List of arguments.
        """
        if not args:
            print("Error: Specify path to unmount")
            print()
            return
            
        path = args[0]
        if self.vfs.unmount_directory(path):
            print(f"Directory '{path}' unmounted")
        else:
            print(f"Error: Directory '{path}' not found")
        print()
        
    def _cmd_rename(self, args) -> None:
        """
        Execute RENAME command.
        
        Args:
            args: List of arguments.
        """
        if len(args) < 2:
            print("Error: Specify old and new file name")
            print()
            return
            
        old_name, new_name = args
        if self.vfs.rename_file(old_name, new_name):
            print(f"File renamed: '{old_name}' -> '{new_name}'")
        else:
            print(f"Error: Could not rename file '{old_name}'")
        print()
        
    def _cmd_del(self, args) -> None:
        """
        Execute DEL command.
        
        Args:
            args: List of arguments.
        """
        if not args:
            print("Error: Specify file name")
            print()
            return
            
        file_name = args[0]
        if self.vfs.delete_file(file_name):
            print(f"File '{file_name}' deleted")
        else:
            print(f"Error: File '{file_name}' not found")
        print()
        
    def _cmd_copy(self, args) -> None:
        """
        Execute COPY command.
        
        Args:
            args: List of arguments.
        """
        if len(args) < 2:
            print("Error: Specify file name and target path")
            print()
            return
            
        file_name, target_path = args
        if self.vfs.copy_file(file_name, target_path):
            print(f"File '{file_name}' copied to '{target_path}'")
        else:
            print(f"Error: Could not copy file '{file_name}' to '{target_path}'")
        print()
        
    def _cmd_save(self, args) -> None:
        """
        Execute SAVE command.
        
        Args:
            args: List of arguments.
        """
        if not args:
            print("Error: Specify file name")
            print()
            return
            
        filename = args[0]
        if self.vfs.save_to_file(filename):
            print(f"VFS state saved to '{filename}'")
        else:
            print(f"Error saving to '{filename}'")
        print()
        
    def _cmd_load(self, args) -> None:
        """
        Execute LOAD command.
        
        Args:
            args: List of arguments.
        """
        if not args:
            print("Error: Specify file name")
            print()
            return
            
        filename = args[0]
        if self.vfs.load_from_file(filename):
            print(f"VFS state loaded from '{filename}'")
        else:
            print(f"Error loading from '{filename}'")
        print()

class VFSDebugger:
    """
    Utilities for debugging the virtual file system.
    """
    
    @staticmethod
    def print_tree(node, level=0):
        """
        Print the file system tree.
        
        Args:
            node: Node to start printing from.
            level: Indentation level.
        """
        indent = "  " * level
        marker = "[D]" if node.is_dir else "[F]"
        print(f"{indent}{marker} {node.name}")
        
        if node.is_dir:
            for child in node.children:
                VFSDebugger.print_tree(child, level + 1)
    
    @staticmethod
    def show_vfs_info(vfs_manager):
        """
        Show information about the VFS state.
        
        Args:
            vfs_manager: VFSManager instance.
        """
        vfs = vfs_manager.vfs
        print("VFS information")
        print(f"Current path: {vfs.get_current_path()}")
        print(f"Root directory: {vfs.root.name}")
        print("\nFile system structure:")
        VFSDebugger.print_tree(vfs.root)
        print()

class VFSValidator:
    """
    Validator for checking VFS integrity.
    """
    
    @staticmethod
    def validate_paths(node, expected_path=""):
        """
        Check path correctness in the tree.
        
        Args:
            node: Node to validate.
            expected_path: Expected path for the node.
            
        Returns:
            List of errors.
        """
        errors = []
        
        if expected_path and node.full_path != expected_path:
            errors.append(f"Invalid path for node '{node.name}': expected '{expected_path}', got '{node.full_path}'")
        
        for child in node.children:
            child_expected_path = f"{node.full_path}/{child.name}" if node.full_path != child.name else child.name
            child_errors = VFSValidator.validate_paths(child, child_expected_path)
            errors.extend(child_errors)
            
        return errors
    
    @staticmethod
    def check_name_conflicts(node):
        """
        Check for name conflicts in a directory.
        
        Args:
            node: Node to check.
            
        Returns:
            List of errors.
        """
        errors = []
        
        if node.is_dir:
            names = [child.name.lower() for child in node.children]
            if len(names) != len(set(names)):
                errors.append(f"Name conflict in directory '{node.full_path}'")
        
        for child in node.children:
            if child.is_dir:
                child_errors = VFSValidator.check_name_conflicts(child)
                errors.extend(child_errors)
                
        return errors