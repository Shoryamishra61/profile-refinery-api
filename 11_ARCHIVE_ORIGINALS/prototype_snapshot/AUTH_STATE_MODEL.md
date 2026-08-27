# System Specification: Authenticated Session and CSRF Model
**Author:** Cryptographic Protocol & Session Management Team  
**Status:** Pre-Design Security Specifications  
**Focus:** Establishing, maintaining, and defending programmatic LinkedIn sessions.

---

## 1. Aligned Cookie Jar Requirements
To query any undocumented Voyager REST or GraphQL endpoints, our service must establish a fully aligned cookie jar that replicates a legitimate browser state [309, 550].

| Session Attribute | Cookie Key | Format | Cryptographic Nature | Lifetime Bounds |
| ------ | ------ | ------ | ------ | ------ |
| **Session Bearer Token** | `li_at` [20, 224] | Cryptographic JWT [20, 224] | signed with LinkedIn internal keys [20]. | typically 3–6 months [135, 153]. *Expires instantly if accessed from suspicious proxy ASN.* |
| **CSRF Cookie Token** | `JSESSIONID` [17, 309] | Double-quoted String [19, 101] | Server-assigned identifier for CSRF verification [17, 309]. | Linked strictly to the lifecycle of the active `li_at` cookie [17, 309]. |

---

## 2. Programmatic CSRF Derivation
Every GET or POST request issued during the session is checked for Cross-Site Request Forgery (CSRF) protections [17, 309]. The server gatekeeper enforces a strict desynchronization policy [176, 310]:

1. The browser cookie jar holds: `JSESSIONID="ajax:1812219885785541610"` [309, 310]
2. The client must extract the cookie, parse the string, and strip the outer double quotes [19, 404, 310].
3. The client injects the resulting alphanumeric string into the custom HTTP header [310]:
   `csrf-token: ajax:1812219885785541610` [309, 310]
4. The server compares the cookie value with the incoming header [17, 310].
5. **Desynchronization Failure:** If the header does not match the cookie exactly (including the quotes or custom prefix), the server returns an immediate `HTTP 403 Forbidden` with a `"CSRF check failed."` body [193, 310].

```python
# Reference CSRF derivation loop
def inject_csrf_header(headers, cookie_jar):
    jsessionid = cookie_jar.get("JSESSIONID")
    if not jsessionid:
        raise ValueError("Missing JSESSIONID cookie")
    csrf_val = jsessionid.replace('"', '') # Strip quotes
    headers["csrf-token"] = csrf_val
```

---

## 3. Proxy-Session Pinning (Geolocation Integrity)
LinkedIn's security systems track the routing ASN and IP address of active sessions [23, 153].
* **The Geo-Friction Trap:** If an `li_at` session cookie is captured from a user browsing in New York (e.g., ASN 701), and a hosted container replays that cookie from an AWS data center in Virginia (ASN 14618), the server edge identifies the routing discrepancy [22, 330].
* **The Consequence:** The session is immediately flagged, triggering verification checkpoints (CAPTCHA, email challenge) and terminating token validity [176, 330].
* **System Policy:** To bypass this, the hosted extraction API must strictly bind each account credential to a residential proxy pool in the exact same metropolitan region and ASN as the captured user browser [135, 461].

---

## 4. Programmatic Operating Thresholds (SRE Pacing)
Raw HTTP requests execute in milliseconds, representing a highly distinctive, non-human profile [112, 153].
* **The Threshold:** SRE analyses indicate standard free accounts are restricted if they execute more than **50–100 profile actions per day** [23, 576].
* **The Pacing Protocol:** Outbound queries must be serialized using a persistent task queue, inserting randomized, human-mimicking delay gaps (jitter) of **3–8 seconds between requests** [153, 576].
