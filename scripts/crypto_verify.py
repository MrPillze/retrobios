"""3DS signature and crypto verification for emulator profile validation.

Reproduces the exact verification logic from Azahar/Citra source code:
- SecureInfo_A: RSA-2048 PKCS1v15 SHA256
- LocalFriendCodeSeed_B: RSA-2048 PKCS1v15 SHA256
- movable.sed: magic check + RSA on embedded LFCS
- otp.bin: AES-128-CBC decrypt + magic + SHA256 hash

RSA verification is pure Python (no dependencies).
AES decryption requires 'cryptography' library or falls back to openssl CLI.

Source refs:
  Azahar src/core/hw/unique_data.cpp
  Azahar src/core/hw/rsa/rsa.cpp
  Azahar src/core/file_sys/otp.cpp
"""
from __future__ import annotations

import hashlib
import struct
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Key file parsing (keys.txt / aes_keys.txt format)
# ---------------------------------------------------------------------------

def parse_keys_file(path: str | Path) -> dict[str, dict[str, bytes]]:
    """Parse a 3DS keys file with :AES, :RSA, :ECC sections.

    Returns {section: {key_name: bytes_value}}.
    """
    sections: dict[str, dict[str, bytes]] = {}
    current_section = ""
    for line in Path(path).read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(":"):
            current_section = line[1:].strip()
            if current_section not in sections:
                sections[current_section] = {}
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        try:
            sections.setdefault(current_section, {})[key] = bytes.fromhex(value)
        except ValueError:
            continue
    return sections


def find_keys_file(bios_dir: str | Path) -> Path | None:
    """Find the 3DS keys file in the bios directory."""
    candidates = [
        Path(bios_dir) / "Nintendo" / "3DS" / "aes_keys.txt",
        Path(bios_dir) / "Nintendo" / "3DS" / "keys.txt",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# Pure Python RSA-2048 PKCS1v15 SHA256 verification (zero dependencies)
# ---------------------------------------------------------------------------

def _rsa_verify_pkcs1v15_sha256(
    message: bytes,
    signature: bytes,
    modulus: bytes,
    exponent: bytes,
) -> bool:
    """Verify RSA-2048 PKCS#1 v1.5 with SHA-256.

    Pure Python — uses Python's native int for modular exponentiation.
    Reproduces CryptoPP::RSASS<PKCS1v15, SHA256>::Verifier.
    """
    n = int.from_bytes(modulus, "big")
    e = int.from_bytes(exponent, "big")
    s = int.from_bytes(signature, "big")

    if s >= n:
        return False

    # RSA verification: m = s^e mod n
    m = pow(s, e, n)

    # Convert to bytes, padded to modulus length
    mod_len = len(modulus)
    try:
        em = m.to_bytes(mod_len, "big")
    except OverflowError:
        return False

    # PKCS#1 v1.5 signature encoding: 0x00 0x01 [0xFF padding] 0x00 [DigestInfo]
    # DigestInfo for SHA-256:
    # SEQUENCE { SEQUENCE { OID sha256, NULL }, OCTET STRING hash }
    digest_info_prefix = bytes([
        0x30, 0x31,  # SEQUENCE (49 bytes)
        0x30, 0x0D,  # SEQUENCE (13 bytes)
        0x06, 0x09,  # OID (9 bytes)
        0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01,  # sha256
        0x05, 0x00,  # NULL
        0x04, 0x20,  # OCTET STRING (32 bytes)
    ])

    sha256_hash = hashlib.sha256(message).digest()
    expected_digest_info = digest_info_prefix + sha256_hash

    # Expected encoding: 0x00 0x01 [0xFF * ps_len] 0x00 [digest_info]
    t_len = len(expected_digest_info)
    ps_len = mod_len - t_len - 3
    if ps_len < 8:
        return False

    expected_em = b"\x00\x01" + (b"\xff" * ps_len) + b"\x00" + expected_digest_info
    return em == expected_em


# ---------------------------------------------------------------------------
# AES-128-CBC decryption (with fallback)
# ---------------------------------------------------------------------------

def _aes_128_cbc_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypt AES-128-CBC without padding."""
    # Try cryptography library first
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        return decryptor.update(data) + decryptor.finalize()
    except ImportError:
        pass

    # Try pycryptodome
    try:
        from Crypto.Cipher import AES  # type: ignore[import-untyped]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.decrypt(data)
    except ImportError:
        pass

    # Fallback to openssl CLI
    try:
        result = subprocess.run(
            [
                "openssl", "enc", "-aes-128-cbc", "-d",
                "-K", key.hex(), "-iv", iv.hex(), "-nopad",
            ],
            input=data,
            capture_output=True,
            check=True,
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(
            "AES decryption requires 'cryptography' or 'pycryptodome' library, "
            "or 'openssl' CLI tool"
        )


# ---------------------------------------------------------------------------
# File verification functions
# ---------------------------------------------------------------------------

def verify_secure_info_a(
    filepath: str | Path,
    keys: dict[str, dict[str, bytes]],
) -> tuple[bool, str]:
    """Verify SecureInfo_A RSA-2048 PKCS1v15 SHA256 signature.

    Source: Azahar src/core/hw/unique_data.cpp:43-92
    Struct: 0x100 signature + 0x11 body (region + unknown + serial) = 0x111

    Returns (valid, reason_string).
    """
    data = Path(filepath).read_bytes()

    # Size check
    if len(data) != 0x111:
        return False, f"size mismatch: expected 273, got {len(data)}"

    # Check validity (at least one non-zero byte in serial)
    serial = data[0x102:0x111]
    if serial == b"\x00" * 15:
        return False, "invalid: serial_number is all zeros"

    # Get RSA keys
    rsa_keys = keys.get("RSA", {})
    modulus = rsa_keys.get("secureInfoMod")
    exponent = rsa_keys.get("secureInfoExp")
    if not modulus or not exponent:
        return False, "missing RSA keys (secureInfoMod/secureInfoExp) in keys file"

    signature = data[0x000:0x100]
    body = data[0x100:0x111]

    if _rsa_verify_pkcs1v15_sha256(body, signature, modulus, exponent):
        return True, "signature valid"

    # Region change detection: try all other region values
    region_byte = data[0x100]
    for test_region in range(7):
        if test_region == region_byte:
            continue
        modified_body = bytes([test_region]) + body[1:]
        if _rsa_verify_pkcs1v15_sha256(modified_body, signature, modulus, exponent):
            return False, f"signature invalid (region changed from {test_region} to {region_byte})"

    return False, "signature invalid"


def verify_local_friend_code_seed_b(
    filepath: str | Path,
    keys: dict[str, dict[str, bytes]],
) -> tuple[bool, str]:
    """Verify LocalFriendCodeSeed_B RSA-2048 PKCS1v15 SHA256 signature.

    Source: Azahar src/core/hw/unique_data.cpp:94-123
    Struct: 0x100 signature + 0x10 body (unknown + friend_code_seed) = 0x110

    Returns (valid, reason_string).
    """
    data = Path(filepath).read_bytes()

    if len(data) != 0x110:
        return False, f"size mismatch: expected 272, got {len(data)}"

    # Check validity (friend_code_seed != 0)
    friend_code_seed = struct.unpack_from("<Q", data, 0x108)[0]
    if friend_code_seed == 0:
        return False, "invalid: friend_code_seed is zero"

    rsa_keys = keys.get("RSA", {})
    modulus = rsa_keys.get("lfcsMod")
    exponent = rsa_keys.get("lfcsExp")
    if not modulus or not exponent:
        return False, "missing RSA keys (lfcsMod/lfcsExp) in keys file"

    signature = data[0x000:0x100]
    body = data[0x100:0x110]

    if _rsa_verify_pkcs1v15_sha256(body, signature, modulus, exponent):
        return True, "signature valid"
    return False, "signature invalid"


def verify_movable_sed(
    filepath: str | Path,
    keys: dict[str, dict[str, bytes]],
) -> tuple[bool, str]:
    """Verify movable.sed: magic check + RSA on embedded LFCS.

    Source: Azahar src/core/hw/unique_data.cpp:170-200
    Struct: 0x08 header + 0x110 embedded LFCS + 0x08 keyY = 0x120
    Full variant: 0x120 + 0x20 extra = 0x140

    Returns (valid, reason_string).
    """
    data = Path(filepath).read_bytes()

    if len(data) not in (0x120, 0x140):
        return False, f"size mismatch: expected 288 or 320, got {len(data)}"

    # Magic check: "SEED" at offset 0
    magic = data[0:4]
    if magic != b"SEED":
        return False, f"invalid magic: expected 'SEED', got {magic!r}"

    # Embedded LFCS at offset 0x08, size 0x110
    lfcs_data = data[0x08:0x118]

    # Verify the embedded LFCS signature (same as LocalFriendCodeSeed_B)
    rsa_keys = keys.get("RSA", {})
    modulus = rsa_keys.get("lfcsMod")
    exponent = rsa_keys.get("lfcsExp")
    if not modulus or not exponent:
        return False, "missing RSA keys (lfcsMod/lfcsExp) in keys file"

    signature = lfcs_data[0x000:0x100]
    body = lfcs_data[0x100:0x110]

    if _rsa_verify_pkcs1v15_sha256(body, signature, modulus, exponent):
        return True, "magic valid, LFCS signature valid"
    return False, "magic valid, LFCS signature invalid"


def verify_otp(
    filepath: str | Path,
    keys: dict[str, dict[str, bytes]],
) -> tuple[bool, str]:
    """Verify otp.bin: AES-128-CBC decrypt + magic + SHA-256 hash.

    Source: Azahar src/core/file_sys/otp.cpp
    Struct: 0xE0 body + 0x20 SHA256 hash = 0x100

    ECC certificate verification (sect233r1) is not reproduced — requires
    binary field curve arithmetic unavailable in standard Python libraries.
    AES decryption + SHA-256 hash is sufficient to prove file integrity.

    Returns (valid, reason_string).
    """
    data = bytearray(Path(filepath).read_bytes())

    if len(data) != 0x100:
        return False, f"size mismatch: expected 256, got {len(data)}"

    aes_keys = keys.get("AES", {})
    otp_key = aes_keys.get("otpKey")
    otp_iv = aes_keys.get("otpIV")

    # Check magic before decryption (file might already be decrypted)
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic != 0xDEADB00F:
        if not otp_key or not otp_iv:
            return False, "encrypted OTP but missing AES keys (otpKey/otpIV) in keys file"
        try:
            data = bytearray(_aes_128_cbc_decrypt(bytes(data), otp_key, otp_iv))
        except RuntimeError as e:
            return False, str(e)
        magic = struct.unpack_from("<I", data, 0)[0]
        if magic != 0xDEADB00F:
            return False, f"decryption failed: magic 0x{magic:08X} != 0xDEADB00F"

    # SHA-256 hash verification
    body = bytes(data[0x00:0xE0])
    stored_hash = bytes(data[0xE0:0x100])
    computed_hash = hashlib.sha256(body).digest()

    if computed_hash != stored_hash:
        return False, "SHA-256 hash mismatch (OTP corrupted)"

    return True, "decrypted, magic valid, SHA-256 valid (ECC cert not verified — sect233r1)"


# ---------------------------------------------------------------------------
# Unified verification interface for verify.py
# ---------------------------------------------------------------------------

# Map from (filename, validation_type) to verification function
_CRYPTO_VERIFIERS: dict[str, callable] = {
    "SecureInfo_A": verify_secure_info_a,
    "LocalFriendCodeSeed_B": verify_local_friend_code_seed_b,
    "movable.sed": verify_movable_sed,
    "otp.bin": verify_otp,
}


def check_crypto_validation(
    local_path: str,
    filename: str,
    bios_dir: str,
) -> str | None:
    """Check signature/crypto validation for 3DS files.

    Returns None if verification passes or is not applicable.
    Returns a reason string on failure.
    """
    verifier = _CRYPTO_VERIFIERS.get(filename)
    if not verifier:
        return None

    keys_file = find_keys_file(bios_dir)
    if not keys_file:
        return "crypto check skipped: no keys file found"

    keys = parse_keys_file(keys_file)
    valid, reason = verifier(local_path, keys)
    if valid:
        return None
    return reason
