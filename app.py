import streamlit as st
import boto3
import json
import hashlib
import uuid
import queue
import threading
from datetime import datetime
from botocore.exceptions import ClientError

# ==========================================
# 1. MANAJER S3 & QUEUE (ANTI-COLLISION)
# ==========================================
@st.cache_resource
def get_worker():
    """Membuat Worker tunggal yang berjalan di background thread."""
    class S3Worker:
        def __init__(self):
            # Koneksi S3 dengan Endpoint yang benar
            self.s3 = boto3.client(
                's3',
                endpoint_url=st.secrets["S3_ENDPOINT_URL"],
                aws_access_key_id=st.secrets["S3_ACCESS_KEY_ID"],
                aws_secret_access_key=st.secrets["S3_SECRET_ACCESS_KEY"]
            )
            self.bucket = st.secrets["S3_BUCKET_NAME"]
            
            # Antrian untuk mencegah tabrakan data (Queue System)
            self.q = queue.Queue()
            
            # Cache data lokal di memori server (RAM)
            self.data = {
                "users": self._load("users.json", []),
                "databases": self._load("databases.json", []),
                "texts": self._load("texts.json", {"content": ""}),
                "payroll": self._load("payroll.json", {}),
                "reports": self._load("reports.json", {"ndp": [], "wd": [], "video": []})
            }
            
            self.last_reset_date = datetime.now().date()
            
            # --- INISIALISASI ADMIN DARI SECRETS ---
            admin_uid = st.secrets.get("ADMIN_UID", "admin")
            admin_pwd = st.secrets.get("ADMIN_PASSWORD", "admin123")
            
            if not self.data["users"]:
                # Database kosong, buat admin pertama kali
                admin_hash = self.hash_pwd(admin_pwd)
                self.data["users"].append({
                    "uid": admin_uid, 
                    "pass_hash": admin_hash, 
                    "name": "Administrator", 
                    "role": "admin", 
                    "banned": False
                })
                self._save("users.json", self.data["users"])
            else:
                # Pastikan admin ada dan password sinkron dengan secrets
                admin_found = False
                for u in self.data["users"]:
                    if u["uid"] == admin_uid and u["role"] == "admin":
                        admin_found = True
                        # Jika password di secrets diubah, update hash di database
                        if u["pass_hash"] != self.hash_pwd(admin_pwd):
                            u["pass_hash"] = self.hash_pwd(admin_pwd)
                            self._save("users.json", self.data["users"])
                        break
                
                if not admin_found:
                    # Jika admin tidak ada di DB (misal terhapus manual), buat ulang
                    admin_hash = self.hash_pwd(admin_pwd)
                    self.data["users"].append({
                        "uid": admin_uid, 
                        "pass_hash": admin_hash, 
                        "name": "Administrator", 
                        "role": "admin", 
                        "banned": False
                    })
                    self._save("users.json", self.data["users"])

            # Mulai background thread untuk memproses antrian
            self.thread = threading.Thread(target=self._process_queue, daemon=True)
            self.thread.start()

        def hash_pwd(self, pwd):
            # Pengganti bcrypt menggunakan SHA256 dengan salt statis
            salt = "elangpintar_secret_salt_2024"
            return hashlib.sha256(f"{salt}{pwd}".encode()).hexdigest()

        def _load(self, key, default):
            try:
                obj = self.s3.get_object(Bucket=self.bucket, Key=key)
                return json.loads(obj['Body'].read().decode('utf-8'))
            except (ClientError, self.s3.exceptions.NoSuchKey):
                # Jika file belum ada di S3, buat dengan default
                self._save(key, default)
                return default
            except Exception:
                return default

        def _save(self, key, data):
            # Fungsi dasar upload ke S3
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(data).encode('utf-8'),
                ContentType='application/json'
            )

        def _process_queue(self):
            """Looping abadi di background thread untuk memproses antrian satu per satu."""
            while True:
                task = self.q.get()
                if task is None: break
                
                func, args, kwargs, result_queue = task
                
                # Cek Reset Harian (00.00) setiap ada tugas masuk
                today = datetime.now().date()
                if self.last_reset_date != today:
                    self.data["databases"] = []
                    self.data["texts"] = {"content": ""}
                    self._save("databases.json", [])
                    self._save("texts.json", {"content": ""})
                    self.last_reset_date = today

                try:
                    # Eksekusi tugas (Baca/Ubah/Simpan)
                    res = func(*args, **kwargs)
                    result_queue.put(res) # Kembalikan hasil ke UI
                except Exception as e:
                    result_queue.put(e)
                finally:
                    self.q.task_done()

        def execute(self, func, *args, **kwargs):
            """Menambahkan tugas ke antrian dan menunggu hasilnya (Blocking)."""
            res_q = queue.Queue()
            self.q.put((func, args, kwargs, res_q))
            # Menunggu sampai background thread selesai memproses tugas ini
            return res_q.get() 

        # --- Fungsi Bisnis yang akan dimasukkan ke Queue ---
        def save_file(self, key, data):
            self.data[key.replace('.json', '')] = data
            self._save(key, data)
            return True

        def upload_file_s3(self, file_bytes, filename):
            self.s3.put_object(Bucket=self.bucket, Key=f"uploads/{filename}", Body=file_bytes)
            return True

    return S3Worker()

worker = get_worker()

# ==========================================
# 2. AUTENTIKASI (LOGIN)
# ==========================================
def login_page():
    st.title("Login ElangPintar")
    with st.form("login_form"):
        uid = st.text_input("UID")
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            user = next((u for u in worker.data["users"] if u["uid"] == uid), None)
            if user and user["pass_hash"] == worker.hash_pwd(pwd):
                if user["banned"]:
                    st.error("Akun Anda telah dibanned oleh Admin.")
                else:
                    st.session_state.user = user
                    st.rerun()
            else:
                st.error("UID atau Password salah.")

if "user" not in st.session_state:
    login_page()
    st.stop()

user = st.session_state.user

# ==========================================
# 3. UI DASHBOARD
# ==========================================
st.sidebar.title(f"Halo, {user['name']}")
st.sidebar.write(f"Role: {user['role'].title()}")

if st.sidebar.button("Logout"):
    del st.session_state.user
    st.rerun()

if user["role"] == "admin":
    page = st.sidebar.radio("Menu Admin", ["Employee", "Payroll", "Analytic", "Report"])
    
    if page == "Employee":
        st.header("Manajemen Karyawan")
        tab1, tab2, tab3, tab4 = st.tabs(["Buat Akun", "Kelola Akun", "GiveDB", "SetText"])
        
        with tab1:
            name = st.text_input("Nama Karyawan Baru")
            if st.button("Generate Akun"):
                if name:
                    new_uid = str(uuid.uuid4())[:6]
                    new_pwd = str(uuid.uuid4())[:6]
                    new_user = {"uid": new_uid, "pass_hash": worker.hash_pwd(new_pwd), "name": name, "role": "karyawan", "banned": False}
                    
                    # Tambahkan ke memori lokal dulu untuk UI responsif
                    worker.data["users"].append(new_user)
                    # Kirim ke antrian S3 (Anti-Collision)
                    with st.spinner("Menyimpan ke S3..."):
                        worker.execute(worker.save_file, "users.json", worker.data["users"])
                    
                    st.success(f"Akun dibuat! UID: `{new_uid}` | Password: `{new_pwd}`")

        with tab2:
            for u in worker.data["users"]:
                if u["role"] == "karyawan":
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"**{u['name']}** (UID: {u['uid']})")
                    btn_label = "Unban" if u["banned"] else "Ban"
                    if col2.button(btn_label, key=f"ban_{u['uid']}"):
                        u["banned"] = not u["banned"]
                        worker.execute(worker.save_file, "users.json", worker.data["users"])
                        st.rerun()

        with tab3:
            target = st.selectbox("Pilih Karyawan", [u["name"] for u in worker.data["users"] if u["role"] == "karyawan"])
            db_input = st.text_area("Input Database (Pisahkan dengan koma)")
            if st.button("Berikan DB"):
                if target and db_input:
                    nums = [n.strip() for n in db_input.split(",") if n.strip()]
                    # Hapus DB lama milik user ini jika ada, lalu timpa
                    worker.data["databases"] = [d for d in worker.data["databases"] if d["name"] != target]
                    db_entry = {"name": target, "numbers": [{"num": n, "status": "Tidak Terdaftar"} for n in nums]}
                    worker.data["databases"].append(db_entry)
                    worker.execute(worker.save_file, "databases.json", worker.data["databases"])
                    st.success("Database berhasil dibagikan!")

        with tab4:
            text_in = st.text_area("Input Teks Harian")
            if st.button("Simpan Teks"):
                worker.data["texts"] = {"content": text_in}
                worker.execute(worker.save_file, "texts.json", worker.data["texts"])
                st.success("Teks berhasil diatur!")

    elif page == "Report":
        st.header("Laporan")
        st.write(f"Total Pengajuan NDP: {len(worker.data['reports']['ndp'])}")
        st.write(f"Total Request Withdraw: {len(worker.data['reports']['wd'])}")

else:
    # HALAMAN KARYAWAN
    page = st.sidebar.radio("Menu Karyawan", ["Akun", "Database", "Pengajuan", "Upload", "Teks"])
    
    if page == "Akun":
        st.header("Profil & Dompet")
        st.write(f"UID: `{user['uid']}`")
        
        # Saldo dummy
        my_payroll = worker.data["payroll"].get(user["name"], 0)
        st.metric("Saldo Dompet", f"Rp {my_payroll}")
        
        if st.button("Tarik Saldo (Withdraw)"):
            worker.data["reports"]["wd"].append({"user": user["name"], "amount": my_payroll, "time": str(datetime.now())})
            worker.execute(worker.save_file, "reports.json", worker.data["reports"])
            st.info("Pengajuan withdraw dikirim ke Admin.")

    elif page == "Database":
        st.header("Database Kerja Saya")
        my_db = next((d for d in worker.data["databases"] if d["name"] == user["name"]), None)
        
        if my_db:
            for i, item in enumerate(my_db["numbers"]):
                col1, col2 = st.columns([1, 2])
                col1.code(item["num"])
                
                statuses = ["Tidak Terdaftar", "Terdaftar", "Dibaca", "Dibalas"]
                curr_idx = statuses.index(item["status"]) if item["status"] in statuses else 0
                
                # Menggunakan selectbox agar user mudah mengubah status
                new_status = col2.selectbox("Status", statuses, index=curr_idx, key=f"st_{user['uid']}_{i}")
                
                if new_status != item["status"]:
                    item["status"] = new_status
                    with st.spinner("Menyinkronkan status..."):
                        worker.execute(worker.save_file, "databases.json", worker.data["databases"])
        else:
            st.warning("Anda belum mendapatkan database hari ini.")

    elif page == "Pengajuan":
        st.header("Pengajuan NDP")
        ndp_input = st.text_area("Masukkan Database untuk diajukan")
        if st.button("Ajukan NDP"):
            if ndp_input:
                worker.data["reports"]["ndp"].append({"user": user["name"], "data": ndp_input})
                worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                st.success("Pengajuan NDP berhasil dikirim!")

    elif page == "Upload":
        st.header("Upload Video")
        vid = st.file_uploader("Pilih Video", type=["mp4", "mov"])
        caption = st.text_input("Caption (Contoh: 1-10)")
        if st.button("Upload Video") and vid and caption:
            with st.spinner("Mengupload ke S3 (Queue)..."):
                filename = f"{user['uid']}_{datetime.now().timestamp()}_{vid.name}"
                # Masukkan upload task ke antrian agar tidak memblokir user lain
                worker.execute(worker.upload_file_s3, vid.getvalue(), filename)
                
                # Simpan log video di reports
                worker.data["reports"]["video"].append({"user": user["name"], "file": filename, "caption": caption})
                worker.execute(worker.save_file, "reports.json", worker.data["reports"])
            st.success("Video berhasil diupload!")

    elif page == "Teks":
        st.header("Teks Kerja Hari Ini")
        text_content = worker.data["texts"].get("content", "Belum ada teks dari Admin.")
        st.code(text_content)
        st.button("Copy Teks", on_click=lambda: st.toast("Teks disalin!"))
