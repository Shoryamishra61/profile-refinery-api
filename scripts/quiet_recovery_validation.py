"""Quiet-period recovery experiment + full live validation.

Hypothesis: LinkedIn's flag decays with complete silence (every 10-minute
probe may have kept resetting it). Protocol:
  1. absolute quiet: zero LinkedIn requests for QUIET_MINUTES
  2. start the local governed instance, run the A/B/C/A differential
  3. if complete, run the paced 30-profile acceptance
  4. otherwise: another quiet period (longer), up to MAX_CYCLES
"""
import asyncio
import os
import subprocess
import sys
import time

LI_AT = os.environ["TROSS_LI_AT"]
JSESSIONID = os.environ["TROSS_JSESSIONID"]
KEY = "local-acceptance-key"
BASE = "http://127.0.0.1:8907"
PY = sys.executable
ENV = {
    **os.environ,
    "LINKEDIN_LI_AT": LI_AT,
    "LINKEDIN_JSESSIONID": JSESSIONID,
    "APP_API_KEYS": KEY,
    "APP_MODE": "live",
    "APP_STORE_DIR": "./.tross_store_local",
    "TROSS_API_KEY": KEY,   # consumed by production_differential / acceptance_run
}
QUIET_MINUTES = int(os.environ.get("QUIET_MINUTES", "60"))
MAX_CYCLES = int(os.environ.get("MAX_CYCLES", "3"))


def run(cmd: list[str], timeout: int | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, env=ENV, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, (proc.stdout + proc.stderr)[-3000:]


async def main() -> None:
    quiet = QUIET_MINUTES * 60
    for cycle in range(1, MAX_CYCLES + 1):
        print(f"=== cycle {cycle}: quiet for {QUIET_MINUTES} minutes (no requests)", flush=True)
        await asyncio.sleep(quiet)
        print(f"=== cycle {cycle}: starting governed instance", flush=True)
        server = await asyncio.create_subprocess_exec(
            PY, "-m", "uvicorn", "tross_linkedin_api.main:app",
            "--port", "8907", "--log-level", "warning", env=ENV,
        )
        try:
            await asyncio.sleep(8)
            code, out = run(
                [PY, "scripts/production_differential.py"], timeout=600
            )
            print(out[-1500:], flush=True)
            if code == 0:
                print("DIFFERENTIAL PASSED - running acceptance", flush=True)
                code, out = run([PY, "scripts/acceptance_run.py", "--base", BASE,
                                 "--out", "C:/tmp/acceptance_result.json"], timeout=3600)
                print(out[-2500:], flush=True)
                print(f"ACCEPTANCE rc={code}", flush=True)
                sys.exit(0 if code == 0 else 1)
            print(f"=== cycle {cycle}: differential incomplete", flush=True)
        finally:
            server.terminate()
            await server.wait()
        quiet = min(quiet + 900, 5400)  # escalate: +15 min per cycle
    print("ALL CYCLES EXHAUSTED", flush=True)
    sys.exit(1)


asyncio.run(main())
