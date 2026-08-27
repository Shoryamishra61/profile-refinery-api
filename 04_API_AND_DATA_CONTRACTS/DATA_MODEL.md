# Data Model

## Envelope
`schema_version`, `input_url`, `canonical_url`, `observed_at`, `partial`, `profile`, `meta`.

## Required profile keys
identity, name, headline, location, about, experience, education, skills, certifications, languages, profile_image.

Optional: background_image, volunteering, projects, publications, honors, courses, organizations, recommendations.

## Field<T>
`value: T|null`, `status: FieldStatus`, `provenance: Provenance`.

## Provenance
`source_operation`, `observation_time`, optional safe `raw_entity_reference`, `parser_version`, optional normalization note. Do not expose query IDs/cookies/headers by default.

## Experience
URN/id if available, title, company, company ref, start/end dates, location, description, grouping metadata only when evidence supports grouping. Never manufacture grouped promotions.

## Date
Year required when date exists; month/day optional.

## Media
URL, artifact ID if available, explicit expiry only when response provides it. Do not infer expiry from URL appearance.
