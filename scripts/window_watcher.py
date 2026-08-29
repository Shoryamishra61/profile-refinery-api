"""Window watcher: one gentle probe per cycle; on an open window, run
differential + acceptance immediately (paced by the governor).

A challenge is never retried within a cycle. Cycles are 20 minutes apart,
bounded to MAX_CYCLES total. This replaces brute-force debugging with a
patient, low-volume window detector.
"""
import asyncio
import os
import subprocess
import sys

LI_AT = os.environ["TROSS_LI_AT"]
JSESSIONID = os.environ["TROSS_JSESSIONID"]
KEY = "local-acceptance-key"
BASE = "http://127.0.0.1:8907"
MAX_CYCLES = int(os.environ.get("MAX_CYCLES", "60"))  # ~20h at 20-min cycles
ENV = {
    **os.environ,
    "LINKEDIN_LI_AT": LI_AT,
    "LINKEDIN_JSESSIONID": JSESSIONID,
    "APP_API_KEYS": KEY,
    "APP_MODE": "live",
    "APP_STORE_DIR": "./.tross_store_local",
    "TROSS_API_KEY": KEY,
    "TROSS_BASE": BASE,
}
PY = sys.executable


async def probe_window() -> bool:
    """One profile request through the governed API. True if it succeeded."""
    server = await asyncio.create_subprocess_exec(
        PY, "-m", "uvicorn", "tross_linkedin_api.main:app",
        "--port", "8907", "--log-level", "warning", env=ENV,
    )
    try:
        await asyncio.sleep(8)
        proc = await asyncio.create_subprocess_exec(
            PY, "scripts/production_differential.py",
            env=ENV, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=240)
            tail = out.decode("utf-8", errors="replace")[-400:]
            print(tail, flush=True)
            return proc.returncode == 0
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return False
    finally:
        server.terminate()
        await server.wait()


async def main() -> None:
    for cycle in range(1, MAX_CYCLES + 1):
        print(f"=== window probe {cycle}/{MAX_CYCLES}", flush=True)
        if await probe_window():
            print("WINDOW OPEN - running acceptance", flush=True)
            proc = await asyncio.create_subprocess_exec(
                PY, "scripts/acceptance_run.py", "--base", BASE,
                "--out", "C:/tmp/acceptance_result.json",
                env=ENV, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            try:
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=3300)
                print(out.decode("utf-8", errors="replace")[-2500:], flush=True)
                print(f"ACCEPTANCE rc={proc.returncode}", flush=True)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                print("ACCEPTANCE TIMED OUT", flush=True)
            sys.exit(0)
        await asyncio.sleep(1200)  # 20 minutes between cycles
    print("NO OPEN WINDOW DETECTED", flush=True)
    sys.exit(1)


asyncio.run(main())
