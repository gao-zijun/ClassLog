import re
import os
import threading
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, send_file, Response

from . import models, config, utils, video
from .decorators import login_required
from .helpers import load_students_for_classes, get_feature_perms
from .ntp import ntp_time
from .ai import call_deepseek, generate_daily_report, classify_action
from .export import generate_password, export_students_xlsx, export_students_image_single, export_students_images_zip

admin_bp = Blueprint('admin', __name__)
lock = threading.Lock()


def classify_and_update(name):
    """后台线程：调用豆包分类后更新积木数据"""
    result = classify_action(name)
    category = result.get('category', '奖励')
    subcategory = result.get('subcategory', '其他')
    with lock:
        actions = models.load_actions()
        for a in actions:
            if a['name'] == name and a.get('status') == 'pending':
                a['category'] = category
                a['subcategory'] = subcategory
                a.pop('status', None)
                break
        models.save_actions(actions)


# ---------------------------------------------------------------
# 主页：课堂记录管理 / 用户操作 / 积木增删等
# ---------------------------------------------------------------
@admin_bp.route('/admin', methods=['GET', 'POST'])
@login_required(min_level=2)
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))
    if models.get_must_select_classes(session['username']):
        return redirect(url_for('auth.select_my_classes'))

    staff = models.load_staff()
    actions = models.load_actions()
    cfg = models.load_config()
    msg = request.args.get('msg', '')
    perms = get_feature_perms()

    if request.method == 'POST':
        act = request.form.get('action')

        # ---------- 添加课堂记录 ----------
        if act == 'add_record':
            cls = request.form.get('class_name', '')
            stu = request.form.get('student_name', '')
            tpl = request.form.get('action_type', '')
            if cls and stu and tpl:
                students = models.load_class_students(cls)
                if stu in students and students[stu]['role'] == 'student':
                    recs = students[stu].get('records', [])
                    if recs:
                        last = datetime.strptime(recs[-1]['time'], '%Y-%m-%d %H:%M:%S')
                        if (ntp_time() - last).total_seconds() < 60:
                            return redirect(url_for('admin.admin', msg=f'{stu} 1分钟内已有记录'))
                    desc = tpl
                    for p in re.findall(r'\{(.+?)\}', tpl):
                        desc = desc.replace(f'{{{p}}}', request.form.get(f'param_{p}', ''))
                    act_obj = next((a for a in actions if a['template'] == tpl), None)
                    category = act_obj.get('category', '') if act_obj else ''
                    subcategory = act_obj.get('subcategory', '') if act_obj else ''
                    students[stu].setdefault('records', []).append({
                        'action': desc,
                        'time': ntp_time().strftime('%Y-%m-%d %H:%M:%S'),
                        'display_time': ntp_time().strftime('%H:%M:%S'),
                        'category': category,
                        'subcategory': subcategory,
                    })
                    models.save_class_students(cls, students)
                    if category == '惩罚':
                        from .email_utils import send_punishment_alert
                        send_punishment_alert(cls, stu, desc)

        # ---------- 删除记录 ----------
        elif act == 'delete_record':
            cls = request.form.get('class_name')
            stu = request.form.get('student_name')
            idx_str = request.form.get('record_index')
            try:
                idx = int(idx_str)
                students = models.load_class_students(cls)
                if cls and stu in students and students[stu]['role'] == 'student' and 0 <= idx < len(students[stu].get('records', [])):
                    del students[stu]['records'][idx]
                    models.save_class_students(cls, students)
                    return redirect(url_for('admin.admin', msg=f'已删除 {stu} 的第 {idx+1} 条记录'))
            except:
                pass
            return redirect(url_for('admin.admin', msg='删除失败'))

        # ---------- 添加积木（主页快捷） ----------
        elif act == 'add_action':
            name = request.form.get('block_name', '').strip()
            params = request.form.get('params', '').strip()
            if not name:
                return redirect(url_for('admin.admin', msg='积木名称不能为空'))
            pl, lbl = [], []
            if params:
                for item in params.split(','):
                    if ':' in item:
                        n, l = item.split(':', 1)
                        pl.append(n.strip()); lbl.append(l.strip())
                    else:
                        pl.append(item); lbl.append(item)
            tpl = name
            for p in pl:
                tpl += f' {{{p}}}'
            new = {'name': name, 'template': tpl, 'params': pl, 'param_labels': lbl,
                   'category': '', 'subcategory': '', 'status': 'pending'}
            if not any(b['name'] == name and b['params'] == pl for b in actions):
                actions.append(new)
                models.save_actions(actions)
                threading.Thread(target=classify_and_update, args=(name,), daemon=True).start()
            return redirect(url_for('admin.admin'))

        # ---------- 修改个人信息 ----------
        elif act == 'change_credentials':
            cur = session['username']
            new_u = request.form.get('new_username', '').strip()
            pwd = request.form.get('new_password', '')
            name = request.form.get('new_name', '').strip()
            email = request.form.get('email', '').strip()
            if new_u and new_u != cur and new_u in staff:
                return redirect(url_for('admin.admin_account', msg='用户名已存在'))
            if pwd and not (8 <= len(pwd) <= 16):
                return redirect(url_for('admin.admin_account', msg='密码8-16位'))
            u = staff.pop(cur)
            u['password'] = pwd or u['password']
            u['name'] = name or u.get('name', cur)
            u['email'] = email
            staff[new_u] = u
            models.save_staff(staff)
            session['username'] = new_u
            return redirect(url_for('admin.admin_account', msg='信息已更新'))

        # ---------- 修改等级 ----------
        elif act == 'change_level' and session.get('level', 0) >= 5:
            target = request.form.get('target_username')
            lvl = int(request.form.get('new_level'))
            if target in staff and target != session['username']:
                staff[target]['level'] = lvl
                models.save_staff(staff)
                return redirect(url_for('admin.admin', msg=f'已将 {target} 等级修改为 {lvl}'))

        # ---------- 导入学生 ----------
        elif act == 'import_students' and session['level'] >= perms.get('import_students', 3):
            cls = request.form.get('import_class', '')
            mode = request.form.get('input_mode', 'file')
            names = []
            if mode == 'manual':
                names = [l.strip() for l in request.form.get('manual_students', '').splitlines() if l.strip()]
            else:
                f = request.files.get('student_file')
                if f:
                    names = [l.strip() for l in f.read().decode('utf-8').splitlines() if l.strip()]
            if names and cls:
                students = models.load_class_students(cls)
                added = 0
                for n in names:
                    if n not in students:
                        students[n] = {'password': '', 'role': 'student', 'level': 1,
                                       'name': n, 'class': cls, 'records': []}
                        added += 1
                models.save_class_students(cls, students)
                return redirect(url_for('admin.admin', msg=f'导入 {added} 名学生'))

        # ---------- 审批教师注册 ----------
        elif act == 'approve_registration' and session['level'] >= perms.get('approvals', 4):
            target = request.form.get('target_username')
            dec = request.form.get('decision')
            pend = models.load_pending_approvals()
            new_pend = [p for p in pend if p['username'] != target]
            approved = next((p for p in pend if p['username'] == target and dec == 'approve'), None)
            models.save_pending_approvals(new_pend)
            if approved:
                staff[approved['username']] = {
                    'password': approved['password'], 'role': approved['role'],
                    'level': approved['level'], 'name': approved['username'],
                    'class': approved.get('class_name', '')
                }
                models.save_staff(staff)
                return redirect(url_for('admin.admin', msg=f'已通过 {target}'))

        # ---------- 添加教职工 ----------
        elif act == 'add_account' and session['level'] >= perms.get('add_staff', 4):
            u = request.form.get('new_username')
            p = request.form.get('new_password')
            r = request.form.get('new_role', 'admin')
            lv = int(request.form.get('new_level', 3))
            n = request.form.get('new_name') or u
            if u in staff:
                return redirect(url_for('admin.admin', msg='用户已存在'))
            staff[u] = {'password': p, 'role': r, 'level': lv, 'name': n, 'class': ''}
            models.save_staff(staff)
            return redirect(url_for('admin.admin', msg=f'已添加 {u}'))

        # ---------- 更新班级人数 ----------
        elif act == 'update_class_size' and session['level'] >= perms.get('config_size', 2):
            sz = int(request.form.get('class_size', 0))
            if 1 <= sz <= 100:
                cfg['class_size'] = sz
                models.save_config(cfg)
                return redirect(url_for('admin.admin', msg=f'应到人数已更新为 {sz}'))

        return redirect(url_for('admin.admin'))

    # GET 部分：显示所有学生（包括无记录学生）
    allowed = models.filter_allowed_classes(session['level'], session['username'])
    stu = load_students_for_classes(allowed)
    by_class = {}
    for uname, info in stu.items():
        if info.get('role') == 'student':
            cls = info.get('class', '未知')
            recs = sorted(info.get('records', []), key=lambda x: x['time'], reverse=True)
            by_class.setdefault(cls, []).append({'username': uname, 'name': info['name'], 'records': recs})

    all_users = [{'username': u, 'password': i.get('password'), 'level': i.get('level', 1),
                  'role': i.get('role'), 'name': i.get('name'), 'class': i.get('class')}
                 for u, i in staff.items()]
    all_users.sort(key=lambda x: x['level'], reverse=True)

    pw_resets = models.load_password_reset_requests() if session['level'] >= 4 else []
    student_pending = models.load_student_pending_approvals() if session['level'] >= 3 else []

    force_read = None
    if session['level'] >= 3:
        rs = models.load_read_status()
        if not rs.get(session['username'], True):
            reports = models.load_reports()
            for r in reversed(reports):
                if r.get('scope') == 'level3' and not rs.get(session['username'], True):
                    force_read = r
                    break

    return render_template('admin.html',
                           students_by_class=by_class,
                           classes=allowed,
                           actions=actions,
                           msg=msg,
                           all_users=all_users,
                           is_super_admin=(session['level'] >= 5),
                           force_read_report=force_read,
                           pending_reports=[],
                           pending_approvals=[],
                           student_pending=student_pending,
                           pw_resets=pw_resets,
                           config=cfg,
                           perms=perms,
                           staff=staff)


# ---------------------------------------------------------------
# 日志页面
# ---------------------------------------------------------------
@admin_bp.route('/admin/logs')
@login_required(min_level=2)
def admin_logs():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))
    allowed = models.filter_allowed_classes(session['level'], session['username'])
    sel = request.args.get('class_name', '')
    logs = []
    if sel in allowed:
        for u, i in models.load_class_students(sel).items():
            if i.get('role') == 'student':
                for r in i.get('records', []):
                    logs.append({'time': r.get('display_time', r['time']),
                                 'student': i.get('name', u), 'class': sel, 'action': r['action']})
        logs.sort(key=lambda x: x['time'], reverse=True)
    return render_template('logs.html', allowed_classes=allowed, selected_class=sel, logs=logs)


# ---------------------------------------------------------------
# 用户管理
# ---------------------------------------------------------------
@admin_bp.route('/admin/users')
@login_required(min_level=4)
def admin_users():
    if models.is_test_account(session.get('username')):
        return "测试账户无此权限", 403
    staff = models.load_staff()
    users = [{'username': u, 'password': i.get('password'), 'level': i.get('level', 1),
              'role': i.get('role'), 'name': i.get('name'), 'class': i.get('class')}
             for u, i in staff.items()]
    users.sort(key=lambda x: x['level'], reverse=True)
    return render_template('users.html', all_users=users,
                           key_generated=request.args.get('key_generated'),
                           key_user=request.args.get('key_user'))


@admin_bp.route('/admin/delete-user', methods=['POST'])
@login_required(min_level=5)
def delete_user():
    if models.is_test_account(session.get('username')):
        return "测试账户无此权限", 403
    target = request.form.get('target_username', '')
    if target and target != session['username']:
        staff = models.load_staff()
        if target in staff:
            del staff[target]
            models.save_staff(staff)
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/admin/bind-classes/<target>', methods=['GET', 'POST'])
@login_required(min_level=4)
def admin_bind_classes(target):
    if models.is_test_account(session.get('username')):
        return "测试账户无此权限", 403
    if target not in models.load_staff():
        return redirect(url_for('admin.admin_users'))
    all_cls = sorted(models.get_all_class_names())
    cur = models.get_user_classes(target)
    if request.method == 'POST':
        sel = [c for c in request.form.getlist('classes') if c in all_cls]
        models.set_user_classes(target, sel)
        return redirect(url_for('admin.admin_users', msg=f'已更新 {target} 班级'))
    return render_template('bind_classes.html', target=target, all_classes=all_cls, current_classes=cur)


@admin_bp.route('/admin/generate-reset-key', methods=['POST'])
@login_required(min_level=5)
def generate_reset_key():
    if models.is_test_account(session.get('username')):
        return "测试账户无此权限", 403
    target = request.form.get('target_username')
    if target:
        key = models.generate_reset_key(target)
        return redirect(url_for('admin.admin_users', key_generated=key, key_user=target))
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/admin/approve-password-reset', methods=['POST'])
@login_required(min_level=4)
def approve_password_reset():
    if models.is_test_account(session.get('username')):
        return "测试账户无此权限", 403
    target = request.form.get('target_username')
    decision = request.form.get('decision')
    if decision == 'approve':
        staff = models.load_staff()
        if target in staff:
            staff[target]['password'] = '12345678'
            models.save_staff(staff)
        models.remove_password_reset_request(target)
    elif decision == 'reject':
        models.remove_password_reset_request(target)
    return redirect(url_for('admin.admin'))


# ---------------------------------------------------------------
# AI 分析 / 审批 / 导入 等页面
# ---------------------------------------------------------------
@admin_bp.route('/admin/ai')
@login_required(min_level=4)
def admin_ai():
    reps = [{'index': i, 'content': r['content'][:200] + '...'}
            for i, r in enumerate(models.load_reports()) if r.get('scope') == 'pending']
    return render_template('ai.html', pending_reports=reps)


@admin_bp.route('/admin/approvals')
@login_required(min_level=4)
def admin_approvals():
    pending = models.load_pending_approvals()
    return render_template('approvals.html', pending_approvals=pending)


@admin_bp.route('/admin/import')
@login_required(min_level=3)
def admin_import():
    classes = models.filter_allowed_classes(session['level'], session['username'])
    return render_template('import.html', classes=classes)


# ---------------------------------------------------------------
# 积木管理（奖励/惩罚分类）
# ---------------------------------------------------------------
@admin_bp.route('/admin/actions', methods=['GET', 'POST'])
@login_required(min_level=2)
def admin_actions():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))
    actions = models.load_actions()
    if request.method == 'POST':
        act = request.form.get('action')
        if act == 'add_action':
            name = request.form.get('block_name', '').strip()
            if name:
                params = request.form.get('params', '').strip()
                pl, lbl = [], []
                if params:
                    for item in params.split(','):
                        if ':' in item:
                            n, l = item.split(':', 1)
                            pl.append(n.strip()); lbl.append(l.strip())
                        else:
                            pl.append(item); lbl.append(item)
                tpl = name
                for p in pl:
                    tpl += f' {{{p}}}'
                new = {'name': name, 'template': tpl, 'params': pl, 'param_labels': lbl,
                       'category': '', 'subcategory': '', 'status': 'pending'}
                if not any(b['name'] == name and b['params'] == pl for b in actions):
                    actions.append(new)
                    models.save_actions(actions)
                    threading.Thread(target=classify_and_update, args=(name,), daemon=True).start()
                    return redirect(url_for('admin.admin_actions', msg=f'已添加 {name}，AI 分类中'))
        elif act == 'edit_action':
            # 四级及以上可修改分类
            if session.get('level', 0) >= 4:
                idx = request.form.get('edit_index', type=int)
                new_category = request.form.get('new_category', '').strip()
                new_subcategory = request.form.get('new_subcategory', '').strip()
                if idx is not None and 0 <= idx < len(actions):
                    if new_category in ('奖励', '惩罚', '在校表现', '其他'):
                        actions[idx]['category'] = new_category
                        if new_subcategory:
                            actions[idx]['subcategory'] = new_subcategory
                        models.save_actions(actions)
                        return redirect(url_for('admin.admin_actions', msg='分类已更新'))
        elif act == 'delete_action':
            idx = request.form.get('del_action', '')
            try:
                idx = int(idx)
                if 0 <= idx < len(actions):
                    del actions[idx]
                    models.save_actions(actions)
            except:
                pass
    reward = [a for a in actions if a.get('category') == '奖励']
    punish = [a for a in actions if a.get('category') == '惩罚']
    performance = [a for a in actions if a.get('category') == '在校表现']
    other = [a for a in actions if a.get('category') not in ('奖励', '惩罚', '在校表现')]
    pending = sum(1 for a in actions if a.get('status') == 'pending')
    return render_template('actions.html',
                           reward_actions=reward,
                           punish_actions=punish,
                           performance_actions=performance,
                           other_actions=other,
                           pending_count=pending)


# ---------------------------------------------------------------
# 账户设置
# ---------------------------------------------------------------
@admin_bp.route('/admin/account', methods=['GET', 'POST'])
@login_required(min_level=2)
def admin_account():
    if request.method == 'POST' and request.form.get('action') == 'update_classes':
        sel = [c for c in request.form.getlist('classes') if c in models.get_all_class_names()]
        models.set_user_classes(session['username'], sel)
        return redirect(url_for('admin.admin_account', msg='班级已更新'))
    return render_template('account.html',
                           all_classes=models.get_all_class_names(),
                           current_classes=models.get_user_classes(session['username']))


# ---------------------------------------------------------------
# 班级人数配置
# ---------------------------------------------------------------
@admin_bp.route('/admin/config')
@login_required(min_level=2)
def admin_config():
    return render_template('config.html', config=models.load_config())


# ---------------------------------------------------------------
# 添加教职工
# ---------------------------------------------------------------
@admin_bp.route('/admin/addstaff')
@login_required(min_level=4)
def admin_addstaff():
    if models.is_test_account(session.get('username')):
        return "测试账户无此权限", 403
    return render_template('addstaff.html')


# ---------------------------------------------------------------
# 扩班审批 / 分配班级 / 学生审批
# ---------------------------------------------------------------
@admin_bp.route('/admin/pending-classes', methods=['GET', 'POST'])
@login_required(min_level=4)
def admin_pending_classes():
    if request.method == 'POST':
        u = request.form.get('username')
        c = request.form.get('class_name')
        if request.form.get('action') == 'approve':
            models.approve_class_request(u, c)
        else:
            models.reject_class_request(u, c)
        return redirect(url_for('admin.admin_pending_classes'))
    return render_template('pending_classes.html', pending=models.get_pending_class_requests())


@admin_bp.route('/admin/assign-classes', methods=['GET', 'POST'])
@login_required(min_level=4)
def admin_assign_classes():
    staff = models.load_staff()
    targets = [u for u, i in staff.items() if u != session['username'] and i.get('level', 0) >= 2]
    if request.method == 'POST':
        for u in request.form.getlist('users'):
            if u in staff:
                models.set_must_select_classes(u, True)
        return render_template('assign_classes.html', targets=targets, staff=staff, msg='已发送选班通知')
    return render_template('assign_classes.html', targets=targets, staff=staff)


@admin_bp.route('/admin/approve-student', methods=['POST'])
@login_required(min_level=3)
def approve_student():
    idx = request.form.get('index', type=int)
    action = request.form.get('action')
    cls = request.form.get('class_name', '')
    pend = models.load_student_pending_approvals()
    if idx is not None and 0 <= idx < len(pend):
        rec = pend[idx]
        if action == 'approve' and cls:
            students = models.load_class_students(cls)
            if rec['student_name'] not in students:
                students[rec['student_name']] = {'password': '', 'role': 'student', 'level': 1,
                                                 'name': rec['student_name'], 'class': cls, 'records': []}
                models.save_class_students(cls, students)
            del pend[idx]
            models.save_student_pending_approvals(pend)
        elif action == 'reject':
            del pend[idx]
            models.save_student_pending_approvals(pend)
    return redirect(url_for('admin.admin'))


# ---------------------------------------------------------------
# AI 报告相关
# ---------------------------------------------------------------
@admin_bp.route('/auto-summary')
@login_required(min_level=3)
def auto_summary():
    today = ntp_time().strftime('%Y-%m-%d')
    reps = models.load_reports()
    for r in reversed(reps):
        if r['date'] == today and r['type'] == 'daily_auto':
            return jsonify({'html': utils.md_to_html(r['content'])})
    generate_daily_report(models.filter_allowed_classes(session['level'], session['username']))
    for r in reversed(models.load_reports()):
        if r['date'] == today and r['type'] == 'daily_auto':
            return jsonify({'html': utils.md_to_html(r['content'])})
    return jsonify({'error': '生成失败'}), 500


@admin_bp.route('/show-summary/<int:idx>')
@login_required(min_level=4)
def show_summary(idx):
    reps = models.load_reports()
    if 0 <= idx < len(reps):
        return render_template('show_summary.html',
                               content=utils.md_to_html(reps[idx]['content']),
                               date=reps[idx]['date'],
                               time=reps[idx]['time'])
    return redirect(url_for('admin.admin'))


# ---------------------------------------------------------------
# 动态密码导出页面及处理
# ---------------------------------------------------------------
@admin_bp.route('/admin/export-password')
@login_required(min_level=4)
def get_export_password():
    return render_template('export_password.html',
                           password=models.generate_totp(),
                           classes=models.get_all_class_names())


@admin_bp.route('/admin/export', methods=['POST'])
@login_required(min_level=4)
def export_data():
    fmt = request.form.get('format', 'xlsx')
    password = request.form.get('password', '')
    sheet_name = request.form.get('sheet_name', '')

    # 图片单张导出
    if fmt == 'image_single':
        img_buffer = export_students_image_single(sheet_name)
        if img_buffer is None:
            return "未找到指定工作表", 404
        filename = f"{sheet_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        return send_file(img_buffer, as_attachment=True, download_name=filename, mimetype='image/png')

    # 图片打包 ZIP（使用当前账户密码加密）
    elif fmt == 'image_zip':
        staff = models.load_staff()
        user_pwd = staff.get(session['username'], {}).get('password', '')
        if not user_pwd:
            user_pwd = 'classlog123'
        zip_buffer = export_students_images_zip(user_pwd)
        filename = f"学生数据图片_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        return send_file(zip_buffer, as_attachment=True, download_name=filename, mimetype='application/zip')

    # 表格导出（需动态密码）
    else:
        if not models.verify_totp(password):
            return redirect(url_for('admin.get_export_password', msg='动态密码错误'))
        excel_file = export_students_xlsx(password)
        filename = f"学生数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(excel_file, as_attachment=True, download_name=filename,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ---------------------------------------------------------------
# 功能权限设置（5级）
# ---------------------------------------------------------------
@admin_bp.route('/admin/feature-permissions', methods=['GET', 'POST'])
@login_required(min_level=5)
def feature_permissions():
    cfg = models.load_config()
    perms = cfg.get('feature_permissions', {})
    if request.method == 'POST':
        for k in ["broadcast", "export", "video_webcam", "import_students", "user_management",
                  "ai_analysis", "approvals", "add_staff", "config_size", "logs", "actions", "account"]:
            perms[k] = int(request.form.get(k, perms.get(k, 5)))
        cfg['feature_permissions'] = perms
        models.save_config(cfg)
        return redirect(url_for('admin.feature_permissions', msg='已更新'))
    return render_template('feature_permissions.html', perms=perms)


@admin_bp.route('/admin/update-camera', methods=['POST'])
@login_required(min_level=5)
def update_camera_source():
    new_source = request.form.get('camera_source', '0').strip()
    try:
        new_source = int(new_source)
    except:
        pass
    cfg = models.load_config()
    cfg['camera_source'] = new_source
    models.save_config(cfg)
    return jsonify({'status': 'ok', 'source': new_source})


# ---------------------------------------------------------------
# 班级重命名（四级以上，测试账户不可用）
# ---------------------------------------------------------------
@admin_bp.route('/admin/rename-class', methods=['GET', 'POST'])
@login_required(min_level=4)
def admin_rename_class():
    if models.is_test_account(session.get('username')):
        return "测试账户无此权限", 403
    allowed = models.filter_allowed_classes(session['level'], session['username'])
    if request.method == 'POST':
        old = request.form.get('old_name')
        new = request.form.get('new_name')
        if old and new and old in allowed and new not in models.get_all_class_names():
            try:
                os.rename(os.path.join(config.DATA_DIR, old), os.path.join(config.DATA_DIR, new))
            except:
                return redirect(url_for('admin.admin_rename_class', msg='重命名失败'))
            return redirect(url_for('admin.admin_rename_class', msg=f'已重命名为 {new}'))
    return render_template('rename_class.html', classes=allowed)


# ---------------------------------------------------------------
# 贡献名单（五级编辑，测试账户不可用）
# ---------------------------------------------------------------
@admin_bp.route('/admin/credits', methods=['GET', 'POST'])
@login_required(min_level=1)
def admin_credits():
    if models.is_test_account(session.get('username')):
        return "测试账户无此权限", 403
    credits = models.load_credits()
    if request.method == 'POST' and session.get('level', 0) >= 5:
        if request.form.get('action') == 'add':
            n = request.form.get('name')
            c = request.form.get('contribution')
            if n and c:
                credits.append({'name': n, 'contribution': c})
                models.save_credits(credits)
        elif request.form.get('action') == 'delete':
            idx = request.form.get('index', type=int)
            if idx is not None and 0 <= idx < len(credits):
                del credits[idx]
                models.save_credits(credits)
    return render_template('credits.html', credits=credits)


# ---------------------------------------------------------------
# 邮件设置（5级）
# ---------------------------------------------------------------
@admin_bp.route('/admin/email-settings', methods=['GET', 'POST'])
@login_required(min_level=5)
def admin_email_settings():
    cfg = models.load_config()
    smtp = cfg.get('smtp', {})
    if request.method == 'POST':
        smtp['server'] = request.form.get('server', '').strip()
        smtp['port'] = int(request.form.get('port', 587))
        smtp['username'] = request.form.get('username', '').strip()
        smtp['password'] = request.form.get('password', '').strip()
        smtp['from'] = request.form.get('from', '').strip() or smtp['username']
        smtp['encryption'] = request.form.get('encryption', 'starttls')
        cfg['smtp'] = smtp
        models.save_config(cfg)
        return redirect(url_for('admin.admin_email_settings', msg='SMTP 配置已更新'))
    msg = request.args.get('msg', '')
    return render_template('email_settings.html', smtp=smtp, msg=msg)


# ---------------------------------------------------------------
# IP 日志查看（4级以上）
# ---------------------------------------------------------------
@admin_bp.route('/admin/ip-logs')
@login_required(min_level=4)
def admin_ip_logs():
    logs = models.load_audit_logs()
    ip_logs = {}
    for log in logs:
        ip = log.get('ip', '未知')
        ip_logs.setdefault(ip, []).append(log)
    sorted_ips = sorted(ip_logs.items(), key=lambda x: x[1][-1]['time'] if x[1] else '', reverse=True)
    return render_template('ip_logs.html', ip_logs=sorted_ips)


# ---------------------------------------------------------------
# 视频列表和流媒体播放（5级）
# ---------------------------------------------------------------
@admin_bp.route('/admin/video-list')
@login_required(min_level=5)
def video_list():
    videos = []
    for fname in os.listdir(config.VIDEO_STORAGE_DIR):
        if fname.endswith('.vidat'):
            videos.append(fname)
    videos.sort(reverse=True)
    return render_template('video_list.html', videos=videos)


@admin_bp.route('/admin/video-stream/<filename>')
@login_required(min_level=5)
def video_stream(filename):
    filepath = os.path.join(config.VIDEO_STORAGE_DIR, filename)
    if not os.path.exists(filepath) or not filename.endswith('.vidat'):
        return "文件不存在", 404
    with open(filepath, 'rb') as f:
        encrypted_data = f.read()
    try:
        decrypted_data = video.fernet.decrypt(encrypted_data)
    except Exception:
        return "视频解密失败", 500
    return Response(decrypted_data, mimetype='video/webm')