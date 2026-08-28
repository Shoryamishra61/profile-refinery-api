"""Wait for the challenged session to recover, then run live validation.

The production breaker probes the upstream every cooldown automatically; this
loop simply checks (one paced request) whether extraction has recovered. On
recovery it runs the A/B/C/A differential and then the paced 30-profile
acceptance run, writing measured results to C:/tmp/.
"""
import asyncio
import os
import subprocess
import sys

KEY = os.environ["TROSS_API_KEY"]
BASE = "https://tross-linkedin-profile-api.vercel.app"
ENV = {**os.environ, "TROSS_API_KEY": KEY, "TROSS_BASE": BASE}
PY = sys.executable


async def recovered() -> bool:
    proc = await asyncio.create_subprocess_exec(
        PY, "scripts/production_differential.py",
        env=ENV, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    tail = out.decode("utf-8", errors="replace")[-300:]
    print(tail, flush=True)
    return proc.returncode == 0


async def main() -> None:
    for attempt in range(1, 37):  # up to ~6 hours at 10-minute pacing
        print(f"=== recovery check {attempt} {attempt * 10}min-mark", flush=True)
        if await recovered():
            print("RECOVERED - running acceptance run", flush=True)
            proc = await asyncio.create_subprocess_exec(
                PY, "scripts/acceptance_run.py", env=ENV,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await proc.communicate()
            print(out.decode("utf-8", errors="replace"), flush=True)
            print("ACCEPTANCE DONE rc=", proc.returncode, flush=True)
            sys.exit(0 if proc.returncode == 0 else 1)
        await asyncio.sleep(600)
    print("SESSION NEVER RECOVERED", flush=True)
    sys.exit(1)


asyncio.run(main())
