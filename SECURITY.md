# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

BharatLink Nexus AI takes security vulnerabilities seriously. If you discover a security vulnerability, please follow responsible disclosure guidelines:

1. **Do not create a public issue**: Please do not file public GitHub issues for security vulnerabilities or secret exposures.
2. **Private Advisory**: Use the GitHub "Report a vulnerability" tab to create a private security advisory.
3. **Include details**: Provide a clear description of the issue, steps to reproduce, affected components, and potential impact.

## Security Practices in BharatLink Nexus AI

- **Environment-based secrets**: API keys and service credentials must never be committed to source code or container images.
- **Signed sessions**: Web sessions use HMAC-SHA256 signatures with cryptographic expiration timestamps.
- **Input sanitization**: User inputs rendered to the DOM undergo HTML entity escaping to prevent cross-site scripting (XSS).
- **Tenant isolation**: Multi-tenant authorization prevents cross-account modifications across sellers and buyers.
