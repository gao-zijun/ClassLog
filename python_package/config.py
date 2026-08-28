import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'AppDate')
LOG_DIR = os.path.join(BASE_DIR, 'log')
VIDEO_STORAGE_DIR = os.path.join(BASE_DIR, 'video_storage')
AI_MODELS_DIR = os.path.join(BASE_DIR, 'ai_models')
AI_MODELS_JSON = os.path.join(AI_MODELS_DIR, 'models.json')
PORT = 443
ICON_PATH = os.path.join(BASE_DIR, 'icon.ico')
NTP_SERVERS = ["ntp.aliyun.com", "time1.cloud.tencent.com", "ntp.ntsc.ac.cn", "pool.ntp.org"]
DEFAULT_CLASS = '默认班级'
VIDEO_KEY_FILE = os.path.join(BASE_DIR, 'video_key.key')
DB_FILE = os.path.join(DATA_DIR, 'classlog.db')   # 新增 SQLite 数据库文件路径
DEFAULT_MODELS = {"daily_auto": "deepseek-chat", "manual_query": "deepseek-chat", "manual_select": "deepseek-chat"}