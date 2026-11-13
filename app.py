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
                admin_found = False
                for u in self.data["users"]:
                    if u["uid"] == admin_uid and u["role"] == "admin":
                        admin_found = True
                        if u["pass_hash"] != self.hash_pwd(admin_pwd):
                            u["pass_hash"] = self.hash_pwd(admin_pwd)
                            self._save("users.json", self.data["users"])
                        if "accounts" not in u:
                            u["accounts"] = []
                        break
                if not admin_found:
                    self.data["users"].append({
                        "uid": admin_uid, "pass_hash": self.hash_pwd(admin_pwd),
                        "name": "Administrator", "role": "admin",
                        "banned": False, "accounts": []
                    })
                    self._save("users.json", self.data["users"])

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
                if task is None:
                    break
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
# HELPERS
# ==========================================
def gen_uid():
    """Generate UID unik 16 digit angka."""
    existing = {u["uid"] for u in worker.data["users"]}
    while True:
        uid = "".join(str(random.randint(0, 9)) for _ in range(16))
        if uid not in existing:
            return uid


def gen_password():
    return str(uuid.uuid4())[:8]


def count_items(text):
    if not text:
        return 0
    items = re.split(r"[,\n\r;]+", text)
    return len([i for i in items if i.strip()])


def save_users():
    worker.execute(worker.save_file, "users.json", worker.data["users"])


# ==========================================
# 2. AUTENTIKASI
# ==========================================
def login_page():
    st.title("Login ElangPintar")
    with st.form("login_form"):
        uid = st.text_input("UID")
        pwd = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
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

user = st.session_state.user


# ==========================================
# 3. SIDEBAR
# ==========================================
st.sidebar.title(f"Halo, {user['name']}")
st.sidebar.write(f"Role: {user['role'].title()}")
st.sidebar.caption(f"UID: `{user['uid']}`")
if st.sidebar.button("Logout"):
    del st.session_state.user
    st.rerun()


# ==========================================
# 4. ADMIN
# ==========================================
if user["role"] == "admin":
    page = st.sidebar.radio("Menu Admin", ["Employee", "Payroll", "Analytic", "Report"])

    # ---------- EMPLOYEE ----------
    if page == "Employee":
        st.header("Manajemen Karyawan")
        tab1, tab2, tab3, tab4 = st.tabs(["Buat Akun", "Kelola Akun", "GiveDB", "SetText"])

        with tab1:
            name = st.text_input("Nama Karyawan Baru")
            if st.button("Generate Akun"):
                if name:
                    new_uid = gen_uid()
                    new_pwd = gen_password()
                    worker.data["users"].append({
                        "uid": new_uid,
                        "pass_hash": worker.hash_pwd(new_pwd),
                        "name": name,
                        "role": "karyawan",
                        "banned": False,
                        "accounts": []
                    })
                    with st.spinner("Menyimpan ke S3..."):
                        save_users()
                    st.success("Akun karyawan berhasil dibuat!")
                    st.code(f"UID      : {new_uid}\nPassword : {new_pwd}", language="text")
                    st.caption("⚠️ Password hanya ditampilkan sekali. Catat sekarang.")

        with tab2:
            for u in worker.data["users"]:
                if u["role"] == "karyawan":
                    col1, col2 = st.columns([4, 1])
                    status_badge = "🚫 BANNED" if u["banned"] else "✅ AKTIF"
                    col1.write(f"**{u['name']}** — `{u['uid']}` — {status_badge}")
                    btn = "Unban" if u["banned"] else "Ban"
                    if col2.button(btn, key=f"ban_{u['uid']}"):
                        u["banned"] = not u["banned"]
                        save_users()
                        st.rerun()

        with tab3:
            karyawan_list = [u["name"] for u in worker.data["users"] if u["role"] == "karyawan"]
            if karyawan_list:
                target = st.selectbox("Pilih Karyawan", karyawan_list)
                db_input = st.text_area("Input Database (pisahkan dengan koma atau enter)")
                if st.button("Berikan DB"):
                    if target and db_input:
                        nums = [n.strip() for n in re.split(r"[,\n\r;]+", db_input) if n.strip()]
                        worker.data["databases"] = [d for d in worker.data["databases"] if d["name"] != target]
                        worker.data["databases"].append({
                            "name": target,
                            "numbers": [{"num": n, "status": "Tidak Terdaftar"} for n in nums]
                        })
                        worker.execute(worker.save_file, "databases.json", worker.data["databases"])
                        st.success(f"Database ({len(nums)} item) diberikan ke {target}.")
            else:
                st.info("Belum ada karyawan terdaftar.")

        with tab4:
            text_in = st.text_area("Input Teks Harian")
            if st.button("Simpan Teks"):
                worker.data["texts"] = {"content": text_in}
                worker.execute(worker.save_file, "texts.json", worker.data["texts"])
                st.success("Teks berhasil diatur!")

    # ---------- PAYROLL ----------
    elif page == "Payroll":
        st.header("Manajemen Payroll / Gaji")
        employees = [u for u in worker.data["users"] if u["role"] == "karyawan"]
        if not employees:
            st.info("Belum ada karyawan.")
        else:
            total_bayar = sum(worker.data["payroll"].get(e["name"], 0) for e in employees)
            st.metric("Total Saldo Seluruh Karyawan", f"Rp {total_bayar:,}")
            st.divider()

            for emp in employees:
                current = worker.data["payroll"].get(emp["name"], 0)
                st.markdown(f"### {emp['name']} — Saldo: **Rp {current:,}**")
                c1, c2, c3 = st.columns([3, 1, 1])
                amount = c1.number_input(
                    "Nominal (Rp)", min_value=0, step=10000,
                    key=f"payamt_{emp['uid']}"
                )
                if c2.button("➕ Tambah", key=f"payadd_{emp['uid']}"):
                    if amount > 0:
                        worker.data["payroll"][emp["name"]] = current + amount
                        worker.execute(worker.save_file, "payroll.json", worker.data["payroll"])
                        st.success(f"Gaji {emp['name']} ditambah Rp {amount:,}")
                        st.rerun()
                if c3.button("🔄 Reset", key=f"payreset_{emp['uid']}"):
                    worker.data["payroll"][emp["name"]] = 0
                    worker.execute(worker.save_file, "payroll.json", worker.data["payroll"])
                    st.warning(f"Saldo {emp['name']} di-reset.")
                    st.rerun()
                st.divider()

    # ---------- ANALYTIC ----------
    elif page == "Analytic":
        st.header("Analitik Kinerja Karyawan")
        employees = [u for u in worker.data["users"] if u["role"] == "karyawan"]
        if not employees:
            st.info("Belum ada karyawan.")
        else:
            selected = st.selectbox("Pilih Karyawan", [e["name"] for e in employees])
            if selected:
                ndp_approved = [
                    r for r in worker.data["reports"]["ndp"]
                    if r["user"] == selected and r.get("status") == "approved"
                ]
                ndp_pending = [
                    r for r in worker.data["reports"]["ndp"]
                    if r["user"] == selected and r.get("status", "pending") == "pending"
                ]
                total_ndp = sum(r.get("count", 0) for r in ndp_approved)
                total_pending = sum(r.get("count", 0) for r in ndp_pending)

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
                c3.metric("Persentase NDP", f"{pct:.1f}%")
                st.caption(f"NDP pending: {total_pending} item")

                if my_db:
                    st.subheader("Rincian Status Database")
                    counts = {}
                    for n in my_db["numbers"]:
                        counts[n["status"]] = counts.get(n["status"], 0) + 1
                    for s, c in counts.items():
                        st.write(f"- **{s}**: {c}")
                else:
                    st.info("Karyawan ini belum menerima database.")

                st.subheader("History Pengajuan NDP")
                my_ndps = [r for r in worker.data["reports"]["ndp"] if r["user"] == selected]
                if not my_ndps:
                    st.caption("Belum ada pengajuan.")
                for r in my_ndps:
                    badge = {"approved": "✅", "rejected": "❌", "pending": "⏳"}.get(r.get("status", "pending"), "⏳")
                    st.write(f"{badge} {r.get('count', 0)} item — {r.get('time', '-')}")

    # ---------- REPORT ----------
    elif page == "Report":
        st.header("Laporan & Approval")
        tab_ndp, tab_wd, tab_video = st.tabs(["NDP", "Withdraw", "Video"])

        # ---- NDP ----
        with tab_ndp:
            ndps = worker.data["reports"]["ndp"]
            pending = [(i, n) for i, n in enumerate(ndps) if n.get("status", "pending") == "pending"]
            st.subheader(f"⏳ Pending ({len(pending)})")
            if not pending:
                st.info("Tidak ada pengajuan NDP pending.")
            for i, n in pending:
                with st.expander(f"{n['user']} — {n.get('count', 0)} item — {n.get('time', '-')}"):
                    st.code(n["data"])
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Approve", key=f"appr_ndp_{i}"):
                        ndps[i]["status"] = "approved"
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                        st.rerun()
                    if c2.button("❌ Reject", key=f"rej_ndp_{i}"):
                        ndps[i]["status"] = "rejected"
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                        st.rerun()

            st.subheader("📜 History")
            history = [(i, n) for i, n in enumerate(ndps) if n.get("status", "pending") != "pending"]
            if not history:
                st.caption("Belum ada history.")
            for _, n in history:
                badge = "✅" if n["status"] == "approved" else "❌"
                st.write(f"{badge} **{n['user']}** — {n.get('count', 0)} item — {n.get('time', '-')}")

        # ---- WITHDRAW ----
        with tab_wd:
            wds = worker.data["reports"]["wd"]
            pending = [(i, n) for i, n in enumerate(wds) if n.get("status", "pending") == "pending"]
            st.subheader(f"⏳ Pending ({len(pending)})")
            if not pending:
                st.info("Tidak ada pengajuan withdraw pending.")
            for i, n in pending:
                acc = n.get("account", {})
                acc_label = f"{acc.get('bank','-')} — {acc.get('number','-')} a.n. {acc.get('name','-')}"
                with st.expander(f"{n['user']} — Rp {n['amount']:,} — {n.get('time', '-')}"):
                    st.write(f"🏦 Rekening tujuan: **{acc_label}**")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Approve (sudah ditransfer)", key=f"appr_wd_{i}"):
                        wds[i]["status"] = "approved"
                        worker.data["payroll"][n["user"]] = max(
                            worker.data["payroll"].get(n["user"], 0) - n["amount"], 0
                        )
                        worker.execute(worker.save_file, "payroll.json", worker.data["payroll"])
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                        st.rerun()
                    if c2.button("❌ Reject", key=f"rej_wd_{i}"):
                        wds[i]["status"] = "rejected"
                        worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                        st.rerun()

            st.subheader("📜 History")
            history = [(i, n) for i, n in enumerate(wds) if n.get("status", "pending") != "pending"]
            if not history:
                st.caption("Belum ada history.")
            for _, n in history:
                badge = "✅" if n["status"] == "approved" else "❌"
                st.write(f"{badge} **{n['user']}** — Rp {n['amount']:,} — {n.get('time', '-')}")

        # ---- VIDEO ----
        with tab_video:
            vids = worker.data["reports"]["video"]
            if not vids:
                st.info("Belum ada video yang diupload.")
            for v in vids:
                st.write(f"🎥 **{v['user']}** — Caption: {v['caption']} — `{v['file']}`")


# ==========================================
# 5. KARYAWAN
# ==========================================
else:
    page = st.sidebar.radio("Menu Karyawan", ["Akun", "Database", "Pengajuan", "Upload", "Teks"])

    # ---------- AKUN ----------
    if page == "Akun":
        st.header("Profil & Dompet")
        st.write(f"Nama: **{user['name']}**")
        st.write(f"UID: `{user['uid']}`")

        my_payroll = worker.data["payroll"].get(user["name"], 0)
        st.metric("Saldo Dompet", f"Rp {my_payroll:,}")

        st.subheader("🏦 Rekening Terdaftar")
        accounts = user.get("accounts", [])
        if not accounts:
            st.warning("Belum ada rekening. Tambahkan dulu di bawah.")
        else:
            for i, a in enumerate(accounts):
                c1, c2 = st.columns([5, 1])
                c1.write(f"{i+1}. **{a['bank']}** — `{a['number']}` a.n. {a['name']}")
                if c2.button("🗑 Hapus", key=f"delacc_{i}"):
                    accounts.pop(i)
                    user["accounts"] = accounts
                    save_users()
                    st.rerun()

        with st.expander("➕ Tambah Rekening Baru"):
            with st.form("add_account_form"):
                bank = st.text_input("Jenis Bank / E-Wallet (BCA, Dana, OVO, dll)")
                number = st.text_input("Nomor Rekening")
                holder = st.text_input("Nama Pemilik Rekening")
                if st.form_submit_button("Simpan Rekening"):
                    if bank and number and holder:
                        if "accounts" not in user:
                            user["accounts"] = []
                        user["accounts"].append({"bank": bank, "number": number, "name": holder})
                        save_users()
                        st.success("Rekening ditambahkan!")
                        st.rerun()
                    else:
                        st.error("Semua field wajib diisi.")

        st.divider()
        st.subheader("💸 Tarik Saldo (Withdraw)")
        accounts = user.get("accounts", [])
        if not accounts:
            st.warning("⚠️ Tambahkan rekening terlebih dahulu sebelum withdraw.")
        else:
            pending_wd = sum(
                r["amount"] for r in worker.data["reports"]["wd"]
                if r["user"] == user["name"] and r.get("status", "pending") == "pending"
            )
            available = max(my_payroll - pending_wd, 0)

            col1, col2 = st.columns(2)
            col1.metric("Saldo Pending Withdraw", f"Rp {pending_wd:,}")
            col2.metric("Saldo Tersedia", f"Rp {available:,}")

            labels = [f"{a['bank']} — {a['number']} a.n. {a['name']}" for a in accounts]
            sel = st.selectbox("Pilih Rekening Tujuan", range(len(accounts)), format_func=lambda i: labels[i])
            sel_acc = accounts[sel]

            if st.button("Ajukan Withdraw"):
                if available <= 0:
                    st.error("Tidak ada saldo yang bisa ditarik.")
                else:
                    worker.data["reports"]["wd"].append({
                        "user": user["name"],
                        "amount": available,
                        "account": sel_acc,
                        "status": "pending",
                        "time": str(datetime.now())
                    })
                    worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                    st.success(f"Pengajuan withdraw Rp {available:,} terkirim ke Admin.")
                    st.rerun()

    # ---------- DATABASE ----------
    elif page == "Database":
        st.header("Database Kerja Saya")
        my_db = next((d for d in worker.data["databases"] if d["name"] == user["name"]), None)
        if my_db:
            statuses = ["Tidak Terdaftar", "Terdaftar", "Dibaca", "Dibalas"]
            for i, item in enumerate(my_db["numbers"], 1):
                c1, c2, c3 = st.columns([1, 4, 3])
                with c1:
                    st.markdown(f"**{i}.**")
                with c2:
                    st.code(item["num"], language="text")  # ada tombol copy di hover
                with c3:
                    curr_idx = statuses.index(item["status"]) if item["status"] in statuses else 0
                    new_status = st.selectbox(
                        "Status", statuses, index=curr_idx,
                        key=f"st_{user['uid']}_{i}",
                        label_visibility="collapsed"
                    )
                    if new_status != item["status"]:
                        item["status"] = new_status
                        worker.execute(worker.save_file, "databases.json", worker.data["databases"])
                        st.rerun()
        else:
            st.warning("Anda belum mendapatkan database hari ini.")

    # ---------- PENGAJUAN ----------
    elif page == "Pengajuan":
        st.header("Pengajuan NDP")
        ndp_input = st.text_area(
            "Masukkan Database untuk diajukan (pisahkan dengan koma atau enter)"
        )
        preview = count_items(ndp_input)
        st.caption(f"Terdeteksi **{preview}** item")
        if st.button("Ajukan NDP"):
            if ndp_input.strip():
                worker.data["reports"]["ndp"].append({
                    "user": user["name"],
                    "data": ndp_input,
                    "count": preview,
                    "status": "pending",
                    "time": str(datetime.now())
                })
                worker.execute(worker.save_file, "reports.json", worker.data["reports"])
                st.success("Pengajuan NDP berhasil dikirim!")
                st.rerun()
            else:
                st.error("Isi data NDP terlebih dahulu.")

        st.subheader("📜 History NDP Saya")
        my_ndps = [r for r in worker.data["reports"]["ndp"] if r["user"] == user["name"]]
        if not my_ndps:
            st.caption("Belum ada pengajuan.")
        for r in my_ndps:
            badge = {"approved": "✅", "rejected": "❌", "pending": "⏳"}.get(r.get("status", "pending"), "⏳")
            st.write(f"{badge} {r.get('count', 0)} item — {r.get('time', '-')}")

    # ---------- UPLOAD ----------
    elif page == "Upload":
        st.header("Upload Video")
        vid = st.file_uploader("Pilih Video", type=["mp4", "mov"])
        caption = st.text_input("Caption (Contoh: 1-10)")
        if st.button("Upload Video") and vid and caption:
            with st.spinner("Mengupload ke S3 (Queue)..."):
                filename = f"{user['uid']}_{datetime.now().timestamp()}_{vid.name}"
                worker.execute(worker.upload_file_s3, vid.getvalue(), filename)
                worker.data["reports"]["video"].append({
                    "user": user["name"],
                    "file": filename,
                    "caption": caption
                })
                worker.execute(worker.save_file, "reports.json", worker.data["reports"])
            st.success("Video berhasil diupload!")

    # ---------- TEKS ----------
    elif page == "Teks":
        st.header("Teks Kerja Hari Ini")
        text_content = worker.data["texts"].get("content", "Belum ada teks dari Admin.")
        st.code(text_content)
        st.button("Copy Teks", on_click=lambda: st.toast("Teks disalin!"))
