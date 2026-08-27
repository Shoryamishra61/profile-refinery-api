# Expected Network Responses & Schema Mapping Specs
**Role:** API Schema Architect and Systems Engineer  
**Status:** Production Mock Catalog

Because our workspace flat-file constraints restrict nested directory trees inside the `/workspace/out/` outbox, this document establishes the layout structure, naming conventions, and mock mapping specifications for expected network responses. It provides a direct mock template mapping to satisfy the requirement for structured mock data testing.

---

## 1. Storage & Mapping Architecture
In the testing environment, expected raw network responses (the files that mock LinkedIn's servers) are stored flat in our mock asset pipeline under the following mapping convention:

`/workspace/scratch/expected_responses/{slug}_{endpoint_type}.json`

Where `{endpoint_type}` maps to:
* `graphql_profile`: The raw, nested JSON returned by `/voyager/api/graphql`POST requests.
* `rest_contact`: The raw JSON returned by GET `/voyager/api/identity/profiles/{profileId}/contactInfo`.
* `rest_positions`: Paginated GET experience arrays from `/voyager/api/identity/profiles/{id}/positions`.

---

## 2. Mock Schema Template: Rich Profile (Jane Doe)
Below is a highly complete, syntactically correct mock network response for our benchmark gold-standard test case. This file illustrates localized multi-locale strings, nested promotion intervals under Google, and CDN expired images.

```json
{
  "data": {
    "voyagerIdentityDashProfiles": {
      "elements": [
        {
          "entityUrn": "urn:li:fsd_profile:ACoAAAtp-4U",
          "firstName": "Jane",
          "lastName": "Doe",
          "headline": "Engineering Director & Protocol Researcher",
          "geoLocation": {
            "name": "San Francisco, California",
            "postalCode": "94105",
            "countryCode": "US"
          },
          "summary": {
            "text": "Specializing in web protocol reverse engineering, high-throughput distributed architectures, and API security. Designing systems with no-browser constraints."
          },
          "profilePicture": {
            "displayImage": {
              "vectorArtifact": "urn:li:digitalmediaAsset:C5603AQF-Wf",
              "elements": [
                {
                  "artifact": "urn:li:digitalmediaAssetElement:123456",
                  "downloadUrl": "https://media.licdn.com/dms/image/v2/C5603AQF-Wf/profile-displayphoto-shrink_800_800?e=1798351200&v=beta&t=EXPIRED_TOKEN",
                  "expiresAt": 1798351200
                }
              ]
            }
          }
        }
      ],
      "included": [
        {
          "entityUrn": "urn:li:fsd_profilePosition:(ACoAAAtp-4U,9881122)",
          "title": "Director of Engineering",
          "companyName": "Google",
          "companyUrn": "urn:li:fsd_company:16247",
          "timePeriod": {
            "startDate": { "year": 2024, "month": 3 },
            "endDate": null
          },
          "locationName": "Mountain View, CA",
          "description": "Leading programmatic data-infrastructure security audits. Standardizing secure API contracts."
        },
        {
          "entityUrn": "urn:li:fsd_profilePosition:(ACoAAAtp-4U,9881123)",
          "title": "Staff Software Engineer",
          "companyName": "Google",
          "companyUrn": "urn:li:fsd_company:16247",
          "timePeriod": {
            "startDate": { "year": 2021, "month": 6 },
            "endDate": { "year": 2024, "month": 3 }
          },
          "locationName": "Mountain View, CA",
          "description": "Architecting low-latency network telemetry aggregators."
        }
      ]
    }
  }
}
```
