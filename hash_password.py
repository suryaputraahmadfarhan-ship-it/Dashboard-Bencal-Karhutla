# -*- coding: utf-8 -*-
"""Buat hash password untuk Secrets Streamlit.  Jalankan di komputer Anda:  python hash_password.py"""
import getpass
import os

from auth_hash import hash_password

username = input("Username (huruf kecil, mis. admin): ").strip().lower()
nama = input("Nama tampilan: ").strip()
role = input("Peran (Admin / Personel): ").strip().capitalize()
if role not in ("Admin", "Personel"):
    raise SystemExit("Peran harus Admin atau Personel.")
pw = getpass.getpass("Password (min. 12 karakter): ")
if len(pw) < 12:
    raise SystemExit("Password terlalu pendek.")
if pw != getpass.getpass("Ulangi password: "):
    raise SystemExit("Password tidak sama.")
salt = os.urandom(16).hex()
print("\nTempel blok ini ke Secrets (di bawah [auth.users]):\n")
print(f'[auth.users.{username}]')
print(f'name = "{nama}"')
print(f'role = "{role}"')
print(f'salt = "{salt}"')
print(f'hash = "{hash_password(pw, salt)}"')
