# Security policy

## Scope
This repository currently targets a local Windows desktop application. It is not a hosted multi-user service.

## Local data protection
- Document text and original file bytes are encrypted at rest with AES-256-GCM.
- On Windows, the random data-encryption key is protected with Windows DPAPI for the current Windows user.
- User passwords are stored as salted PBKDF2-HMAC-SHA256 hashes; repeated failed logins trigger a temporary account lockout.
- Document database operations require an explicit owner ID. Legacy documents without a known owner remain unassigned rather than being exposed to a new account.
- Encryption is not protection against malware or an attacker already running as the same Windows user. Keep Windows sign-in protected and use BitLocker/device encryption where available.
- The DPAPI key file and database must be backed up together. A database backup without its matching key cannot be decrypted. Restoring the key to another Windows user profile will not work.
- Ollama should remain bound to localhost. Do not expose its API to untrusted networks.

## Reporting
Do not publish exploit details or private document data in public issues. Use GitHub's private vulnerability reporting if enabled.

## Release status
This project is under active development. Unit tests and local encryption do not constitute a penetration test or security certification. Test clean installs, upgrades, uninstall, data migration, backup/restore, and Ollama connectivity on Windows 10 and 11 before release.
