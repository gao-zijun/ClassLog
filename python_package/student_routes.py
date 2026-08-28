import re
from flask import Blueprint, render_template, request, redirect, url_for, session
from . import models
from .decorators import login_required

student_bp = Blueprint('student', __name__)

@student_bp.route('/student', methods=['GET','POST'])
@login_required(min_level=1)
def student():
    info = models.load_all_students().get(session['username'])
    if not info: return redirect(url_for('auth.logout'))
    if request.method == 'POST':
        pwd = request.form.get('new_password','')
        if pwd and not re.fullmatch(r'\d{6,18}', pwd): return render_template('student.html', student=info, password_error='6-18位数字')
        info['password'] = pwd
        models.save_class_students(info.get('class',''), {session['username']: info})
    info['records'] = sorted(info.get('records',[]), key=lambda x:x['time'], reverse=True)
    return render_template('student.html', student=info)