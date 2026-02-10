import os
import shutil
import re
from agents.base_agent import LIAAgent
from core.logger import logger
from core.permissions import permission_manager

class FileAgent(LIAAgent):
    def __init__(self):
        super().__init__("FileAgent", ["File search", "Organization", "Backup", "Clean up"])
        
        # Register tools WITH keywords for fast routing
        self.register_tool("list_directory", self.list_directory, 
            "Lists files in a directory",
            keywords=["list", "show files", "ls", "dir", "what's in", "contents of"])
        
        self.register_tool("move_file", self.move_file, 
            "Moves a file from src to dest",
            keywords=["move", "mv", "rename", "relocate"])
        
        self.register_tool("create_directory", self.create_directory, 
            "Creates a new directory",
            keywords=["create dir", "mkdir", "create folder", "make folder", "new folder"])
        
        self.register_tool("find_files", self.find_files, 
            "Finds files based on a pattern",
            keywords=["find", "search", "locate", "where is", "look for"])

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        """Extract arguments from natural language using regex — no LLM needed."""
        if tool_name == "list_directory":
            # Try to extract path from quotes or after prepositions
            match = re.search(r'(?:in|of|at|for)\s+["\']?([^\'"]+)["\']?', task, re.I)
            return {"path": match.group(1).strip() if match else "."}
        
        if tool_name == "create_directory":
            match = re.search(r'(?:named?|called?)\s+["\']?([^\'"]+)["\']?', task, re.I)
            if match:
                return {"path": match.group(1).strip()}
            # Try last word as path
            words = task.split()
            return {"path": words[-1] if words else "new_folder"}
        
        if tool_name == "find_files":
            match = re.search(r'(?:find|search|locate)\s+(?:all\s+)?["\']?([^\'"]+)["\']?', task, re.I)
            return {"pattern": match.group(1).strip() if match else "*"}
        
        return {}

    def list_directory(self, path: str = "."):
        if not permission_manager.is_path_allowed(path):
            return "Permission Denied: LIA does not have access to this folder."
        try:
            items = os.listdir(path)
            return "\n".join(items) if items else "Directory is empty."
        except FileNotFoundError:
            return f"Error: Directory '{path}' not found."
        except PermissionError:
            return f"Error: OS-level permission denied for '{path}'."
        except Exception as e:
            return f"Error: {str(e)}"

    def move_file(self, src: str, dest: str):
        if not (permission_manager.is_path_allowed(src) and permission_manager.is_path_allowed(dest)):
            return "Permission Denied: Access restricted for one or both paths."
        try:
            shutil.move(src, dest)
            return f"Successfully moved {src} to {dest}"
        except FileNotFoundError:
            return f"Error: Source file '{src}' not found."
        except Exception as e:
            return f"Error: {str(e)}"

    def create_directory(self, path: str):
        if not permission_manager.is_path_allowed(path):
            return "Permission Denied: Cannot create directory in restricted path."
        try:
            os.makedirs(path, exist_ok=True)
            return f"Directory created: {path}"
        except Exception as e:
            return f"Error: {str(e)}"

    def find_files(self, pattern: str, root: str = "."):
        """Uses OS-native search. Python os.walk is fast enough for local dirs."""
        found = []
        try:
            for r, d, f in os.walk(root):
                for file in f:
                    if pattern.lower() in file.lower():
                        found.append(os.path.join(r, file))
                if len(found) >= 100:  # Cap results to prevent memory issues
                    break
        except Exception as e:
            return f"Error searching: {str(e)}"
        return "\n".join(found) if found else "No files matched the pattern."

    def execute(self, task: str) -> str:
        """Uses smart_execute: keyword match first, LLM fallback for ambiguous tasks."""
        logger.info(f"FileAgent executing task: {task}")
        return self.smart_execute(task)
