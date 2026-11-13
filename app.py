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
# 0. KONFIGURASI HALAMAN & CSS (TEMA BIRU)
# ==========================================
st.set_page_config(
    page_title="ElangPintar",
    page_icon="https://cdn.aceimg.com/mD4NlOxLG.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    /* Sembunyikan sidebar default & menu Streamlit */
    [data-testid="collapsedControl"] {display: none;}
    [data-testid="stSidebar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Jarak aman di bawah konten agar tidak tertutup nav */
    .block-container { padding-bottom: 120px !important; padding-top: 2rem !important; }

    /* =======================================
       DESAIN NAVIGASI BAWAH (BIRU GELAP)
       ======================================= */
    div[data-testid="stRadio"] {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #0B132B;
        padding: 10px 5px;
        z-index: 9999;
        border-top: 1px solid #1C2541;
        box-shadow: 0px -4px 15px rgba(0,0,0,0.4);
        display: flex;
        justify-content: center;
    }
    
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: row !important;
        justify-content: space-around;
        width: 100%;
        gap: 0;
    }

    div[data-testid="stRadio"] label {
        flex: 1;
        text-align: center;
        margin: 0 !important;
        padding: 0 !important;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    /* Sembunyikan lingkaran radio bawaan */
    div[data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }

    /* Teks & Gambar Navigasi */
    div[data-testid="stRadio"] label p {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 4px;
        font-size: 10px !important;
        color: #8A99AD !important;
        margin: 0 !important;
        font-weight: 600 !important;
        transition: color 0.2s ease;
        line-height: 1.2;
    }

    div[data-testid="stRadio"] label img {
        width: 24px;
        height: 24px;
        margin: 0 !important;
        opacity: 0.7;
        transition: all 0.2s ease;
    }

    /* State Aktif (Biru Terang) */
    div[data-testid="stRadio"] label:has(input:checked) p {
        color: #38BDF8 !important;
    }

    /* Filter CSS untuk mengubah SVG abu-abu menjadi Biru Terang saat aktif */
    div[data-testid="stRadio"] label:has(input:checked) img {
        opacity: 1;
        filter: invert(63%) sepia(54%) saturate(3282%) hue-rotate(177deg) brightness(99%) contrast(95%);
    }

    /* =======================================
       DESAIN CARD KUSTOM
       ======================================= */
    .profile-card {
        background: linear-gradient(135deg, #1E3A8A, #3B82F6);
        border-radius: 20px;
        padding: 20px;
        color: white;
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }
    .profile-avatar {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        background-color: rgba(255,255,255,0.15);
        display: flex;
        justify-content: center;
        align-items: center;
        margin-right: 15px;
    }
    .profile-info h3 { margin: 0; font-size: 20px; font-weight: 700; color: white; }
    .profile-info p { margin: 5px 0 0 0; font-size: 14px; color: #E0E0E0; }
    
    .wallet-card {
        background: linear-gradient(135deg, #0EA5E9, #0284C7);
        border-radius: 20px;
        padding: 25px 20px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(2, 132, 199, 0.3);
    }
    .wallet-card h4 { margin: 0; font-size: 14px; font-weight: 500; opacity: 0.9; }
    .wallet-card h1 { margin: 10px 0 20px 0; font-size: 32px; font-weight: 700; }
    
    .list-item {
        background-color: #1E293B;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        font-weight: 500;
        color: #F8FAFC;
        border: 1px solid #334155;
    }
    .list-item-left {
        display: flex; 
        align-items: center; 
        gap: 12px;
    }
</style>
""", unsafe_allow_html=True)


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
                    "banned": False, "accounts": []
                })
                self._save("users.json", self.data["users"])
            else:
                for u in self.data["users"]:
                    if u["uid"] == admin_uid and u["role"] == "admin":
                        if u["pass_hash"] != self.hash_pwd(admin_pwd):
                            u["pass_hash"] = self.hash_pwd(admin_pwd)
                            self._save("users.json", self.data["users"])
                        if "accounts" not in u:
                            u["accounts"] = []
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
                    result_queue.put(func(*args, **kwargs))
                except Exception as e:
                    result_queue.put(e)
                finally:
                    self.q.task_done()

        def execute(self, func, *args, **kwargs):
            res_q = queue.Queue()
            self.q.put((func, args, kwargs, res_q))
            return res_q.get()

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

def save_users():
    worker.execute(worker.save_file, "users.json", worker.data["users"])

# ==========================================
# 3. AUTENTIKASI
# ==========================================
def login_page():
    st.markdown("<div style='text-align: center;'><img src='https://cdn.aceimg.com/mD4NlOxLG.png' width='100'></div>", unsafe_allow_html=True)
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

# Ambil data user terbaru dari memory
user = next((u for u in worker.data["users"] if u["uid"] == st.session_state.user["uid"]), st.session_state.user)
st.session_state.user = user

# Tampilkan Logo di Atas Halaman
st.markdown("<div style='text-align: center; margin-bottom: 20px;'><img src='https://cdn.aceimg.com/mD4NlOxLG.png' width='70'></div>", unsafe_allow_html=True)


# ==========================================
# 4. ROUTING NAVIGASI BAWAH (SVG VIA ICONIFY)
# ==========================================
# Fungsi bantuan untuk men-generate string Markdown SVG
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
    menu_options = ["Data", "Pengajuan", "Upload", "Teks", "Akun"]
    page = st.radio(
        "Nav", menu_options, horizontal=True, label_visibility="collapsed",
        format_func=lambda x: {
            "Data": nav_icon("database", "Data"),
            "Pengajuan": nav_icon("file-plus", "NDP"),
            "Upload": nav_icon("upload-simple", "Upload"),
            "Teks": nav_icon("text-align-left", "Teks"),
            "Akun": nav_icon("user", "Akun")
        }[x]
    )


# ==========================================
# 5. HALAMAN AKUN (DESAIN MOBILE)
# ==========================================
if page == "Akun":
    # 1. Profile Card (SVG User)
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

    # 2. Wallet Card
    my_payroll = worker.data["payroll"].get(user["name"], 0)
    st.markdown(f"""
    <div class="wallet-card">
        <h4>Dompet Kucing</h4>
        <h1>Rp {my_payroll:,}</h1>
    </div>
    """, unsafe_allow_html=True)

    # Tombol Withdraw
    if st.button("Withdraw", use_container_width=True, type="primary", icon=":material/account_balance_wallet:"):
        st.session_state.show_withdraw = not st.session_state.get("show_withdraw", False)
        
    # 3. List Menu (SVG Icons)
    # SVG: Phone, Clock, Bell, WhatsApp, Telegram
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
        <span style="color: #64748B;">@{user['name'].lower().replace(' ', '')} ></span>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("Keluar / Logout", use_container_width=True, icon=":material/logout:"):
        del st.session_state.user
        st.rerun()

    # --- FORM WITHDRAW & REKENING ---
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

            pending_wd = sum(
                r["amount"] for r in worker.data["reports"]["wd"]
                if r["user"] == user["name"] and r.get("status", "pending") == "pending"
            )
            available = max(my_payroll - pending_wd, 0)
            st.info(f"Saldo Tersedia: **Rp {available:,}** (Pending: Rp {pending_wd:,})")

            labels = [f"{a['bank']} - {a['number']}" for a in accounts]
            sel = st.selectbox("Pilih Rekening Tujuan", range(len(accounts)), format_func=lambda i: labels[i])
            
            if st.button("Ajukan Withdraw", type="primary", use_container_width=True):
                if available <= 0:
                    st.error("Tidak ada saldo yang bisa ditarik.")
                else:
                    worker.data["reports"]["wd"].append({
                        "user": user["name"],
                        "amount": available,
                        "account": accounts[sel],
                        "status": "pending",
                        "time": str(datetime.now())
                    })
                    worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                    st.success(f"Pengajuan withdraw Rp {available:,} terkirim!")
                    st.session_state.show_withdraw = False
                    st.rerun()

        with st.expander("Tambah Rekening Baru"):
            with st.form("add_account_form"):
                bank = st.text_input("Jenis Bank / E-Wallet (BCA, Dana, dll)")
                number = st.text_input("Nomor Rekening")
                holder = st.text_input("Nama Pemilik Rekening")
                if st.form_submit_button("Simpan Rekening", icon=":material/save:"):
                    if bank and number and holder:
                        if "accounts" not in user: user["accounts"] = []
                        user["accounts"].append({"bank": bank, "number": number, "name": holder})
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
                        "name": name, "role": "karyawan", "banned": False, "accounts": []
                    })
                    save_users()
                    st.success("Akun berhasil dibuat!")
                    st.code(f"UID      : {new_uid}\nPassword : {new_pwd}")
        
        with tab2:
            for u in worker.data["users"]:
                if u["role"] == "karyawan":
                    col1, col2 = st.columns([4, 1])
                    status = "BANNED" if u["banned"] else "AKTIF"
                    col1.write(f"**{u['name']}** (`{u['uid']}`) - {status}")
                    if col2.button("Unban" if u["banned"] else "Ban", key=f"ban_{u['uid']}"):
                        u["banned"] = not u["banned"]
                        save_users()
                        st.rerun()
                        
        with tab3:
            karyawan_list = [u["name"] for u in worker.data["users"] if u["role"] == "karyawan"]
            if karyawan_list:
                target = st.selectbox("Pilih Karyawan", karyawan_list)
                db_input = st.text_area("Input Database (pisahkan dengan koma/enter)")
                if st.button("Berikan DB", icon=":material/database:") and db_input:
                    nums = [n.strip() for n in re.split(r"[,\n\r;]+", db_input) if n.strip()]
                    worker.data["databases"] = [d for d in worker.data["databases"] if d["name"] != target]
                    worker.data["databases"].append({
                        "name": target,
                        "numbers": [{"num": n, "status": "Tidak Terdaftar"} for n in nums]
                    })
                    worker.execute(worker.save_file, "databases.json", worker.data["databases"])
                    st.success(f"{len(nums)} Database diberikan ke {target}.")
            else:
                st.info("Belum ada karyawan.")
                
        with tab4:
            text_in = st.text_area("Teks Kerja Harian")
            if st.button("Simpan Teks", icon=":material/save:"):
                worker.data["texts"] = {"content": text_in}
                worker.execute(worker.save_file, "texts.json", worker.data["texts"])
                st.success("Teks disimpan!")

    elif page == "Payroll":
        st.header("Manajemen Payroll")
        employees = [u for u in worker.data["users"] if u["role"] == "karyawan"]
        if not employees:
            st.info("Belum ada karyawan.")
        else:
            for emp in employees:
                current = worker.data["payroll"].get(emp["name"], 0)
                st.markdown(f"**{emp['name']}** — Saldo: **Rp {current:,}**")
                c1, c2, c3 = st.columns([2, 1, 1])
                amount = c1.number_input("Nominal", min_value=0, step=10000, key=f"amt_{emp['uid']}")
                if c2.button("Tambah", key=f"add_{emp['uid']}", icon=":material/add:"):
                    worker.data["payroll"][emp["name"]] = current + amount
                    worker.execute(worker.save_file, "payroll.json", worker.data["payroll"])
                    st.rerun()
                if c3.button("Reset", key=f"rst_{emp['uid']}", icon=":material/restart_alt:"):
                    worker.data["payroll"][emp["name"]] = 0
                    worker.execute(worker.save_file, "payroll.json", worker.data["payroll"])
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
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                        st.rerun()
                    if c2.button("Reject", key=f"r_n_{i}", icon=":material/cancel:"):
                        ndps[i]["status"] = "rejected"
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
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
                with st.expander(f"{n['user']} — Rp {n['amount']:,}"):
                    st.write(f"{acc.get('bank','-')} — {acc.get('number','-')} a.n. {acc.get('name','-')}")
                    c1, c2 = st.columns(2)
                    if c1.button("Approve", key=f"a_w_{i}", icon=":material/check_circle:"):
                        wds[i]["status"] = "approved"
                        worker.data["payroll"][n["user"]] = max(worker.data["payroll"].get(n["user"], 0) - n["amount"], 0)
                        worker.execute(worker.save_file, "payroll.json", worker.data["payroll"])
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                        st.rerun()
                    if c2.button("Reject", key=f"r_w_{i}", icon=":material/cancel:"):
                        wds[i]["status"] = "rejected"
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                        st.rerun()

# ==========================================
# 7. HALAMAN KARYAWAN (SELAIN AKUN)
# ==========================================
else:
    if page == "Data":
        st.header("Database Kerja Saya")
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
                        worker.execute(worker.save_file, "databases.json", worker.data["databases"])
                        st.rerun()
        else:
            st.warning("Belum ada database hari ini.")

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
                worker.execute(worker.save_file, "reports.json", worker.data["reports"])
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
                worker.execute(worker.save_file, "reports.json", worker.data["reports"])
            st.success("Video berhasil diupload!")

    elif page == "Teks":
        st.header("Teks Kerja")
        text_content = worker.data["texts"].get("content", "Belum ada teks.")
        st.code(text_content)
        st.button("Copy Teks", icon=":material/content_copy:", on_click=lambda: st.toast("Teks disalin!"))
