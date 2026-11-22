# Security policy

## Scope

This project currently targets a local Windows desktop application. It is not a hosted multi-user service.

## Data and privacy

- Documents and account records are stored locally in SQLite.
- Local-only does not mean encrypted: anyone with access to the Windows account and database files may be able to read them.
- Keep Windows sign-in protected, use device encryption (such as BitLocker where available), and maintain encrypted backups.
- Ollama inference is intended to use the local Ollama service. Do not expose the Ollama API to untrusted networks.

## Reporting a vulnerability

Please do not publish sensitive exploit details or personal document data in public issues. Contact the repository maintainer privately through GitHub's security reporting feature if enabled, or request a private reporting channel.

## Current limitations

The project is under active development. A passing unit test suite is not a penetration test or a security certification. The Windows installer must be tested on clean Windows 10 and 11 systems before release.
