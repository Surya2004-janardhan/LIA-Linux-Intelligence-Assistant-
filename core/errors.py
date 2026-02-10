"""
LIA Error System — Structured errors with codes, severity, and recovery suggestions.
Replaces raw string errors with typed, actionable error objects.
"""
from enum import Enum
from typing import Optional
from datetime import datetime


class ErrorSeverity(Enum):
    LOW = "low"           # Informational, task still succeeded partially
    MEDIUM = "medium"     # Task failed but system is stable
    HIGH = "high"         # Agent crashed, may affect other steps
    CRITICAL = "critical" # System-level failure, needs attention


class ErrorCode(Enum):
    # Permission errors (1xx)
    PATH_DENIED = 101
    PATH_NOT_WHITELISTED = 102
    CONNECTION_DISABLED = 103
    OS_PERMISSION_DENIED = 104
    WRITE_NOT_ALLOWED = 105
    
    # File errors (2xx)
    FILE_NOT_FOUND = 201
    DIR_NOT_FOUND = 202
    FILE_EXISTS = 203
    DISK_FULL = 204
    
    # Network errors (3xx)
    HOST_UNREACHABLE = 301
    TIMEOUT = 302
    DNS_FAILURE = 303
    PORT_CLOSED = 304
    
    # LLM errors (4xx)
    LLM_CONNECTION_FAILED = 401
    LLM_EMPTY_RESPONSE = 402
    LLM_INVALID_JSON = 403
    LLM_TIMEOUT = 404
    
    # Agent errors (5xx)
    AGENT_NOT_FOUND = 501
    TOOL_NOT_FOUND = 502
    INVALID_ARGS = 503
    AGENT_CRASHED = 504
    
    # System errors (6xx)
    COMMAND_NOT_FOUND = 601
    COMMAND_TIMEOUT = 602
    SERVICE_UNAVAILABLE = 603
    DEPENDENCY_MISSING = 604
    
    # Config errors (7xx)
    CONFIG_INVALID = 701
    CONFIG_KEY_MISSING = 702


class LIAError:
    """Structured error with code, severity, message, and recovery suggestion."""
    
    def __init__(self, code: ErrorCode, message: str, 
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 suggestion: str = None, details: str = None):
        self.code = code
        self.message = message
        self.severity = severity
        self.suggestion = suggestion or self._default_suggestion(code)
        self.details = details
        self.timestamp = datetime.now().isoformat()
    
    def _default_suggestion(self, code: ErrorCode) -> str:
        suggestions = {
            ErrorCode.PATH_DENIED: "Add the path to 'permissions.allowed_paths' in config.yaml",
            ErrorCode.CONNECTION_DISABLED: "Enable the connection in Settings > Connections",
            ErrorCode.FILE_NOT_FOUND: "Check the file path and try again",
            ErrorCode.LLM_CONNECTION_FAILED: "Ensure Ollama is running: 'ollama serve'",
            ErrorCode.LLM_TIMEOUT: "Try a simpler query or check if the model is loaded",
            ErrorCode.COMMAND_NOT_FOUND: "Install the required tool or check your PATH",
            ErrorCode.COMMAND_TIMEOUT: "The command took too long. Try with a shorter timeout.",
            ErrorCode.AGENT_NOT_FOUND: "Check agent name. Run 'lia.py status' to see available agents.",
            ErrorCode.OS_PERMISSION_DENIED: "Run LIA with appropriate permissions or check file ownership",
            ErrorCode.DEPENDENCY_MISSING: "Install missing dependency: pip install <package>",
            ErrorCode.WRITE_NOT_ALLOWED: "Database agent only supports SELECT queries for safety",
        }
        return suggestions.get(code, "Check logs for more details.")

    def to_dict(self) -> dict:
        return {
            "error_code": self.code.value,
            "error_name": self.code.name,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "details": self.details,
            "timestamp": self.timestamp
        }

    def to_user_string(self) -> str:
        """Human-readable error for GUI/CLI display."""
        parts = [f"[{self.code.name}] {self.message}"]
        if self.suggestion:
            parts.append(f"  💡 Fix: {self.suggestion}")
        return "\n".join(parts)

    def __str__(self):
        return self.to_user_string()

    def __repr__(self):
        return f"LIAError({self.code.name}, severity={self.severity.value})"


class LIAResult:
    """
    Standardized result wrapper. Every agent tool should return this.
    Replaces raw strings with structured success/error data.
    """
    def __init__(self, success: bool, data: str = "", error: LIAError = None):
        self.success = success
        self.data = data
        self.error = error
    
    @staticmethod
    def ok(data: str) -> 'LIAResult':
        return LIAResult(success=True, data=data)
    
    @staticmethod
    def fail(code: ErrorCode, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
             suggestion: str = None) -> 'LIAResult':
        return LIAResult(
            success=False, 
            data="",
            error=LIAError(code, message, severity, suggestion)
        )
    
    def __str__(self):
        if self.success:
            return self.data
        return str(self.error)
