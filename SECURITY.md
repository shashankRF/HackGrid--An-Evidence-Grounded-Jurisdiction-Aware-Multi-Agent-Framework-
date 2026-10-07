# Security Policy

## Overview

HackGrid is an evidence-grounded, jurisdiction-aware AI framework for technical, regulatory, security, and research analysis.

Because HackGrid may process security-related and regulatory information, security, provenance, and responsible handling of information are important parts of the project.

## Supported Versions

Security fixes will primarily be applied to the latest development/release version of HackGrid.

| Version | Supported |
|---------|-----------|
| v1.0.x  | Yes |
| Older versions | No |

## Reporting a Security Vulnerability

Please do not publicly disclose security vulnerabilities through GitHub Issues or Pull Requests.

If you discover a potential security vulnerability involving HackGrid, please report it privately to the project maintainer.

### Include

- Description of the vulnerability
- Affected component or file
- Steps required to reproduce the issue
- Potential security impact
- Relevant logs or screenshots, if safe to share
- Suggested mitigation, if known

Please do not include API keys, passwords, authentication tokens, personal information, or other secrets in vulnerability reports.

## Secrets and Credentials

HackGrid uses environment-based configuration for sensitive credentials.

API keys and other secrets must:

- Never be committed to the repository
- Never be embedded in frontend code
- Never be included in screenshots or demonstrations
- Be stored in local environment configuration
- Be rotated immediately if accidentally exposed

The project's `.env` file is intentionally excluded from version control.

## Knowledge Base and Evidence Security

HackGrid distinguishes between:

- Real knowledge-base evidence
- Retrieved evidence
- Simulated scenario data
- AI-generated analysis

Simulated scenarios must not be represented as real-world evidence.

Retrieved evidence should retain appropriate provenance and source metadata wherever supported by the system.

## AI and Governance

HackGrid is designed around the following principles:

> AI recommends. Evidence supports. Risk Engine determines governance requirements. Human authority makes consequential decisions.

The AI system must not:

- Grant itself authority
- Approve its own output
- Bypass mandatory human review
- Fabricate evidence, regulations, standards, or citations
- Remove or downgrade governance requirements
- Fabricate human approval

High-impact decisions should remain subject to the project's Risk & Authority and Human Review mechanisms.

## Responsible Disclosure

Security researchers are encouraged to report vulnerabilities privately so that issues can be investigated and addressed before public disclosure where appropriate.

We appreciate responsible disclosure and will make reasonable efforts to investigate reported security issues.

## Scope

This policy applies to the HackGrid source code and associated project infrastructure maintained in this repository.

Third-party services used by HackGrid may have their own security and vulnerability-reporting policies.

## Disclaimer

HackGrid is an evolving research and prototype project.

It should not be treated as a substitute for professional cybersecurity, regulatory, legal, safety, or operational decision-making.

Users remain responsible for independently validating consequential decisions and ensuring compliance with applicable requirements.
