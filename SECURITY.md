# Security policy

## Supported state

Security fixes target the current default branch of the eventual standalone repository.

## Secrets

- Never commit `.env` or a personal NASA API key.
- Never place a key in frontend HTML or JavaScript.
- Never provide a key through a GitHub workflow input.
- Use a local process environment, a local ignored `.env`, or an encrypted repository/hosting secret.
- Rotate any key disclosed in chat, logs, screenshots, commits, issues or pull requests.

## Reporting

Do not open a public issue containing a credential, exploit payload, private URL or personal data. Contact the repository owner privately through an appropriate verified channel and provide the minimum information needed to reproduce the problem.

## Intended boundary

The application is a local dashboard and proxy for selected public data APIs. It is not an authentication service, multi-user production gateway, safety-critical system or guarantee of upstream availability.
