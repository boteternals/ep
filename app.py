import streamlit as st
import boto3
import json
import hashlib
import uuid
import queue
import threading
import random
import re
import mimetypes
import requests
from datetime import datetime
from botocore.exceptions import ClientError
from botocore.client import Config

# === COOKIE LIB (fallback aman kalau belum install) ===
try:
    import extra_streamlit_components as stx
    _HAS_COOKIES = True
except ImportError:
    _HAS_COOKIES = False


# ==========================================
# 0. PAGE CONFIG & CSS (TEMA BIRU)
# ==========================================
st.set_page_config(
    page_title="ElangPintar",
    page_icon="https://cdn.aceimg.com/mD4NlOxLG.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp { background: radial-gradient(ellipse at top, #1E3A8A 0%, #0F172A 45%, #020617 100%); }
    [data-testid="collapsedControl"] {display: none;}
    [data-testid="stSidebar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding-bottom: 130px !important; padding-top: 2rem !important; }
    h1, h2, h3, h4, h5, h6 { color: #E0F2FE !important; }
    .stMarkdown p, label { color: #CBD5E1; }

    div[data-testid="stRadio"] {
        position: fixed; bottom: 0; left: 0; right: 0;
        background: linear-gradient(180deg, #0B132B 0%, #020617 100%);
        padding: 12px 5px 16px 5px; z-index: 9999;
        border-top: 1px solid #1E3A8A;
        box-shadow: 0 -8px 25px rgba(30, 64, 175, 0.35);
    }
    div[data-testid="stRadio"] > div {
        display: flex; flex-direction: row !important;
        justify-content: space-around; width: 100%; gap: 4px;
    }
    div[data-testid="stRadio"] label {
        flex: 1; text-align: center; margin: 0 !important;
        padding: 8px 4px 6px 4px !important; cursor: pointer;
        display: flex; flex-direction: column; align-items: center;
        position: relative; border-radius: 12px;
        transition: background 0.25s ease, transform 0.2s ease;
    }
    div[data-testid="stRadio"] label:hover {
        background: rgba(56, 189, 248, 0.08); transform: translateY(-1px);
    }
    div[data-testid="stRadio"] label::before {
        content: ''; position: absolute; top: -1px; left: 50%;
        transform: translateX(-50%); width: 0; height: 3px;
        background: linear-gradient(90deg, #3B82F6, #38BDF8);
        border-radius: 3px;
        transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 0 10px #38BDF8;
    }
    div[data-testid="stRadio"] label:has(input:checked)::before { width: 45%; }
    div[data-testid="stRadio"] label > div:first-child { display: none !important; }
    div[data-testid="stRadio"] label p {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 4px;
        font-size: 10px !important; color: #64748B !important;
        margin: 0 !important; font-weight: 600 !important;
        transition: color 0.25s ease; line-height: 1.2;
    }
    div[data-testid="stRadio"] label img {
        width: 24px; height: 24px; margin: 0 !important;
        opacity: 0.6; transition: all 0.25s ease;
    }
    div[data-testid="stRadio"] label:has(input:checked) p { color: #38BDF8 !important; }
    div[data-testid="stRadio"] label:has(input:checked) img {
        opacity: 1;
        filter: invert(63%) sepia(54%) saturate(3282%) hue-rotate(177deg) brightness(99%) contrast(95%);
        transform: scale(1.12);
    }

    .stButton > button {
        background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%);
        border: 1px solid #2563EB; color: white !important;
        border-radius: 12px; font-weight: 600; transition: all 0.2s ease;
        box-shadow: 0 2px 10px rgba(59, 130, 246, 0.3);
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563EB 0%, #60A5FA 100%);
        box-shadow: 0 6px 18px rgba(59, 130, 246, 0.5);
        transform: translateY(-2px); border-color: #60A5FA;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 100%);
        box-shadow: 0 4px 16px rgba(56, 189, 248, 0.45);
    }
    .stTextInput input, .stTextArea textarea {
        background: #0F172A !important; border: 1px solid #1E3A8A !important;
        color: #E0F2FE !important; border-radius: 10px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background: #0F172A; border-radius: 12px;
        padding: 4px; gap: 4px; border: 1px solid #1E3A8A;
    }
    .stTabs [data-baseweb="tab"] {
        color: #64748B; border-radius: 8px; font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1E40AF, #3B82F6) !important;
        color: white !important;
    }
    .profile-card {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        border-radius: 20px; padding: 20px; color: white;
        display: flex; align-items: center; margin-bottom: 20px;
        box-shadow: 0 10px 28px rgba(59, 130, 246, 0.4);
        border: 1px solid rgba(96, 165, 250, 0.35);
    }
    .profile-avatar {
        width: 64px; height: 64px; border-radius: 50%;
        background: rgba(255,255,255,0.15);
        display: flex; justify-content: center; align-items: center;
        margin-right: 15px; border: 2px solid rgba(255,255,255,0.35);
        box-shadow: 0 0 15px rgba(96, 165, 250, 0.5);
    }
    .profile-info h3 { margin: 0; font-size: 20px; font-weight: 700; color: white !important; }
    .profile-info p { margin: 5px 0 0 0; font-size: 13px; color: rgba(255,255,255,0.85) !important; }
    .wallet-card {
        background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 45%, #0EA5E9 100%);
        border-radius: 24px; padding: 22px 24px; color: white;
        margin-bottom: 20px;
        box-shadow: 0 12px 32px rgba(59, 130, 246, 0.45), inset 0 1px 0 rgba(255,255,255,0.25);
        position: relative; overflow: hidden;
        border: 1px solid rgba(96, 165, 250, 0.4);
    }
    .wallet-card::before {
        content: ''; position: absolute; top: -60%; right: -20%;
        width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 55%);
        pointer-events: none;
    }
    .wallet-header {
        display: flex; align-items: center; gap: 8px;
        font-size: 13px; opacity: 0.95; font-weight: 500;
        margin-bottom: 4px; position: relative; z-index: 1;
    }
    .wallet-balance {
        font-size: 34px; font-weight: 800; letter-spacing: -0.5px;
        margin: 10px 0 6px 0; text-shadow: 0 3px 10px rgba(0,0,0,0.25);
        position: relative; z-index: 1;
    }
    .wallet-footer {
        display: flex; justify-content: space-between; align-items: center;
        font-size: 12px; opacity: 0.92; margin-top: 14px;
        padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.28);
        position: relative; z-index: 1;
    }
    .wallet-badge {
        background: rgba(255,255,255,0.22); padding: 3px 10px;
        border-radius: 20px; font-size: 11px; font-weight: 600;
        backdrop-filter: blur(6px);
    }
    .list-item {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 14px 16px; border-radius: 14px; margin-bottom: 10px;
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 2px 10px rgba(0,0,0,0.35);
        font-weight: 500; color: #F8FAFC;
        border: 1px solid #1E3A8A;
        transition: all 0.25s ease;
    }
    .list-item:hover {
        border-color: #3B82F6;
        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.25);
        transform: translateY(-1px);
    }
    .list-item-left { display: flex; align-items: center; gap: 12px; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# COOKIE MANAGER (persist session)
# ==========================================
# PERBAIKAN: Hapus @st.cache_resource
def get_cookie_manager():
    if not _HAS_COOKIES:
        return None
    return stx.CookieManager(key="elang_cookie_mgr")

cookie_manager = get_cookie_manager()


# ==========================================
# SVG INLINE HELPER
# ==========================================
_SVG_PATHS = {
    "check":      '<polyline points="20 6 9 17 4 12"/>',
    "x":          '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "trash":      '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "download":   '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    "video":      '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>',
    "clock":      '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "calendar":   '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    "folder":     '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    "pending":    '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
    "link":       '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "package":    '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    "user":       '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "bell":       '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    "send":       '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    "alert":      '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "info":       '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
}

def svg(name, size=16, color="#38BDF8"):
    path = _SVG_PATHS.get(name, "")
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'style="display:inline-block;vertical-align:middle;">{path}</svg>'
    )

def svg_html(name, text, size=16, color="#38BDF8"):
    return f"{svg(name, size, color)} <span style='vertical-align:middle;'>{text}</span>"


# ==========================================
# 1. S3 WORKER + QUEUE
# ==========================================
@st.cache_resource
def get_worker():
    class S3Worker:
        def __init__(self):
            raw_bucket = st.secrets.get("S3_BUCKET_NAME", "SatyaDev13/ElangP")
            if "/" in raw_bucket:
                namespace, bucket_name = raw_bucket.split("/", 1)
            else:
                namespace = st.secrets.get("S3_NAMESPACE", "SatyaDev13")
                bucket_name = raw_bucket

            raw_endpoint = st.secrets.get("S3_ENDPOINT_URL", "https://s3.hf.co").rstrip("/")
            if "huggingface.co" in raw_endpoint:
                raw_endpoint = "https://s3.hf.co"
            if not raw_endpoint.endswith(f"/{namespace}"):
                endpoint_url = f"{raw_endpoint}/{namespace}"
            else:
                endpoint_url = raw_endpoint

            self.s3 = boto3.client(
                "s3", endpoint_url=endpoint_url,
                aws_access_key_id=st.secrets["S3_ACCESS_KEY_ID"],
                aws_secret_access_key=st.secrets["S3_SECRET_ACCESS_KEY"],
                config=Config(s3={"addressing_style": "path"}, signature_version="s3v4")
            )
            self.bucket = bucket_name
            self.q = queue.Queue()
            self.data = {
                "users": self._load("users.json", []),
                "databases": self._load("databases.json", []),
                "texts": self._load("texts.json", {"content": ""}),
                "payroll": self._load("payroll.json", {}),
                "reports": self._load("reports.json", {"ndp": [], "wd": [], "video": []}),
                "sessions": self._load("sessions.json", {})   # ⬅️ session persist
            }
            self.last_reset_date = datetime.now().date()

            admin_uid = st.secrets.get("ADMIN_UID", "admin")
            admin_pwd = st.secrets.get("ADMIN_PASSWORD", "admin123")

            if not self.data["users"]:
                self.data["users"].append({
                    "uid": admin_uid, "pass_hash": self.hash_pwd(admin_pwd),
                    "name": "Administrator", "role": "admin",
                    "banned": False, "accounts": [], "telegram": "",
                    "notifications": []
                })
                self._save("users.json", self.data["users"])
            else:
                for u in self.data["users"]:
                    u.setdefault("telegram", "")
                    u.setdefault("notifications", [])
                    u.setdefault("accounts", [])
                    if u["uid"] == admin_uid and u["role"] == "admin":
                        if u["pass_hash"] != self.hash_pwd(admin_pwd):
                            u["pass_hash"] = self.hash_pwd(admin_pwd)
                            self._save("users.json", self.data["users"])
                        break

            # Bersihkan session expired saat startup
            self._cleanup_expired_sessions()

            self.thread = threading.Thread(target=self._process_queue, daemon=True)
            self.thread.start()

        def hash_pwd(self, pwd):
            return hashlib.sha256(f"elangpintar_secret_salt_2024{pwd}".encode()).hexdigest()

        def _load(self, key, default):
            try:
                obj = self.s3.get_object(Bucket=self.bucket, Key=key)
                return json.loads(obj["Body"].read().decode("utf-8"))
            except ClientError:
                self._save(key, default)
                return default
            except Exception:
                return default

        def _save(self, key, data):
            self.s3.put_object(
                Bucket=self.bucket, Key=key,
                Body=json.dumps(data).encode("utf-8"),
                ContentType="application/json"
            )

        def _process_queue(self):
            while True:
                task = self.q.get()
                if task is None: break
                func, args, kwargs, result_queue = task
                today = datetime.now().date()
                if self.last_reset_date != today:
                    self.data["databases"] = []
                    self.data["texts"] = {"content": ""}
                    self.data["sessions"] = {}                     # ⬅️ reset session
                    self._save("databases.json", [])
                    self._save("texts.json", {"content": ""})
                    self._save("sessions.json", {})                # ⬅️ reset session
                    self.last_reset_date = today
                try:
                    res = func(*args, **kwargs)
                    if result_queue is not None:
                        result_queue.put(res)
                except Exception as e:
                    print(f"[Worker Error] {e}")
                    if result_queue is not None:
                        result_queue.put(e)
                finally:
                    self.q.task_done()

        def execute(self, func, *args, **kwargs):
            res_q = queue.Queue()
            self.q.put((func, args, kwargs, res_q))
            return res_q.get()

        def execute_async(self, func, *args, **kwargs):
            self.q.put((func, args, kwargs, None))

        def save_file(self, key, data):
            self.data[key.replace(".json", "")] = data
            self._save(key, data)
            return True

        def upload_file_s3(self, file_bytes, filename):
            self.s3.put_object(Bucket=self.bucket, Key=f"uploads/{filename}", Body=file_bytes)
            return True

        def upload_video_s3(self, file_bytes, filename):
            try:
                if not file_bytes:
                    return "ERROR: File kosong."
                safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
                key = f"videos/{safe}"
                mime_type = mimetypes.guess_type(filename)[0] or "video/mp4"
                self.s3.put_object(
                    Bucket=self.bucket, Key=key,
                    Body=bytes(file_bytes), ContentType=mime_type
                )
                return key
            except Exception as e:
                return f"ERROR: {type(e).__name__}: {e}"

        def video_link(self, key, expires=3600):
            try:
                return self.s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=expires
                )
            except Exception:
                return ""

        def delete_video_s3(self, key):
            try:
                self.s3.delete_object(Bucket=self.bucket, Key=key)
                return "OK"
            except Exception as e:
                return f"ERROR: {e}"

        # ===== SESSION (persist sampai 00:00) =====
        def _end_of_day_iso(self):
            now = datetime.now()
            eod = now.replace(hour=23, minute=59, second=59, microsecond=0)
            return eod.isoformat()

        def _cleanup_expired_sessions(self):
            now_iso = datetime.now().isoformat()
            expired = [t for t, s in self.data["sessions"].items()
                       if s.get("expires", "") < now_iso]
            if expired:
                for t in expired:
                    del self.data["sessions"][t]
                self._save("sessions.json", self.data["sessions"])

        def create_session(self, uid):
            self._cleanup_expired_sessions()
            token = uuid.uuid4().hex
            self.data["sessions"][token] = {
                "uid": uid,
                "created": datetime.now().isoformat(),
                "expires": self._end_of_day_iso()
            }
            self._save("sessions.json", self.data["sessions"])
            return token

        def validate_session(self, token):
            if not token:
                return None
            sess = self.data["sessions"].get(token)
            if not sess:
                return None
            if datetime.now().isoformat() > sess.get("expires", ""):
                del self.data["sessions"][token]
                self._save("sessions.json", self.data["sessions"])
                return None
            return sess.get("uid")

        def delete_session(self, token):
            if token and token in self.data["sessions"]:
                del self.data["sessions"][token]
                self._save("sessions.json", self.data["sessions"])

    return S3Worker()

worker = get_worker()


# ==========================================
# 2. HELPERS
# ==========================================
def gen_uid():
    existing = {u["uid"] for u in worker.data["users"]}
    while True:
        uid = "".join(str(random.randint(0, 9)) for _ in range(16))
        if uid not in existing:
            return uid

def gen_password():
    return str(uuid.uuid4())[:8]

def count_items(text):
    if not text: return 0
    return len([i for i in re.split(r"[,\n\r;]+", text) if i.strip()])

def fmt_rp(n):
    try:
        return f"Rp {int(n):,}".replace(",", ".")
    except Exception:
        return f"Rp {n}"

def save_users():
    worker.execute_async(worker.save_file, "users.json", worker.data["users"])

def save_key(key):
    worker.execute_async(worker.save_file, key, worker.data[key.replace(".json", "")])


# ==========================================
# 3. AUTENTIKASI
# ==========================================
def login_page():
    st.markdown(
        "<div style='text-align: center; margin-bottom: 10px; "
        "filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.6));'>"
        "<img src='https://cdn.aceimg.com/mD4NlOxLG.png' width='100'></div>",
        unsafe_allow_html=True
    )
    st.markdown("<h2 style='text-align: center; color: #38BDF8;'>ElangPintar</h2>", unsafe_allow_html=True)
    st.caption("Login akan bertahan hingga akhir hari (00:00).")
    st.write("")
    with st.form("login_form"):
        uid = st.text_input("UID (16 Digit)")
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True, icon=":material/login:")
        if submit:
            u = next((x for x in worker.data["users"] if x["uid"] == uid), None)
            if u and u["pass_hash"] == worker.hash_pwd(pwd):
                if u["banned"]:
                    st.error("Akun Anda telah dibanned oleh Admin.")
                else:
                    st.session_state.user = u

                    # Buat session persisten (valid sampai 00:00)
                    token = worker.create_session(u["uid"])
                    st.session_state.session_token = token

                    # Set cookie di browser
                    if cookie_manager is not None:
                        try:
                            eod = datetime.now().replace(
                                hour=23, minute=59, second=59, microsecond=0
                            )
                            cookie_manager.set(
                                "elang_session_token",
                                token,
                                expires_at=eod,
                                key="set_cookie_login"
                            )
                        except Exception:
                            pass

                    st.rerun()
            else:
                st.error("UID atau Password salah.")


def try_restore_session():
    """Coba pulihkan user dari token cookie yang tersimpan di browser."""
    if cookie_manager is None:
        return False
    try:
        token = cookie_manager.get("elang_session_token")
    except Exception:
        return False
    if not token:
        return False
    uid = worker.validate_session(token)
    if not uid:
        return False
    u = next((x for x in worker.data["users"] if x["uid"] == uid), None)
    if not u or u.get("banned"):
        return False
    st.session_state.user = u
    st.session_state.session_token = token
    return True


# ==========================================
# 3b. SESSION FLOW (restore dari cookie)
# ==========================================
# Paksa rerun 1x agar cookie_manager sempat membaca cookie dari browser.
# Hanya terjadi pada load pertama di sesi browser baru.
if "cookie_loaded" not in st.session_state:
    st.session_state.cookie_loaded = True
    if cookie_manager is not None:
        try:
            cookie_manager.get_all()  # trigger read
        except Exception:
            pass
        st.rerun()

# Coba restore dari cookie kalau belum login
if "user" not in st.session_state:
    try_restore_session()

# Kalau masih belum login, tampilkan form login
if "user" not in st.session_state:
    login_page()
    st.stop()

# Refresh data user dari worker (data bisa berubah)
user = next((u for u in worker.data["users"] if u["uid"] == st.session_state.user["uid"]), st.session_state.user)
st.session_state.user = user

st.markdown(
    "<div style='text-align: center; margin-bottom: 20px; "
    "filter: drop-shadow(0 0 15px rgba(59, 130, 246, 0.6));'>"
    "<img src='https://cdn.aceimg.com/mD4NlOxLG.png' width='70'></div>",
    unsafe_allow_html=True
)


# ==========================================
# 4. ROUTING NAV BAWAH
# ==========================================
def nav_icon(name, label):
    url = f"https://api.iconify.design/ph/{name}.svg?color=%238A99AD"
    return f"![icon]({url})\n{label}"

if user["role"] == "admin":
    menu_options = ["Employee", "Payroll", "Analytic", "Report", "Akun"]
    page = st.radio(
        "Nav", menu_options, horizontal=True, label_visibility="collapsed",
        format_func=lambda x: {
            "Employee": nav_icon("users-three", "Karyawan"),
            "Payroll":  nav_icon("wallet", "Gaji"),
            "Analytic": nav_icon("chart-line-up", "Analitik"),
            "Report":   nav_icon("file-text", "Laporan"),
            "Akun":     nav_icon("user", "Akun")
        }[x]
    )
else:
    unread_count = sum(1 for n in user.get("notifications", []) if not n.get("read", False))
    data_label = f"Data ({unread_count})" if unread_count else "Data"
    menu_options = ["Data", "Pengajuan", "Upload", "Teks", "Akun"]
    page = st.radio(
        "Nav", menu_options, horizontal=True, label_visibility="collapsed",
        format_func=lambda x: {
            "Data":      nav_icon("database", data_label),
            "Pengajuan": nav_icon("file-plus", "NDP"),
            "Upload":    nav_icon("upload-simple", "Upload"),
            "Teks":      nav_icon("text-align-left", "Teks"),
            "Akun":      nav_icon("user", "Akun")
        }[x]
    )


# ==========================================
# 5. HALAMAN AKUN
# ==========================================
if page == "Akun":
    st.markdown(f"""
    <div class="profile-card">
        <div class="profile-avatar">{svg('user', 36, 'white')}</div>
        <div class="profile-info">
            <h3>{user['name']}</h3>
            <p>UID: {user['uid']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    my_payroll = worker.data["payroll"].get(user["name"], 0)
    pending_wd = sum(
        r["amount"] for r in worker.data["reports"]["wd"]
        if r["user"] == user["name"] and r.get("status", "pending") == "pending"
    )
    available = max(my_payroll - pending_wd, 0)

    st.markdown(f"""
    <div class="wallet-card">
        <div class="wallet-header">{svg('package', 18)}<span>Dompet Elang</span></div>
        <div class="wallet-balance">{fmt_rp(my_payroll)}</div>
        <div class="wallet-footer">
            <span>Tersedia: <b>{fmt_rp(available)}</b></span>
            <span class="wallet-badge">Aktif</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Withdraw", use_container_width=True, type="primary", icon=":material/account_balance_wallet:"):
        st.session_state.show_withdraw = not st.session_state.get("show_withdraw", False)

    tg_raw = user.get("telegram", "").strip().lstrip("@")
    tg_display = f"@{tg_raw}" if tg_raw else "Belum diatur"
    tg_color = "#22C55E" if tg_raw else "#F59E0B"

    st.markdown(f"""
    <div class="list-item">
        <div class="list-item-left">{svg('bell', 20)}<span>Notifikasi</span></div>
        <span style="color: #64748B;">&gt;</span>
    </div>
    <div class="list-item">
        <div class="list-item-left">{svg('link', 20, '#3B82F6')}<span>Telegram</span></div>
        <span style="color: {tg_color};">{tg_display} &gt;</span>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    with st.expander("Pengaturan Akun", expanded=False):
        with st.form("settings_form"):
            st.write("**Ubah Username & Telegram**")
            new_name = st.text_input("Username Akun", value=user.get("name", ""), max_chars=50)
            new_telegram = st.text_input(
                "Username Telegram",
                value=user.get("telegram", "").lstrip("@"),
                placeholder="username_tanpa_@"
            )
            if st.form_submit_button("Simpan Perubahan", use_container_width=True, icon=":material/save:"):
                new_name_clean = new_name.strip()
                new_tg_clean = new_telegram.strip().lstrip("@")

                if not new_name_clean:
                    st.error("Username tidak boleh kosong.")
                elif any(u["name"] == new_name_clean and u["uid"] != user["uid"] for u in worker.data["users"]):
                    st.error("Username sudah dipakai user lain.")
                else:
                    old_name = user["name"]
                    user["name"] = new_name_clean
                    user["telegram"] = new_tg_clean

                    if old_name != new_name_clean:
                        for d in worker.data["databases"]:
                            if d["name"] == old_name: d["name"] = new_name_clean
                        if old_name in worker.data["payroll"]:
                            worker.data["payroll"][new_name_clean] = worker.data["payroll"].pop(old_name)
                        for k in ["ndp", "wd", "video"]:
                            for r in worker.data["reports"][k]:
                                if r["user"] == old_name: r["user"] = new_name_clean
                        save_key("databases.json")
                        save_key("payroll.json")
                        save_key("reports.json")

                    save_users()
                    st.toast("Profil berhasil diperbarui!")
                    st.rerun()

    if st.button("Keluar / Logout", use_container_width=True, icon=":material/logout:"):
        # Hapus session di server
        token = st.session_state.get("session_token")
        worker.delete_session(token)

        # Hapus cookie di browser
        if cookie_manager is not None:
            try:
                cookie_manager.delete("elang_session_token", key="del_cookie_logout")
            except Exception:
                pass

        st.session_state.pop("user", None)
        st.session_state.pop("session_token", None)
        st.rerun()

    if st.session_state.get("show_withdraw", False):
        st.divider()
        st.subheader("Pengaturan Rekening & Withdraw")
        accounts = user.get("accounts", [])
        if not accounts:
            st.warning("Anda belum memiliki rekening. Tambahkan dulu di bawah.")
        else:
            st.write("**Rekening Terdaftar:**")
            for i, a in enumerate(accounts):
                c1, c2 = st.columns([4, 1])
                c1.write(f"{i+1}. **{a['bank']}** — `{a['number']}` a.n. {a['name']}")
                if c2.button("Hapus", key=f"delacc_{i}", icon=":material/delete:"):
                    accounts.pop(i)
                    user["accounts"] = accounts
                    save_users()
                    st.rerun()

            st.info(f"Saldo Tersedia: **{fmt_rp(available)}** (Pending: {fmt_rp(pending_wd)})")

            labels = [f"{a['bank']} - {a['number']}" for a in accounts]
            sel = st.selectbox("Pilih Rekening Tujuan", range(len(accounts)), format_func=lambda i: labels[i])

            if st.button("Ajukan Withdraw", type="primary", use_container_width=True):
                if available <= 0:
                    st.error("Tidak ada saldo yang bisa ditarik.")
                else:
                    worker.data["reports"]["wd"].append({
                        "user": user["name"], "amount": available,
                        "account": accounts[sel], "status": "pending",
                        "time": str(datetime.now())
                    })
                    save_key("reports.json")
                    st.success(f"Pengajuan withdraw {fmt_rp(available)} terkirim!")
                    st.session_state.show_withdraw = False
                    st.rerun()

        with st.expander("Tambah Rekening Baru"):
            with st.form("add_account_form"):
                bank = st.text_input("Jenis Bank / E-Wallet (BCA, Dana, dll)")
                number = st.text_input("Nomor Rekening")
                holder = st.text_input("Nama Pemilik Rekening")
                if st.form_submit_button("Simpan Rekening", icon=":material/save:"):
                    if bank and number and holder:
                        user.setdefault("accounts", []).append({"bank": bank, "number": number, "name": holder})
                        save_users()
                        st.success("Rekening ditambahkan!")
                        st.rerun()
                    else:
                        st.error("Semua field wajib diisi.")


# ==========================================
# 6. HALAMAN ADMIN
# ==========================================
elif user["role"] == "admin":
    if page == "Employee":
        st.header("Manajemen Karyawan")
        tab1, tab2, tab3, tab4 = st.tabs(["Buat Akun", "Kelola", "GiveDB", "SetText"])

        with tab1:
            name = st.text_input("Nama Karyawan Baru")
            if st.button("Generate Akun", icon=":material/person_add:"):
                if name:
                    new_uid = gen_uid()
                    new_pwd = gen_password()
                    worker.data["users"].append({
                        "uid": new_uid, "pass_hash": worker.hash_pwd(new_pwd),
                        "name": name, "role": "karyawan", "banned": False,
                        "accounts": [], "telegram": "", "notifications": []
                    })
                    save_users()
                    st.success("Akun berhasil dibuat!")
                    st.code(f"UID      : {new_uid}\nPassword : {new_pwd}")

        with tab2:
            st.caption("Kelola, ban, atau hapus akun karyawan.")
            for u in list(worker.data["users"]):
                if u["role"] == "karyawan":
                    status_txt = "BANNED" if u["banned"] else "AKTIF"
                    with st.expander(f"{u['name']} — {u['uid']} [{status_txt}]"):
                        st.write(f"Status: **{status_txt}** | Telegram: `@{u.get('telegram','-') or '-'}`")
                        c1, c2 = st.columns(2)
                        if c1.button("Unban" if u["banned"] else "Ban", key=f"ban_{u['uid']}", use_container_width=True):
                            u["banned"] = not u["banned"]
                            save_users()
                            st.rerun()
                        if c2.button("Hapus Akun", key=f"del_{u['uid']}", use_container_width=True, icon=":material/delete:"):
                            st.session_state.confirm_delete = u["uid"]

                        if st.session_state.get("confirm_delete") == u["uid"]:
                            st.error(f"Hapus permanen **{u['name']}** beserta semua datanya?")
                            cc1, cc2 = st.columns(2)
                            if cc1.button("Ya, Hapus", key=f"yes_{u['uid']}", type="primary", use_container_width=True):
                                worker.data["users"] = [x for x in worker.data["users"] if x["uid"] != u["uid"]]
                                worker.data["databases"] = [d for d in worker.data["databases"] if d["name"] != u["name"]]
                                if u["name"] in worker.data["payroll"]:
                                    del worker.data["payroll"][u["name"]]
                                for k in ["ndp", "wd", "video"]:
                                    worker.data["reports"][k] = [r for r in worker.data["reports"][k] if r["user"] != u["name"]]
                                save_users()
                                save_key("databases.json")
                                save_key("payroll.json")
                                save_key("reports.json")
                                st.session_state.confirm_delete = None
                                st.success(f"Akun {u['name']} dihapus.")
                                st.rerun()
                            if cc2.button("Batal", key=f"no_{u['uid']}", use_container_width=True):
                                st.session_state.confirm_delete = None
                                st.rerun()

        with tab3:
            karyawan_list = [u["name"] for u in worker.data["users"] if u["role"] == "karyawan"]
            if karyawan_list:
                st.info("Database dikirim secara privat — hanya karyawan terpilih yang bisa melihat.")
                target = st.selectbox("Pilih Karyawan", karyawan_list)
                db_input = st.text_area("Input Database (pisahkan dengan koma/enter)")
                if st.button("Kirim DB Privat", icon=":material/send:") and db_input:
                    nums = [n.strip() for n in re.split(r"[,\n\r;]+", db_input) if n.strip()]
                    worker.data["databases"] = [d for d in worker.data["databases"] if d["name"] != target]
                    worker.data["databases"].append({
                        "name": target,
                        "numbers": [{"num": n, "status": "Tidak Terdaftar"} for n in nums]
                    })
                    target_u = next((u for u in worker.data["users"] if u["name"] == target), None)
                    if target_u:
                        target_u.setdefault("notifications", []).append({
                            "type": "db",
                            "message": f"Anda menerima {len(nums)} database baru dari admin",
                            "read": False,
                            "time": str(datetime.now())
                        })
                        save_users()
                    save_key("databases.json")
                    st.success(f"{len(nums)} DB dikirim privat ke {target}.")
            else:
                st.info("Belum ada karyawan.")

        with tab4:
            text_in = st.text_area("Teks Kerja Harian", value=worker.data["texts"].get("content", ""))
            if st.button("Simpan Teks", icon=":material/save:"):
                worker.data["texts"] = {"content": text_in}
                save_key("texts.json")
                st.success("Teks disimpan!")

    elif page == "Payroll":
        st.header("Manajemen Payroll")
        employees = [u for u in worker.data["users"] if u["role"] == "karyawan"]
        if not employees:
            st.info("Belum ada karyawan.")
        else:
            for emp in employees:
                current = worker.data["payroll"].get(emp["name"], 0)
                st.markdown(f"**{emp['name']}** — Saldo: **{fmt_rp(current)}**")
                c1, c2, c3 = st.columns([2, 1, 1])
                amount = c1.number_input("Nominal", min_value=0, step=10000, key=f"amt_{emp['uid']}")
                if c2.button("Tambah", key=f"add_{emp['uid']}", icon=":material/add:"):
                    worker.data["payroll"][emp["name"]] = current + amount
                    save_key("payroll.json")
                    st.rerun()
                if c3.button("Reset", key=f"rst_{emp['uid']}", icon=":material/restart_alt:"):
                    worker.data["payroll"][emp["name"]] = 0
                    save_key("payroll.json")
                    st.rerun()
                st.divider()

    elif page == "Analytic":
        st.header("Analitik Kinerja")
        employees = [u["name"] for u in worker.data["users"] if u["role"] == "karyawan"]
        if not employees:
            st.info("Belum ada karyawan.")
        else:
            selected = st.selectbox("Pilih Karyawan", employees)

            ndp_approved = [r for r in worker.data["reports"]["ndp"]
                            if r["user"] == selected and r.get("status") == "approved"]
            total_ndp = sum(r.get("count", 0) for r in ndp_approved)

            my_db = next((d for d in worker.data["databases"] if d["name"] == selected), None)
            if my_db:
                total_db = len(my_db["numbers"])
                done_db = sum(1 for n in my_db["numbers"] if n["status"] != "Tidak Terdaftar")
                dibalas_db = sum(1 for n in my_db["numbers"] if n["status"] == "Dibalas")
            else:
                total_db = done_db = dibalas_db = 0

            ndp_vid_approved = sum(
                1 for n in worker.data["reports"]["ndp"]
                if n["user"] == selected and n.get("status") == "approved" and n.get("video_key")
            )
            ndp_vid_pending = sum(
                1 for n in worker.data["reports"]["ndp"]
                if n["user"] == selected and n.get("status", "pending") == "pending" and n.get("video_key")
            )
            stand_vid_approved = sum(
                1 for v in worker.data["reports"]["video"]
                if v["user"] == selected and v.get("status") == "approved"
            )
            stand_vid_pending = sum(
                1 for v in worker.data["reports"]["video"]
                if v["user"] == selected and v.get("status", "pending") == "pending"
            )

            video_approved = ndp_vid_approved + stand_vid_approved
            video_pending  = ndp_vid_pending + stand_vid_pending
            vid_total = video_approved + video_pending

            db_pct = (dibalas_db / total_ndp * 100) if total_ndp > 0 else 0
            video_pct = (video_approved / vid_total * 100) if vid_total > 0 else 0
            kinerja = (db_pct + video_pct) / 2

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("NDP", total_ndp)
            c2.metric("DB", f"{done_db}/{total_db}")
            c3.metric("Video", f"{video_approved}/{vid_total}")
            c4.metric("Kinerja", f"{kinerja:.1f}%")

            st.progress(min(kinerja / 100, 1.0))

            if my_db:
                st.write("**Rincian Status DB:**")
                counts = {}
                for n in my_db["numbers"]:
                    counts[n["status"]] = counts.get(n["status"], 0) + 1
                for s, c in counts.items():
                    st.write(f"- {s}: {c}")

    elif page == "Report":
        st.header("Laporan & Approval")
        tab_ndp, tab_wd, tab_video = st.tabs(["Cek NDP+Video", "Withdraw", "Video Standalone"])

        # ===== TAB NDP + VIDEO =====
        with tab_ndp:
            ndps = worker.data["reports"]["ndp"]
            pending = [(i, n) for i, n in enumerate(ndps) if n.get("status", "pending") == "pending"]
            history = [(i, n) for i, n in enumerate(ndps) if n.get("status", "pending") != "pending"]

            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("Total", len(ndps))
            sc2.metric("Pending", len(pending))
            sc3.metric("Selesai", len(history))

            st.divider()

            if not pending:
                st.success("Tidak ada pengajuan NDP yang menunggu review.")

            for i, n in pending:
                vkey = n.get("video_key")
                v_cap = n.get("video_caption", "-")
                v_size = n.get("video_size_mb", "-")
                has_vid = f" · Video: {v_cap}" if vkey else " · TANPA VIDEO"

                with st.expander(f"{n['user']} — {n.get('count', 0)} item{has_vid}"):
                    st.write("**Data NDP:**")
                    st.code(n["data"] or "(kosong)", language="text")

                    st.write("**Video Bukti:**")
                    if vkey:
                        url = worker.video_link(vkey)
                        if url:
                            try:
                                st.video(url)
                            except Exception:
                                st.warning("Video tidak bisa diputar langsung.")
                            st.markdown(
                                f"<a href='{url}' target='_blank' "
                                f"style='display:inline-block;padding:8px 18px;"
                                f"background:linear-gradient(135deg,#1E40AF,#3B82F6);"
                                f"color:white;border-radius:10px;text-decoration:none;"
                                f"font-weight:600;margin:6px 0;'>"
                                f"{svg('download', 14, 'white')} Download / Buka Video</a>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.warning("URL video tidak tersedia.")
                        st.caption(f"Caption: **{v_cap}** · {v_size} MB · Key: `{vkey}`")
                    else:
                        st.warning("Pengajuan ini TIDAK ada video (data lama / bug).")

                    st.caption(f"Waktu: {n.get('time', '-')}")

                    st.write("")
                    c1, c2, c3 = st.columns(3)
                    if c1.button("Approve", key=f"a_n_{i}", use_container_width=True,
                                 icon=":material/check_circle:"):
                        ndps[i]["status"] = "approved"
                        save_key("reports.json")
                        st.toast(f"NDP {n['user']} disetujui")
                        st.rerun()
                    if c2.button("Reject", key=f"r_n_{i}", use_container_width=True,
                                 icon=":material/cancel:"):
                        ndps[i]["status"] = "rejected"
                        save_key("reports.json")
                        st.toast(f"NDP {n['user']} ditolak")
                        st.rerun()
                    if c3.button("Hapus", key=f"del_n_{i}", use_container_width=True,
                                 icon=":material/delete:"):
                        st.session_state[f"cd_ndp_{i}"] = True

                    if st.session_state.get(f"cd_ndp_{i}", False):
                        st.error("Hapus permanen pengajuan NDP ini beserta video?")
                        y1, y2 = st.columns(2)
                        if y1.button("Ya, Hapus", key=f"y_ndp_{i}", type="primary", use_container_width=True):
                            if vkey:
                                worker.execute(worker.delete_video_s3, vkey)
                            ndps.pop(i)
                            save_key("reports.json")
                            st.session_state[f"cd_ndp_{i}"] = False
                            st.success("NDP + video dihapus.")
                            st.rerun()
                        if y2.button("Batal", key=f"n_ndp_{i}", use_container_width=True):
                            st.session_state[f"cd_ndp_{i}"] = False
                            st.rerun()

            st.subheader("History")
            if not history:
                st.info("Belum ada riwayat.")
            for i, n in history:
                badge = "APPROVED" if n["status"] == "approved" else "REJECTED"
                vmark = " · [VIDEO]" if n.get("video_key") else " · [NO-VIDEO]"
                with st.expander(f"[{badge}] {n['user']} — {n.get('count', 0)} item{vmark}"):
                    st.write("**Data NDP:**")
                    st.code(n["data"] or "(kosong)", language="text")
                    vkey = n.get("video_key")
                    if vkey:
                        url = worker.video_link(vkey)
                        if url:
                            try:
                                st.video(url)
                            except Exception:
                                st.warning("Video tidak bisa diputar.")
                            st.markdown(
                                f"<a href='{url}' target='_blank' "
                                f"style='display:inline-block;padding:6px 14px;"
                                f"background:#1E40AF;color:white;border-radius:8px;"
                                f"text-decoration:none;font-size:12px;'>"
                                f"{svg('download', 12, 'white')} Buka Video</a>",
                                unsafe_allow_html=True
                            )
                    st.caption(f"Waktu: {n.get('time', '-')}")

        # ===== TAB WITHDRAW =====
        with tab_wd:
            wds = worker.data["reports"]["wd"]
            pending_wd = [(i, n) for i, n in enumerate(wds) if n.get("status", "pending") == "pending"]
            st.subheader(f"Pending ({len(pending_wd)})")
            for i, n in pending_wd:
                acc = n.get("account", {})
                with st.expander(f"{n['user']} — {fmt_rp(n['amount'])}"):
                    st.write(f"{acc.get('bank','-')} — {acc.get('number','-')} a.n. {acc.get('name','-')}")
                    c1, c2 = st.columns(2)
                    if c1.button("Approve", key=f"a_w_{i}", icon=":material/check_circle:"):
                        wds[i]["status"] = "approved"
                        worker.data["payroll"][n["user"]] = max(
                            worker.data["payroll"].get(n["user"], 0) - n["amount"], 0
                        )
                        save_key("payroll.json")
                        save_key("reports.json")
                        st.rerun()
                    if c2.button("Reject", key=f"r_w_{i}", icon=":material/cancel:"):
                        wds[i]["status"] = "rejected"
                        save_key("reports.json")
                        st.rerun()

        # ===== TAB VIDEO STANDALONE =====
        with tab_video:
            vids = worker.data["reports"]["video"]
            if not vids:
                st.info("Belum ada video standalone.")
            else:
                now = datetime.now()
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

                def _parse_t(s):
                    try:
                        return datetime.fromisoformat(s)
                    except Exception:
                        return datetime.min

                pending_items   = [(i, v) for i, v in enumerate(vids)
                                   if v.get("status", "pending") == "pending"]
                hari_ini_items  = [(i, v) for i, v in enumerate(vids)
                                   if _parse_t(v.get("time", "")) >= today_start
                                   and v.get("status", "pending") != "pending"]
                lalu_items      = [(i, v) for i, v in enumerate(vids)
                                   if _parse_t(v.get("time", "")) < today_start]

                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("Total", len(vids))
                sc2.metric("Pending", len(pending_items))
                sc3.metric("Hari ini", len(hari_ini_items))
                sc4.metric("Lalu", len(lalu_items))

                st.divider()

                def render_video(idx, v):
                    status = v.get("status", "pending")
                    badge_map = {"pending": "[PENDING]", "approved": "[APPROVED]", "rejected": "[REJECTED]"}
                    badge = badge_map.get(status, "[?]")
                    label = f"{badge} {v['user']} · {v.get('caption','-')}"

                    with st.expander(label):
                        st.markdown(
                            f"{svg('clock', 14)} {v.get('time','-')} &nbsp; "
                            f"{svg('package', 14)} {v.get('size_mb','-')} MB",
                            unsafe_allow_html=True
                        )
                        url = worker.video_link(v["key"]) if v.get("key") else v.get("url", "")
                        if url:
                            try:
                                st.video(url)
                            except Exception:
                                st.warning("Video tidak bisa diputar langsung.")
                            st.markdown(
                                f"<a href='{url}' target='_blank' "
                                f"style='display:inline-block;padding:8px 18px;"
                                f"background:linear-gradient(135deg,#1E40AF,#3B82F6);"
                                f"color:white;border-radius:10px;text-decoration:none;"
                                f"font-weight:600;margin:6px 0;'>"
                                f"{svg('download', 14, 'white')} Download / Buka</a>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.warning("URL video tidak tersedia.")

                        c1, c2, c3 = st.columns(3)
                        if c1.button("Approve", key=f"av_{idx}",
                                     disabled=(status == "approved"),
                                     use_container_width=True, icon=":material/check_circle:"):
                            vids[idx]["status"] = "approved"
                            save_key("reports.json")
                            st.rerun()
                        if c2.button("Reject", key=f"rv_{idx}",
                                     disabled=(status == "rejected"),
                                     use_container_width=True, icon=":material/cancel:"):
                            vids[idx]["status"] = "rejected"
                            save_key("reports.json")
                            st.rerun()
                        if c3.button("Hapus", key=f"dv_{idx}",
                                     use_container_width=True, icon=":material/delete:"):
                            st.session_state[f"cd_{idx}"] = True

                        if st.session_state.get(f"cd_{idx}", False):
                            st.error(f"Hapus permanen video **{v.get('caption','-')}**?")
                            y1, y2 = st.columns(2)
                            if y1.button("Ya, Hapus", key=f"y_{idx}", type="primary", use_container_width=True):
                                if v.get("key"):
                                    worker.execute(worker.delete_video_s3, v["key"])
                                vids.pop(idx)
                                save_key("reports.json")
                                st.session_state[f"cd_{idx}"] = False
                                st.success("Video dihapus.")
                                st.rerun()
                            if y2.button("Batal", key=f"n_{idx}", use_container_width=True):
                                st.session_state[f"cd_{idx}"] = False
                                st.rerun()

                s1, s2, s3 = st.tabs([
                    f"Terbaru ({len(pending_items)})",
                    f"Hari ini ({len(hari_ini_items)})",
                    f"Lalu ({len(lalu_items)})"
                ])
                with s1:
                    if not pending_items: st.success("Tidak ada video pending.")
                    for idx, v in pending_items: render_video(idx, v)
                with s2:
                    if not hari_ini_items: st.info("Belum ada video diproses hari ini.")
                    for idx, v in hari_ini_items: render_video(idx, v)
                with s3:
                    if not lalu_items: st.info("Tidak ada video lama.")
                    for idx, v in lalu_items: render_video(idx, v)


# ==========================================
# 7. HALAMAN KARYAWAN
# ==========================================
else:
    if page == "Data":
        st.header("Database Kerja Saya")
        st.caption("Data ini privat — hanya Anda yang bisa melihat.")

        unread = [n for n in user.get("notifications", []) if not n.get("read", False)]
        if unread:
            with st.container(border=True):
                st.markdown(
                    f"{svg('bell', 16)} <b>{len(unread)} notifikasi baru dari admin</b>",
                    unsafe_allow_html=True
                )
                for n in unread:
                    st.write(f"- {n['message']}")
                if st.button("Tandai Dibaca", use_container_width=True, icon=":material/done_all:"):
                    for n in user.get("notifications", []):
                        n["read"] = True
                    save_users()
                    st.rerun()

        my_db = next((d for d in worker.data["databases"] if d["name"] == user["name"]), None)
        if my_db:
            statuses = ["Tidak Terdaftar", "Terdaftar", "Dibaca", "Dibalas"]
            for i, item in enumerate(my_db["numbers"], 1):
                c1, c2, c3 = st.columns([1, 4, 3])
                with c1: st.markdown(f"**{i}.**")
                with c2: st.code(item["num"], language="text")
                with c3:
                    curr = statuses.index(item["status"]) if item["status"] in statuses else 0
                    new_st = st.selectbox("Status", statuses, index=curr,
                                          key=f"st_{i}", label_visibility="collapsed")
                    if new_st != item["status"]:
                        item["status"] = new_st
                        save_key("databases.json")
                        st.rerun()
        else:
            st.warning("Belum ada database. Admin akan mengirim via private.")

    elif page == "Pengajuan":
        st.header("Pengajuan NDP")
        st.caption("Setiap pengajuan NDP **wajib disertai video bukti**.")

        with st.container(border=True):
            st.subheader("1. Data NDP")
            ndp_input = st.text_area(
                "Masukkan Database NDP",
                key="ndp_input_text",
                height=150
            )
            preview = count_items(ndp_input)
            st.caption(f"Terdeteksi **{preview}** item")

        with st.container(border=True):
            st.subheader("2. Video Bukti *")
            vid = st.file_uploader(
                "Pilih Video (MP4/MOV)",
                type=["mp4", "mov"],
                key="ndp_video_file"
            )
            size_mb = 0
            if vid is not None:
                size_mb = round(len(vid.getvalue()) / (1024 * 1024), 2)
                st.caption(f"Ukuran: **{size_mb} MB** / 200 MB")
                if size_mb > 200:
                    st.error("File terlalu besar. Maksimal 200 MB.")
                    vid = None

            caption = st.text_input(
                "Caption Video (1-10/11-20/dst)",
                max_chars=10,
                key="ndp_video_caption"
            )

        st.write("")
        if st.button("Ajukan NDP + Video", use_container_width=True, type="primary",
                     icon=":material/send:"):
            errors = []
            if not ndp_input.strip():
                errors.append("Data NDP wajib diisi.")
            if vid is None:
                errors.append("Video bukti wajib diupload.")
            if not caption or not (1 <= len(caption) <= 10):
                errors.append("Video harus memiliki Caption")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    with st.spinner(f"Mengupload video ({size_mb} MB)"):
                        key = worker.execute(
                            worker.upload_video_s3,
                            vid.getvalue(),
                            f"{user['uid']}_{int(datetime.now().timestamp())}_{vid.name}"
                        )
                        if isinstance(key, Exception) or not str(key).startswith("videos/"):
                            raise Exception(str(key))

                        worker.data["reports"]["ndp"].append({
                            "user": user["name"],
                            "data": ndp_input,
                            "count": preview,
                            "video_key": key,
                            "video_caption": caption,
                            "video_size_mb": size_mb,
                            "status": "pending",
                            "time": str(datetime.now())
                        })
                        save_key("reports.json")
                    st.success("Pengajuan NDP dan Video berhasil dikirim!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal upload: {e}")

        st.divider()
        st.subheader("Riwayat Pengajuan Saya")
        my_ndps = [(i, n) for i, n in enumerate(worker.data["reports"]["ndp"])
                   if n["user"] == user["name"]]
        if not my_ndps:
            st.info("Belum ada pengajuan.")
        else:
            for i, n in reversed(my_ndps):
                stt = n.get("status", "pending")
                icon_map = {"pending": "PENDING", "approved": "APPROVED", "rejected": "REJECTED"}
                mark = "VIDEO" if n.get("video_key") else "NO-VIDEO"
                with st.expander(f"[{icon_map.get(stt, stt.upper())}] {n.get('count', 0)} item · {mark}"):
                    st.code(n["data"] or "(kosong)", language="text")
                    if n.get("video_key"):
                        url = worker.video_link(n["video_key"])
                        if url:
                            try:
                                st.video(url)
                            except Exception:
                                st.warning("Video tidak bisa diputar.")
                        st.caption(f"Caption: **{n.get('video_caption','-')}** · {n.get('video_size_mb','-')} MB")
                    st.caption(f"Waktu: {n.get('time', '-')}")

    elif page == "Upload":
        st.header("Upload Video")
        st.caption("Gunakan menu ini untuk upload video di luar pengajuan NDP.")

        vid = st.file_uploader("Pilih Video (MP4/MOV)", type=["mp4", "mov"], key="up_vid")
        size_mb = 0
        if vid is not None:
            size_mb = round(len(vid.getvalue()) / (1024 * 1024), 2)
            st.caption(f"Ukuran: **{size_mb} MB** / 200 MB")
            if size_mb > 200:
                st.error("File terlalu besar. Maksimal 200 MB.")
                vid = None

        caption = st.text_input("Caption", max_chars=10, key="up_cap")

        if st.button("Upload", use_container_width=True, icon=":material/upload:"):
            if vid is None:
                st.error("Pilih video dulu!")
            elif not caption or not (1 <= len(caption) <= 10):
                st.error("Contoh caption: 1-10")
            else:
                try:
                    with st.spinner(f"Mengupload {size_mb} MB..."):
                        key = worker.execute(
                            worker.upload_video_s3,
                            vid.getvalue(),
                            f"{user['uid']}_{int(datetime.now().timestamp())}_{vid.name}"
                        )
                        if isinstance(key, Exception) or not str(key).startswith("videos/"):
                            raise Exception(str(key))

                        worker.data["reports"]["video"].append({
                            "user": user["name"],
                            "key": key,
                            "caption": caption,
                            "size_mb": size_mb,
                            "status": "pending",
                            "time": str(datetime.now())
                        })
                        save_key("reports.json")
                    st.success("Video berhasil diupload!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Upload gagal: {e}")

    elif page == "Teks":
        st.header("Teks Kerja")
        text_content = worker.data["texts"].get("content", "Belum ada teks.")
        st.code(text_content)
        st.button("Copy Teks", icon=":material/content_copy:",
                  on_click=lambda: st.toast("Teks disalin!"))
