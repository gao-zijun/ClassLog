from flask import render_template
from . import models

def register_broadcast_routes(app):
    @app.route('/broadcast/view')
    def broadcast_view():
        return render_template('broadcast.html', broadcast_text=models.load_config().get('broadcast_text',''))