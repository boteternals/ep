import streamlit as st
import boto3
import json
import hashlib
import uuid
import queue
import threading
import random
import re
from datetime import datetime
from botocore.exceptions import ClientError
from botocore.client import Config

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
    /* === BACKGROUND BLUE GRADIENT === */
    .stApp {
        background: radial-gradient(ellipse at top, #1E3A8A 0%, #0F172A 45%, #020617 100%);
    }
    
    /* Hide default UI */
    [data-testid="collapsedControl"] {display: none;}
    [data-testid="stSidebar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container { padding-bottom: 130px !important; padding-top: 2rem !important; }
    
    /* === TEXT & HEADERS === */
    h1, h2, h3, h4, h5, h6 { color: #E0F2FE !important; }
    .stMarkdown p, label { color: #CBD5E1; }
    
    /* === NAVIGATION BAR (BIRU GELAP GLOW) === */
    div[data-testid="stRadio"] {
        position: fixed;
        bottom: 0; left: 0; right: 0;
        background: linear-gradient(180deg, #0B132B 0%, #020617 100%);
        padding: 12px 5px 16px 5px;
        z-index: 9999;
        border-top: 1px solid #1E3A8A;
        box-shadow: 0 -8px 25px rgba(30, 64, 175, 0.35);
    }
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: row !important;
        justify-content: space-around;
        width: 100%;
        gap: 4px;
    }
    div[data-testid="stRadio"] label {
        flex: 1;
        text-align: center;
        margin: 0 !important;
        padding: 8px 4px 6px 4px !important;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        border-radius: 12px;
        transition: background 0.25s ease, transform 0.2s ease;
    }
    div[data-testid="stRadio"] label:hover {
        background: rgba(56, 189, 248, 0.08);
        transform: translateY(-1px);
    }
    div[data-testid="stRadio"] label::before {
        content: '';
        position: absolute;
        top: -1px;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 3px;
        background: linear-gradient(90deg, #3B82F6, #38BDF8);
        border-radius: 3px;
        transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 0 10px #38BDF8;
    }
    div[data-testid="stRadio"] label:has(input:checked)::before {
        width: 45%;
    }
    div[data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }
    div[data-testid="stRadio"] label p {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 4px;
        font-size: 10px !important;
        color: #64748B !important;
        margin: 0 !important;
        font-weight: 600 !important;
        transition: color 0.25s ease;
        line-height: 1.2;
    }
    div[data-testid="stRadio"] label img {
        width: 24px;
        height: 24px;
        margin: 0 !important;
        opacity: 0.6;
        transition: all 0.25s ease;
    }
    div[data-testid="stRadio"] label:has(input:checked) p {
        color: #38BDF8 !important;
    }
    div[data-testid="stRadio"] label:has(input:checked) img {
        opacity: 1;
        filter: invert(63%) sepia(54%) saturate(3282%) hue-rotate(177deg) brightness(99%) contrast(95%);
        transform: scale(1.12);
    }
    
    /* === BUTTONS (BLUE GRADIENT) === */
    .stButton > button {
        background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%);
        border: 1px solid #2563EB;
        color: white !important;
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.2s ease;
        box-shadow: 0 2px 10px rgba(59, 130, 246, 0.3);
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563EB 0%, #60A5FA 100%);
        box-shadow: 0 6px 18px rgba(59, 130, 246, 0.5);
        transform: translateY(-2px);
        border-color: #60A5FA;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0EA5E9 0%, #38BDF8 100%);
        box-shadow: 0 4px 16px rgba(56, 189, 248, 0.45);
    }
    
    /* === INPUTS === */
    .stTextInput input, .stTextArea textarea {
        background: #0F172A !important;
        border: 1px solid #1E3A8A !important;
        color: #E0F2FE !important;
        border-radius: 10px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
    }
    
    /* === TABS === */
    .stTabs [data-baseweb="tab-list"] {
        background: #0F172A;
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
        border: 1px solid #1E3A8A;
    }
    .stTabs [data-baseweb="tab"] {
        color: #64748B;
        border-radius: 8px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1E40AF, #3B82F6) !important;
        color: white !important;
    }
    
    /* === PROFILE CARD === */
    .profile-card {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        border-radius: 20px;
        padding: 20px;
        color: white;
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        box-shadow: 0 10px 28px rgba(59, 130, 246, 0.4);
        border: 1px solid rgba(96, 165, 250, 0.35);
    }
    .profile-avatar {
        width: 64px; height: 64px;
        border-radius: 50%;
        background: rgba(255,255,255,0.15);
        display: flex; justify-content: center; align-items: center;
        margin-right: 15px;
        border: 2px solid rgba(255,255,255,0.35);
        box-shadow: 0 0 15px rgba(96, 165, 250, 0.5);
    }
    .profile-info h3 { margin: 0; font-size: 20px; font-weight: 700; color: white !important; }
    .profile-info p { margin: 5px 0 0 0; font-size: 13px; color: rgba(255,255,255,0.85) !important; }
    
    /* === WALLET CARD (BALANCE) === */
    .wallet-card {
        background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 45%, #0EA5E9 100%);
        border-radius: 24px;
        padding: 22px 24px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 12px 32px rgba(59, 130, 246, 0.45), inset 0 1px 0 rgba(255,255,255,0.25);
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(96, 165, 250, 0.4);
    }
    .wallet-card::before {
        content: '';
        position: absolute;
        top: -60%; right: -20%;
        width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 55%);
        pointer-events: none;
    }
    .wallet-card::after {
        content: '';
        position: absolute;
        bottom: -40%; left: -20%;
        width: 150%; height: 150%;
        background: radial-gradient(circle, rgba(14, 165, 233, 0.3) 0%, transparent 60%);
        pointer-events: none;
    }
    .wallet-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        opacity: 0.95;
        font-weight: 500;
        margin-bottom: 4px;
        position: relative;
        z-index: 1;
    }
    .wallet-balance {
        font-size: 34px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 10px 0 6px 0;
        text-shadow: 0 3px 10px rgba(0,0,0,0.25);
        position: relative;
        z-index: 1;
    }
    .wallet-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        opacity: 0.92;
        margin-top: 14px;
        padding-top: 12px;
        border-top: 1px solid rgba(255,255,255,0.28);
        position: relative;
        z-index: 1;
    }
    .wallet-badge {
        background: rgba(255,255,255,0.22);
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        backdrop-filter: blur(6px);
    }
    
    /* === LIST ITEM === */
    .list-item {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 14px 16px;
        border-radius: 14px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 10px rgba(0,0,0,0.35);
        font-weight: 500;
        color: #F8FAFC;
        border: 1px solid #1E3A8A;
        transition: all 0.25s ease;
    }
    .list-item:hover {
        border-color: #3B82F6;
        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.25);
        transform: translateY(-1px);
    }
    .list-item-left { display: flex; align-items: center; gap: 12px; }
    
    /* === BADGE === */
    .notif-badge {
        background: linear-gradient(135deg, #EF4444, #DC2626);
        color: white;
        font-size: 10px;
        padding: 2px 8px;
        border-radius: 10px;
        font-weight: 700;
        margin-left: 8px;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.5);
        animation: pulse-badge 1.5s ease-in-out infinite;
    }
    @keyframes pulse-badge {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 1. S3 WORKER + QUEUE (ASYNC SAVES)
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
                "s3",
                endpoint_url=endpoint_url,
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
                "reports": self._load("reports.json", {"ndp": [], "wd": [], "video": []})
            }
            self.last_reset_date = datetime.now().date()

            admin_uid = st.secrets.get("ADMIN_UID", "admin")
            admin_pwd = st.secrets.get("ADMIN_PASSWORD", "admin123")

            if not self.data["users"]:
                self.data["users"].append({
                    "uid": admin_uid, "pass_hash": self.hash_pwd(admin_pwd),
                    "name": "Administrator", "role": "admin",
                    "banned": False, "accounts": [], "telegram": ""
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
                    self._save("databases.json", [])
                    self._save("texts.json", {"content": ""})
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
            """Sinkron — tunggu hasil (dipakai hanya kalau perlu)."""
            res_q = queue.Queue()
            self.q.put((func, args, kwargs, res_q))
            return res_q.get()

        def execute_async(self, func, *args, **kwargs):
            """Async — fire & forget, UI tetap smooth tanpa lag."""
            self.q.put((func, args, kwargs, None))

        def save_file(self, key, data):
            self.data[key.replace(".json", "")] = data
            self._save(key, data)
            return True

        def upload_file_s3(self, file_bytes, filename):
            self.s3.put_object(Bucket=self.bucket, Key=f"uploads/{filename}", Body=file_bytes)
            return True

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
    st.markdown("<div style='text-align: center; margin-bottom: 10px; filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.6));'><img src='https://cdn.aceimg.com/mD4NlOxLG.png' width='100'></div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: #38BDF8;'>ElangPintar</h2>", unsafe_allow_html=True)
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
                    st.rerun()
            else:
                st.error("UID atau Password salah.")

if "user" not in st.session_state:
    login_page()
    st.stop()

user = next((u for u in worker.data["users"] if u["uid"] == st.session_state.user["uid"]), st.session_state.user)
st.session_state.user = user

st.markdown("<div style='text-align: center; margin-bottom: 20px; filter: drop-shadow(0 0 15px rgba(59, 130, 246, 0.6));'><img src='https://cdn.aceimg.com/mD4NlOxLG.png' width='70'></div>", unsafe_allow_html=True)


# ==========================================
# 4. ROUTING NAVIGASI BAWAH
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
            "Payroll": nav_icon("wallet", "Gaji"),
            "Analytic": nav_icon("chart-line-up", "Analitik"),
            "Report": nav_icon("file-text", "Laporan"),
            "Akun": nav_icon("user", "Akun")
        }[x]
    )
else:
    unread_count = sum(1 for n in user.get("notifications", []) if not n.get("read", False))
    data_label = f"Data{' ●' if unread_count else ''}"
    menu_options = ["Data", "Pengajuan", "Upload", "Teks", "Akun"]
    page = st.radio(
        "Nav", menu_options, horizontal=True, label_visibility="collapsed",
        format_func=lambda x: {
            "Data": nav_icon("database", data_label),
            "Pengajuan": nav_icon("file-plus", "NDP"),
            "Upload": nav_icon("upload-simple", "Upload"),
            "Teks": nav_icon("text-align-left", "Teks"),
            "Akun": nav_icon("user", "Akun")
        }[x]
    )


# ==========================================
# 5. HALAMAN AKUN
# ==========================================
if page == "Akun":
    # Profile Card
    st.markdown(f"""
    <div class="profile-card">
        <div class="profile-avatar">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
            </svg>
        </div>
        <div class="profile-info">
            <h3>{user['name']}</h3>
            <p>UID: {user['uid']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Wallet Card
    my_payroll = worker.data["payroll"].get(user["name"], 0)
    pending_wd = sum(
        r["amount"] for r in worker.data["reports"]["wd"]
        if r["user"] == user["name"] and r.get("status", "pending") == "pending"
    )
    available = max(my_payroll - pending_wd, 0)

    st.markdown(f"""
    <div class="wallet-card">
        <div class="wallet-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="2" y="6" width="20" height="12" rx="2"></rect>
                <path d="M2 10h20"></path>
                <circle cx="16" cy="14" r="1.5" fill="currentColor"></circle>
            </svg>
            <span>Dompet Elang</span>
        </div>
        <div class="wallet-balance">{fmt_rp(my_payroll)}</div>
        <div class="wallet-footer">
            <span>Tersedia: <b>{fmt_rp(available)}</b></span>
            <span class="wallet-badge">● Aktif</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Withdraw", use_container_width=True, type="primary", icon=":material/account_balance_wallet:"):
        st.session_state.show_withdraw = not st.session_state.get("show_withdraw", False)

    # Telegram value
    tg_raw = user.get("telegram", "").strip().lstrip("@")
    tg_display = f"@{tg_raw}" if tg_raw else "Belum diatur ⚠️"
    tg_color = "#22C55E" if tg_raw else "#F59E0B"

    st.markdown(f"""
    <div class="list-item">
        <div class="list-item-left">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
            <span>Telepon</span>
        </div>
        <span style="color: #64748B;">Belum ada</span>
    </div>
    <div class="list-item">
        <div class="list-item-left">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            <span>Riwayat panggilan</span>
        </div>
        <span style="color: #64748B;">></span>
    </div>
    <div class="list-item">
        <div class="list-item-left">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
            <span>Notifikasi</span>
        </div>
        <span style="color: #64748B;">></span>
    </div>
    <div class="list-item">
        <div class="list-item-left">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22C55E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
            <span>WhatsApp</span>
        </div>
        <span style="color: #F59E0B;">Belum ada ⚠️</span>
    </div>
    <div class="list-item">
        <div class="list-item-left">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            <span>Telegram</span>
        </div>
        <span style="color: {tg_color};">{tg_display} ></span>
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    # === PENGATURAN AKUN ===
    with st.expander("⚙️ Pengaturan Akun", expanded=False):
        with st.form("settings_form"):
            st.write("**Ubah Username & Telegram**")
            new_name = st.text_input("Username Akun", value=user.get("name", ""), max_chars=50)
            new_telegram = st.text_input("Username Telegram", value=user.get("telegram", "").lstrip("@"), placeholder="username_tanpa_@")
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
                        for r in worker.data["reports"]["ndp"]:
                            if r["user"] == old_name: r["user"] = new_name_clean
                        for r in worker.data["reports"]["wd"]:
                            if r["user"] == old_name: r["user"] = new_name_clean
                        for r in worker.data["reports"]["video"]:
                            if r["user"] == old_name: r["user"] = new_name_clean
                        save_key("databases.json")
                        save_key("payroll.json")
                        save_key("reports.json")

                    save_users()
                    st.toast("✅ Profil berhasil diperbarui!")
                    st.rerun()

    if st.button("Keluar / Logout", use_container_width=True, icon=":material/logout:"):
        del st.session_state.user
        st.rerun()

    # === WITHDRAW & REKENING ===
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
            st.caption("🔐 Kelola, ban, atau hapus akun karyawan.")
            for u in list(worker.data["users"]):
                if u["role"] == "karyawan":
                    with st.expander(f"{'🔴' if u['banned'] else '🟢'} **{u['name']}** · `{u['uid']}`"):
                        st.write(f"Status: {'BANNED' if u['banned'] else 'AKTIF'}")
                        c1, c2 = st.columns(2)
                        if c1.button("Unban" if u["banned"] else "Ban", key=f"ban_{u['uid']}", use_container_width=True):
                            u["banned"] = not u["banned"]
                            save_users()
                            st.rerun()
                        if c2.button("Hapus Akun", key=f"del_{u['uid']}", use_container_width=True, icon=":material/delete:"):
                            st.session_state.confirm_delete = u["uid"]

                        if st.session_state.get("confirm_delete") == u["uid"]:
                            st.error(f"⚠️ Hapus permanen **{u['name']}** beserta semua datanya?")
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
                st.info("🔒 **Pengiriman Privat** — Database hanya bisa dilihat oleh karyawan yang dipilih.")
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
                            "message": f"📥 Anda menerima {len(nums)} database baru dari admin",
                            "read": False,
                            "time": str(datetime.now())
                        })
                        save_users()
                    save_key("databases.json")
                    st.success(f"✅ {len(nums)} DB dikirim **secara privat** ke {target}.")
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
            ndp_approved = [r for r in worker.data["reports"]["ndp"] if r["user"] == selected and r.get("status") == "approved"]
            total_ndp = sum(r.get("count", 0) for r in ndp_approved)
            my_db = next((d for d in worker.data["databases"] if d["name"] == selected), None)
            if my_db:
                total_db = len(my_db["numbers"])
                done_db = sum(1 for n in my_db["numbers"] if n["status"] != "Tidak Terdaftar")
                dibalas_db = sum(1 for n in my_db["numbers"] if n["status"] == "Dibalas")
            else:
                total_db = done_db = dibalas_db = 0
            pct = (dibalas_db / total_ndp * 100) if total_ndp > 0 else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("NDP Diterima", total_ndp)
            c2.metric("DB Dikerjakan", f"{done_db}/{total_db}")
            c3.metric("Persentase", f"{pct:.1f}%")
            if my_db:
                st.write("**Rincian Status:**")
                counts = {}
                for n in my_db["numbers"]:
                    counts[n["status"]] = counts.get(n["status"], 0) + 1
                for s, c in counts.items():
                    st.write(f"- {s}: {c}")

    elif page == "Report":
        st.header("Laporan & Approval")
        tab_ndp, tab_wd = st.tabs(["NDP", "Withdraw"])
        with tab_ndp:
            ndps = worker.data["reports"]["ndp"]
            pending = [(i, n) for i, n in enumerate(ndps) if n.get("status", "pending") == "pending"]
            st.subheader(f"Pending ({len(pending)})")
            for i, n in pending:
                with st.expander(f"{n['user']} — {n.get('count', 0)} item"):
                    st.code(n["data"])
                    c1, c2 = st.columns(2)
                    if c1.button("Approve", key=f"a_n_{i}", icon=":material/check_circle:"):
                        ndps[i]["status"] = "approved"
                        save_key("reports.json")
                        st.rerun()
                    if c2.button("Reject", key=f"r_n_{i}", icon=":material/cancel:"):
                        ndps[i]["status"] = "rejected"
                        save_key("reports.json")
                        st.rerun()
            st.subheader("History")
            for n in [x for x in ndps if x.get("status", "pending") != "pending"]:
                badge = "APPROVED" if n["status"] == "approved" else "REJECTED"
                st.write(f"[{badge}] {n['user']} — {n.get('count', 0)} item")

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
                        worker.data["payroll"][n["user"]] = max(worker.data["payroll"].get(n["user"], 0) - n["amount"], 0)
                        save_key("payroll.json")
                        save_key("reports.json")
                        st.rerun()
                    if c2.button("Reject", key=f"r_w_{i}", icon=":material/cancel:"):
                        wds[i]["status"] = "rejected"
                        save_key("reports.json")
                        st.rerun()


# ==========================================
# 7. HALAMAN KARYAWAN
# ==========================================
else:
    if page == "Data":
        st.header("🔒 Database Kerja Saya")
        st.caption("Data ini privat — hanya Anda yang bisa melihat.")

        unread = [n for n in user.get("notifications", []) if not n.get("read", False)]
        if unread:
            with st.container(border=True):
                st.markdown(f"📬 **{len(unread)} notifikasi baru dari admin**")
                for n in unread:
                    st.write(f"• {n['message']}")
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
                    new_st = st.selectbox("Status", statuses, index=curr, key=f"st_{i}", label_visibility="collapsed")
                    if new_st != item["status"]:
                        item["status"] = new_st
                        save_key("databases.json")
                        st.rerun()
        else:
            st.warning("Belum ada database. Admin akan mengirim via private.")

    elif page == "Pengajuan":
        st.header("Pengajuan NDP")
        ndp_input = st.text_area("Masukkan Database (koma/enter)")
        preview = count_items(ndp_input)
        st.caption(f"Terdeteksi **{preview}** item")
        if st.button("Ajukan NDP", use_container_width=True, icon=":material/send:"):
            if ndp_input.strip():
                worker.data["reports"]["ndp"].append({
                    "user": user["name"], "data": ndp_input, "count": preview,
                    "status": "pending", "time": str(datetime.now())
                })
                save_key("reports.json")
                st.success("Pengajuan dikirim!")
                st.rerun()

    elif page == "Upload":
        st.header("Upload Video")
        vid = st.file_uploader("Pilih Video", type=["mp4", "mov"])
        caption = st.text_input("Caption (1-10)")
        if st.button("Upload", use_container_width=True, icon=":material/upload:") and vid and caption:
            with st.spinner("Mengupload..."):
                filename = f"{user['uid']}_{datetime.now().timestamp()}_{vid.name}"
                worker.execute(worker.upload_file_s3, vid.getvalue(), filename)
                worker.data["reports"]["video"].append({"user": user["name"], "file": filename, "caption": caption})
                save_key("reports.json")
            st.success("Video berhasil diupload!")

    elif page == "Teks":
        st.header("Teks Kerja")
        text_content = worker.data["texts"].get("content", "Belum ada teks.")
        st.code(text_content)
        st.button("Copy Teks", icon=":material/content_copy:", on_click=lambda: st.toast("Teks disalin!"))
