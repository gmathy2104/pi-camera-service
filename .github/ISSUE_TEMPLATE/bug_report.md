---
name: Bug Report
about: Report a bug or issue
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description

A clear and concise description of the bug.

## Environment

- **Raspberry Pi Model:** (e.g., Pi 5, Pi 4, Zero 2W)
- **Camera Model:** (e.g., Camera Module 3, Camera Module 3 Wide NoIR, HQ Camera)
- **OS Version:** (run `cat /etc/os-release`)
- **Python Version:** (run `python --version`)
- **Service Version:** (run `cat VERSION`)

## Steps to Reproduce

1. Step one
2. Step two
3. Step three
4. See error

## Expected Behavior

What you expected to happen.

## Actual Behavior

What actually happened.

## Logs

Please provide relevant log output:

```bash
sudo journalctl -u pi-camera-service -n 100
```

<details>
<summary>Logs (click to expand)</summary>

```
[paste logs here]
```

</details>

## Configuration

Your `.env` configuration (remove sensitive data like API keys!):

```bash
CAMERA_WIDTH=1920
CAMERA_HEIGHT=1080
# ... other settings
```

## Screenshots

If applicable, add screenshots to help explain the problem.

## Additional Context

Any other context about the problem.
