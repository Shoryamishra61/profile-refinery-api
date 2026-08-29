"""Extract GraphQL contracts from the browser HAR capture.

Outputs to C:/tmp/har_extract/:
  graphql_index.json      — every api/graphql request: queryId, variables, status
  <queryId>.json          — each unique query's response body (for shape analysis)
  voyager_rest.json       — non-graphql /voyager/api/ requests (index only)
"""
import json
import os
from collections import Counter

HAR = r"C:\code_shit\TROSS\TROSS MANUS DATA\www.linkedin.com.bilgates.har"
OUT = r"C:\tmp\har_extract"

os.makedirs(OUT, exist_ok=True)

index = []
voyager_rest = []
saved = {}
with open(HAR, encoding="utf-8", errors="replace") as fh:
    har = json.load(fh)

entries = har.get("log", {}).get("entries", [])
print(f"total entries: {len(entries)}", flush=True)

for entry in entries:
    request = entry.get("request", {})
    url = request.get("url", "")
    if "/voyager/api/graphql" not in url:
        if "/voyager/api/" in url:
            voyager_rest.append({
                "url": url[:300],
                "status": entry.get("response", {}).get("status"),
                "method": request.get("method"),
            })
        continue
    query_id = "unknown"
    for param in request.get("queryString", []):
        if param.get("name") == "queryId":
            query_id = param.get("value", "unknown")
            break
    variables = ""
    for param in request.get("queryString", []):
        if param.get("name") == "variables":
            variables = param.get("value", "")[:200]
            break
    response = entry.get("response", {})
    status = response.get("status")
    body = (response.get("content", {}) or {}).get("text", "") or ""
    record = {"query_id": query_id, "variables": variables, "status": status,
              "body_bytes": len(body), "url": url[:300]}
    index.append(record)
    if status == 200 and body and query_id != "unknown" and query_id not in saved:
        # keep the FIRST 200 body per queryId (complete response shapes)
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict) and parsed.get("included"):
                saved[query_id] = parsed
                with open(os.path.join(OUT, f"{query_id.replace('/', '_')}.json"),
                          "w", encoding="utf-8") as out:
                    json.dump(parsed, out, indent=1, ensure_ascii=False)
        except json.JSONDecodeError:
            pass

with open(os.path.join(OUT, "graphql_index.json"), "w", encoding="utf-8") as fh:
    json.dump(index, fh, indent=1, ensure_ascii=False)
with open(os.path.join(OUT, "voyager_rest.json"), "w", encoding="utf-8") as fh:
    json.dump(voyager_rest[:200], fh, indent=1, ensure_ascii=False)

counts = Counter(r["query_id"] for r in index)
print("\ngraphql queryIds seen:", flush=True)
for query_id, count in counts.most_common():
    print(f"  {count}x {query_id}", flush=True)
print(f"\nsaved 200 response bodies: {len(saved)}", flush=True)
for query_id, doc in saved.items():
    types = {}
    for entity in doc.get("included", []):
        kind = entity.get("$type", "?").split(".")[-1]
        types[kind] = types.get(kind, 0) + 1
    print(f"  {query_id}: {len(doc.get('included', []))} entities {dict(sorted(types.items(), key=lambda kv: -kv[1])[:8])}", flush=True)
