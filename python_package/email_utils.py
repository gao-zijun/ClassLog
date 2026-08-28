import smtplib
import threading
from email.mime.text import MIMEText
from email.header import Header
from . import models


def send_email(to_email, subject, body):
    """发送邮件，支持 STARTTLS 和 SSL"""
    cfg = models.load_config()
    smtp = cfg.get('smtp', {})
    if not smtp.get('server') or not smtp.get('username') or not smtp.get('password'):
        print("SMTP 未配置，无法发送邮件")
        return False

    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = smtp.get('from') or smtp['username']
        msg['To'] = to_email

        server = None
        port = int(smtp.get('port', 587))
        encryption = smtp.get('encryption', 'starttls')

        if encryption == 'ssl' or port == 465:
            server = smtplib.SMTP_SSL(smtp['server'], port, timeout=10)
        else:
            server = smtplib.SMTP(smtp['server'], port, timeout=10)
            server.starttls()

        server.login(smtp['username'], smtp['password'])
        server.sendmail(msg['From'], [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False


def send_punishment_alert(class_name, student_name, action_desc):
    """当学生有惩罚行为时，异步通知该班级所有绑定老师"""
    def worker():
        teachers = models.get_users_by_class(class_name)
        for t in teachers:
            if not t.get('email'):
                continue
            subject = f"【ClassLog】{class_name} 学生 {student_name} 有严重行为提醒"
            body = f"学生：{student_name}\n班级：{class_name}\n行为：{action_desc}\n时间：请登录系统查看详情"
            send_email(t['email'], subject, body)
    threading.Thread(target=worker, daemon=True).start()