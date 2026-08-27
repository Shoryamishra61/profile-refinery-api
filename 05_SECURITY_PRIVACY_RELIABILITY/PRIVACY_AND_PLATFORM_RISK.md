# Privacy and Platform-Risk Notes

Engineering risk memo, not legal advice.

LinkedIn's current User Agreement prohibits scraping/copying profiles and bypassing access controls/use limits. Tross nevertheless explicitly asks candidates to reverse engineer and directly call LinkedIn endpoints. State this tension honestly; do not claim LinkedIn approval/compliance.

Profile data is identifiable personal data. Engineering mitigations: own/consented validation profiles, no email enrichment, minimize fields to assignment scope, no persistent profile DB by default, no raw payload logs, timestamps/provenance.

Avoid claims: “fully GDPR compliant,” “fully DPDP compliant,” “hiQ legalized LinkedIn scraping,” or “public data is privacy-exempt.”

Frame the submission as a technical reverse-engineering/system-design demonstration, not a production data-broker launch.
