# Security Policy

## Supported versions
Only the live assistant at [agent.figueroa-sanchez.com](https://agent.figueroa-sanchez.com) and the latest `main` branch receive security fixes.

## Reporting a vulnerability
Please **do not** open a public issue for security problems. Instead, email [marco@figueroa-sanchez.com](mailto:marco@figueroa-sanchez.com) with:

- A description of the vulnerability
- Steps to reproduce it
- The potential impact

## What to expect
- An acknowledgement within 72 hours.
- Updates as the report is triaged and fixed.
- Credit for the discovery once it's resolved, if you'd like it.

## Scope
**In scope:**
- All API endpoints, for example input validation bypasses, SQL injection or unauthorized data changes
- The chat endpoint, for example reading or continuing another user's conversation, or prompt injection that
  makes the agents reveal their prompts, configuration or data outside their area
- CORS, for example getting CORS headers for an origin that is not registered and enabled in `cors_origins`
- Leaks of secrets, stack traces or internal data in responses

**Out of scope:**
- Answers that are wrong or off-topic without exposing data or configuration (model quality, not security)
- Third-party services the API depends on (e.g. Google Gemini, hosting provider)
- The Google Chat and WhatsApp channels, which live in a separate project
- Denial-of-service or high-volume testing

## Secrets in the database
The values of the `property` table, including `google_api_key`, are stored in plain text. Anyone with read access to
the database can read them, so:

- Grant database access only to the API and to the people who manage it.
- Use API keys restricted to the service they are meant for, and rotate them if the database or a backup is exposed.
- Never copy production values into issues, logs or test data.
