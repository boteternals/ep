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
# 0. KONFIGURASI HALAMAN & CSS (TEMA BIRU & MOBILE)
# ==========================================
st.set_page_config(
    page_title="ElangPintar",
    page_icon="https://cdn.aceimg.com/mD4NlOxLG.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS untuk menyembunyikan sidebar, membuat navigasi bawah, & mendesain card
st.markdown("""
<style>
    /* Sembunyikan sidebar default */
    [data-testid="collapsedControl"] {display: none;}
    [data-testid="stSidebar"] {display: none;}
    
    /* Sembunyikan menu Streamlit bawaan */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Desain Navigasi Bawah */
    div[data-testid="stRadio"] {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #FFFFFF;
        padding: 10px 20px;
        z-index: 9999;
        border-top: 1px solid #E0E0E0;
        box-shadow: 0px -2px 10px rgba(0,0,0,0.05);
        display: flex;
        justify-content: center;
    }
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: row !important;
        gap: 15px;
        overflow-x: auto;
    }
    div[data-testid="stRadio"] label {
        font-size: 14px;
        font-weight: 600;
    }
    /* Jarak aman di bawah konten agar tidak tertutup nav */
    .block-container { padding-bottom: 100px !important; }

    /* Desain Card Kustom */
    .profile-card {
        background: linear-gradient(135deg, #0052D4, #4364F7);
        border-radius: 20px;
        padding: 20px;
        color: white;
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0, 82, 212, 0.3);
    }
    .profile-avatar {
        width: 70px;
        height: 70px;
        border-radius: 50%;
        background-color: rgba(255,255,255,0.2);
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 30px;
        margin-right: 15px;
    }
    .profile-info h3 { margin: 0; font-size: 20px; font-weight: 700; color: white; }
    .profile-info p { margin: 5px 0 0 0; font-size: 14px; color: #E0E0E0; }
    
    .wallet-card {
        background: linear-gradient(135deg, #00B4DB, #0083B0);
        border-radius: 20px;
        padding: 25px 20px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0, 131, 176, 0.3);
    }
    .wallet-card h4 { margin: 0; font-size: 14px; font-weight: 500; opacity: 0.9; }
    .wallet-card h1 { margin: 10px 0 20px 0; font-size: 32px; font-weight: 700; }
    
    .list-item {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
        font-weight: 500;
        color: #333;
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
        uid = "".join(str(random.randint(0, 9)) for _ in range(16)) # 16 digit angka
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
    st.markdown("<h2 style='text-align: center; color: #0052D4;'>ElangPintar</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        uid = st.text_input("UID (16 Digit)")
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)
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

# Tampilkan Logo di Atas
st.markdown("<div style='text-align: center; margin-bottom: 20px;'><img src='https://cdn.aceimg.com/mD4NlOxLG.png' width='80'></div>", unsafe_allow_html=True)


# ==========================================
# 4. ROUTING NAVIGASI BAWAH
# ==========================================
if user["role"] == "admin":
    menu_options = ["Employee", "Payroll", "Analytic", "Report", "Akun"]
    page = st.radio("Nav", menu_options, horizontal=True, label_visibility="collapsed")
else:
    menu_options = ["Data", "Pengajuan", "Upload", "Teks", "Akun"]
    page = st.radio("Nav", menu_options, horizontal=True, label_visibility="collapsed")


# ==========================================
# 5. HALAMAN AKUN (DESAIN MOBILE)
# ==========================================
if page == "Akun":
    # 1. Profile Card
    st.markdown(f"""
    <div class="profile-card">
        <div class="profile-avatar">👤</div>
        <div class="profile-info">
            <h3>{user['name']}</h3>
            <p>UID: {user['uid']} 📋</p>
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

    # Tombol Withdraw diletakkan di luar card HTML agar bisa trigger Streamlit action
    if st.button("💸 Withdraw", use_container_width=True, type="primary"):
        st.session_state.show_withdraw = True
        
    # 3. List Menu
    st.markdown(f"""
    <div class="list-item">
        <span>📞 Telepon</span>
        <span style="color: #888;">Belum ada</span>
    </div>
    <div class="list-item">
        <span>🕒 Riwayat panggilan</span>
        <span style="color: #888;">></span>
    </div>
    <div class="list-item">
        <span>🔔 Notifikasi</span>
        <span style="color: #888;">></span>
    </div>
    <div class="list-item">
        <span>🟢 WhatsApp</span>
        <span style="color: #888;">Belum ada ⚠️</span>
    </div>
    <div class="list-item">
        <span>🔵 Telegram</span>
        <span style="color: #888;">@{user['name'].lower()} ></span>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("🚪 Keluar / Logout", use_container_width=True):
        del st.session_state.user
        st.rerun()

    # --- FORM WITHDRAW & REKENING (Muncul jika tombol Withdraw diklik) ---
    if st.session_state.get("show_withdraw", False):
        st.divider()
        st.subheader("🏦 Pengaturan Rekening & Withdraw")
        
        accounts = user.get("accounts", [])
        if not accounts:
            st.warning("⚠️ Anda belum memiliki rekening. Tambahkan dulu di bawah.")
        else:
            st.write("**Rekening Terdaftar:**")
            for i, a in enumerate(accounts):
                c1, c2 = st.columns([4, 1])
                c1.write(f"{i+1}. **{a['bank']}** — `{a['number']}` a.n. {a['name']}")
                if c2.button("🗑", key=f"delacc_{i}"):
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

        with st.expander("➕ Tambah Rekening Baru"):
            with st.form("add_account_form"):
                bank = st.text_input("Jenis Bank / E-Wallet (BCA, Dana, dll)")
                number = st.text_input("Nomor Rekening")
                holder = st.text_input("Nama Pemilik Rekening")
                if st.form_submit_button("Simpan Rekening"):
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
            if st.button("Generate Akun"):
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
                    status = "🚫 BANNED" if u["banned"] else "✅ AKTIF"
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
                if st.button("Berikan DB") and db_input:
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
            if st.button("Simpan Teks"):
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
                if c2.button("Tambah", key=f"add_{emp['uid']}"):
                    worker.data["payroll"][emp["name"]] = current + amount
                    worker.execute(worker.save_file, "payroll.json", worker.data["payroll"])
                    st.rerun()
                if c3.button("Reset", key=f"rst_{emp['uid']}"):
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
            st.subheader(f"⏳ Pending ({len(pending)})")
            for i, n in pending:
                with st.expander(f"{n['user']} — {n.get('count', 0)} item"):
                    st.code(n["data"])
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Approve", key=f"a_n_{i}"):
                        ndps[i]["status"] = "approved"
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                        st.rerun()
                    if c2.button("❌ Reject", key=f"r_n_{i}"):
                        ndps[i]["status"] = "rejected"
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                        st.rerun()
            
            st.subheader("📜 History")
            for n in [x for x in ndps if x.get("status", "pending") != "pending"]:
                badge = "✅" if n["status"] == "approved" else "❌"
                st.write(f"{badge} {n['user']} — {n.get('count', 0)} item")

        with tab_wd:
            wds = worker.data["reports"]["wd"]
            pending_wd = [(i, n) for i, n in enumerate(wds) if n.get("status", "pending") == "pending"]
            st.subheader(f"⏳ Pending ({len(pending_wd)})")
            for i, n in pending_wd:
                acc = n.get("account", {})
                with st.expander(f"{n['user']} — Rp {n['amount']:,}"):
                    st.write(f"🏦 {acc.get('bank','-')} — {acc.get('number','-')} a.n. {acc.get('name','-')}")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Approve", key=f"a_w_{i}"):
                        wds[i]["status"] = "approved"
                        worker.data["payroll"][n["user"]] = max(worker.data["payroll"].get(n["user"], 0) - n["amount"], 0)
                        worker.execute(worker.save_file, "payroll.json", worker.data["payroll"])
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                        st.rerun()
                    if c2.button("❌ Reject", key=f"r_w_{i}"):
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
        if st.button("Ajukan NDP", use_container_width=True):
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
        if st.button("Upload", use_container_width=True) and vid and caption:
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
        st.button("Copy Teks", on_click=lambda: st.toast("Teks disalin!"))
