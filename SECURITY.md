# Security policy

## Do not commit secrets or private data

Never commit:
- `.env` files or real database credentials
- JWT signing keys, API tokens, passwords, or private keys
- MySQL exports containing personal or institutional data
- Runtime logs, PID files, local databases, or backups

Use the `.env.example` files as templates and replace all placeholder values locally.

## Reporting a vulnerability

Do not publish exploit details or sensitive data in a public issue. Contact the repository owner privately through GitHub.
