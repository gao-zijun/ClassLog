import os
import sys
import threading
import webbrowser
from datetime import datetime
from flask import Flask, request, session
from cheroot import wsgi
from cheroot.ssl.builtin import BuiltinSSLAdapter
from pystray import Icon, Menu, MenuItem
from PIL import Image

from . import config, models
from .helpers import inject_globals
from .auth_routes import auth_bp
from .admin_routes import admin_bp
from .recorder_routes import recorder_bp
from .student_routes import student_bp
from .api_routes import api_bp
from .broadcast import register_broadcast_routes

# SSL 证书路径
CERT_FILE = os.path.join(config.BASE_DIR, 'fullchain.pem')
KEY_FILE  = os.path.join(config.BASE_DIR, 'privkey.pem')


def create_app():
    app = Flask(__name__, template_folder=os.path.join(config.BASE_DIR, 'templates'))
    app.secret_key = 'classlog_secret_change_me'

    app.context_processor(lambda: inject_globals())

    for bp in [auth_bp, admin_bp, recorder_bp, student_bp, api_bp]:
        app.register_blueprint(bp)

    register_broadcast_routes(app)

    @app.before_request
    def record_audit_log():
        if request.path.startswith('/static'):
            return
        if request.path in ('/api/heartbeat', '/api/check-broadcast'):
            return
        entry = {
            'ip': request.remote_addr,
            'user': session.get('username', '匿名'),
            'method': request.method,
            'path': request.path,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_agent': request.user_agent.string[:200]
        }
        models.add_audit_log(entry)

    try:
        models.init_data()
    except Exception:
        for d in [config.DATA_DIR, config.LOG_DIR, config.VIDEO_STORAGE_DIR]:
            os.makedirs(d, exist_ok=True)

    return app


def start():
    app = create_app()

    def on_open(icon, item):
        webbrowser.open(f'https://127.0.0.1:{config.PORT}')

    def on_restart(icon, item):
        icon.stop()
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    def on_exit(icon, item):
        icon.stop()
        os._exit(0)

    menu = Menu(
        MenuItem('打开网页', on_open, default=True),
        MenuItem('重启程序', on_restart),
        MenuItem('关闭程序', on_exit)
    )

    try:
        image = Image.open(config.ICON_PATH)
    except Exception:
        image = Image.new('RGB', (64, 64), color='gray')

    icon = Icon("ClassLog", image, "ClassLog 课堂管理系统", menu)

    def run_server():
        print(f"服务器已启动，访问 https://127.0.0.1:{config.PORT}")
        if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
            server = wsgi.Server(('0.0.0.0', config.PORT), app)
            server.ssl_adapter = BuiltinSSLAdapter(CERT_FILE, KEY_FILE)
            server.start()
        else:
            print("警告：未找到证书或私钥，使用 HTTP 模式")
            server = wsgi.Server(('0.0.0.0', config.PORT), app)
            server.start()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    icon.run()


if __name__ == '__main__':
    start()