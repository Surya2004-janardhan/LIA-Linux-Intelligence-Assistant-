import os
import shutil
import re
from agents.base_agent import LIAAgent
from core.logger import logger
from core.os_layer import os_layer
from core.permissions import permission_manager, Operation
from core.errors import LIAResult, ErrorCode, ErrorSeverity

class FileAgent(LIAAgent):
    def __init__(self):
        super().__init__("FileAgent", ["File search", "Organization", "Backup", "Clean up"])
        
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
        self.register_tool("file_info", self.file_info,
            "Shows size, modified date, and type of a file",
            keywords=["info", "size", "details", "about", "how big"])

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        if tool_name == "list_directory":
            match = re.search(r'(?:in|of|at|for)\s+["\']?([^\'"]+)["\']?', task, re.I)
            return {"path": match.group(1).strip() if match else "."}
        if tool_name == "create_directory":
            match = re.search(r'(?:named?|called?)\s+["\']?([^\'"]+)["\']?', task, re.I)
            if match:
                return {"path": match.group(1).strip()}
            words = task.split()
            return {"path": words[-1] if words else "new_folder"}
        if tool_name == "find_files":
            match = re.search(r'(?:find|search|locate)\s+(?:all\s+)?["\']?(.+?)["\']?\s*$', task, re.I)
            return {"pattern": match.group(1).strip() if match else "*"}
        if tool_name == "file_info":
            match = re.search(r'(?:info|details|about|size)\s+(?:of\s+)?["\']?(.+?)["\']?\s*$', task, re.I)
            return {"path": match.group(1).strip() if match else "."}
        return {}

    def list_directory(self, path: str = ".") -> str:
        if not permission_manager.is_path_allowed(path, Operation.READ):
            return str(LIAResult.fail(ErrorCode.PATH_DENIED, f"Access denied: {path}"))
        
        result = os_layer.safe_listdir(path)
        if not result["success"]:
            return str(LIAResult.fail(ErrorCode.DIR_NOT_FOUND, result["error"]))
        
        items = result["items"]
        if not items:
            return "Directory is empty."
        
        # Categorize: dirs vs files
        resolved = os_layer.resolve_path(path)
        dirs = []
        files = []
        for item in sorted(items):
            full = os.path.join(resolved, item)
            if os.path.isdir(full):
                dirs.append(f"📁 {item}/")
            else:
                size = os.path.getsize(full) if os.path.exists(full) else 0
                files.append(f"📄 {item} ({self._human_size(size)})")
        
        output = []
        if dirs:
            output.extend(dirs)
        if files:
            output.extend(files)
        output.append(f"\n({len(dirs)} folders, {len(files)} files)")
        return "\n".join(output)

    def move_file(self, src: str, dest: str) -> str:
        if not permission_manager.is_path_allowed(src, Operation.READ):
            return str(LIAResult.fail(ErrorCode.PATH_DENIED, f"Cannot read: {src}"))
        if not permission_manager.is_path_allowed(dest, Operation.WRITE):
            return str(LIAResult.fail(ErrorCode.PATH_DENIED, f"Cannot write to: {dest}"))
        if not permission_manager.check_agent_operation("FileAgent", Operation.WRITE):
            return str(LIAResult.fail(ErrorCode.PATH_DENIED, "FileAgent write permission denied"))
        
        try:
            shutil.move(src, dest)
            return f"✅ Moved: {src} → {dest}"
        except FileNotFoundError:
            return str(LIAResult.fail(ErrorCode.FILE_NOT_FOUND, f"Source not found: {src}"))
        except PermissionError:
            return str(LIAResult.fail(ErrorCode.OS_PERMISSION_DENIED, f"OS denied access to move {src}"))
        except Exception as e:
            return str(LIAResult.fail(ErrorCode.FILE_NOT_FOUND, str(e)))

    def create_directory(self, path: str) -> str:
        if not permission_manager.is_path_allowed(path, Operation.WRITE):
            return str(LIAResult.fail(ErrorCode.PATH_DENIED, f"Cannot create directory at: {path}"))
        try:
            os.makedirs(path, exist_ok=True)
            return f"✅ Directory created: {path}"
        except PermissionError:
            return str(LIAResult.fail(ErrorCode.OS_PERMISSION_DENIED, f"OS denied: {path}"))
        except Exception as e:
            return str(LIAResult.fail(ErrorCode.FILE_NOT_FOUND, str(e)))

    def find_files(self, pattern: str, root: str = ".") -> str:
        found = []
        try:
            for r, d, f in os.walk(root):
                for file in f:
                    if pattern.lower() in file.lower():
                        full_path = os.path.join(r, file)
                        size = self._human_size(os.path.getsize(full_path))
                        found.append(f"  {full_path} ({size})")
                if len(found) >= 100:
                    found.append(f"  ... (capped at 100 results)")
                    break
        except PermissionError:
            return str(LIAResult.fail(ErrorCode.OS_PERMISSION_DENIED, f"OS denied access to {root}"))
        except Exception as e:
            return str(LIAResult.fail(ErrorCode.FILE_NOT_FOUND, str(e)))
        
        if not found:
            return f"No files matching '{pattern}' found."
        return f"Found {len(found)} matches:\n" + "\n".join(found)

    def file_info(self, path: str) -> str:
        resolved = os_layer.resolve_path(path)
        if not os.path.exists(resolved):
            return str(LIAResult.fail(ErrorCode.FILE_NOT_FOUND, f"Not found: {path}"))
        
        import time
        stat = os.stat(resolved)
        modified = time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))
        
        return (f"Path: {resolved}\n"
                f"Type: {'Directory' if os.path.isdir(resolved) else 'File'}\n"
                f"Size: {self._human_size(stat.st_size)}\n"
                f"Modified: {modified}")

    def _human_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"

    def execute(self, task: str) -> str:
        logger.info(f"FileAgent executing: {task}")
        return self.smart_execute(task)
