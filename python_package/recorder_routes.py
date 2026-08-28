import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session
from . import models, config
from .decorators import login_required
from .helpers import load_students_for_classes, get_feature_perms
from .ntp import ntp_time

recorder_bp = Blueprint('recorder', __name__)

@recorder_bp.route('/recorder', methods=['GET', 'POST'])
@login_required(min_level=2)
def recorder():
    if session.get('role') != 'recorder':
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
        if act == 'add_record':
            cls, stu, tpl = request.form['class_name'], request.form['student_name'], request.form['action_type']
            if cls and stu and tpl:
                students = models.load_class_students(cls)
                if stu in students and students[stu]['role'] == 'student':
                    recs = students[stu].get('records', [])
                    if recs and (ntp_time() - datetime.strptime(recs[-1]['time'], '%Y-%m-%d %H:%M:%S')).seconds < 60:
                        return redirect(url_for('recorder.recorder', msg=f'{stu} 1分钟内已有记录'))
                    desc = tpl
                    for p in re.findall(r'\{(.+?)\}', tpl):
                        desc = desc.replace(f'{{{p}}}', request.form.get(f'param_{p}', ''))
                    # 获取行为分类
                    act_obj = next((a for a in actions if a['template'] == tpl), None)
                    category = act_obj.get('category', '') if act_obj else ''
                    subcategory = act_obj.get('subcategory', '') if act_obj else ''
                    students[stu].setdefault('records', []).append({
                        "action": desc,
                        "time": ntp_time().strftime('%Y-%m-%d %H:%M:%S'),
                        "display_time": ntp_time().strftime('%H:%M:%S'),
                        "category": category,
                        "subcategory": subcategory
                    })
                    models.save_class_students(cls, students)
                    # 如果分类为“惩罚”，触发邮件提醒
                    if category == '惩罚':
                        from .email_utils import send_punishment_alert
                        send_punishment_alert(cls, stu, desc)
        elif act == 'change_credentials':
            cur = session['username']
            new_u = request.form.get('new_username', '').strip()
            pwd = request.form.get('new_password', '')
            name = request.form.get('new_name', '').strip()
            email = request.form.get('email', '').strip()
            if new_u and new_u != cur and new_u in staff:
                return redirect(url_for('recorder.recorder', msg='用户名已存在'))
            if pwd and not (8 <= len(pwd) <= 16):
                return redirect(url_for('recorder.recorder', msg='密码8-16位'))
            u = staff.pop(cur)
            u['password'] = pwd or u['password']
            u['name'] = name or u.get('name', cur)
            u['email'] = email
            staff[new_u] = u
            models.save_staff(staff)
            session['username'] = new_u
            return redirect(url_for('recorder.recorder', msg='信息已更新'))
        elif act == 'mark_read':
            rs = models.load_read_status()
            rs[session['username']] = True
            models.save_read_status(rs)
            return redirect(url_for('recorder.recorder'))
        elif act == 'update_class_size':
            if session.get('level', 0) < perms.get('config_size', 2):
                return redirect(url_for('recorder.recorder', msg='无权修改'))
            sz = int(request.form.get('class_size', 0))
            if 1 <= sz <= 100:
                cfg['class_size'] = sz
                models.save_config(cfg)
                return redirect(url_for('recorder.recorder', msg=f'应到人数已更新为 {sz}'))
        return redirect(url_for('recorder.recorder'))

    # GET 部分：显示所有学生（包括无记录学生）
    allowed = models.filter_allowed_classes(session['level'], session['username'])
    stu = load_students_for_classes(allowed)
    by_class = {}
    for uname, info in stu.items():
        if info.get('role') == 'student':
            cls = info.get('class', '未知')
            recs = sorted(info.get('records', []), key=lambda x: x['time'], reverse=True)
            by_class.setdefault(cls, []).append({'username': uname, 'name': info['name'], 'records': recs})

    force_read = None
    if session.get('level', 0) >= 2:
        rs = models.load_read_status()
        if not rs.get(session['username'], True):
            reports = models.load_reports()
            for r in reversed(reports):
                if r.get('scope') in ('level2', 'level3') and not rs.get(session['username'], True):
                    force_read = r
                    break

    return render_template('recorder.html',
                           students_by_class=by_class, classes=allowed,
                           actions=actions, current_user=staff.get(session['username'], {}),
                           msg=msg, force_read_report=force_read,
                           config=cfg, perms=perms)