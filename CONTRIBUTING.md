# Contributing to AnyPS5 Launcher

Thank you for your interest in contributing to AnyPS5 Launcher! This document outlines guidelines and conventions for contributing to the project.

---

## 🔒 Hard Constraints & Security Rules

1. **Strict Localhost Binding:**
   The backend must bind **strictly to `127.0.0.1`** (never `0.0.0.0`).
2. **Subprocess Safety:**
   Never use `shell=True` when invoking processes or the AnyPS5 relinker. Always pass arguments as clean, tokenized lists (`subprocess.Popen([...])`).
3. **No Copyrighted Material:**
   Never commit, distribute, or link to copyrighted Sony PlayStation 5 game files, decryption keys, or proprietary firmware. Users supply dumps from consoles they legally own.
4. **Third-Party Separation:**
   The launcher is a companion and workflow tool; it does not fork or redistribute AnyPS5 itself.
5. **Zero External Dependencies:**
   The backend core runs entirely on the Python Standard Library (Python 3.8+). Do not introduce mandatory third-party pip dependencies without maintainer approval.

---

## 🛠️ Development Workflow

### 1. Clone & Setup
```bash
git clone https://github.com/ErenYeager1836/AnyPS5-Launcher.git
cd AnyPS5-Launcher
```

### 2. Run the Local Backend
```bash
python server/main.py
```
This serves the frontend at `http://127.0.0.1:8085` and initiates the background API.

### 3. Running the Test Suite
All tests use Python's built-in `unittest` framework (no packages required):
```bash
python -m unittest discover tests -v
```

Before opening a pull request, ensure all 20+ unit and integration tests pass without error.

---

## 📝 Commit Conventions

- Use clear, descriptive commit messages describing the feature or bug fixed.
- Keep commits focused and atomic.
- Update documentation in `docs/` and `README.md` when introducing new endpoints or changing configuration schemas.

---

## 🐛 Reporting Issues

If you encounter bugs or have feature ideas, please use the issue templates:
- [Bug Report](https://github.com/ErenYeager1836/AnyPS5-Launcher/issues/new?template=bug_report.md)
- [Feature Request](https://github.com/ErenYeager1836/AnyPS5-Launcher/issues/new?template=feature_request.md)
