# -*- coding: utf-8 -*-
"""Autentikasi Admin & Personel.

- Kredensial TIDAK disimpan di kode/GitHub. Semua ada di st.secrets (lihat secrets.toml.example).
- Password disimpan sebagai hash PBKDF2-HMAC-SHA256 + salt (buat dengan hash_password.py).
- Akun dikunci 15 menit setelah 5 kali salah (dihitung di server, per username).
- Sesi otomatis berakhir setelah tidak aktif (default 30 menit).
"""
import hmac
import time
from datetime import datetime, timedelta, timezone

import streamlit as st

from auth_hash import hash_password
from theme import EMBLEM

MAX_FAILS = 5
LOCK_SECONDS = 15 * 60
WIB = timezone(timedelta(hours=7))
ROLES = ("Admin", "Personel")


@st.cache_resource
def _server_state():
    # dipakai bersama semua sesi: percobaan gagal & log akses
    return {"fails": {}, "log": []}


def _log(user, event):
    _server_state()["log"].append({
        "Waktu (WIB)": datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S"),
        "Username": user,
        "Peristiwa": event,
    })
    del _server_state()["log"][:-500]  # simpan 500 terakhir


def get_log():
    return list(reversed(_server_state()["log"]))


def _users():
    try:
        raw = st.secrets["auth"]["users"]
        return {str(k).lower(): dict(v) for k, v in raw.items()}
    except Exception:
        return None


def _session_minutes():
    try:
        return int(st.secrets["auth"].get("session_minutes", 30))
    except Exception:
        return 30


def _locked_for(username):
    rec = _server_state()["fails"].get(username)
    if rec and rec["until"] > time.time():
        return int(rec["until"] - time.time())
    return 0


def _register_fail(username):
    fails = _server_state()["fails"]
    rec = fails.get(username, {"n": 0, "until": 0})
    if rec["until"] and rec["until"] <= time.time():
        rec = {"n": 0, "until": 0}
    rec["n"] += 1
    if rec["n"] >= MAX_FAILS:
        rec["until"] = time.time() + LOCK_SECONDS
        rec["n"] = 0
        _log(username, "Akun dikunci 15 menit (5x gagal)")
    fails[username] = rec


def _check(username, password, users):
    """Verifikasi dengan waktu konstan; tetap menghitung hash walau username tidak ada."""
    u = users.get(username)
    salt = u["salt"] if u else "00" * 16
    expected = u["hash"] if u else "0" * 64
    ok = hmac.compare_digest(hash_password(password, salt), expected)
    return u if (u and ok) else None


def current_user():
    return st.session_state.get("auth")


def is_admin():
    u = current_user()
    return bool(u and u["role"] == "Admin")


def logout(reason=None):
    u = current_user()
    if u:
        _log(u["username"], "Logout" if not reason else reason)
    st.session_state.pop("auth", None)
    if reason:
        st.session_state["login_notice"] = reason


def _login_css():
    st.markdown("""
    <style>
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {display:none;}
    .stApp {background: radial-gradient(1200px 600px at 15% -10%, #dbe8ff 0%, #f3f7fd 55%, #eef3fb 100%);}
    .login-brand {text-align:center; margin: 4vh 0 18px 0;}
    .login-brand img {width: 84px;}
    .login-brand .t1 {font-weight:700; color:#0f2a5c; letter-spacing:.3px; margin-top:10px;}
    .login-brand .t2 {color:#475f8a; font-size:14px;}
    .login-note {color:#5b6f94; font-size:12.5px; text-align:center; margin-top:10px;}
    </style>""", unsafe_allow_html=True)


def require_login():
    """Hentikan halaman sampai pengguna login. Mengembalikan dict pengguna."""
    # ---- sesi aktif: cek batas waktu tidak aktif
    u = current_user()
    if u:
        idle = time.time() - u["last_seen"]
        if idle > _session_minutes() * 60:
            logout("Sesi berakhir karena tidak aktif")
        else:
            u["last_seen"] = time.time()
            return u

    _login_css()
    users = _users()

    left, mid, right = st.columns([1, 1.15, 1])
    with mid:
        st.markdown(f"""
        <div class="login-brand">
          <img src="{EMBLEM}">
          <div class="t1">Dashboard Kebencanaan</div>
          <div class="t2">Direktorat 2.3 · Deputi 2 · Sumatera &amp; Kalimantan</div>
        </div>""", unsafe_allow_html=True)

        if users is None:
            st.error("Akun login belum dikonfigurasi.")
            st.markdown(
                "Tambahkan bagian `[auth]` di **Secrets** (Streamlit Cloud: *Manage app → Settings → Secrets*; "
                "lokal: `.streamlit/secrets.toml`). Contoh format ada di `secrets.toml.example`, "
                "dan hash password dibuat dengan `python hash_password.py`.")
            st.stop()

        notice = st.session_state.pop("login_notice", None)
        if notice:
            st.info(notice)

        with st.form("login", clear_on_submit=False):
            st.markdown("#### Masuk")
            username = st.text_input("Username", autocomplete="username").strip().lower()
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submit = st.form_submit_button("Masuk", type="primary", use_container_width=True)

        if submit:
            wait = _locked_for(username)
            if wait:
                st.error(f"Akun dikunci sementara. Coba lagi dalam {wait // 60 + 1} menit.")
            elif not username or not password:
                st.warning("Isi username dan password.")
            else:
                user = _check(username, password, users)
                if user is None:
                    _register_fail(username)
                    _log(username or "-", "Login gagal")
                    st.error("Username atau password salah.")
                else:
                    role = user.get("role", "Personel")
                    if role not in ROLES:
                        role = "Personel"
                    st.session_state["auth"] = {
                        "username": username,
                        "name": user.get("name", username),
                        "role": role,
                        "last_seen": time.time(),
                    }
                    _server_state()["fails"].pop(username, None)
                    _log(username, f"Login berhasil ({role})")
                    st.rerun()

        st.markdown('<div class="login-note">Akses terbatas untuk personel yang berwenang. '
                    'Seluruh aktivitas masuk dicatat.</div>', unsafe_allow_html=True)
    st.stop()
