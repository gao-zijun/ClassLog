# 📋 ClassLog 课堂行为管理系统

> 源于晚自习记录，服务于学校管理与教育效率

## 📖 项目简介

ClassLog 是一套专为中小学晚自习、课堂管理场景设计的**课堂行为记录与管理系统**。它最初是为了解决教师手工记录学生行为繁琐、易错、耗时的问题而开发，经过多轮迭代，已成长为一款功能全面、权限清晰、数据安全的轻量级 Web 应用。

系统支持**学生、记录员、管理员、超级管理员**四级权限，可记录学生的**奖励、惩罚、在校表现**等行为，并自动通过 AI 分类、邮件提醒、屏幕广播等方式提升管理效率。数据存储采用 JSON 文件（后续版本计划迁移至 SQLite），部署简单，适合校园内网或私有服务器使用。

---

## ✨ 核心功能

### 🧑‍🏫 多角色权限体系
| 等级 | 角色 | 主要权限 |
|------|------|----------|
| 1 | 学生 | 查看自己的行为记录，设置个人密码 |
| 2 | 记录员 | 添加、删除本班学生记录，管理个人信息 |
| 3 | 教师/三级管理员 | 导入学生、审批学生注册、生成 AI 日报、发送屏幕广播 |
| 4 | 管理员 | 查看所有班级，用户管理（部分）、导出数据、IP 日志、班级重命名、审批教师、AI 分析 |
| 5 | 超级管理员 | 所有功能，包括功能权限配置、邮件设置、贡献名单编辑、视频录制与查看、删除用户、修改等级 |

### 📝 行为记录与 AI 分类
- 支持自定义行为模板（积木），包括**奖励、惩罚、在校表现**三大类别及细分子类别。
- 管理员可添加新模板，系统自动调用**豆包 (Doubao)** AI 模型进行智能分类，或手动修改分类。
- 添加记录时，可通过关键词搜索和分类筛选快速选择行为模板。

### 📊 数据导出
- 导出 Excel 表格：包含**所有班级工作表 + 三个汇总表（奖励/惩罚/在校表现）**，需动态密码验证。
- 导出图片：支持单个工作表 PNG 导出，或全部工作表打包为加密 ZIP（使用当前账户密码加密）。
- 动态密码：每 5 分钟自动刷新，供四级及以上用户查看，确保导出安全。

### 📧 邮件提醒
- 当某班级学生被记录“惩罚”类行为时，系统自动向该班级所有绑定且填写了邮箱的教师/记录员发送提醒邮件。
- SMTP 配置支持 Outlook、QQ 邮箱等，建议使用应用专用密码。

### 📢 屏幕广播
- 三级及以上用户可向指定班级、学生或低等级账户发送强制广播。
- 接收端以全屏飘窗形式展示，8 秒后自动消失，且广播期间阻止操作。

### 🎥 视频录制与加密
- 五级管理员可录制摄像头视频，视频自动使用 Fernet 加密后保存为 `.vidat` 文件。
- 支持在线视频列表查看与播放（需管理员权限），确保敏感内容安全。

### 🌐 IP 操作日志
- 系统记录每次请求的 IP、用户、方法、路径、时间及 User-Agent，四级以上用户可按 IP 分组查看，便于安全审计。

### 🏆 贡献名单
- 展示项目贡献者信息，五级管理员可添加或删除贡献条目。

### ⚙️ 其他管理功能
- 班级管理：支持班级重命名、班级绑定、扩班审批。
- 学生管理：批量导入、密码重置（重置为初始密码 `12345678`）。
- 账户设置：用户可修改用户名、密码、真实姓名、邮箱和绑定班级。
- 动态密码导出：导出 Excel 时需输入动态密码，图片导出无需密码。
- 邮件设置：配置 SMTP 服务器信息，用于自动发送提醒邮件。

---

## 🛠 技术栈

- **后端框架**：Flask（Python 3.10+）
- **服务器**：Waitress（可选 Werkzeug 开发服务器）
- **存储**：JSON 文件（当前版本），计划迁移至 SQLite
- **AI 集成**：DeepSeek（自动日报）、豆包（行为分类）
- **视频加密**：cryptography (Fernet)
- **Excel 导出**：openpyxl
- **图片生成**：Pillow
- **ZIP 加密**：pyzipper
- **系统托盘**：pystray
- **前端**：HTML + CSS + JavaScript（原生，无框架）

---

## 📁 项目结构

```
ClassLog/
├── run.py
├── requirements.txt
├── .gitignore
├── LICENSE
├── deepseek.key                  # 需手动创建，写入 DeepSeek API Key
├── doubao.key                    # 需手动创建，写入豆包 API Key
├── fullchain.pem                 # SSL 证书（可选，放在根目录）
├── privkey.pem                   # SSL 私钥（可选，放在根目录）
├── credits.json                  # 贡献名单数据（系统自动生成）
├── AppDate/                      # 数据目录（系统自动创建）
│   ├── staff.json                # 教职工账户数据
│   ├── actions.json              # 行为积木数据
│   ├── config.json               # 系统配置（含SMTP、功能权限、TOTP密钥）
│   ├── reports.json              # AI 报告
│   ├── read_status.json          # 已读状态
│   ├── pending_approvals.json    # 教师注册审批
│   ├── student_pending_approvals.json # 学生注册审批
│   ├── pending_class_requests.json    # 扩班请求
│   ├── password_reset_requests.json   # 密码重置申请
│   ├── reset_keys.json           # 重置密钥
│   ├── audit_logs.json           # IP 操作日志
│   └── 班级文件夹/                # 每个班级一个文件夹（如“初一12班”）
│       └── students.json         # 该班学生数据及记录
├── log/                          # 运行日志（可选）
├── video_storage/                # 加密视频文件（.vidat）
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

## 🚀 安装与运行

### 环境要求
- Windows 10/11 或 Linux（推荐 Windows）
- Python 3.10+
- 可选：OpenSSL（用于证书转换）

### 安装依赖
```bash
pip install flask waitress pystray pillow requests openpyxl cryptography markdown ntplib opencv-python numpy openai matplotlib pandas pyzipper -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
```

### 配置 API Key
在项目根目录创建两个文本文件：
- `deepseek.key`：写入 DeepSeek API Key
- `doubao.key`：写入火山方舟（豆包）API Key

### 启动系统
```bash
python run.py
```

### 默认账户
| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin  | admin123 | 超级管理员 |

> ⚠️ 首次登录后请立即修改默认密码。

---

## 🔒 安全说明

- **证书**：系统支持 HTTPS，请配置有效的 SSL 证书（如 Let's Encrypt 或自签名证书）。
- **密码**：用户密码保存于 JSON 文件中，建议迁移至 SQLite 并使用哈希存储（未来版本）。
- **动态密码**：用于导出 Excel 时二次验证，每 5 分钟自动更换。
- **审计日志**：记录所有请求 IP 和操作，便于追踪异常。
- **视频加密**：录制的视频文件以加密格式存储，需系统内解密播放。

---

## 📈 后续规划

- [ ] 数据存储迁移至 SQLite
- [ ] 使用 WebSocket 优化广播实时性
- [ ] 增加人脸签到功能
- [ ] 移动端适配优化
- [ ] 密码哈希存储

---

## 👥 贡献者

感谢以下人员为 ClassLog 做出的贡献：
- 高梓骏（项目发起人 & 主开发者）

（可在系统中“贡献名单”页面动态维护）

---

## 📄 许可证

本项目采用**自定义许可证**：允许个人、教育和内部管理用途使用、修改，但禁止商业用途及未经授权的修改版分发。详见 `LICENSE` 文件。

---

## 📧 联系方式

- 项目地址：`https://github.com/gao-zijun/ClassLog`
- 电子邮箱-个人：`gao18510303466@outlook.com`
- 电子游戏-项目：`classlogpro@outlook.com`
- 问题反馈：请在仓库 Issues 中提交

---

**ClassLog** —— 让课堂行为管理更简单、更智能。
