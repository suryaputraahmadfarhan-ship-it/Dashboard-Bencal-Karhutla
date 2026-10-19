# -*- coding: utf-8 -*-
"""Fungsi hash murni (tanpa Streamlit) agar hash_password.py bisa jalan di komputer mana pun."""
import hashlib

ITERATIONS = 260_000


def hash_password(password: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), ITERATIONS).hex()
