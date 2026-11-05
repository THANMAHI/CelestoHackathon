import os
import sys
import re
import json
import math
import unittest
from datetime import datetime

# Insert root to sys.path
sys.path.insert(0, os.path.abspath("."))

from src.api.main import health, list_runs, create_run, RunCreateRequest
from fastapi import HTTPException

SANDBOX_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")
ALLOWED_CAPABILITIES = {
    "persistence", "snapshots", "celestofs", "browser", "published_ports",
    "network_policy", "safety_hooks", "host_mounts", "coding_agent_preset",
    "agentor_durable"
}
ALLOWED_ATTACKS = {"prompt_injection_exfil", "destructive_command", "suspicious_package"}
ALLOWED_POLICIES = {"resume", "rollback", "fresh"}

class TestHackathonSubmission(unittest.TestCase):

    def test_01_docker_compose_and_dockerfile(self):
        """1. Verify docker-compose.yml and Dockerfile specs."""
        self.assertTrue(os.path.exists("docker-compose.yml"), "docker-compose.yml must exist at repo root")
        self.assertTrue(os.path.exists("Dockerfile"), "Dockerfile must exist at repo root")

        with open("docker-compose.yml", "r", encoding="utf-8") as f:
            compose_text = f.read()

        self.assertIn("services:", compose_text)
        self.assertIn("api:", compose_text)
        self.assertIn("ledger:", compose_text)
        self.assertIn("8080", compose_text)
        self.assertIn("pg_isready", compose_text)
        self.assertIn("http://localhost:8080/health", compose_text)
        self.assertIn("interval:", compose_text)
        self.assertIn("timeout:", compose_text)
        self.assertIn("retries:", compose_text)
        self.assertIn("start_period:", compose_text)
        self.assertIn("./seeds", compose_text)
        self.assertIn("service_healthy", compose_text)

    def test_02_env_example_and_no_live_env(self):
        """2. Verify .env.example and absence of committed .env."""
        self.assertTrue(os.path.exists(".env.example"), ".env.example must exist at repo root")
        self.assertFalse(os.path.exists(".env"), ".env must NOT be present at repo root")

        with open(".env.example", "r", encoding="utf-8") as f:
            env_content = f.read()

        required_keys = [
            "CELESTO_PROVIDER", "CELESTO_API_KEY", "LLM_API_KEY",
            "LLM_MODEL", "DATABASE_URL", "API_PORT"
        ]
        for key in required_keys:
            self.assertIn(f"{key}=", env_content, f"Missing required env key: {key}")

        # Ensure placeholders, no live secrets
        self.assertIn("replace-me", env_content)

    def test_03_problem_statement(self):
        """3. Verify reports/problem.json."""
        self.assertTrue(os.path.exists("reports/problem.json"))
        with open("reports/problem.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("who", data)
        self.assertIn("agent_work", data)
        self.assertIn("proof_output", data)
        self.assertIn("idea_source", data)

        self.assertGreaterEqual(len(data["who"]), 40, "who must be at least 40 characters")
        self.assertGreaterEqual(len(data["agent_work"]), 40, "agent_work must be at least 40 characters")
        self.assertGreaterEqual(len(data["proof_output"]), 20, "proof_output must be at least 20 characters")
        self.assertIn(data["idea_source"], ["idea_bank", "original"])

    def test_04_command_audit_log(self):
        """4. Verify logs/commands.jsonl format and execution target."""
        self.assertTrue(os.path.exists("logs/commands.jsonl"))
        with open("logs/commands.jsonl", "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        self.assertGreaterEqual(len(lines), 1, "Must contain at least one command entry")
        has_blocked = False

        for line in lines:
            entry = json.loads(line)
            self.assertIn("ts", entry)
            self.assertIn("sandbox_name", entry)
            self.assertIn("command", entry)
            self.assertIn("decision", entry)
            self.assertIn("execution_target", entry)

            self.assertTrue(SANDBOX_REGEX.match(entry["sandbox_name"]), f"Invalid sandbox name: {entry['sandbox_name']}")
            self.assertTrue(len(entry["command"]) > 0, "Command must be non-empty")
            self.assertIn(entry["decision"], ["allow", "block"])
            self.assertEqual(entry["execution_target"], "celesto_sandbox", "Execution target MUST be celesto_sandbox")

            if entry["decision"] == "block":
                has_blocked = True

        self.assertTrue(has_blocked, "Audit log must demonstrate blocked malicious commands")

    def test_05_capabilities(self):
        """5. Verify reports/capabilities.json."""
        self.assertTrue(os.path.exists("reports/capabilities.json"))
        with open("reports/capabilities.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        caps = data.get("capabilities", [])
        self.assertGreaterEqual(len(caps), 2, "Must include at least two capabilities")

        seen_ids = set()
        for cap in caps:
            cid = cap["id"]
            self.assertIn(cid, ALLOWED_CAPABILITIES, f"Disallowed capability id: {cid}")
            self.assertNotIn(cid, seen_ids, f"Duplicate capability id: {cid}")
            seen_ids.add(cid)

            self.assertGreaterEqual(len(cap["why"]), 80, f"Capability {cid} why must be at least 80 chars")
            self.assertTrue(os.path.exists(cap["evidence_path"]), f"Evidence path must exist: {cap['evidence_path']}")

    def test_06_lifecycle_hygiene(self):
        """6. Verify reports/lifecycle.json."""
        self.assertTrue(os.path.exists("reports/lifecycle.json"))
        with open("reports/lifecycle.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertTrue(data.get("cleanup_on_success") is True)
        self.assertTrue(data.get("cleanup_on_failure") is True)
        self.assertTrue(data.get("cleanup_on_interrupt") is True)

        sbx_names = data.get("sandbox_names", [])
        self.assertGreater(len(sbx_names), 0)
        self.assertEqual(len(sbx_names), len(set(sbx_names)), "Sandbox names must be unique")

        for name in sbx_names:
            self.assertTrue(SANDBOX_REGEX.match(name), f"Invalid sandbox name: {name}")

    def test_07_reliability_eval_and_math(self):
        """7. Verify reports/reliability.json arithmetic and postmortem.md."""
        self.assertTrue(os.path.exists("reports/reliability.json"))
        with open("reports/reliability.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        runs = data.get("runs", [])
        run_count = data.get("run_count")

        self.assertGreaterEqual(run_count, 20, "Must contain at least 20 runs")
        self.assertEqual(run_count, len(runs), "run_count must equal length of runs")

        names = [r["sandbox_name"] for r in runs]
        self.assertEqual(len(names), len(set(names)), "Sandbox names in runs must be unique")

        for r in runs:
            self.assertTrue(SANDBOX_REGEX.match(r["sandbox_name"]))
            self.assertTrue(r["fresh"] is True)
            self.assertIsInstance(r["success"], bool)
            self.assertGreaterEqual(r["wall_clock_s"], 0)
            self.assertGreaterEqual(r["boot_to_ready_s"], 0)
            self.assertGreaterEqual(r["cost_usd"], 0)

        # Mathematical verifications
        computed_success_rate = sum(1 for r in runs if r["success"]) / run_count
        self.assertAlmostEqual(data["success_rate"], computed_success_rate, delta=0.001)

        # Wall clock sorted
        sorted_wall = sorted([r["wall_clock_s"] for r in runs])
        computed_median_wall = (sorted_wall[9] + sorted_wall[10]) / 2.0
        self.assertAlmostEqual(data["median_wall_clock_s"], computed_median_wall, delta=0.001)

        # p90 wall clock: 18th sorted value (1-based ceil(0.9*20)=18, index 17)
        computed_p90 = sorted_wall[17]
        self.assertAlmostEqual(data["p90_wall_clock_s"], computed_p90, delta=0.001)

        # Boot to ready median
        sorted_boot = sorted([r["boot_to_ready_s"] for r in runs])
        computed_median_boot = (sorted_boot[9] + sorted_boot[10]) / 2.0
        self.assertAlmostEqual(data["median_boot_to_ready_s"], computed_median_boot, delta=0.001)

        # Total cost
        computed_total_cost = sum(r["cost_usd"] for r in runs)
        self.assertAlmostEqual(data["total_cost_usd"], computed_total_cost, delta=0.01)

        # Postmortem verification
        postmortem_path = data["postmortem_path"]
        self.assertTrue(os.path.exists(postmortem_path))
        with open(postmortem_path, "r", encoding="utf-8") as f:
            pm_content = f.read()
        self.assertGreaterEqual(len(pm_content), 200, "postmortem.md must be at least 200 characters")

    def test_08_containment_proof(self):
        """8. Verify reports/containment.json."""
        self.assertTrue(os.path.exists("reports/containment.json"))
        with open("reports/containment.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn(data["attack"], ALLOWED_ATTACKS)
        self.assertTrue(data["blocked"] is True)
        self.assertTrue(data["host_untouched"] is True)
        self.assertGreaterEqual(len(data["evidence_paths"]), 1)
        for ep in data["evidence_paths"]:
            self.assertTrue(os.path.exists(ep), f"Evidence path must exist: {ep}")

    def test_09_failure_policy_and_trace(self):
        """9. Verify reports/failure_policy.json and failure_trace.jsonl."""
        self.assertTrue(os.path.exists("reports/failure_policy.json"))
        with open("reports/failure_policy.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["failed_step"], 7)
        self.assertEqual(data["total_steps"], 10)
        self.assertIn(data["policy"], ALLOWED_POLICIES)
        self.assertGreaterEqual(len(data["rationale"]), 200)

        trace_path = data["trace_path"]
        self.assertTrue(os.path.exists(trace_path))
        with open(trace_path, "r", encoding="utf-8") as f:
            trace_lines = [json.loads(line) for line in f if line.strip()]

        found_policy_applied = False
        for entry in trace_lines:
            if entry.get("event") == "policy_applied" and entry.get("policy") == data["policy"]:
                found_policy_applied = True
                break

        self.assertTrue(found_policy_applied, f"Trace must contain event=policy_applied with policy={data['policy']}")

    def test_10_concurrency(self):
        """10. Verify reports/concurrency.json."""
        self.assertTrue(os.path.exists("reports/concurrency.json"))
        with open("reports/concurrency.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        jobs = data.get("jobs", [])
        self.assertGreaterEqual(len(jobs), 5, "Must list at least 5 jobs")

        job_names = [j["sandbox_name"] for j in jobs]
        self.assertEqual(len(job_names), len(set(job_names)), "Job sandbox names must be unique")

        for j in jobs:
            self.assertTrue(SANDBOX_REGEX.match(j["sandbox_name"]))
            self.assertGreater(len(j["started_at"]), 0)

        self.assertGreaterEqual(len(data["breakage_notes"]), 40)

    def test_11_ledger_api_endpoints(self):
        """11. Verify Ledger API endpoints and validation."""
        # Test GET /health
        h = health()
        self.assertEqual(h, {"status": "ok"})

        # Test GET /api/runs (includes sbx-seeddemo1)
        runs = list_runs()
        self.assertGreaterEqual(len(runs), 1)
        sbx_names = [r["sandbox_name"] for r in runs]
        self.assertIn("sbx-seeddemo1", sbx_names)

        # Test POST /api/runs valid
        valid_req = RunCreateRequest(
            run_id="run-validtest01",
            sandbox_name="sbx-validtest01",
            problem_id="p-webqa",
            state="created",
            execution_target="celesto_sandbox"
        )
        res = create_run(valid_req)
        self.assertEqual(res.status_code, 201)

        # Test POST /api/runs invalid target (e.g. host) -> 400
        with self.assertRaises(HTTPException) as cm:
            create_run(RunCreateRequest(
                run_id="run-invalid01",
                sandbox_name="sbx-validtest01",
                problem_id="p-webqa",
                state="created",
                execution_target="host"
            ))
        self.assertEqual(cm.exception.status_code, 400)

        # Test POST /api/runs invalid state -> 400
        with self.assertRaises(HTTPException) as cm:
            create_run(RunCreateRequest(
                run_id="run-invalid02",
                sandbox_name="sbx-validtest01",
                problem_id="p-webqa",
                state="invalid_state_xyz",
                execution_target="celesto_sandbox"
            ))
        self.assertEqual(cm.exception.status_code, 400)

        # Test POST /api/runs invalid sandbox name -> 400
        with self.assertRaises(HTTPException) as cm:
            create_run(RunCreateRequest(
                run_id="run-invalid03",
                sandbox_name="bad-name",
                problem_id="p-webqa",
                state="created",
                execution_target="celesto_sandbox"
            ))
        self.assertEqual(cm.exception.status_code, 400)

    def test_12_readme_phrases_and_demo(self):
        """12. Verify README.md required phrases and demo existence."""
        self.assertTrue(os.path.exists("README.md"), "README.md must exist at repo root")
        with open("README.md", "r", encoding="utf-8") as f:
            readme_text = f.read()

        required_phrases = [
            "Problem statement",
            "How I used Celesto",
            "Eval report",
            "Containment test",
            "State and failure design",
            "Setup"
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, readme_text, f"README.md missing required phrase: '{phrase}'")

        # Verify demo video exists
        self.assertTrue(os.path.exists(os.path.join("demo", "walkthrough.mp4")), "demo/walkthrough.mp4 must exist")

if __name__ == "__main__":
    unittest.main()
