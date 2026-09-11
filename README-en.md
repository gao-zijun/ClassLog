# 📋 ClassLog Classroom Behavior Management System

> Originated from classroom records, serving school management and educational efficiency

## 📖 Project Introduction

ClassLog is a **classroom behavior recording and management system** designed specifically for evening self-study and classroom management scenarios in primary and secondary schools. It was initially developed to solve the problems of tedious, error-prone, and time-consuming manual student behavior recording by teachers. After multiple iterations, it has grown into a lightweight web application with comprehensive features, clear permissions, and secure data.

The system supports a four-level permission structure: **Student, Recorder, Administrator, and Super Administrator**. It can record student behaviors such as **rewards, penalties, and school performance**, and automatically improves management efficiency through AI classification, email reminders, screen broadcasts, and other methods. Data is stored in JSON files (future versions are planned to migrate to SQLite). Deployment is simple, making it suitable for campus intranets or private servers.

---

## ✨ Core Features

### 🧑‍🏫 Multi-Role Permission System
| Level | Role | Main Permissions |
|------|------|----------|
| 1 | Student | View their own behavior records, set a personal password |
| 2 | Recorder | Add and delete records for students in their own class, manage personal information |
| 3 | Teacher/Level 3 Administrator | Import students, approve student registrations, generate AI daily reports, send screen broadcasts |
| 4 | Administrator | View all classes, user management (partial), export data, IP logs, class renaming, approve teachers, AI analysis |
| 5 | Super Administrator | All functions, including feature permission configuration, email settings, contributor list editing, video recording and viewing, deleting users, modifying levels |

### 📝 Behavior Records and AI Classification
- Supports custom behavior templates (blocks), including three major categories: **Rewards, Penalties, and School Performance**, with detailed subcategories.
- Administrators can add new templates. The system automatically calls the **Doubao** AI model for intelligent classification, or classification can be modified manually.
- When adding records, behavior templates can be quickly selected through keyword search and category filtering.

### 📊 Data Export
- Export Excel spreadsheets: includes **all class worksheets + three summary sheets (Rewards/Penalties/School Performance)**, requiring dynamic password verification.
- Export images: supports PNG export of a single worksheet, or packaging all worksheets into an encrypted ZIP (encrypted with the current account password).
- Dynamic password: automatically refreshes every 5 minutes, available for Level 4 and above users to view, ensuring export security.

### 📧 Email Reminders
- When a student in a class is recorded with a “Penalty” type behavior, the system automatically sends reminder emails to all teachers/recorders in that class who are bound and have provided an email address.
- SMTP configuration supports Outlook, QQ Mail, etc. Using an app-specific password is recommended.

### 📢 Screen Broadcast
- Level 3 and above users can send forced broadcasts to specified classes, students, or lower-level accounts.
- The receiving end displays them as full-screen floating pop-ups, which automatically disappear after 8 seconds, and operations are blocked during the broadcast.

### 🎥 Video Recording and Encryption
- Level 5 administrators can record webcam videos. Videos are automatically encrypted with Fernet and saved as `.vidat` files.
- Supports online video list viewing and playback (administrator permission required), ensuring sensitive content security.

### 🌐 IP Operation Logs
- The system records the IP, user, method, path, time, and User-Agent of every request. Level 4 and above users can view them grouped by IP for security auditing.

### 🏆 Contributors List
- Displays project contributor information. Level 5 administrators can add or delete contributor entries.

### ⚙️ Other Management Features
- Class management: supports class renaming, class binding, and class expansion approval.
- Student management: batch import, password reset (reset to the initial password `12345678`).
- Account settings: users can modify username, password, real name, email, and bound class.
- Dynamic password export: a dynamic password is required when exporting Excel; image export does not require a password.
- Email settings: configure SMTP server information for automatically sending reminder emails.

---

## 🛠 Tech Stack

- **Backend Framework**: Flask (Python 3.10+)
- **Server**: Waitress (optional Werkzeug development server)
- **Storage**: JSON files (current version), planned migration to SQLite
- **AI Integration**: DeepSeek (automatic daily reports), Doubao (behavior classification)
- **Video Encryption**: cryptography (Fernet)
- **Excel Export**: openpyxl
- **Image Generation**: Pillow
- **ZIP Encryption**: pyzipper
- **System Tray**: pystray
- **Frontend**: HTML + CSS + JavaScript (vanilla, no framework)

---

## 📁 Project Structure

```
ClassLog/
├── run.py
├── requirements.txt
├── .gitignore
├── LICENSE
├── deepseek.key                  # Must be manually created; write the DeepSeek API Key into it
├── doubao.key                    # Must be manually created; write the Doubao API Key into it
├── fullchain.pem                 # SSL certificate (optional, place in root directory)
├── privkey.pem                   # SSL private key (optional, place in root directory)
├── credits.json                  # Contributor list data (auto-generated by the system)
├── AppDate/                      # Data directory (auto-created by the system)
│   ├── staff.json                # Staff account data
│   ├── actions.json              # Behavior block data
│   ├── config.json               # System configuration (including SMTP, feature permissions, TOTP keys)
│   ├── reports.json              # AI reports
│   ├── read_status.json          # Read status
│   ├── pending_approvals.json    # Teacher registration approvals
│   ├── student_pending_approvals.json # Student registration approvals
│   ├── pending_class_requests.json    # Class expansion requests
│   ├── password_reset_requests.json   # Password reset requests
│   ├── reset_keys.json           # Reset keys
│   ├── audit_logs.json           # IP operation logs
│   └── class_folder/             # One folder per class (e.g., “Grade 7 Class 12”)
│       └── students.json         # Student data and records for that class
├── log/                          # Runtime logs (optional)
├── video_storage/                # Encrypted video files (.vidat)
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

## 🚀 Installation and Running

### Requirements
- Windows 10/11 or Linux (Windows recommended)
- Python 3.10+
- Optional: OpenSSL (for certificate conversion)

### Install Dependencies
- Use Aliyun acceleration to install Python extension libraries

```bash
pip install flask waitress pystray pillow requests openpyxl cryptography markdown ntplib opencv-python numpy openai matplotlib pandas pyzipper -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
```

### Configure API Keys
Create two text files in the project root directory:
- `deepseek.key`: write the DeepSeek API Key into it
- `doubao.key`: write the Volcano Ark (Doubao) API Key into it

### Start the System
- Method 1: run in cmd or another terminal in the file directory

```bash
python run.py
```

### Default Account
| Username | Password | Role |
|--------|------|------|
| admin  | admin123 | Super Administrator |

> ⚠️ Please change the default password immediately after first login.

---

## 🔒 Security Notes

- **Certificate**: The system supports HTTPS. Please configure a valid SSL certificate (e.g., Let's Encrypt or a self-signed certificate).
- **Passwords**: User passwords are stored in JSON files. It is recommended to migrate to SQLite and use hashed storage (future version).
- **Dynamic Password**: Used for secondary verification when exporting Excel, and automatically changes every 5 minutes.
- **Audit Logs**: Records all request IPs and operations for tracking anomalies.
- **Video Encryption**: Recorded video files are stored in encrypted format and require in-system decryption for playback.

---

## 📈 Future Plans

- [ ] Migrate data storage to SQLite
- [ ] Use WebSocket to optimize broadcast real-time performance
- [ ] Add face check-in functionality
- [ ] Optimize mobile adaptation
- [ ] Password hash storage

---

## 👥 Contributors

Thanks to the following people for their contributions to ClassLog:
- Gao Zijun (Project Founder & Lead Developer)
- Li Zirui (Later data categorization)

(Can be dynamically maintained on the “Contributors List” page in the system)

---

## 📄 License

This project uses a **custom license**: it allows use and modification for personal internal management purposes, but prohibits commercial and large-scale non-personal use, as well as distribution of modified versions without authorization via electronic contract. See the `LICENSE` file for details.

---

## 📧 Contact

- Project URL: `https://github.com/gao-zijun/ClassLog`
- Personal email: `gao18510303466@outlook.com`
- Project email: `classlogpro@outlook.com`
- Feedback: Please submit in the repository Issues

---

**ClassLog** — Making classroom behavior management simpler and smarter.
