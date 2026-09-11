# 📋 ClassLog 課堂行為管理系統

> 源於課堂記錄，服務於學校管理與教育效率

## 📖 專案簡介

ClassLog 是一套專為中小學晚自習、課堂管理場景設計的**課堂行為記錄與管理系統**。它最初是為了解決教師手工記錄學生行為繁瑣、易錯、耗時的問題而開發，經過多輪迭代，已成長為一款功能全面、權限清晰、資料安全的輕量級 Web 應用。

系統支持**學生、記錄員、管理員、超級管理員**四級權限，可記錄學生的**獎勵、懲罰、在校表現**等行為，並自動透過 AI 分類、郵件提醒、螢幕廣播等方式提升管理效率。資料儲存採用 JSON 檔案（後續版本計劃遷移至 SQLite），部署簡單，適合校園內網或私有伺服器使用。

---

## ✨ 核心功能

### 🧑‍🏫 多角色權限體系
| 等級 | 角色 | 主要權限 |
|------|------|----------|
| 1 | 學生 | 查看自己的行為記錄，設定個人密碼 |
| 2 | 記錄員 | 新增、刪除本班學生記錄，管理個人資訊 |
| 3 | 教師/三級管理員 | 匯入學生、審批學生註冊、生成 AI 日報、發送螢幕廣播 |
| 4 | 管理員 | 查看所有班級，使用者管理（部分）、匯出資料、IP 日誌、班級重新命名、審批教師、AI 分析 |
| 5 | 超級管理員 | 所有功能，包括功能權限設定、郵件設定、貢獻名單編輯、影片錄製與查看、刪除使用者、修改等級 |

### 📝 行為記錄與 AI 分類
- 支援自訂行為模板（積木），包括**獎勵、懲罰、在校表現**三大類別及細分子類別。
- 管理員可新增模板，系統自動呼叫**豆包 (Doubao)** AI 模型進行智慧分類，或手動修改分類。
- 新增記錄時，可透過關鍵字搜尋和分類篩選快速選擇行為模板。

### 📊 資料匯出
- 匯出 Excel 表格：包含**所有班級工作表 + 三個彙總表（獎勵/懲罰/在校表現）**，需動態密碼驗證。
- 匯出圖片：支援單個工作表 PNG 匯出，或全部工作表打包為加密 ZIP（使用當前帳戶密碼加密）。
- 動態密碼：每 5 分鐘自動重新整理，供四級及以上使用者查看，確保匯出安全。

### 📧 郵件提醒
- 當某班級學生被記錄「懲罰」類行為時，系統自動向該班級所有綁定且填寫了信箱的教師/記錄員發送提醒郵件。
- SMTP 設定支援 Outlook、QQ 信箱等，建議使用應用程式專用密碼。

### 📢 螢幕廣播
- 三級及以上使用者可向指定班級、學生或低等級帳戶發送強制廣播。
- 接收端以全螢幕飄窗形式展示，8 秒後自動消失，且廣播期間阻止操作。

### 🎥 影片錄製與加密
- 五級管理員可錄製攝影機影片，影片自動使用 Fernet 加密後儲存為 `.vidat` 檔案。
- 支援線上影片列表查看與播放（需管理員權限），確保敏感內容安全。

### 🌐 IP 操作日誌
- 系統記錄每次請求的 IP、使用者、方法、路徑、時間及 User-Agent，四級以上使用者可按 IP 分組查看，便於安全稽核。

### 🏆 貢獻名單
- 展示專案貢獻者資訊，五級管理員可新增或刪除貢獻條目。

### ⚙️ 其他管理功能
- 班級管理：支援班級重新命名、班級綁定、擴班審批。
- 學生管理：批次匯入、密碼重設（重設為初始密碼 `12345678`）。
- 帳戶設定：使用者可修改使用者名稱、密碼、真實姓名、信箱和綁定班級。
- 動態密碼匯出：匯出 Excel 時需輸入動態密碼，圖片匯出無需密碼。
- 郵件設定：設定 SMTP 伺服器資訊，用於自動發送提醒郵件。

---

## 🛠 技術棧

- **後端框架**：Flask（Python 3.10+）
- **伺服器**：Waitress（可選 Werkzeug 開發伺服器）
- **儲存**：JSON 檔案（當前版本），計劃遷移至 SQLite
- **AI 整合**：DeepSeek（自動日報）、豆包（行為分類）
- **影片加密**：cryptography (Fernet)
- **Excel 匯出**：openpyxl
- **圖片生成**：Pillow
- **ZIP 加密**：pyzipper
- **系統托盤**：pystray
- **前端**：HTML + CSS + JavaScript（原生，無框架）

---

## 📁 專案結構

```
ClassLog/
├── run.py
├── requirements.txt
├── .gitignore
├── LICENSE
├── deepseek.key                  # 需手動建立，寫入 DeepSeek API Key
├── doubao.key                    # 需手動建立，寫入豆包 API Key
├── fullchain.pem                 # SSL 憑證（可選，放在根目錄）
├── privkey.pem                   # SSL 私鑰（可選，放在根目錄）
├── credits.json                  # 貢獻名單資料（系統自動生成）
├── AppDate/                      # 資料目錄（系統自動建立）
│   ├── staff.json                # 教職工帳戶資料
│   ├── actions.json              # 行為積木資料
│   ├── config.json               # 系統設定（含SMTP、功能權限、TOTP金鑰）
│   ├── reports.json              # AI 報告
│   ├── read_status.json          # 已讀狀態
│   ├── pending_approvals.json    # 教師註冊審批
│   ├── student_pending_approvals.json # 學生註冊審批
│   ├── pending_class_requests.json    # 擴班請求
│   ├── password_reset_requests.json   # 密碼重設申請
│   ├── reset_keys.json           # 重設金鑰
│   ├── audit_logs.json           # IP 操作日誌
│   └── 班級資料夾/                # 每個班級一個資料夾（如「初一12班」）
│       └── students.json         # 該班學生資料及記錄
├── log/                          # 執行日誌（可選）
├── video_storage/                # 加密影片檔案（.vidat）
├── python_package/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── helpers.py
│   ├── decorators.py
│   ├── ntp.py
│   ├── ai.py
│   ├── export.py
│   ├── video.py
│   ├── email_utils.py
│   ├── broadcast.py
│   ├── auth_routes.py
│   ├── admin_routes.py
│   ├── recorder_routes.py
│   ├── student_routes.py
│   ├── api_routes.py
│   └── main.py
└── templates/
    ├── base.html
    ├── simple_base.html
    ├── intro.html
    ├── login.html
    ├── register.html
    ├── select_class.html
    ├── select_student.html
    ├── student_select.html
    ├── student_password.html
    ├── forgot_password.html
    ├── admin.html
    ├── recorder.html
    ├── student.html
    ├── logs.html
    ├── users.html
    ├── actions.html
    ├── ai.html
    ├── ai_select.html
    ├── approvals.html
    ├── addstaff.html
    ├── assign_classes.html
    ├── select_classes.html
    ├── pending_classes.html
    ├── bind_classes.html
    ├── config.html
    ├── export_password.html
    ├── feature_permissions.html
    ├── video_record.html
    ├── video_list.html
    ├── broadcast.html
    ├── broadcast_send.html
    ├── broadcast_view.html
    ├── show_summary.html
    ├── feedback.html
    ├── feature_request.html
    ├── honor_bank.html
    ├── rename_class.html
    ├── credits.html
    ├── email_settings.html
    ├── ip_logs.html
    └── 404.html
    └── broadcast_check.html
```

---

## 🚀 安裝與執行

### 環境要求
- Windows 10/11 或 Linux（推薦 Windows）
- Python 3.10+
- 可選：OpenSSL（用於憑證轉換）

### 安裝依賴
-使用阿里雲加速進行安裝 python 擴充庫

```bash
pip install flask waitress pystray pillow requests openpyxl cryptography markdown ntplib opencv-python numpy openai matplotlib pandas pyzipper -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
```

### 設定 API Key
在專案根目錄建立兩個文字檔案：
- `deepseek.key`：寫入 DeepSeek API Key
- `doubao.key`：寫入火山方舟（豆包）API Key

### 啟動系統
-方法一、需要在檔案目錄的 cmd 或其他終端

```bash
python run.py
```

### 預設帳戶
| 使用者名稱 | 密碼 | 角色 |
|--------|------|------|
| admin  | admin123 | 超級管理員 |

> ⚠️ 首次登入後請立即修改預設密碼。

---

## 🔒 安全說明

- **憑證**：系統支持 HTTPS，請設定有效的 SSL 憑證（如 Let's Encrypt 或自簽憑證）。
- **密碼**：使用者密碼儲存於 JSON 檔案中，建議遷移至 SQLite 並使用雜湊儲存（未來版本）。
- **動態密碼**：用於匯出 Excel 時二次驗證，每 5 分鐘自動更換。
- **稽核日誌**：記錄所有請求 IP 和操作，便於追蹤異常。
- **影片加密**：錄製的影片檔案以加密格式儲存，需系統內解密播放。

---

## 📈 後續規劃

- [ ] 資料儲存遷移至 SQLite
- [ ] 使用 WebSocket 優化廣播即時性
- [ ] 增加人臉簽到功能
- [ ] 行動端適配優化
- [ ] 密碼雜湊儲存

---

## 👥 貢獻者

感謝以下人員為 ClassLog 做出的貢獻：
- 高梓駿（專案發起人 & 主要開發者）
- 李梓瑞（後期資料歸類）

（可在系統中「貢獻名單」頁面動態維護）

---

## 📄 授權條款

本專案採用**自訂授權條款**：允許個人內部管理用途使用、修改，但禁止商業和大型場所等非個人用途及未經授權電子合約授權的修改版散布。詳見 `LICENSE` 檔案。

---

## 📧 聯絡方式

- 專案位址：`https://github.com/gao-zijun/ClassLog`
- 電子郵件-個人：`gao18510303466@outlook.com`
- 電子遊戲-專案：`classlogpro@outlook.com`
- 問題回饋：請在倉庫 Issues 中提交

---

**ClassLog** —— 讓課堂行為管理更簡單、更智慧。
