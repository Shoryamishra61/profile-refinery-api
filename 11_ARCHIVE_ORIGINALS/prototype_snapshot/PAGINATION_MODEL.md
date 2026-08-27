# Protocol Specification: Pagination and Truncation Model
**Author:** Protocol Reverse-Engineering & Systems Architecture Group  
**Status:** Pre-Design Technical Specifications  
**Focus:** Navigating un-truncated profile history arrays.

---

## 1. The Truncation Bottleneck (The 2-Job Limit)
Standard full-profile view endpoints (such as `/voyager/api/identity/profileView` or the primary GraphQL Dash Profiles query) are heavily optimized for mobile web load times [31, 120]. By default, the server applies projection masks that truncate collections, returning **only the first two positions and educations** [31, 120]:

* Experience history is restricted to the current role and the immediate previous role [120].
* Educational background is restricted to the most recent degree [120, 230].

If a candidate has a 15-year career spanning 10 distinct roles, replaying only the top-level gateway request will silently omit 80% of their career history [120, 146]. This represents a critical quality failure [330].

---

## 2. Navigating Rest.li Paging Arrays
To fetch the complete career and educational history, the service must execute separate paginated GET queries against the specific sub-resource endpoints [8, 31]:

* Experience Endpoint: `/voyager/api/identity/profiles/{id}/positions` [414, 415]
* Education Endpoint: `/voyager/api/identity/profiles/{id}/educations` [404, 413]

These endpoints support Rest.li 2.0 pagination query parameters [267, 269]:

```
https://www.linkedin.com/voyager/api/identity/profiles/ACoAAAtp-4U/positions?start=0&count=10
```

### URL Parameter Semantics
* `start` (Integer): Offset index starting from 0 [267, 269].
* `count` (Integer): Number of records requested (default is 10, max supported is typically 50) [267, 269].

### Pagination Metadata Response Payload
The Rest.li server wraps arrays in a `com.linkedin.rest.CollectionResponse` structure [272, 293]:

```json
{
  "elements": [ ... ],
  "paging": {
    "start": 0,
    "count": 10,
    "total": 14,
    "links": [
      {
        "href": "/identity/profiles/ACoAAAtp-4U/positions?count=10&start=10",
        "rel": "next",
        "type": "application/json"
      }
    ]
  }
}
```

---

## 3. Dynamic Pagination Traversal Loop
To reconstruct the full list of positions, educations, or certifications, our service backend must implement a deterministic traversal loop [18, 267]:

```python
# Technical pagination implementation
positions = []
start = 0
count = 20

while True:
    url = f"https://www.linkedin.com/voyager/api/identity/profiles/{member_id}/positions?start={start}&count={count}"
    response = session.get(url, headers=headers)
    
    if response.status_code != 200:
        break
        
    data = response.json()
    elements = data.get("elements", [])
    positions.extend(elements)
    
    total = data.get("paging", {}).get("total", 0)
    start += len(elements)
    
    if start >= total or not elements:
        break
```

---

## 4. GraphQL Pre-Registered Pagination Variables
For modern UI views, queries routed to `/voyager/api/graphql` POST gateway map variables inside the serialized payload string [307, 332]:

* Query Payload:
  ```json
  {
    "query_params": {
      "variables": "(start:10,count:10,profileId:urn:li:fsd_profile:ACoAAAtp-4U)",
      "queryId": "voyagerIdentityDashProfiles.d831bf85b9873ef0228a2bab19781290"
    },
    "method": "GET",
    "url": "https://www.linkedin.com/voyager/api/graphql"
  }
  ```
Because GraphQL queries are pre-registered and immutable on the server, our client must map variables into the exact string representation defined by the query template [104, 307].
