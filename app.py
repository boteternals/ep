import streamlit as st
import streamlit.components.v1 as components
import boto3
import json
import hashlib
import uuid
import queue
import threading
import random
import re
import mimetypes
import copy
import html
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
    WIB = ZoneInfo("Asia/Jakarta")
except Exception:
    WIB = timezone(timedelta(hours=7))

def now_wib_aware():
    return datetime.now(WIB)

def now_wib():
    return now_wib_aware().replace(tzinfo=None)

def today_wib_str():
    return now_wib().date().isoformat()

from botocore.exceptions import ClientError
from botocore.client import Config

# === COOKIE LIB (fallback aman kalau belum install) ===
try:
    import extra_streamlit_components as stx
    _HAS_COOKIES = True
except ImportError:
    _HAS_COOKIES = False


# ==========================================
# 0. PAGE CONFIG & CSS (TEMA BIRU ELANG)
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
    header, header[data-testid="stHeader"] {
        visibility: hidden; height: 0 !important; min-height: 0 !important;
    }
    .block-container { padding-bottom: 120px !important; padding-top: 1.2rem !important; }
    h1, h2, h3, h4, h5, h6 { color: #E0F2FE !important; }
    .stMarkdown p, label { color: #CBD5E1; }

    /* =====================================================
       NAV BAWAH — hanya berlaku untuk st.container(key="nav_bottom")
       ===================================================== */
    .st-key-nav_bottom div[data-testid="stRadio"] {
        position: fixed; bottom: 0; left: 0; right: 0;
        background: linear-gradient(180deg, #0B132B 0%, #020617 100%);
        padding: 10px 5px 14px 5px; z-index: 9999;
        border-top: 1px solid #1E3A8A;
        box-shadow: 0 -8px 25px rgba(30, 64, 175, 0.35);
    }
    .st-key-nav_bottom div[data-testid="stRadio"] > div {
        display: flex; flex-direction: row !important;
        justify-content: space-around; width: 100%; gap: 4px;
    }
    .st-key-nav_bottom div[data-testid="stRadio"] label {
        flex: 1; text-align: center; margin: 0 !important;
        padding: 8px 4px 6px 4px !important; cursor: pointer;
        display: flex; flex-direction: column; align-items: center;
        position: relative; border-radius: 12px;
        transition: background 0.25s ease, transform 0.2s ease;
    }
    .st-key-nav_bottom div[data-testid="stRadio"] label:hover {
        background: rgba(56, 189, 248, 0.08); transform: translateY(-1px);
    }
    .st-key-nav_bottom div[data-testid="stRadio"] label::before {
        content: ''; position: absolute; top: -1px; left: 50%;
        transform: translateX(-50%); width: 0; height: 3px;
        background: linear-gradient(90deg, #3B82F6, #38BDF8);
        border-radius: 3px;
        transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 0 10px #38BDF8;
    }
    .st-key-nav_bottom div[data-testid="stRadio"] label:has(input:checked)::before { width: 45%; }

    /* Sembunyikan lingkaran radio bawaan Streamlit (versi lama & terbaru) */
    .st-key-nav_bottom div[data-testid="stRadio"] label > div:first-child,
    .st-key-nav_bottom div[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child,
    .st-key-nav_bottom div[data-testid="stRadio"] input[type="radio"] {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    .st-key-nav_bottom div[data-testid="stRadio"] label p {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 4px;
        font-size: 10px !important; color: #64748B !important;
        margin: 0 !important; font-weight: 600 !important;
        transition: color 0.25s ease; line-height: 1.2;
    }
    .st-key-nav_bottom div[data-testid="stRadio"] label img {
        width: 24px; height: 24px; margin: 0 !important;
        opacity: 0.6; transition: all 0.25s ease;
    }
    .st-key-nav_bottom div[data-testid="stRadio"] label:has(input:checked) p { color: #38BDF8 !important; }
    .st-key-nav_bottom div[data-testid="stRadio"] label:has(input:checked) img {
        opacity: 1;
        filter: invert(63%) sepia(54%) saturate(3282%) hue-rotate(177deg) brightness(99%) contrast(95%);
        transform: scale(1.12);
    }
    .st-key-nav_bottom div[data-testid="stRadio"] > label { display: none !important; }

    /* =====================================================
       UMUM
       ===================================================== */
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
        display: flex; align-items: center; margin-bottom: 16px;
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

            try:
                s3_cfg = Config(
                    s3={"addressing_style": "path"},
                    signature_version="s3v4",
                    request_checksum_calculation="when_required",
                    response_checksum_validation="when_required",
                )
            except TypeError:
                s3_cfg = Config(s3={"addressing_style": "path"}, signature_version="s3v4")

            self.s3 = boto3.client(
                "s3", endpoint_url=endpoint_url,
                aws_access_key_id=st.secrets["S3_ACCESS_KEY_ID"],
                aws_secret_access_key=st.secrets["S3_SECRET_ACCESS_KEY"],
                config=s3_cfg
            )
            self.bucket = bucket_name
            self.q = queue.Queue()
            self.lock = threading.Lock()

            texts_raw = self._load("texts.json", [])
            if isinstance(texts_raw, dict) and "content" in texts_raw:
                old_content = texts_raw.get("content", "")
                if old_content:
                    texts_raw = [{"id": uuid.uuid4().hex, "title": "Teks Kerja Utama", "content": old_content, "image_key": None}]
                else:
                    texts_raw = []
                self._save("texts.json", texts_raw)

            meta_raw = self._load("meta.json", {"last_reset_date": today_wib_str()})
            if not isinstance(meta_raw, dict):
                meta_raw = {"last_reset_date": today_wib_str()}

            self.data = {
                "users": self._load("users.json", []),
                "databases": self._load("databases.json", []),
                "texts": texts_raw,
                "payroll": self._load("payroll.json", {}),
                "reports": self._load("reports.json", {"ndp": [], "wd": [], "video": []}),
                "sessions": self._load("sessions.json", {}),
                "db_stats": self._load("db_stats.json", {}),
                "popups": self._load("popups.json", []),
                "meta": meta_raw,
            }

            # --- MIGRASI: pastikan setiap item DB punya 'name' & 'id' unik ---
            _needs_mig = False
            for d in self.data["databases"]:
                for n in d.get("numbers", []):
                    if "name" not in n:
                        n["name"] = ""
                        _needs_mig = True
                    if "id" not in n:
                        n["id"] = uuid.uuid4().hex
                        _needs_mig = True
            if _needs_mig:
                self._save("databases.json", self.data["databases"])

            self.last_reset_date = self.data["meta"].get("last_reset_date") or today_wib_str()

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

            self.ensure_daily_reset()
            self.cleanup_expired_popups()
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

        def ensure_daily_reset(self):
            # Catatan: texts.json dan popups.json TIDAK ikut terhapus harian
            today_str = today_wib_str()
            if self.last_reset_date == today_str:
                return False
            with self.lock:
                today_str = today_wib_str()
                if self.last_reset_date == today_str:
                    return False
                self.data["databases"] = []
                self.data["sessions"] = {}
                self.data["db_stats"] = {}
                self.data["meta"] = {"last_reset_date": today_str}
                self._save("databases.json", [])
                self._save("sessions.json", {})
                self._save("db_stats.json", {})
                self._save("meta.json", self.data["meta"])
                self.last_reset_date = today_str
                return True

        def cleanup_expired_popups(self):
            now_iso = now_wib().isoformat()
            with self.lock:
                popups = self.data.get("popups", [])
                active = []
                expired = []
                for p in popups:
                    exp = p.get("expires_at", "")
                    if exp and now_iso > exp:
                        expired.append(p)
                    else:
                        active.append(p)
                if expired:
                    for p in expired:
                        ikey = p.get("image_key")
                        if ikey:
                            try:
                                self.s3.delete_object(Bucket=self.bucket, Key=ikey)
                            except Exception:
                                pass
                    self.data["popups"] = active
                    self._save("popups.json", active)

        def _process_queue(self):
            while True:
                task = self.q.get()
                if task is None: break
                func, args, kwargs, result_queue = task
                try:
                    self.ensure_daily_reset()
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
            with self.lock:
                self.data[key.replace(".json", "")] = data
                self._save(key, data)
            return True

        def upload_file_s3(self, file_bytes, filename):
            self.s3.put_object(Bucket=self.bucket, Key=f"uploads/{filename}", Body=file_bytes)
            return True

        def upload_image_s3(self, file_obj_or_bytes, filename):
            try:
                if file_obj_or_bytes is None:
                    return "ERROR: File kosong."
                safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
                key = f"images/{uuid.uuid4().hex[:8]}_{safe}"
                mime_type = mimetypes.guess_type(filename)[0] or "image/png"
                if hasattr(file_obj_or_bytes, "read"):
                    file_obj_or_bytes.seek(0)
                    self.s3.upload_fileobj(
                        file_obj_or_bytes, self.bucket, key,
                        ExtraArgs={"ContentType": mime_type}
                    )
                else:
                    if not file_obj_or_bytes:
                        return "ERROR: File kosong."
                    self.s3.put_object(
                        Bucket=self.bucket, Key=key,
                        Body=file_obj_or_bytes, ContentType=mime_type
                    )
                return key
            except Exception as e:
                return f"ERROR: {type(e).__name__}: {e}"

        def upload_video_s3(self, file_obj_or_bytes, filename):
            try:
                if file_obj_or_bytes is None:
                    return "ERROR: File kosong."
                safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
                key = f"videos/{safe}"
                mime_type = mimetypes.guess_type(filename)[0] or "video/mp4"
                if hasattr(file_obj_or_bytes, "read"):
                    file_obj_or_bytes.seek(0)
                    self.s3.upload_fileobj(
                        file_obj_or_bytes, self.bucket, key,
                        ExtraArgs={"ContentType": mime_type}
                    )
                else:
                    if not file_obj_or_bytes:
                        return "ERROR: File kosong."
                    self.s3.put_object(
                        Bucket=self.bucket, Key=key,
                        Body=file_obj_or_bytes, ContentType=mime_type
                    )
                return key
            except Exception as e:
                return f"ERROR: {type(e).__name__}: {e}"

        def media_link(self, key, expires=3600):
            if not key:
                return ""
            try:
                return self.s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=expires
                )
            except Exception:
                return ""

        def video_link(self, key, expires=3600):
            return self.media_link(key, expires=expires)

        def delete_media_s3(self, key):
            if not key:
                return "OK"
            try:
                self.s3.delete_object(Bucket=self.bucket, Key=key)
                return "OK"
            except Exception as e:
                return f"ERROR: {e}"

        def delete_video_s3(self, key):
            return self.delete_media_s3(key)

        def _end_of_day_iso(self):
            now = now_wib()
            eod = now.replace(hour=23, minute=59, second=59, microsecond=0)
            return eod.isoformat()

        def _cleanup_expired_sessions(self):
            with self.lock:
                now_iso = now_wib().isoformat()
                expired = [t for t, s in self.data["sessions"].items()
                           if s.get("expires", "") < now_iso]
                if expired:
                    for t in expired:
                        del self.data["sessions"][t]
                    self._save("sessions.json", self.data["sessions"])

        def create_session(self, uid):
            self._cleanup_expired_sessions()
            with self.lock:
                token = uuid.uuid4().hex
                self.data["sessions"][token] = {
                    "uid": uid,
                    "created": now_wib().isoformat(),
                    "expires": self._end_of_day_iso()
                }
                self._save("sessions.json", self.data["sessions"])
                return token

        def validate_session(self, token):
            if not token:
                return None
            with self.lock:
                sess = self.data["sessions"].get(token)
                if not sess:
                    return None
                if now_wib().isoformat() > sess.get("expires", ""):
                    del self.data["sessions"][token]
                    self._save("sessions.json", self.data["sessions"])
                    return None
                return sess.get("uid")

        def delete_session(self, token):
            if not token:
                return
            with self.lock:
                if token in self.data["sessions"]:
                    del self.data["sessions"][token]
                    self._save("sessions.json", self.data["sessions"])

    return S3Worker()

worker = get_worker()
worker.ensure_daily_reset()
worker.cleanup_expired_popups()


# ==========================================
# 2. HELPERS
# ==========================================
DB_STATUSES = ["Belum Dicek", "Tidak Terdaftar", "Terdaftar", "Dibaca", "Dibalas"]

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

def fmt_remaining(expires_iso):
    try:
        exp = datetime.fromisoformat(expires_iso)
        diff = exp - now_wib()
        secs = int(diff.total_seconds())
        if secs <= 0:
            return "Kedaluwarsa"
        days, rem = divmod(secs, 86400)
        hours, rem = divmod(rem, 3600)
        mins, _ = divmod(rem, 60)
        parts = []
        if days: parts.append(f"{days}h")
        if hours: parts.append(f"{hours}j")
        if mins or not parts: parts.append(f"{mins}m")
        return " ".join(parts)
    except Exception:
        return "-"

def save_users():
    worker.execute_async(worker.save_file, "users.json", copy.deepcopy(worker.data["users"]))

def save_users_sync():
    worker.execute(worker.save_file, "users.json", copy.deepcopy(worker.data["users"]))

def save_key(key):
    worker.execute_async(worker.save_file, key, copy.deepcopy(worker.data[key.replace(".json", "")]))

def save_key_sync(key):
    worker.execute(worker.save_file, key, copy.deepcopy(worker.data[key.replace(".json", "")]))

def archive_db_items(emp_name, items):
    if not items:
        return
    stats = worker.data["db_stats"].setdefault(emp_name, {
        "total": 0,
        "done": 0,
        "dibalas": 0,
        "counts": {s: 0 for s in DB_STATUSES}
    })
    stats.setdefault("counts", {})
    for n in items:
        stt = n.get("status", "Belum Dicek")
        stats["total"] = stats.get("total", 0) + 1
        if stt != "Belum Dicek":
            stats["done"] = stats.get("done", 0) + 1
        if stt == "Dibalas":
            stats["dibalas"] = stats.get("dibalas", 0) + 1
        stats["counts"][stt] = stats["counts"].get(stt, 0) + 1

def revoke_employee_db(emp_name, item_ids=None, keep_stats=True, notify=True):
    my_db = next((d for d in worker.data["databases"] if d["name"] == emp_name), None)
    if not my_db or not my_db.get("numbers"):
        return 0
    numbers = my_db["numbers"]
    if item_ids is None:
        revoked = list(numbers)
        remaining = []
    else:
        id_set = set(item_ids)
        revoked = [n for n in numbers if n.get("id") in id_set]
        remaining = [n for n in numbers if n.get("id") not in id_set]

    if not revoked:
        return 0

    if keep_stats:
        archive_db_items(emp_name, revoked)
        save_key_sync("db_stats.json")

    if remaining:
        my_db["numbers"] = remaining
    else:
        worker.data["databases"] = [d for d in worker.data["databases"] if d["name"] != emp_name]
    save_key_sync("databases.json")

    if notify:
        target_u = next((u for u in worker.data["users"] if u["name"] == emp_name), None)
        if target_u:
            ket = "statistik tetap dipertahankan" if keep_stats else "statistik direset sesuai pencabutan"
            target_u.setdefault("notifications", []).append({
                "type": "db_revoke",
                "message": f"{len(revoked)} database Anda ditarik/dicabut oleh admin ({ket}).",
                "read": False,
                "time": str(now_wib())
            })
            save_users_sync()
    return len(revoked)

def render_eagle_wallet_card(balance, role_label, owner_name):
    bal_int = int(balance or 0)
    safe_owner = html.escape(owner_name or "")
    safe_role = html.escape(role_label or "Karyawan")
    wib_now_txt = now_wib().strftime("%d %b %Y · %H:%M WIB")
    card_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        body {{ background: transparent; overflow: hidden; padding: 2px; }}
        .eagle-card {{
            position: relative;
            border-radius: 24px;
            padding: 22px 22px 18px 22px;
            color: #F8FAFC;
            background: linear-gradient(135deg, #091534 0%, #16337A 45%, #0B63B8 82%, #0284C7 100%);
            border: 1px solid rgba(56, 189, 248, 0.45);
            box-shadow: 0 14px 34px rgba(14, 165, 233, 0.35), inset 0 1px 0 rgba(255,255,255,0.22);
            overflow: hidden;
            min-height: 218px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .shimmer {{
            position: absolute; top: -50%; left: -60%; width: 45%; height: 220%;
            background: linear-gradient(115deg, transparent 20%, rgba(255,255,255,0.16) 50%, transparent 80%);
            transform: rotate(22deg);
            animation: sweep 5.5s infinite ease-in-out;
            pointer-events: none;
        }}
        @keyframes sweep {{
            0% {{ left: -70%; }}
            45% {{ left: 140%; }}
            100% {{ left: 140%; }}
        }}
        .eagle-bg {{
            position: absolute; right: -12px; bottom: -16px;
            width: 175px; height: 175px; opacity: 0.16;
            pointer-events: none;
            animation: floatWing 4.5s ease-in-out infinite;
        }}
        @keyframes floatWing {{
            0%, 100% {{ transform: translateY(0px) scale(1); }}
            50% {{ transform: translateY(-5px) scale(1.03); }}
        }}
        .glow-orb {{
            position: absolute; top: -40px; right: -30px;
            width: 150px; height: 150px; border-radius: 50%;
            background: radial-gradient(circle, rgba(250, 204, 21, 0.25) 0%, transparent 70%);
            pointer-events: none;
        }}
        .top-row {{
            display: flex; justify-content: space-between; align-items: center;
            position: relative; z-index: 2;
        }}
        .brand {{
            display: flex; align-items: center; gap: 10px;
        }}
        .crest {{
            width: 38px; height: 38px; border-radius: 12px;
            background: linear-gradient(135deg, rgba(250,204,21,0.22), rgba(56,189,248,0.22));
            border: 1px solid rgba(250,204,21,0.45);
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 0 14px rgba(250,204,21,0.25);
        }}
        .brand-text .title {{
            font-size: 13px; font-weight: 700; letter-spacing: 0.6px; color: #E0F2FE;
            text-transform: uppercase;
        }}
        .brand-text .sub {{
            font-size: 11px; color: #93C5FD; margin-top: 1px;
        }}
        .eye-btn {{
            background: rgba(15, 23, 42, 0.45);
            border: 1px solid rgba(148, 163, 184, 0.35);
            color: #E0F2FE; border-radius: 999px;
            padding: 6px 12px; font-size: 11px; font-weight: 600;
            cursor: pointer; display: flex; align-items: center; gap: 6px;
            backdrop-filter: blur(6px); transition: all 0.2s ease;
        }}
        .eye-btn:hover {{ background: rgba(56, 189, 248, 0.25); border-color: #38BDF8; }}
        .mid-row {{
            position: relative; z-index: 2; margin: 16px 0 14px 0;
        }}
        .bal-label {{
            font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
            color: #BAE6FD; opacity: 0.9; margin-bottom: 4px;
        }}
        .bal-value {{
            font-size: 32px; font-weight: 800; letter-spacing: -0.5px;
            background: linear-gradient(90deg, #FFFFFF 0%, #E0F2FE 65%, #FDE047 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            text-shadow: 0 2px 12px rgba(0,0,0,0.18);
        }}
        .bot-row {{
            display: flex; justify-content: space-between; align-items: center;
            padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.18);
            position: relative; z-index: 2; font-size: 11px; color: #DBEAFE;
        }}
        .pill {{
            background: linear-gradient(135deg, rgba(250,204,21,0.2), rgba(56,189,248,0.22));
            border: 1px solid rgba(250,204,21,0.4);
            color: #FEF08A; padding: 4px 10px; border-radius: 999px;
            font-weight: 700; font-size: 10px; letter-spacing: 0.5px;
        }}
    </style>
    </head>
    <body>
    <div class="eagle-card">
        <div class="shimmer"></div>
        <div class="glow-orb"></div>

        <!-- Custom SVG Elang Sayap Terbentang (Watermark) -->
        <svg class="eagle-bg" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M100 32 C112 22, 130 24, 138 36 C126 36, 120 42, 118 50 C142 38, 174 34, 194 44 C174 58, 152 68, 132 72 C154 74, 174 82, 186 94 C162 98, 140 96, 120 90 C134 104, 142 122, 142 142 C126 130, 114 116, 106 100 L100 168 L94 100 C86 116, 74 130, 58 142 C58 122, 66 104, 80 90 C60 96, 38 98, 14 94 C26 82, 46 74, 68 72 C48 68, 26 58, 6 44 C26 34, 58 38, 82 50 C80 42, 74 36, 62 36 C70 24, 88 22, 100 32 Z" fill="url(#eagleGrad)"/>
            <defs>
                <linearGradient id="eagleGrad" x1="0" y1="0" x2="200" y2="200" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stop-color="#FACC15"/>
                    <stop offset="100%" stop-color="#38BDF8"/>
                </linearGradient>
            </defs>
        </svg>

        <div class="top-row">
            <div class="brand">
                <div class="crest">
                    <!-- Custom SVG Kepala Elang -->
                    <svg width="24" height="24" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M14 48 C14 28, 26 14, 44 12 C40 17, 39 21, 41 25 C49 24, 55 27, 58 33 C51 32, 46 34, 43 38 C46 41, 46 47, 41 51 C34 48, 26 48, 14 48 Z" fill="#FACC15"/>
                        <path d="M44 27 C49 27, 54 29, 57 33 C52 33, 47 35, 44 38 L39 33 Z" fill="#F59E0B"/>
                        <circle cx="35" cy="24" r="2.6" fill="#0F172A"/>
                    </svg>
                </div>
                <div class="brand-text">
                    <div class="title">Dompet Elang</div>
                    <div class="sub">{safe_owner} · {safe_role}</div>
                </div>
            </div>
            <button class="eye-btn" id="toggleBtn" onclick="toggleBalance()">
                <span id="eyeLabel">Sembunyikan</span>
            </button>
        </div>

        <div class="mid-row">
            <div class="bal-label">Total Saldo Gaji</div>
            <div class="bal-value" id="balText">Rp 0</div>
        </div>

        <div class="bot-row">
            <span>{wib_now_txt}</span>
            <span class="pill">ELANG GOLD</span>
        </div>
    </div>

    <script>
        const target = {bal_int};
        let hidden = false;
        const balEl = document.getElementById("balText");
        const eyeLabel = document.getElementById("eyeLabel");

        function fmtRp(val) {{
            return "Rp " + Number(val).toLocaleString("id-ID");
        }}

        function animateValue(start, end, duration) {{
            const startTime = performance.now();
            function frame(now) {{
                const progress = Math.min((now - startTime) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const current = Math.round(start + (end - start) * eased);
                if (!hidden) balEl.textContent = fmtRp(current);
                if (progress < 1) requestAnimationFrame(frame);
            }}
            requestAnimationFrame(frame);
        }}

        function toggleBalance() {{
            hidden = !hidden;
            if (hidden) {{
                balEl.textContent = "Rp ••••••••";
                eyeLabel.textContent = "Tampilkan";
            }} else {{
                balEl.textContent = fmtRp(target);
                eyeLabel.textContent = "Sembunyikan";
            }}
        }}

        animateValue(0, target, 750);
    </script>
    </body>
    </html>
    """
    components.html(card_html, height=238, scrolling=False)


# ==========================================
# 3. AUTENTIKASI
# ==========================================
def read_session_cookie(cookie_tokens):
    tok = None
    if isinstance(cookie_tokens, dict):
        tok = cookie_tokens.get("elang_session_token")
    if not tok:
        try:
            tok = st.context.cookies.get("elang_session_token")
        except Exception:
            tok = None
    return tok


cookie_tokens = {}
if cookie_manager is not None:
    try:
        cookie_tokens = cookie_manager.get_all() or {}
    except Exception:
        cookie_tokens = {}


def login_page():
    st.markdown(
        "<div style='text-align: center; margin-bottom: 10px; "
        "filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.6));'>"
        "<img src='https://cdn.aceimg.com/mD4NlOxLG.png' width='100'></div>",
        unsafe_allow_html=True
    )
    st.markdown("<h2 style='text-align: center; color: #38BDF8;'>ElangPintar</h2>", unsafe_allow_html=True)
    st.caption("Login akan bertahan hingga akhir hari (00:00 WIB).")
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
                    token = worker.create_session(u["uid"])
                    st.session_state.session_token = token
                    st.session_state["_pending_cookie_set"] = token
                    st.session_state["_cookie_set_tries"] = 0
                    st.session_state.pop("_pending_cookie_delete", None)
                    st.rerun()
            else:
                st.error("UID atau Password salah.")


def try_restore_session(tokens_dict):
    if st.session_state.get("_pending_cookie_delete"):
        return False
    token = read_session_cookie(tokens_dict)
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


# Sinkronkan hapus cookie saat logout tanpa terpotong st.rerun()
if st.session_state.get("_pending_cookie_delete"):
    existing_tok = read_session_cookie(cookie_tokens)
    tries = st.session_state.get("_cookie_del_tries", 0)
    if cookie_manager is not None and existing_tok and tries < 3:
        try:
            cookie_manager.delete("elang_session_token", key="del_cookie_logout")
        except Exception:
            pass
        st.session_state["_cookie_del_tries"] = tries + 1
    else:
        st.session_state.pop("_pending_cookie_delete", None)
        st.session_state.pop("_cookie_del_tries", None)

if "user" not in st.session_state:
    try_restore_session(cookie_tokens)

if "user" not in st.session_state:
    login_page()
    st.stop()

# Sinkronkan simpan cookie setelah login tanpa terpotong st.rerun()
_pending_tok = st.session_state.get("_pending_cookie_set")
if _pending_tok:
    if cookie_tokens.get("elang_session_token") == _pending_tok:
        st.session_state.pop("_pending_cookie_set", None)
        st.session_state.pop("_cookie_set_tries", None)
    else:
        tries = st.session_state.get("_cookie_set_tries", 0)
        if cookie_manager is not None and tries < 3:
            try:
                eod_aware = now_wib_aware().replace(hour=23, minute=59, second=59, microsecond=0)
                try:
                    cookie_manager.set(
                        "elang_session_token",
                        _pending_tok,
                        expires_at=eod_aware,
                        same_site="lax",
                        key="set_cookie_login"
                    )
                except TypeError:
                    cookie_manager.set(
                        "elang_session_token",
                        _pending_tok,
                        expires_at=eod_aware,
                        key="set_cookie_login"
                    )
            except Exception:
                pass
            st.session_state["_cookie_set_tries"] = tries + 1
        else:
            st.session_state.pop("_pending_cookie_set", None)
            st.session_state.pop("_cookie_set_tries", None)

user = next((u for u in worker.data["users"] if u["uid"] == st.session_state.user["uid"]), st.session_state.user)
st.session_state.user = user


# ==========================================
# 3B. POPUP MODAL UNTUK KARYAWAN
# ==========================================
@st.dialog("📢 Pengumuman Dari Admin")
def show_employee_popups(active_popups, current_user):
    for idx, p in enumerate(active_popups):
        if idx > 0:
            st.divider()
        if p.get("title"):
            st.subheader(p["title"])
        if p.get("image_key"):
            img_url = worker.media_link(p["image_key"])
            if img_url:
                st.image(img_url, use_container_width=True)
        if p.get("message"):
            st.write(p["message"])
        st.caption(f"Berakhir otomatis dalam: **{fmt_remaining(p.get('expires_at', ''))}** (s.d. {p.get('expires_at', '-')[:16].replace('T', ' ')} WIB)")

    st.write("")
    if st.button("Mengerti / Tutup", type="primary", use_container_width=True, icon=":material/check_circle:", key="btn_close_popup_modal"):
        closed_sess = st.session_state.setdefault("closed_popups_session", set())
        changed = False
        for p in active_popups:
            closed_sess.add(p["id"])
            if p.get("allow_dismiss", True):
                dismissed = p.setdefault("dismissed_by", [])
                if current_user["uid"] not in dismissed:
                    dismissed.append(current_user["uid"])
                    changed = True
        if changed:
            save_key_sync("popups.json")
        st.rerun()

if user["role"] == "karyawan":
    now_iso = now_wib().isoformat()
    closed_sess = st.session_state.get("closed_popups_session", set())
    visible_popups = [
        p for p in worker.data.get("popups", [])
        if (not p.get("expires_at") or now_iso <= p["expires_at"])
        and p.get("target") in ("all", user["name"])
        and p["id"] not in closed_sess
        and (not p.get("allow_dismiss", True) or user["uid"] not in p.get("dismissed_by", []))
    ]
    if visible_popups:
        show_employee_popups(visible_popups, user)


st.markdown(
    "<div style='text-align: center; margin-bottom: 16px; "
    "filter: drop-shadow(0 0 15px rgba(59, 130, 246, 0.6));'>"
    "<img src='https://cdn.aceimg.com/mD4NlOxLG.png' width='66'></div>",
    unsafe_allow_html=True
)


# ==========================================
# 4. ROUTING NAV BAWAH  (WAJIB dibungkus container key="nav_bottom")
# ==========================================
def nav_icon(name, label):
    url = f"https://api.iconify.design/ph/{name}.svg?color=%238A99AD"
    return f"![icon]({url})\n{label}"

with st.container(key="nav_bottom"):
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
            }[x],
            key="nav_radio_admin"
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
            }[x],
            key="nav_radio_karyawan"
        )


# ==========================================
# 5. HALAMAN AKUN (TANPA WITHDRAW, KARTU SALDO ELANG SVG+JS)
# ==========================================
if page == "Akun":
    st.markdown(f"""
    <div class="profile-card">
        <div class="profile-avatar">{svg('user', 36, 'white')}</div>
        <div class="profile-info">
            <h3>{html.escape(user['name'])}</h3>
            <p>UID: {user['uid']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    my_payroll = worker.data["payroll"].get(user["name"], 0)
    role_txt = "Administrator" if user["role"] == "admin" else "Karyawan ElangPintar"
    render_eagle_wallet_card(my_payroll, role_txt, user["name"])

    tg_raw = user.get("telegram", "").strip().lstrip("@")
    tg_display = f"@{tg_raw}" if tg_raw else "Belum diatur"
    tg_color = "#22C55E" if tg_raw else "#F59E0B"
    notif_count = len(user.get("notifications", []))

    st.markdown(f"""
    <div class="list-item">
        <div class="list-item-left">{svg('bell', 20)}<span>Notifikasi</span></div>
        <span style="color: #94A3B8;">{notif_count} pesan &gt;</span>
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
                        if old_name in worker.data["db_stats"]:
                            worker.data["db_stats"][new_name_clean] = worker.data["db_stats"].pop(old_name)
                            save_key_sync("db_stats.json")
                        for p in worker.data.get("popups", []):
                            if p.get("target") == old_name:
                                p["target"] = new_name_clean
                        save_key_sync("popups.json")
                        for k in ["ndp", "wd", "video"]:
                            for r in worker.data["reports"][k]:
                                if r["user"] == old_name: r["user"] = new_name_clean
                        save_key_sync("databases.json")
                        save_key_sync("payroll.json")
                        save_key_sync("reports.json")

                    save_users_sync()
                    st.toast("Profil berhasil diperbarui!")
                    st.rerun()

    if st.button("Keluar / Logout", use_container_width=True, icon=":material/logout:"):
        token = st.session_state.get("session_token")
        worker.delete_session(token)

        st.session_state.pop("user", None)
        st.session_state.pop("session_token", None)
        st.session_state.pop("closed_popups_session", None)
        st.session_state.pop("_pending_cookie_set", None)
        st.session_state.pop("_cookie_set_tries", None)
        st.session_state["_pending_cookie_delete"] = True
        st.session_state["_cookie_del_tries"] = 0
        st.rerun()


# ==========================================
# 6. HALAMAN ADMIN
# ==========================================
elif user["role"] == "admin":
    if page == "Employee":
        st.header("Manajemen Karyawan")
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Buat Akun", "Kelola", "GiveDB", "SetText", "PopUp"])

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
                                if u["name"] in worker.data["db_stats"]:
                                    del worker.data["db_stats"][u["name"]]
                                    save_key_sync("db_stats.json")
                                for k in ["ndp", "wd", "video"]:
                                    worker.data["reports"][k] = [r for r in worker.data["reports"][k] if r["user"] != u["name"]]
                                save_users_sync()
                                save_key_sync("databases.json")
                                save_key_sync("payroll.json")
                                save_key_sync("reports.json")
                                st.session_state.confirm_delete = None
                                st.success(f"Akun {u['name']} dihapus.")
                                st.rerun()
                            if cc2.button("Batal", key=f"no_{u['uid']}", use_container_width=True):
                                st.session_state.confirm_delete = None
                                st.rerun()

        with tab3:
            karyawan_list = [u["name"] for u in worker.data["users"] if u["role"] == "karyawan"]
            if karyawan_list:
                st.info("Database dikirimkan"
                        "Format: **1 baris = 1 DB** — `DB Nama` (pisahkan DB dan nama dengan spasi).")
                target = st.selectbox("Pilih Karyawan", karyawan_list, key="givedb_target")

                existing_db = next((d for d in worker.data["databases"] if d["name"] == target), None)
                replace_mode = "replace_drop"
                if existing_db and existing_db.get("numbers"):
                    st.warning(f"⚠️ **{target}** saat ini masih memiliki **{len(existing_db['numbers'])} DB aktif**.")
                    replace_mode = st.radio(
                        "Perlakuan terhadap DB lama saat mengirim DB baru:",
                        [
                            "replace_drop",
                            "replace_keep",
                            "append"
                        ],
                        format_func=lambda x: {
                            "replace_drop": "Ganti DB lama & hapus pengaruh DB lama dari statistik",
                            "replace_keep": "Ganti DB lama & pertahankan pengaruh DB lama di statistik",
                            "append": "Tambahkan ke DB yang sudah ada",
                        }[x],
                        key="givedb_replace_mode"
                    )

                db_input = st.text_area(
                    "Input Database",
                    placeholder="Contoh:\n628123456789 Budi\n628987654321 Siti\n628555555555 Andi Wijaya",
                    height=220,
                    key="givedb_input"
                )

                if st.button("Kirim DB Privat", icon=":material/send:") and db_input.strip():
                    parsed = []
                    for line in db_input.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split(None, 1)
                        num = parts[0]
                        nm = parts[1].strip() if len(parts) > 1 else ""
                        parsed.append({
                            "id": uuid.uuid4().hex,
                            "num": num,
                            "name": nm,
                            "status": "Belum Dicek"
                        })

                    if not parsed:
                        st.error("Tidak ada baris valid.")
                    else:
                        if existing_db and existing_db.get("numbers") and replace_mode == "append":
                            existing_db["numbers"].extend(parsed)
                        else:
                            if existing_db and existing_db.get("numbers") and replace_mode == "replace_keep":
                                archive_db_items(target, existing_db["numbers"])
                                save_key_sync("db_stats.json")
                            worker.data["databases"] = [d for d in worker.data["databases"] if d["name"] != target]
                            worker.data["databases"].append({
                                "name": target,
                                "numbers": parsed
                            })

                        target_u = next((u for u in worker.data["users"] if u["name"] == target), None)
                        if target_u:
                            target_u.setdefault("notifications", []).append({
                                "type": "db",
                                "message": f"Anda menerima {len(parsed)} database baru dari admin",
                                "read": False,
                                "time": str(now_wib())
                            })
                            save_users_sync()

                        save_key_sync("databases.json")
                        st.success(f"✅ {len(parsed)} DB dikirim privat ke {target}. Notifikasi terkirim.")
                        st.rerun()

                st.divider()
                st.subheader("Tarik / Cabut DB Karyawan")
                st.caption("Cabut DB yang sudah dikirim (misal jika salah kirim) kapan saja.")
                active_db_owners = [d["name"] for d in worker.data["databases"] if d.get("numbers")]
                if not active_db_owners:
                    st.info("Saat ini tidak ada karyawan yang memiliki DB aktif.")
                else:
                    rev_target = st.selectbox("Pilih Karyawan yang DB-nya Akan Ditarik", active_db_owners, key="rev_target_givedb")
                    rev_db = next((d for d in worker.data["databases"] if d["name"] == rev_target), None)
                    if rev_db and rev_db.get("numbers"):
                        nums = rev_db["numbers"]
                        st.caption(
                            f"DB aktif **{rev_target}**: **{len(nums)}** item "
                            f"(Belum Dicek: {sum(1 for n in nums if n.get('status', 'Belum Dicek')=='Belum Dicek')}, "
                            f"Tidak Terdaftar: {sum(1 for n in nums if n.get('status')=='Tidak Terdaftar')}, "
                            f"Terdaftar: {sum(1 for n in nums if n.get('status')=='Terdaftar')}, "
                            f"Dibaca: {sum(1 for n in nums if n.get('status')=='Dibaca')}, "
                            f"Dibalas: {sum(1 for n in nums if n.get('status')=='Dibalas')})"
                        )
                        rev_mode = st.radio(
                            "Mode Pencabutan",
                            ["Tarik Semua DB", "Pilih Item DB Tertentu"],
                            horizontal=True,
                            key="rev_mode_givedb"
                        )
                        selected_ids = None
                        if rev_mode == "Pilih Item DB Tertentu":
                            id_map = {
                                n["id"]: f"{idx+1}. {n['num']} ({n.get('name') or '-'}) [{n.get('status', 'Belum Dicek')}]"
                                for idx, n in enumerate(nums)
                            }
                            selected_ids = st.multiselect(
                                "Pilih Item DB yang Dicabut",
                                list(id_map.keys()),
                                format_func=lambda k: id_map[k],
                                key="rev_items_givedb"
                            )

                        stat_choice = st.radio(
                            "Pengaruh Terhadap Statistik (Analitik)",
                            [
                                "Pertahankan statistik (pengaruh DB tetap dihitung)",
                                "Hapus pengaruh DB dari statistik"
                            ],
                            key="rev_stat_givedb"
                        )
                        keep_stats = stat_choice.startswith("Pertahankan")
                        notify_emp = st.checkbox("Kirim notifikasi ke karyawan", value=True, key="rev_notify_givedb")

                        if st.button("Cabut / Tarik DB", type="primary", icon=":material/undo:", key="btn_rev_givedb"):
                            if rev_mode == "Pilih Item DB Tertentu" and not selected_ids:
                                st.error("Pilih minimal 1 item DB untuk ditarik.")
                            else:
                                count_rev = revoke_employee_db(
                                    rev_target,
                                    item_ids=selected_ids,
                                    keep_stats=keep_stats,
                                    notify=notify_emp
                                )
                                st.success(
                                    f"✅ {count_rev} DB milik {rev_target} berhasil ditarik "
                                    f"({'statistik dipertahankan' if keep_stats else 'pengaruh DB dihapus dari statistik'})."
                                )
                                st.rerun()
            else:
                st.info("Belum ada karyawan.")

        with tab4:
            st.subheader("Tambah Teks & Foto Baru")
            st.caption("Teks dan foto di sini **tersimpan permanen** (tidak ikut terhapus otomatis harian).")
            with st.form("add_new_text_form"):
                new_title = st.text_input("Nama / Judul Teks")
                new_content = st.text_area("Isi Teks (opsional jika hanya mengirim foto)", height=140)
                new_img = st.file_uploader("Upload Foto Pendukung (Opsional - PNG/JPG/WEBP)", type=["png", "jpg", "jpeg", "webp"], key="new_text_img")
                if st.form_submit_button("Tambah Teks / Foto", icon=":material/add:"):
                    if not new_title.strip():
                        st.error("Judul tidak boleh kosong.")
                    elif not new_content.strip() and new_img is None:
                        st.error("Isi minimal teks atau upload foto.")
                    else:
                        img_key = None
                        if new_img is not None:
                            res_key = worker.execute(worker.upload_image_s3, new_img, new_img.name)
                            if isinstance(res_key, Exception) or not str(res_key).startswith("images/"):
                                st.error(f"Gagal upload foto: {res_key}")
                                st.stop()
                            img_key = res_key
                        worker.data["texts"].append({
                            "id": uuid.uuid4().hex,
                            "title": new_title.strip(),
                            "content": new_content,
                            "image_key": img_key,
                            "created_at": str(now_wib())
                        })
                        save_key_sync("texts.json")
                        st.success("Teks / Foto berhasil ditambahkan!")
                        st.rerun()

            st.divider()
            st.subheader("Daftar Teks & Foto Tersimpan")
            if not worker.data["texts"]:
                st.info("Belum ada teks yang tersimpan.")
            else:
                for idx, t in enumerate(worker.data["texts"]):
                    has_img = " 🖼️" if t.get("image_key") else ""
                    with st.expander(f"📄 {t['title']}{has_img}"):
                        if t.get("image_key"):
                            cur_url = worker.media_link(t["image_key"])
                            if cur_url:
                                st.image(cur_url, use_container_width=True)
                        with st.form(f"edit_form_{t['id']}"):
                            edit_title = st.text_input("Edit Judul", value=t["title"])
                            edit_content = st.text_area("Edit Isi Teks", value=t.get("content", ""), height=140)
                            replace_img = st.file_uploader("Ganti / Tambah Foto (Opsional)", type=["png", "jpg", "jpeg", "webp"], key=f"rep_img_{t['id']}")
                            remove_img = st.checkbox("Hapus foto saat ini", value=False, key=f"rm_img_{t['id']}") if t.get("image_key") else False

                            c1, c2 = st.columns(2)
                            if c1.form_submit_button("Simpan Perubahan", use_container_width=True, icon=":material/save:"):
                                t["title"] = edit_title.strip() or t["title"]
                                t["content"] = edit_content
                                if replace_img is not None:
                                    res_key = worker.execute(worker.upload_image_s3, replace_img, replace_img.name)
                                    if not isinstance(res_key, Exception) and str(res_key).startswith("images/"):
                                        if t.get("image_key"):
                                            worker.execute(worker.delete_media_s3, t["image_key"])
                                        t["image_key"] = res_key
                                    else:
                                        st.error(f"Gagal upload foto: {res_key}")
                                elif remove_img and t.get("image_key"):
                                    worker.execute(worker.delete_media_s3, t["image_key"])
                                    t["image_key"] = None
                                save_key_sync("texts.json")
                                st.toast("Teks diperbarui!")
                                st.rerun()

                            if c2.form_submit_button("Hapus Teks", type="primary", use_container_width=True, icon=":material/delete:"):
                                if t.get("image_key"):
                                    worker.execute(worker.delete_media_s3, t["image_key"])
                                worker.data["texts"].pop(idx)
                                save_key_sync("texts.json")
                                st.toast("Teks dihapus!")
                                st.rerun()

        with tab5:
            st.subheader("Kirim PopUp ke Karyawan")
            st.caption("PopUp langsung muncul sebagai jendela pengumuman di layar karyawan dan otomatis terhapus saat waktu berakhir.")

            karyawan_list = [u["name"] for u in worker.data["users"] if u["role"] == "karyawan"]
            target_options = ["all"] + karyawan_list

            p_target = st.selectbox(
                "Target Penerima",
                target_options,
                format_func=lambda x: "Semua Karyawan" if x == "all" else x,
                key="popup_target_sel"
            )
            p_title = st.text_input("Judul PopUp", placeholder="Contoh: Promo / Arahan Penting Hari Ini", key="popup_title_in")
            p_msg = st.text_area("Pesan PopUp (opsional jika hanya kirim foto)", height=120, key="popup_msg_in")
            p_img = st.file_uploader("Foto PopUp (Opsional - PNG/JPG/WEBP)", type=["png", "jpg", "jpeg", "webp"], key="popup_img_in")

            dur_mode = st.radio(
                "Waktu Hapus Otomatis",
                ["Durasi Cepat", "Tanggal & Jam Spesifik (WIB)"],
                horizontal=True,
                key="popup_dur_mode"
            )

            now_dt = now_wib()
            if dur_mode == "Durasi Cepat":
                dur_choices = {
                    "15 Menit": timedelta(minutes=15),
                    "1 Jam": timedelta(hours=1),
                    "3 Jam": timedelta(hours=3),
                    "6 Jam": timedelta(hours=6),
                    "12 Jam": timedelta(hours=12),
                    "24 Jam": timedelta(hours=24),
                    "3 Hari": timedelta(days=3),
                    "7 Hari": timedelta(days=7),
                }
                sel_dur = st.selectbox("Tampilkan Selama", list(dur_choices.keys()), index=3, key="popup_dur_preset")
                expires_dt = now_dt + dur_choices[sel_dur]
            else:
                dc1, dc2 = st.columns(2)
                exp_date = dc1.date_input("Tanggal Berakhir", value=now_dt.date(), min_value=now_dt.date(), key="popup_exp_date")
                default_time = (now_dt + timedelta(hours=2)).time().replace(second=0, microsecond=0)
                exp_time = dc2.time_input("Jam Berakhir (WIB)", value=default_time, key="popup_exp_time")
                expires_dt = datetime.combine(exp_date, exp_time)

            allow_dismiss = st.checkbox(
                "Izinkan karyawan menutup permanen (jika tidak dicentang, popup hanya tertutup per sesi & muncul lagi saat refresh sampai waktu habis)",
                value=True,
                key="popup_allow_dismiss"
            )

            if st.button("Kirim PopUp Sekarang", type="primary", use_container_width=True, icon=":material/campaign:", key="btn_send_popup"):
                if not p_title.strip() and not p_msg.strip() and p_img is None:
                    st.error("Isi minimal judul, pesan, atau upload foto.")
                elif expires_dt <= now_wib():
                    st.error("Waktu berakhir harus lebih besar dari waktu sekarang (WIB).")
                else:
                    img_key = None
                    if p_img is not None:
                        res_key = worker.execute(worker.upload_image_s3, p_img, p_img.name)
                        if isinstance(res_key, Exception) or not str(res_key).startswith("images/"):
                            st.error(f"Gagal upload foto popup: {res_key}")
                            st.stop()
                        img_key = res_key

                    worker.data["popups"].append({
                        "id": uuid.uuid4().hex,
                        "title": p_title.strip() or "Pengumuman Admin",
                        "message": p_msg.strip(),
                        "image_key": img_key,
                        "target": p_target,
                        "allow_dismiss": allow_dismiss,
                        "dismissed_by": [],
                        "created_at": now_wib().isoformat(),
                        "expires_at": expires_dt.isoformat()
                    })
                    save_key_sync("popups.json")
                    st.success(f"✅ PopUp aktif sampai {expires_dt.strftime('%d %b %Y %H:%M WIB')}!")
                    st.rerun()

            st.divider()
            st.subheader("Daftar PopUp Aktif")
            worker.cleanup_expired_popups()
            active_popups_list = worker.data.get("popups", [])
            if not active_popups_list:
                st.info("Tidak ada PopUp aktif saat ini.")
            else:
                for p_idx, p in enumerate(list(active_popups_list)):
                    tgt_lbl = "Semua Karyawan" if p.get("target") == "all" else p.get("target", "-")
                    rem_lbl = fmt_remaining(p.get("expires_at", ""))
                    with st.expander(f" {p.get('title','PopUp')} → {tgt_lbl} (Sisa: {rem_lbl})"):
                        if p.get("image_key"):
                            p_url = worker.media_link(p["image_key"])
                            if p_url:
                                st.image(p_url, use_container_width=True)
                        if p.get("message"):
                            st.write(p["message"])
                        st.caption(
                            f"Dibuat: {p.get('created_at','-')[:16].replace('T',' ')} WIB · "
                            f"Berakhir: {p.get('expires_at','-')[:16].replace('T',' ')} WIB · "
                            f"Sudah ditutup permanen oleh: {len(p.get('dismissed_by', []))} user"
                        )
                        if st.button("Hentikan & Hapus PopUp", key=f"del_pop_{p['id']}", type="primary", icon=":material/delete:"):
                            if p.get("image_key"):
                                worker.execute(worker.delete_media_s3, p["image_key"])
                            worker.data["popups"] = [x for x in worker.data["popups"] if x["id"] != p["id"]]
                            save_key_sync("popups.json")
                            st.success("PopUp dihentikan dan dihapus.")
                            st.rerun()


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
            preserved = worker.data["db_stats"].get(selected)
            pres_counts = (preserved or {}).get("counts", {})

            active_total = len(my_db["numbers"]) if my_db else 0
            active_done = sum(1 for n in my_db["numbers"] if n.get("status", "Belum Dicek") != "Belum Dicek") if my_db else 0
            active_tidak = sum(1 for n in my_db["numbers"] if n.get("status") == "Tidak Terdaftar") if my_db else 0
            active_dibalas = sum(1 for n in my_db["numbers"] if n.get("status") == "Dibalas") if my_db else 0

            pres_total = preserved.get("total", 0) if preserved else 0
            pres_done = preserved.get("done", 0) if preserved else 0
            pres_tidak = pres_counts.get("Tidak Terdaftar", 0)
            pres_dibalas = preserved.get("dibalas", 0) if preserved else 0

            total_db = active_total + pres_total
            done_db = active_done + pres_done
            tidak_db = active_tidak + pres_tidak
            dibalas_db = active_dibalas + pres_dibalas

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

            checked_pct = (done_db / total_db * 100) if total_db > 0 else 0.0
            valid_pool = max(total_db - tidak_db, 0)
            if total_db == 0:
                reply_pct = 0.0
                db_pct = 0.0
            elif valid_pool == 0:
                reply_pct = 100.0 if done_db == total_db else 0.0
                db_pct = checked_pct
            else:
                reply_pct = dibalas_db / valid_pool * 100
                db_pct = (checked_pct + reply_pct) / 2

            video_pct = (video_approved / vid_total * 100) if vid_total > 0 else 0.0
            kinerja = (db_pct + video_pct) / 2

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("NDP", total_ndp)
            c2.metric("DB Dicek", f"{done_db}/{total_db}")
            c3.metric("Video", f"{video_approved}/{vid_total}")
            c4.metric("Kinerja", f"{kinerja:.1f}%")

            st.progress(min(kinerja / 100, 1.0))
            st.caption(
                f"Progres Cek DB: **{checked_pct:.1f}%** · "
                f"Rasio Dibalas (dari DB valid/belum dicek): **{reply_pct:.1f}%** · "
                f"Video Approved: **{video_pct:.1f}%**"
            )

            if pres_total > 0:
                st.info(
                    f"📊 Termasuk **{pres_total} DB yang telah dicabut** (statistik dipertahankan): "
                    f"Dicek **{pres_done}**, Dibalas **{pres_dibalas}**."
                )
                if st.button("Hapus Pengaruh DB Tarikan dari Statistik", key=f"clr_pres_{selected}", icon=":material/delete_sweep:"):
                    worker.data["db_stats"].pop(selected, None)
                    save_key_sync("db_stats.json")
                    st.success("Pengaruh DB tarikan dihapus dari statistik.")
                    st.rerun()

            if (my_db and my_db.get("numbers")) or pres_total > 0:
                st.divider()
                st.subheader("Rincian Database")

                status_order = list(DB_STATUSES)

                cols = st.columns(len(status_order))
                for col, stt in zip(cols, status_order):
                    active_cnt = sum(1 for n in my_db["numbers"] if n.get("status", "Belum Dicek") == stt) if my_db else 0
                    cnt = active_cnt + pres_counts.get(stt, 0)
                    col.metric(stt, cnt)

                if my_db and my_db.get("numbers"):
                    st.write("")
                    filter_st = st.multiselect(
                        "Filter Status",
                        status_order,
                        default=status_order,
                        key=f"anfilt_{selected}"
                    )

                    filtered = [n for n in my_db["numbers"] if n.get("status", "Belum Dicek") in filter_st]

                    if filtered:
                        rows = [
                            {
                                "No": idx,
                                "DB": n["num"],
                                "Nama": n.get("name") or "-",
                                "Status": n.get("status", "Belum Dicek"),
                            }
                            for idx, n in enumerate(filtered, 1)
                        ]
                        st.dataframe(rows, use_container_width=True, hide_index=True)
                        st.caption(f"Menampilkan **{len(filtered)}** dari **{len(my_db['numbers'])}** DB aktif.")
                    else:
                        st.info("Tidak ada DB aktif dengan status yang dipilih.")

                    with st.expander("Tarik / Cabut DB Karyawan Ini"):
                        an_rev_mode = st.radio(
                            "Mode Pencabutan",
                            ["Tarik Semua DB", "Pilih Item DB Tertentu"],
                            horizontal=True,
                            key=f"an_rev_mode_{selected}"
                        )
                        an_sel_ids = None
                        if an_rev_mode == "Pilih Item DB Tertentu":
                            an_id_map = {
                                n["id"]: f"{idx+1}. {n['num']} ({n.get('name') or '-'}) [{n.get('status', 'Belum Dicek')}]"
                                for idx, n in enumerate(my_db["numbers"])
                            }
                            an_sel_ids = st.multiselect(
                                "Pilih Item DB yang Dicabut",
                                list(an_id_map.keys()),
                                format_func=lambda k: an_id_map[k],
                                key=f"an_rev_items_{selected}"
                            )
                        an_stat_choice = st.radio(
                            "Pengaruh Terhadap Statistik",
                            [
                                "Pertahankan statistik (pengaruh DB tetap dihitung)",
                                "Hapus pengaruh DB dari statistik"
                            ],
                            key=f"an_rev_stat_{selected}"
                        )
                        an_keep = an_stat_choice.startswith("Pertahankan")
                        an_notify = st.checkbox("Kirim notifikasi ke karyawan", value=True, key=f"an_rev_notify_{selected}")
                        if st.button("Cabut / Tarik DB", type="primary", icon=":material/undo:", key=f"an_rev_btn_{selected}"):
                            if an_rev_mode == "Pilih Item DB Tertentu" and not an_sel_ids:
                                st.error("Pilih minimal 1 item DB untuk ditarik.")
                            else:
                                count_rev = revoke_employee_db(
                                    selected,
                                    item_ids=an_sel_ids,
                                    keep_stats=an_keep,
                                    notify=an_notify
                                )
                                st.success(f"✅ {count_rev} DB berhasil ditarik.")
                                st.rerun()
                else:
                    st.caption("Saat ini karyawan tidak memiliki DB aktif (hanya statistik DB yang dipertahankan).")
            else:
                st.info("Karyawan ini belum memiliki database.")

    elif page == "Report":
        st.header("Laporan & Approval")
        tab_ndp, tab_wd, tab_video = st.tabs(["Cek NDP+Video", "Withdraw", "Video Standalone"])

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

        with tab_video:
            vids = worker.data["reports"]["video"]
            if not vids:
                st.info("Belum ada video standalone.")
            else:
                now = now_wib()
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
                                   if _parse_t(v.get("time", "")) < today_start
                                   and v.get("status", "pending") != "pending"]

                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("Total", len(vids))
                sc2.metric("Pending", len(pending_items))
                sc3.metric("Hari ini", len(hari_ini_items))
                sc4.metric("Lalu", len(lalu_items))

                st.divider()

                def render_video(idx, v, tab_tag):
                    status = v.get("status", "pending")
                    badge_map = {"pending": "[PENDING]", "approved": "[APPROVED]", "rejected": "[REJECTED]"}
                    badge = badge_map.get(status, "[?]")
                    label = f"{badge} {v['user']} · {v.get('caption','-')}"
                    cd_key = f"cd_{tab_tag}_{idx}"

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
                        if c1.button("Approve", key=f"av_{tab_tag}_{idx}",
                                     disabled=(status == "approved"),
                                     use_container_width=True, icon=":material/check_circle:"):
                            vids[idx]["status"] = "approved"
                            save_key("reports.json")
                            st.rerun()
                        if c2.button("Reject", key=f"rv_{tab_tag}_{idx}",
                                     disabled=(status == "rejected"),
                                     use_container_width=True, icon=":material/cancel:"):
                            vids[idx]["status"] = "rejected"
                            save_key("reports.json")
                            st.rerun()
                        if c3.button("Hapus", key=f"dv_{tab_tag}_{idx}",
                                     use_container_width=True, icon=":material/delete:"):
                            st.session_state[cd_key] = True

                        if st.session_state.get(cd_key, False):
                            st.error(f"Hapus permanen video **{v.get('caption','-')}**?")
                            y1, y2 = st.columns(2)
                            if y1.button("Ya, Hapus", key=f"y_{tab_tag}_{idx}", type="primary", use_container_width=True):
                                if v.get("key"):
                                    worker.execute(worker.delete_video_s3, v["key"])
                                vids.pop(idx)
                                save_key("reports.json")
                                st.session_state[cd_key] = False
                                st.success("Video dihapus.")
                                st.rerun()
                            if y2.button("Batal", key=f"n_{tab_tag}_{idx}", use_container_width=True):
                                st.session_state[cd_key] = False
                                st.rerun()

                s1, s2, s3 = st.tabs([
                    f"Terbaru ({len(pending_items)})",
                    f"Hari ini ({len(hari_ini_items)})",
                    f"Lalu ({len(lalu_items)})"
                ])
                with s1:
                    if not pending_items: st.success("Tidak ada video pending.")
                    for idx, v in pending_items: render_video(idx, v, "p")
                with s2:
                    if not hari_ini_items: st.info("Belum ada video diproses hari ini.")
                    for idx, v in hari_ini_items: render_video(idx, v, "h")
                with s3:
                    if not lalu_items: st.info("Tidak ada video lama.")
                    for idx, v in lalu_items: render_video(idx, v, "l")


# ==========================================
# 7. HALAMAN KARYAWAN
# ==========================================
else:
    if page == "Data":
        st.header("Database Kerja Saya")
        st.caption("Data ini privat — hanya Anda yang bisa melihat dan mengubah status.")

        unread = [n for n in user.get("notifications", []) if not n.get("read", False)]
        if unread:
            with st.container(border=True):
                st.markdown(
                    f"{svg('bell', 16)} <b>{len(unread)} notifikasi baru dari admin</b>",
                    unsafe_allow_html=True
                )
                for n in unread:
                    st.write(f"- {n['message']}  \n  <span style='color:#64748B;font-size:11px;'>{n.get('time','')}</span>",
                             unsafe_allow_html=True)
                if st.button("Tandai Dibaca", use_container_width=True, icon=":material/done_all:"):
                    for n in user.get("notifications", []):
                        n["read"] = True
                    save_users()
                    st.rerun()

        my_db = next((d for d in worker.data["databases"] if d["name"] == user["name"]), None)
        statuses = list(DB_STATUSES)

        if my_db and my_db.get("numbers"):
            st.caption(f"Total: **{len(my_db['numbers'])}** DB")
            for idx, item in enumerate(my_db["numbers"]):
                item_id = item.get("id") or f"legacy_{idx}"
                with st.container(border=True):
                    st.markdown(f"**{idx+1}.**")

                    st.caption("DB")
                    st.code(item["num"], language="text")

                    st.caption("Nama")
                    st.code(item.get("name") or "-", language="text")

                    st.caption("Status")
                    cur_status = item.get("status", "Belum Dicek")
                    curr = statuses.index(cur_status) if cur_status in statuses else 0
                    new_st = st.radio(
                        "Status", statuses, index=curr,
                        key=f"st_{item_id}", label_visibility="collapsed"
                    )
                    if new_st != cur_status:
                        item["status"] = new_st
                        save_key("databases.json")
                        st.rerun()
        elif my_db:
            st.info("Database Anda masih kosong. Hubungi admin untuk pengiriman DB.")
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
                size_mb = round(vid.size / (1024 * 1024), 2)
                st.caption(f"Ukuran: **{size_mb} MB** / 200 MB")
                if size_mb > 200:
                    st.error("File terlalu besar. Maksimal 200 MB.")
                    vid = None

            caption = st.text_input(
                "Caption Video (NomorDB:Nominal:NDP/RDP)",
                max_chars=100,
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
            if not caption:
                errors.append("Video harus memiliki Caption")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    with st.spinner(f"Mengupload video ({size_mb} MB)"):
                        key = worker.execute(
                            worker.upload_video_s3,
                            vid,
                            f"{user['uid']}_{int(now_wib().timestamp())}_{vid.name}"
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
                            "time": str(now_wib())
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
            size_mb = round(vid.size / (1024 * 1024), 2)
            st.caption(f"Ukuran: **{size_mb} MB** / 200 MB")
            if size_mb > 200:
                st.error("File terlalu besar. Maksimal 200 MB.")
                vid = None

        caption = st.text_input("Caption", max_chars=100, key="up_cap")

        if st.button("Upload", use_container_width=True, icon=":material/upload:"):
            if vid is None:
                st.error("Pilih video dulu!")
            elif not caption:
                st.error("Caption tidak boleh kosong")
            else:
                try:
                    with st.spinner(f"Mengupload {size_mb} MB..."):
                        key = worker.execute(
                            worker.upload_video_s3,
                            vid,
                            f"{user['uid']}_{int(now_wib().timestamp())}_{vid.name}"
                        )
                        if isinstance(key, Exception) or not str(key).startswith("videos/"):
                            raise Exception(str(key))

                        worker.data["reports"]["video"].append({
                            "user": user["name"],
                            "key": key,
                            "caption": caption,
                            "size_mb": size_mb,
                            "status": "pending",
                            "time": str(now_wib())
                        })
                        save_key("reports.json")
                    st.success("Video berhasil diupload!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Upload gagal: {e}")

    elif page == "Teks":
        st.header("Teks & Materi Kerja")

        if not worker.data["texts"]:
            st.info("Belum ada teks / materi dari Admin.")
        else:
            for t in worker.data["texts"]:
                with st.container(border=True):
                    st.subheader(f" {t['title']}")
                    if t.get("image_key"):
                        img_url = worker.media_link(t["image_key"])
                        if img_url:
                            st.image(img_url, use_container_width=True)
                            st.markdown(
                                f"<a href='{img_url}' target='_blank' "
                                f"style='display:inline-block;padding:6px 14px;"
                                f"background:linear-gradient(135deg,#1E40AF,#3B82F6);"
                                f"color:white;border-radius:8px;text-decoration:none;"
                                f"font-size:12px;font-weight:600;margin-bottom:8px;'>"
                                f"{svg('download', 12, 'white')} Download / Buka Foto</a>",
                                unsafe_allow_html=True
                            )
                    if t.get("content"):
                        st.code(t["content"], language="text")
                        st.caption(" *Klik ikon copy di pojok kanan atas kotak untuk menyalin teks.*")
