import os
from flask import Blueprint, render_template, request, redirect, url_for, session
from . import models, config
from .decorators import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        pending = models.load_pending_approvals()
        for p in pending:
            if p['username'] == username:
                return render_template('login.html', error='账户正在等待管理员审批，请耐心等待')
        staff = models.load_staff()
        user = staff.get(username)
        if user and user.get('level', 0) >= 2:
            stored_pw = user.get('password', '')
            if not password:
                return render_template('login.html', error='密码不能为空')
            if stored_pw == password:
                session['username'] = username
                session['role'] = user['role']
                session['level'] = user['level']
                if models.get_must_select_classes(username):
                    return redirect(url_for('auth.select_my_classes'))
                return redirect(url_for('admin.admin') if user['role'] == 'admin' else url_for('recorder.recorder'))
        return render_template('login.html', error='账号或密码错误，或无权登录')
    return render_template('login.html', error=None)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    staff = models.load_staff()
    teachers = {u: i for u, i in staff.items() if i.get('level') == 3}
    if request.method == 'POST':
        role = request.form['role']
        if role == 'student':
            student_name = request.form['student_name'].strip()
            teacher = request.form['teacher'].strip()
            if not student_name or not teacher:
                return render_template('register.html', error='请填写完整信息', teachers=teachers)
            pending = models.load_student_pending_approvals()
            if any(p['student_name'] == student_name and p['teacher'] == teacher and p['status'] == 'pending' for p in pending):
                return render_template('register.html', error='你已提交过申请，请耐心等待', teachers=teachers)
            pending.append({"student_name": student_name, "teacher": teacher, "status": "pending"})
            models.save_student_pending_approvals(pending)
            return render_template('register.html', msg='申请已提交，请等待教师审批', teachers={})
        elif role == 'teacher':
            username = request.form['username'].strip()
            password = request.form['password'].strip()
            class_name = request.form['class_name'].strip()
            if not username or not class_name:
                return render_template('register.html', error='请填写完整信息', teachers=teachers)
            staff = models.load_staff()
            if username in staff:
                return render_template('register.html', error='用户名已存在', teachers=teachers)
            pending = models.load_pending_approvals()
            if any(p['username'] == username for p in pending):
                return render_template('register.html', error='该用户名已提交审批', teachers=teachers)
            if password and not (8 <= len(password) <= 16):
                return render_template('register.html', error='密码长度必须为8-16位', teachers=teachers)
            pending.append({
                "username": username, "password": password,
                "class_name": class_name, "name": username,
                "role": "admin", "level": 3
            })
            models.save_pending_approvals(pending)
            return render_template('register.html', msg='注册已提交，请等待管理员审批', teachers={})
    return render_template('register.html', error=None, teachers=teachers)

@auth_bp.route('/select-class')
def select_class():
    classes = [f for f in os.listdir(config.DATA_DIR) if os.path.isdir(os.path.join(config.DATA_DIR, f))]
    return render_template('select_class.html', classes=sorted(classes))

@auth_bp.route('/select-student')
def select_student():
    class_name = request.args.get('class_name', '')
    students = models.load_class_students(class_name)
    student_names = list(students.keys())
    if not student_names:
        return redirect(url_for('auth.select_class'))
    return render_template('student_select.html', students=student_names, current_class=class_name)

@auth_bp.route('/student-login', methods=['POST'])
def student_login():
    selected = request.form.get('student_name')
    class_name = request.form.get('class_name', '')
    students = models.load_class_students(class_name)
    if selected in students and students[selected]['role'] == 'student':
        user = students[selected]
        if user.get('password', '') == '':
            session['username'] = selected
            session['role'] = 'student'
            session['level'] = 1
            return redirect(url_for('student.student'))
        else:
            session['pending_student'] = selected
            session['pending_class'] = class_name
            return redirect(url_for('auth.student_password'))
    return redirect(url_for('auth.select_student', class_name=class_name))

@auth_bp.route('/student-password', methods=['GET', 'POST'])
def student_password():
    if 'pending_student' not in session:
        return redirect(url_for('auth.select_class'))
    class_name = session.get('pending_class', '')
    if request.method == 'POST':
        password = request.form.get('password', '')
        students = models.load_class_students(class_name)
        pending = session['pending_student']
        if pending in students and students[pending]['password'] == password:
            session.pop('pending_student', None)
            session.pop('pending_class', None)
            session['username'] = pending
            session['role'] = 'student'
            session['level'] = 1
            return redirect(url_for('student.student'))
        else:
            return render_template('student_password.html', student_name=pending, error='密码错误')
    return render_template('student_password.html', student_name=session['pending_student'], error=None)

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/select-my-classes', methods=['GET', 'POST'])
@login_required(min_level=2)
def select_my_classes():
    username = session['username']
    existing_classes = models.get_user_classes(username)
    all_classes = sorted([f for f in os.listdir(config.DATA_DIR) if os.path.isdir(os.path.join(config.DATA_DIR, f))])
    staff = models.load_staff()
    current_name = staff.get(username, {}).get('name', username)
    if request.method == 'POST':
        selected = request.form.getlist('classes')
        selected = [c for c in selected if c]
        formal = selected[:2] if len(selected) > 2 else selected
        pending = selected[2:] if len(selected) > 2 else []
        models.set_user_classes(username, formal)
        if pending:
            models.add_pending_class_request(username, pending)
        models.set_must_select_classes(username, False)
        real_name = request.form.get('real_name', '').strip()
        if real_name:
            models.set_user_name(username, real_name)
        return redirect(url_for('admin.admin') if session.get('role') == 'admin' else url_for('recorder.recorder'))
    return render_template('select_classes.html', existing=existing_classes, all_classes=all_classes, current_name=current_name)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    step = request.form.get('step', '1')
    username = request.form.get('username', '').strip()
    if request.method == 'POST' and step == '1':
        staff = models.load_staff()
        user = staff.get(username)
        if user and user.get('level', 0) >= 2:
            return render_template('forgot_password.html', username=username, step='2')
        else:
            return render_template('forgot_password.html', error='用户名不存在或无权限（需要二级及以上）', step='1')
    elif request.method == 'POST' and step == '2':
        action = request.form.get('action')
        username = request.form.get('username')
        if action == 'submit_key':
            key = request.form.get('reset_key', '').strip()
            if models.verify_reset_key(username, key):
                staff = models.load_staff()
                if username in staff:
                    staff[username]['password'] = '12345678'
                    models.save_staff(staff)
                return render_template('forgot_password.html', step='success', msg='密码已重置为 12345678，请返回登录')
            else:
                return render_template('forgot_password.html', username=username, step='2', error='密钥无效或已过期')
        elif action == 'submit_apply':
            models.add_password_reset_request(username)
            return render_template('forgot_password.html', step='success', msg='申请已提交，请等待管理员审批')
        else:
            return redirect(url_for('auth.forgot_password'))
    return render_template('forgot_password.html', step='1')