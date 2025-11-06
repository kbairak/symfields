# Releasing SymFields

This document describes how to release a new version of SymFields to PyPI.

## Prerequisites

### One-Time Setup

1. **PyPI Account**: Create an account at https://pypi.org/account/register/

2. **Trusted Publishing**: Set up OpenID Connect (OIDC) publishing on PyPI:
   - Go to https://pypi.org/manage/account/publishing/
   - Click "Add a new pending publisher"
   - Fill in:
     - **PyPI Project Name**: `symfields`
     - **Owner**: `kbairak` (GitHub username)
     - **Repository name**: `symfields`
     - **Workflow name**: `publish.yml`
     - **Environment name**: (leave blank)
   - Click "Add"

   This allows GitHub Actions to publish automatically without storing API tokens.

## Release Process

### 1. Pre-Release Checklist

Before creating a release, ensure:

- [ ] All tests pass locally: `make test`
- [ ] Linting passes: `make lint`
- [ ] CI is green on the main branch
- [ ] README is up to date with any new features
- [ ] Examples work correctly

### 2. Update Version Number

Edit `pyproject.toml` and update the version:

```toml
version = "0.2.0"  # or whatever the new version is
```

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality (backward compatible)
- **PATCH** version for bug fixes (backward compatible)

### 3. Test the Build Locally

```bash
# Build the package
uv build

# Verify the built files
ls -lh dist/
```

This should create two files:
- `symfields-{version}-py3-none-any.whl`
- `symfields-{version}.tar.gz`

### 4. Commit Version Bump

```bash
git add pyproject.toml
git commit -m "Bump version to {version}"
git push origin main
```

### 5. Create a GitHub Release

1. Go to https://github.com/kbairak/symfields/releases/new
2. Fill in the release form:
   - **Tag**: `v{version}` (e.g., `v0.2.0`) - create new tag
   - **Target**: `main` branch
   - **Release title**: `v{version} - [Brief Description]`
   - **Description**: Write release notes (see template below)
3. Click "Publish release"

#### Release Notes Template

```markdown
## What's New in v{version}

### Added
- New feature 1
- New feature 2

### Changed
- Changed behavior 1
- Changed behavior 2

### Fixed
- Bug fix 1
- Bug fix 2

### Installation

```bash
pip install symfields
```

### Documentation

See the [README](https://github.com/kbairak/symfields#readme) for full documentation.
```

### 6. Verify Publication

After creating the release:

1. **Watch GitHub Actions**:
   - Go to https://github.com/kbairak/symfields/actions
   - The "Publish to PyPI" workflow should start automatically
   - Wait for it to complete (usually 1-2 minutes)

2. **Verify on PyPI**:
   - Go to https://pypi.org/project/symfields/
   - Confirm the new version appears

3. **Test Installation**:
   ```bash
   # In a fresh virtual environment
   pip install symfields=={version}
   python -c "from symfields import SymFields, S; print('Success!')"
   ```

## Troubleshooting

### Build Fails

If `uv build` fails:
- Check `pyproject.toml` syntax
- Ensure all required files are present
- Run tests to verify code integrity

### GitHub Actions Fails

If the publish workflow fails:
- Check workflow logs at https://github.com/kbairak/symfields/actions
- Verify trusted publishing is set up correctly on PyPI
- Ensure the tag name starts with `v` (e.g., `v0.2.0`)

### PyPI Rejects Package

If PyPI rejects the upload:
- Ensure the version number hasn't been used before (you cannot overwrite)
- Check that all required metadata is in `pyproject.toml`
- Verify the package name is available

### Fix After Failed Release

If you need to fix something after creating a release:

1. Delete the GitHub release (if it exists)
2. Delete the tag locally and remotely:
   ```bash
   git tag -d v{version}
   git push origin :refs/tags/v{version}
   ```
3. Fix the issue
4. Start the release process again with the same or new version

**Note**: You cannot re-upload the same version to PyPI. If the package was already published, you must bump to a new version.

## Post-Release

After a successful release:

1. Announce on relevant channels (if any)
2. Update documentation if needed
3. Close related GitHub issues/milestones
4. Consider adding the version to a CHANGELOG.md

## Emergency: Yanking a Release

If a critical bug is found in a released version:

1. Release a fixed version ASAP
2. Optionally yank the broken version on PyPI:
   - Go to https://pypi.org/manage/project/symfields/releases/
   - Find the problematic version
   - Click "Options" → "Yank release"
   - Provide a reason

Yanked versions can still be installed explicitly but won't be installed by default.
