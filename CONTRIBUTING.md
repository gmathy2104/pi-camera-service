# Contributing to Pi Camera Service

Thank you for your interest in contributing to Pi Camera Service! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)

---

## Code of Conduct

This project follows a Code of Conduct to ensure a welcoming environment for all contributors:

- **Be respectful** - Treat everyone with respect and consideration
- **Be collaborative** - Work together and help each other
- **Be inclusive** - Welcome newcomers and diverse perspectives
- **Be professional** - Keep discussions focused and constructive

---

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates.

**When submitting a bug report, include:**

- **Clear title** - Descriptive summary of the issue
- **Environment details:**
  - Raspberry Pi model (4, 5, Zero 2W)
  - Camera model (Module 3, HQ, NoIR, etc.)
  - OS version (`cat /etc/os-release`)
  - Python version (`python --version`)
  - Service version (`cat VERSION`)
- **Steps to reproduce** - Detailed steps to trigger the bug
- **Expected behavior** - What you expected to happen
- **Actual behavior** - What actually happened
- **Logs** - Relevant log output (`sudo journalctl -u pi-camera-service -n 100`)
- **Configuration** - Your `.env` settings (remove sensitive data!)

**Bug report template:**
```markdown
**Environment:**
- Pi Model: Raspberry Pi 5
- Camera: Camera Module 3 Wide NoIR
- OS: Raspberry Pi OS Bookworm
- Python: 3.11.2
- Version: 2.0.0

**Description:**
Brief description of the issue

**Steps to Reproduce:**
1. Step one
2. Step two
3. See error

**Expected:**
What should happen

**Actual:**
What actually happens

**Logs:**
```
[paste relevant logs]
```

**Configuration:**
```
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
...
```
```

### Suggesting Features

Feature suggestions are welcome! Please:

- **Check existing issues/PRs** - Someone may have already suggested it
- **Explain the use case** - Why is this feature needed?
- **Describe the solution** - How should it work?
- **Consider alternatives** - What other approaches did you consider?
- **Assess compatibility** - Will it work with all camera models?

**Feature request template:**
```markdown
**Problem:**
What problem does this solve?

**Proposed Solution:**
How should this feature work?

**Use Case:**
Real-world scenario where this is useful

**Alternatives Considered:**
Other approaches you've thought about

**Additional Context:**
Screenshots, links, examples, etc.
```

### Improving Documentation

Documentation improvements are highly valued:

- Fix typos or unclear explanations
- Add examples or use cases
- Improve installation/setup instructions
- Translate documentation (future)
- Add troubleshooting tips

**No coding experience required!**

### Contributing Code

See [Development Setup](#development-setup) and [Pull Request Process](#pull-request-process) below.

---

## Development Setup

### Prerequisites

- Raspberry Pi 4/5 or Zero 2W
- Raspberry Pi Camera (any model)
- Raspberry Pi OS Bullseye or newer
- Python 3.9+
- Git

### 1. Fork and Clone

```bash
# Fork the repository on GitHub (click "Fork" button)

# Clone your fork
git clone https://github.com/YOUR_USERNAME/pi-camera-service.git
cd pi-camera-service

# Add upstream remote
git remote add upstream https://github.com/gmathy2104/pi-camera-service.git
```

### 2. Install Dependencies

```bash
# System dependencies
sudo apt update
sudo apt install -y \
  python3-venv \
  python3-picamera2 \
  python3-libcamera \
  libcamera-apps \
  ffmpeg

# Create virtual environment (MUST use --system-site-packages!)
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Verify Setup

```bash
# Verify picamera2 access
python -c "from picamera2 import Picamera2; print('✓ OK')"

# Run tests
pytest

# Run service
python main.py
```

---

## Pull Request Process

### 1. Create a Branch

```bash
# Fetch latest changes
git fetch upstream
git checkout master
git merge upstream/master

# Create feature branch
git checkout -b feature/my-feature
```

**Branch naming:**
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring
- `test/description` - Test improvements

### 2. Make Changes

- Write code following [Coding Standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=camera_service --cov-report=term-missing

# Format code
black camera_service tests

# Lint code
ruff check camera_service tests --fix

# Type check
mypy camera_service
```

### 4. Commit Changes

Follow [Commit Message Guidelines](#commit-message-guidelines):

```bash
git add .
git commit -m "feat(camera): add autofocus control for Camera Module 3"
```

### 5. Push and Create PR

```bash
# Push to your fork
git push origin feature/my-feature

# Create Pull Request on GitHub
# Fill in the PR template with details
```

### 6. PR Review Process

- Automated tests must pass
- Code review by maintainer(s)
- Address feedback if requested
- Once approved, PR will be merged

### 7. Keep Your Branch Updated

```bash
# Fetch latest upstream changes
git fetch upstream

# Rebase your branch
git checkout feature/my-feature
git rebase upstream/master

# Force push (if already pushed)
git push origin feature/my-feature --force
```

---

## Coding Standards

### Python Style

- **PEP 8** - Follow Python style guide
- **Black** - Use Black for formatting (line length: 88)
- **Ruff** - Use Ruff for linting
- **Type hints** - Add type hints to all functions
- **Docstrings** - Document public methods (Google style)

**Example:**

```python
def capture_snapshot(
    self,
    width: int = 1920,
    height: int = 1080,
    autofocus_trigger: bool = True
) -> str:
    """Capture JPEG snapshot without stopping streaming.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        autofocus_trigger: Trigger autofocus before capture.

    Returns:
        Base64-encoded JPEG image data.

    Raises:
        CameraError: If camera is not initialized.
    """
    with self._lock:
        # Implementation
        pass
```

### Code Organization

- **One class per file** (exceptions allowed for small helper classes)
- **Group related functions** together
- **Separate concerns** - Don't mix business logic with I/O
- **DRY principle** - Don't repeat yourself
- **KISS principle** - Keep it simple

### Error Handling

- Use **custom exceptions** from `exceptions.py`
- **Always log errors** with appropriate level
- **Provide context** in error messages
- **Clean up resources** in `finally` blocks

**Example:**

```python
try:
    result = self._picam2.capture_array("main")
except Exception as e:
    logger.error(f"Snapshot capture failed: {e}")
    raise CameraError(f"Snapshot capture failed: {e}") from e
finally:
    # Cleanup if needed
    pass
```

### Thread Safety

- **Always acquire lock** before camera operations
- Use **`RLock`** (reentrant), not `Lock`
- **Keep lock duration minimal**
- **Never do I/O** while holding lock

**Example:**

```python
def my_camera_operation(self, param: int) -> bool:
    with self._lock:
        # Camera operations only
        return self._picam2.set_controls({"Param": param})
```

### Configuration

- **Use environment variables** via Pydantic Settings
- **Provide defaults** for all settings
- **Validate inputs** with Pydantic Field constraints
- **No hardcoded values** in code

---

## Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation only
- **style:** Code style (formatting, no logic change)
- **refactor:** Code refactoring (no feature/fix)
- **test:** Adding or updating tests
- **chore:** Maintenance tasks (dependencies, build, etc.)
- **perf:** Performance improvement
- **ci:** CI/CD changes

### Scopes

- **camera** - Camera controller
- **api** - API endpoints
- **streaming** - Streaming manager
- **config** - Configuration
- **tests** - Test suite
- **docs** - Documentation

### Examples

```
feat(camera): add autofocus control for Camera Module 3

Implements autofocus mode, lens position, and range controls
for Camera Module 3 with hardware autofocus support.

Closes #42
```

```
fix(api): handle null values in status endpoint

Status endpoint was returning null for v2.0 fields because
they weren't being passed to the Pydantic model. Fixed by
adding all new fields to CameraStatusResponse constructor.

Fixes #89
```

```
docs: add installation guide for NoIR cameras

Added section on NoIR camera setup with tuning file
auto-detection and IR illumination recommendations.
```

```
test: add integration tests for snapshot endpoint

Covers base64 encoding, resolution parameter, and
autofocus trigger functionality.
```

### Commit Best Practices

- **Atomic commits** - One logical change per commit
- **Clear description** - Explain WHAT and WHY, not HOW
- **Present tense** - "add feature" not "added feature"
- **Imperative mood** - "fix bug" not "fixes bug"
- **Reference issues** - Use "Closes #123" or "Fixes #456"

---

## Testing Requirements

### Test Coverage

- **Minimum 80% coverage** for new code
- **All public methods** must have tests
- **Happy path AND error cases** must be tested
- **Integration tests** for new API endpoints

### Running Tests

```bash
# All unit tests
pytest tests/ --ignore=tests/test_api_integration.py

# With coverage
pytest --cov=camera_service --cov-report=term-missing

# Specific test file
pytest tests/test_camera_controller.py -v

# Integration tests (requires running service)
python main.py  # Terminal 1
./scripts/test-api-v2.sh  # Terminal 2
```

### Writing Tests

**Unit test example:**

```python
def test_set_autofocus_mode_continuous(mock_camera_controller):
    """Test setting autofocus to continuous mode."""
    controller = mock_camera_controller

    result = controller.set_autofocus_mode("continuous")

    assert result is True
    assert controller._autofocus_mode == "continuous"
```

**Integration test example:**

```python
def test_snapshot_endpoint():
    """Test POST /v1/camera/snapshot returns base64 JPEG."""
    response = requests.post(
        f"{BASE_URL}/v1/camera/snapshot",
        json={"width": 1920, "height": 1080}
    )

    assert response.status_code == 200
    data = response.json()
    assert "image" in data
    assert len(data["image"]) > 0
    # Verify base64
    import base64
    base64.b64decode(data["image"])  # Should not raise
```

---

## Documentation

### What to Document

- **New features** - Update README.md and docs/
- **API changes** - Update docs/api-reference.md
- **Configuration** - Update docs/configuration.md
- **Breaking changes** - Update docs/upgrade-v2.md
- **Installation changes** - Update docs/installation.md

### Documentation Style

- **Clear and concise** - Easy to understand
- **Examples** - Show don't just tell
- **Code blocks** - Use syntax highlighting
- **Screenshots** - Include when helpful
- **Keep updated** - Docs should match code

### Documentation Checklist

When adding a feature, update:

- [ ] README.md (if user-facing)
- [ ] docs/api-reference.md (if API endpoint)
- [ ] docs/configuration.md (if new config option)
- [ ] .env.example (if new environment variable)
- [ ] CHANGELOG.md (following Keep a Changelog format)
- [ ] Docstrings in code (public methods)

---

## Questions?

- **Documentation:** Read [docs/development.md](docs/development.md)
- **Issues:** [GitHub Issues](https://github.com/gmathy2104/pi-camera-service/issues)
- **Discussions:** [GitHub Discussions](https://github.com/gmathy2104/pi-camera-service/discussions)

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to Pi Camera Service! 🎉
