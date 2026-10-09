# HƯỚNG DẪN KHỞI CHẠY VÀ SỬ DỤNG ASTRA

> **ASTRA** — Local-First AI Command Center  
> Phiên bản: 2026-10-09 | Chủ sở hữu: **Dannz** | Python ≥ 3.10 | Windows 10/11

---

## 1. YÊU CẦU HỆ THỐNG

| Thành phần | Yêu cầu |
|------------|---------|
| **Python** | 3.10+ (khuyên dùng 3.11) |
| **Ollama** | Cài đặt và chạy model `qwen2.5:1.5b` (mặc định) |
| **Vosk Models** | English (`vosk-model-small-en-us-0.15`) + Vietnamese (`vosk-model-small-vn-0.4`) |
| **Microphone & Speakers** | Hoạt động bình thường |
| **Google Chrome** | Cần cho Automation web |
| **Windows 10/11** | SAPI TTS, UIA Automation, Windows Hello |

---

## 2. CÀI ĐẶT

### 2.1 Clone & Môi trường ảo

```bash
git clone https://github.com/AnubhavChaturvedi-GitHub/jarvis-ai-assistant.git
cd jarvis-ai-assistant

# Tạo virtual environment
py -3.11 -m venv .venv
.venv\Scripts\activate

# Cài dependencies
.venv\Scripts\python -m pip install -r requirements.txt
```

### 2.2 Cài đặt Vosk Models (BẮT BUỘC cho STT)

```bash
# English (~40 MB)
.venv\Scripts\python download_vosk_model.py small-en-us-0.15

# Vietnamese (~40 MB)
.venv\Scripts\python download_vosk_model.py small-vn-0.4
```

Models sẽ được đặt tại thư mục gốc project:
```
D:\ASTRA\jarvis-ai-assistant\vosk-model-small-en-us-0.15\
D:\ASTRA\jarvis-ai-assistant\vosk-model-small-vn-0.4\
```

### 2.3 Khởi động Ollama & Pull Model

```bash
# Khởi động Ollama service
ollama serve

# Pull model mặc định (trong terminal khác)
ollama pull qwen2.5:1.5b

# Hoặc model mạnh hơn
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

---

## 3. KHỞI CHẠY ỨNG DỤNG

### 3.1 Giao diện Desktop Command Center (Khuyên dùng)

```bash
.venv\Scripts\python ui.py
```

- Cửa sổ **AstraWindow** hiện ra (1440×900, có thể maximize)
- 6 trang chính: **Command Center**, **Conversations**, **Agent Loop**, **Voice Interface**, **Tools & Skills**, **Memory**
- Orb thần kinh ở trung tâm hiển thị trạng thái real-time

### 3.2 Chế độ Secure (Yêu cầu đăng nhập)

```bash
.venv\Scripts\python astra_secure.py
# hoặc
.venv\Scripts\python start_secure.py
```

- Màn hình Login hiển thị (Starfield + Glass container)
- Hỗ trợ: PIN, Password, Face ID, Fingerprint, Windows Hello
- Sau khi xác thực thành công → tự mở AstraWindow

### 3.3 Chế độ Voice-only (Không UI)

```bash
.venv\Scripts\python jarvis.py
```

- Chạy nền, lắng nghe wake word → xử lý → nói phản hồi
- Phù hợp cho headless/background

### 3.4 Web Visualizer (Thử nghiệm)

```bash
# Terminal 1: Khởi động Web Bridge Server
.venv\Scripts\python web_bridge.py --port 8765

# Terminal 2: Mở trình duyệt
# http://127.0.0.1:8765
```

- Three.js/WebGL Orb với GLSL shaders
- Real-time sync với Python qua WebSocket (`/ws`)

---

## 4. CẤU TRÚC GIAO DIỆN (AstraWindow)

### 4.1 Sidebar (Bên trái)
| Khu vực | Chức năng |
|---------|-----------|
| **Brand** | Logo ◉ + tên "ASTRA" + "LOCAL COMMAND CENTER" |
| **Navigation** | 6 nút chuyển trang (Command Center, Conversations, Agent Loop, Voice, Tools, Memory) |
| **Voice Status Card** | Trạng thái mic: Standby / Listening / Active / Error |
| **Privacy Note** | "LOCAL-FIRST CORE · Dannz · Ollama · OpenJarvis runtime" |

### 4.2 Command Center (Trang 0 - Mặc định)
| Vùng | Nội dung |
|------|----------|
| **Top Bar** | "PERSONAL AI · ON YOUR DEVICE" + System Badge (● SYSTEM STANDBY / ● AGENT ACTIVE) |
| **Metrics Row** | LOCAL MODEL, VOICE INPUT, VOICE OUTPUT, AGENT CORE |
| **Controls** | Model Selector, Auto Route checkbox, Agent Selector |
| **Orb Card** | OrbVisualizer (lõi trực quan) + State Label ("READY WHEN YOU ARE") |
| **Chat Card** | Transcript (read-only) + Message Input + Send + Mic Button |
| **Right Panel** | Runtime Health, Activity Feed, Quick Prompts |
| **Footer** | "LOCAL AGENT / OLLAMA / VOICE" + Clock |

### 4.3 Các trang khác
| Trang | Mô tả |
|-------|-------|
| **Conversations** | Lịch sử hội thoại (đọc file `log.txt`) |
| **Agent Loop** | Live feed Thought → Action → Observation, ô nhập Goal, danh sách Runs |
| **Voice Interface** | Mic level progress bar, Start/Stop voice listener, ghi chú Vosk/SAPI |
| **Tools & Skills** | Toggle các tool: Calculator, Web Search, Think |
| **Memory** | Bật/tắt Memory, Policy (Explicit/Ask/Do Not Save), Editor Profile, Episodic Records |

---

## 5. TƯƠNG TÁC CƠ BẢN

### 5.1 Chat văn bản
1. Nhập tin nhắn vào ô **"Message your local agent…"**
2. Nhấn **Enter** hoặc nút **Send**
3. Xem phản hồi trong Transcript
4. TTS tự động phát âm (Windows SAPI)

### 5.2 Voice (Giọng nói)
1. Nhấn nút **"Start voice"** (hoặc trang Voice Interface → "Start voice listener")
2. Orb chuyển sang **Listening** (màu xanh cyan)
3. Nói yêu cầu (Tiếng Việt/English)
4. Orb chuyển **Thinking** → **Speaking**
5. Nghe phản hồi qua loa
6. Nhấn **"Stop voice"** để dừng

> **Lưu ý**: STT dùng Vosk (offline, không cần internet). TTS dùng Windows SAPI (Microsoft David voice).

### 5.3 Agentic Mode (Đa bước)
1. Chuyển sang trang **Agent Loop**
2. Chọn Agent = **"agentic"** trong dropdown (hoặc Command Center)
3. Nhập Goal ví dụ:
   - *"Tạo file hello.py in ra 'Hello ASTRA' và chạy nó"*
   - *"Tìm file config.json trong thư mục project"*
4. Nhấn **Run agent** → Theo dõi live feed:
   ```
   [step 1] thinking...
   [step 1] thought: Cần tạo file python
     action: write_file {"path": "hello.py", "content": "print('Hello ASTRA')"}
   [step 1] observation (ok): File created
   [step 2] thought: Chạy file
     action: execute_command {"cmd": "python hello.py"}
   [step 2] observation (ok): Hello ASTRA
   === finish: File created and executed successfully ===
   ```
5. Có thể **Resume last** hoặc double-click Run ID trong danh sách để tiếp tục

### 5.4 Quản lý Memory
- **Trang Memory** → Tab **Profile & preferences**: Sửa nội dung, Save/Reload
- **Tab Episodic records**: Xem danh sách, Pin/Unpin, Delete, Clear all
- **Settings**: Bật/tắt Memory, chọn Policy:
  - **Save only when I ask** (Explicit) — mặc định
  - **Ask before saving**
  - **Do not save from chat**

---

## 6. CÁC TÍNH NĂNG NÂNG CAO

### 6.1 Automation Desktop
| Lệnh ví dụ | Hành động |
|------------|-----------|
| `"Mở Chrome"` | Launch app (allowlist) |
| `"Tìm file report.pdf"` | Tìm file trong ASTRA_FILE_ROOTS |
| `"Tạo file notes.txt với nội dung..."` | Write file |
| `"Chụp màn hình"` | Screenshot → lưu ~/.astra/screenshots/ |
| `"Click tọa độ 500, 300"` | Click chuột (bounds-checked) |
| `"Gõ text 'Xin chào'"` | Type text (clipboard paste unicode-safe) |

### 6.2 Web Search
- `"Tìm kiếm thời tiết Hà Nội hôm nay"` → DuckDuckGo scraping
- `"Tìm giải pháp lỗi Python ModuleNotFoundError"` → google_search_fix

### 6.3 Office Automation (COM)
- Word: tạo/đọc/ghi docx
- Excel: tạo/đọc/ghi xlsx
- PowerPoint: tạo slide

### 6.4 Google Workspace (Cần OAuth)
```bash
# Đặt credentials tại ~/.astra/google_credentials.json
# Lần đầu chạy sẽ mở browser xin consent
```
Hỗ trợ: Gmail, Calendar, Drive, Docs, Sheets, Slides, Tasks

### 6.5 Vision (Camera)
- `"Mô tả cái tôi đang cầm"` → Chụp ảnh camera → Ollama vision

### 6.6 Text-to-Image
- `"Tạo ảnh xe thể thao đỏ hoàng hôn"` → Gen image

---

## 7. CẤU HÌNH & TUỶ CHỈNH

### 7.1 File cấu hình
| File | Mô tả |
|------|-------|
| `settings.json` (AppData) | Model, Agent, Tools, Memory, Auto-route |
| `ASTRA_FILE_ROOTS` (env) | Thư mục gốc cho file ops (mặc định: project root) |
| `ASTRA_DANNZ_WHATSAPP` (env) | Số WhatsApp để gửi tin nhắn |

### 7.2 Biến môi trường quan trọng
```powershell
# WhatsApp
$env:ASTRA_DANNZ_WHATSAPP = "+84xxxxxxxxx"

# Ollama performance
$env:OLLAMA_MAX_LOADED_MODELS = "1"
$env:OLLAMA_NUM_PARALLEL = "1"
$env:OLLAMA_KEEP_ALIVE = "0"
```

### 7.3 Thay đổi Model mặc định
1. Command Center → Model Selector → Chọn model đã pull
2. Hoặc bật **Auto route** để ASTRA tự chọn fast/reasoning

---

## 8. XỬ LÝ SỰ CỐ THƯỜNG GẶP

| Vấn đề | Nguyên nhân | Giải pháp |
|--------|-------------|-----------|
| **ModuleNotFoundError: vosk** | Chưa cài `vosk` hoặc model | `pip install vosk` + download model |
| **Ollama timeout 30s** | Model quá lớn / CPU chậm | Dùng model nhỏ hơn (`qwen2.5:1.5b`), giảm `ASTRA_MAX_TOKENS` |
| **Mic không nghe** | Vosk model sai / mic bị mute | Kiểm tra model EN/VN, quyền micro Windows |
| **TTS không nói** | SAPI voice không có | Cài voice Microsoft David, fallback pyttsx3 |
| **UI không mở** | PyQt5 / QApplication conflict | Chạy `python ui.py` trực tiếp, không import ui ở nơi khác |
| **Agentic không chạy** | Chưa chọn agent "agentic" | Dropdown Agent → chọn "agentic" |
| **Web Bridge lỗi port** | Port 8765 bị chiếm | `web_bridge.py --port 8766` |

---

## 9. CẤU TRÚC THƯ MỤC DỰ ÁN

```
jarvis-ai-assistant/
├── ui.py                      # Entry point Desktop UI
├── jarvis.py                  # Entry point Voice-only
├── co_brain.py                # Legacy intent routing
├── jarvis_runtime.py          # Core runtime (model routing, tools, memory)
├── web_bridge.py              # aiohttp + WebSocket server
├── branding.py                # ASSISTANT_NAME, OWNER_NAME
├── astra_ui/                  # Modular PyQt components
│   ├── core/theme.py          # STYLESHEET, COLORS, mode_stylesheet
│   ├── widgets/orb.py         # OrbVisualizer (13 profiles)
│   ├── widgets/panels.py      # Card, MetricCard, HealthRow
│   ├── widgets/animations.py  # AnimationEngine
│   ├── widgets/welcome.py     # WelcomeScreen
│   ├── widgets/icons.py       # SVG loader
│   └── assets.py              # load_assets()
├── Brain/                     # Core brain modules
│   ├── agent_state.py         # State machine + EventBus
│   ├── agent_loop.py          # ReAct Agent + AgentJournal
│   ├── conversation_context.py
│   ├── memory_store.py        # SQLite + embeddings
│   ├── task_store.py          # Persistent tasks
│   ├── model_router.py        # Local model selection
│   ├── tool_registry.py       # Typed tools + permissions
│   ├── local_tool_router.py   # Regex fast-path
│   ├── orb_bridge.py          # Python ↔ Three.js bridge
│   ├── logger.py              # Centralized logging
│   ├── barge_in.py            # Acoustic barge-in
│   ├── multistep_planner.py   # Durable planner
│   └── google_workspace.py    # OAuth clients
├── Security/                  # Auth & Biometrics
│   ├── auth_manager.py        # Central orchestration
│   ├── pin_auth.py            # PBKDF2 PIN
│   ├── secure_storage.py      # Fernet encryption
│   ├── face_recognition.py    # OpenCV LBPH
│   ├── fingerprint.py         # Windows Biometric Framework
│   ├── liveness.py            # Anti-spoofing
│   ├── winbio_wrapper.py      # Windows Hello
│   └── login_ui.py            # Holographic login
├── Automation/                # Desktop control
│   ├── Automation_Brain.py
│   ├── open_App.py            # App allowlist
│   ├── office_automation.py   # Word/Excel/PPT COM
│   ├── windows_uia.py         # UIA adapter
│   └── Youtube_play_back.py   # Media keys
├── Features/                  # System utils
│   ├── file_agent.py
│   ├── mike_health.py
│   ├── speaker_health.py
│   ├── br_persentage.py
│   ├── set_br.py
│   ├── check_running_app.py
│   └── set_get_volume.py
├── NetHyTechSTT/              # Vosk STT
├── TextToSpeech/              # SAPI + pyttsx3
├── Vision/                    # Camera + Ollama vision
├── Real_Time/                 # Web search
├── TextToImage/               # Image generation
├── public/                    # Three.js WebGL Orb
│   ├── index.html
│   ├── orb.js
│   ├── audio.js
│   ├── planner.js
│   └── workspace.js
├── vosk-model-small-en-us-0.15/
├── vosk-model-small-vn-0.4/
└── requirements.txt
```

---

## 10. PHÍM TẮT (SHORTCUTS)

| Phím | Hành động |
|------|-----------|
| `Ctrl + Enter` | Gửi tin nhắn (trong chat) |
| `Ctrl + K` | (Dự định) Command Palette |
| `Esc` | Hủy voice / đóng dialog |

---

## 11. LOG & DEBUG

| File | Mô tả |
|------|-------|
| `log.txt` (project root) | Session chat log (User / ASTRA / runtime / tool) |
| `~/.astra/agent_journal.sqlite3` | Agentic runs journal |
| `~/.astra/memory.sqlite3` | Persistent memory |
| `~/.astra/tasks.sqlite3` | Task store |
| `~/.astra/screenshots/` | Screenshots từ automation |

**Xem log real-time**: Trang Command Center → Activity Feed tự cập nhật mỗi 350ms

---

## 12. BÁO CÁO LỖI / ĐÓNG GÓP

1. **Issues**: Mở GitHub Issues mô tả lỗi, steps to reproduce, log snippet
2. **PR**: Fork → feature branch → PR với mô tả rõ ràng
3. **Logs cần kèm**: `log.txt`, error traceback, Ollama model version

---

## 13. GIẤY PHÉP & CHỦ SỞ HỮU

- **License**: MIT
- **Owner**: **Dannz**
- **Repo**: https://github.com/AnubhavChaturvedi-GitHub/jarvis-ai-assistant

---

## 14. CHECKLIST KHỞI CHẠY NHANH (QUICK START)

```
[ ] Python 3.11 + venv activated
[ ] Ollama serve running
[ ] ollama pull qwen2.5:1.5b
[ ] Vosk models downloaded (EN + VN)
[ ] Microphone & Speakers working
[ ] pip install -r requirements.txt
[ ] python ui.py
[ ] Chọn Model + Agent trong Command Center
[ ] Test: "Xin chào ASTRA" (chat hoặc voice)
[ ] Test Agentic: "Tạo file test.py in ra 123"
```

---

**Chúc bạn trải nghiệm tốt với ASTRA! 🚀**  
*Local-First · Voice-First · Agentic · Private*