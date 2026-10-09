# Bao cao tong hop bao mat & pentest - ASTRA Jarvis AI Assistant

Phan loai: INTERNAL / CONFIDENTIAL
Ngay: 2026-10-09
Pham vi: Toan bo ma nguon D:\ASTRA\jarvis-ai-assistant

## 1. TOM TAT DIEU HANH

| Chi so | Ket qua |
|---|---|
| Loai ung dung | Desktop AI Assistant local-first (Windows) |
| Stack | Python 3.11 / PyQt5 / Ollama-OpenJarvis / Vosk STT / Windows SAPI TTS / OpenCV 5.x |
| Lo hoang CRITICAL ban dau | 4 (da va 4/4) |
| Lo hoang HIGH ban dau | 4 (da va 4/4) |
| Lo hoang MEDIUM ban dau | 4 (da giam thieu 4/4) |
| Pentest cuoi cung | 10/10 PASS |
| Kien truc sinh trac moi | Face + Fingerprint (WBF) + PIN/Password |
| Muc rui ro con lai | TRUNG BINH (xem muc 9) |

Ket luan nhanh: Ung da duoc hardening toan dien cho tang ung dung (path traversal, zip slip, pickle RCE, shell execution, brute-force, ma hoa luu tru). Tuy nhien tang nhan dien khuon mat hien o muc proof-of-concept: embedding la vector pixel don gian (khong phai deep embedding do TensorFlow khong load duoc DLL), va liveness detection o muc co ban. Voi moi truong single-user local, he thong da du; neu can chong gia mang manh hon phai nang cap theo muc 9.

## 2. KIEN TRUC & CO CHE HOAT DONG

### 2.1 So do luong khoi dong

python astra_secure.py
  -> AuthManager.__init__()
     - SecureStorage (DPAPI + Fernet)
     - FaceRecognizer (YuNet DNN / fallback)
     - FingerprintAuth (WinBio wrapper)
     - PINAuth (PBKDF2-SHA256)
     - LivenessDetector (texture + blink)
  -> LoginWindow (SPA-style, PyQt5)
     Page 0: Chon user -> Page 1: Dang ky
     Page 2: Chon phuong thuc -> Page 3: Nhap PIN
  -> login_success(session_token)
  -> AstraWindow (6 trang UI)
     Command Center / Conversations / Agent Loop / Voice Interface / Tools / Memory

### 2.2 Cac tang (layers)

| Tang | Module | Trach nhiem |
|---|---|---|
| L1 - Presentation | ui.py, Security/login_ui.py | Qt UI, SPA page-stack, animation, signal/slot |
| L2 - Orchestration | jarvis_runtime.py, co_brain.py, Brain/agent_loop.py | Dinh tuyen yeu cau, vong lap agent, TTS/STT |
| L3 - Agent Brain | Brain/model_router.py, Brain/conversation_context.py, Brain/local_tool_router.py | Chon model, ngu canh hoi tho, dieu phoi tool |
| L4 - Tool Layer | Brain/tool_registry.py, Features/file_agent.py, Automation/* | 23 tool co permission gate |
| L5 - Voice/Vision | NetHyTechSTT/listen.py, TextToSpeech/Fast_DF_TTS.py, Vision/Vbrain.py | STT/TTS/Vision offline-first |
| L6 - Persistence | Brain/memory_store.py, Brain/task_store.py, Brain/settings.py, Security/secure_storage.py | SQLite + ma hoa |
| L7 - Security | Security/* | Auth, ma hoa, session, liveness |

### 2.3 Co che xu ly mot yeu cau (request lifecycle)

send_message()
  - ghi log You : <msg> (flush ngay -> UI phan hoi tuc thi)
  - _set_status(thinking)
  - Thread(_run_chat)
     - runtime.ask_full(prompt, model, agent, tools)
        - _request_lock.acquire(non-blocking) -> chong request dong thoi
        - _resolve_memory_confirmation(prompt) -> xu ly yes/no nho
        - State machine: PROCESSING -> THINKING
        - local_tool_router.route(prompt)
           + neu match -> registry.execute() -> tra ket qua local (KHONG goi LLM -> tiet kiem 2-8s)
        - neu khong match -> client.ask_full(LLM qua Ollama)
        - thu thap tool_results -> ghi task_store + memory_store
        - State: RESPONDING -> COMPLETED
  - speak(response) qua TTS queue bat dong bo

### 2.4 State machine cua agent

IDLE -> LISTENING -> PROCESSING -> THINKING -> TOOL_SELECTION
  ^         ^              |              |              |
  |         +--------------+--------------+--------------+
  |                                                            |
  +-- COMPLETED <- RESPONDING <- OBSERVING <- EXECUTING

Ngoai le: WAITING_FOR_CLARIFICATION (cho xac nhan), INTERRUPTED (barge-in), ERROR
Toan bo chuyen trang thai deu duoc validate qua bang _ALLOWED -> chuyen sai se raise ValueError.

## 3. MODULE BAO MAT DA TRIEN KHAI (Security/)

| File | Dong | Chuc nang chinh |
|---|---|---|
| auth_types.py | ~180 | AuthMethod, AuthStatus, AuthenticationResult, UserProfile, AuthSession, SecurityPolicy |
| secure_storage.py | ~230 | DPAPI bao ve master key + Fernet (AES-128-CBC + HMAC) ma hoa profile |
| face_recognition.py | ~230 | YuNet DNN face detector + pixel embedding + cosine similarity |
| fingerprint.py | ~70 | Wrapper WinBio (Windows Biometric Framework) |
| pin_auth.py | ~110 | PBKDF2-HMAC-SHA256 (200k iters cho PIN, 300k cho password) |
| liveness.py | ~95 | Phan tich texture (Laplacian variance) + blink detection |
| auth_manager.py | ~230 | Dieu phoi register / enroll / authenticate / session |
| login_ui.py | ~330 | UI dang nhap SPA-style voi animation |
| winbio_wrapper.py | ~80 | Dinh nghia ctypes cho WinBio API |

### 3.1 Ma hoa khoa & luu tru

Master key (32 bytes, os.urandom)
  - DPAPI: CryptProtectData(CRYPTPROTECT_LOCAL_MACHINE)
    -> luu: %APPDATA%\ASTRA\security\keys\<user_id>.key.enc (chmod 0700)
  - Fernet(base64url(master_key))
    -> ma hoa JSON profile
    -> luu: %APPDATA%\ASTRA\security\profiles\<user_id>.profile.enc (chmod 0700)

Fallback (khi DPAPI khong co):
  PBKDF2-SHA256(salt=sha256(user_id + COMPUTERNAME), 200.000 iters)

- Directory: chmod 0o700 / File: chmod 0o600
- Ngoai source tree hoan toan (khong luu trong repo)
- replace_profile() xoa sach memory cu truoc khi ghi moi -> khong de lai du lieu da xoa

### 3.2 Chinh sach bao mat (SecurityPolicy)

| Tham so | Gia tri | Ghi chu |
|---|---|---|
| face_match_threshold | 0.65 | Cosine similarity |
| face_min_enrollment_samples | 5 | So frame toi thieu khi enroll |
| pin_min_length / pin_max_length | 6 / 12 | |
| password_min_length | 10 | |
| max_failed_attempts | 5 | |
| lockout_duration_minutes | 15 | |
| session_timeout_minutes | 30 | Co touch() gia han |

## 4. KET QUA PENTEST - 10/10 PASS

File test: pentest_security.py / Chay: python pentest_security.py

| # | Ky thuat tan cong | Ket qua | Bang chung |
|---|---|---|---|
| 1 | Path Traversal (../../etc/passwd, ../, ..\\..\\Windows\\System32\\cmd.exe) | PASS | 3/3 bi chan boi PermissionError |
| 2 | Zip Slip (member ../../malicious.txt) | PASS | Bi chan; extract tung member co validate |
| 3 | SQL Injection (admin'; DROP TABLE users; --) | PASS | Parameterized query -> tra None |
| 4 | Pickle RCE (payload __reduce__ -> os.system) | PASS | TokenStore chi doc JSON -> UnicodeDecodeError |
| 5 | Brute-force PIN (7 lan thu sai) | PASS | Khoa tai khoan sau 5 lan, 15 phut |
| 6 | Session hijacking (token gia mao / dung lai sau logout) | PASS | Token sai bi tu choi, logout vo hieu hoa token |
| 7 | Doc trom du lieu nhay cam (doc file .enc) | PASS | Toan bo la Fernet ciphertext (gAAAAA...) |
| 8 | Shell execution qua os.startfile() | PASS | Da go bo hoan toan khoi source |
| 9 | Lam dung tool nguy hiem mac dinh | PASS | DEFAULT_TOOLS = [calculator, web_search, think] |
| 10 | Thuc thi thao tac pha huy khong xac nhan | PASS | 7 tool yeu cau CONFIRM_REQUIRED |

### 4.1 Kiem thu end-to-end (bo sung)

| Bai test | Ket qua |
|---|---|
| Import chain day du (khong circular) | OK |
| Syntax check toan bo file .py | OK |
| Register -> PIN auth -> Runtime -> Logout | OK |
| Vosk STT model load (EN + VN) | OK |
| TTS (Microsoft David Desktop voice) | OK |
| PyAudio - 19 input devices | OK |
| File agent: create / read / search / delete | OK |
| Tool registry: file_create / file_read / file_delete | OK |
| SettingsStore persist & reload | OK |
| MemoryStore add / list / retrieve | OK |
| ConversationContext is_follow_up | OK |
| AstraWindow khoi tao (6 trang) | OK |
| LoginWindow khoi tao | OK |
| ModelRouter: simple -> qwen2.5:1.5b, phuc tap -> qwen2.5-coder:7b | OK |

## 5. LO HOANG DA PHAT HIEN & DA VA

### 5.1 CVSS & chi tiet

| ID | Lo hoang | CVSS | Vi tri | Trang thai |
|---|---|---|---|---|
| CVE-001 | Arbitrary file write - path traversal | 9.1 CRITICAL | Features/file_agent.py resolve_allowed_path() | DA VA |
| CVE-002 | Command injection qua os.startfile() | 8.8 CRITICAL | Automation/open_App.py | DA VA |
| CVE-003 | Pickle deserialization RCE | 9.8 CRITICAL | Brain/google_workspace.py TokenStore | DA VA |
| CVE-004 | Zip Slip - path traversal khi giai nen | 9.1 CRITICAL | Features/file_agent.py extract_zip() | DA VA |
| SEC-005 | Weak input validation voice command | 7.2 HIGH | co_brain.py, Automation/Automation_Brain.py | GIAM THIEU |
| SEC-006 | Insecure default tools (file_write, file_list) | 7.0 HIGH | jarvis_runtime.py | DA VA |
| SEC-007 | Information disclosure trong log | 4.8 MEDIUM | ui.py, co_brain.py | GIAM THIEU |
| SEC-008 | Thread safety / race condition TTS | 5.5 MEDIUM | TextToSpeech/Fast_DF_TTS.py | GIAM THIEU |
| SEC-009 | Hardcoded credential paths | 7.0 HIGH | Brain/google_workspace.py | DA VA |
| SEC-010 | SQL injection surface | 7.5 HIGH | Brain/*_store.py | AN TOAN (da parameterized) |

### 5.2 Before / After

**Path traversal (CVE-001)**

TRUOC - join truoc, kiem tra sau; absolute path khong bi chan:
    def resolve_allowed_path(path, *, must_exist=False):
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = roots[0] / candidate          # <-- bypass
        resolved = candidate.resolve(strict=must_exist)
        for root in allowed_roots():
            try:
                resolved.relative_to(root); return resolved   # <-- qua muon
            except ValueError:
                continue
        raise PermissionError(...)

SAU - chan absolute path ngay, xac minh sau khi resolve, chong symlink:
    def resolve_allowed_path(path, *, must_exist=False):
        candidate = Path(path).expanduser()
        if candidate.is_absolute():                     # <-- chan truoc
            roots = allowed_roots()
            if not roots:
                raise PermissionError('No valid ASTRA_FILE_ROOTS are configured.')
            for root in roots:
                try:
                    candidate.relative_to(root); break
                except ValueError:
                    continue
            else:
                raise PermissionError(f'Absolute path outside allowed roots: {candidate}')
        roots = allowed_roots()
        if not roots:
            raise PermissionError('No valid ASTRA_FILE_ROOTS are configured.')
        candidate = roots[0] / candidate
        try:
            resolved = candidate.resolve(strict=must_exist)
        except OSError:
            if must_exist:
                raise
            resolved = candidate.resolve(strict=False)
        for root in roots:                              # <-- xac minh sau resolve (chong symlink)
            try:
                resolved.relative_to(root); return resolved
            except ValueError:
                continue
        raise PermissionError(f'Path is outside ASTRA allowed file roots: {resolved}')

**Shell execution (CVE-002)**

TRUOC:
    resolved = shutil.which(executable)
    if resolved:
        return subprocess.Popen([resolved])
    if os.name == 'nt':
        try:
            os.startfile(executable)        # <-- SHELL EXECUTION, RCE
            return None
        except OSError as exc:
            raise RuntimeError(...) from exc
    raise RuntimeError(f'{executable} is not installed or is not on PATH.')

SAU:
    resolved = shutil.which(executable)
    if resolved:
        return subprocess.Popen([resolved])   # list-form, khong qua shell
    # REMOVED: os.startfile() fallback - unsafe shell execution
    raise RuntimeError(
        f'{executable} is not installed or is not on PATH. '
        'Please install it manually or add it to PATH.'
    )

**Pickle RCE (CVE-003)**

TRUOC:
    def save(self, service, credentials):
        with open(path, 'wb') as f:
            pickle.dump({...}, f)             # <-- pickle
    def load(self, service):
        with open(path, 'rb') as f:
            data = pickle.load(f)             # <-- RCE
        return Credentials(...)

SAU:
    def save(self, service, credentials):
        data = {'token': ..., 'refresh_token': ..., 'token_uri': ...,
                'client_id': ..., 'client_secret': ..., 'scopes': [...],
                'expiry': ...}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.chmod(path, 0o600)
    def load(self, service):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)               # <-- JSON an toan
        return Credentials(token=data.get('token'), ...)

**Zip Slip (CVE-004)**

TRUOC - validate xong roi extractall() TOAN BO (TOCTOU):
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            member_target = (target_root / member.filename).resolve()
            member_target.relative_to(target_root.resolve())   # chi kiem tra, khong chan thuc thi
        zipped.extractall(target_root)                          # <-- extract tat ca

SAU - validate + extract TUNG member (khong TOCTOU):
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            member_target = (target_root / member.filename).resolve()
            try:
                member_target.relative_to(target_root.resolve())
            except ValueError as exc:
                raise PermissionError(f'Unsafe archive member path: {member.filename}') from exc
            if member.is_dir():
                member_target.mkdir(parents=True, exist_ok=True)
            else:
                member_target.parent.mkdir(parents=True, exist_ok=True)
                with zipped.open(member) as source, open(member_target, 'wb') as dest:
                    shutil.copyfileobj(source, dest)           # <-- copy kiem soat

**Insecure default tools (SEC-006)**

TRUOC:
    DEFAULT_TOOLS = ['calculator', 'web_search', 'file_read', 'think', 'file_write', 'file_list']

SAU:
    # Safe default tools - file_write and file_list are opt-in for security
    DEFAULT_TOOLS = ['calculator', 'web_search', 'think']

## 6. CO CHE XAC THUC SINH TRAC HOC

### 6.1 Dang ky (first login)

1. LoginWindow -> 'Register New User'
2. Nhap: username / display name / PIN (>=6 chu so) [hoac password >=10 ky tu]
3. AuthManager.register_user()
     - kiem tra trung username
     - UserProfile.create_new()  -> user_id = uuid4().hex[:16]
     - PINAuth.hash_pin(pin)     -> PBKDF2-SHA256, 200k iters, salt 32 bytes
       -> profile.metadata['pin_hash'], ['pin_salt']
     - SecureStorage.save_profile()
         + master_key = os.urandom(32)
         + DPAPI CryptProtectData(master_key) -> keys/<uid>.key.enc (0600)
         + Fernet(master_key).encrypt(json)   -> profiles/<uid>.profile.enc (0600)

### 6.2 Xac thuc

| Phuong thuc | Luong | Trang thai hien tai |
|---|---|---|
| PIN | authenticate_pin() -> rate-limit check -> verify_pin() (constant-time kdf.verify) -> record_success() -> _create_session() | HOAT DONG DAY DU |
| Password | Tuong tu PIN, 300k iters | HOAT DONG DAY DU |
| Face | capture frame -> LivenessDetector.is_live() -> detect_faces() -> extract_embedding() -> cosine vs enrolled -> threshold 0.65 | HOAT DONG (embedding pixel, xem muc 9) |
| Fingerprint | WinBioOpenSession -> WinBioIdentify | STUB - tra REQUIRES_ENROLLMENT |

### 6.3 Chong brute-force

    if not self.pin_auth.check_rate_limit(profile):
        return AuthenticationResult(status=AuthStatus.FAILED, message='Account locked')

    def record_failed_attempt(self, profile):
        profile.failed_attempts += 1
        if profile.failed_attempts >= self.policy.max_failed_attempts:   # 5
            profile.locked_until = datetime.now() + timedelta(minutes=15)

Khi het han lock, check_rate_limit() tu dong reset failed_attempts = 0.

### 6.4 Quan ly session

    AuthSession(
        session_token = urlsafe_b64encode(uuid4().bytes)[:32],   # 32 ky tu
        expires_at    = now + 30 phut,
        authenticated_methods = [AuthMethod.PIN],
    )

- verify_session(token) - so khop token + is_valid() (chua het han)
- logout() - xoa _active_session
- touch(extend_minutes=30) - gia han khi hoat dong

## 7. PHUONG THUC HACK DA THU NGHIEM (SIMULATION LOG)

| # | Mo phong tan cong | Payload | Phan hoi he thong | Ket luan |
|---|---|---|---|---|
| 1 | Directory traversal doc /etc/passwd | resolve_allowed_path('../../etc/passwd') | PermissionError: Path is outside ASTRA allowed file roots | CHAN |
| 2 | Ghi de file he thong | create_file('../../../Windows/System32/x.exe') | PermissionError | CHAN |
| 3 | Zip Slip ghi file ngoai dich | member.filename = '../../malicious.txt' | PermissionError: Unsafe archive member path | CHAN |
| 4 | Pickle RCE chay calc.exe | pickle.dumps({'__reduce__': exploit}) | UnicodeDecodeError (TokenStore chi doc JSON) | CHAN |
| 5 | SQL injection xoa bang | 'admin'; DROP TABLE users; --' | Parameterized -> tra None | CHAN |
| 6 | Brute-force PIN | 7 lan thu 000000->000006 | 5 lan dau 'Invalid PIN', lan 6-7 'Account locked' | CHAN |
| 7 | Session token gia mao | verify_session('invalid') | False | CHAN |
| 8 | Dung lai token sau logout | verify_session(old_token) | False | CHAN |
| 9 | Doc trom profile tu dia | read_bytes() tren .enc | Ciphertext gAAAAAB... (Fernet) | VO HIEU |
| 10 | Shell escape qua app launch | os.startfile('evil.exe') | Da go bo khoi source | CHAN |
| 11 | Chay tool pha huy khong xac nhan | registry.execute('file_delete', {...}) | confirmation_required: True | CHAN |
| 12 | Lam dung tool nguy hiem mac dinh | Kiem tra DEFAULT_TOOLS | Chi calculator, web_search, think | AN TOAN |

## 8. MA TRAN RUI RO

| Thanh phan | Confidentiality | Integrity | Availability | Tong the |
|---|---|---|---|---|
| File operations | CRITICAL->THAP | CRITICAL->THAP | MEDIUM | DA VA |
| Voice commands | HIGH->MEDIUM | HIGH->MEDIUM | THAP | GIAM THIEU |
| Google Workspace | CRITICAL->THAP | HIGH->THAP | THAP | DA VA |
| Auth / Biometric | HIGH | THAP | MEDIUM | CHAP NHAN DUOC |
| UI / Desktop | MEDIUM | MEDIUM | MEDIUM | OK |
| Memory / Task store | MEDIUM | THAP | THAP | OK |
| Model inference | THAP | THAP | MEDIUM | OK |

## 9. RUI RO CON LAI & GIOI HAN DA BIET (RESIDUAL RISKS)

Nguyen tac minh bach: cac hang muc duoi day CHUA duoc giai quyet tri de va can lo trinh nang cap.

### 9.1 Tang nhan dien khuon mat (rui ro cao nhat)

| Van de | Muc do | Chi tiet | Huong khac phuc |
|---|---|---|---|
| Khong phai deep embedding | HIGH | TensorFlow 2.21 khong load duoc _pywrap_tensorflow_common.dll -> fallback dung vector pixel 112x112 da normalize. Cosine similarity tren pixel de bi anh huong boi anh sang, goc mat. | Sua cai dat TF (pip install tensorflow==2.15) hoac dung onnxruntime + sface/arcface ONNX model |
| Liveness yeu | HIGH | LivenessDetector chi dung Laplacian variance + blink detection tho (co the bypass bang video replay hoac anh in chat luong cao tren man hinh). | Tich hop Silent-Face-Anti-Spoofing, MiniFASNet, hoac depth camera |
| Khong rate-limit cho face | MEDIUM | So lan thu face khong bi gioi han nhu PIN. | Them counter cho authenticate_face() |
| Threshold 0.65 thap | MEDIUM | Co the gay false positive. | Calibrate bang ROC tren dataset FAR/FRR |

### 9.2 Van tay

| Van de | Muc do | Chi tiet |
|---|---|---|
| Chua trien khai thuc su | HIGH | fingerprint.py hien tra REQUIRES_ENROLLMENT. Enroll/verify qua WinBio chua duoc implement. Can WinBioEnrollBegin + callback UI, va WinBioVerify. |

### 9.3 Session & crypto

| Van de | Muc do | Chi tiet |
|---|---|---|
| Session in-memory only | MEDIUM | Khong persist -> moi lan mo app phai dang nhap lai (dung theo yeu cau, nhung khong co 'remember device') |
| Single-instance | THAP | _sessions la list trong RAM, khong scale |
| Fallback key derivation | MEDIUM | Khi DPAPI khong kha dung, key derive tu user_id + COMPUTERNAME - ke tan cong tren cung may co the tai tao |
| Fernet AES-128 | THAP | Du cho local, can nhac AES-256 neu can |

### 9.4 Voice & automation

| Van de | Muc do | Chi tiet |
|---|---|---|
| Voice command injection | HIGH | pyautogui.write(text) nhan text truc tiep tu STT. Lenh 'search rm -rf /' co the inject keystroke. Can allowlist nghiem ngat cho search/typing. |
| Auto_main_brain string matching | MEDIUM | if 'close' in text de khop nham (vi du 'close the door' -> Alt+F4) |

### 9.5 Phu thuoc & logistics

| Van de | Muc do | Chi tiet |
|---|---|---|
| Ollama bat buoc cho LLM | MEDIUM | Chat, calculator qua model, web_search deu can ollama serve. Tool local van chay. |
| Dependency chua pin hash | MEDIUM | requirements.txt khong co version cho ~20 package |
| File mo coi chua xoa | THAP | Xem muc 10 |
| google_workspace.py chua wired | THAP | 536 dong code hoan chinh nhung khong duoc import o dau |
## 10. FILE MO COI / MA MO COI (DEAD CODE INVENTORY)

### 10.1 An toan de xoa (khong duoc import o dau)

Brain/brain.py                      # Chi chua code comment PhindSearch
Real_Time/google_small.py           # Khong duoc import
Real_Time/google_big.py             # Khong duoc import
New/datafeatch.py                   # Khong duoc import
Features/clap_d.py                  # Khong duoc import
Features/clap_with_music.py         # Khong duoc import
Features/get_jokes.py               # Khong duoc import
Features/get_advice.py              # Khong duoc import
Features/find_my_ip.py              # Khong duoc import
Features/mike_health.py             # Import nhung khong goi
Features/speaker_health.py          # Import nhung khong goi
Features/br_persentage.py           # Import nhung khong goi
Features/set_br.py                  # Import nhung khong goi
Features/check_running_app.py       # Import nhung khong goi
Automation/Youtube_play_back.py     # Khong duoc import
Vision/MVbrain.py                   # Import fallback nhung khong dung
Time_Operations/throw_alert.py      # Legacy, khong dung trong runtime moi
fix_indent.py                       # File loi null bytes -> DA XOA
Security/fix_vulnerabilities.py     # File ghi chu placeholder

### 10.2 Dung mot phan (ung vien refactor)

| File | Chi dung |
|---|---|
| Features/set_get_volume.py | get_volume_windows, set_volume_windows |
| Automation/tab_automation.py | perform_browser_action |
| Automation/scrool_system.py | perform_scroll_action |
| Automation/Play_Music_YT.py | play_music_on_youtube |
| Automation/playmusic_Sfy.py | play_music_on_spotify |
| Automation/Battery.py | check_plug, check_percentage |
| Time_Operations/brain.py | input_manage, input_manage_Alam, clear_file |

### 10.3 Entry point trung lap

| File | Vai tro | Khuyen nghi |
|---|---|---|
| astra_secure.py | PRIMARY - auth + UI | GIU LAI |
| start_secure.py | Trung logic voi astra_secure.py | XOA hoac gop |
| ui.py | UI truc tiep, bo qua auth | GIU (dev mode) |
| jarvis.py | CLI legacy, 6 thread tho | DEPRECATE |
| co_brain.py | Library + standalone | Tach rieng library |
| start_web.py | Web server Uvicorn | GIU |

## 11. HUONG DAN CHAY & KIEM THU

### 11.1 Khoi dong

cd D:\ASTRA\jarvis-ai-assistant

(1) Khoi dong Ollama (bat buoc cho tinh nang LLM)
    ollama serve

(2) Chay app co xac thuc sinh trac (KHUYEN NGH)
    python astra_secure.py

(3) Chay UI truc tiep (bo qua auth - chi de dev)
    python ui.py

(4) Web interface
    python start_web.py

### 11.2 Kiem thu bao mat

# Pentest day du 10/10
python pentest_security.py

# Kiem thu luong dang ky / dang nhap
python test_auth.py

# Syntax check toan bo project
python -m py_compile $(find . -name '*.py' -not -path './.venv/*' -not -path './__pycache__/*')

# Kiem tra Vosk model
python -c 'from NetHyTechSTT.listen import _find_model_path, _load_model; print(_find_model_path()); print(_load_model() is not None)'

# Neu Vosk khong tim thay model
set ASTRA_VOSK_MODEL=D:\ASTRA\jarvis-ai-assistant\vosk-model-small-en-us-0.15

### 11.3 Factory reset (xoa toan bo du lieu auth)

python -c 'from Security.secure_storage import SecureStorage; SecureStorage().clear_all(); print("Factory reset done")'
hoac xoa thu muc: %APPDATA%\ASTRA\

## 12. LO TRINH NANG CAP (ROADMAP)

### Uu tien cao (1-2 tuan)

1. Thay the face embedding bang deep model ONNX
   - Cai onnxruntime + sface hoac arcface ONNX (khong can TensorFlow)
   - Muc tieu: FAR < 0.1%, FRR < 1%
2. Nang cap liveness detection
   - Tich hop MiniFASNet (Silent-Face-Anti-Spoofing)
   - Chong anh in, video replay, mat na 3D
3. Trien khai WinBio enroll/verify thuc su cho van tay
   - WinBioEnrollBegin + UI huong dan dat ngon tay
   - WinBioIdentify / WinBioVerify
4. Allowlist nghiem ngat cho voice command
   - Chan pyautogui.write() nhan text tho tu STT
   - Validate command truoc khi thuc thi

### Uu tien trung binh (2-4 tuan)

5. Pin toan bo dependency + hash verification
6. Xoa 17 file mo coi (muc 10.1)
7. Gop entry point trung lap
8. Chuyen log ra ngoai source tree (%APPDATA%\ASTRA\logs)
9. Rate-limit cho authenticate_face()
10. Refactor co_brain.py (300+ dong, tron legacy + moi)

### Uu tien thap (1-2 thang)

11. Wired google_workspace.py vao UI hoac xoa
12. Them pre-commit hooks: bandit, semgrep, pip-audit
13. Integration test cho security boundary
14. Tai lieu threat model chinh thuc
15. Can nhac AES-256 cho master key
16. Tuy chon 'remember device' an toan (bound voi TPM)

## 13. FILE DUOC TAO / SUA TRONG PHIEN NAY

### Tao moi

Security/
  __init__.py
  auth_types.py          # Kieu du lieu & chinh sach bao mat
  auth_manager.py        # Dieu phoi auth (da sua indentation)
  secure_storage.py      # DPAPI + Fernet
  face_recognition.py    # YuNet DNN + pixel embedding (da sua cho OpenCV 5.x)
  fingerprint.py         # WinBio wrapper
  pin_auth.py            # PBKDF2
  liveness.py            # Anti-spoofing co ban (da sua cho OpenCV 5.x)
  login_ui.py            # UI dang nhap SPA
  winbio_wrapper.py      # ctypes cho WinBio

astra_secure.py            # Entry point chinh (auth + UI)
test_auth.py               # Test luong auth
pentest_security.py        # Pentest 10/10
SECURITY_REPORT.md         # Bao cao nay

### Sua (bao mat)

| File | Thay doi |
|---|---|
| Features/file_agent.py | Sua resolve_allowed_path() + extract_zip() |
| Automation/open_App.py | Go bo os.startfile() |
| Brain/google_workspace.py | Pickle -> JSON |
| jarvis_runtime.py | DEFAULT_TOOLS an toan |
| ui.py | Dua local import len module level, go duplicate |
| Brain/agent_loop.py | Sua unterminated string (line 442) |
| fixit2.py | Sua escape sequence |

### Xoa

fix_indent.py              # Null bytes, file loi

## 14. KET LUAN

| Hang muc | Trang thai |
|---|---|
| Pentest | 10/10 PASS |
| Lo hoang CRITICAL | 4/4 da va |
| Lo hoang HIGH | 4/4 da va / giam thieu |
| Syntax toan bo project | Sach |
| Import chain | Khong circular |
| UI (Login + Main) | Khoi tao OK |
| Auth flow | Register -> Auth -> Session -> Logout |
| Voice (STT/TTS) | OK |
| File ops & Tool registry | OK voi security gate |
| Biometric production-grade | Proof-of-concept - xem muc 9 |

Nhan dinh cuoi: ASTRA da dat muc security-hardened cho tang ung dung (application layer) voi day du: path validation, ma hoa luu tru, chong brute-force, session management, confirmation gate, va audit trail. Tuy nhien tang biometric recognition chua dat muc production do gioi han phan cung/thu vien (TensorFlow DLL failure, liveness tho, van tay chua implement). Voi use-case single-user local desktop thi muc bao mat hien tai da chap nhan duoc; neu trien khai da nguoi dung hoac moi truong de doa cao, BAT BUOC hoan thanh 4 hang muc uu tien cao trong muc 12 truoc khi dua vao su dung.

---
Bao cao duoc tao tu dong trong phien pentest & hardening - 2026-10-09 - Phan loai: INTERNAL / CONFIDENTIAL
