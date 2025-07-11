from typing import List, Optional, Tuple

class Command:
    """
    Class to represent a command with arguments.
    """
    
    def __init__(self, command: str, *args: str):
        self.command = command.upper()
        self.args = list(args)
        
    def __repr__(self):
        return f"Command({self.command}, {self.args})"

class CommandParser:
    """
    Command parser for the virtual file system.
    """
    
    VALID_COMMANDS = {
        'CD', 'DIR', 'MKDIR', 'MKFILE', 'MOUNT', 'UMOUNT', 'SAVE', 'LOAD', 'RENAME', 'DEL', 'COPY', 'QUIT', 'EXIT'
    }
    
    @staticmethod
    def parse(input_command: str) -> Optional[Command]:
        """
        Parse the input command and return a Command object.
        
        Args:
            input_command: String containing the command.
            
        Returns:
            Command object or None if invalid.
        """
        input_command = input_command.strip()
        if not input_command:
            return None
            
        parts = input_command.split()
        if not parts:
            return None
            
        command = parts[0].upper()
        args = parts[1:]
        
        if command == "LS":
            command = "DIR"
        elif command == "EXIT":
            command = "QUIT"
            
        if command not in CommandParser.VALID_COMMANDS:
            return None
            
        if not CommandParser._validate_args(command, args):
            return None
            
        return Command(command, *args)
    
    @staticmethod
    def _validate_args(command: str, args: List[str]) -> bool:
        """
        Validate the number of arguments for a command.
        
        Args:
            command: Command name.
            args: List of arguments.
            
        Returns:
            True if the number of arguments is valid, False otherwise.
        """
        arg_requirements = {
            'CD': (0, 1),
            'DIR': (0, 0),
            'MKDIR': (1, 1),
            'MKFILE': (1, 1),
            'MOUNT': (2, 2),
            'UMOUNT': (1, 1),
            'SAVE': (1, 1),
            'LOAD': (1, 1),
            'RENAME': (2, 2),
            'DEL': (1, 1),
            'COPY': (2, 2),
            'QUIT': (0, 0),
            'EXIT': (0, 0),
        }
        
        if command not in arg_requirements:
            return False
            
        min_args, max_args = arg_requirements[command]
        return min_args <= len(args) <= max_args
    
    @staticmethod
    def get_help() -> str:
        """
        Return help text for commands.
        
        Returns:
            String containing help text.
        """
        help_text = """
Available commands:

Navigation:
  CD [path]           - Change directory (no argument - to parent directory)
  DIR                 - List contents of current directory

Creation:
  MKDIR <name>        - Create directory
  MKFILE <name>       - Create file

Mounting:
  MOUNT <source> <target> - Mount real directory
  UMOUNT <path>       - Unmount directory

File operations:
  RENAME <old> <new>  - Rename file
  DEL <file>          - Delete file
  COPY <file> <path>  - Copy file to directory

State management:
  SAVE <filename>     - Save VFS state to file
  LOAD <filename>     - Load VFS state from file

Exit:
  QUIT                - Exit interactive mode
        """
        return help_text.strip()

def parse_command(input_str: str) -> Optional[Command]:
    """
    Convenience function to parse a command.
    
    Args:
        input_str: String containing the command.
        
    Returns:
        Command object or None.
    """
    return CommandParser.parse(input_str)