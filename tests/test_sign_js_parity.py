"""Cross-implementation parity tests: scripts/sign.js against scripts/sign.py.

Skipped automatically when Node.js is not on PATH, so this never blocks CI
on a runner without a Node toolchain -- it exists for contributors, and for
any future CI job that does have one.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="Node.js not available on PATH"
)

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
SIGN_PY = SCRIPTS_DIR / "sign.py"
SIGN_JS = SCRIPTS_DIR / "sign.js"

TEST_SEED = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd"
TEST_PASSPHRASE = "a passphrase seed, not hex"


def run_py(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SIGN_PY), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def run_js(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", str(SIGN_JS), *args], capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize("seed", [TEST_SEED, TEST_PASSPHRASE])
def test_did_matches(seed: str) -> None:
    assert run_py("did", "--seed", seed).stdout == run_js("did", "--seed", seed).stdout


@pytest.mark.parametrize("seed", [TEST_SEED, TEST_PASSPHRASE])
def test_say_matches(seed: str) -> None:
    py = run_py("say", "--seed", seed, "lobby", "12345", "hello world")
    js = run_js("say", "--seed", seed, "lobby", "12345", "hello world")
    assert py.stdout == js.stdout


def test_set_matches() -> None:
    py = run_py("set", "--seed", TEST_SEED, "ns", "key", "999", "a value")
    js = run_js("set", "--seed", TEST_SEED, "ns", "key", "999", "a value")
    assert py.stdout == js.stdout


def test_unicode_sweep_matches() -> None:
    text = "\thello\u200dworld  \t \U0001f389 \u4f60\u597d "
    py = run_py("say", "--seed", TEST_SEED, "room", "1", text)
    js = run_js("say", "--seed", TEST_SEED, "room", "1", text)
    assert py.stdout == js.stdout


def test_bad_nonce_matches() -> None:
    py = run_py("say", "--seed", TEST_SEED, "room", "abc", "hi")
    js = run_js("say", "--seed", TEST_SEED, "room", "abc", "hi")
    assert py.returncode == js.returncode == 1
    assert py.stderr.strip() == js.stderr.strip()


def test_bad_nonce_with_quote_matches() -> None:
    # Exercises the repr()-style quote selection in the error message:
    # a value containing a single quote should switch to double quotes.
    py = run_py("say", "--seed", TEST_SEED, "room", "a'bc", "hi")
    js = run_js("say", "--seed", TEST_SEED, "room", "a'bc", "hi")
    assert py.returncode == js.returncode == 1
    assert py.stderr.strip() == js.stderr.strip()


def test_empty_after_sweep_matches() -> None:
    py = run_py("say", "--seed", TEST_SEED, "room", "1", "\t\t\t")
    js = run_js("say", "--seed", TEST_SEED, "room", "1", "\t\t\t")
    assert py.returncode == js.returncode == 1
    assert py.stderr.strip() == js.stderr.strip()


def test_over_limit_matches() -> None:
    long_text = "a" * 5000
    py = run_py("say", "--seed", TEST_SEED, "room", "1", long_text)
    js = run_js("say", "--seed", TEST_SEED, "room", "1", long_text)
    assert py.returncode == js.returncode == 1
    assert py.stderr.strip() == js.stderr.strip()


@pytest.mark.parametrize(
    "args",
    [
        ("keygen", "extra"),
        ("did", "--seed", TEST_SEED, "extra"),
        ("say", "--seed", TEST_SEED, "room", "1", "text", "extra"),
        ("set", "--seed", TEST_SEED, "ns", "key", "1", "value", "extra"),
        ("did", "--seed"),
    ],
)
def test_malformed_invocations_are_rejected(args: tuple[str, ...]) -> None:
    assert run_py(*args).returncode != 0
    assert run_js(*args).returncode != 0
