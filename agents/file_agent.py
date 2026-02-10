import os
import shutil
import subprocess
from typing import List
from agents.base_agent import LIAAgent
from core.logger import logger
from core.llm_bridge import llm_bridge
from core.permissions import permission_manager

class FileAgent(LIAAgent):
    def __init__(self):
        super().__init__("FileAgent", ["File search", "Organization", "Backup", "Clean up"])
        self.register_tool("list_directory", self.list_directory, "Lists files in a directory")
        self.register_tool("move_file", self.move_file, "Moves a file from src to dest")
        self.register_tool("create_directory", self.create_directory, "Creates a new directory")
        self.register_tool("find_files", self.find_files, "Finds files based on a pattern")

    def list_directory(self, path: str = "."):
        if not permission_manager.is_path_allowed(path):
            return "Permission Denied: LIA does not have access to this folder."
        try:
            items = os.listdir(path)
            return "\n".join(items) if items else "Directory is empty."
        except Exception as e:
            return f"Error: {str(e)}"

    def move_file(self, src: str, dest: str):
        if not (permission_manager.is_path_allowed(src) and permission_manager.is_path_allowed(dest)):
            return "Permission Denied: Access restricted for one or both paths."
        try:
            shutil.move(src, dest)
            return f"Successfully moved {src} to {dest}"
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
        # For Linux native, we would prefer 'find', but using Python for portability
        found = []
        for r, d, f in os.walk(root):
            for file in f:
                if pattern in file:
                    found.append(os.path.join(r, file))
        return "\n".join(found) if found else "No files matched the pattern."

    def execute(self, task: str) -> str:
        logger.info(f"FileAgent executing task: {task}")
        
        # Use LLM to pick the tool and arguments
        prompt = f"""
        {self.get_capabilities_prompt()}
        
        User Task: {task}
        
        Decide which tool to use and provide the arguments in JSON format.
        Example: {{"tool": "move_file", "args": {{"src": "old.txt", "dest": "new.txt"}}}}
        """
        
        messages = [{"role": "system", "content": "You are a precise File Management Agent."},
                    {"role": "user", "content": prompt}]
        
        try:
            response = llm_bridge.generate(messages, response_format={"type": "json_object"})
            # Parse the response safely
            import json
            data = json.loads(response)
            tool_name = data.get("tool")
            args = data.get("args", {})
            
            if tool_name in self.tools:
                logger.info(f"FileAgent calling tool: {tool_name} with {args}")
                result = self.tools[tool_name]["func"](**args)
                return result
            else:
                return f"Error: Tool {tool_name} not found."
        except Exception as e:
            logger.error(f"FileAgent failed to process task: {e}")
            return f"Task failed: {str(e)}"
