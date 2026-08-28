import os
import json
import time
import hashlib
import hmac
import string
import random
import sqlite3
import threading
from . import config

# ==================== 数据库初始化与连接 ====================
DB_FILE = config.DB_FILE
DB_LOCK = threading.RLock()   # 可重入锁，确保线程安全

def get_conn():
    """获取数据库连接，启用 WAL 模式提升并发"""
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """初始化数据库表和默认数据"""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with DB_LOCK:
        conn = get_conn()
        try:
            # 工作人员表
            conn.execute('''CREATE TABLE IF NOT EXISTS staff (
                username TEXT PRIMARY KEY,
                password TEXT,
                role TEXT,
                level INTEGER,
                name TEXT,
                class TEXT,
                classes TEXT,
                must_select_classes INTEGER DEFAULT 0,
                test_account INTEGER DEFAULT 0,
                email TEXT
            )''')
            # 行为积木表
            conn.execute('''CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                template TEXT,
                params TEXT,
                param_labels TEXT,
                category TEXT,
                subcategory TEXT,
                status TEXT
            )''')
            # 学生表（按班级存储，使用联合主键）
            conn.execute('''CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT,
                username TEXT,
                password TEXT,
                role TEXT,
                level INTEGER,
                name TEXT,
                records TEXT,
                UNIQUE(class_name, username)
            )''')
            # 配置表（存储整个配置字典）
            conn.execute('''CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )''')
            # 报告表
            conn.execute('''CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                time TEXT,
                content TEXT,
                type TEXT,
                scope TEXT
            )''')
            # 已读状态表
            conn.execute('''CREATE TABLE IF NOT EXISTS read_status (
                username TEXT PRIMARY KEY,
                status INTEGER DEFAULT 1
            )''')
            # 教师审批表
            conn.execute('''CREATE TABLE IF NOT EXISTS pending_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                password TEXT,
                class_name TEXT,
                name TEXT,
                role TEXT,
                level INTEGER
            )''')
            # 学生注册审批表
            conn.execute('''CREATE TABLE IF NOT EXISTS student_pending_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT,
                teacher TEXT,
                status TEXT
            )''')
            # 扩班请求表
            conn.execute('''CREATE TABLE IF NOT EXISTS pending_class_requests (
                username TEXT,
                class_name TEXT,
                PRIMARY KEY(username, class_name)
            )''')
            # 密码重置请求表
            conn.execute('''CREATE TABLE IF NOT EXISTS password_reset_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                status TEXT,
                timestamp TEXT
            )''')
            # 重置密钥表
            conn.execute('''CREATE TABLE IF NOT EXISTS reset_keys (
                username TEXT PRIMARY KEY,
                key TEXT,
                expire REAL
            )''')
            # 审计日志表
            conn.execute('''CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT,
                user TEXT,
                method TEXT,
                path TEXT,
                time TEXT,
                user_agent TEXT
            )''')
            # 贡献名单表
            conn.execute('''CREATE TABLE IF NOT EXISTS credits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                contribution TEXT
            )''')

            # 初始化默认数据（仅当表为空时）
            init_default_data(conn)
        finally:
            conn.close()

def init_default_data(conn):
    """在首次运行时插入默认员工、积木和配置"""
    # 工作人员
    cur = conn.execute("SELECT COUNT(*) FROM staff")
    if cur.fetchone()[0] == 0:
        default_staff = [
            ("admin", "gao201343", "admin", 5, "管理员", "", "[]", 0, 0, ""),
            ("kfzh", "", "recorder", 2, "记录员", "", "[]", 0, 0, ""),
            ("zhang", "zhang123", "admin", 3, "章老师", "", "[]", 0, 0, ""),
            ("test", "12345678", "admin", 4, "测试账户", "", "[]", 0, 1, ""),
        ]
        conn.executemany('''INSERT INTO staff (username, password, role, level, name, class, classes, must_select_classes, test_account, email)
                            VALUES (?,?,?,?,?,?,?,?,?,?)''', default_staff)

    # 行为积木
    cur = conn.execute("SELECT COUNT(*) FROM actions")
    if cur.fetchone()[0] == 0:
        default_actions = [
            ("积极回答问题", "积极回答问题", "[]", "[]", "奖励", "课堂表现", ""),
            ("帮助同学", "帮助同学", "[]", "[]", "奖励", "助人为乐", ""),
            ("完成作业优秀", "完成作业优秀", "[]", "[]", "奖励", "作业表彰", ""),
            ("上课讲话", "上课讲话", "[]", "[]", "惩罚", "课堂违纪", ""),
            ("未完成作业", "未完成作业", "[]", "[]", "惩罚", "作业问题", ""),
            ("迟到", "迟到", "[]", "[]", "惩罚", "考勤违纪", ""),
        ]
        conn.executemany('''INSERT INTO actions (name, template, params, param_labels, category, subcategory, status)
                            VALUES (?,?,?,?,?,?,?)''', default_actions)

    # 配置（如果不存在则写入默认配置）
    cur = conn.execute("SELECT value FROM config WHERE key='main'")
    if cur.fetchone() is None:
        default_cfg = {
            "class_size": 40,
            "camera_source": 0,
            "feature_permissions": {
                "broadcast": 3, "export": 5, "video_webcam": 5,
                "import_students": 3, "user_management": 4, "ai_analysis": 4,
                "approvals": 4, "add_staff": 4,
                "config_size": 2, "logs": 1, "actions": 1, "account": 1
            },
            "smtp": {
                "server": "", "port": 587,
                "username": "", "password": "",
                "from": "", "encryption": "starttls"
            }
        }
        conn.execute("INSERT INTO config (key, value) VALUES ('main', ?)", (json.dumps(default_cfg),))

# 在线状态与广播队列（保留原实现，不存储到数据库）
online_users = {}
broadcast_queue = {}

def update_user_heartbeat(username):
    online_users[username] = time.time()

def is_user_online(username):
    return (time.time() - online_users.get(username, 0)) < 15

def add_broadcast_to_user(username, sender, message):
    broadcast_queue[username] = {'sender': sender, 'message': message, 'time': time.time()}

def get_and_clear_broadcast(username):
    return broadcast_queue.pop(username, None)

# ==================== 通用辅助函数 ====================
def init_data():
    """初始化数据库（替代之前的 JSON 文件初始化）"""
    init_db()

# ==================== 工作人员 ====================
def load_staff():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM staff").fetchall()
            staff = {}
            for row in rows:
                r = dict(row)
                r['classes'] = json.loads(r.get('classes', '[]'))
                r['must_select_classes'] = bool(r.get('must_select_classes', 0))
                r['test_account'] = bool(r.get('test_account', 0))
                staff[r['username']] = r
            return staff
        finally:
            conn.close()

def save_staff(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM staff")
            for username, info in data.items():
                conn.execute('''INSERT OR REPLACE INTO staff (username, password, role, level, name, class, classes, must_select_classes, test_account, email)
                                VALUES (?,?,?,?,?,?,?,?,?,?)''',
                             (username,
                              info.get('password', ''),
                              info.get('role', ''),
                              info.get('level', 1),
                              info.get('name', username),
                              info.get('class', ''),
                              json.dumps(info.get('classes', [])),
                              1 if info.get('must_select_classes', False) else 0,
                              1 if info.get('test_account', False) else 0,
                              info.get('email', '')))
            conn.commit()
        finally:
            conn.close()

def set_user_name(username, name):
    staff = load_staff()
    if username in staff:
        staff[username]['name'] = name
        save_staff(staff)

# ==================== 行为积木 ====================
def load_actions():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM actions ORDER BY id").fetchall()
            actions = []
            for row in rows:
                a = dict(row)
                a['params'] = json.loads(a.get('params', '[]'))
                a['param_labels'] = json.loads(a.get('param_labels', '[]'))
                actions.append(a)
            return actions
        finally:
            conn.close()

def save_actions(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM actions")
            for a in data:
                conn.execute('''INSERT INTO actions (name, template, params, param_labels, category, subcategory, status)
                                VALUES (?,?,?,?,?,?,?)''',
                             (a.get('name',''),
                              a.get('template',''),
                              json.dumps(a.get('params', [])),
                              json.dumps(a.get('param_labels', [])),
                              a.get('category',''),
                              a.get('subcategory',''),
                              a.get('status','')))
            conn.commit()
        finally:
            conn.close()

# ==================== 班级学生 ====================
def load_class_students(class_name):
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM students WHERE class_name=?", (class_name,)).fetchall()
            students = {}
            for row in rows:
                r = dict(row)
                r['records'] = json.loads(r.get('records', '[]'))
                students[r['username']] = r
            return students
        finally:
            conn.close()

def save_class_students(class_name, data):
    with DB_LOCK:
        conn = get_conn()
        try:
            # 先删除该班级所有学生，再重新插入（简单，适用于当前需求）
            conn.execute("DELETE FROM students WHERE class_name=?", (class_name,))
            for username, info in data.items():
                conn.execute('''INSERT INTO students (class_name, username, password, role, level, name, records)
                                VALUES (?,?,?,?,?,?,?)''',
                             (class_name,
                              username,
                              info.get('password', ''),
                              info.get('role', 'student'),
                              info.get('level', 1),
                              info.get('name', username),
                              json.dumps(info.get('records', []))))
            conn.commit()
        finally:
            conn.close()

def load_all_students():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM students").fetchall()
            students = {}
            for row in rows:
                r = dict(row)
                r['records'] = json.loads(r.get('records', '[]'))
                r['class'] = r['class_name']
                students[r['username']] = r
            return students
        finally:
            conn.close()

# ==================== 配置 ====================
def load_config():
    with DB_LOCK:
        conn = get_conn()
        try:
            row = conn.execute("SELECT value FROM config WHERE key='main'").fetchone()
            return json.loads(row['value']) if row else {}
        finally:
            conn.close()

def save_config(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('main', ?)", (json.dumps(data),))
            conn.commit()
        finally:
            conn.close()

# ==================== 报告 ====================
def load_reports():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM reports ORDER BY id").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

def save_reports(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM reports")
            for r in data:
                conn.execute('''INSERT INTO reports (date, time, content, type, scope)
                                VALUES (?,?,?,?,?)''',
                             (r.get('date',''), r.get('time',''), r.get('content',''), r.get('type',''), r.get('scope','')))
            conn.commit()
        finally:
            conn.close()

# ==================== 已读状态 ====================
def load_read_status():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT username, status FROM read_status").fetchall()
            return {r['username']: bool(r['status']) for r in rows}
        finally:
            conn.close()

def save_read_status(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM read_status")
            for username, status in data.items():
                conn.execute("INSERT INTO read_status (username, status) VALUES (?,?)",
                             (username, 1 if status else 0))
            conn.commit()
        finally:
            conn.close()

# ==================== 教师审批 ====================
def load_pending_approvals():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM pending_approvals").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

def save_pending_approvals(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM pending_approvals")
            for r in data:
                conn.execute('''INSERT INTO pending_approvals (username, password, class_name, name, role, level)
                                VALUES (?,?,?,?,?,?)''',
                             (r.get('username',''), r.get('password',''), r.get('class_name',''),
                              r.get('name',''), r.get('role',''), r.get('level',3)))
            conn.commit()
        finally:
            conn.close()

# ==================== 学生注册审批 ====================
def load_student_pending_approvals():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM student_pending_approvals").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

def save_student_pending_approvals(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM student_pending_approvals")
            for r in data:
                conn.execute('''INSERT INTO student_pending_approvals (student_name, teacher, status)
                                VALUES (?,?,?)''',
                             (r.get('student_name',''), r.get('teacher',''), r.get('status','pending')))
            conn.commit()
        finally:
            conn.close()

# ==================== 用户班级管理 ====================
def get_user_classes(username):
    staff = load_staff()
    user = staff.get(username, {})
    if 'classes' in user and isinstance(user['classes'], list):
        return user['classes']
    return [user.get('class')] if user.get('class') else []

def set_user_classes(username, classes):
    staff = load_staff()
    if username in staff:
        staff[username]['classes'] = classes
        staff[username]['class'] = classes[0] if classes else ''
        save_staff(staff)

def set_must_select_classes(username, val):
    staff = load_staff()
    if username in staff:
        staff[username]['must_select_classes'] = val
        save_staff(staff)

def get_must_select_classes(username):
    staff = load_staff()
    return staff.get(username, {}).get('must_select_classes', False)

def get_pending_class_requests():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT username, class_name FROM pending_class_requests").fetchall()
            reqs = {}
            for row in rows:
                reqs.setdefault(row['username'], []).append(row['class_name'])
            return reqs
        finally:
            conn.close()

def save_pending_class_requests(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM pending_class_requests")
            for username, classes in data.items():
                for cls in classes:
                    conn.execute("INSERT INTO pending_class_requests (username, class_name) VALUES (?,?)", (username, cls))
            conn.commit()
        finally:
            conn.close()

def add_pending_class_request(username, new_classes):
    reqs = get_pending_class_requests()
    reqs.setdefault(username, [])
    for cls in new_classes:
        if cls not in reqs[username]:
            reqs[username].append(cls)
    save_pending_class_requests(reqs)

def approve_class_request(username, class_name):
    classes = get_user_classes(username)
    if class_name not in classes:
        classes.append(class_name)
        set_user_classes(username, classes)
    reqs = get_pending_class_requests()
    if username in reqs and class_name in reqs[username]:
        reqs[username].remove(class_name)
        if not reqs[username]:
            del reqs[username]
        save_pending_class_requests(reqs)

def reject_class_request(username, class_name):
    reqs = get_pending_class_requests()
    if username in reqs and class_name in reqs[username]:
        reqs[username].remove(class_name)
        if not reqs[username]:
            del reqs[username]
        save_pending_class_requests(reqs)

# ==================== 班级过滤辅助 ====================
def get_all_class_names():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT DISTINCT class_name FROM students").fetchall()
            return sorted([r['class_name'] for r in rows])
        finally:
            conn.close()

def filter_allowed_classes(level, username):
    if level >= 4:
        return get_all_class_names()
    return get_user_classes(username)

# ==================== 密码重置相关 ====================
def load_password_reset_requests():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM password_reset_requests").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

def save_password_reset_requests(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM password_reset_requests")
            for r in data:
                conn.execute('''INSERT INTO password_reset_requests (username, status, timestamp)
                                VALUES (?,?,?)''',
                             (r.get('username',''), r.get('status','pending'), r.get('timestamp','')))
            conn.commit()
        finally:
            conn.close()

def add_password_reset_request(username):
    reqs = load_password_reset_requests()
    if not any(r['username'] == username and r['status'] == 'pending' for r in reqs):
        reqs.append({"username": username, "status": "pending", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
        save_password_reset_requests(reqs)

def remove_password_reset_request(username):
    reqs = [r for r in load_password_reset_requests() if not (r['username'] == username and r['status'] == 'pending')]
    save_password_reset_requests(reqs)

def load_reset_keys():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT username, key, expire FROM reset_keys").fetchall()
            return {r['username']: {'key': r['key'], 'expire': r['expire']} for r in rows}
        finally:
            conn.close()

def save_reset_keys(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM reset_keys")
            for username, info in data.items():
                conn.execute("INSERT INTO reset_keys (username, key, expire) VALUES (?,?,?)",
                             (username, info['key'], info['expire']))
            conn.commit()
        finally:
            conn.close()

def generate_reset_key(username):
    key = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    keys = load_reset_keys()
    keys[username] = {'key': key, 'expire': time.time() + 1800}
    save_reset_keys(keys)
    return key

def verify_reset_key(username, key):
    keys = load_reset_keys()
    if username not in keys:
        return False
    info = keys[username]
    if time.time() > info['expire'] or info['key'] != key:
        return False
    del keys[username]
    save_reset_keys(keys)
    return True

# ==================== 动态密码 (TOTP) ====================
TOTP_SECRET = None

def _get_totp_secret():
    global TOTP_SECRET
    if TOTP_SECRET:
        return TOTP_SECRET
    cfg = load_config()
    if 'totp_secret' not in cfg:
        cfg['totp_secret'] = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        save_config(cfg)
    TOTP_SECRET = cfg['totp_secret']
    return TOTP_SECRET

def generate_totp():
    secret = _get_totp_secret()
    counter = int(time.time() // 300)
    h = hmac.new(secret.encode(), counter.to_bytes(8, 'big'), hashlib.sha1).digest()
    offset = h[-1] & 0x0f
    bin_val = ((h[offset] & 0x7f) << 24) | ((h[offset+1] & 0xff) << 16) | ((h[offset+2] & 0xff) << 8) | (h[offset+3] & 0xff)
    return f'{bin_val % 10**6:06d}'

def verify_totp(pwd):
    return pwd == generate_totp()

# ==================== 贡献名单 ====================
def load_credits():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT name, contribution FROM credits").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

def save_credits(data):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM credits")
            for r in data:
                conn.execute("INSERT INTO credits (name, contribution) VALUES (?,?)",
                             (r.get('name',''), r.get('contribution','')))
            conn.commit()
        finally:
            conn.close()

# ==================== 测试账户判断 ====================
def is_test_account(username):
    staff = load_staff()
    return staff.get(username, {}).get('test_account', False)

# ==================== 绑定老师查询 ====================
def get_users_by_class(class_name):
    staff = load_staff()
    users = []
    for uname, info in staff.items():
        if info.get('role') in ('admin', 'recorder'):
            if class_name in get_user_classes(uname):
                users.append({
                    'username': uname,
                    'email': info.get('email', ''),
                    'name': info.get('name', uname)
                })
    return users

# ==================== 审计日志 ====================
def load_audit_logs():
    with DB_LOCK:
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 5000").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

def add_audit_log(entry):
    with DB_LOCK:
        conn = get_conn()
        try:
            conn.execute('''INSERT INTO audit_logs (ip, user, method, path, time, user_agent)
                            VALUES (?,?,?,?,?,?)''',
                         (entry.get('ip',''), entry.get('user',''), entry.get('method',''),
                          entry.get('path',''), entry.get('time',''), entry.get('user_agent','')))
            # 限制最多5000条，超出删除最旧的
            conn.execute("DELETE FROM audit_logs WHERE id NOT IN (SELECT id FROM audit_logs ORDER BY id DESC LIMIT 5000)")
            conn.commit()
        finally:
            conn.close()