import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

COMMAND_LOG_PATH = os.path.join("logs", "commands.jsonl")

# Regular expressions for blocked commands (destructive operations & exfiltration)
BLOCKED_PATTERNS = [
    re.compile(r"rm\s+-rf\s+(/|\*|~|/\w+)", re.IGNORECASE),
    re.compile(r"curl.*evil-c2", re.IGNORECASE),
    re.compile(r"curl.*exfil", re.IGNORECASE),
    re.compile(r"wget.*exfil", re.IGNORECASE),
    re.compile(r"\$CANARY_SECRET", re.IGNORECASE),
    re.compile(r"mkfs", re.IGNORECASE),
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:", re.IGNORECASE), # fork bomb
    re.compile(r"cat\s+/etc/shadow", re.IGNORECASE),
]

class CommandBlockedError(Exception):
    """Raised when a command is blocked by Celesto safety hooks before VM execution."""
    def __init__(self, command: str, reason: str):
        super().__init__(f"Command blocked by Celesto Safety Hook: '{command}'. Reason: {reason}")
        self.command = command
        self.reason = reason

def log_command_audit(sandbox_name: str, command: str, decision: str) -> Dict[str, Any]:
    """Appends an audited command entry to logs/commands.jsonl."""
    os.makedirs("logs", exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "sandbox_name": sandbox_name,
        "command": command.strip(),
        "decision": decision,
        "execution_target": "celesto_sandbox"
    }
    with open(COMMAND_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

class CommandSafetyHook:
    """Pre-execution safety callback that inspects and filters guest VM commands."""

    def __init__(self, sandbox_name: str):
        self.sandbox_name = sandbox_name

    def inspect(self, command: str) -> Tuple[bool, str]:
        """Inspects command against security policies.
        Returns: (is_allowed: bool, reason: str)
        """
        for pattern in BLOCKED_PATTERNS:
            if pattern.search(command):
                return False, f"Matched forbidden security pattern: {pattern.pattern}"
        return True, "Passed security inspection"

    def execute_with_guard(self, command: str) -> bool:
        """Evaluates command, logs the decision to commands.jsonl, and enforces safety."""
        is_allowed, reason = self.inspect(command)
        if not is_allowed:
            log_command_audit(self.sandbox_name, command, decision="block")
            raise CommandBlockedError(command, reason)
        log_command_audit(self.sandbox_name, command, decision="allow")
        return True
