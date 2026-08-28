import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from . import models, config
from .decorators import login_required
from .ntp import ntp_time
from .video import fernet

api_bp = Blueprint('api', __name__)

@api_bp.route('/record-noise', methods=['POST'])
@login_required(min_level=2)
def record_noise():
    db = request.form.get('db', 0, type=float)
    now = ntp_time(); desc = f"[自动] 环境噪音过高 ({db:.1f} dB)"
    for u,i in models.load_all_students().items():
        if i['role']=='student':
            i.setdefault('records',[]).append({"action":desc, "time":now.strftime('%Y-%m-%d %H:%M:%S'), "display_time":now.strftime('%H:%M:%S')})
            models.save_class_students(i.get('class',config.DEFAULT_CLASS), {u:i})
    return jsonify({'status':'ok'})

@api_bp.route('/broadcast/send', methods=['GET','POST'])
@login_required(min_level=3)
def broadcast_send():
    staff = models.load_staff(); lv = session.get('level',0)
    users = [{'username':u, 'level':i['level'], 'role':i['role'], 'class':i.get('class')} for u,i in staff.items() if i.get('level',0)<lv]
    classes = models.filter_allowed_classes(session['level'], session['username'])
    if request.method == 'POST':
        msg = request.form.get('message','').strip()
        if not msg: return render_template('broadcast_send.html', users=users, classes=classes, error='内容不能为空')
        targets = set()
        for cls in request.form.getlist('classes'):
            for u,i in models.load_all_students().items():
                if i.get('role')=='student' and i.get('class')==cls: targets.add(u)
        for stu in request.form.getlist('students'):
            if stu in models.load_all_students(): targets.add(stu)
        for u in request.form.getlist('users'):
            if u in staff and staff[u]['level']<lv: targets.add(u)
        sender = staff[session['username']].get('name', session['username'])
        cnt = sum(1 for t in targets if models.is_user_online(t) and not models.add_broadcast_to_user(t, sender, msg))
        return render_template('broadcast_send.html', users=users, classes=classes, msg=f'已发送给 {cnt} 人')
    return render_template('broadcast_send.html', users=users, classes=classes)

@api_bp.route('/api/heartbeat')
def heartbeat():
    if 'username' in session: models.update_user_heartbeat(session['username'])
    return jsonify({'status':'ok'})

@api_bp.route('/api/check-broadcast')
def check_broadcast():
    if 'username' not in session: return jsonify({'broadcast':None})
    models.update_user_heartbeat(session['username'])
    bc = models.get_and_clear_broadcast(session['username'])
    return jsonify({'broadcast':{'sender':bc['sender'],'message':bc['message']} if bc else None})

@api_bp.route('/feedback')
@login_required(min_level=1)
def feedback():
    return render_template('feedback.html')

@api_bp.route('/feature-request')
@login_required(min_level=1)
def feature_request():
    return render_template('feature_request.html')

@api_bp.route('/video/upload-web', methods=['POST'])
@login_required(min_level=5)
def upload_web_video():
    f = request.files.get('video')
    if not f: return jsonify({'error':'无文件'}), 400
    data = f.read(); enc = fernet.encrypt(data)
    fn = datetime.now().strftime('%Y%m%d_%H%M%S')+'.vidat'
    with open(os.path.join(config.VIDEO_STORAGE_DIR, fn), 'wb') as f: f.write(enc)
    return jsonify({'status':'ok','filename':fn})

@api_bp.route('/video/record')
@login_required(min_level=5)
def video_record():
    return render_template('video_record.html')