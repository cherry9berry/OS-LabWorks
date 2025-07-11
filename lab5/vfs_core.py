import os
import json
from typing import List, Optional, Dict, Any

class VFSNode:
    """
    Base class for nodes in the virtual file system (files and directories).
    """
    
    def __init__(self, name: str, is_dir: bool = True):
        self.name = name
        self.is_dir = is_dir
        self.children: List['VFSNode'] = []
        self.full_path = name
        self._content = ""
        
    def update_full_path(self, parent_path: str = "") -> None:
        """
        Update the full path for the node and its children.
        
        Args:
            parent_path: Parent directory path.
        """
        if parent_path:
            self.full_path = f"{parent_path}/{self.name}"
        else:
            self.full_path = self.name
            
        for child in self.children:
            if child.is_dir:
                child.update_full_path(self.full_path)
                
    def find_node(self, path: str) -> Optional['VFSNode']:
        """
        Find a node by path.
        
        Args:
            path: Path to the node.
            
        Returns:
            VFSNode object or None if not found.
        """
        path = path.lower().strip('/')
        if not path:
            path = 'root'
            
        if self.full_path.lower() == path:
            return self
            
        for child in self.children:
            result = child.find_node(path)
            if result:
                return result
        return None
        
    def get_children_list(self, path: str = "") -> Optional[List['VFSNode']]:
        """
        Get list of children for a given path.
        
        Args:
            path: Path to the directory.
            
        Returns:
            List of child nodes or None.
        """
        if not path:
            return self.children
            
        target_node = self.find_node(path)
        return target_node.children if target_node and target_node.is_dir else None
        
    def name_exists(self, name: str, parent_path: str = "") -> bool:
        """
        Check if a name exists in the parent directory.
        
        Args:
            name: Name to check.
            parent_path: Path to the parent directory.
            
        Returns:
            True if the name exists, False otherwise.
        """
        parent_path = parent_path.lower().strip('/') or 'root'
        name = name.lower()
        
        if self.full_path.lower() == parent_path:
            return any(child.name.lower() == name for child in self.children)
            
        for child in self.children:
            if child.is_dir and child.name_exists(name, parent_path):
                return True
        return False
        
    def add_child(self, name: str, is_dir: bool = True, content: str = "") -> bool:
        """
        Add a child node.
        
        Args:
            name: Name of the node.
            is_dir: True if directory, False if file.
            content: Content for file nodes.
            
        Returns:
            True if added successfully, False otherwise.
        """
        if name.lower() == 'root':
            return False
            
        if any(child.name.lower() == name.lower() for child in self.children):
            return False
            
        new_node = VFSNode(name, is_dir)
        if not is_dir:
            new_node._content = content
        new_node.update_full_path(self.full_path)
        self.children.append(new_node)
        return True
        
    def remove_child(self, name: str) -> bool:
        """
        Remove a child node.
        
        Args:
            name: Name of the node to remove.
            
        Returns:
            True if removed, False otherwise.
        """
        name = name.lower()
        for i, child in enumerate(self.children):
            if child.name.lower() == name:
                del self.children[i]
                return True
        return False
        
    def rename_file(self, old_name: str, new_name: str) -> bool:
        """
        Rename a file.
        
        Args:
            old_name: Current name of the file.
            new_name: New name for the file.
            
        Returns:
            True if renamed, False otherwise.
        """
        if new_name.lower() == 'root':
            return False
            
        old_name = old_name.lower()
        
        if any(child.name.lower() == new_name.lower() for child in self.children):
            return False
            
        for child in self.children:
            if child.name.lower() == old_name and not child.is_dir:
                child.name = new_name
                child.full_path = f"{self.full_path}/{new_name}"
                return True
        return False
        
    def delete_file(self, name: str) -> bool:
        """
        Delete a file.
        
        Args:
            name: Name of the file to delete.
            
        Returns:
            True if deleted, False otherwise.
        """
        name = name.lower()
        for i, child in enumerate(self.children):
            if child.name.lower() == name and not child.is_dir:
                del self.children[i]
                return True
        return False
        
    def copy_file(self, file_name: str, target_path: str, root_node: 'VFSNode') -> bool:
        """
        Copy a file to another directory.
        
        Args:
            file_name: Name of the file to copy.
            target_path: Target directory path.
            root_node: Root node of the VFS.
            
        Returns:
            True if copied, False otherwise.
        """
        file_name = file_name.lower()
        
        source_file = None
        for child in self.children:
            if child.name.lower() == file_name and not child.is_dir:
                source_file = child
                break
                
        if not source_file:
            return False
            
        target_node = root_node.find_node(target_path)
        if not target_node or not target_node.is_dir:
            return False
            
        if target_node.name_exists(source_file.name, target_node.full_path):
            return False
            
        return target_node.add_child(source_file.name, False, source_file._content)
        
    def delete_directory(self, name: str) -> bool:
        """
        Delete a directory.
        
        Args:
            name: Name of the directory to delete.
            
        Returns:
            True if deleted, False otherwise.
        """
        name = name.lower()
        for i, child in enumerate(self.children):
            if child.name.lower() == name and child.is_dir:
                del self.children[i]
                return True
        return False
        
    def mount_real_directory(self, source: str, target_name: str) -> bool:
        """
        Mount a real directory.
        
        Args:
            source: Source directory path.
            target_name: Target name in VFS.
            
        Returns:
            True if mounted, False otherwise.
        """
        if target_name.lower() == 'root':
            return False
            
        if not os.path.exists(source) or not os.path.isdir(source):
            return False
            
        if self.name_exists(target_name, self.full_path):
            return False
            
        mounted_dir = VFSNode(target_name, True)
        mounted_dir.update_full_path(self.full_path)
        self.children.append(mounted_dir)
        
        try:
            self._mount_recursive(source, mounted_dir)
            return True
        except Exception:
            self.remove_child(target_name)
            return False
            
    def _mount_recursive(self, source_path: str, target_node: 'VFSNode') -> None:
        """
        Recursively mount a directory.
        
        Args:
            source_path: Source directory path.
            target_node: Target VFS node.
        """
        try:
            for item in os.listdir(source_path):
                if item.lower() == 'root':
                    continue
                    
                item_path = os.path.join(source_path, item)
                
                if os.path.isdir(item_path):
                    if target_node.add_child(item, True):
                        child_dir = next(
                            child for child in target_node.children 
                            if child.name.lower() == item.lower() and child.is_dir
                        )
                        self._mount_recursive(item_path, child_dir)
                else:
                    target_node.add_child(item, False, f"[Mounted file: {item_path}]")
                    
        except (PermissionError, OSError):
            pass
            
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert node to dictionary for serialization.
        
        Returns:
            Dictionary representing the node.
        """
        return {
            "name": self.name,
            "is_dir": self.is_dir,
            "content": self._content if not self.is_dir else "",
            "children": [child.to_dict() for child in self.children]
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VFSNode':
        """
        Create a node from a dictionary.
        
        Args:
            data: Dictionary containing node data.
            
        Returns:
            VFSNode object.
        """
        node = cls(data["name"], data["is_dir"])
        if not node.is_dir:
            node._content = data.get("content", "")
            
        for child_data in data.get("children", []):
            child = cls.from_dict(child_data)
            node.children.append(child)
            
        return node
        
    def get_content(self) -> str:
        """
        Get file content.
        
        Returns:
            Content of the file.
        """
        return self._content if not self.is_dir else ""
        
    def set_content(self, content: str) -> None:
        """
        Set file content.
        
        Args:
            content: Content to set.
        """
        if not self.is_dir:
            self._content = content

class VirtualFileSystem:
    """
    Main class for the virtual file system.
    """
    
    def __init__(self, root_name: str = "root"):
        self.root = VFSNode(root_name, True)
        self.current_directory = [root_name]
        
    def get_current_path(self) -> str:
        """
        Get the current path.
        
        Returns:
            Current path as a string.
        """
        return "/".join(self.current_directory)
        
    def resolve_path(self, path: str) -> Optional[str]:
        """
        Resolve a path relative to the current directory.
        
        Args:
            path: Path to resolve.
            
        Returns:
            Resolved path or None if invalid.
        """
        if not path:
            return self.get_current_path()
            
        path = path.strip('/')
        if not path:
            return 'root'
            
        current = self.current_directory[:]
        
        if path.startswith('root'):
            current = ['root']
            path = path[5:] if path.startswith('root/') else path[4:]
        elif path.startswith('/'):
            current = ['root']
            path = path[1:] if path else ''
            
        if path:
            parts = path.split('/')
            for i, part in enumerate(parts):
                if part == '..':
                    if len(current) > 1:
                        current.pop()
                elif part and part != '.':
                    full_path = '/'.join(current + [part]).lower()
                    node = self.root.find_node(full_path)
                    if node or (i == len(parts) - 1):  # Allow file paths for the last component
                        current.append(part)
                    else:
                        return None
                        
        return '/'.join(current) if current else 'root'
        
    def change_directory(self, path: str = None) -> bool:
        """
        Change the current directory.
        
        Args:
            path: Target directory path.
            
        Returns:
            True if changed, False otherwise.
        """
        if path:
            resolved = self.resolve_path(path)
            if resolved and self.root.find_node(resolved) and self.root.find_node(resolved).is_dir:
                self.current_directory = resolved.split('/')
                return True
            return False
        else:
            if len(self.current_directory) > 1:
                self.current_directory.pop()
                return True
            return False
            
    def create_directory(self, name: str) -> bool:
        """
        Create a directory in the current location.
        
        Args:
            name: Name of the directory.
            
        Returns:
            True if created, False otherwise.
        """
        if not name:
            return False
            
        current_path = self.get_current_path()
        current_node = self.root.find_node(current_path)
        
        if current_node and current_node.is_dir:
            return current_node.add_child(name, True)
        return False
        
    def create_file(self, name: str, content: str = "") -> bool:
        """
        Create a file in the current location.
        
        Args:
            name: Name of the file.
            content: Content for the file.
            
        Returns:
            True if created, False otherwise.
        """
        if not name:
            return False
            
        current_path = self.get_current_path()
        current_node = self.root.find_node(current_path)
        
        if current_node and current_node.is_dir:
            return current_node.add_child(name, False, content)
        return False
        
    def list_directory(self) -> List[VFSNode]:
        """
        List contents of the current directory.
        
        Returns:
            List of nodes in the current directory.
        """
        current_path = self.get_current_path()
        current_node = self.root.find_node(current_path)
        
        if current_node and current_node.is_dir:
            return current_node.children
        return []
        
    def mount_directory(self, source: str, target: str) -> bool:
        """
        Mount a real directory.
        
        Args:
            source: Source directory path.
            target: Target path in VFS.
            
        Returns:
            True if mounted, False otherwise.
        """
        target = target.strip('/')
        target_name = target.split('/')[-1]
        
        if len(target.split('/')) > 1:
            target_parent = '/'.join(target.split('/')[:-1])
            resolved_parent = self.resolve_path(target_parent)
        else:
            resolved_parent = self.get_current_path()
            
        if not resolved_parent:
            return False
            
        parent_node = self.root.find_node(resolved_parent)
        if parent_node and parent_node.is_dir:
            return parent_node.mount_real_directory(source, target_name)
        return False
        
    def unmount_directory(self, dir_name: str) -> bool:
        """
        Unmount (delete) a directory.
        
        Args:
            dir_name: Name of the directory to unmount.
            
        Returns:
            True if unmounted, False otherwise.
        """
        if not dir_name:
            return False
            
        current_path = self.get_current_path()
        current_node = self.root.find_node(current_path)
        
        if current_node and current_node.is_dir:
            return current_node.delete_directory(dir_name)
        return False
        
    def rename_file(self, old_name: str, new_name: str) -> bool:
        """
        Rename a file.
        
        Args:
            old_name: Current file name.
            new_name: New file name.
            
        Returns:
            True if renamed, False otherwise.
        """
        old_path = self.resolve_path(old_name)
        if not old_path:
            return False
            
        parent_path = '/'.join(old_path.split('/')[:-1]) or 'root'
        old_file_name = old_path.split('/')[-1]
        parent_node = self.root.find_node(parent_path)
        
        if parent_node and parent_node.is_dir:
            return parent_node.rename_file(old_file_name, new_name)
        return False
        
    def delete_file(self, name: str) -> bool:
        """
        Delete a file.
        
        Args:
            name: Name of the file to delete.
            
        Returns:
            True if deleted, False otherwise.
        """
        file_path = self.resolve_path(name)
        if not file_path:
            return False
            
        parent_path = '/'.join(file_path.split('/')[:-1]) or 'root'
        file_name = file_path.split('/')[-1]
        parent_node = self.root.find_node(parent_path)
        
        if parent_node and parent_node.is_dir:
            return parent_node.delete_file(file_name)
        return False
        
    def copy_file(self, file_name: str, target_path: str) -> bool:
        """
        Copy a file.
        
        Args:
            file_name: Name of the file to copy.
            target_path: Target directory path.
            
        Returns:
            True if copied, False otherwise.
        """
        file_path = self.resolve_path(file_name)
        if not file_path:
            return False
            
        resolved_target = self.resolve_path(target_path)
        if not resolved_target:
            return False
            
        parent_path = '/'.join(file_path.split('/')[:-1]) or 'root'
        source_file_name = file_path.split('/')[-1]
        parent_node = self.root.find_node(parent_path)
        
        if parent_node and parent_node.is_dir:
            return parent_node.copy_file(source_file_name, resolved_target, self.root)
        return False
        
    def save_to_file(self, filename: str) -> bool:
        """
        Save VFS state to a file.
        
        Args:
            filename: Name of the file to save to.
            
        Returns:
            True if saved, False otherwise.
        """
        try:
            data = {
                "root": self.root.to_dict(),
                "current_directory": self.current_directory
            }
            with open(filename, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
            
    def load_from_file(self, filename: str) -> bool:
        """
        Load VFS state from a file.
        
        Args:
            filename: Name of the file to load from.
            
        Returns:
            True if loaded, False otherwise.
        """
        if not os.path.exists(filename):
            return False
            
        try:
            with open(filename, "r", encoding='utf-8') as f:
                data = json.load(f)
                
            self.root = VFSNode.from_dict(data["root"])
            self.root.update_full_path("")
            self.current_directory = data.get("current_directory", [self.root.name])
            
            current_path = self.get_current_path()
            if not self.root.find_node(current_path):
                self.current_directory = [self.root.name]
                
            return True
        except Exception:
            return False