from flask import session
from . import models, config


def load_students_for_classes(class_list: list) -> dict:
    result = {}
    for cls in class_list:
        students = models.load_class_students(cls)
        for uname, info in students.items():
            info['class'] = cls
            result[uname] = info
    return result


def get_feature_perms():
    cfg = models.load_config()
    perms = cfg.get('feature_permissions', {})
    defaults = {
        "broadcast": 3, "export": 5, "video_webcam": 5,
        "import_students": 3, "user_management": 4, "ai_analysis": 4,
        "model_settings": 5, "approvals": 4, "add_staff": 4,
        "config_size": 2, "logs": 1, "actions": 1, "account": 1
    }
    for k, v in defaults.items():
        if k not in perms:
            perms[k] = v
    return perms


def inject_globals():
    cfg = models.load_config()
    perms = get_feature_perms()
    username = session.get('username', '')
    level = session.get('level', 0)
    role = session.get('role', '')
    name = username
    if role == 'student':
        name = username
    elif role in ('admin', 'recorder'):
        staff = models.load_staff()
        user = staff.get(username)
        if user and user.get('name'):
            name = user['name']

    test_account = models.is_test_account(username)

    # 获取当前用户邮箱（用于账户设置显示，仅教职工角色有效）
    email = ''
    if role in ('admin', 'recorder'):
        staff = models.load_staff()
        user = staff.get(username)
        if user:
            email = user.get('email', '')

    return {
        'server_data': {
            'level': level,
            'username': username,
            'class_name': session.get('class_name', ''),
            'name': name,
            'test_account': test_account,
            'email': email
        },
        'perms': perms
    }