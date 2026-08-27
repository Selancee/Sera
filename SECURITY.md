# Security and private-data handling

Do not report a vulnerability by attaching an API key, private score, or complete local
settings file to a public issue. Contact `[SUPPORT EMAIL]` after the maintainer supplies
the release support address.

SeraEdit is local-first but optional model calls transmit a compact score-derived
context to the configured provider. Users should review the provider's data policy and
avoid sending material they are not authorized to process. Secrets are stored outside
the repository and are omitted from run traces, exports and SoftwareX archives.

The host bridge uses loopback HTTP and temporary MusicXML snapshots. It is not a remote
multi-user authorization service. Do not expose the local API port to untrusted networks.
