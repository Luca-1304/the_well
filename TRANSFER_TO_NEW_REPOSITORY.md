# Transfer this export into `Luca-1304/nasa-data-hub`

The `standalone/nasa-data-hub` branch is a clean root-level project tree, but it still lives inside the large `the_well` Git repository. Create a new empty public repository named `nasa-data-hub`, then import the files with a fresh history so the upstream simulation repository and its 674 MB history are not carried across.

## GitHub setup

Create an empty repository with:

- Owner: `Luca-1304`
- Repository name: `nasa-data-hub`
- Visibility: Public
- Do not initialise it with a README, licence or `.gitignore`; those files already exist in this export.

## Clean-history transfer — PowerShell

```powershell
git clone --depth 1 --single-branch --branch standalone/nasa-data-hub https://github.com/Luca-1304/the_well.git nasa-data-hub
Set-Location nasa-data-hub
Remove-Item -Recurse -Force .git
git init -b main
git add .
git commit -m "Initial standalone NASA Data Hub"
git remote add origin https://github.com/Luca-1304/nasa-data-hub.git
git push -u origin main
```

## Clean-history transfer — macOS/Linux

```bash
git clone --depth 1 --single-branch --branch standalone/nasa-data-hub https://github.com/Luca-1304/the_well.git nasa-data-hub
cd nasa-data-hub
rm -rf .git
git init -b main
git add .
git commit -m "Initial standalone NASA Data Hub"
git remote add origin https://github.com/Luca-1304/nasa-data-hub.git
git push -u origin main
```

## Immediately after transfer

1. Open the new repository's Actions tab and allow the workflows if GitHub requests approval.
2. Confirm the normal Python 3.10–3.13 matrix passes.
3. Run **Fifteen consecutive verification passes** manually once in the new repository.
4. Add branch protection for `main`, requiring pull requests and the normal test matrix.
5. Rotate the previously disclosed NASA key.
6. Add the new key as the encrypted repository secret `NASA_API_KEY` only when the registered live soak is deliberately required.
7. Never paste the replacement key into a workflow input, issue, pull request, source file or chat.

## Evidence boundary

The exported source blobs match the application files that previously completed 15/15 clean-package cycles on Linux and 15/15 on Windows. The new standalone repository should still run its own workflows after transfer so the new repository context is independently verified.
