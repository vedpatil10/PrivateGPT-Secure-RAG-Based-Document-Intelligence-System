from core.security import create_access_token, decode_access_token, decrypt_file, encrypt_file


def test_access_token_roundtrip(sample_claims):
    token = create_access_token(sample_claims)
    decoded = decode_access_token(token)

    assert decoded["sub"] == sample_claims["sub"]
    assert decoded["email"] == sample_claims["email"]
    assert decoded["org_id"] == sample_claims["org_id"]
    assert decoded["role"] == sample_claims["role"]


def test_access_token_contains_timestamps(sample_claims):
    token = create_access_token(sample_claims)
    decoded = decode_access_token(token)

    assert "exp" in decoded
    assert "iat" in decoded


def test_file_encryption_roundtrip():
    payload = b"private document bytes"

    encrypted = encrypt_file(payload)
    decrypted = decrypt_file(encrypted)

    assert encrypted != payload
    assert decrypted == payload
