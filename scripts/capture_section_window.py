"""One-attempt-per-window section capture.

The observed LinkedIn behavior allows ~one scripted voyager request per fresh
login window. This script spends the window's single attempt on the highest
value unverified contract: the profileCards EXPERIENCE resource. If it
succeeds the live payload is saved and the section contract can be promoted.

Run after a fresh login. One attempt per invocation — never a retry loop.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

LI_AT = os.environ["TROSS_LI_AT"]
JSESSIONID = os.environ["TROSS_JSESSIONID"]
MEMBER_ID = os.environ.get("TROSS_MEMBER_ID", "ACoAAA8BYqEBCGLg_vT_ca6mMEqkpp9nVffJ3hc")
OUT = Path(os.environ.get("TROSS_OUT", "C:/tmp/card_experience_live.json"))


async def main() -> None:
    os.environ.setdefault("APP_API_KEYS", "capture")

    from tross_linkedin_api.config import Settings
    from tross_linkedin_api.errors import ProblemError
    from tross_linkedin_api.graph import NormalizedGraph
    from tross_linkedin_api.operation_registry import OperationRegistry
    from tross_linkedin_api.parsers import parse_experience
    from tross_linkedin_api.session import SessionProvider
    from tross_linkedin_api.transport import LinkedInTransport

    settings = Settings(
        app_api_keys=["capture"], app_mode="live",
        linkedin_li_at=LI_AT, linkedin_jsessionid=JSESSIONID,
        app_upstream_retries=0,
    )
    registry = OperationRegistry.load(Path("config/operation_registry.yaml"))
    transport = LinkedInTransport(settings, registry, SessionProvider(settings))
    try:
        result = await transport.execute(
            "profile_experience", "williamhgates", "cards-capture",
            resource_id=f"{MEMBER_ID}-EXPERIENCE-en_US",
        )
        graph = NormalizedGraph(result.payload)
        positions = parse_experience(graph)
        await asyncio.to_thread(
            OUT.write_text,
            json.dumps(result.payload, indent=1, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"SECTION CAPTURED: {len(result.payload.get('included', []))} entities, "
              f"{len(positions)} owned positions", flush=True)
        for position in positions:
            print(f"  - {position.get('title')} @ {position.get('company_name')} "
                  f"current={position.get('is_current')}", flush=True)
        sys.exit(0)
    except ProblemError as exc:
        print(f"ATTEMPT FAILED: {exc.code} | {exc.detail[:120]}", flush=True)
        sys.exit(1)
    finally:
        await transport.aclose()


asyncio.run(main())
