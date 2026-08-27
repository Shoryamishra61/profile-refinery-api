# Specification: Raw Candidate Profile JSON Fixture
**Author:** Knowledge Representation & Systems Architecture Group  
**Status:** Pre-Design Technical Specifications  
**Focus:** Establishing a gold-standard mock testing fixture modeled after LinkedIn internal Voyager formats.

---

## 1. Specification Overview
To guarantee the reliability of our hosted extraction service, we define a gold-standard raw input fixture representing the complex, multi-locale, flat relational structure returned by LinkedIn’s server-driven UI layer [40, 210, 415].

This mock fixture models a real-world candidate profile (**Jane Doe**) and includes advanced structural edge cases: localized multi-locale name strings, overlapping positions within a single company (promotions), and expire-aware media URLs [210, 235, 414].

---

## 2. Complete Candidate Profile JSON Fixture (`jane_doe_raw.json`)
```json
{
  "data": {
    "identityDashProfilesByMemberIdentity": {
      "*elements": [
        "urn:li:fsd_profile:ACoAAAmember123"
      ],
      "$type": "com.linkedin.voyager.dash.identity.ProfilesCollection"
    }
  },
  "included": [
    {
      "entityUrn": "urn:li:fsd_profile:ACoAAAmember123",
      "publicIdentifier": "jane-doe-sre",
      "firstName": {
        "localized": {
          "en_US": "Jane",
          "fr_FR": "Jeanne"
        },
        "preferredLocale": {
          "country": "US",
          "language": "en"
        }
      },
      "lastName": {
        "localized": {
          "en_US": "Doe",
          "fr_FR": "Martin"
        },
        "preferredLocale": {
          "country": "US",
          "language": "en"
        }
      },
      "headline": {
        "localized": {
          "en_US": "Principal SRE at Contoso Systems"
        },
        "preferredLocale": {
          "country": "US",
          "language": "en"
        }
      },
      "summary": {
        "localized": {
          "en_US": "Distributed systems engineer specializing in high-throughput network protocols and wire-level proxy reverse engineering."
        },
        "preferredLocale": {
          "country": "US",
          "language": "en"
        }
      },
      "profileLocation": {
        "countryCode": "US",
        "postalCode": "94043",
        "preferredGeoPlace": "urn:li:geo:12345"
      },
      "profilePicture": {
        "displayImage": "urn:li:digitalmediaAsset:C4D00AAAAbBC"
      },
      "backgroundPicture": {
        "originalImage": "urn:li:digitalmediaAsset:C4D00BBBAbCD"
      },
      "$type": "com.linkedin.voyager.dash.identity.Profile"
    },
    {
      "entityUrn": "urn:li:digitalmediaAsset:C4D00AAAAbBC",
      "croppedImage": {
        "downloadUrl": "https://media.licdn.com/dms/image/v2/D4E03AQ/profile-pic.jpg",
        "downloadUrlExpiresAt": 1785122741000
      },
      "$type": "com.linkedin.voyager.dash.identity.ProfilePicture"
    },
    {
      "entityUrn": "urn:li:fs_position:(urn:li:fs_member:123,pos1)",
      "title": "Principal Site Reliability Engineer",
      "companyName": "Contoso Systems",
      "*company": "urn:li:fs_company:98765",
      "description": "Architected parallel Rest.li proxy pools and TLS impersonation layers.",
      "dateRange": {
        "start": {
          "year": 2024,
          "month": 1
        },
        "end": null
      },
      "locationName": "Mountain View, CA",
      "$type": "com.linkedin.voyager.dash.identity.Position"
    },
    {
      "entityUrn": "urn:li:fs_position:(urn:li:fs_member:123,pos2)",
      "title": "Senior Software Engineer (SRE)",
      "companyName": "Contoso Systems",
      "*company": "urn:li:fs_company:98765",
      "description": "Maintained high-availability distributed message brokers.",
      "dateRange": {
        "start": {
          "year": 2021,
          "month": 6
        },
        "end": {
          "year": 2023,
          "month": 12
        }
      },
      "locationName": "Mountain View, CA",
      "$type": "com.linkedin.voyager.dash.identity.Position"
    },
    {
      "entityUrn": "urn:li:fs_company:98765",
      "name": "Contoso Systems",
      "universalName": "contoso-systems",
      "url": "https://www.linkedin.com/company/contoso-systems",
      "$type": "com.linkedin.voyager.dash.entities.Company"
    },
    {
      "entityUrn": "urn:li:fs_education:(urn:li:fs_member:123,edu1)",
      "schoolName": "Stanford University",
      "degreeName": "Bachelor of Science",
      "fieldOfStudy": "Computer Science",
      "dateRange": {
        "start": {
          "year": 2017
        },
        "end": {
          "year": 2021
        }
      },
      "$type": "com.linkedin.voyager.dash.identity.Education"
    },
    {
      "entityUrn": "urn:li:fs_skill:(urn:li:fs_member:123,skill1)",
      "name": "Distributed Systems",
      "endorsementCount": 42,
      "$type": "com.linkedin.voyager.dash.identity.Skill"
    },
    {
      "entityUrn": "urn:li:fs_skill:(urn:li:fs_member:123,skill2)",
      "name": "Reverse Engineering",
      "endorsementCount": 18,
      "$type": "com.linkedin.voyager.dash.identity.Skill"
    }
  ]
}
```
