"""
WIA Integration Tests — Verifies system integrity.

Tests:
1. Orchestrator routing (mock)
2. Safety Guard (destructive commands)
3. Permission Manager (whitelisting)
4. Context Engine (live system state)
5. Feedback RAG (history)
"""
import unittest
import os
import sys
import shutil
import tempfile

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.safety import safety_guard
from core.permissions import permission_manager, Operation
from core.context_engine import context_engine
from core.feedback import feedback_manager
from core.orchestrator import Orchestrator
from agents.sys_agent import SysAgent
from core.errors import WIAResult, ErrorCode


class TestWIA(unittest.TestCase):
    
    def setUp(self):
        # Create temp environment
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Reset Managers
        permission_manager.allowed_paths = [self.test_dir]
        permission_manager.clear_cache()
    
    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def test_safety_guard(self):
        """Verify destructive commands are blocked"""
        # Blocked
        res = safety_guard.validate_command("rm -rf /")
        self.assertEqual(res["risk_level"], "BLOCKED")
        self.assertFalse(res["allow_execution"])
        
        # High Risk + Dry Run suggestion
        res = safety_guard.validate_command("rsync -av /src /dest")
        self.assertTrue(res["dry_run_available"])
        self.assertIn("--dry-run", res["dry_run_command"])
        
        # Safe
        res = safety_guard.validate_command("ls -la")
        self.assertEqual(res["risk_level"], "SAFE")
        self.assertTrue(res["allow_execution"])

    def test_permissions(self):
        """Verify path whitelisting prevents traversal"""
        # Allowed (temp dir)
        self.assertTrue(permission_manager.is_path_allowed(self.test_dir))
        self.assertTrue(permission_manager.is_path_allowed(os.path.join(self.test_dir, "foo.txt")))
        
        # Denied (system paths)
        if os.name == 'nt':
            self.assertFalse(permission_manager.is_path_allowed("C:\\Windows\\System32"))
        else:
            self.assertFalse(permission_manager.is_path_allowed("/etc/passwd"))
            
        # Traversal attempt (should resolve to blocked path or outside whitelist)
        traversal = os.path.join(self.test_dir, "../../../etc/passwd")
        self.assertFalse(permission_manager.is_path_allowed(traversal))

    def test_context_engine(self):
        """Verify system context injection"""
        ctx = context_engine.get_context("why is my pc slow")
        self.assertIn("[OS]", ctx)
        self.assertIn("[System] CPU:", ctx)  # Performance query triggers resources
        
        ctx_git = context_engine.get_context("check git status")
        self.assertIsNotNone(ctx_git)

    def test_feedback_rag(self):
        """Verify command history recording and retrieval"""
        # Record a successful command
        feedback_manager.record_command(
            query="check ram",
            agent="SysAgent",
            tool="check_ram",
            command="",
            result="RAM: 50%",
            success=True
        )
        
        # Rate it highly
        feedback_manager.rate_last_command(5)
        
        # Search similar (RAG)
        results = feedback_manager.find_similar("check memory", min_rating=4)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['query'], "check ram")
        self.assertEqual(results[0]['rating'], 5)

if __name__ == "__main__":
    unittest.main()
