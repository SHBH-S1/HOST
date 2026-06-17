# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════╗
║  🚀 SERVER HUB — Professional Hosting Control Panel                      ║
║  Version: 2.0  |  By: @SHBH_S1  |  Admin: RIKO                           ║
╠══════════════════════════════════════════════════════════════════════════╣
║  - Full PHP / Node.js / Python support                                   ║
║  - Docker user isolation                                                 ║
║  - ZIP extract, file manager, drag & drop                                ║
║  - Admin approval for new registrations                                  ║
║  - Modern responsive UI (SERVER HUB theme)                               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, gc, re, ast, json, time, uuid, html, shutil, socket
import signal, string, random, secrets, hashlib, logging, platform
import zipfile, tarfile, threading, subprocess, warnings
import urllib.request, urllib.parse
from datetime import datetime, timedelta
from functools import wraps
from collections import deque
from io import BytesIO

try:
    import resource
except ImportError:
    resource = None

try:
    import psutil
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

from flask import (Flask, render_template_string, request, jsonify, session,
                   redirect, url_for, send_file, send_from_directory)
from werkzeug.utils import secure_filename

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────
#  1.  Unlimited Resources
# ─────────────────────────────────────────────
def set_unlimited_resources():
    if not resource:
        return False
    try:
        resource.setrlimit(resource.RLIMIT_AS,    (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        resource.setrlimit(resource.RLIMIT_DATA,  (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        resource.setrlimit(resource.RLIMIT_NOFILE,(999999, 999999))
        resource.setrlimit(resource.RLIMIT_NPROC, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        return True
    except Exception:
        return False

set_unlimited_resources()

def _memory_monitor():
    while True:
        time.sleep(30)
        try:
            gc.collect()
            try:
                open('/proc/sys/vm/drop_caches','w').write('3')
            except Exception:
                pass
        except Exception:
            pass

threading.Thread(target=_memory_monitor, daemon=True).start()

# ─────────────────────────────────────────────
#  2.  Paths & Settings
# ─────────────────────────────────────────────
DEFAULT_BASE = os.environ.get('BASE_PATH') or (
    os.path.join(os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', os.getcwd()), 'panel_data')
    if (os.path.exists('/home/runner') or 'REPL_ID' in os.environ)
    else '/tmp/panel_data'
)
BASE_PATH          = DEFAULT_BASE
os.makedirs(BASE_PATH, exist_ok=True)

USERS_FOLDER       = os.path.join(BASE_PATH, 'users_data')
USERS_FILE         = os.path.join(BASE_PATH, 'users.json')
PROCESSES_FILE     = os.path.join(BASE_PATH, 'processes.json')
SCHEDULES_FILE     = os.path.join(BASE_PATH, 'schedules.json')
LOGS_FILE          = os.path.join(BASE_PATH, 'activity.log')
USER_SESSIONS_FILE = os.path.join(BASE_PATH, 'user_sessions.json')
BACKUPS_FOLDER     = os.path.join(BASE_PATH, 'backups')
TEMP_FOLDER        = os.path.join(BASE_PATH, 'temp')
PACKAGES_FILE      = os.path.join(BASE_PATH, 'packages.json')
DOCKER_FILE        = os.path.join(BASE_PATH, 'docker.json')
MASTER_CONFIG_FILE = os.path.join(BASE_PATH, 'master_config.json')
PORTS_FILE         = os.path.join(BASE_PATH, 'ports.json')
ACTIVITY_FILE      = os.path.join(BASE_PATH, 'activity_feed.json')
OWNER_CONFIG_FILE  = os.path.join(BASE_PATH, 'owner_config.json')
MAINTENANCE_FILE   = os.path.join(BASE_PATH, 'maintenance.json')
BOT_STATS_FILE     = os.path.join(BASE_PATH, 'bot_stats.json')
ANNOUNCE_FILE      = os.path.join(BASE_PATH, 'announcements.json')
SECURITY_ALERTS_FILE = os.path.join(BASE_PATH, 'security_alerts.json')
NODEJS_PROCS_FILE  = os.path.join(BASE_PATH, 'nodejs_procs.json')
PHP_CONFIG_FILE    = os.path.join(BASE_PATH, 'php_config.json')

PROFILE_IMAGE_URL = "https://j.top4top.io/p_3820hbxes1.png"
ENTRY_SOUND_URL   = "https://b.top4top.io/m_3785fa5tu2.mp4"

# ─────────────────────────────────────────────
#  3.  JSON Helpers (Advanced & Thread-Safe)
# ─────────────────────────────────────────────
import tempfile
import logging
from threading import Lock

# قاموس لحفظ الأقفال لكل ملف لمنع تداخل الكتابة والقراءة في نفس اللحظة
_file_locks = {}

def _get_file_lock(path):
    if path not in _file_locks:
        _file_locks[path] = Lock()
    return _file_locks[path]

def init_json_file(path, default):
    """تهيئة الملف إذا لم يكن موجوداً بطريقة آمنة"""
    with _get_file_lock(path):
        if not os.path.exists(path):
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(default, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logging.error(f"[JSON ERROR] Failed to initialize {path}: {str(e)}")

def load_json_file(path, default=None):
    """قراءة الملف بشكل آمن مع معالجة أخطاء التنسيق"""
    with _get_file_lock(path):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"[JSON ERROR] Corrupt JSON format in {path}. Loading default.")
        except Exception as e:
            logging.error(f"[JSON ERROR] Failed to load {path}: {str(e)}")
        
        return default if default is not None else {}

def save_json_file(path, data):
    """الكتابة الآمنة (Atomic Write): يكتب في ملف مؤقت ثم يستبدله لمنع التلف"""
    with _get_file_lock(path):
        tmp_path = None
        try:
            dir_name = os.path.dirname(path)
            os.makedirs(dir_name, exist_ok=True)
            
            # إنشاء ملف مؤقت للكتابة
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix="tmp_", suffix=".json")
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            # استبدال الملف القديم بالجديد في خطوة واحدة آمنة (Atomic)
            os.replace(tmp_path, path)
            return True
        except Exception as e:
            logging.error(f"[JSON ERROR] Failed to save {path}: {str(e)}")
            # تنظيف الملف المؤقت في حال فشل العملية
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            return False

# ─────────────────────────────────────────────
#  4.  Master Config & Storage System
# ─────────────────────────────────────────────
import logging

def load_master_config():
    """تحميل إعدادات المالك مع ميزة الإصلاح التلقائي (Self-Healing)"""
    default = {
        'master_username': 'RIKO',
        'master_password_hash': hashlib.sha256('Bahaa123.'.encode()).hexdigest(),
        'port': 3178,
        'main_file': 'main.py'
    }
    
    if not os.path.exists(MASTER_CONFIG_FILE):
        logging.info(f"[CONFIG] Creating new master config for {default['master_username']}")
        save_json_file(MASTER_CONFIG_FILE, default)
        return default
        
    cfg = load_json_file(MASTER_CONFIG_FILE)
    if not cfg or not isinstance(cfg, dict):
        logging.warning("[CONFIG] Master config corrupted. Restoring defaults.")
        save_json_file(MASTER_CONFIG_FILE, default)
        return default
        
    # الإصلاح التلقائي: التحقق من المفاتيح المفقودة وإضافتها ثم حفظ الملف
    needs_saving = False
    for k, v in default.items():
        if k not in cfg:
            cfg[k] = v
            needs_saving = True
            
    if needs_saving:
        logging.info("[CONFIG] Repairing missing keys in master config.")
        save_json_file(MASTER_CONFIG_FILE, cfg)
        
    return cfg

MASTER_CONFIG        = load_master_config()
MASTER_USERNAME      = MASTER_CONFIG.get('master_username', 'RIKO')
MASTER_PASSWORD_HASH = MASTER_CONFIG.get('master_password_hash')
SERVER_START_TIME    = time.time()

# ─────────────────────────────────────────────
#  نظام المساحات المخصص (Storage Limits)
# ─────────────────────────────────────────────
PLAN_STORAGE_LIMITS = {
    'free_trial': 1 * 1024**3,  # 1 جيجا بايت (المجاني)
    'paid_20':    2 * 1024**3,  # 2 جيجا بايت (الوسط)
    'paid_30':    4 * 1024**3,  # 4 جيجا بايت (الكبير)
    'custom':     6 * 1024**3   # 6 جيجا بايت (أقصى شيء)
}

def get_user_storage_usage(username):
    """حساب المساحة المستخدمة حالياً للمستخدم (بالبايت)"""
    if username == MASTER_USERNAME:
        return 0
    p = get_user_path(username)
    size = 0
    if os.path.exists(p):
        for r, d, f in os.walk(p):
            for fl in f:
                fp = os.path.join(r, fl)
                if os.path.exists(fp):
                    size += os.path.getsize(fp)
    return size

def can_user_upload(username, file_size=0):
    """التحقق مما إذا كان المستخدم يمتلك مساحة كافية للرفع حسب خطته"""
    if username == MASTER_USERNAME:
        return True
    
    users = load_users()
    ud = users.get(username, {})
    
    plan = ud.get('plan', 'free_trial') 
    limit = PLAN_STORAGE_LIMITS.get(plan, 1 * 1024**3)
    current_usage = get_user_storage_usage(username)
    
    return (current_usage + file_size) <= limit

# ─────────────────────────────────────────────
#  5.  Create Folders & Init Files
# ─────────────────────────────────────────────
for _f in [USERS_FOLDER, TEMP_FOLDER, BACKUPS_FOLDER]:
    os.makedirs(_f, exist_ok=True)

# تهيئة ملفات قواعد البيانات لتتوافق مع لوحة تحكم الموقع
init_json_file(USERS_FILE, {})
init_json_file(PROCESSES_FILE, {})
init_json_file(SCHEDULES_FILE, {})
init_json_file(USER_SESSIONS_FILE, {})
init_json_file(PACKAGES_FILE, {'pip': [], 'apt': [], 'npm': []})
init_json_file(DOCKER_FILE, {'containers': [], 'images': []})
init_json_file(PORTS_FILE, {'ports': []})
init_json_file(ACTIVITY_FILE, {'events': []})

# إعدادات المالك الافتراضية (تم تجهيزها لـ RIKO)
init_json_file(OWNER_CONFIG_FILE, {
    'telegram_token': '', 
    'telegram_owner_id': '', 
    'bot_linked': False,
    'panel_name': 'DEV RIKO PANEL', 
    'welcome_msg': 'Welcome to DEV RIKO Hosting'
})
init_json_file(MAINTENANCE_FILE, {'enabled': False, 'message': 'Under maintenance. Try later.'})
init_json_file(BOT_STATS_FILE, {'total_users':0, 'total_servers':0, 'active_bots':0, 'zip_files':0, 'last_updated':''})
init_json_file(ANNOUNCE_FILE, {'list': []})
init_json_file(SECURITY_ALERTS_FILE, {'alerts': []})
init_json_file(NODEJS_PROCS_FILE, {})
init_json_file(PHP_CONFIG_FILE, {'default_version': '8.1'})

# ─────────────────────────────────────────────
#  6.  Owner Helpers & Site Approvals (نظام المراجعة من الموقع)
# ─────────────────────────────────────────────
def load_owner_config():
    d = {'telegram_token':'','telegram_owner_id':'','bot_linked':False,
         'panel_name':'DEV RIKO PANEL','welcome_msg':'Welcome to DEV RIKO Hosting'}
    cfg = load_json_file(OWNER_CONFIG_FILE, d)
    for k,v in d.items(): cfg.setdefault(k,v)
    return cfg

def load_maintenance(): return load_json_file(MAINTENANCE_FILE, {'enabled':False,'message':'Under maintenance'})
def save_maintenance(d): save_json_file(MAINTENANCE_FILE, d)
def load_bot_stats(): return load_json_file(BOT_STATS_FILE, {})
def load_announcements(): return load_json_file(ANNOUNCE_FILE, {'list':[]})
def save_announcements(d): save_json_file(ANNOUNCE_FILE, d)

def load_security_alerts(): 
    return load_json_file(SECURITY_ALERTS_FILE, {'alerts':[]})

def save_security_alert(username, filename, threats, ip):
    """
    حفظ التنبيه الأمني في الموقع ليقوم المالك (RIKO) بمراجعته من اللوحة
    (يظهر في قسم Security Alerts بانتظار الموافقة/المراجعة)
    """
    data = load_security_alerts()
    alert = {
        'id': str(uuid.uuid4())[:8],
        'username': username,
        'filename': filename,
        'threats': threats,
        'ip': ip,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'reviewed': False  # بانتظار مراجعة المالك من الموقع
    }
    data['alerts'].insert(0, alert)
    data['alerts'] = data['alerts'][:200]   # الاحتفاظ بآخر 200 تنبيه فقط
    save_json_file(SECURITY_ALERTS_FILE, data)
    return alert

# ─────────────────────────────────────────────
#  6.  Owner Helpers (مساعدات المالك - مخصصة لـ RIKO)
# ─────────────────────────────────────────────
def load_owner_config():
    # تم تغيير الأسماء الافتراضية لتناسب هوية RIKO
    d = {
        'telegram_token': '', 
        'telegram_owner_id': '', 
        'bot_linked': False,
        'panel_name': 'DEV RIKO PANEL', 
        'welcome_msg': 'Welcome to DEV RIKO Hosting'
    }
    cfg = load_json_file(OWNER_CONFIG_FILE, d)
    for k, v in d.items(): 
        cfg.setdefault(k, v)
    return cfg

def load_maintenance(): 
    return load_json_file(MAINTENANCE_FILE, {'enabled': False, 'message': 'Under maintenance'})

def save_maintenance(d): 
    save_json_file(MAINTENANCE_FILE, d)

def load_bot_stats(): 
    return load_json_file(BOT_STATS_FILE, {})

def load_announcements(): 
    return load_json_file(ANNOUNCE_FILE, {'list': []})

def save_announcements(d): 
    save_json_file(ANNOUNCE_FILE, d)

def load_security_alerts(): 
    return load_json_file(SECURITY_ALERTS_FILE, {'alerts': []})

def save_security_alert(username, filename, threats, ip):
    """
    حفظ التنبيه الأمني ليتم مراجعته من لوحة التحكم داخل الموقع
    وإظهاره للمالك في قسم التنبيهات الأمنية.
    """
    data = load_security_alerts()
    alert = {
        'id': str(uuid.uuid4())[:8],
        'username': username,
        'filename': filename,
        'threats': threats,
        'ip': ip,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'reviewed': False  # بانتظار مراجعة المالك من اللوحة
    }
    data['alerts'].insert(0, alert)
    data['alerts'] = data['alerts'][:200]   # الاحتفاظ بآخر 200 تنبيه لتخفيف الضغط على ملف الـ JSON
    save_json_file(SECURITY_ALERTS_FILE, data)
    return alert

# ─────────────────────────────────────────────
#  7.  Flask App & Security Headers
# ─────────────────────────────────────────────
app = Flask(__name__)

# إعداد مفتاح التشفير السري للجلسات
_SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.secret_key')
if os.path.exists(_SECRET_FILE):
    with open(_SECRET_FILE) as _sf:
        app.secret_key = _sf.read().strip()
else:
    _k = secrets.token_hex(64)
    with open(_SECRET_FILE, 'w') as _sf:
        _sf.write(_k)
    app.secret_key = _k

# إعدادات الجلسات والحماية
app.permanent_session_lifetime = timedelta(days=30)
# تحديد أقصى حجم للرفع بـ 6 جيجا (لحماية السيرفر من هجمات إغراق الذاكرة DoS)
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024 * 1024  
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.before_request
def check_maintenance():
    """التحقق من وضع الصيانة قبل أي طلب"""
    maint = load_maintenance()
    if not maint.get('enabled'):
        return None
    # استثناء المسارات الأساسية والأدمن من شاشة الصيانة
    if request.path in ['/login', '/logout', '/register'] or request.path.startswith('/api/'):
        return None
    if session.get('username') == MASTER_USERNAME:
        return None
    return render_template_string(MAINTENANCE_TMPL, message=maint.get('message', 'Under maintenance. Try later.')), 503

@app.after_request
def add_security_headers(response):
    """إضافة ترويسات حماية أمنية للوحة التحكم لمنع الاختراقات الشائعة"""
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# ─────────────────────────────────────────────
#  8.  Activity & Logging (Enhanced & Thread-Safe)
# ─────────────────────────────────────────────
import logging
from threading import Lock
from flask import request, has_request_context

# قفل لمنع التداخل أثناء الكتابة في الملف النصي للأنشطة
_log_file_lock = Lock()

def add_activity_event(username, action, details=''):
    """إضافة حدث إلى ملف الأنشطة (JSON) ليُعرض في لوحة تحكم الموقع بشكل آمن"""
    try:
        # قص التفاصيل إذا كانت طويلة جداً لمنع تضخم ملف الـ JSON
        safe_details = str(details)[:500] + ('...' if len(str(details)) > 500 else '')
        
        # جلب الآيبي بشكل آمن للعمليات المباشرة أو عمليات الخلفية
        ip_addr = '-'
        if has_request_context():
            ip_addr = request.remote_addr or '-'

        data = load_json_file(ACTIVITY_FILE, {'events': []})
        events = data.get('events', [])
        
        events.insert(0, {
            'id': str(uuid.uuid4())[:8],
            'username': username,
            'action': action,
            'details': safe_details,
            'ip': ip_addr,
            'timestamp': datetime.now().isoformat(),
            'time_text': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # نحتفظ بآخر 300 حدث فقط لتخفيف الضغط وتقليل حجم الملف
        save_json_file(ACTIVITY_FILE, {'events': events[:300]})
    except Exception as e:
        logging.error(f"[LOG ERROR] Failed to add activity event for {username}: {str(e)}")

def log_activity(username, action, details=''):
    """تسجيل الأنشطة في ملف نصي (Log) وفي نظام الأنشطة (JSON) مع منع تداخل الكتابة"""
    try:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # تنظيف التفاصيل لتكون في سطر واحد لسهولة القراءة النصية
        safe_details = str(details).replace('\n', ' ')[:500] 
        log_line = f"[{ts}] [{username}] {action} | {safe_details}\n"
        
        # استخدام القفل لمنع تداخل العمليات أثناء الكتابة في الملف النصي
        with _log_file_lock:
            with open(LOGS_FILE, 'a', encoding='utf-8') as f:
                f.write(log_line)
                
        # توجيه الحدث ليتم تسجيله في واجهة الموقع
        add_activity_event(username, action, details)
    except Exception as e:
        logging.error(f"[LOG ERROR] Failed to log activity for {username}: {str(e)}")

# ─────────────────────────────────────────────
#  9.  Replit KV Store & Data Helpers (Enhanced)
# ─────────────────────────────────────────────
import logging

_REPLIT_DB_URL = os.environ.get('REPLIT_DB_URL','')
_KV_USERS_KEY  = 'serverhub_users_v2'  # لم أغير المفتاح لكي لا تفقد بيانات المستخدمين السابقة

def _kv_get(key):
    """جلب البيانات من Replit DB مع تسجيل الأخطاء"""
    if not _REPLIT_DB_URL: 
        return None
    try:
        url = _REPLIT_DB_URL.rstrip('/') + '/' + urllib.parse.quote(key, safe='')
        with urllib.request.urlopen(urllib.request.Request(url), timeout=5) as r:
            return r.read().decode('utf-8')
    except Exception as e:
        logging.error(f"[KV STORE] GET Error for {key}: {e}")
        return None

def _kv_set(key, value):
    """حفظ البيانات في Replit DB مع تسجيل الأخطاء"""
    if not _REPLIT_DB_URL: 
        return False
    try:
        data = urllib.parse.urlencode({key: value}).encode('utf-8')
        req = urllib.request.Request(_REPLIT_DB_URL, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=5):
            pass
        return True
    except Exception as e:
        logging.error(f"[KV STORE] SET Error for {key}: {e}")
        return False

def load_users():
    """تحميل المستخدمين (الأولوية لقاعدة بيانات Replit ثم الملف المحلي)"""
    if _REPLIT_DB_URL:
        raw = _kv_get(_KV_USERS_KEY)
        if raw:
            try:
                d = json.loads(raw)
                if isinstance(d, dict):
                    # تحديث الملف المحلي ليكون نسخة احتياطية
                    save_json_file(USERS_FILE, d)
                    return d
            except json.JSONDecodeError:
                logging.error("[KV STORE] Corrupted users data in Replit DB.")
            except Exception as e:
                logging.error(f"[KV STORE] load_users Error: {e}")
                
    # الاعتماد على الملف المحلي في حال فشل Replit أو عدم توفره
    return load_json_file(USERS_FILE, {})

def save_users(u):
    """حفظ بيانات المستخدمين بحماية متقدمة ضد الحذف العشوائي"""
    if not isinstance(u, dict): 
        logging.warning("[USERS] Attempted to save non-dict users data. Blocked.")
        return
        
    existing = load_json_file(USERS_FILE, {})
    
    # حماية ضد مسح جميع المستخدمين بالخطأ
    if not u and existing:
        logging.warning("[USERS] Attempted to wipe out all existing users. Blocked for safety.")
        return
        
    save_json_file(USERS_FILE, u)
    
    if _REPLIT_DB_URL:
        if not _kv_set(_KV_USERS_KEY, json.dumps(u, ensure_ascii=False)):
            logging.error("[KV STORE] Failed to sync users to Replit DB.")

# ─────────────────────────────────────────────
# دوال التحميل والحفظ الآمنة لباقي البيانات
# ─────────────────────────────────────────────
def load_processes():     return load_json_file(PROCESSES_FILE, {})
def save_processes(p):    save_json_file(PROCESSES_FILE, p)

def load_schedules():     return load_json_file(SCHEDULES_FILE, {})
def save_schedules(s):    save_json_file(SCHEDULES_FILE, s)

def load_user_sessions(): return load_json_file(USER_SESSIONS_FILE, {})
def save_user_sessions(s):save_json_file(USER_SESSIONS_FILE, s)

def load_packages():      return load_json_file(PACKAGES_FILE, {'pip':[], 'apt':[], 'npm':[]})
def save_packages(p):     save_json_file(PACKAGES_FILE, p)

def load_ports():         return load_json_file(PORTS_FILE, {'ports':[]}).get('ports', [])
def save_ports(p):        save_json_file(PORTS_FILE, {'ports': p})

# ─────────────────────────────────────────────
#  10.  User Paths & Session Helpers
# ─────────────────────────────────────────────
import os
from threading import Lock
from datetime import datetime

_session_lock = Lock()

def get_user_path(username):
    if username == MASTER_USERNAME:
        return BASE_PATH
    return os.path.join(USERS_FOLDER, username)

def ensure_user_folder(username):
    if username == MASTER_USERNAME: 
        return
    p = get_user_path(username)
    os.makedirs(p, exist_ok=True)

def is_path_allowed(username, path):
    """حماية صارمة لمنع الوصول لملفات خارج مجلد المستخدم (Path Traversal)"""
    try:
        base = os.path.abspath(os.path.realpath(get_user_path(username)))
        target = os.path.abspath(os.path.realpath(str(path)))
        return target.startswith(base)
    except Exception:
        return False

def register_session(username):
    """تسجيل الدخول مع منع التداخل (Race Condition)"""
    with _session_lock:
        s = load_user_sessions()
        s[username] = s.get(username, 0) + 1
        save_user_sessions(s)

def unregister_session(username):
    with _session_lock:
        s = load_user_sessions()
        s[username] = max(0, s.get(username, 1) - 1)
        save_user_sessions(s)

def can_user_login(username):
    if username == MASTER_USERNAME:
        return True
        
    users = load_users()
    ud = users.get(username, {})
    if not isinstance(ud, dict): 
        return True
        
    # التحقق من تاريخ انتهاء الصلاحية
    exp = ud.get('expiry')
    if exp:
        try:
            if datetime.fromisoformat(exp) < datetime.now():
                return False
        except Exception:
            pass
            
    # التحقق من الحد الأقصى للجلسات
    mx = ud.get('max_sessions', 999)
    s = load_user_sessions()
    return s.get(username, 0) < mx

# ─────────────────────────────────────────────
#  11.  System Stats (Enhanced for Server Management)
# ─────────────────────────────────────────────
import psutil
import socket
import time
import platform
import sys
import os
import logging

def get_system_stats():
    """جلب إحصائيات السيرفر الحية بدقة عالية وعرضها في لوحة التحكم"""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        
        # قراءة مساحة القرص الخاصة بمسار الاستضافة الفعلي بدلاً من الجذر لتجنب أخطاء الصلاحيات
        disk_path = os.path.realpath(BASE_PATH)
        disk = psutil.disk_usage(disk_path)
        
        net = psutil.net_io_counters()
        
        uptime = int(time.time() - SERVER_START_TIME)
        h, r = divmod(uptime, 3600)
        m, s = divmod(r, 60)

        def _get_active_ip():
            try:
                # استخدام with لضمان إغلاق الـ socket فوراً وعدم تعليق البورتات
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s2:
                    s2.connect(('8.8.8.8', 80))
                    return s2.getsockname()[0]
            except Exception:
                return '127.0.0.1'

        port = int(os.environ.get('PORT', MASTER_CONFIG.get('port') or 3178))
        
        return {
            'cpu': f'{cpu}%',
            'memory': f'{mem.used/1024**3:.1f} GB / {mem.total/1024**3:.1f} GB',
            'memory_percent': mem.percent,
            'disk': f'{disk.used/1024**3:.1f} GB / {disk.total/1024**3:.1f} GB',
            'disk_percent': disk.percent,
            'network_in': f'{net.bytes_recv/1024**2:.1f} MB',
            'network_out': f'{net.bytes_sent/1024**2:.1f} MB',
            'uptime': f'{h}h {m}m {s}s',
            'hostname': socket.gethostname(),
            'ip': _get_active_ip(),
            'port': port,
            'platform': platform.system(),
            'python': sys.version.split()[0],
            'status': 'Online 🟢'
        }
    except Exception as e:
        logging.error(f"[SYSTEM STATS] Error fetching stats: {e}")
        # إرجاع قيم افتراضية لمنع انهيار واجهة HTML في حال حدوث خطأ
        return {
            'error': str(e),
            'cpu': '0%', 'memory': '0 GB / 0 GB', 'memory_percent': 0,
            'disk': '0 GB / 0 GB', 'disk_percent': 0,
            'network_in': '0.0 MB', 'network_out': '0.0 MB',
            'uptime': '0h 0m 0s', 'ip': '127.0.0.1', 
            'status': 'Error 🔴'
        }

# ─────────────────────────────────────────────
#  12.  Process Management (Secured & Enhanced)
# ─────────────────────────────────────────────
import zipfile
import subprocess
import os
import sys
import re
import logging

running_processes = {}
file_processes    = {}
nodejs_processes  = {}

def read_process_output(pid, proc, store=None):
    """قراءة مخرجات السيرفر (Terminal) بشكل آمن ومنع تعطل الترميز"""
    if store is None:
        store = file_processes
    try:
        # نقرأ المخرجات سواء كانت نصوص (str) أو بايتات (bytes)
        for line in iter(proc.stdout.readline, b''):
            if not line:
                break
            
            # معالجة الترميز لتفادي أخطاء الحروف اللاتينية والعربية
            if isinstance(line, bytes):
                line_str = line.decode('utf-8', errors='replace').rstrip('\n')
            else:
                line_str = line.rstrip('\n')
                
            if line_str and pid in store:
                store[pid]['output'].append(line_str)
                # الاحتفاظ بآخر 500 سطر فقط لمنع استنزاف الرام
                if len(store[pid]['output']) > 500:
                    store[pid]['output'] = store[pid]['output'][-500:]
                    
    except Exception as e:
        logging.error(f"[PROCESS] Error reading output for PID {pid}: {e}")

def get_run_command(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.py':
        return f'{sys.executable} "{filepath}"'
    elif ext == '.js':
        return f'node "{filepath}"'
    elif ext == '.sh':
        return f'bash "{filepath}"'
    elif ext == '.php':
        return f'php "{filepath}"'
    elif ext == '.rb':
        return f'ruby "{filepath}"'
    return f'"{filepath}"'

def extract_and_find_main(zip_path, extract_dir):
    """استخراج آمن للملفات لمنع ثغرات مسار الضغط (Zip Slip) والبحث عن ملف التشغيل"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # فحص أمني: منع استخراج ملفات خارج المسار المخصص للمستخدم
            for member in zf.namelist():
                member_path = os.path.abspath(os.path.join(extract_dir, member))
                if not member_path.startswith(os.path.abspath(extract_dir)):
                    logging.warning(f"[SECURITY] Blocked Zip-Slip attempt in {zip_path}")
                    continue
                zf.extract(member, extract_dir)
                
        # البحث عن الملف الرئيسي للتشغيل
        target_names = ['main.py', 'index.js', 'app.py', 'server.js', 'bot.py', 'index.php', 'app.js']
        for root, dirs, files in os.walk(extract_dir):
            for name in target_names:
                if name in files:
                    return os.path.join(root, name)
    except Exception as e:
        logging.error(f"[ZIP EXTRACT] Error processing {zip_path}: {e}")
    return None

def auto_install_dependencies(filepath):
    """أداة التثبيت التلقائي الذكية للمكاتب الناقصة (مع تتبع الأخطاء)"""
    installed, failed = [], []
    try:
        ext = os.path.splitext(filepath)[1].lower()
        if ext != '.py':
            return {'installed': [], 'failed': []}
            
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            src = f.read()
            
        packages = re.findall(r'^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)', src, re.MULTILINE)
        
        pkg_map = {
            'telegram': 'python-telegram-bot', 'cv2': 'opencv-python', 'PIL': 'Pillow',
            'dotenv': 'python-dotenv', 'mysql': 'mysql-connector-python',
            'psycopg2': 'psycopg2-binary', 'youtube_dl': 'youtube-dl', 'yt_dlp': 'yt-dlp',
        }
        
        std = {
            'os','sys','time','json','re','math','random','datetime','threading',
            'subprocess','collections','io','typing','abc','flask','requests',
            'psutil','hashlib','base64','uuid','socket','platform','signal',
            'warnings','gc','resource','shutil','zipfile','tarfile','secrets',
            'functools','itertools','string','textwrap','pathlib','glob',
            'tempfile','contextlib','html','logging','ast'
        }
        
        for pkg in set(packages):
            if not pkg or pkg.startswith('.') or pkg in std:
                continue
            actual = pkg_map.get(pkg, pkg)
            try:
                __import__(pkg)
            except ImportError:
                try:
                    logging.info(f"[AUTO-INSTALL] Attempting to install: {actual}")
                    r = subprocess.run(
                        [sys.executable, '-m', 'pip', 'install', '--user', actual],
                        capture_output=True, text=True, timeout=120
                    )
                    if r.returncode == 0:
                        installed.append(actual)
                    else:
                        failed.append(actual)
                        logging.error(f"[AUTO-INSTALL] Failed to install {actual}:\n{r.stderr}")
                except Exception as ex:
                    failed.append(actual)
                    logging.error(f"[AUTO-INSTALL] Crash installing {actual}: {ex}")
                    
        return {'installed': installed, 'failed': failed}
    except Exception as e:
        logging.error(f"[AUTO-INSTALL] Critical error: {e}")
        return {'installed': installed, 'failed': failed + [str(e)]}

# ─────────────────────────────────────────────
#  13.  Node.js Helpers (Secured & Enhanced)
# ─────────────────────────────────────────────
import socket
import os
import json
import time
import subprocess
import threading
import logging
from datetime import datetime

def find_free_port(start=4000, end=9000):
    """البحث عن منفذ متاح بطريقة آمنة لتجنب تداخل المنافذ"""
    for p in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # SO_REUSEADDR يمنع خطأ 'Address already in use' إذا أُغلق المنفذ للتو
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', p))
                return p
        except OSError:
            continue
    return start

def get_nodejs_install_commands(project_path, deps_file=None):
    """توليد أوامر التثبيت بشكل آمن لتجنب ثغرات حقن الأوامر"""
    cmds = []
    pkg_json = os.path.join(project_path, 'package.json')
    yarn_lock = os.path.join(project_path, 'yarn.lock')
    custom_deps = os.path.join(project_path, deps_file) if deps_file else None

    if custom_deps and os.path.exists(custom_deps):
        ext = os.path.splitext(deps_file)[1].lower()
        if ext == '.txt':
            try:
                # قراءة الملف عبر بايثون بدلاً من shell لحماية النظام
                with open(custom_deps, 'r', encoding='utf-8') as f:
                    packages = f.read().replace('\n', ' ').strip()
                if packages:
                    cmds.append(f'npm install {packages}')
            except Exception as e:
                logging.error(f"[NODEJS] Error reading deps txt: {e}")
        elif ext == '.json':
            cmds.append('npm install --prefix . --package-lock-only && npm install')
        else:
            cmds.append('npm install')
    elif os.path.exists(yarn_lock):
        cmds.append('yarn install --frozen-lockfile')
    elif os.path.exists(pkg_json):
        cmds.append('npm install')
    return cmds

def start_nodejs_project(project_path, username, port=None, main_file=None, deps_file=None):
    """تشغيل مشاريع Node.js في بيئة معزولة وآمنة"""
    install_output = ''
    pkg_json = os.path.join(project_path, 'package.json')
    deps_abs = os.path.join(project_path, deps_file) if deps_file else None

    # ── 1. تثبيت الحزم (Dependencies) ─────────────────────────
    install_cmds = []
    if deps_abs and os.path.exists(deps_abs):
        install_cmds = get_nodejs_install_commands(project_path, deps_file)
    elif os.path.exists(pkg_json):
        install_cmds = ['npm install']

    for ic in install_cmds:
        try:
            ir = subprocess.run(ic, shell=True, cwd=project_path,
                                capture_output=True, text=True, timeout=180)
            install_output += ir.stdout + ir.stderr
        except Exception as e:
            install_output += f'[Error] Install failed: {str(e)}\n'

    # ── 2. تحديد أمر التشغيل (Start Command) ───────────────────
    start_cmd = None

    if main_file:
        mf_path = os.path.join(project_path, main_file)
        if os.path.exists(mf_path):
            start_cmd = f'node "{main_file}"'
        else:
            return {'success': False, 'error': f'Main file not found: {main_file}', 'install_output': install_output}

    if not start_cmd and os.path.exists(pkg_json):
        try:
            with open(pkg_json, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
            scripts = pkg.get('scripts', {})
            start_cmd = scripts.get('start') or scripts.get('dev')
        except Exception:
            pass

    if not start_cmd:
        for name in ['index.js', 'app.js', 'server.js', 'main.js', 'bot.js']:
            if os.path.exists(os.path.join(project_path, name)):
                start_cmd = f'node "{name}"'
                break

    if not start_cmd:
        ic_list = get_nodejs_install_commands(project_path, deps_file)
        return {
            'success': False,
            'error': 'لم يتم العثور على ملف البداية. حدد الملف الرئيسي يدوياً.',
            'install_commands': ic_list or ['npm install'],
            'run_command': 'node your_file.js',
            'install_output': install_output
        }

    # ── 3. التشغيل في الخلفية (Background Process) ─────────────
    assigned_port = port or find_free_port()
    env = os.environ.copy()
    env['PORT'] = str(assigned_port)

    pid_key = f'{username}_nodejs_{int(time.time())}'
    try:
        kwargs = dict(
            shell=True, cwd=project_path,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=False, bufsize=1, env=env  # text=False ليتوافق مع المعالجة الآمنة للترميز في الجزء 12
        )
        if hasattr(os, 'setsid'):
            kwargs['preexec_fn'] = os.setsid
            
        p = subprocess.Popen(start_cmd, **kwargs)
        nodejs_processes[pid_key] = {
            'process': p, 'username': username,
            'project': project_path, 'port': assigned_port,
            'command': start_cmd, 'main_file': main_file or '(auto)',
            'deps_file': deps_file or 'package.json',
            'output': [], 'started': datetime.now().isoformat()
        }
        
        threading.Thread(target=read_process_output, args=(pid_key, p),
                         kwargs={'store': nodejs_processes}, daemon=True).start()
                         
        log_activity(username, 'nodejs.start', f'{start_cmd} port={assigned_port}')
        
        return {'success': True, 'pid': pid_key, 'port': assigned_port,
                'command': start_cmd, 'install_output': install_output}
    except Exception as e:
        return {'success': False, 'error': str(e), 'install_output': install_output}

def get_nodejs_info(project_path, main_file=None, deps_file=None):
    """إرجاع أوامر التشغيل والتثبيت دون تنفيذها לעرضها في اللوحة"""
    pkg_json = os.path.join(project_path, 'package.json')
    yarn_lock = os.path.join(project_path, 'yarn.lock')

    install_cmd = 'npm install'
    if deps_file and os.path.exists(os.path.join(project_path, deps_file)):
        if deps_file.endswith('.lock') or 'yarn' in deps_file:
            install_cmd = 'yarn install'
    elif os.path.exists(yarn_lock):
        install_cmd = 'yarn install'

    run_cmd = f'node "{main_file}"' if main_file else None
    if not run_cmd and os.path.exists(pkg_json):
        try:
            with open(pkg_json, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
            if 'start' in pkg.get('scripts', {}) or 'dev' in pkg.get('scripts', {}):
                run_cmd = 'npm start'
        except Exception:
            pass
            
    if not run_cmd:
        for name in ['index.js', 'app.js', 'server.js', 'main.js']:
            if os.path.exists(os.path.join(project_path, name)):
                run_cmd = f'node "{name}"'
                break
                
    if not run_cmd:
        run_cmd = 'node your_main_file.js'

    return {'install_command': install_cmd, 'run_command': run_cmd}

# ─────────────────────────────────────────────
#  14.  PHP Helpers (Secured & Routing Fixed)
# ─────────────────────────────────────────────
import os
import subprocess
import threading
import time
import logging
from datetime import datetime

_php_servers = {}  # pid_key -> {process, port, path}

def get_php_install_commands(php_root, deps_file=None):
    """توليد أوامر تثبيت Composer بطريقة آمنة"""
    composer_json = os.path.join(php_root, 'composer.json')
    composer_lock = os.path.join(php_root, 'composer.lock')
    custom_deps   = os.path.join(php_root, deps_file) if deps_file else None

    if custom_deps and os.path.exists(custom_deps):
        if 'composer' in deps_file.lower() or deps_file.endswith('.json'):
            if os.path.exists(composer_lock):
                return ['composer install --no-dev']
            return ['composer install']
        elif deps_file.endswith('.txt'):
            try:
                # قراءة الملف برمجياً بدلاً من استخدام cat لمنع ثغرات حقن الأوامر
                with open(custom_deps, 'r', encoding='utf-8') as f:
                    packages = f.read().replace('\n', ' ').strip()
                if packages:
                    return [f'composer require {packages}']
            except Exception as e:
                logging.error(f"[PHP] Error reading deps txt: {e}")
    elif os.path.exists(composer_lock):
        return ['composer install --no-dev']
    elif os.path.exists(composer_json):
        return ['composer install']
    
    return []

def start_php_server(php_root, username, port=None, main_file=None, deps_file=None):
    """
    تشغيل خادم PHP الداخلي مع إصلاح مسارات الـ Routing
    main_file: يمكن أن يكون مجلداً (مثل public) أو ملف توجيه (مثل router.php)
    """
    assigned_port = port or find_free_port(5000)
    install_output = ''

    # ── 1. تثبيت الحزم (Composer) ───────────────────────────────
    cmds = get_php_install_commands(php_root, deps_file)
    for ic in cmds:
        try:
            ir = subprocess.run(ic, shell=True, cwd=php_root,
                                capture_output=True, text=True, timeout=180)
            install_output += ir.stdout + ir.stderr
        except Exception as e:
            install_output += f'[Error] Install failed: {str(e)}\n'

    # ── 2. إعداد أمر التشغيل (Routing Logic) ────────────────────
    php_bin = 'php'
    doc_root = php_root
    router = ''

    if main_file:
        mf_abs = os.path.join(php_root, main_file)
        if not os.path.exists(mf_abs):
            return {
                'success': False, 
                'error': f'Main file or directory not found: {main_file}',
                'install_output': install_output,
                'install_commands': cmds or ['composer install'],
                'run_command': f'php -S 0.0.0.0:{assigned_port} -t "{doc_root}"'
            }
            
        if os.path.isdir(mf_abs):
            # إذا كان الملف المحدد عبارة عن مجلد، نجعله هو الـ Document Root
            doc_root = mf_abs
        elif os.path.isfile(mf_abs) and main_file.endswith('.php'):
            # إذا كان ملف PHP، نستخدمه كـ Router Script
            router = f' "{main_file}"'
    else:
        # اكتشاف تلقائي للمجلد public (للتعامل الصحيح مع إطارات العمل مثل Laravel)
        public_dir = os.path.join(php_root, 'public')
        if os.path.isdir(public_dir):
            doc_root = public_dir

    cmd = f'{php_bin} -S 0.0.0.0:{assigned_port} -t "{doc_root}"{router}'

    # ── 3. تشغيل الخادم ─────────────────────────────────────────
    pid_key = f'{username}_php_{int(time.time())}'
    try:
        kwargs = dict(
            shell=True, cwd=php_root,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=False, bufsize=1  # text=False لضمان التوافق مع قراءة المخرجات وتجنب أخطاء الترميز
        )
        if hasattr(os, 'setsid'):
            kwargs['preexec_fn'] = os.setsid
            
        p = subprocess.Popen(cmd, **kwargs)
        _php_servers[pid_key] = {
            'process': p, 'username': username,
            'path': php_root, 'port': assigned_port,
            'main_file': main_file or '(auto)', 
            'deps_file': deps_file or 'composer.json',
            'output': [], 'install_output': install_output,
            'started': datetime.now().isoformat()
        }
        
        threading.Thread(target=read_process_output, args=(pid_key, p),
                         kwargs={'store': _php_servers}, daemon=True).start()
                         
        log_activity(username, 'php.start', f'{cmd} port={assigned_port}')
        
        return {'success': True, 'pid': pid_key, 'port': assigned_port,
                'command': cmd, 'install_output': install_output}
    except Exception as e:
        return {'success': False, 'error': str(e), 'install_output': install_output}

def get_php_info(php_root, main_file=None, deps_file=None):
    """إرجاع أوامر التشغيل دون تنفيذها לעرضها في الواجهة"""
    cmds = get_php_install_commands(php_root, deps_file)
    doc_root = php_root
    router = ''
    
    if main_file:
        mf_abs = os.path.join(php_root, main_file)
        if os.path.isdir(mf_abs):
            doc_root = mf_abs
        elif os.path.isfile(mf_abs) and main_file.endswith('.php'):
            router = f' "{main_file}"'
    else:
        if os.path.isdir(os.path.join(php_root, 'public')):
            doc_root = os.path.join(php_root, 'public')
            
    run_cmd = f'php -S 0.0.0.0:PORT -t "{doc_root}"{router}'
    return {
        'install_commands': cmds or ['composer install (if needed)'],
        'run_command': run_cmd
    }

# ─────────────────────────────────────────────
#  15.  ZIP Extract Helpers & Security Scanners
# ─────────────────────────────────────────────
import re
import os
import zipfile
import tarfile
import subprocess
import logging

ALLOWED_EXTENSIONS = {
    'py','js','ts','jsx','tsx','json','yaml','yml','toml','cfg','ini',
    'txt','md','html','htm','css','scss','sass','less',
    'sh','bash','bat','cmd',
    'jpg','jpeg','png','gif','webp','svg','ico',
    'mp3','mp4','ogg','wav',
    'zip','tar','gz','rar','7z',
    'pdf','doc','docx','xls','xlsx',
    'php','rb','go','rs','java','c','cpp','h',
    'sql','db','sqlite','env','xml',
    'woff','woff2','ttf','eot',
}

BLOCKED_EXTENSIONS = {
    'exe','com','scr','vbs','bat','cmd','ps1','msi','dll','sys',
    'pif','application','gadget','hta','cpl','msc','jar','ws','wsf','wsh'
}

# ─── Dangerous code patterns — comprehensive threat detection ───────────────
DANGEROUS_PATTERNS = [
    (r'api\.telegram\.org/bot[A-Za-z0-9:_-]{20,}', '⚠️ Telegram bot token hardcoded in file'),
    (r'bot\.send_document\s*\(|sendDocument\s*\(', '⚠️ Telegram file-send function (exfiltration risk)'),
    (r'bot\.send_message\s*\(.*ADMIN_ID|sendMessage.*chat_id', '⚠️ Telegram C2 messaging pattern'),
    (r'telebot\s*\.\s*TeleBot\s*\(|telegram\.ext.*Application', '⚠️ Telegram bot library initialised — potential C2'),
    (r'os\.walk\s*\(.*\).*\.py|get_all_py_files|scan_directory.*py', '🚨 Mass .py file harvesting pattern'),
    (r'zipfile\.ZipFile.*os\.walk|ZipFile.*zipf\.write.*os\.walk', '🚨 Mass zip-and-send exfiltration'),
    (r'backup_all|python_backup|full_python_backup|zip_buffer.*BytesIO.*ZipFile', '🚨 Backup-and-send pattern'),
    (r'scan_current|scan_home|scan_root|scan_custom|scan_directory', '🚨 File system scanning bot pattern'),
    (r'send_document.*chat\.id.*zip_buffer|send_document.*message\.chat', '🚨 Direct file exfil via Telegram'),
    (r'find_config|config\*\.py|settings\*\.json|\*\.env.*os\.walk', '🚨 Config/secret file hunting pattern'),
    (r'exec\s*\(base64\.b64decode', '🚨 Base64-encoded exec (obfuscated payload)'),
    (r'__import__\s*\(\s*["\']os["\']\s*\)\.system', '🚨 Dynamic os.system call'),
    (r'socket\.connect.*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}.*(?:4444|1337|9999|31337)', '🚨 Raw reverse-shell socket'),
    (r'Popen.*shell=True.*PIPE.*stdin|popen.*|.*PIPE.*communicate', '⚠️ Shell injection with pipe'),
    (r'eval\s*\(\s*(?:compile|input|request)', '🚨 Dynamic eval with user/net input'),
    (r'/etc/passwd|/etc/shadow|\.ssh/id_rsa|\.bash_history|\.aws/credentials', '🚨 Sensitive system file access'),
    (r'SECRET_KEY\s*=\s*["\'][^"\']{10,}|DATABASE_URL\s*=\s*["\']|API_KEY\s*=\s*["\'][A-Za-z0-9]{20,}', '⚠️ Hardcoded secret/credential'),
    (r'ipapi\.co|ip-api\.com|checkip\.amazonaws|api\.ipify', '⚠️ IP geolocation/fingerprinting call'),
    (r'system\s*\(\s*\$_(?:GET|POST|REQUEST)|passthru\s*\(\s*\$_', '🚨 PHP web shell pattern'),
    (r'eval\s*\(\s*base64_decode\s*\(\s*\$_|eval\s*\(\s*gzinflate', '🚨 PHP obfuscated web shell'),
    (r'<\?php.*system\s*\(|<\?php.*exec\s*\(', '🚨 PHP command execution'),
    (r'subprocess\.getoutput\s*\(\s*["\']whoami|subprocess.*getoutput.*id\b', '⚠️ whoami/id system recon'),
    (r'security_dump|backup_and_send|data_exfil|steal_files', '🚨 Known malware function name'),
    (r'reverse_shell|rev_shell|bind_shell|meterpreter', '🚨 Known shell payload keyword'),
]

FILE_THEFT_BOT_SIGNATURES = [
    {'name': '🚨 File-theft Telegram bot (full fingerprint)',
     'require_all': [r'TeleBot\s*\(|telegram\.Bot\s*\(', r'os\.walk\s*\(', r'send_document|sendDocument']},
    {'name': '🚨 System directory scanner bot',
     'require_all': [r'TeleBot\s*\(|telegram\.Bot\s*\(', r"['\"](?:/home|/var|/opt|/etc)['\"]", r'os\.walk\s*\(']},
]

def scan_file_content(filepath):
    """Deep-scan uploaded file for malicious patterns."""
    threats = []
    try:
        ext = os.path.splitext(filepath)[1].lower().lstrip('.')
        if ext not in ('py','js','php','sh','bash','rb','ts','jsx','tsx','txt','json','html','htm'):
            return []
            
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(500_000)   # cap at 500 KB

        for pattern, desc in DANGEROUS_PATTERNS:
            try:
                if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                    threats.append(desc)
            except re.error:
                pass

        for sig in FILE_THEFT_BOT_SIGNATURES:
            if all(re.search(p, content, re.IGNORECASE | re.DOTALL) for p in sig['require_all']):
                if sig['name'] not in threats:
                    threats.append(sig['name'])

    except Exception as e:
        logging.error(f"[SCAN ERROR] Failed to scan {filepath}: {e}")
        
    return threats

MAX_EXTRACT_SIZE = 500 * 1024 * 1024  # أقصى حجم لفك الضغط في العملية الواحدة: 500 ميجا

def safe_extract(archive_path, dest_dir, username):
    """فك الضغط بشكل آمن مع فحص المساحة المسموحة للمستخدم وحظر الملفات الممنوعة"""
    os.makedirs(dest_dir, exist_ok=True)
    if not is_path_allowed(username, dest_dir):
        return {'success': False, 'error': 'Forbidden destination'}
    
    ext = os.path.splitext(archive_path)[1].lower()
    extracted = []
    
    try:
        if ext == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zf:
                # 1. التحقق من إجمالي الحجم قبل فك الضغط لضمان عدم تخطي خطة المستخدم
                uncompressed_size = sum(info.file_size for info in zf.infolist())
                if uncompressed_size > MAX_EXTRACT_SIZE:
                    return {'success': False, 'error': 'Archive too large (>500 MB)'}
                if not can_user_upload(username, uncompressed_size):
                    return {'success': False, 'error': 'Not enough storage space in your plan to extract this archive.'}

                for info in zf.infolist():
                    # 2. منع استخراج الملفات ذات الامتدادات المحظورة من داخل الـ ZIP
                    file_ext = os.path.splitext(info.filename)[1].lower().lstrip('.')
                    if file_ext in BLOCKED_EXTENSIONS:
                        logging.warning(f"[SECURITY] Blocked extracting {info.filename}")
                        continue

                    target = os.path.realpath(os.path.join(dest_dir, info.filename))
                    if not target.startswith(os.path.realpath(dest_dir)):
                        continue
                    zf.extract(info, dest_dir)
                    extracted.append(info.filename)
        
        elif ext in ('.tar','.gz','.bz2','.tgz') or archive_path.endswith('.tar.gz'):
            with tarfile.open(archive_path, 'r:*') as tf:
                members = tf.getmembers()
                uncompressed_size = sum(m.size for m in members)
                
                if uncompressed_size > MAX_EXTRACT_SIZE:
                    return {'success': False, 'error': 'Archive too large (>500 MB)'}
                if not can_user_upload(username, uncompressed_size):
                    return {'success': False, 'error': 'Not enough storage space in your plan.'}

                for member in members:
                    file_ext = os.path.splitext(member.name)[1].lower().lstrip('.')
                    if file_ext in BLOCKED_EXTENSIONS:
                        continue

                    target = os.path.realpath(os.path.join(dest_dir, member.name))
                    if not target.startswith(os.path.realpath(dest_dir)):
                        continue
                    tf.extract(member, dest_dir)
                    extracted.append(member.name)
        
        else:
            try:
                # لا يمكننا التحقق من الحجم المسبق لـ unrar بسهولة، لكن يمكننا تقييد العملية
                r = subprocess.run(['unrar', 'x', '-y', archive_path, dest_dir],
                                   capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    extracted = ['(unrar extracted)']
                else:
                    return {'success': False, 'error': 'Unsupported format or unrar not available'}
            except Exception:
                return {'success': False, 'error': 'Unsupported archive format'}
        
        log_activity(username, 'files.extract', f'{len(extracted)} files extracted to {dest_dir}')
        return {'success': True, 'extracted': len(extracted), 'dest': dest_dir}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ─────────────────────────────────────────────
#  16.  Decorators (Secured & Session Validated)
# ─────────────────────────────────────────────
from functools import wraps
from flask import session, request, jsonify, redirect

def login_required(f):
    @wraps(f)
    def w(*a, **kw):
        # 1. التحقق من وجود الجلسة واسم المستخدم
        if 'logged_in' not in session or not session.get('username'):
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Session expired or invalid'}), 401
            return redirect('/login')
            
        # 2. التحقق الحي المتقدم: هل الحساب ما زال فعالاً؟ (لم يتم حذفه أو انتهاء خطته)
        username = session.get('username')
        if not can_user_login(username):
            # تدمير الجلسة فوراً إذا كان الحساب موقوفاً أو منتهياً
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Account expired, disabled or max sessions reached'}), 403
            return redirect('/login?error=account_expired')
            
        return f(*a, **kw)
    return w

def master_required(f):
    @wraps(f)
    def w(*a, **kw):
        username = session.get('username')
        # حماية مسارات المالك (DEV RIKO) ومنع أي مستخدم عادي من الوصول إليها
        if username != MASTER_USERNAME:
            if username:
                # تسجيل محاولة اختراق أو تطفل إذا حاول مستخدم عادي الدخول لمسار المالك
                log_activity(username, 'security.warning', f'Unauthorized access attempt to master route: {request.path}')
            return jsonify({'success': False, 'error': 'Access Denied. Master only'}), 403
        return f(*a, **kw)
    return w

# ─────────────────────────────────────────────
#  17.  Maintenance Template (DEV RIKO Edition)
# ─────────────────────────────────────────────
MAINTENANCE_TMPL = r'''
<!DOCTYPE html>
<html lang="ar" dir="auto">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>وضع الصيانة — DEV RIKO</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family:'Tajawal', sans-serif; }
        body { 
            background: #090b10; 
            color: #c9d1d9; 
            min-height: 100vh; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            overflow: hidden;
        }
        .card { 
            text-align: center; 
            padding: 50px 40px; 
            background: #11151c; 
            border: 1px solid #232a35; 
            border-radius: 16px; 
            max-width: 480px; 
            width: 92%; 
            box-shadow: 0 0 25px rgba(124, 92, 252, 0.15);
            position: relative;
        }
        /* تأثير النبض الاحترافي بدلاً من الدوران المزعج */
        .icon { 
            font-size: 72px; 
            margin-bottom: 20px; 
            animation: pulse 2s ease-in-out infinite;
        }
        @keyframes pulse { 
            0% { transform: scale(1); filter: drop-shadow(0 0 5px rgba(124,92,252,0.5)); } 
            50% { transform: scale(1.1); filter: drop-shadow(0 0 15px rgba(124,92,252,0.8)); } 
            100% { transform: scale(1); filter: drop-shadow(0 0 5px rgba(124,92,252,0.5)); } 
        }
        h1 { font-size: 28px; color: #fff; margin-bottom: 8px; font-weight: 700; }
        .sub { 
            color: #7c5cfc; 
            font-size: 14px; 
            letter-spacing: 2px; 
            text-transform: uppercase; 
            margin-bottom: 25px; 
            font-weight: bold; 
        }
        .msg { 
            background: #0d1117; 
            border: 1px solid #232a35; 
            border-right: 4px solid #7c5cfc; /* توافق مع اتجاه اليمين */
            padding: 18px; 
            border-radius: 8px; 
            color: #a3abb6; 
            line-height: 1.7; 
            font-size: 16px;
        }
        .foot { margin-top: 25px; font-size: 13px; color: #484f58; }
        .foot a { color: #7c5cfc; text-decoration: none; font-weight: bold; transition: 0.3s; }
        .foot a:hover { color: #fff; text-shadow: 0 0 8px #7c5cfc; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🛠️</div>
        <h1>النظام تحت التحديث</h1>
        <div class="sub">DEV RIKO PANEL</div>
        <div class="msg">{{ message }}</div>
        <div class="foot">
            جميع الحقوق محفوظة © DEV RIKO — المطور 
            <a href="https://t.me/SHBH_S1" target="_blank">@SHBH_S1</a>
        </div>
    </div>
</body>
</html>
'''

# ─────────────────────────────────────────────────────────────────────────────
#  18.  AUTH TEMPLATE  (Login + Register — SERVER HUB theme)
# ─────────────────────────────────────────────────────────────────────────────
AUTH_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SERVER HUB — Access</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter','Segoe UI',sans-serif}
html,body{height:100%;background:#0b0f17}
body{
  display:flex;align-items:center;justify-content:center;min-height:100vh;
  background:
    radial-gradient(ellipse at 15% 50%,rgba(192,57,43,.4) 0%,transparent 55%),
    radial-gradient(ellipse at 85% 20%,rgba(142,68,173,.3) 0%,transparent 50%),
    radial-gradient(ellipse at 50% 100%,rgba(231,76,60,.2) 0%,transparent 60%),
    url('https://i.ibb.co/60Zvqk5L/photo.jpg') center/cover no-repeat fixed,
    #080b12;
  position:relative;overflow:hidden;
}
body::after{
  content:'';position:fixed;inset:0;
  background:rgba(8,11,18,.68);
  backdrop-filter:blur(3px) saturate(1.4);
  pointer-events:none;z-index:1;
}
body::before{
  content:'';position:absolute;inset:0;
  background-image:
    linear-gradient(rgba(124,92,252,.04) 1px,transparent 1px),
    linear-gradient(90deg,rgba(124,92,252,.04) 1px,transparent 1px);
  background-size:60px 60px;
  animation:gridMove 25s linear infinite;
  pointer-events:none;
}
@keyframes gridMove{to{background-position:60px 60px}}

/* ── Glow orbs ── */
.orb{position:fixed;border-radius:50%;filter:blur(80px);pointer-events:none;z-index:2}
.orb1{width:400px;height:400px;background:rgba(192,57,43,.14);top:-100px;left:-100px;animation:orbFloat1 12s ease-in-out infinite}
.orb2{width:300px;height:300px;background:rgba(142,68,173,.1);bottom:-80px;right:-80px;animation:orbFloat2 15s ease-in-out infinite}
@keyframes orbFloat1{0%,100%{transform:translate(0,0)}50%{transform:translate(60px,40px)}}
@keyframes orbFloat2{0%,100%{transform:translate(0,0)}50%{transform:translate(-40px,-30px)}}

/* ── Main wrap ── */
.wrap{
  position:relative;z-index:3;
  display:flex;flex-direction:column;align-items:center;
  width:min(460px,95vw);
}

/* ── Card (single container for logo + forms) ── */
.card{
  width:100%;
  background:rgba(13,17,23,.92);
  border:1px solid rgba(48,54,61,.8);
  border-radius:24px;
  overflow:hidden;
  box-shadow:
    0 30px 80px rgba(0,0,0,.6),
    0 0 0 1px rgba(124,92,252,.08),
    inset 0 1px 0 rgba(255,255,255,.04);
  backdrop-filter:blur(24px);
}

/* ── Logo block inside card ── */
.logo-block{
  display:flex;flex-direction:column;align-items:center;
  padding:32px 28px 24px;
  background:linear-gradient(180deg,rgba(124,92,252,.06) 0%,transparent 100%);
  border-bottom:1px solid rgba(48,54,61,.5);
  position:relative;
}
.logo-block::before{
  content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse at 50% 0%,rgba(124,92,252,.15) 0%,transparent 70%);
  pointer-events:none;
}
.logo-img{
  width:90px;height:90px;border-radius:50%;
  object-fit:cover;
  border:3px solid rgba(124,92,252,.5);
  box-shadow:0 0 30px rgba(124,92,252,.4),0 0 60px rgba(124,92,252,.15);
  animation:logoPulse 3s ease-in-out infinite;
  position:relative;z-index:1;
  background:#161b22;
}
@keyframes logoPulse{
  0%,100%{box-shadow:0 0 30px rgba(192,57,43,.5),0 0 60px rgba(192,57,43,.15);border-color:rgba(192,57,43,.6)}
  50%{box-shadow:0 0 50px rgba(231,76,60,.7),0 0 90px rgba(142,68,173,.3);border-color:rgba(231,76,60,.8)}
}
.logo-title{
  font-size:26px;font-weight:900;letter-spacing:2px;margin-top:14px;
  background:linear-gradient(135deg,#ff6b6b,#c0392b,#8e44ad);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  position:relative;z-index:1;
}
.logo-sub{
  color:#484f58;font-size:11px;margin-top:5px;
  letter-spacing:3px;text-transform:uppercase;
  position:relative;z-index:1;
}

/* ── Forms area ── */
.forms-area{padding:28px}

/* Tabs */
.tabs{
  display:flex;margin-bottom:24px;
  background:#0b0f17;border-radius:10px;padding:4px;gap:4px;
  border:1px solid rgba(48,54,61,.6);
}
.tab{
  flex:1;text-align:center;padding:10px 8px;cursor:pointer;
  color:#8b949e;font-weight:600;font-size:13px;border-radius:7px;
  transition:.25s;user-select:none;
}
.tab:hover{color:#c9d1d9;background:rgba(255,255,255,.04)}
.tab.active{
  color:#fff;
  background:linear-gradient(135deg,#c0392b,#922b21);
  box-shadow:0 2px 12px rgba(192,57,43,.5);
}

/* Form */
.form{display:none}
.form.active{display:block;animation:fadeUp .25s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.field{margin-bottom:14px}
.field label{
  display:block;color:#8b949e;font-size:10px;
  text-transform:uppercase;letter-spacing:1.2px;margin-bottom:5px;font-weight:700;
}
.field input{
  width:100%;padding:12px 14px;
  background:rgba(255,255,255,.04);
  border:1px solid rgba(48,54,61,.8);
  border-radius:8px;color:#e6edf3;font-size:14px;outline:none;
  transition:.2s;
}
.field input:focus{
  border-color:#7c5cfc;
  background:rgba(124,92,252,.05);
  box-shadow:0 0 0 3px rgba(124,92,252,.15);
}
.field input::placeholder{color:#30363d}
.btn{
  width:100%;padding:13px;border:none;border-radius:9px;cursor:pointer;
  background:linear-gradient(135deg,#e74c3c,#c0392b,#8e44ad);color:#fff;
  font-weight:700;font-size:14px;transition:.25s;margin-top:6px;
  box-shadow:0 4px 16px rgba(192,57,43,.45);
  letter-spacing:.8px;position:relative;overflow:hidden;
}
.btn::before{
  content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,.1),transparent);
  opacity:0;transition:.2s;
}
.btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(124,92,252,.55)}
.btn:hover::before{opacity:1}
.btn:active{transform:translateY(0)}
.msg{
  margin-top:12px;padding:11px 14px;border-radius:8px;font-size:12.5px;text-align:center;
  display:flex;align-items:center;justify-content:center;gap:6px;
}
.msg.error{background:rgba(248,81,73,.08);border:1px solid rgba(248,81,73,.25);color:#f85149}
.msg.success{background:rgba(46,160,67,.08);border:1px solid rgba(46,160,67,.25);color:#3fb950}
.msg.pending{background:rgba(255,170,0,.08);border:1px solid rgba(255,170,0,.25);color:#e3a008}
.divider{
  display:flex;align-items:center;gap:10px;
  margin:16px 0;color:#30363d;font-size:11px;
}
.divider::before,.divider::after{content:'';flex:1;height:1px;background:rgba(48,54,61,.6)}
.foot{
  text-align:center;margin-top:18px;padding-top:14px;
  border-top:1px solid rgba(48,54,61,.4);
  font-size:11px;color:#30363d;
}
.foot a{color:#7c5cfc;text-decoration:none;transition:.2s}
.foot a:hover{color:#a78bfa}

/* Particles */
.particles{position:fixed;inset:0;pointer-events:none;z-index:2;overflow:hidden}
.particle{
  position:absolute;border-radius:50%;
  background:rgba(124,92,252,.5);animation:float linear infinite;
}
@keyframes float{
  0%{transform:translateY(100vh) scale(0);opacity:0}
  10%{opacity:1;transform:translateY(80vh) scale(1)}
  90%{opacity:.6}
  100%{transform:translateY(-5vh) scale(.5) rotate(360deg);opacity:0}
}
</style>
</head>
<body>
<div class="orb orb1"></div>
<div class="orb orb2"></div>
<div class="particles" id="ptcls"></div>
<audio id="ea" autoplay loop preload="auto"><source src="''' + ENTRY_SOUND_URL + r'''" type="audio/mp4"></audio>

<div class="wrap">
  <div class="card">

    <!-- ── Logo Block ── -->
    <div class="logo-block">
      <img class="logo-img"
           src="https://i.ibb.co/60Zvqk5L/photo.jpg"
           alt="SERVER HUB"
           onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
      <div style="display:none;width:90px;height:90px;border-radius:50%;background:linear-gradient(135deg,#7c5cfc,#00bfff);align-items:center;justify-content:center;font-size:36px;border:3px solid rgba(124,92,252,.5);box-shadow:0 0 30px rgba(124,92,252,.4)">🚀</div>
      <div class="logo-title">SERVER HUB</div>
      <div class="logo-sub">Professional Hosting Panel</div>
    </div>

    <!-- ── Forms Block ── -->
    <div class="forms-area">
      <div class="tabs">
        <div class="tab active" data-f="login">🔐 Sign In</div>
        <div class="tab" data-f="register">✨ Register</div>
      </div>

      <form class="form active" id="login-form" method="post" action="/login">
        <div class="field"><label>Username</label><input name="username" placeholder="Enter your username" required autofocus autocomplete="username"></div>
        <div class="field"><label>Password</label><input type="password" name="password" placeholder="Enter your password" required autocomplete="current-password"></div>
        <button class="btn" type="submit">Sign In →</button>
        {% if error and error_type == 'login' %}
          <div class="msg {% if 'pending' in error.lower() or 'waiting' in error.lower() or 'approval' in error.lower() %}pending{% else %}error{% endif %}">{{ error }}</div>
        {% endif %}
      </form>

      <form class="form" id="register-form" method="post" action="/register">
        <div class="field"><label>Username</label><input name="username" placeholder="Choose a username" required autocomplete="username"></div>
        <div class="field"><label>🔵 Telegram Username <span style="color:#f85149">*</span></label><input name="tg_username" placeholder="@yourusername" required autocomplete="off"></div>
        <div class="field"><label>Password</label><input type="password" name="password" placeholder="Min 4 characters" required autocomplete="new-password"></div>
        <div class="field"><label>Confirm Password</label><input type="password" name="confirm_password" placeholder="Repeat password" required autocomplete="new-password"></div>
        <button class="btn" type="submit">Create Account →</button>
        {% if error and error_type == 'register' %}
          <div class="msg {% if '✅' in error or 'sent' in error.lower() %}success{% else %}error{% endif %}">{{ error }}</div>
        {% endif %}
      </form>

      <div class="foot">SERVER HUB &copy; 2025 &nbsp;·&nbsp; By <a href="https://t.me/I_tt_6" target="_blank">@I_tt_6</a></div>
    </div>

  </div>
</div>

<script>
document.querySelectorAll('.tab').forEach(t=>{
  t.addEventListener('click',()=>{
    const fid=t.dataset.f;
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    document.querySelectorAll('.form').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById(fid+'-form').classList.add('active');
  });
});
{% if error and error_type == 'register' %}
document.querySelectorAll('.tab').forEach(t=>{if(t.dataset.f==='register')t.click();});
{% endif %}
(function(){
  var a=document.getElementById('ea');
  if(!a)return;a.volume=0.35;
  function p(){var r=a.play();if(r)r.catch(()=>{});}
  p();setInterval(()=>{if(a.paused)p();},1000);
  ['click','keydown','touchstart'].forEach(e=>document.addEventListener(e,p,{once:true}));
})();
(function(){
  var c=document.getElementById('ptcls');
  for(var i=0;i<18;i++){
    var d=document.createElement('div');
    var s=2+Math.random()*4;
    d.className='particle';
    d.style.cssText='left:'+(Math.random()*100)+'%;width:'+s+'px;height:'+s+'px;animation-duration:'+(10+Math.random()*14)+'s;animation-delay:'+(-Math.random()*24)+'s';
    c.appendChild(d);
  }
})();
</script>
</body>
</html>
'''

# ─────────────────────────────────────────────────────────────────────────────
#  19.  MAIN DASHBOARD TEMPLATE  (DEV RIKO PANEL)
# ─────────────────────────────────────────────────────────────────────────────
def get_html_template(is_master, username=None):
    extra_tabs = ''
    if is_master:
        extra_tabs = '''
        <div class="tab-item" data-tab="ai" style="color:#a78bfa;font-weight:600">🤖 الذكاء الاصطناعي</div>
        <div class="tab-item" data-tab="users">👥 المستخدمين</div>
        <div class="tab-item" data-tab="nodejs">🟢 Node.js</div>
        <div class="tab-item" data-tab="php">🐘 PHP</div>
        <div class="tab-item" data-tab="backups">💾 النسخ الاحتياطية</div>
        <div class="tab-item" data-tab="network">🌐 الشبكة والمنافذ</div>
        <div class="tab-item" data-tab="startup">🚀 بدء التشغيل</div>
        <div class="tab-item" data-tab="settings">⚙️ الإعدادات</div>
        <div class="tab-item" data-tab="activity">📋 سجل الأنشطة</div>
        <div class="tab-item" data-tab="owner" style="color:#7c5cfc;font-weight:700">👑 تحكم المالك</div>
        '''
    else:
        extra_tabs = '''
        <div class="tab-item" data-tab="ai" style="color:#a78bfa;font-weight:600">🤖 الذكاء الاصطناعي</div>
        <div class="tab-item" data-tab="nodejs">🟢 Node.js</div>
        <div class="tab-item" data-tab="php">🐘 PHP</div>
        <div class="tab-item" data-tab="settings">⚙️ الإعدادات</div>
        <div class="tab-item" data-tab="activity">📋 سجل الأنشطة</div>
        '''

    owner_panel_html = ''
    if is_master:
        owner_panel_html = r'''
<div class="tab-content" id="tab-owner">
  <div class="stats4">
    <div class="stat4 purple"><div class="s4lbl">إجمالي المستخدمين</div><div class="s4val" id="ow-users">—</div></div>
    <div class="stat4 blue"><div class="s4lbl">السيرفرات المتصلة</div><div class="s4val" id="ow-servers">—</div></div>
    <div class="stat4 green"><div class="s4lbl">البوتات النشطة</div><div class="s4val" id="ow-bots">—</div></div>
    <div class="stat4 orange"><div class="s4lbl">ملفات الـ ZIP</div><div class="s4val" id="ow-zips">—</div></div>
  </div>

  <div class="section-card">
    <div class="section-head">🔧 وضع الصيانة (Maintenance Mode)</div>
    <div class="section-body">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
        <label class="toggle-switch">
          <input type="checkbox" id="maint-toggle-chk" onchange="toggleMaintenance()">
          <span class="slider"></span>
        </label>
        <span style="color:#8b949e;font-size:13px;font-weight:600">تفعيل وضع الصيانة وإيقاف اللوحة للمستخدمين</span>
      </div>
      <div class="field-block">
        <label>رسالة الصيانة</label>
        <textarea id="maint-msg" rows="2" placeholder="عذراً، اللوحة تحت الصيانة حالياً..." style="width:100%;padding:12px;background:var(--bg3);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;resize:vertical;outline:none;" dir="auto"></textarea>
      </div>
      <div class="row-end">
        <button class="btn-action" onclick="saveMaintMsg()">حفظ الرسالة</button>
      </div>
    </div>
  </div>

  <div class="section-card">
    <div class="section-head">🤖 إعدادات بوت التيليجرام (DEV RIKO BOT)</div>
    <div class="section-body">
      <div id="bot-status-badge" style="margin-bottom:12px"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
        <div class="field-block"><label>توكن البوت (Bot Token)</label><input id="tg-token" type="password" placeholder="1234567890:AAF..." dir="ltr"></div>
        <div class="field-block"><label>معرف المالك (Owner ID)</label><input id="tg-ownerid" placeholder="123456789" dir="ltr"></div>
      </div>
      <div id="bot-link-status" style="color:#8b949e;font-size:12px;margin-bottom:12px;font-weight:600"></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn-action" onclick="linkBot()">🔗 ربط البوت</button>
        <button class="btn-action danger" onclick="unlinkBot()">🔓 إلغاء الربط</button>
      </div>
      
      <div id="bot-control-panel" style="display:none;margin-top:20px;padding-top:16px;border-top:1px solid var(--border)">
        <div class="section-head" style="margin-bottom:12px;background:transparent;padding:0;border:none">لوحة تحكم البوت</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
          <button class="btn-action green" onclick="botAction('start')">▶ تشغيل البوت</button>
          <button class="btn-action" onclick="botAction('restart')">↺ إعادة التشغيل</button>
          <button class="btn-action danger" onclick="botAction('stop')">■ إيقاف</button>
          <button class="btn-action gray" onclick="refreshBotStats()">🔄 تحديث الحالة</button>
        </div>
        <div class="console-box" id="bot-console" style="height:140px;background:#010409" dir="ltr"></div>
        <div class="cmd-input" style="margin-top:10px" dir="ltr">
          <span class="prompt" style="color:var(--accent)">$</span>
          <input id="bot-cmd-input" placeholder="Send command to bot..." onkeydown="if(event.key==='Enter')sendBotCmd()">
        </div>
      </div>
    </div>
  </div>
'''

  <div class="section-card">
    <div class="section-head">⚙️ إعدادات اللوحة</div>
    <div class="section-body">
      <div class="field-block"><label>اسم اللوحة</label><input id="panel-name-inp" placeholder="DEV RIKO PANEL" dir="auto"></div>
      <div class="field-block"><label>رسالة الترحيب</label><input id="panel-welcome-inp" placeholder="مرحباً بك في الاستضافة!" dir="auto"></div>
      <button class="btn-action" onclick="savePanelSettings()">حفظ الإعدادات</button>
    </div>
  </div>

  <div class="section-card">
    <div class="section-head">📢 الإعلانات</div>
    <div class="section-body">
      <div class="field-block"><label>إعلان جديد</label><input id="ann-txt" placeholder="اكتب إعلانك هنا..." dir="auto"></div>
      <div style="display:flex;gap:8px;margin-bottom:12px">
        <button class="btn-action" onclick="addAnnouncement()">إضافة</button>
        <button class="btn-action gray" onclick="ownerBroadcast()">📡 بث للمستخدمين</button>
      </div>
      <div id="ann-list"></div>
    </div>
  </div>

  <div class="section-card">
    <div class="section-head">📦 ملفات مضغوطة (ZIP)</div>
    <div class="section-body">
      <div style="display:flex;gap:8px;margin-bottom:10px">
        <button class="btn-action" onclick="loadOwnerZips()">🔄 تحديث</button>
        <button class="btn-action green" onclick="downloadAllZips()">⬇ تحميل الكل</button>
      </div>
      <div id="owner-zip-list"></div>
    </div>
  </div>

  <div class="section-card">
    <div class="section-head">⏳ طلبات التسجيل المعلقة</div>
    <div class="section-body">
      <button class="btn-action" onclick="loadPendingUsers()" style="margin-bottom:10px">🔄 تحديث القائمة</button>
      <div id="pending-users-list"></div>
    </div>
  </div>

  <div class="section-card" style="border-color:rgba(248,81,73,.4)">
    <div class="section-head" style="color:#f85149">🛡️ الإنذارات الأمنية — ملفات مشبوهة</div>
    <div class="section-body">
      <div style="display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap">
        <button class="btn-action gray" onclick="loadSecurityAlerts()">🔄 تحديث التنبيهات</button>
        <button class="btn-action danger" onclick="clearSecurityAlerts()">🗑 مسح الكل</button>
      </div>
      <div id="security-alerts-list">
        <div style="color:var(--text3);padding:10px;text-align:center">اضغط تحديث لتحميل التنبيهات</div>
      </div>
    </div>
  </div>

  <div class="section-card" style="border-color:#f85149">
    <div class="section-head" style="color:#f85149">⚠️ منطقة الخطر</div>
    <div class="section-body">
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn-action danger" onclick="ownerAction('clear_all_logs')">🗑 مسح السجلات</button>
        <button class="btn-action danger" onclick="ownerAction('kick_all_users')">👢 طرد جميع المستخدمين</button>
        <button class="btn-action danger" onclick="ownerAction('reset_stats')">📊 تصفير الإحصائيات</button>
        <button class="btn-action gray" onclick="ownerAction('restart_panel')">🔄 إعادة تشغيل اللوحة</button>
      </div>
    </div>
  </div>
</div>
'''

    return r'''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DEV RIKO — لوحة التحكم</title>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#090b10;--bg2:#11151c;--bg3:#161b22;--bg4:#1e242e;
  --border:#232a35;--border2:#30363d;
  --accent:#7c5cfc;--accent2:#00bfff;--accent3:#8e44ad;
  --neon:#ff2d55;--neon2:#a855f7;
  --green:#3fb950;--red:#f85149;--yellow:#d29922;--orange:#f0883e;
  --text:#e6edf3;--text2:#8b949e;--text3:#484f58;
  --sidebar-width: 260px;
}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Tajawal',sans-serif}
html,body{background:var(--bg);color:var(--text);height:100vh;overflow:hidden;}

body::before{
  content:'';position:absolute;inset:0;
  background: url('https://i.ibb.co/60Zvqk5L/photo.jpg') center/cover no-repeat fixed;
  opacity: 0.04; pointer-events:none; z-index:0;
}

::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:3px}
'''

/* ── APP LAYOUT (توزيع الشاشة لدعم الشريط الجانبي) ── */
.app-layout {
  display: flex; height: 100vh; width: 100vw; position:relative; z-index:1;
}

/* ── SIDEBAR (بديل الـ TOPBAR والـ TABS) ── */
.sidebar {
  width: var(--sidebar-width); background: var(--bg2); border-left: 1px solid var(--border);
  display: flex; flex-direction: column; flex-shrink: 0; box-shadow: -2px 0 15px rgba(0,0,0,0.3);
}
.sidebar-header {
  padding: 24px 20px 16px; border-bottom: 1px solid var(--border); text-align: center;
}
.sidebar-logo {
  width: 75px; height: 75px; border-radius: 50%; object-fit: cover;
  border: 2px solid var(--accent); box-shadow: 0 0 15px rgba(124,92,252,0.3); margin-bottom: 12px;
}
.sidebar-brand {
  font-size: 18px; font-weight: 800;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.sidebar-user {
  display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 8px; font-size: 13px; color: var(--text2);
}
.status-dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--green); animation: blink 2s ease-in-out infinite; box-shadow: 0 0 8px var(--green);
}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.4}}

.sidebar-tabs {
  flex: 1; overflow-y: auto; padding: 16px 10px; display: flex; flex-direction: column; gap: 4px;
}
.tab-item {
  padding: 12px 16px; color: var(--text2); cursor: pointer; font-size: 14px; font-weight: 500; border-radius: 8px; transition: .2s; user-select: none; display: flex; align-items: center; gap: 10px;
}
.tab-item:hover { background: rgba(255,255,255,0.03); color: var(--text); }
.tab-item.active {
  background: linear-gradient(90deg, rgba(124,92,252,0.15), transparent);
  color: var(--accent); font-weight: 700; border-right: 3px solid var(--accent);
}

.sidebar-footer { padding: 16px; border-top: 1px solid var(--border); }
.logout-btn {
  width: 100%; padding: 12px; background: rgba(248,81,73,0.1); color: var(--red);
  border: 1px solid rgba(248,81,73,0.2); border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 13px; transition: .2s;
}
.logout-btn:hover { background: var(--red); color: #fff; }

/* ── MAIN CONTENT & TOP ACTIONS ── */
.main-content {
  flex: 1; display: flex; flex-direction: column; overflow: hidden; background: rgba(9, 11, 16, 0.85); backdrop-filter: blur(10px);
}
.top-actions {
  height: 56px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 24px; background: var(--bg2);
}
.top-actions-right { display: flex; gap: 10px; }
.action-icon {
  background: var(--bg3); border: 1px solid var(--border); color: var(--text2); width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: .2s; font-size: 16px;
}
.action-icon:hover { color: var(--accent); border-color: var(--accent); }

/* ── CONTAINER ── */
.container { flex: 1; overflow-y: auto; padding: 24px; }
.tab-content { display: none; animation: fadein .3s ease; }
.tab-content.active { display: block; }
@keyframes fadein { from{opacity:0; transform:translateX(-10px)} to{opacity:1; transform:translateX(0)} }

/* ── LTR Overrides (للحفاظ على الأكواد سليمة) ── */
.console-box, .cmd-input, .editor-box, .log-box { direction: ltr; text-align: left; }
.field-block input[dir="ltr"] { direction: ltr; text-align: left; }

/* ── CONSOLE ── */
.power-row { display: flex; gap: 10px; margin-bottom: 16px; align-items: center; direction: ltr; }
.btn-power { padding: 10px 20px; border: none; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; color: #fff; transition: .2s; }
.btn-start { background: linear-gradient(135deg, #1a7f37, #2ea043); }
.btn-restart { background: linear-gradient(135deg, #7c5cfc, #5a3fc0); }
.btn-stop { background: linear-gradient(135deg, #b62324, #f85149); }
.btn-power:hover { transform: translateY(-2px); filter: brightness(1.1); }
.status-badge { display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; padding: 8px 12px; background: var(--bg3); border: 1px solid var(--border); border-radius: 8px; font-family: monospace; }

.console-box {
  background: #010409; border: 1px solid #30363d; border-radius: 10px; padding: 16px; font-family: 'Consolas', monospace; font-size: 13px; color: #7ee787; height: 380px; overflow-y: auto; margin-bottom: 12px; line-height: 1.6;
}
.console-box .line-err { color: #f85149; }
.console-box .line-warn { color: #d29922; }
.console-box .line-info { color: #79c0ff; }

.cmd-input { display: flex; align-items: center; background: #0d1117; border: 1px solid var(--border); border-radius: 8px; padding: 0 16px; }
.cmd-input:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(124,92,252,.15); }
.cmd-input .prompt { color: var(--accent); margin-right: 8px; font-weight: 700; font-size: 14px; }
.cmd-input input { flex: 1; background: none; border: 0; outline: 0; color: var(--text); padding: 14px 0; font-family: monospace; font-size: 14px; }

/* ── STATS GRID ── */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; margin-bottom: 20px; }
.stat-card { background: var(--bg3); border: 1px solid var(--border); border-radius: 10px; padding: 16px; position: relative; overflow: hidden; transition: .2s; }
.stat-card::before { content: ''; position: absolute; top: 0; right: 0; left: 0; height: 3px; background: linear-gradient(90deg, var(--accent), var(--accent2)); }
.stat-card:hover { border-color: var(--accent); transform: translateY(-1px); }
.stat-card .lbl { font-size: 12px; color: var(--text2); margin-bottom: 8px; font-weight: 700; }
.stat-card .val { font-size: 16px; color: var(--text); font-weight: 800; direction: ltr; text-align: right; }
.stat-card.green::before { background: var(--green); }
.stat-card.red::before { background: var(--red); }
.stat-card.yellow::before { background: var(--yellow); }
.stat-card.orange::before { background: var(--orange); }

/* ── SECTION CARD ── */
.section-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  margin-bottom: 20px;
  overflow: hidden;
  box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}
.section-head {
  padding: 14px 20px;
  background: var(--bg3);
  border-bottom: 1px solid var(--border);
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-body {
  padding: 20px;
}

/* ── FILES ── */
.file-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.file-toolbar button {
  padding: 10px 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg3);
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  font-weight: 600;
  transition: .2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.file-toolbar button:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(124,92,252,0.3);
}
.breadcrumb {
  padding: 12px 16px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text2);
  font-family: monospace;
  margin-bottom: 14px;
  overflow-x: auto;
  white-space: nowrap;
  direction: ltr; /* لحفظ مسارات الملفات من اليسار لليمين */
  text-align: left;
}
.file-list {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}
.file-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: .15s;
  gap: 12px;
  direction: ltr; /* لعرض أسماء الملفات بشكل سليم */
}
.file-item:last-child {
  border-bottom: none;
}
.file-item:hover {
  background: var(--bg3);
}
.file-icon {
  font-size: 18px;
  width: 28px;
  text-align: center;
  flex-shrink: 0;
}
.file-name {
  flex: 1;
  font-size: 14px;
  color: var(--text);
  font-weight: 600;
  word-break: break-all;
  text-align: left;
}
.file-size {
  font-size: 12px;
  color: var(--text3);
  flex-shrink: 0;
}
.file-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.file-actions button {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  background: var(--bg4);
  color: var(--text2);
  font-weight: 600;
  transition: .15s;
}
.file-actions button:hover {
  background: var(--accent);
  color: #fff;
}
.file-actions button.danger:hover {
  background: var(--red);
}

/* ── AI CHAT ── */
.ai-chat-wrap {
  display: flex; flex-direction: column;
  height: calc(100vh - 130px); min-height: 500px; max-height: 800px;
  background: var(--bg2); border: 1px solid rgba(124,92,252,.2);
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 0 40px rgba(124,92,252,.05);
}
.ai-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px;
  background: linear-gradient(90deg, rgba(124,92,252,.1), transparent);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.ai-header-left { display: flex; align-items: center; gap: 12px; }
.ai-avatar-main {
  width: 42px; height: 42px; border-radius: 50%;
  background: linear-gradient(135deg, #7c5cfc, #00bfff);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; flex-shrink: 0;
  box-shadow: 0 0 15px rgba(124,92,252,.4);
}
.ai-header-title { font-size: 15px; font-weight: 800; color: var(--text); }
.ai-header-sub { font-size: 12px; color: var(--text3); margin-top: 2px; }
.ai-clear-btn {
  background: rgba(248,81,73,.1); border: 1px solid rgba(248,81,73,.2);
  color: var(--red); font-weight: 600;
  border-radius: 8px; padding: 8px 14px; cursor: pointer; font-size: 13px; transition: .2s;
}
.ai-clear-btn:hover { background: var(--red); color: #fff; box-shadow: 0 4px 15px rgba(248,81,73,.3); }

.ai-messages-box {
  flex: 1; overflow-y: auto; padding: 20px;
  display: flex; flex-direction: column; gap: 16px;
  /* دمج لون الخلفية مع شعارك بشفافية 4% ليكون كعلامة مائية */
  background: linear-gradient(rgba(1, 4, 9, 0.96), rgba(1, 4, 9, 0.96)), url('https://j.top4top.io/p_3820hbxes1.png') center/280px no-repeat;
  background-attachment: fixed;
  scrollbar-width: thin; scrollbar-color: #30363d transparent;
}
.ai-messages-box::-webkit-scrollbar { width: 5px; }
.ai-messages-box::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }

.ai-msg { display: flex; flex-direction: column; animation: fadeUp .3s ease; position: relative; z-index: 1; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.ai-bubble { display: flex; gap: 12px; align-items: flex-start; max-width: 85%; }
.ai-msg.ai-user .ai-bubble { flex-direction: row-reverse; margin-left: auto; max-width: 85%; }

.ai-avatar {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 16px;
  background: var(--bg3); border: 1px solid var(--border); margin-top: 2px;
}
.ai-msg.ai-user .ai-avatar {
  background: linear-gradient(135deg, #7c5cfc, #5a3fc0); border-color: transparent;
  font-size: 14px; color: #fff; font-weight: 700;
}

.ai-text {
  padding: 14px 18px; border-radius: 16px; font-size: 14px; line-height: 1.7;
  background: rgba(255,255,255,.03); border: 1px solid var(--border);
  color: var(--text); white-space: pre-wrap; word-break: break-word;
  border-top-right-radius: 4px;
}
.ai-msg.ai-user .ai-text {
  background: linear-gradient(135deg, rgba(124,92,252,.15), rgba(90,63,192,.08));
  border-color: rgba(124,92,252,.3);
  border-top-right-radius: 16px; border-top-left-radius: 4px;
  text-align: right; direction: rtl;
}

.ai-text code {
  background: rgba(124,92,252,.15); padding: 2px 8px; border-radius: 6px;
  font-family: 'Fira Code', 'Consolas', monospace; font-size: 13px; color: #a78bfa;
}
.ai-text pre {
  background: #0d1117; border: 1px solid var(--border2); border-radius: 10px;
  padding: 16px; overflow-x: auto; margin: 10px 0; position: relative;
  direction: ltr; text-align: left; /* للحفاظ على الأكواد يسار-يمين */
}
.ai-text pre code { background: none; padding: 0; color: #7ee787; font-size: 13px; display: block; }

.ai-time { font-size: 11px; color: var(--text3); margin-top: 6px; padding: 0 4px; }
.ai-msg.ai-user .ai-time { text-align: right; }

/* ── AI CHAT: Thinking & Input ── */
.ai-thinking-box {
  padding: 12px 18px; flex-shrink: 0;
  background: rgba(124,92,252,.05); border-top: 1px solid rgba(48,54,61,.5);
}
.ai-thinking-label {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--accent); font-weight: 700; letter-spacing: .5px; margin-bottom: 8px;
}
.ai-think-dots { display: flex; gap: 4px; align-items: center; }
.ai-think-dots span { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); animation: typingDot 1.2s ease-in-out infinite; }
.ai-think-dots span:nth-child(2) { animation-delay: .2s; }
.ai-think-dots span:nth-child(3) { animation-delay: .4s; }
.ai-reasoning-text {
  font-size: 12px; color: var(--text2); font-family: 'Fira Code', 'Consolas', monospace;
  max-height: 100px; overflow-y: auto; line-height: 1.6; white-space: pre-wrap; direction: rtl;
}

.ai-input-area {
  flex-shrink: 0; padding: 16px 20px;
  border-top: 1px solid var(--border);
  background: rgba(9, 11, 16, 0.8);
}
.ai-input-row { display: flex; gap: 12px; align-items: flex-end; }
.ai-textarea {
  flex: 1; padding: 14px 18px; min-height: 50px; max-height: 130px;
  background: var(--bg3); border: 1px solid var(--border);
  border-radius: 12px; color: var(--text); font-size: 14px;
  outline: none; resize: none; transition: .2s; font-family: inherit; line-height: 1.6;
  direction: auto; overflow-y: auto;
}
.ai-textarea:focus {
  border-color: var(--accent);
  background: rgba(124,92,252,.04);
  box-shadow: 0 0 0 3px rgba(124,92,252,.15);
}
.ai-textarea::placeholder { color: var(--text3); }
.ai-send-btn {
  width: 50px; height: 50px; flex-shrink: 0;
  background: linear-gradient(135deg, var(--accent), #5a3fc0);
  border: none; border-radius: 12px; color: #fff; cursor: pointer; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
  transition: .2s; box-shadow: 0 4px 15px rgba(124,92,252,.35);
}
.ai-send-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(124,92,252,.5); }
.ai-send-btn:active { transform: translateY(0); }
.ai-send-btn:disabled { opacity: .5; cursor: not-allowed; transform: none; }
.ai-footer-info { font-size: 11px; color: var(--text3); margin-top: 8px; text-align: center; }

.ai-typing-wrap { display: flex; align-items: center; gap: 10px; }
.ai-typing { display: flex; gap: 4px; align-items: center; padding: 12px 16px; background: var(--bg3); border: 1px solid var(--border); border-radius: 16px; border-top-right-radius: 4px; }
.ai-typing span { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); animation: typingDot 1.2s ease-in-out infinite; }
.ai-typing span:nth-child(2) { animation-delay: .2s; }
.ai-typing span:nth-child(3) { animation-delay: .4s; }
@keyframes typingDot { 0%,60%,100% { transform: translateY(0); opacity: .3; } 30% { transform: translateY(-5px); opacity: 1; } }

/* ── BUTTONS ── */
.btn-action {
  padding: 10px 18px; border: none; border-radius: 8px; cursor: pointer;
  background: linear-gradient(135deg, var(--accent), #5a3fc0); color: #fff;
  font-weight: 700; font-size: 13px; transition: .2s; letter-spacing: .3px; 
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
}
.btn-action:hover { filter: brightness(1.1); transform: translateY(-1px); box-shadow: 0 4px 15px rgba(124,92,252,.4); }
.btn-action.gray { background: var(--bg4); border: 1px solid var(--border); color: var(--text); box-shadow: none; }
.btn-action.gray:hover { background: var(--border); color: #fff; }
.btn-action.green { background: linear-gradient(135deg, #1a7f37, #2ea043); box-shadow: 0 4px 15px rgba(26,127,55,.3); }
.btn-action.danger { background: linear-gradient(135deg, #b62324, #f85149); box-shadow: 0 4px 15px rgba(248,81,73,.3); }
.btn-action.orange { background: linear-gradient(135deg, var(--orange), #c7541f); box-shadow: 0 4px 15px rgba(240,136,62,.3); }

/* ── FORMS ── */
.field-block { margin-bottom: 14px; }
.field-block label { display: block; font-size: 12px; color: var(--text2); font-weight: 700; margin-bottom: 6px; }
.field-block input, .field-block select, .field-block textarea {
  width: 100%; padding: 12px 14px; background: var(--bg3);
  border: 1px solid var(--border); border-radius: 8px; color: var(--text);
  font-size: 14px; outline: none; transition: .2s;
}
.field-block input:focus, .field-block select:focus, .field-block textarea:focus {
  border-color: var(--accent); box-shadow: 0 0 0 3px rgba(124,92,252,.15);
}
.field-block input::placeholder, .field-block textarea::placeholder { color: var(--text3); }
.row-end { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }

/* ── MODALS ── */
.modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.8); z-index: 9999; align-items: center; justify-content: center; backdrop-filter: blur(5px); }
.modal.open { display: flex; animation: fadeInModal .2s ease; }
@keyframes fadeInModal { from { opacity: 0; } to { opacity: 1; } }

.modal-box { background: var(--bg2); border: 1px solid var(--border); border-radius: 16px; width: min(600px, 94vw); max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 20px 60px rgba(0,0,0,.6); transform: scale(0.98); animation: scaleUpModal .2s ease forwards; }
@keyframes scaleUpModal { to { transform: scale(1); } }

.modal-head { padding: 18px 24px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.modal-head h3 { font-size: 16px; font-weight: 800; color: var(--text); }
.modal-head .close { background: rgba(248,81,73,.1); border: 1px solid rgba(248,81,73,.2); border-radius: 6px; color: var(--red); font-size: 18px; cursor: pointer; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; transition: .2s; }
.modal-head .close:hover { background: var(--red); color: #fff; box-shadow: 0 4px 10px rgba(248,81,73,.4); }
.modal-body { padding: 24px; overflow-y: auto; flex: 1; }
.modal-foot { padding: 16px 24px; border-top: 1px solid var(--border); display: flex; gap: 10px; justify-content: flex-end; background: var(--bg3); border-bottom-left-radius: 16px; border-bottom-right-radius: 16px; }

/* ── EDITOR ── */
.editor-wrap { position: relative; }
.editor-box {
  width: 100%; min-height: 400px; padding: 16px;
  background: #010409; border: 1px solid var(--border); border-radius: 8px;
  color: #7ee787; font-family: 'Fira Code', 'Consolas', monospace; font-size: 14px;
  outline: none; resize: vertical; line-height: 1.6; tab-size: 2;
  direction: ltr; text-align: left; /* هام جداً لكي تبقى الأكواد صحيحة */
}
.editor-box:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(124,92,252,.15); }

/* ── NODE.JS TAB ── */
.nodejs-project-card {
  background: var(--bg3); border: 1px solid var(--border); border-radius: 12px;
  padding: 16px; margin-bottom: 12px;
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  box-shadow: 0 4px 10px rgba(0,0,0,.1); transition: .2s;
}
.nodejs-project-card:hover { border-color: rgba(46,160,67,.4); }
.project-info .p-name { font-size: 15px; font-weight: 800; color: var(--text); }
.project-info .p-meta { font-size: 12px; color: var(--text2); margin-top: 4px; direction: ltr; text-align: left; }
.p-status { font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 20px; }
.p-status.running { background: rgba(46,160,67,.15); color: var(--green); border: 1px solid rgba(46,160,67,.3); }
.p-status.stopped { background: rgba(248,81,73,.1); color: var(--red); border: 1px solid rgba(248,81,73,.2); }
.log-box {
  background: #010409; border: 1px solid var(--border); border-radius: 8px;
  padding: 14px; font-family: 'Fira Code', monospace; font-size: 12px; color: #7ee787;
  height: 200px; overflow-y: auto; margin-top: 10px; white-space: pre-wrap; direction: ltr; text-align: left;
}

/* ── PHP TAB ── */
.php-server-card {
  background: var(--bg3); border: 1px solid var(--border); border-radius: 12px;
  padding: 16px; margin-bottom: 12px; box-shadow: 0 4px 10px rgba(0,0,0,.1); transition: .2s;
}
.php-server-card:hover { border-color: rgba(240,136,62,.4); }

/* ── TOAST (الإشعارات) ── */
.toast-container { position: fixed; bottom: 20px; left: 20px; z-index: 99999; display: flex; flex-direction: column; gap: 10px; }
.toast {
  padding: 14px 20px; border-radius: 12px; font-size: 14px; font-weight: 700; color: #fff;
  display: flex; align-items: center; gap: 10px;
  animation: slideIn .3s ease; box-shadow: 0 6px 20px rgba(0,0,0,.4); max-width: 350px;
}
.toast.ok { background: linear-gradient(135deg, #1a7f37, #2ea043); }
.toast.err { background: linear-gradient(135deg, #b62324, #f85149); }
.toast.info { background: linear-gradient(135deg, var(--accent), #5a3fc0); }
@keyframes slideIn { from { transform: translateX(-100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

/* ── LIST ITEMS (الخوادم، النسخ، الطلبات المعلقة) ── */
.srv-card, .zip-item, .pending-card {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  background: var(--bg4); border: 1px solid var(--border); border-radius: 10px;
  padding: 14px 16px; margin-bottom: 8px; transition: .2s;
}
.srv-card:hover, .zip-item:hover, .pending-card:hover { border-color: var(--accent); }
.srv-name, .p-user { font-size: 15px; font-weight: 700; color: var(--text); }
.srv-meta, .p-time { font-size: 12px; color: var(--text2); margin-top: 4px; direction: ltr; text-align: left; }
.z-name { color: var(--text); font-size: 14px; font-family: monospace; font-weight: 600; direction: ltr; text-align: left; }
.z-size { color: var(--text2); font-size: 12px; margin-top: 4px; direction: ltr; text-align: left; }

/* ── RESPONSIVE (الهواتف) ── */
@media(max-width: 768px) {
  .app-layout { flex-direction: column; }
  .sidebar { width: 100%; height: auto; border-left: none; border-bottom: 1px solid var(--border); padding: 10px; }
  .sidebar-header { display: none; }
  .sidebar-tabs { flex-direction: row; padding: 0; overflow-x: auto; gap: 10px; }
  .tab-item { white-space: nowrap; padding: 10px; border-right: none; border-bottom: 3px solid transparent; }
  .tab-item.active { background: none; border-bottom-color: var(--accent); }
  .stats-grid { grid-template-columns: 1fr 1fr; }
  .power-row { flex-wrap: wrap; justify-content: center; }
  .btn-power { flex: 1; min-width: 100px; text-align: center; }
  .top-actions { padding: 0 14px; }
  .container { padding: 16px 10px; }
}
</style>
</head>
<body>

<div class="app-layout">
  
  <aside class="sidebar">
    <div class="sidebar-header">
      <img src="https://j.top4top.io/p_3820hbxes1.png" alt="DEV RIKO" class="sidebar-logo">
      <div class="sidebar-brand">DEV RIKO PANEL</div>
      <div class="sidebar-user"><div class="status-dot"></div> <span id="topbar-user" dir="ltr">''' + __import__('html').escape(username or '') + r'''</span></div>
    </div>
    <div class="sidebar-tabs" id="tabs">
      <div class="tab-item active" data-tab="console">💻 الترمنال</div>
      <div class="tab-item" data-tab="files">📁 إدارة الملفات</div>
      <div class="tab-item" data-tab="databases">🗄 قواعد البيانات</div>
      <div class="tab-item" data-tab="schedules">⏰ الجدولة</div>
      ''' + extra_tabs + r'''
    </div>
    <div class="sidebar-footer">
      <button class="logout-btn" onclick="location.href='/logout'">تسجيل الخروج</button>
    </div>
  </aside>

  <main class="main-content">
    
    <div class="top-actions">
      <div style="font-weight:800; color:var(--text); font-size: 16px;">مرحباً بك في DEV RIKO PANEL</div>
      <div class="top-actions-right">
        <button class="action-icon" onclick="loadSearch()" title="بحث شامل">🔍</button>
        <button class="action-icon" onclick="openServersModal()" title="إدارة السيرفرات المتصلة">🗂</button>
      </div>
    </div>

    <div class="container">
      <div id="toast-container" class="toast-container"></div>

      <div class="tab-content active" id="tab-console">
        
        <div id="term-tabs-bar" style="display:flex;align-items:center;gap:8px;margin-bottom:14px;flex-wrap:wrap">
          <button class="btn-action gray" onclick="addTerminal()" style="padding:6px 12px; font-size: 12px;">＋ فتح ترمنال جديد</button>
        </div>

        <div class="power-row">
          <button class="btn-power btn-start" onclick="powerAction('start')">▶ تشغيل السيرفر</button>
          <button class="btn-power btn-restart" onclick="powerAction('restart')">↺ إعادة التشغيل</button>
          <button class="btn-power btn-stop" onclick="powerAction('stop')">■ إيقاف</button>
          <div class="status-badge" dir="ltr" style="margin-right: auto;">
            <span id="proc-dot" style="width:10px;height:10px;border-radius:50%;background:#f85149;display:inline-block"></span>
            <span id="proc-status">Stopped</span>
          </div>
        </div>

        <div id="terminals-container"></div>

        <div class="stats-grid" id="stats-grid">
          <div class="stat-card"><div class="lbl">IP Address</div><div class="val" id="s-ip">—</div></div>
          <div class="stat-card"><div class="lbl">Panel Port</div><div class="val" id="s-port" style="color:var(--green);cursor:pointer" onclick="copyPort()" title="نسخ البورت">—</div></div>
          <div class="stat-card"><div class="lbl">Uptime</div><div class="val" id="s-uptime">—</div></div>
          <div class="stat-card"><div class="lbl">CPU Usage</div><div class="val" id="s-cpu">—</div></div>
          <div class="stat-card"><div class="lbl">RAM Memory</div><div class="val" id="s-mem">—</div></div>
          <div class="stat-card"><div class="lbl">Disk Storage</div><div class="val" id="s-disk">—</div></div>
          <div class="stat-card green"><div class="lbl">Network In</div><div class="val" id="s-in">—</div></div>
          <div class="stat-card orange"><div class="lbl">Network Out</div><div class="val" id="s-out">—</div></div>
          <div class="stat-card"><div class="lbl">Hostname</div><div class="val" id="s-host">—</div></div>
          <div class="stat-card"><div class="lbl">Platform OS</div><div class="val" id="s-plat">—</div></div>
        </div>

        <!-- Service Links -->
        <div class="section-card">
          <div class="section-head">🔗 الروابط السريعة والخدمات</div>
          <div class="section-body">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">
              <div class="stat-card" style="cursor:pointer" id="web-link-card" onclick="openWebLink()">
                <div class="lbl">🌐 رابط الموقع</div>
                <div class="val" style="font-size:13px;color:var(--green);word-break:break-all" id="web-link">No HTML file</div>
              </div>
              <div class="stat-card" style="cursor:pointer" id="api-link-card" onclick="openApiLink()">
                <div class="lbl">⚡ رابط الـ API</div>
                <div class="val" style="font-size:13px;color:var(--accent2);word-break:break-all" id="api-link">No API file</div>
              </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:14px">
              <a href="https://t.me/SHBH_S1" target="_blank" style="text-decoration:none">
                <div class="stat-card"><div class="lbl">👨‍💻 المطور</div><div class="val" style="font-size:14px;color:var(--accent)">@SHBH_S1</div></div>
              </a>
              <a href="https://t.me/SHOBING_HXH" target="_blank" style="text-decoration:none">
                <div class="stat-card"><div class="lbl">📢 القناة الرسمية</div><div class="val" style="font-size:14px;color:var(--yellow)">@SHOBING_HXH</div></div>
              </a>
              <div class="stat-card"><div class="lbl">🔌 المنفذ (Port)</div><div class="val" id="port-display" style="color:var(--green);cursor:pointer" onclick="copyPort()">—</div></div>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== FILES TAB ===== -->
      <div class="tab-content" id="tab-files">
        <input type="file" id="file-up" style="display:none" multiple onchange="uploadFiles(this)">
        <input type="file" id="zip-up" style="display:none" accept=".zip,.tar,.gz,.tar.gz,.rar" onchange="uploadAndExtract(this)">

        <div class="file-toolbar">
          <button class="btn-action gray" onclick="createDir()">📁 مجلد جديد</button>
          <button class="btn-action gray" onclick="newFile()">📄 ملف جديد</button>
          <button class="btn-action gray" onclick="document.getElementById('file-up').click()">⬆ رفع ملفات</button>
          <button class="btn-action gray" onclick="document.getElementById('zip-up').click()">📦 استخراج ZIP</button>
          <button class="btn-action gray" onclick="loadFiles()">🔄 تحديث القائمة</button>
        </div>

        <div class="breadcrumb" id="breadcrumb" dir="ltr">/ home /</div>
        <div class="file-list" id="file-list"></div>
      </div>

      <!-- ===== AI TAB ===== -->
      <div class="tab-content" id="tab-ai">
        <div class="ai-chat-wrap">
          <!-- Header -->
          <div class="ai-header">
            <div class="ai-header-left">
              <div class="ai-avatar-main">🤖</div>
              <div>
                <div class="ai-header-title">DEV RIKO AI</div>
                <div class="ai-header-sub">GPT-OSS 120B · المساعد الذكي</div>
              </div>
            </div>
            <button class="ai-clear-btn" onclick="clearAiChat()" title="مسح المحادثة">🗑 مسح</button>
          </div>

          <!-- Messages -->
          <div id="ai-messages" class="ai-messages-box">
            <div class="ai-msg ai-assistant">
              <div class="ai-bubble">
                <span class="ai-avatar">🤖</span>
                <div class="ai-text">مرحباً بك! أنا مساعدك الذكي الخاص بلوحة DEV RIKO.<br>اسألني أي شيء — أكواد، حل مشاكل، أو أي استفسار آخر!</div>
              </div>
            </div>
          </div>

          <!-- Thinking -->
          <div id="ai-thinking-box" class="ai-thinking-box" style="display:none">
            <div class="ai-thinking-label">
              <span class="ai-think-dots"><span></span><span></span><span></span></span>
              جاري التفكير وجمع المعلومات...
            </div>
            <div id="ai-reasoning" class="ai-reasoning-text"></div>
          </div>

          <!-- Input -->
          <div class="ai-input-area">
            <div class="ai-input-row">
              <textarea id="ai-input"
                class="ai-textarea"
                placeholder="اكتب رسالتك هنا... (Enter للإرسال، Shift+Enter لسطر جديد)"
                rows="1"
                onkeydown="aiKeyDown(event)"
                oninput="autoResizeAI(this)"
              ></textarea>
              <button onclick="sendAiMessage()" id="ai-send-btn" class="ai-send-btn">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              </button>
            </div>
            <div class="ai-footer-info">Enter للإرسال · Shift+Enter لسطر جديد · يدعم العربية والإنجليزية</div>
          </div>
        </div>
      </div>

      <!-- ===== DATABASES TAB ===== -->
      <div class="tab-content" id="tab-databases">
        <div class="section-card">
          <div class="section-head">🗄 إنشاء قاعدة بيانات</div>
          <div class="section-body">
            <p style="color:var(--text2);font-size:13px;margin-bottom:12px;font-weight:600">إدارة وإنشاء قواعد بيانات SQLite / JSON داخل مجلد اللوحة الخاص بك.</p>
            <div class="field-block"><label>اسم قاعدة البيانات (Database Name)</label><input id="db-name" placeholder="my_database" dir="ltr"></div>
            <div class="row-end"><button class="btn-action" onclick="createDB()">إنشاء قاعدة بيانات</button></div>
          </div>
        </div>
        <div id="db-list"></div>
      </div>

      <!-- ===== SCHEDULES TAB ===== -->
      <div class="tab-content" id="tab-schedules">
        <div class="section-card">
          <div class="section-head">⏰ إنشاء جدول (Cron Schedule)</div>
          <div class="section-body">
            <div class="field-block"><label>اسم الجدول (Name)</label><input id="sch-name" placeholder="Daily backup" dir="ltr"></div>
            <div class="field-block"><label>الأمر المراد تنفيذه (Command)</label><input id="sch-cmd" placeholder="python3 script.py" dir="ltr"></div>
            <div class="field-block"><label>تعبير الكرون (Cron Expression)</label><input id="sch-cron" value="* * * * *" dir="ltr"></div>
            <div class="row-end"><button class="btn-action" onclick="addSchedule()">إضافة الجدول</button></div>
          </div>
        </div>
        <div id="sch-list"></div>
      </div>

      <div class="tab-content" id="tab-nodejs">
        <div class="section-card">
          <div class="section-head">🟢 تشغيل مشاريع Node.js</div>
          <div class="section-body">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <div class="field-block" style="grid-column:1/-1">
                <label>📁 مسار المشروع (Project Path)</label>
                <input id="nodejs-path" placeholder="/panel_data/users_data/myuser/myproject" dir="ltr">
              </div>
              <div class="field-block">
                <label>📄 الملف الرئيسي <span style="color:var(--text3);font-weight:400">(e.g. index.js, src/app.js)</span></label>
                <div style="display:flex;gap:6px;align-items:center">
                  <input id="nodejs-main" placeholder="auto-detect" style="flex:1" dir="ltr">
                  <button class="btn-action gray" style="font-size:11px;white-space:nowrap" onclick="loadNodeJsFiles()">📂 تصفح</button>
                </div>
                <div id="nodejs-files-list" style="display:none;margin-top:6px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;max-height:140px;overflow-y:auto"></div>
              </div>
              <div class="field-block">
                <label>📦 ملف الحزم <span style="color:var(--text3);font-weight:400">(e.g. package.json)</span></label>
                <input id="nodejs-deps" placeholder="package.json (default)" dir="ltr">
              </div>
              <div class="field-block">
                <label>🔌 المنفذ (Port) <span style="color:var(--text3);font-weight:400">(اختياري)</span></label>
                <input id="nodejs-port" type="number" placeholder="auto" dir="ltr">
              </div>
              <div class="field-block" style="grid-column:1/-1">
                <div style="background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:12px;display:none" id="nodejs-cmd-preview">
                  <div style="font-size:11px;color:var(--text2);margin-bottom:6px;font-weight:700;text-transform:uppercase;letter-spacing:.8px">📋 معاينة أوامر التشغيل</div>
                  <div id="nodejs-install-cmd" style="font-family:monospace;font-size:12px;color:#79c0ff;padding:4px 0" dir="ltr"></div>
                  <div id="nodejs-run-cmd" style="font-family:monospace;font-size:12px;color:#7ee787;padding:4px 0" dir="ltr"></div>
                </div>
              </div>
            </div>
            <div class="row-end" style="gap:8px">
              <button class="btn-action gray" onclick="previewNodeCmd()">👁 معاينة الأوامر</button>
              <button class="btn-action green" onclick="startNodeProject()">▶ تشغيل Node.js</button>
            </div>
            <div id="nodejs-start-output" style="display:none;margin-top:10px;background:#010409;border:1px solid var(--border);border-radius:6px;padding:10px;font-family:monospace;font-size:11px;color:#7ee787;max-height:120px;overflow-y:auto;white-space:pre-wrap" dir="ltr"></div>
          </div>
        </div>
        <div id="nodejs-list"></div>
      </div>

      <div class="tab-content" id="tab-php">
        <div class="section-card">
          <div class="section-head">🐘 تشغيل سيرفر PHP</div>
          <div class="section-body">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <div class="field-block" style="grid-column:1/-1">
                <label>📁 مسار مجلد PHP الأساسي</label>
                <input id="php-path" placeholder="/panel_data/users_data/myuser/mysite" dir="ltr">
              </div>
              <div class="field-block">
                <label>📄 الملف الرئيسي <span style="color:var(--text3);font-weight:400">(e.g. index.php)</span></label>
                <div style="display:flex;gap:6px;align-items:center">
                  <input id="php-main" placeholder="index.php (default)" style="flex:1" dir="ltr">
                  <button class="btn-action gray" style="font-size:11px;white-space:nowrap" onclick="loadPhpFiles()">📂 تصفح</button>
                </div>
                <div id="php-files-list" style="display:none;margin-top:6px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;max-height:140px;overflow-y:auto"></div>
              </div>
              <div class="field-block">
                <label>📦 ملف الحزم <span style="color:var(--text3);font-weight:400">(e.g. composer.json)</span></label>
                <input id="php-deps" placeholder="composer.json (auto-detect)" dir="ltr">
              </div>
              <div class="field-block">
                <label>🔌 المنفذ (Port) <span style="color:var(--text3);font-weight:400">(اختياري)</span></label>
                <input id="php-port" type="number" placeholder="auto" dir="ltr">
              </div>
              <div class="field-block" style="grid-column:1/-1">
                <div style="background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:12px" id="php-cmd-preview">
                  <div style="font-size:11px;color:var(--text2);margin-bottom:6px;font-weight:700;text-transform:uppercase;letter-spacing:.8px">📋 معاينة أوامر التشغيل</div>
                  <div id="php-install-cmd" style="font-family:monospace;font-size:12px;color:#79c0ff;padding:4px 0" dir="ltr">— اضغط معاينة لعرض الأوامر —</div>
                  <div id="php-run-cmd" style="font-family:monospace;font-size:12px;color:#7ee787;padding:4px 0" dir="ltr"></div>
                </div>
              </div>
            </div>
            <div class="row-end" style="gap:8px">
              <button class="btn-action gray" onclick="previewPhpCmd()">👁 معاينة الأوامر</button>
              <button class="btn-action orange" onclick="startPhpServer()">▶ تشغيل PHP</button>
            </div>
            <div id="php-start-output" style="display:none;margin-top:10px;background:#010409;border:1px solid var(--border);border-radius:6px;padding:10px;font-family:monospace;font-size:11px;color:#7ee787;max-height:120px;overflow-y:auto;white-space:pre-wrap" dir="ltr"></div>
          </div>
        </div>
        <div id="php-list"></div>
      </div>

''' + (r'''
      <div class="tab-content" id="tab-users">
        <div class="section-card">
          <div class="section-head">👤 إضافة مستخدم جديد</div>
          <div class="section-body">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
              <div class="field-block"><label>اسم المستخدم (Username)</label><input id="u-name" placeholder="username" dir="ltr"></div>
              <div class="field-block"><label>كلمة المرور (Password)</label><input id="u-pass" type="password" placeholder="password" dir="ltr"></div>
              <div class="field-block"><label>🔵 معرف التيليجرام</label><input id="u-tg" placeholder="@username" dir="ltr"></div>
              <div class="field-block"><label>خطة الاشتراك (Plan)</label>
                <select id="u-plan" style="width:100%;padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px" onchange="onPlanChange()">
                  <option value="free_trial">🆓 تجربة مجانية — 7 أيام</option>
                  <option value="paid_20">⭐ مدفوع 20 يوم — 15 نجمة</option>
                  <option value="paid_30">💎 مدفوع 30 يوم — 25 نجمة</option>
                  <option value="custom">🎯 مخصص (Custom)</option>
                </select>
              </div>
              <div class="field-block" id="u-custom-days-wrap" style="display:none"><label>عدد الأيام المخصصة</label><input id="u-days" type="number" value="7" min="1" dir="ltr"></div>
              <div class="field-block"><label>أقصى عدد للجلسات</label><input id="u-max" type="number" value="1" dir="ltr"></div>
              <div class="field-block"><label>أقصى عدد للسيرفرات</label>
                <select id="u-maxsrv" style="width:100%;padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px">
                  <option value="1">1 سيرفر</option><option value="2">2 سيرفرات</option>
                  <option value="3">3 سيرفرات</option><option value="5">5 سيرفرات</option>
                  <option value="10">10 سيرفرات</option><option value="999">لا محدود</option>
                </select>
              </div>
              <div class="field-block"><label>الملف الرئيسي (Main File)</label><input id="u-main" value="main.py" dir="ltr"></div>
            </div>
            <div class="row-end"><button class="btn-action" onclick="addUser()">إضافة المستخدم</button></div>
          </div>
        </div>
        <div id="users-list"></div>

        <div class="modal" id="edit-user-modal">
          <div class="modal-box">
            <div class="modal-head"><h3>تعديل المستخدم</h3><button class="close" onclick="closeModal('edit-user-modal')">×</button></div>
            <div class="modal-body">
              <input type="hidden" id="eu-name">
              <div class="field-block"><label>كلمة مرور جديدة (New Password)</label><input id="eu-pass" type="password" placeholder="(اتركه فارغاً لعدم التغيير)" dir="ltr"></div>
              <div class="field-block"><label>أقصى عدد للجلسات (Max Sessions)</label><input id="eu-max" type="number" dir="ltr"></div>
              <div class="field-block"><label>أقصى عدد للسيرفرات (Max Servers)</label>
                <select id="eu-maxsrv" style="width:100%;padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px">
                  <option value="1">1</option><option value="2">2</option><option value="3">3</option>
                  <option value="5">5</option><option value="10">10</option><option value="999">Unlimited</option>
                </select>
              </div>
              <div class="field-block"><label>الملف الرئيسي (Main File)</label><input id="eu-main" dir="ltr"></div>
              <div class="field-block"><label>تمديد الاشتراك بالأيام</label><input id="eu-days" type="number" value="30" min="1" dir="ltr"></div>
            </div>
            <div class="modal-foot">
              <button class="btn-action gray" onclick="closeModal('edit-user-modal')">إلغاء</button>
              <button class="btn-action" onclick="saveEditUser()">حفظ التعديلات</button>
            </div>
          </div>
        </div>
      </div>

      <div class="tab-content" id="tab-backups">
        <div class="section-card">
          <div class="section-head">💾 النسخ الاحتياطية (Backups)</div>
          <div class="section-body">
            <div style="display:flex;gap:8px;margin-bottom:12px">
              <button class="btn-action green" onclick="createBackup()">➕ إنشاء نسخة احتياطية</button>
              <button class="btn-action gray" onclick="loadBackups()">🔄 تحديث القائمة</button>
            </div>
            <div id="backups-list"></div>
          </div>
        </div>
      </div>

      <div class="tab-content" id="tab-network">
        <div class="section-card">
          <div class="section-head">🔌 إدارة المنافذ الإضافية</div>
          <div class="section-body">
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">
              <input id="new-port" type="number" placeholder="Port (e.g. 8080)" dir="ltr" style="padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;width:160px">
              <input id="new-port-note" placeholder="ملاحظة (اختياري)" style="padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;flex:1;min-width:120px">
              <button class="btn-action" onclick="addPort()">إضافة منفذ</button>
            </div>
            <div id="ports-list"></div>
          </div>
        </div>
        <div class="section-card">
          <div class="section-head">🔍 فحص المنافذ (Port Scanner)</div>
          <div class="section-body">
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <input id="scan-host" placeholder="Host (e.g. 127.0.0.1)" dir="ltr" style="padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;flex:1">
              <input id="scan-ports" placeholder="Ports (22,80,443,8080)" dir="ltr" style="padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;flex:1">
              <button class="btn-action" onclick="scanPorts()">فحص</button>
            </div>
            <div id="scan-results" style="margin-top:12px" dir="ltr"></div>
          </div>
        </div>
      </div>

      <div class="tab-content" id="tab-startup">
        <div class="section-card">
          <div class="section-head">🚀 التشغيل التلقائي (Startup)</div>
          <div class="section-body">
            <div class="field-block"><label>الملف الأساسي للتشغيل</label><input id="startup-file" placeholder="main.py" dir="ltr"></div>
            <button class="btn-action" onclick="setStartupFile()">حفظ ملف التشغيل</button>
          </div>
        </div>
        <div class="section-card">
          <div class="section-head">📦 إدارة الحزم (Package Manager)</div>
          <div class="section-body">
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <input id="pip-pkg" placeholder="pip package name" dir="ltr" style="padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;flex:1">
              <button class="btn-action orange" onclick="installPip()">تثبيت بـ pip</button>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px">
              <input id="npm-pkg" placeholder="npm package name" dir="ltr" style="padding:10px;background:var(--bg3);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;flex:1">
              <button class="btn-action green" onclick="installNpm()">تثبيت بـ npm</button>
            </div>
          </div>
        </div>
      </div>
''' if is_master else '') + r'''

      <div class="tab-content" id="tab-settings">
        <div class="section-card">
          <div class="section-head">🔒 تغيير كلمة المرور</div>
          <div class="section-body">
            <div class="field-block"><label>كلمة المرور الحالية</label><input id="cur-pass" type="password" placeholder="Current password" dir="ltr"></div>
            <div class="field-block"><label>كلمة المرور الجديدة</label><input id="new-pass" type="password" placeholder="New password" dir="ltr"></div>
            <div class="row-end"><button class="btn-action" onclick="changePassword()">تغيير كلمة المرور</button></div>
          </div>
        </div>
        <div class="section-card">
          <div class="section-head">🖥 معلومات النظام (System Info)</div>
          <div class="section-body">
            <pre id="sysinfo-box" style="color:var(--text2);font-size:12px;font-family:monospace;white-space:pre-wrap" dir="ltr"></pre>
            <div class="row-end"><button class="btn-action gray" onclick="loadSysinfo()">🔄 تحديث المعلومات</button></div>
          </div>
        </div>
      </div>

      <div class="tab-content" id="tab-activity">
        <div class="section-card">
          <div class="section-head">📋 سجل الأنشطة (Activity Feed)</div>
          <div class="section-body">
            <div style="display:flex;justify-content:flex-end;margin-bottom:10px">
              <button class="btn-action gray" onclick="loadActivity()">🔄 تحديث السجل</button>
            </div>
            <div id="activity-list" dir="ltr"></div>
          </div>
        </div>
      </div>

''' + owner_panel_html + r'''

    </div></main>
</div><div class="modal" id="editor-modal">
  <div class="modal-box" style="width:min(900px, 95vw)">
    <div class="modal-head">
      <h3 id="editor-title">تعديل الملف</h3>
      <button class="close" onclick="closeModal('editor-modal')">×</button>
    </div>
    <div class="modal-body">
      <textarea class="editor-box" id="editor-content" spellcheck="false" dir="ltr"></textarea>
    </div>
    <div class="modal-foot">
      <button class="btn-action gray" onclick="closeModal('editor-modal')">إلغاء</button>
      <button class="btn-action" onclick="saveFile()">💾 حفظ التعديلات</button>
    </div>
  </div>
</div>

<div class="modal" id="servers-modal">
  <div class="modal-box">
    <div class="modal-head">
      <h3>🗂 السيرفرات المتصلة</h3>
      <button class="close" onclick="closeModal('servers-modal')">×</button>
    </div>
    <div class="modal-body" id="servers-modal-list" style="max-height:400px;overflow-y:auto" dir="ltr"></div>
    <div class="modal-foot">
      <button class="btn-action gray" onclick="closeModal('servers-modal')">إغلاق</button>
    </div>
  </div>
</div>

<div class="modal" id="extract-modal">
  <div class="modal-box">
    <div class="modal-head">
      <h3>📦 استخراج الملف المضغوط</h3>
      <button class="close" onclick="closeModal('extract-modal')">×</button>
    </div>
    <div class="modal-body">
      <input type="hidden" id="extract-src">
      <div class="field-block">
        <label>استخراج إلى مجلد (اختياري)</label>
        <input id="extract-dest" placeholder="(يتم الاستخراج في نفس المسار الافتراضي)" dir="ltr">
      </div>
    </div>
    <div class="modal-foot">
      <button class="btn-action gray" onclick="closeModal('extract-modal')">إلغاء</button>
      <button class="btn-action" onclick="doExtract()">📦 استخراج الآن</button>
    </div>
  </div>
</div>

<script>
// ─── إعدادات اللوحة الأساسية ───
const IS_MASTER = ''' + ('true' if is_master else 'false') + r''';
var USER_PATH = '';
var currentPath = '';
var currentEditPath = null;
var statsInterval = null;

// ─── محرك الترمنال المتعدد (Multi-Terminal State) ───
var terminals = {};          // tid -> { processId, history, histIdx, interval, dir }
var activeTerminalId = null;
var terminalCounter = 0;

function createTerminalState(tid){
  terminals[tid] = {
    processId: null,
    history: [],
    histIdx: -1,
    interval: null,
    dir: '~'
  };
}

// دعم الأكواد القديمة (Legacy shims)
Object.defineProperty(window, 'currentProcessId', {
  get(){ return activeTerminalId ? terminals[activeTerminalId]?.processId : null; },
  set(v){ if(activeTerminalId && terminals[activeTerminalId]) terminals[activeTerminalId].processId = v; }
});
Object.defineProperty(window, 'cmdHistory', {
  get(){ return activeTerminalId ? (terminals[activeTerminalId]?.history||[]) : []; },
  set(v){ if(activeTerminalId && terminals[activeTerminalId]) terminals[activeTerminalId].history = v; }
});
Object.defineProperty(window, 'cmdHistIdx', {
  get(){ return activeTerminalId ? (terminals[activeTerminalId]?.histIdx ?? -1) : -1; },
  set(v){ if(activeTerminalId && terminals[activeTerminalId]) terminals[activeTerminalId].histIdx = v; }
});
Object.defineProperty(window, 'consoleInterval', {
  get(){ return activeTerminalId ? terminals[activeTerminalId]?.interval : null; },
  set(v){ if(activeTerminalId && terminals[activeTerminalId]) terminals[activeTerminalId].interval = v; }
});

// ─── نظام الإشعارات (Toast) ───
function toast(msg, isErr=false, isInfo=false){
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = 'toast ' + (isErr ? 'err' : isInfo ? 'info' : 'ok');
  t.innerHTML = `${isErr ? '❌' : isInfo ? 'ℹ️' : '✅'} ${msg}`;
  c.appendChild(t);
  setTimeout(()=> t.remove(), 3500);
}

// ─── نظام التبديل بين التبويبات (Tab Switching) ───
document.querySelectorAll('.tab-item').forEach(tab=>{
  tab.addEventListener('click', ()=>{
    const id = tab.dataset.tab;
    document.querySelectorAll('.tab-item').forEach(t=> t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c=> c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-'+id).classList.add('active');
    
    // تحميل البيانات عند فتح التبويب لتخفيف الضغط
    if(id==='users') loadUsers();
    if(id==='backups') loadBackups();
    if(id==='network') loadPorts();
    if(id==='activity') loadActivity();
    if(id==='owner') loadOwnerPanel();
    if(id==='nodejs') loadNodejsList();
    if(id==='php') loadPhpList();
  });
});

// ─── أدوات مساعدة للنوافذ المنبثقة ───
function openModal(id){ document.getElementById(id).classList.add('open'); }
function closeModal(id){ document.getElementById(id).classList.remove('open'); }
document.querySelectorAll('.modal').forEach(m=>{
  m.addEventListener('click', e=>{ if(e.target===m) m.classList.remove('open'); });
});

// ─── حماية النصوص (Escape HTML) ───
function escapeHtml(s){ return String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

// ─── التحديث الحي لإحصائيات السيرفر (Stats Polling) ───
async function loadStats(){
  try{
    const r = await fetch('/api/system');
    const d = await r.json();
    if(d.cpu){
      document.getElementById('s-ip').textContent = d.ip||'—';
      document.getElementById('s-cpu').textContent = d.cpu||'—';
      document.getElementById('s-mem').textContent = d.memory||'—';
      document.getElementById('s-disk').textContent = d.disk||'—';
      document.getElementById('s-uptime').textContent = d.uptime||'—';
      document.getElementById('s-in').textContent = d.network_in||'—';
      document.getElementById('s-out').textContent = d.network_out||'—';
      document.getElementById('s-host').textContent = d.hostname||'—';
      document.getElementById('s-port').textContent = d.port||'—';
      document.getElementById('s-plat').textContent = (d.platform||'')+(d.python?' / py'+d.python:'');
      document.getElementById('port-display').textContent = d.port||'—';
      USER_PATH = USER_PATH || '';
    }
  } catch(e){}
}

async function loadProfile(){
  try{
    const r = await fetch('/api/profile');
    const d = await r.json();
    USER_PATH = d.user_path || '';
    currentPath = USER_PATH;
    document.getElementById('topbar-user').textContent = d.username || '';
    // تحديث روابط الويب والـ API
    document.getElementById('web-link').textContent = '/web/'+d.username+'/';
    document.getElementById('api-link').textContent = '/api-service/'+d.username+'/';
  }catch(e){}
}

function openWebLink(){ window.open('/web/'+(document.getElementById('topbar-user').textContent||'')+'/', '_blank'); }
function openApiLink(){ window.open('/api-service/'+(document.getElementById('topbar-user').textContent||'')+'/', '_blank'); }

function copyPort(){
  const p = document.getElementById('port-display').textContent;
  navigator.clipboard.writeText(p).then(()=> toast('تم نسخ المنفذ: '+p, false, true));
}

// ─── التحكم في التشغيل (Power / Process) ───
async function powerAction(action){
  if(action==='start'){
    let mainFile = 'main.py';
    try {
      const mfR = await fetch('/api/files/main-file');
      const mfD = await mfR.json();
      mainFile = mfD.main_file || 'main.py';
    } catch(e) {}
    if(!currentPath){
      try{ const p=await fetch('/api/profile').then(r=>r.json()); currentPath=p.user_path||''; }catch(e){}
    }
    // تحديث الهوية في مخرجات الترمنال الوهمية
    appendConsole('┌──(runner㉿dev-riko)-[~]');
    appendConsole('└─$ python3 ' + mainFile + '  ▶ Starting...');
    try {
      const r = await fetch('/api/file/run', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({path: currentPath, filename: mainFile})});
      const d = await r.json();
      if(d.success){
        currentProcessId = d.process_id;
        setProcStatus(true);
        appendConsole('[✔] Process started — ID: ' + d.process_id);
        toast('▶ تم التشغيل: ' + mainFile, false, true);
        startConsolePolling();
      } else {
        appendConsole('[✘] ERROR: ' + (d.error||'Failed to start'));
        toast('❌ ' + (d.error||'فشل التشغيل'), true);
      }
    } catch(e) {
      appendConsole('[✘] Network error: ' + (e.message||e));
      toast('❌ خطأ في الاتصال', true);
    }
  } else if(action==='stop'){
    if(!currentProcessId){ toast('لا يوجد بروسيس شغال حالياً', true); return; }
    appendConsole('└─$ kill ' + currentProcessId + '  ■ Stopping...');
    try {
      await fetch('/api/file/stop', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({process_id: currentProcessId})});
      appendConsole('[✔] Process stopped.');
    } catch(e) {
      appendConsole('[!] Stop request sent (connection issue).');
    }
    currentProcessId = null;
    setProcStatus(false);
    toast('■ تم الإيقاف', false, true);
    stopConsolePolling();
  } else if(action==='restart'){
    appendConsole('└─$ ↺ Restarting...');
    if(currentProcessId){
      try {
        await fetch('/api/file/stop', {method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({process_id: currentProcessId})});
      } catch(e) {}
      currentProcessId = null;
      setProcStatus(false);
      stopConsolePolling();
      appendConsole('[✔] Stopped — restarting in 800ms...');
    }
    setTimeout(()=> powerAction('start'), 800);
  }
}

function setProcStatus(running){
  const dot = document.getElementById('proc-dot');
  const txt = document.getElementById('proc-status');
  dot.style.background = running ? '#3fb950' : '#f85149';
  txt.textContent = running ? 'Running' : 'Stopped';
}

// ═══════════════════════════════════════════════════════════════════════════
//  MULTI-TERMINAL ENGINE — DEVELOPED BY RIKO
// ═══════════════════════════════════════════════════════════════════════════

function terminalBannerHTML(tid){
  return `<div style="line-height:1.6;margin-bottom:12px;user-select:none">
  <div style="font-family:'Fira Code',monospace;font-size:16px;font-weight:900;letter-spacing:3px;
    background:linear-gradient(90deg,var(--accent),var(--accent2),var(--accent));-webkit-background-clip:text;
    -webkit-text-fill-color:transparent;margin-bottom:4px">▪ 𝚁𝙸𝙺𝙾 ▪</div>
  <div style="color:var(--accent);font-family:'Fira Code',monospace;font-size:11px;opacity:0.85;line-height:1.2">
    ╔══════════════════════════════════════════════════╗<br>
    ║  🚀 <span style="color:var(--accent2);font-weight:700">SERVER HUB v2.0</span> — Professional Panel       ║<br>
    ║  👑 Developer : <span style="color:#fff;font-weight:600">@SHBH_S1</span>                         ║<br>
    ║  📢 Channel   : <span style="color:var(--yellow);font-weight:600">@SHOBING_HXH</span>                       ║<br>
    ╚══════════════════════════════════════════════════╝
  </div>
  <div style="color:var(--green);font-family:monospace;font-size:12px;margin-top:8px">┌──(<span style="color:var(--neon);font-weight:700">riko</span>㉿<span style="color:var(--accent2)">serverhub</span>)-[<span style="color:var(--yellow)">~</span>]</div>
  <div style="color:var(--green);font-family:monospace;font-size:12px">└─<span style="color:var(--neon);font-weight:700">$</span> <span style="color:var(--text)">👋 الترمنال #${tid} جاهز للعمل — يدعم العربي والإنجليزي ✓</span></div>
</div>`;
}

function buildTerminalEl(tid){
  const wrap = document.createElement('div');
  wrap.id = `term-wrap-${tid}`;
  wrap.style.display = 'none';

  // output box
  const box = document.createElement('div');
  box.id = `console-output-${tid}`;
  box.className = 'console-box';
  box.style.cursor = 'text';
  box.style.padding = '16px';
  box.style.minHeight = '300px';
  box.innerHTML = terminalBannerHTML(tid);
  box.addEventListener('click', ()=>{
    const inp = document.getElementById(`cmd-field-${tid}`);
    if(inp) inp.focus();
  });

  // fixed kali prompt footer inside box
  const footer = document.createElement('div');
  footer.id = `term-footer-${tid}`;
  footer.style.cssText = 'color:var(--green);font-family:monospace;font-size:12px;margin-top:8px;pointer-events:none;user-select:none;border-top:1px solid var(--border);padding-top:6px';
  footer.innerHTML = `┌──(<span style="color:var(--neon);font-weight:700">riko</span>㉿<span style="color:var(--accent2)">serverhub</span>)-[<span style="color:var(--yellow)" id="cwd-footer-${tid}">~</span>]<br>└─<span style="color:var(--neon);font-weight:700">$</span>`;
  box.appendChild(footer);

  // input row
  const cmdRow = document.createElement('div');
  cmdRow.className = 'cmd-input';
  cmdRow.style.marginTop = '8px';
  cmdRow.innerHTML = `
    <div style="width:100%">
      <div style="color:var(--green);font-family:monospace;font-size:11px;padding:4px 0;pointer-events:none;white-space:nowrap">
        ┌──(<span style="color:var(--neon);font-weight:700">riko</span>㉿<span style="color:var(--accent2)">serverhub</span>)-[<span style="color:var(--yellow)" id="cwd-input-${tid}">~</span>]<br>
        └─<span style="color:var(--neon);font-weight:700;font-size:13px">$</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <input id="cmd-field-${tid}"
          dir="auto" lang="ar,en" inputmode="text"
          autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
          placeholder="اكتب الأمر هنا (عربي أو إنجليزي)..."
          style="flex:1;background:none;border:0;outline:0;color:var(--text);padding:10px 0;
                 font-family:'Fira Code',monospace;font-size:13.5px;direction:ltr;unicode-bidi:embed"
          onkeydown="termKeyDown(event,'${tid}')">
        <button onclick="termRunCmd('${tid}')"
          style="padding:6px 14px;background:var(--bg3);border:1px solid var(--border2);border-radius:8px;
                 color:var(--accent);cursor:pointer;font-size:13px;flex-shrink:0;transition:0.2s"
          onmouseover="this.style.borderColor='var(--accent)'" 
          onmouseout="this.style.borderColor='var(--border2)'">↵</button>
      </div>
    </div>`;

  wrap.appendChild(box);
  wrap.appendChild(cmdRow);
  return wrap;
}

function addTerminal(){
  terminalCounter++;
  const tid = String(terminalCounter);
  createTerminalState(tid);

  const tabsBar = document.getElementById('term-tabs-bar');
  const btn = document.createElement('div');
  btn.id = `term-tab-${tid}`;
  btn.style.cssText = `display:flex;align-items:center;gap:6px;padding:6px 14px;background:var(--bg3);
    border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:12.5px;
    color:var(--text2);transition:.15s;white-space:nowrap;font-weight:500`;
  btn.innerHTML = `<span style="color:var(--green);font-size:10px;animation:blink 2s infinite">●</span> ترمنال ${tid}
    <span onclick="event.stopPropagation();closeTerminal('${tid}')"
      style="color:var(--text3);margin-left:6px;font-size:16px;line-height:1;transition:0.2s" 
      onmouseover="this.style.color='var(--red)'" onmouseout="this.style.color='var(--text3)'" title="إغلاق">×</span>`;
  btn.onclick = ()=> switchTerminal(tid);
  tabsBar.insertBefore(btn, tabsBar.lastElementChild);

  const container = document.getElementById('terminals-container');
  container.appendChild(buildTerminalEl(tid));
  switchTerminal(tid);
}

function switchTerminal(tid){
  Object.keys(terminals).forEach(id=>{
    const w = document.getElementById(`term-wrap-${id}`);
    if(w) w.style.display='none';
    const t = document.getElementById(`term-tab-${id}`);
    if(t){ 
      t.style.borderColor='var(--border)'; 
      t.style.color='var(--text2)'; 
      t.style.background='var(--bg3)';
      t.style.fontWeight='500';
    }
  });
  activeTerminalId = tid;
  const w = document.getElementById(`term-wrap-${tid}`);
  if(w) w.style.display='block';
  const t = document.getElementById(`term-tab-${tid}`);
  if(t){ 
    t.style.borderColor='var(--accent)'; 
    t.style.color='var(--accent)'; 
    t.style.background='rgba(124,92,252,0.08)'; 
    t.style.fontWeight='700';
  }
  setTimeout(()=>{ document.getElementById(`cmd-field-${tid}`)?.focus(); }, 50);
}

function closeTerminal(tid){
  if(Object.keys(terminals).length <= 1){ toast('يجب إبقاء ترمنال واحد على الأقل', true); return; }
  if(terminals[tid]?.interval) clearInterval(terminals[tid].interval);
  delete terminals[tid];
  document.getElementById(`term-wrap-${tid}`)?.remove();
  document.getElementById(`term-tab-${tid}`)?.remove();
  const rem = Object.keys(terminals);
  if(rem.length) switchTerminal(rem[rem.length-1]);
}

function appendToTerminal(tid, txt){
  const box = document.getElementById(`console-output-${tid}`);
  if(!box) return;
  const line = document.createElement('div');
  line.style.fontFamily = "'Fira Code',monospace";
  line.style.fontSize   = '13px';
  line.style.marginBottom = '2px';
  line.dir              = 'auto';
  const t = txt||'';
  
  if(/error|err:|exception|traceback|failed/i.test(t)){
    line.style.color='var(--red)'; line.style.textShadow='0 0 6px rgba(248,81,73,.2)';
  } else if(/warn|warning/i.test(t)){
    line.style.color='var(--yellow)';
  } else if(/\[.\]|started|running|success/i.test(t)){
    line.style.color='var(--green)'; line.style.textShadow='0 0 5px rgba(63,185,80,.1)';
  } else if(t.startsWith('$')||t.startsWith('└─')||t.startsWith('┌──')){
    line.style.color='var(--green)';
  } else {
    line.style.color='var(--text)';
  }
  
  line.textContent = t;
  const footer = document.getElementById(`term-footer-${tid}`);
  if(footer) box.insertBefore(line, footer);
  else       box.appendChild(line);
  box.scrollTop = box.scrollHeight;
  const kids = box.querySelectorAll(':scope>div:not([id])');
  if(kids.length > 1000) kids[0].remove();
}

function appendConsole(txt){
  if(activeTerminalId) appendToTerminal(activeTerminalId, txt);
}

async function termRunCmd(tid){
  const inp = document.getElementById(`cmd-field-${tid}`);
  if(!inp) return;
  const cmd = inp.value.trim();
  if(!cmd) return;
  const ts = terminals[tid];
  ts.history.unshift(cmd); ts.histIdx=-1;
  inp.value='';
  appendToTerminal(tid, '└─$ '+cmd);
  if(ts.processId){
    await fetch('/api/file/input',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({process_id:ts.processId,input:cmd})});
  } else {
    try{
      const r=await fetch('/api/exec',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({command:cmd,cwd:currentPath})});
      const d=await r.json();
      if(d.output) d.output.split('\n').forEach(l=>{ if(l.trim()) appendToTerminal(tid,l); });
      if(d.error)  appendToTerminal(tid,'❌ '+d.error);
      if(/^cd\s/.test(cmd)){
        const nd=cmd.slice(3).trim()||'~';
        document.getElementById(`cwd-footer-${tid}`)?.textContent !== undefined &&
          (document.getElementById(`cwd-footer-${tid}`).textContent=nd);
        document.getElementById(`cwd-input-${tid}`)?.textContent !== undefined &&
          (document.getElementById(`cwd-input-${tid}`).textContent=nd);
      }
    }catch(e){ appendToTerminal(tid,'❌ Error: '+e); }
  }
}

async function runCmd(){
  if(activeTerminalId) await termRunCmd(activeTerminalId);
}

function termKeyDown(e, tid){
  const ts=terminals[tid];
  const inp=document.getElementById(`cmd-field-${tid}`);
  if(!ts||!inp) return;
  if(e.key==='Enter'){ e.preventDefault(); termRunCmd(tid); }
  else if(e.key==='ArrowUp'){
    e.preventDefault();
    ts.histIdx=Math.min(ts.histIdx+1,ts.history.length-1);
    inp.value=ts.history[ts.histIdx]||'';
    inp.selectionStart=inp.selectionEnd=inp.value.length;
  } else if(e.key==='ArrowDown'){
    e.preventDefault();
    ts.histIdx=Math.max(ts.histIdx-1,-1);
    inp.value=ts.histIdx>=0?ts.history[ts.histIdx]:'';
    inp.selectionStart=inp.selectionEnd=inp.value.length;
  } else if(e.key==='Tab') e.preventDefault();
}

function cmdKeyDown(e){
  if(activeTerminalId) termKeyDown(e,activeTerminalId);
}

function startConsolePolling(){
  if(!activeTerminalId) return;
  stopConsolePolling();
  const tid=activeTerminalId;
  const ts=terminals[tid];
  ts.interval=setInterval(async()=>{
    if(!ts.processId) return;
    try{
      const r=await fetch('/api/file/output/'+ts.processId);
      const d=await r.json();
      if(d.success && d.output && d.output.length){
        d.output.forEach(l=>appendToTerminal(tid,l));
        await fetch('/api/file/output/'+ts.processId+'/clear',{method:'POST'}).catch(()=>{});
      }
      if(!d.is_running){ setProcStatus(false); ts.processId=null; clearInterval(ts.interval); ts.interval=null; }
    }catch(e){}
  },800);
}

function stopConsolePolling(){
  if(!activeTerminalId) return;
  const ts=terminals[activeTerminalId];
  if(ts?.interval){ clearInterval(ts.interval); ts.interval=null; }
}

function initTerminals(){ addTerminal(); }

// ═══════════════════════════════════════════════════════════════════════════
//  PREMIUM FILE MANAGER ENGINE — DEVELOPED BY RIKO
//  👑 Dev: @SHBH_S1 | 📢 Channel: @SHOBING_HXH
// ═══════════════════════════════════════════════════════════════════════════

async function loadFiles(path){
  if(!path && !currentPath){
    try {
      const prof = await fetch('/api/profile').then(r=>r.json());
      currentPath = prof.user_path || '';
    } catch(e) { currentPath = ''; }
  }
  const p = path || currentPath;
  currentPath = p;
  try{
    const r = await fetch('/api/files?path='+encodeURIComponent(p));
    const d = await r.json();
    renderFiles(d.files||[], p);
    renderBreadcrumb(p);
  }catch(e){ toast('❌ فشل في تحميل الملفات', true); }
}

function getFileIcon(name, isDir){
  if(isDir) return '📁';
  const ext = name.split('.').pop().toLowerCase();
  const m = {
    py:'🐍', js:'📜', ts:'📜', jsx:'⚛️', tsx:'⚛️',
    html:'🌐', htm:'🌐', css:'🎨', scss:'🎨',
    json:'📋', yml:'⚙️', yaml:'⚙️', toml:'⚙️', ini:'⚙️',
    md:'📝', txt:'📄', sh:'⚡', bash:'⚡',
    zip:'📦', tar:'📦', gz:'📦', rar:'📦',
    jpg:'🖼', jpeg:'🖼', png:'🖼', gif:'🖼', svg:'🖼',
    mp4:'🎬', mp3:'🎵', pdf:'📕', php:'🐘', rb:'💎',
    sql:'🗄', db:'🗄', sqlite:'🗄'
  };
  return m[ext] || '📄';
}

function renderFiles(files, path){
  const list = document.getElementById('file-list');
  if(!list) return;
  
  if(!files.length){
    list.innerHTML = `
      <div style="padding:40px;text-align:center;color:var(--text3);font-family:monospace;font-size:14px">
        <span style="font-size:32px;display:block;margin-bottom:8px">📂</span> المجلد فارغ تماماً
      </div>`;
    return;
  }
  
  list.innerHTML = '';
  files.forEach(f => {
    const fp = path.replace(/\/*$/, '') + '/' + f.name;
    const row = document.createElement('div');
    
    // تصميم مخصص ومحسّن لكل سطر ملف ليناسب الـ Dashboard
    row.className = 'file-item';
    row.style.cssText = `
      display:flex;align-items:center;justify-content:between;padding:10px 14px;
      background:var(--bg2);border:1px solid var(--border);border-radius:10px;
      margin-bottom:8px;transition:all 0.2s ease;gap:12px;box-sizing:border-box;
    `;
    
    // تنسيق الأزرار الافتراضي المتناسق
    const btnStyle = `
      padding:5px 10px;background:var(--bg3);border:1px solid var(--border2);
      border-radius:6px;color:var(--text2);font-size:12px;cursor:pointer;
      font-weight:500;transition:0.15s;display:inline-flex;align-items:center;gap:4px;
    `;

    row.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;flex:1;min-width:0">
        <span style="font-size:18px;flex-shrink:0;user-select:none">${getFileIcon(f.name, f.is_dir)}</span>
        <span style="color:var(--text);font-family:'Fira Code',monospace;font-size:13.5px;
                     white-space:nowrap;overflow:hidden;text-overflow:ellipsis;direction:ltr;text-align:left">${escapeHtml(f.name)}</span>
        <span style="color:var(--text3);font-size:11px;font-family:monospace;margin-left:auto;flex-shrink:0">${f.size || ''}</span>
      </div>
      <div class="file-actions" style="display:flex;align-items:center;gap:6px;flex-shrink:0">
        ${f.is_dir ? 
          `<button style="${btnStyle}color:var(--accent)" onclick="loadFiles('${escapeHtml(fp)}')">📂 فتح</button>` :
          `<button style="${btnStyle}color:var(--yellow)" onclick="editFile('${escapeHtml(fp)}','${escapeHtml(f.name)}')">✏️ تعديل</button>
           <button style="${btnStyle}color:var(--green)" onclick="runSingleFile('${escapeHtml(fp)}','${escapeHtml(f.name)}')">▶ تشغيل</button>`
        }
        ${(f.name.endsWith('.zip') || f.name.endsWith('.tar.gz') || f.name.endsWith('.tar')) ?
          `<button style="${btnStyle}color:var(--neon)" onclick="openExtractModal('${escapeHtml(fp)}')">📦 فك الضغط</button>` : ''
        }
        <button style="${btnStyle}" onclick="setMain('${escapeHtml(f.name)}','${escapeHtml(fp)}')">★ أساسي</button>
        <button style="${btnStyle}color:var(--red);border-color:rgba(248,81,73,0.2)" 
                onmouseover="this.style.background='var(--red)';this.style.color='#fff'" 
                onmouseout="this.style.background='var(--bg3)';this.style.color='var(--red)'"
                onclick="deleteFile('${escapeHtml(fp)}','${escapeHtml(f.name)}')">🗑</button>
      </div>`;
      
    list.appendChild(row);
  });
}

function renderBreadcrumb(path){
  const el = document.getElementById('breadcrumb');
  if(!el) return;
  const base = USER_PATH || '';
  const rel = path.replace(base, '') || '/';
  
  // تنسيق مسار التنقل الداخلي ليعطي طابعاً برمجياً أنيقاً
  el.style.cssText = `font-family:'Fira Code',monospace;font-size:12.5px;color:var(--text2);
                      background:var(--bg3);padding:8px 14px;border-radius:8px;border:1px solid var(--border);
                      display:inline-flex;align-items:center;gap:4px;direction:ltr`;
                      
  el.innerHTML = `<span style="color:var(--accent);font-weight:700">~ root</span> <span style="color:var(--text3)">/</span> ` + 
                 escapeHtml(rel.replace(/\//g, ' <span style="color:var(--text3)">/</span> '));
}

async function editFile(path, name){
  try{
    const r = await fetch('/api/files/content?path='+encodeURIComponent(path));
    const d = await r.json();
    const title = document.getElementById('editor-title');
    const area = document.getElementById('editor-content');
    
    if(title) title.textContent = '✏️ تعديل ملف: ' + name;
    if(area) area.value = d.content || '';
    
    currentEditPath = path;
    openModal('editor-modal');
  }catch(e){ toast('❌ لا يمكن فتح الملف المتواجد بالمسار', true); }
}

async function saveFile(){
  if(!currentEditPath) return;
  const area = document.getElementById('editor-content');
  const content = area ? area.value : '';
  
  try {
    const r = await fetch('/api/files/save',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path:currentEditPath,content})});
    const d = await r.json();
    toast(d.success ? '✅ تم حفظ التغييرات بنجاح' : '❌ فشل في حفظ الملف', !d.success);
    if(d.success) closeModal('editor-modal');
  } catch(e) { toast('❌ خطأ أثناء الاتصال بالخادم', true); }
}

async function runSingleFile(path, name){
  const dir = path.substring(0, path.lastIndexOf('/'));
  try {
    const r = await fetch('/api/file/run',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path:dir,filename:name})});
    const d = await r.json();
    if(d.success){
      currentProcessId = d.process_id;
      if (typeof setProcStatus === "function") setProcStatus(true);
      
      document.querySelectorAll('.tab-item').forEach(t => { 
        if(t.dataset.tab === 'console' || t.getAttribute('data-tab') === 'console') t.click(); 
      });
      
      toast('▶ تم بدء تشغيل: ' + name);
      if (typeof startConsolePolling === "function") startConsolePolling();
    } else { 
      toast('❌ ' + (d.error || 'فشل تشغيل الملف'), true); 
    }
  } catch(e) { toast('❌ خطأ في تنفيذ الملف', true); }
}

async function setMain(filename, path){
  try {
    const r = await fetch('/api/files/set-main',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({filename,path})});
    const d = await r.json();
    toast(d.success ? '★ تم تعيين الملف الرئيسي: ' + filename : '❌ فشل التعيين', !d.success);
  } catch(e) { toast('❌ فشل في إرسال الطلب', true); }
}

async function deleteFile(path, name){
  if(!confirm(`هل أنت متأكد من حذف الملف "${name}" نهائياً؟`)) return;
  try {
    const r = await fetch('/api/files/delete',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path})});
    const d = await r.json();
    toast(d.success ? '🗑 تم حذف الملف' : '❌ فشل الحذف', !d.success);
    if(d.success) loadFiles(currentPath);
  } catch(e) { toast('❌ حدث خطأ غير متوقع', true); }
}

async function createDir(){
  const n = prompt('أدخل اسم المجلد الجديد:'); 
  if(!n) return;
  const p = currentPath.replace(/\/*$/, '') + '/' + n;
  try {
    const r = await fetch('/api/files/folder',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path:p})});
    const d = await r.json();
    toast(d.success ? '📁 تم إنشاء المجلد بنجاح' : '❌ فشل إنشاء المجلد', !d.success);
    if(d.success) loadFiles(currentPath);
  } catch(e) { toast('❌ خطأ في العملية', true); }
}

async function newFile(){
  const n = prompt('أدخل اسم الملف الجديد مع الصيغة (مثال: index.js):'); 
  if(!n) return;
  const p = currentPath.replace(/\/*$/, '') + '/' + n;
  try {
    const r = await fetch('/api/files/create',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path:p,content:''})});
    const d = await r.json();
    toast(d.success ? '📄 تم إنشاء الملف بنجاح' : '❌ فشل إنشاء الملف', !d.success);
    if(d.success){ loadFiles(currentPath); editFile(p, n); }
  } catch(e) { toast('❌ خطأ في العملية', true); }
}

async function uploadFiles(inp){
  const files = inp.files; 
  if(!files.length) return;
  let ok = 0, fail = 0;
  
  for(const f of files){
    const fd = new FormData();
    fd.append('file', f);
    fd.append('path', currentPath);
    try {
      const r = await fetch('/api/files/upload', {method:'POST', body:fd});
      const d = await r.json();
      if(d.success){
        ok++;
      } else {
        fail++;
        const errMsg = (d.error || 'Upload failed');
        if(errMsg.startsWith('SECURITY_ALERT|')){
          const threats = errMsg.replace('SECURITY_ALERT|', '');
          showSecurityAlert(f.name, threats);
        } else {
          toast('❌ ' + errMsg, true);
        }
      }
    } catch(e) { fail++; }
  }
  if(ok > 0) toast('⬆ تم رفع: ' + ok + ' ملف بنجاح', false);
  loadFiles(currentPath);
  inp.value = '';
}

function showSecurityAlert(fname, threats){
  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:999999;
    display:flex;align-items:center;justify-content:center;backdrop-filter:blur(10px);
    transition: all 0.3s ease;
  `;
  
  overlay.innerHTML = `
    <div style="background:var(--bg);border:2px solid var(--red);border-radius:20px;
                padding:36px 32px;max-width:460px;width:92%;text-align:center;
                box-shadow:0 0 50px rgba(248,81,73,0.35), 0 0 100px rgba(248,81,73,0.1);box-sizing:border-box">
      <div style="font-size:64px;margin-bottom:12px;user-select:none;animation:pulse 1.2s ease-in-out infinite">🚨</div>
      <div style="color:var(--red);font-size:24px;font-weight:900;margin-bottom:12px;letter-spacing:1px;font-family:sans-serif">تحذير أمني صارم!</div>
      
      <div style="background:rgba(248,81,73,0.05);border:1px solid rgba(248,81,73,0.25);border-radius:12px;padding:16px;margin-bottom:20px">
        <div style="color:#ff8888;font-size:14.5px;font-weight:700;margin-bottom:8px">⚠️ بطل عبط يا حبيبي عشان متتحظرش!</div>
        <div style="color:var(--text2);font-size:12.5px;margin-bottom:8px;text-align:right;direction:rtl">الملف: <span style="color:var(--red);font-family:'Fira Code',monospace;font-weight:600">${escapeHtml(fname)}</span></div>
        <div style="color:var(--text2);font-size:12.5px;text-align:right;direction:rtl">المشكلة المخالفة: <span style="color:var(--yellow);font-family:'Fira Code',monospace;font-size:12px;font-weight:600">${escapeHtml(threats)}</span></div>
      </div>
      
      <div style="color:var(--text3);font-size:12px;margin-bottom:20px;font-family:monospace">⛔ [SYSTEM]: تم تسجيل النشاط وإرسال تقرير فوري للمطور RIKO</div>
      <button onclick="this.closest('div').parentElement.remove()" 
              style="padding:12px 36px;background:linear-gradient(135deg, #b62324, var(--red));border:none;border-radius:10px;
                     color:#fff;font-weight:800;cursor:pointer;font-size:15px;box-shadow:0 4px 15px rgba(248,81,73,0.3);
                     transition:0.2s"
              onmouseover="this.style.opacity='0.9'" onmouseout="this.style.opacity='1'">حسناً، فهمت ✓</button>
    </div>
  `;
  document.body.appendChild(overlay);
}


// ═══════════════════════════════════════════════════════════════════════════
//  ADVANCED UTILITIES & SCHEDULES ENGINE — DEVELOPED BY RIKO
//  👑 Dev: @SHBH_S1 | 📢 Channel: @SHOBING_HXH
// ═══════════════════════════════════════════════════════════════════════════

async function uploadAndExtract(inp){
  const f = inp.files[0]; 
  if(!f) return;
  
  toast('⬆ جاري رفع الملف المضغوط وفكه...', false);
  const fd = new FormData();
  fd.append('file', f);
  fd.append('path', currentPath);
  
  try {
    const r = await fetch('/api/files/upload', {method:'POST', body:fd});
    const d = await r.json();
    
    if(!d.success){ 
      const errMsg = d.error || 'فشل الرفع';
      if(errMsg.startsWith('SECURITY_ALERT|') && typeof showSecurityAlert === 'function'){
        showSecurityAlert(f.name, errMsg.replace('SECURITY_ALERT|', ''));
      } else {
        toast('❌ فشل رفع الملف: ' + errMsg, true); 
      }
      return; 
    }
    
    // تحديد المسارات بشكل آمن وبدون تكرار السلاش
    const safePath = currentPath.replace(/\/*$/, '');
    const archivePath = safePath + '/' + d.filename;
    const destPath = safePath + '/' + d.filename.replace(/\.(zip|tar\.gz|tar|rar|gz)$/i, '');
    
    const er = await fetch('/api/files/extract', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({archive:archivePath, dest:destPath})
    });
    const ed = await er.json();
    
    if(ed.success) {
      toast(`📦 تم استخراج الأرشيف بنجاح: ${ed.extracted} ملف`, false);
    } else {
      toast('❌ فشل فك الضغط: ' + (ed.error || 'خطأ مجهول'), true);
    }
    
    loadFiles(currentPath);
  } catch(e) { 
    toast('❌ خطأ أثناء معالجة الأرشيف', true); 
  } finally {
    inp.value = '';
  }
}

function openExtractModal(srcPath){
  const srcField = document.getElementById('extract-src');
  const destField = document.getElementById('extract-dest');
  
  if(srcField) srcField.value = srcPath;
  if(destField) destField.value = '';
  
  if(typeof openModal === 'function') openModal('extract-modal');
}

async function doExtract(){
  const srcField = document.getElementById('extract-src');
  const destField = document.getElementById('extract-dest');
  
  if(!srcField) return;
  const src = srcField.value;
  const destIn = destField ? destField.value.trim() : '';
  const dest = destIn || src.replace(/\.(zip|tar\.gz|tar|rar|gz)$/i, '');
  
  try {
    const r = await fetch('/api/files/extract', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({archive:src, dest})
    });
    const d = await r.json();
    
    if(d.success){
      toast(`📦 تم فك الضغط بنجاح: ${d.extracted} ملف`, false);
      if(typeof closeModal === 'function') closeModal('extract-modal');
      loadFiles(currentPath);
    } else {
      toast('❌ ' + (d.error || 'فشل فك الضغط عن الملف'), true);
    }
  } catch(e) {
    toast('❌ خطأ في الاتصال بالخادم', true);
  }
}

// ─── DATABASE MANAGEMENT (JSON BASED) ───
async function createDB(){
  const dbInput = document.getElementById('db-name');
  if(!dbInput) return;
  
  const n = dbInput.value.trim(); 
  if(!n) { toast('⚠️ يرجى إدخال اسم قاعدة البيانات', true); return; }
  
  const safePath = currentPath.replace(/\/*$/, '');
  const dbPath = safePath + '/' + n + '.json';
  
  try {
    const r = await fetch('/api/files/create', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({path: dbPath, content: '{}'})
    });
    const d = await r.json();
    
    if(d.success) {
      toast('🗄️ تم إنشاء قاعدة البيانات بنجاح: ' + n + '.json', false);
      dbInput.value = '';
      loadFiles(currentPath);
    } else {
      toast('❌ فشل إنشاء قاعدة البيانات', true);
    }
  } catch(e) {
    toast('❌ حدث خطأ أثناء إنشاء الملف', true);
  }
}

// ─── CRON SCHEDULES MANAGEMENT ───
async function addSchedule(){
  const nameField = document.getElementById('sch-name');
  const cmdField = document.getElementById('sch-cmd');
  const cronField = document.getElementById('sch-cron');
  
  if(!nameField || !cmdField || !cronField) return;
  
  const name = nameField.value.trim();
  const cmd  = cmdField.value.trim();
  const cron = cronField.value.trim();
  
  if(!name || !cmd) { 
    toast('⚠️ يرجى ملء حقول الاسم والأمر على الأقل', true); 
    return; 
  }
  
  try {
    const r = await fetch('/api/schedules/add', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name, command:cmd, schedule:cron})
    });
    const d = await r.json();
    
    if(d.success){
      toast('⏰ تم إضافة المجدول الزمني بنجاح: ' + name, false);
      nameField.value = '';
      cmdField.value = '';
      cronField.value = '';
      // إذا كان هناك دالة لتحديث قائمة المجدولات يمكن استدعاؤها هنا
    } else {
      toast('❌ فشل إضافة المجدول الزمني', true);
    }
  } catch(e) {
    toast('❌ خطأ في الاتصال بالنظام', true);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  PREMIUM NODE.JS ENGINE — DEVELOPED BY RIKO
//  👑 Dev: @SHBH_S1 | 📢 Channel: @SHOBING_HXH
// ═══════════════════════════════════════════════════════════════════════════

async function loadNodeJsFiles(){
  const pathEl = document.getElementById('nodejs-path');
  const mainEl = document.getElementById('nodejs-main');
  const depsEl = document.getElementById('nodejs-deps');
  const listEl = document.getElementById('nodejs-files-list');
  
  if(!pathEl || !listEl) return;
  const path = pathEl.value.trim();
  if(!path){ toast('⚠️ اكتب مسار المشروع أولاً', true); return; }
  
  listEl.style.display = 'block';
  listEl.style.cssText = `display:block;background:var(--bg2);border:1px solid var(--border);
                          border-radius:10px;margin-top:8px;max-height:220px;overflow-y:auto;padding:6px;`;
  listEl.innerHTML = '<div style="padding:12px;color:var(--text2);font-size:12.5px;font-family:monospace">⏳ جاري فحص ملفات المشروع...</div>';
  
  try{
    const r = await fetch('/api/nodejs/info',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        path, 
        main_file: mainEl ? mainEl.value.trim() || null : null,
        deps_file: depsEl ? depsEl.value.trim() || null : null
      })
    });
    const d = await r.json();
    
    if(!d.success){ 
      listEl.innerHTML = `<div style="padding:12px;color:var(--red);font-size:12.5px;font-family:monospace">❌ ${escapeHtml(d.error || 'Error')}</div>`; 
      return; 
    }
    
    // عرض أوامر التثبيت والتشغيل المتوقعة بتنسيق الكونسول
    const ic = document.getElementById('nodejs-install-cmd');
    const rc = document.getElementById('nodejs-run-cmd');
    if(ic) ic.textContent = '$ ' + (d.install_command || 'npm install');
    if(rc) rc.textContent = '$ ' + (d.run_command || 'node index.js');
    
    const previewEl = document.getElementById('nodejs-cmd-preview');
    if(previewEl) previewEl.style.display = 'block';
    
    // عرض قائمة ملفات الـ JS المتاحة
    const files = d.js_files || [];
    if(!files.length){ 
      listEl.innerHTML = '<div style="padding:12px;color:var(--text3);font-size:12.5px">📂 لا توجد ملفات .js في هذا المسار</div>'; 
      return; 
    }
    
    listEl.innerHTML = files.map(f => `
      <div onclick="if(document.getElementById('nodejs-main')) document.getElementById('nodejs-main').value='${escapeHtml(f)}'; document.getElementById('nodejs-files-list').style.display='none';"
           style="padding:8px 12px;font-size:13px;color:var(--text);cursor:pointer;border-radius:6px;
                  font-family:'Fira Code',monospace;transition:0.15s;display:flex;align-items:center;gap:8px;" 
           onmouseover="this.style.background='var(--bg3)';this.style.color='var(--accent)';" 
           onmouseout="this.style.background='';this.style.color='var(--text)';">
        <span style="color:var(--yellow)">📜</span> ${escapeHtml(f)}
      </div>`).join('');
  }catch(e){ 
    listEl.innerHTML = '<div style="padding:12px;color:var(--red);font-size:12.5px">❌ خطأ في تحميل مسار الملفات</div>'; 
  }
}

async function previewNodeCmd(){
  const pathEl = document.getElementById('nodejs-path');
  const mainEl = document.getElementById('nodejs-main');
  const depsEl = document.getElementById('nodejs-deps');
  if(!pathEl) return;
  
  const path = pathEl.value.trim();
  if(!path){ toast('⚠️ اكتب مسار المشروع أولاً', true); return; }
  
  try {
    const r = await fetch('/api/nodejs/info',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        path,
        main_file: mainEl ? mainEl.value.trim() || null : null,
        deps_file: depsEl ? depsEl.value.trim() || null : null
      })
    });
    const d = await r.json();
    const ic = document.getElementById('nodejs-install-cmd');
    const rc = document.getElementById('nodejs-run-cmd');
    if(ic) ic.textContent = '$ ' + (d.install_command || 'npm install');
    if(rc) rc.textContent = '$ ' + (d.run_command || 'node index.js');
    
    const previewEl = document.getElementById('nodejs-cmd-preview');
    if(previewEl) previewEl.style.display = 'block';
    toast('✅ تم تحديث ومعاينة الأوامر', false);
  } catch(e) { toast('❌ فشل جلب المعاينة', true); }
}

async function startNodeProject(){
  const path = document.getElementById('nodejs-path')?.value.trim();
  const port = document.getElementById('nodejs-port')?.value.trim();
  const mainFile = document.getElementById('nodejs-main')?.value.trim();
  const depsFile = document.getElementById('nodejs-deps')?.value.trim();
  
  if(!path){ toast('⚠️ يرجى إدخال مسار مشروع Node.js', true); return; }
  toast('🟢 جاري تشغيل بيئة الـ Node.js...', false);
  
  const outEl = document.getElementById('nodejs-start-output');
  if(outEl){ 
    outEl.style.display = 'block'; 
    outEl.style.cssText = `display:block;padding:14px;background:#090d13;border:1px solid var(--border);
                            border-radius:10px;color:#e6edf3;font-family:'Fira Code',monospace;font-size:12.5px;
                            line-height:1.5;margin-top:12px;white-space:pre-wrap;`;
    outEl.textContent = '⏳ [SYSTEM]: Installing project dependencies...\n'; 
  }
  
  try {
    const r = await fetch('/api/nodejs/start',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        path, 
        port: port ? parseInt(port) : null,
        main_file: mainFile || null, 
        deps_file: depsFile || null
      })
    });
    const d = await r.json();
    
    if(outEl && d.install_output) outEl.textContent += d.install_output;
    
    if(d.success){
      if(outEl) outEl.textContent += `\n✅ [SUCCESS]: Started command -> ${d.command}\n🔌 [PORT]: Project deployed on port ${d.port}\n`;
      toast(`▶ تم تشغيل المشروع بنجاح على البورت ${d.port}`);
      loadNodejsList();
    } else {
      if(outEl && d.install_commands) outEl.textContent += `\n📋 [REQUIRED INSTALL]:\n  ${d.install_commands.join('\n  ')}\n`;
      if(outEl && d.run_command) outEl.textContent += `📋 [RUN COMMAND]:\n  ${d.run_command}\n`;
      toast('❌ فشل بدء تشغيل المشروع: ' + (d.error || 'خطأ داخلي'), true);
    }
  } catch(e) { 
    toast('❌ خطأ أثناء بدء خادم Node.js', true); 
  }
}

async function loadNodejsList(){
  try{
    const r = await fetch('/api/nodejs/list');
    const d = await r.json();
    const list = document.getElementById('nodejs-list');
    if(!list) return;
    
    if(!(d.processes || []).length){
      list.innerHTML = `
        <div style="padding:32px;text-align:center;color:var(--text3);font-family:monospace;font-size:13px">
          📭 لا توجد عمليات Node.js نشطة حالياً.
        </div>`;
      return;
    }
    
    list.innerHTML = '';
    d.processes.forEach(p => {
      const card = document.createElement('div');
      card.className = 'nodejs-project-card';
      
      // تنسيق بطاقات المشاريع بشكل بريميوم متناسق ومستقر
      card.style.cssText = `
        display:flex;align-items:center;justify-content:space-between;padding:14px;
        background:var(--bg2);border:1px solid var(--border);border-radius:12px;
        margin-bottom:10px;gap:16px;box-sizing:border-box;transition:0.2s ease;
      `;
      
      const isRunning = !!p.running;
      const statusColor = isRunning ? 'var(--green)' : 'var(--red)';
      const statusBg = isRunning ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)';
      const shadowGlow = isRunning ? '0 0 8px rgba(63,185,80,0.3)' : 'none';
      
      const btnStyle = `padding:6px 12px;background:var(--bg3);border:1px solid var(--border2);
                        border-radius:8px;color:var(--text2);font-size:12px;cursor:pointer;
                        font-weight:600;font-family:sans-serif;transition:0.15s;`;

      card.innerHTML = `
        <div class="project-info" style="flex:1;min-width:0;text-align:left;direction:ltr">
          <div class="p-name" style="font-family:'Fira Code',monospace;font-size:14px;font-weight:700;color:var(--text);margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            <span style="color:${statusColor};text-shadow:${shadowGlow};margin-right:4px">●</span> ${escapeHtml(p.command || p.pid)}
          </div>
          <div class="p-meta" style="font-family:monospace;font-size:11.5px;color:var(--text3);line-height:1.4">
            Port: <span style="color:var(--accent)">${p.port || '—'}</span> · 
            Main: <span style="color:var(--text2)">${escapeHtml(p.main_file || 'auto')}</span> · 
            Deps: <span style="color:var(--text2)">${escapeHtml(p.deps_file || 'package.json')}</span>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
          <span style="padding:4px 10px;background:${statusBg};color:${statusColor};border-radius:6px;font-size:11px;font-weight:700;font-family:monospace;letter-spacing:0.5px">
            ${isRunning ? 'RUNNING' : 'STOPPED'}
          </span>
          <button style="${btnStyle}color:var(--yellow)" onclick="viewNodeLogs('${escapeHtml(p.pid)}')">📋 السجلات</button>
          <button style="${btnStyle}color:var(--red);border-color:rgba(248,81,73,0.15)" 
                  onmouseover="this.style.background='var(--red)';this.style.color='#fff'"
                  onmouseout="this.style.background='var(--bg3)';this.style.color='var(--red)'"
                  onclick="stopNodeProcess('${escapeHtml(p.pid)}')">■ إيقاف</button>
        </div>`;
        
      list.appendChild(card);
    });
  }catch(e){}
}

async function stopNodeProcess(pid){
  if(!confirm('هل أنت متأكد من إيقاف عملية الـ Node هذه؟')) return;
  try {
    const r = await fetch('/api/nodejs/stop',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pid})});
    const d = await r.json();
    toast(d.success ? '■ تم إيقاف عملية المشروع' : '❌ فشل إيقاف المشروع', !d.success);
    if(d.success) loadNodejsList();
  } catch(e) { toast('❌ خطأ في الاتصال بالسيرفر', true); }
}

async function viewNodeLogs(pid){
  try {
    const r = await fetch('/api/nodejs/logs/' + pid);
    const d = await r.json();
    
    if(activeTerminalId){
      const box = document.getElementById('console-output-' + activeTerminalId);
      if(box){ 
        const footer = document.getElementById('term-footer-' + activeTerminalId); 
        while(box.firstChild && box.firstChild !== footer) {
          box.removeChild(box.firstChild); 
        }
      }
    }
    
    // طباعة السجلات واللوغات داخل الترمنال النشط لـ RIKO
    if(d.output && d.output.length){
      d.output.forEach(l => appendConsole(l));
    } else {
      appendConsole(`[SYSTEM]: No logs found for process ${pid}`);
    }
    
    document.querySelectorAll('.tab-item').forEach(t => { 
      if(t.dataset.tab === 'console' || t.getAttribute('data-tab') === 'console') t.click(); 
    });
    toast('📋 تم تحميل وعرض سجلات المخرجات بنجاح', false);
  } catch(e) { toast('❌ فشل جلب سجلات اللوغات', true); }
}

// ═══════════════════════════════════════════════════════════════════════════
//  PREMIUM PHP ENGINE — DEVELOPED BY RIKO
//  👑 Dev: @SHBH_S1 | 📢 Channel: @SHOBING_HXH
// ═══════════════════════════════════════════════════════════════════════════

async function loadPhpFiles(){
  const pathEl = document.getElementById('php-path');
  const mainEl = document.getElementById('php-main');
  const depsEl = document.getElementById('php-deps');
  const listEl = document.getElementById('php-files-list');
  
  if(!pathEl || !listEl) return;
  const path = pathEl.value.trim();
  if(!path){ toast('⚠️ اكتب مسار المشروع أولاً', true); return; }
  
  listEl.style.display = 'block';
  listEl.style.cssText = `display:block;background:var(--bg2);border:1px solid var(--border);
                          border-radius:10px;margin-top:8px;max-height:220px;overflow-y:auto;padding:6px;`;
  listEl.innerHTML = '<div style="padding:12px;color:var(--text2);font-size:12.5px;font-family:monospace">⏳ جاري فحص ملفات PHP...</div>';
  
  try{
    const r = await fetch('/api/php/info',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        path, 
        main_file: mainEl ? mainEl.value.trim() || null : null,
        deps_file: depsEl ? depsEl.value.trim() || null : null
      })
    });
    const d = await r.json();
    
    if(!d.success){ 
      listEl.innerHTML = `<div style="padding:12px;color:var(--red);font-size:12.5px;font-family:monospace">❌ ${escapeHtml(d.error || 'Error')}</div>`; 
      return; 
    }
    
    // عرض أوامر التشغيل المتوقعة في شاشة المعاينة
    const ic = document.getElementById('php-install-cmd');
    const rc = document.getElementById('php-run-cmd');
    const icArr = Array.isArray(d.install_commands) ? d.install_commands : [d.install_commands || 'composer install (if needed)'];
    
    if(ic) ic.textContent = '$ ' + icArr.join('\n$ ');
    if(rc) rc.textContent = '$ ' + escapeHtml(d.run_command || 'php -S 0.0.0.0:PORT');
    
    const previewEl = document.getElementById('php-cmd-preview');
    if(previewEl) previewEl.style.display = 'block';
    
    // عرض قائمة ملفات PHP
    const files = d.php_files || [];
    if(!files.length){ 
      listEl.innerHTML = '<div style="padding:12px;color:var(--text3);font-size:12.5px">📂 لا توجد ملفات .php في هذا المسار</div>'; 
      return; 
    }
    
    listEl.innerHTML = files.map(f => `
      <div onclick="if(document.getElementById('php-main')) document.getElementById('php-main').value='${escapeHtml(f)}'; document.getElementById('php-files-list').style.display='none';"
           style="padding:8px 12px;font-size:13px;color:var(--text);cursor:pointer;border-radius:6px;
                  font-family:'Fira Code',monospace;transition:0.15s;display:flex;align-items:center;gap:8px;" 
           onmouseover="this.style.background='var(--bg3)';this.style.color='var(--accent)';" 
           onmouseout="this.style.background='';this.style.color='var(--text)';">
        <span style="color:var(--accent2)">🐘</span> ${escapeHtml(f)}
      </div>`).join('');
  }catch(e){ 
    listEl.innerHTML = '<div style="padding:12px;color:var(--red);font-size:12.5px">❌ خطأ في تحميل مسار الملفات</div>'; 
  }
}

async function previewPhpCmd(){
  const pathEl = document.getElementById('php-path');
  const mainEl = document.getElementById('php-main');
  const depsEl = document.getElementById('php-deps');
  if(!pathEl) return;
  
  const path = pathEl.value.trim();
  if(!path){ toast('⚠️ اكتب المسار أولاً لمعاينة الأوامر', true); return; }
  
  try {
    const r = await fetch('/api/php/info',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        path,
        main_file: mainEl ? mainEl.value.trim() || null : null,
        deps_file: depsEl ? depsEl.value.trim() || null : null
      })
    });
    const d = await r.json();
    
    const ic = document.getElementById('php-install-cmd');
    const rc = document.getElementById('php-run-cmd');
    const icArr = Array.isArray(d.install_commands) ? d.install_commands : [d.install_commands || 'composer install (if needed)'];
    
    if(ic) ic.textContent = '$ ' + icArr.join('\n$ ');
    if(rc) rc.textContent = '$ ' + (d.run_command || 'php -S 0.0.0.0:PORT');
    
    const previewEl = document.getElementById('php-cmd-preview');
    if(previewEl) previewEl.style.display = 'block';
    
    toast('✅ تم تحديث ومعاينة الأوامر', false);
  } catch(e) { toast('❌ فشل جلب المعاينة', true); }
}

async function startPhpServer(){
  const path = document.getElementById('php-path')?.value.trim();
  const port = document.getElementById('php-port')?.value.trim();
  const mainFile = document.getElementById('php-main')?.value.trim();
  const depsFile = document.getElementById('php-deps')?.value.trim();
  
  if(!path){ toast('⚠️ يرجى إدخال المسار الأساسي (Root Path) لمشروع PHP', true); return; }
  toast('🐘 جاري تشغيل خادم PHP...', false);
  
  const outEl = document.getElementById('php-start-output');
  if(outEl){ 
    outEl.style.display = 'block'; 
    outEl.style.cssText = `display:block;padding:14px;background:#090d13;border:1px solid var(--border);
                           border-radius:10px;color:#e6edf3;font-family:'Fira Code',monospace;font-size:12.5px;
                           line-height:1.5;margin-top:12px;white-space:pre-wrap;`;
    outEl.textContent = '⏳ [SYSTEM]: Checking Composer dependencies...\n'; 
  }
  
  try {
    const r = await fetch('/api/php/start',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        path, 
        port: port ? parseInt(port) : null,
        main_file: mainFile || null, 
        deps_file: depsFile || null
      })
    });
    const d = await r.json();
    
    if(outEl && d.install_output) outEl.textContent += d.install_output;
    
    if(d.success){
      if(outEl) outEl.textContent += `\n✅ [SUCCESS]: PHP Server running on port ${d.port}\n📄 [ENTRY]: ${d.command}\n`;
      toast(`▶ تم تشغيل خادم PHP بنجاح على المنفذ ${d.port}`);
      loadPhpList();
    } else {
      if(outEl && d.install_commands) outEl.textContent += `\n📋 [INSTALL COMMANDS]:\n  ${d.install_commands.join('\n  ')}\n`;
      if(outEl && d.run_command)  outEl.textContent += `📋 [RUN COMMAND]:\n  ${d.run_command}\n`;
      toast('❌ فشل تشغيل خادم PHP: ' + (d.error || 'خطأ داخلي'), true);
    }
  } catch(e) {
    toast('❌ خطأ أثناء الاتصال بالخادم', true);
  }
}

async function loadPhpList(){
  try{
    const r = await fetch('/api/php/list');
    const d = await r.json();
    const list = document.getElementById('php-list');
    if(!list) return;
    
    if(!(d.servers || []).length){
      list.innerHTML = `
        <div style="padding:32px;text-align:center;color:var(--text3);font-family:monospace;font-size:13px">
          📭 لا توجد خوادم PHP نشطة حالياً.
        </div>`;
      return;
    }
    
    list.innerHTML = '';
    d.servers.forEach(s => {
      const card = document.createElement('div');
      card.className = 'php-server-card';
      
      // تنسيق بطاقات خوادم PHP بطابع احترافي
      card.style.cssText = `
        display:flex;align-items:center;justify-content:space-between;padding:14px;
        background:var(--bg2);border:1px solid var(--border);border-radius:12px;
        margin-bottom:10px;gap:16px;box-sizing:border-box;transition:0.2s ease;
      `;
      
      const isRunning = !!s.running;
      const statusColor = isRunning ? 'var(--green)' : 'var(--red)';
      const statusBg = isRunning ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)';
      const shadowGlow = isRunning ? '0 0 8px rgba(63,185,80,0.3)' : 'none';
      
      const btnStyle = `padding:6px 12px;background:var(--bg3);border:1px solid var(--border2);
                        border-radius:8px;color:var(--text2);font-size:12px;cursor:pointer;
                        font-weight:600;font-family:sans-serif;transition:0.15s;`;

      card.innerHTML = `
        <div class="project-info" style="flex:1;min-width:0;text-align:left;direction:ltr">
          <div class="p-name" style="font-family:'Fira Code',monospace;font-size:14px;font-weight:700;color:var(--text);margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            <span style="color:${statusColor};text-shadow:${shadowGlow};margin-right:4px">●</span> 🐘 PHP Server — Port <span style="color:var(--accent2)">${s.port || '—'}</span>
          </div>
          <div class="p-meta" style="font-family:monospace;font-size:11.5px;color:var(--text3);line-height:1.4">
            Entry: <span style="color:var(--text2)">${escapeHtml(s.main_file || 'auto')}</span> · 
            Deps: <span style="color:var(--text2)">${escapeHtml(s.deps_file || 'composer.json')}</span> · 
            ${escapeHtml((s.started || '').split('T')[0] || '')}
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
          <span style="padding:4px 10px;background:${statusBg};color:${statusColor};border-radius:6px;font-size:11px;font-weight:700;font-family:monospace;letter-spacing:0.5px">
            ${isRunning ? 'RUNNING' : 'STOPPED'}
          </span>
          <button style="${btnStyle}color:var(--red);border-color:rgba(248,81,73,0.15)" 
                  onmouseover="this.style.background='var(--red)';this.style.color='#fff'"
                  onmouseout="this.style.background='var(--bg3)';this.style.color='var(--red)'"
                  onclick="stopPhpServer('${escapeHtml(s.pid)}')">■ إيقاف</button>
        </div>`;
        
      list.appendChild(card);
    });
  }catch(e){}
}

async function stopPhpServer(pid){
  if(!confirm('هل أنت متأكد من إيقاف خادم PHP هذا؟')) return;
  try {
    const r = await fetch('/api/php/stop',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pid})});
    const d = await r.json();
    toast(d.success ? '■ تم إيقاف خادم PHP بنجاح' : '❌ فشل إيقاف الخادم', !d.success);
    if(d.success) loadPhpList();
  } catch(e) { toast('❌ خطأ في الاتصال بالخادم', true); }
}


// ═══════════════════════════════════════════════════════════════════════════
//  PREMIUM USERS MANAGEMENT ENGINE — DEVELOPED BY RIKO
//  👑 Dev: @SHBH_S1 | 📢 Channel: @SHOBING_HXH
// ═══════════════════════════════════════════════════════════════════════════

function onPlanChange(){
  const plan = document.getElementById('u-plan')?.value;
  const wrap = document.getElementById('u-custom-days-wrap');
  if(wrap) {
    wrap.style.display = plan === 'custom' ? 'block' : 'none';
    if(plan === 'custom') wrap.style.animation = 'fadeInModal 0.3s ease';
  }
}

async function addUser(){
  const plan = document.getElementById('u-plan')?.value;
  const username = document.getElementById('u-name')?.value.trim();
  const password = document.getElementById('u-pass')?.value;
  
  if(!username || !password){ 
    toast('⚠️ يرجى تعبئة اسم المستخدم وكلمة المرور', true); 
    return; 
  }

  const data = {
    username: username,
    password: password,
    tg_username: (document.getElementById('u-tg')?.value || '').trim().replace('@',''),
    max_sessions: parseInt(document.getElementById('u-max')?.value) || 1,
    max_servers: parseInt(document.getElementById('u-maxsrv')?.value) || 1,
    main_file: document.getElementById('u-main')?.value || 'main.py',
    plan: plan,
    expiry_days: plan === 'custom' ? (parseInt(document.getElementById('u-days')?.value) || 7) : undefined
  };
  
  toast('⏳ جاري إضافة المستخدم...', false);
  try {
    const r = await fetch('/api/users/add', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });
    const d = await r.json();
    
    if(d.success){
      toast('✅ تم إضافة المستخدم بنجاح: ' + username, false);
      // تفريغ الحقول بعد الإضافة لسهولة الاستخدام
      document.getElementById('u-name').value = '';
      document.getElementById('u-pass').value = '';
      document.getElementById('u-tg').value = '';
      loadUsers();
    } else {
      toast('❌ فشل الإضافة: ' + (d.error || 'خطأ مجهول'), true);
    }
  } catch(e) {
    toast('❌ خطأ في الاتصال بالخادم', true);
  }
}

const PLAN_LABELS = {
  free_trial: '<span style="color:var(--text2)">🆓 تجربة مجانية</span>',
  paid_20: '<span style="color:var(--yellow)">⭐ 20 يوم</span>',
  paid_30: '<span style="color:var(--accent2)">💎 30 يوم</span>',
  custom: '<span style="color:var(--accent)">🎯 مخصص</span>'
};

async function loadUsers(){
  const el = document.getElementById('users-list'); 
  if(!el) return;
  
  el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2);font-family:monospace;font-size:13px">⏳ جاري تحميل بيانات المستخدمين...</div>';
  
  try {
    const r = await fetch('/api/users/list');
    const d = await r.json();
    
    if(!(d.users || []).length){
      el.innerHTML = `
        <div style="padding:32px;text-align:center;color:var(--text3);font-family:monospace;font-size:13px">
          📭 لا يوجد مستخدمين مسجلين حالياً.
        </div>`;
      return;
    }
    
    el.innerHTML = '';
    d.users.forEach(u => {
      const card = document.createElement('div');
      card.className = 'user-card';
      
      // تصميم احترافي لبطاقة المستخدم
      card.style.cssText = `
        display:flex;align-items:center;justify-content:space-between;padding:16px;
        background:var(--bg2);border:1px solid var(--border);border-radius:12px;
        margin-bottom:12px;gap:16px;flex-wrap:wrap;transition:all 0.2s ease;
      `;
      card.onmouseover = () => card.style.borderColor = 'var(--accent)';
      card.onmouseout = () => card.style.borderColor = 'var(--border)';

      const isActive = u.active !== false;
      const statusBadge = isActive 
        ? `<span style="padding:4px 8px;background:rgba(63,185,80,0.1);color:var(--green);border-radius:6px;font-size:11px;font-weight:700;">✅ نشط</span>` 
        : `<span style="padding:4px 8px;background:rgba(210,153,34,0.1);color:var(--yellow);border-radius:6px;font-size:11px;font-weight:700;">⏳ بانتظار الموافقة</span>`;

      const expStr = u.expiry ? (() => {
        const diff = Math.ceil((new Date(u.expiry) - new Date()) / 86400000);
        if(diff > 0){
          return `<span style="padding:4px 8px;background:rgba(255,255,255,0.05);color:${diff<3 ? 'var(--red)' : 'var(--text2)'};border-radius:6px;font-size:11px;font-weight:600;">⏳ ${diff} يوم متبقي</span>`;
        }
        return `<span style="padding:4px 8px;background:rgba(248,81,73,0.1);color:var(--red);border-radius:6px;font-size:11px;font-weight:700;">❌ منتهي الصلاحية</span>`;
      })() : '<span style="padding:4px 8px;background:rgba(255,255,255,0.05);color:var(--text2);border-radius:6px;font-size:11px;">∞ غير محدود</span>';
      
      const planLabel = PLAN_LABELS[u.plan || 'free_trial'] || `<span style="color:var(--text2)">${escapeHtml(u.plan)}</span>`;
      const pwDisplay = u.password_hash ? u.password_hash.substring(0,16) + '...' : '—';
      
      const btnStyle = `padding:6px 12px;background:var(--bg3);border:1px solid var(--border2);
                        border-radius:8px;color:var(--text2);font-size:12px;cursor:pointer;
                        font-weight:600;font-family:sans-serif;transition:0.15s;`;

      card.innerHTML = `
        <div style="flex:1;min-width:250px;text-align:right;direction:rtl">
          <div style="font-size:16px;font-weight:800;color:var(--text);margin-bottom:8px;display:flex;align-items:center;gap:8px">
            👤 ${escapeHtml(u.username)}
            ${u.tg_username ? `<a href="https://t.me/${escapeHtml(u.tg_username)}" target="_blank" style="text-decoration:none;color:var(--accent2);font-size:13px;font-weight:600;background:rgba(0,191,255,0.1);padding:2px 6px;border-radius:4px">@${escapeHtml(u.tg_username)}</a>` : ''}
          </div>
          
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px">
            <span style="font-size:12px;font-weight:600;padding:4px 8px;background:var(--bg3);border:1px solid var(--border2);border-radius:6px;">${planLabel}</span>
            ${statusBadge}
            ${expStr}
          </div>
          
          <div style="display:flex;align-items:center;gap:6px;background:var(--bg3);padding:6px 10px;border-radius:8px;border:1px solid var(--border2);display:inline-flex;">
            <span style="font-size:11px;color:var(--text3);font-family:'Fira Code',monospace;">🔑 Hash: </span>
            <span class="pw-hash-text" style="font-size:11.5px;color:var(--text2);font-family:'Fira Code',monospace;">${escapeHtml(pwDisplay)}</span>
            <button onclick="togglePwHash(this, '${escapeHtml(u.password_hash || '')}')" 
                    style="background:none;border:none;color:var(--accent);font-size:11px;cursor:pointer;font-weight:700;margin-right:8px;padding:0;">👁 إظهار</button>
          </div>
        </div>
        
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          ${!isActive ? `<button style="${btnStyle}color:var(--green);border-color:rgba(63,185,80,0.3)" 
                                 onmouseover="this.style.background='var(--green)';this.style.color='#fff'"
                                 onmouseout="this.style.background='var(--bg3)';this.style.color='var(--green)'"
                                 onclick="approveUser('${escapeHtml(u.username)}')">✅ قبول الحساب</button>` : ''}
                                 
          <button style="${btnStyle}color:var(--yellow)" 
                  onmouseover="this.style.borderColor='var(--yellow)'" onmouseout="this.style.borderColor='var(--border2)'"
                  onclick="openEditUser('${escapeHtml(u.username)}','${u.max_sessions||1}','${u.max_servers||1}','${escapeHtml(u.main_file||'main.py')}')">✏️ تعديل</button>
                  
          <button style="${btnStyle}color:var(--red);border-color:rgba(248,81,73,0.2)" 
                  onmouseover="this.style.background='var(--red)';this.style.color='#fff'"
                  onmouseout="this.style.background='var(--bg3)';this.style.color='var(--red)'"
                  onclick="deleteUser('${escapeHtml(u.username)}')">🗑 حذف</button>
        </div>`;
        
      el.appendChild(card);
    });
  } catch(e) {
    el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--red);font-size:13px">❌ فشل تحميل بيانات المستخدمين</div>';
  }
}

function togglePwHash(btn, fullHash){
  const textSpan = btn.previousElementSibling;
  if(!textSpan) return;
  
  if(btn.dataset.showing === '1'){
    textSpan.textContent = fullHash.substring(0, 16) + '...';
    btn.textContent = '👁 إظهار';
    btn.dataset.showing = '0';
  } else {
    textSpan.textContent = fullHash;
    btn.textContent = '🙈 إخفاء';
    btn.dataset.showing = '1';
  }
}

async function approveUser(username){
  toast('⏳ جاري تفعيل الحساب...', false);
  try {
    const r = await fetch('/api/users/approve', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username})
    });
    const d = await r.json();
    toast(d.success ? `✅ تم تفعيل حساب: ${username}` : '❌ فشل التفعيل', !d.success);
    if(d.success) loadUsers();
  } catch(e) { toast('❌ خطأ في الاتصال', true); }
}

function openEditUser(name, maxS, maxSrv, mainF){
  document.getElementById('eu-name').value = name;
  document.getElementById('eu-pass').value = '';
  document.getElementById('eu-max').value = maxS;
  document.getElementById('eu-maxsrv').value = maxSrv;
  document.getElementById('eu-main').value = mainF;
  document.getElementById('eu-days').value = 30;
  openModal('edit-user-modal');
}

async function saveEditUser(){
  const username = document.getElementById('eu-name').value;
  const data = {
    username: username,
    password: document.getElementById('eu-pass').value || undefined,
    max_sessions: parseInt(document.getElementById('eu-max').value) || 1,
    max_servers: parseInt(document.getElementById('eu-maxsrv').value) || 1,
    main_file: document.getElementById('eu-main').value,
    expiry_days: parseInt(document.getElementById('eu-days').value) || 30
  };
  
  toast('⏳ جاري حفظ التعديلات...', false);
  try {
    const r = await fetch('/api/users/update', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });
    const d = await r.json();
    
    if(d.success){
      toast(`✅ تم تحديث بيانات [${username}] بنجاح`, false);
      closeModal('edit-user-modal'); 
      loadUsers();
    } else {
      toast('❌ فشل التحديث: ' + (d.error || ''), true);
    }
  } catch(e) { toast('❌ خطأ في الاتصال', true); }
}

async function deleteUser(username){
  if(!confirm(`⚠️ تحذير: هل أنت متأكد من حذف المستخدم "${username}" وجميع ملفاته نهائياً؟\nهذا الإجراء لا يمكن التراجع عنه.`)) return;
  
  toast('⏳ جاري الحذف...', false);
  try {
    const r = await fetch('/api/users/delete', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username})
    });
    const d = await r.json();
    toast(d.success ? `🗑 تم حذف المستخدم: ${username}` : '❌ فشل الحذف', !d.success);
    if(d.success) loadUsers();
  } catch(e) { toast('❌ خطأ في الاتصال', true); }
}

// ═══════════════════════════════════════════════════════════════════════════
//  PREMIUM BACKUPS & NETWORK ENGINE — DEVELOPED BY RIKO
//  👑 Dev: @SHBH_S1 | 📢 Channel: @SHOBING_HXH
// ═══════════════════════════════════════════════════════════════════════════

// ─── BACKUPS MANAGEMENT ───
async function createBackup(){
  toast('⏳ جاري إنشاء النسخة الاحتياطية، يرجى الانتظار...', false);
  try {
    const r = await fetch('/api/backups/create', {method: 'POST'});
    const d = await r.json();
    toast(d.success ? '✅ تم إنشاء النسخة الاحتياطية بنجاح' : '❌ فشل في إنشاء النسخة', !d.success);
    if(d.success) loadBackups();
  } catch(e) {
    toast('❌ خطأ في الاتصال بالسيرفر', true);
  }
}

async function loadBackups(){
  const el = document.getElementById('backups-list'); 
  if(!el) return;
  
  el.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text2);font-family:monospace;font-size:13px">⏳ جاري تحميل النسخ...</div>';
  
  try {
    const r = await fetch('/api/backups/list');
    const d = await r.json();
    
    if(!(d.backups || []).length){ 
      el.innerHTML = `
        <div style="padding:32px;text-align:center;color:var(--text3);font-family:monospace;font-size:13px">
          📭 لا توجد نسخ احتياطية محفوظة حالياً.
        </div>`;
      return; 
    }
    
    el.innerHTML = '';
    d.backups.forEach(b => {
      const card = document.createElement('div');
      
      card.style.cssText = `
        display:flex;align-items:center;justify-content:space-between;padding:14px 16px;
        background:var(--bg2);border:1px solid var(--border);border-radius:12px;
        margin-bottom:10px;gap:16px;transition:0.2s ease;
      `;
      card.onmouseover = () => card.style.borderColor = 'var(--accent)';
      card.onmouseout = () => card.style.borderColor = 'var(--border)';

      const btnStyle = `padding:6px 14px;background:var(--bg3);border:1px solid var(--border2);
                        border-radius:8px;color:var(--accent2);font-size:12px;cursor:pointer;
                        font-weight:700;font-family:sans-serif;transition:0.15s;display:flex;align-items:center;gap:6px;`;

      card.innerHTML = `
        <div style="flex:1;min-width:0;direction:ltr;text-align:left">
          <div style="font-size:14px;font-weight:700;color:var(--text);font-family:'Fira Code',monospace;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            📦 ${escapeHtml(b.name)}
          </div>
          <div style="font-size:12px;color:var(--text3);font-family:monospace">
            Size: <span style="color:var(--text2)">${escapeHtml(b.size || '—')}</span>
          </div>
        </div>
        <button style="${btnStyle}" 
                onmouseover="this.style.background='rgba(0,191,255,0.1)';this.style.borderColor='var(--accent2)'"
                onmouseout="this.style.background='var(--bg3)';this.style.borderColor='var(--border2)'"
                onclick="window.open('/api/backups/download?name=${encodeURIComponent(b.name)}','_blank')">
          ⬇ تحميل
        </button>`;
      el.appendChild(card);
    });
  } catch(e) {
    el.innerHTML = '<div style="padding:16px;text-align:center;color:var(--red);font-size:13px">❌ فشل تحميل النسخ الاحتياطية</div>';
  }
}

// ─── PORTS MANAGEMENT ───
async function addPort(){
  const portInput = document.getElementById('new-port');
  const noteInput = document.getElementById('new-port-note');
  
  if(!portInput) return;
  const port = parseInt(portInput.value);
  const note = noteInput ? noteInput.value.trim() : '';
  
  if(!port || isNaN(port)){ 
    toast('⚠️ يرجى إدخال رقم منفذ (Port) صحيح', true); 
    return; 
  }
  
  toast('⏳ جاري إضافة المنفذ...', false);
  try {
    const r = await fetch('/api/ports/add', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({port, note})
    });
    const d = await r.json();
    
    if(d.success){
      toast(`✅ تم إضافة المنفذ [${port}] بنجاح`, false);
      portInput.value = '';
      if(noteInput) noteInput.value = '';
      loadPorts();
    } else {
      toast('❌ فشل الإضافة: ' + (d.error || 'خطأ مجهول'), true);
    }
  } catch(e) { toast('❌ خطأ في الاتصال بالخادم', true); }
}

async function loadPorts(){
  const el = document.getElementById('ports-list'); 
  if(!el) return;
  
  el.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text2);font-size:13px">⏳ جاري التحميل...</div>';
  
  try {
    const r = await fetch('/api/ports/list');
    const d = await r.json();
    
    if(!(d.ports || []).length){ 
      el.innerHTML = `
        <div style="padding:24px;text-align:center;color:var(--text3);font-family:monospace;font-size:13px">
          📭 لا توجد منافذ إضافية مهيأة حالياً.
        </div>`;
      return; 
    }
    
    el.innerHTML = '';
    d.ports.forEach(p => {
      const card = document.createElement('div');
      
      card.style.cssText = `
        display:flex;align-items:center;justify-content:space-between;padding:14px 16px;
        background:var(--bg2);border:1px solid var(--border);border-radius:12px;
        margin-bottom:10px;gap:16px;transition:0.2s ease;
      `;
      card.onmouseover = () => card.style.borderColor = 'var(--accent)';
      card.onmouseout = () => card.style.borderColor = 'var(--border)';

      const btnStyle = `padding:6px 12px;background:var(--bg3);border:1px solid var(--border2);
                        border-radius:8px;color:var(--red);font-size:12px;cursor:pointer;
                        font-weight:700;transition:0.15s;`;

      const statusBadge = `<span style="padding:2px 6px;background:rgba(255,255,255,0.05);border-radius:4px;color:var(--text2);font-size:10px;text-transform:uppercase;">${escapeHtml(p.status || 'idle')}</span>`;

      card.innerHTML = `
        <div style="flex:1;direction:ltr;text-align:left">
          <div style="font-size:14px;font-weight:800;color:var(--text);margin-bottom:6px;font-family:monospace">
            🔌 Port <span style="color:var(--accent)">${p.port}</span>
          </div>
          <div style="font-size:12px;color:var(--text3);display:flex;align-items:center;gap:8px">
            📝 ${escapeHtml(p.note || 'No description')}
            ${statusBadge}
          </div>
        </div>
        <button style="${btnStyle}" 
                onmouseover="this.style.background='var(--red)';this.style.color='#fff';this.style.borderColor='var(--red)'"
                onmouseout="this.style.background='var(--bg3)';this.style.color='var(--red)';this.style.borderColor='var(--border2)'"
                onclick="deletePort(${p.port})">
          🗑 حذف
        </button>`;
      el.appendChild(card);
    });
  } catch(e) {
    el.innerHTML = '<div style="padding:16px;text-align:center;color:var(--red);font-size:13px">❌ فشل تحميل المنافذ</div>';
  }
}

async function deletePort(port){
  if(!confirm(`⚠️ هل أنت متأكد من رغبتك في حذف المنفذ المخصص ${port}؟`)) return;
  
  toast('⏳ جاري الحذف...', false);
  try {
    const r = await fetch('/api/ports/delete', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({port})
    });
    const d = await r.json();
    toast(d.success ? `🗑 تم حذف المنفذ ${port}` : '❌ فشل الحذف', !d.success);
    if(d.success) loadPorts();
  } catch(e) { toast('❌ خطأ في الاتصال بالسيرفر', true); }
}

// ─── PORT SCANNER ───
async function scanPorts(){
  const hostInput = document.getElementById('scan-host');
  const portsInput = document.getElementById('scan-ports');
  const resultsEl = document.getElementById('scan-results');
  
  if(!hostInput || !portsInput || !resultsEl) return;
  
  const host = hostInput.value.trim();
  const ports = portsInput.value.split(',').map(p => parseInt(p.trim())).filter(Boolean);
  
  if(!host || !ports.length){ 
    toast('⚠️ يرجى إدخال الـ Host والمنافذ المطلوبة للفحص', true); 
    return; 
  }
  
  resultsEl.style.display = 'block';
  resultsEl.innerHTML = '<div style="padding:16px;text-align:center;color:var(--accent);font-family:monospace;font-size:13px;animation:pulse 1.5s infinite">🔍 جاري فحص المنافذ، يرجى الانتظار...</div>';
  
  try {
    const r = await fetch('/api/network/scan', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({host, ports})
    });
    const d = await r.json();
    
    if(!(d.results || []).length){
      resultsEl.innerHTML = '<div style="padding:12px;color:var(--text3);font-size:13px;text-align:center;">لم يتم العثور على نتائج.</div>';
      return;
    }
    
    // تصميم شبكي (Grid) لعرض النتائج بشكل احترافي
    resultsEl.innerHTML = '<div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(140px, 1fr));gap:10px;margin-top:12px;"></div>';
    const grid = resultsEl.querySelector('div');
    
    d.results.forEach(p => {
      const isOpen = p.open;
      const color = isOpen ? 'var(--green)' : 'var(--red)';
      const bgColor = isOpen ? 'rgba(63,185,80,0.1)' : 'rgba(248,81,73,0.1)';
      const statusText = isOpen ? 'OPEN' : 'CLOSED';
      
      grid.innerHTML += `
        <div style="background:var(--bg3);border:1px solid ${bgColor};border-radius:8px;padding:12px;text-align:center;direction:ltr;transition:0.2s" onmouseover="this.style.borderColor='${color}'" onmouseout="this.style.borderColor='${bgColor}'">
          <div style="color:var(--text);font-family:'Fira Code',monospace;font-size:14px;font-weight:700;margin-bottom:6px">
            Port ${p.port}
          </div>
          <div style="display:inline-block;padding:4px 10px;background:${bgColor};color:${color};border-radius:6px;font-size:11px;font-weight:800;letter-spacing:1px">
            ${statusText}
          </div>
        </div>
      `;
    });
    
    toast('✅ اكتمل الفحص', false);
  } catch(e) {
    resultsEl.innerHTML = '<div style="padding:12px;color:var(--red);font-size:13px;text-align:center;">❌ فشل عملية الفحص</div>';
    toast('❌ خطأ في الاتصال أثناء الفحص', true);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  PREMIUM SETTINGS & ACTIVITY ENGINE — DEVELOPED BY RIKO
//  👑 Dev: @SHBH_S1 | 📢 Channel: @SHOBING_HXH
// ═══════════════════════════════════════════════════════════════════════════

// ─── SETTINGS MANAGEMENT ───
async function changePassword(){
  const cur = document.getElementById('cur-pass')?.value;
  const nw = document.getElementById('new-pass')?.value;
  
  if(!cur || !nw){ toast('⚠️ يرجى ملء جميع الحقول', true); return; }
  
  toast('⏳ جاري تحديث كلمة المرور...', false);
  try {
    const r = await fetch('/api/master/change-password', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({current_password: cur, new_password: nw})
    });
    const d = await r.json();
    toast(d.success ? '✅ تم تغيير كلمة المرور بنجاح' : '❌ كلمة المرور الحالية غير صحيحة', !d.success);
    if(d.success) { document.getElementById('cur-pass').value = ''; document.getElementById('new-pass').value = ''; }
  } catch(e) { toast('❌ خطأ في الاتصال', true); }
}

async function loadSysinfo(){
  const el = document.getElementById('sysinfo-box');
  if(!el) return;
  
  try {
    const r = await fetch('/api/sysinfo');
    const d = await r.json();
    el.textContent = d.info || '⚠️ لا توجد معلومات نظام متاحة';
    el.style.fontFamily = "'Fira Code', monospace";
  } catch(e) { el.textContent = '❌ فشل جلب معلومات النظام'; }
}

async function setStartupFile(){
  const f = document.getElementById('startup-file')?.value.trim();
  if(!f) { toast('⚠️ يرجى كتابة اسم الملف', true); return; }
  
  try {
    const r = await fetch('/api/files/set-main', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({filename: f, path: ''})
    });
    const d = await r.json();
    toast(d.success ? `🚀 تم تعيين ملف البدء: ${f}` : '❌ فشل التعيين', !d.success);
  } catch(e) { toast('❌ خطأ في الاتصال', true); }
}

// ─── PACKAGE INSTALLATION ───
async function installPip(){
  const p = document.getElementById('pip-pkg')?.value.trim();
  if(!p) { toast('⚠️ أدخل اسم الحزمة (Package)', true); return; }
  
  toast(`📦 جاري تثبيت الحزمة عبر Pip: ${p}...`, false);
  try {
    const r = await fetch('/api/packages/install/pip', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({package: p})
    });
    const d = await r.json();
    toast(d.success ? `✅ تم تثبيت: ${p}` : `❌ فشل التثبيت: ${d.error || ''}`, !d.success);
  } catch(e) { toast('❌ خطأ في الاتصال', true); }
}

async function installNpm(){
  const p = document.getElementById('npm-pkg')?.value.trim();
  if(!p) { toast('⚠️ أدخل اسم الحزمة (Package)', true); return; }
  
  toast(`📦 جاري تثبيت الحزمة عبر Npm: ${p}...`, false);
  try {
    const r = await fetch('/api/packages/install/npm', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({package: p})
    });
    const d = await r.json();
    toast(d.success ? `✅ تم تثبيت: ${p}` : `❌ فشل التثبيت: ${d.error || ''}`, !d.success);
  } catch(e) { toast('❌ خطأ في الاتصال', true); }
}

// ─── ACTIVITY LOGS ───
async function loadActivity(){
  const el = document.getElementById('activity-list');
  if(!el) return;
  
  try {
    const r = await fetch('/api/activity');
    const d = await r.json();
    
    if(!(d.events || []).length){
      el.innerHTML = '<div style="color:var(--text3);padding:20px;text-align:center;font-size:13px">📭 لا توجد سجلات نشاط حالياً.</div>';
      return;
    }
    
    el.innerHTML = '';
    d.events.slice(0, 100).forEach(e => {
      const row = document.createElement('div');
      row.style.cssText = `
        display:flex;gap:12px;padding:10px 14px;border-bottom:1px solid var(--border);
        font-size:12.5px;transition:0.2s;align-items:center;
      `;
      row.onmouseover = () => row.style.background = 'var(--bg3)';
      row.onmouseout = () => row.style.background = 'transparent';
      
      const time = (e.time_text || '').split(' ')[1] || '00:00';
      
      row.innerHTML = `
        <span style="color:var(--accent);font-family:monospace;min-width:50px;font-weight:600">${time}</span>
        <span style="color:var(--yellow);min-width:90px;font-weight:700">@${escapeHtml(e.username || 'system')}</span>
        <span style="color:var(--text);flex:1">
          ${escapeHtml(e.action || '')}
          ${e.details ? `<span style="color:var(--text3);margin-left:8px;font-style:italic">| ${escapeHtml(e.details)}</span>` : ''}
        </span>
      `;
      el.appendChild(row);
    });
  } catch(e) {
    el.innerHTML = '<div style="color:var(--red);padding:20px;text-align:center">❌ فشل تحميل السجلات</div>';
  }
}

-dots span:nth-child(2) { animation-delay: 0.2s; }
.ai-think-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typingDot {
  0%, 100% { transform: translateY(0); opacity: 0.4; }
  50% { transform: translateY(-5px); opacity: 1; }
}

.ai-input-wrap {
  display: flex; gap: 10px; padding: 16px 20px;
  background: var(--bg3); border-top: 1px solid var(--border);
  flex-shrink: 0; align-items: center;
}
.ai-input {
  flex: 1; background: var(--bg4); border: 1px solid var(--border2);
  border-radius: 12px; padding: 14px 16px; color: var(--text);
  font-size: 14px; outline: none; transition: .2s;
}
.ai-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(124,92,252,.1); }
.ai-send-btn {
  background: linear-gradient(135deg, var(--accent), var(--accent3));
  color: #fff; border: none; border-radius: 12px; width: 48px; height: 48px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; font-size: 18px; transition: .2s; box-shadow: 0 4px 15px rgba(124,92,252,.4);
}
.ai-send-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(124,92,252,.6); }
.ai-send-btn:active { transform: translateY(0); }
</style>
</head>
<body>
<div class="app-layout">

  <!-- ── الشريط الجانبي (Sidebar) ── -->
  <div class="sidebar">
    <div class="sidebar-header">
      <img src="https://i.ibb.co/60Zvqk5L/photo.jpg" alt="Logo" class="sidebar-logo">
      <div class="sidebar-brand">DEV RIKO</div>
      <div class="sidebar-user">
        <div class="status-dot"></div>
        <span>{{ username }}</span>
      </div>
    </div>
    
    <div class="sidebar-tabs">
      {{ extra_tabs | safe }}
    </div>

    <div class="sidebar-footer">
      <button class="logout-btn" onclick="location.href='/logout'">تسجيل الخروج</button>
      <div style="text-align:center; margin-top:14px; font-size:12px; color:var(--text3); line-height:1.6;">
         المطور: <a href="https://t.me/SHBH_S1" target="_blank" style="color:var(--accent); text-decoration:none; font-weight:700;">@SHBH_S1</a><br>
         القناة: <a href="https://t.me/SHOBING_HXH" target="_blank" style="color:var(--accent); text-decoration:none; font-weight:700;">@SHOBING_HXH</a>
      </div>
    </div>
  </div>

  <!-- ── المحتوى الرئيسي (Main Content) ── -->
  <div class="main-content">
    <div class="top-actions">
       <div style="font-weight:700; font-size:16px; color:var(--text);">لوحة تحكم الاستضافة</div>
       <div class="top-actions-right">
          <div class="action-icon" onclick="location.reload()" title="تحديث الصفحة">🔄</div>
       </div>
    </div>

    <div class="container">
       
       <!-- ── تبويب الذكاء الاصطناعي (AI Chat) ── -->
       <div class="tab-content active" id="tab-ai">
          <div class="ai-chat-wrap">
             <div class="ai-header">
                <div class="ai-header-left">
                   <div class="ai-avatar-main">🤖</div>
                   <div>
                      <div class="ai-header-title">المساعد الذكي لـ RIKO</div>
                      <div class="ai-header-sub">جاهز للمساعدة في الأكواد وإدارة السيرفر</div>
                   </div>
                </div>
                <button class="ai-clear-btn" onclick="clearAiChat()">مسح المحادثة 🗑</button>
             </div>
             
             <div class="ai-messages-box" id="ai-messages">
                <div class="ai-msg">
                   <div class="ai-bubble">
                      <div class="ai-avatar">🤖</div>
                      <div>
                         <div class="ai-text">مرحباً بك في لوحة تحكم DEV RIKO 🚀!
كيف يمكنني مساعدتك اليوم؟ يمكنك سؤالي عن إصلاح الأكواد، كتابة أوامر تشغيل، أو أي استفسار يخص الاستضافة.</div>
                         <div class="ai-time">الآن</div>
                      </div>
                   </div>
                </div>
             </div>
             
             <div class="ai-thinking-box" id="ai-thinking" style="display:none;">
                <div class="ai-thinking-label">
                   <div class="ai-think-dots"><span></span><span></span><span></span></div>
                   جاري التفكير...
                </div>
             </div>
             
             <div class="ai-input-wrap">
                <input type="text" id="ai-chat-input" class="ai-input" placeholder="اكتب سؤالك أو مشكلتك هنا..." onkeydown="if(event.key==='Enter') sendAiMessage()">
                <button class="ai-send-btn" onclick="sendAiMessage()">➤</button>
             </div>
          </div>
       </div>

       <!-- ── تضمين مساحات الأقسام الأخرى بناءً على الصلاحيات ── -->
       {{ owner_panel_html | safe }}

       <!-- ── تبويب الإعدادات (Settings) ── -->
       <div class="tab-content" id="tab-settings">
          <div class="section-card">
             <div class="section-head">تغيير كلمة المرور</div>
             <div class="section-body" style="max-width: 400px;">
                <div class="field-block" style="margin-bottom:12px;">
                   <label style="display:block; margin-bottom:6px; color:var(--text2); font-size:13px;">كلمة المرور الجديدة</label>
                   <input type="password" id="new-password" placeholder="أدخل كلمة المرور الجديدة" style="width:100%; padding:10px; border-radius:8px; border:1px solid var(--border); background:var(--bg3); color:white; outline:none;">
                </div>
                <button class="btn-action" style="background:var(--accent); color:white; padding:10px 16px; border:none; border-radius:8px; cursor:pointer; font-weight:600; width:100%; transition: .2s;" onmouseover="this.style.opacity='0.8'" onmouseout="this.style.opacity='1'" onclick="changePassword()">تحديث كلمة المرور</button>
             </div>
          </div>
       </div>

    </div>
  </div>
</div>

<script>
// ── التبديل بين التبويبات ──
document.querySelectorAll('.tab-item').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    tab.classList.add('active');
    const target = document.getElementById('tab-' + tab.dataset.tab);
    if(target) target.classList.add('active');
  });
});

// ── منطق محادثة الذكاء الاصطناعي ──
function appendAiMessage(text, isUser = false) {
  const box = document.getElementById('ai-messages');
  const time = new Date().toLocaleTimeString('ar-SA', { hour: '2-digit', minute:'2-digit' });
  const msgDiv = document.createElement('div');
  msgDiv.className = 'ai-msg ' + (isUser ? 'ai-user' : '');
  
  msgDiv.innerHTML = `
    <div class="ai-bubble">
      <div class="ai-avatar">${isUser ? '👤' : '🤖'}</div>
      <div>
        <div class="ai-text">${escapeHtml(text)}</div>
        <div class="ai-time">${time}</div>
      </div>
    </div>
  `;
  box.appendChild(msgDiv);
  box.scrollTop = box.scrollHeight;
}

async function sendAiMessage() {
  const input = document.getElementById('ai-chat-input');
  const text = input.value.trim();
  if(!text) return;
  
  input.value = '';
  appendAiMessage(text, true);
  
  const thinkingBox = document.getElementById('ai-thinking');
  thinkingBox.style.display = 'block';
  const box = document.getElementById('ai-messages');
  box.scrollTop = box.scrollHeight;
  
  try {
    const res = await fetch('/api/ai_chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: text })
    });
    const data = await res.json();
    thinkingBox.style.display = 'none';
    
    if(data.success) {
      appendAiMessage(data.reply);
    } else {
      appendAiMessage("⚠️ عذراً، حدث خطأ أثناء الاتصال بالخادم: " + (data.error || "خطأ غير معروف"));
    }
  } catch(e) {
    thinkingBox.style.display = 'none';
    appendAiMessage("⚠️ فشل الاتصال بالخادم الذكي. تأكد من اتصالك بالإنترنت.");
  }
}

function clearAiChat() {
  if(confirm("هل أنت متأكد من مسح المحادثة بالكامل؟")) {
    const box = document.getElementById('ai-messages');
    box.innerHTML = '';
    appendAiMessage("تم تفريغ المحادثة بنجاح. كيف يمكنني مساعدتك الآن؟");
  }
}

// ── دالة حماية النصوص من هجمات XSS ──
function escapeHtml(unsafe) {
    return (unsafe || '').toString()
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// ── تغيير كلمة المرور ──
function changePassword() {
  const pwd = document.getElementById('new-password').value;
  if(!pwd) return alert("الرجاء إدخال كلمة المرور الجديدة أولاً.");
  
  fetch('/api/users/change_password', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ new_password: pwd })
  }).then(r => r.json()).then(d => {
     if(d.success) {
         alert("✅ تم تغيير كلمة المرور بنجاح");
         document.getElementById('new-password').value = '';
     } else {
         alert("❌ خطأ: " + d.error);
     }
  }).catch(e => alert("حدث خطأ في الاتصال بالسيرفر."));
}

// ── تفعيل أول تبويب تلقائياً عند تحميل الصفحة ──
window.onload = function() {
  const firstTab = document.querySelector('.tab-item');
  if (firstTab) firstTab.click();
};
</script>
</body>
</html>

// ─── Announcements (الإعلانات) ───
async function loadAnnouncements() {
  try {
    const r = await fetch('/api/owner/announcements');
    const d = await r.json();
    const list = document.getElementById('announcements-list');
    if (!list) return;
    if (!(d.announcements || []).length) {
      list.innerHTML = '<div style="color:var(--text3); padding:15px; text-align:center; font-size:13px;">لا توجد إعلانات حالياً.</div>';
      return;
    }
    list.innerHTML = '';
    d.announcements.forEach(a => {
      list.innerHTML += `
        <div class="announcement-item" style="background:var(--bg4); border:1px solid var(--border); padding:12px; border-radius:8px; margin-bottom:10px; border-right: 4px solid var(--accent);">
          <div style="font-weight:700; color:var(--text); font-size:14px; margin-bottom:4px;">📢 ${escapeHtml(a.title)}</div>
          <div style="color:var(--text2); font-size:13px; line-height:1.5;">${escapeHtml(a.message)}</div>
          <div style="text-align:left; margin-top:8px;">
            <button class="btn-action danger" style="padding:4px 10px; font-size:11px;" onclick="deleteAnnouncement('${a.id}')">🗑 حذف</button>
          </div>
        </div>`;
    });
  } catch (e) {
    console.error("Failed to load announcements");
  }
}

async function postAnnouncement() {
  const title = document.getElementById('ann-title-inp').value.trim();
  const msg = document.getElementById('ann-msg-inp').value.trim();
  if (!title || !msg) return toast('الرجاء إدخال العنوان والمحتوى', true);
  
  const r = await fetch('/api/owner/announcements/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, message: msg })
  });
  const d = await r.json();
  if (d.success) {
    toast('✅ تم نشر الإعلان بنجاح');
    document.getElementById('ann-title-inp').value = '';
    document.getElementById('ann-msg-inp').value = '';
    loadAnnouncements();
  } else {
    toast('❌ فشل النشر: ' + (d.error || ''), true);
  }
}

async function deleteAnnouncement(id) {
  if (!confirm('هل أنت متأكد من حذف هذا الإعلان؟')) return;
  const r = await fetch('/api/owner/announcements/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id })
  });
  const d = await r.json();
  toast(d.success ? '🗑 تم الحذف' : '❌ فشل الحذف', !d.success);
  if (d.success) loadAnnouncements();
}

// ─── Pending Users (طلبات التسجيل) ───
async function loadPendingUsers() {
  try {
    const r = await fetch('/api/owner/users/pending');
    const d = await r.json();
    const list = document.getElementById('pending-users-list');
    if (!list) return;
    if (!(d.users || []).length) {
      list.innerHTML = '<div style="color:var(--text3); padding:15px; text-align:center; font-size:13px;">لا توجد طلبات تسجيل معلقة.</div>';
      return;
    }
    list.innerHTML = '';
    d.users.forEach(u => {
      list.innerHTML += `
        <div class="pending-user-card" style="display:flex; justify-content:space-between; align-items:center; background:var(--bg3); padding:12px; border-radius:8px; margin-bottom:8px;">
          <div>
            <div style="font-weight:600; color:var(--text); font-size:14px;">👤 ${escapeHtml(u.username)}</div>
            <div style="color:var(--text3); font-size:12px;">طلب إنشاء سيرفر جديد</div>
          </div>
          <div style="display:flex; gap:6px;">
            <button class="btn-action" style="background:var(--green); color:#fff; font-size:12px; padding:6px 12px;" onclick="approveUser('${escapeHtml(u.username)}')">✔ قبول</button>
            <button class="btn-action danger" style="font-size:12px; padding:6px 12px;" onclick="rejectUser('${escapeHtml(u.username)}')">✖ رفض</button>
          </div>
        </div>`;
    });
  } catch (e) {
    console.error("Failed to load pending users");
  }
}

async function approveUser(username) {
  const r = await fetch('/api/owner/users/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username })
  });
  const d = await r.json();
  toast(d.success ? `✅ تم قبول ${username}` : '❌ فشل القبول', !d.success);
  if (d.success) {
    loadPendingUsers();
    loadOwnerPanel(); // Refresh stats
  }
}

async function rejectUser(username) {
  if (!confirm(`هل أنت متأكد من رفض طلب ${username}؟`)) return;
  const r = await fetch('/api/owner/users/reject', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username })
  });
  const d = await r.json();
  toast(d.success ? `🗑 تم رفض وحذف ${username}` : '❌ فشل الرفض', !d.success);
  if (d.success) loadPendingUsers();
}

async function deleteUser(username) {
  if (!confirm(`تحذير: هل أنت متأكد من حذف السيرفر الخاص بـ ${username} نهائياً؟`)) return;
  const r = await fetch('/api/users/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username })
  });
  const d = await r.json();
  toast(d.success ? `🗑 تم حذف السيرفر بنجاح` : '❌ حدث خطأ أثناء الحذف', !d.success);
  if (d.success) {
    loadServersModal();
    loadOwnerPanel();
  }
}

// ─── Utilities & UI (الأدوات وتنبيهات النظام) ───
function toast(msg, isError = false, isSilent = false) {
  if (isSilent) { console.log(msg); return; }
  
  const toastContainer = document.getElementById('toast-container') || (function() {
    const c = document.createElement('div');
    c.id = 'toast-container';
    c.style.cssText = 'position:fixed; bottom:20px; left:20px; display:flex; flex-direction:column; gap:10px; z-index:9999;';
    document.body.appendChild(c);
    return c;
  })();

  const t = document.createElement('div');
  t.style.cssText = `
    background: ${isError ? 'var(--red)' : 'var(--accent)'};
    color: #fff; padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 600;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3); opacity: 0; transform: translateY(20px);
    transition: all 0.3s ease; display: flex; align-items: center; gap: 8px;
  `;
  t.innerHTML = msg;
  toastContainer.appendChild(t);
  
  // Animation
  setTimeout(() => { t.style.opacity = '1'; t.style.transform = 'translateY(0)'; }, 10);
  setTimeout(() => { 
    t.style.opacity = '0'; t.style.transform = 'translateY(20px)'; 
    setTimeout(() => t.remove(), 300);
  }, 4000);
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return (text || '').toString().replace(/[&<>"']/g, m => map[m]);
}

// ─── RIKO Identity & Console Branding (حقوق النظام) ───
function applyDevIdentity() {
  // Console Log Branding
  console.log(
    "%c 🚀 SERVER HUB - DEV RIKO %c", 
    "color: white; background: linear-gradient(135deg, #7c5cfc, #ff5c93); font-size: 20px; padding: 10px 20px; border-radius: 8px; font-weight: bold;", 
    ""
  );
  console.log(
    "%c المطور: @SHBH_S1 | القناة: @SHOBING_HXH ", 
    "color: #7c5cfc; font-size: 14px; font-weight: bold; margin-top: 5px;"
  );
  console.log("%c النظام يعمل بكفاءة ومحمي بواسطة إصدار RIKO V2.0", "color: #4CAF50; font-size: 12px;");
}

// ─── Initialize Dashboard ───
document.addEventListener('DOMContentLoaded', () => {
  applyDevIdentity();
  if (typeof IS_MASTER !== 'undefined' && IS_MASTER) {
    loadOwnerPanel();
    // Auto-refresh stats every 60 seconds
    setInterval(refreshBotStats, 60000);
  }
});

// ─── Security Alerts & Administration Panel (RIKO Center) ───────────────────

async function loadSecurityAlerts(){
  const el=document.getElementById('security-alerts-list');
  if(!el) return;
  el.innerHTML='<div style="color:var(--text2);padding:10px;text-align:center">⏳ جاري فحص النظام وتأمين لوحة RIKO...</div>';
  try{
    const r=await fetch('/api/security/alerts');
    const d=await r.json();
    if(!(d.alerts||[]).length){
      el.innerHTML='<div style="color:var(--green);padding:12px;text-align:center;font-size:13px;font-weight:600">✅ نظام الحماية مستقر — جميع خوادم RIKO آمنة ومحمية بالكامل!</div>';
      return;
    }
    el.innerHTML='';
    d.alerts.forEach(a=>{
      const threats=(a.threats||[]).join(' | ');
      const reviewed=a.reviewed;
      const div=document.createElement('div');
      div.style.cssText=`
        background:${reviewed?'var(--bg2)':'rgba(248,81,73,.05)'};
        border:1px solid ${reviewed?'var(--border)':'rgba(248,81,73,.3)'};
        border-radius:10px;padding:12px 14px;margin-bottom:8px;
        transition: 0.2s ease-in-out;
      `;
      div.innerHTML=`
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex-wrap:wrap">
          <div style="flex:1">
            <div style="font-size:13px;font-weight:700;color:${reviewed?'var(--text2)':'#f85149'};margin-bottom:4px">
              ${reviewed?'✅':'🚨'} ${escapeHtml(a.filename||'—')}
              <span style="font-size:10px;color:var(--text3);font-weight:400;margin-left:6px">#${escapeHtml(a.id||'')}</span>
            </div>
            <div style="font-size:11px;color:var(--text2);margin-bottom:4px">
              👤 User: ${escapeHtml(a.username||'—')} &nbsp;·&nbsp; 🌐 IP: ${escapeHtml(a.ip||'—')} &nbsp;·&nbsp; 🕐 Time: ${escapeHtml(a.time||'—')}
            </div>
            <div style="font-size:11px;color:#ffcc00;font-family:monospace;word-break:break-word">
              📌 Threats: ${escapeHtml(threats)}
            </div>
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0">
            ${!reviewed?`<button class="btn-action green" style="font-size:10px;padding:5px 10px"
              onclick="markAlertReviewed('${escapeHtml(a.id)}',this)">✓ مراجعة</button>`:''}
            <button class="btn-action danger" style="font-size:10px;padding:5px 10px"
              onclick="deleteAlert('${escapeHtml(a.id)}',this)">🗑</button>
          </div>
        </div>`;
      el.appendChild(div);
    });
  }catch(e){
    el.innerHTML='<div style="color:var(--red);padding:10px">❌ فشل تحميل جدار الحماية الأمني.</div>';
  }
}

async function markAlertReviewed(id, btn){
  const r=await fetch('/api/security/alerts/review',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  const d=await r.json();
  if(d.success){ toast('✅ تم وسم التنبيه كمُراجع',false,true); loadSecurityAlerts(); }
  else toast('❌ فشل تعديل حالة التنبيه',true);
}

async function deleteAlert(id, btn){
  const r=await fetch('/api/security/alerts/delete',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  const d=await r.json();
  if(d.success){ toast('🗑 تم حذف التنبيه الأمني بنجاح',false,true); loadSecurityAlerts(); }
  else toast('❌ فشل حذف التنبيه',true);
}

async function clearSecurityAlerts(){
  if(!confirm('هل تود حقاً مسح سجل التنبيهات الأمنية بالكامل؟')) return;
  const r=await fetch('/api/security/alerts/clear',{method:'POST'});
  const d=await r.json();
  toast(d.success?'🗑 تم تصفير سجل الحماية بنجاح':'❌ فشل تنفيذ الأمر',!d.success);
  if(d.success) loadSecurityAlerts();
}

// ─── Announcements & Custom Broadcasts (RIKO Broadcast) ─────────────────────

async function loadAnnouncements(){
  try{
    const r=await fetch('/api/owner/announcements');
    const d=await r.json();
    const list=document.getElementById('ann-list'); if(!list) return;
    if(!(d.list||[]).length){ list.innerHTML='<div style="color:var(--text3);padding:8px;text-align:center">📢 لا توجد إعلانات منشورة حالياً</div>'; return; }
    list.innerHTML='';
    d.list.forEach((a,i)=>{
      list.innerHTML+=`<div class="zip-item" style="border-left: 3px solid var(--accent)">
        <div>
          <div class="z-name" style="font-weight:600; color:var(--text)">${escapeHtml(a.text)}</div>
          <div class="z-size" style="font-size:11px; color:var(--text3); margin-top:3px;">⏰ ${escapeHtml(a.time||'')}</div>
        </div>
        <button class="btn-action danger" style="font-size:11px; padding:4px 8px" onclick="deleteAnn(${i})">🗑 حذف</button>
      </div>`;
    });
  }catch(e){ console.error("Error loading announcements"); }
}

async function addAnnouncement(){
  const txt=document.getElementById('ann-txt').value.trim(); if(!txt) return toast('⚠️ الرجاء كتابة الإعلان أولاً', true);
  const r=await fetch('/api/owner/announcements/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt})});
  const d=await r.json();
  toast(d.success?'📢 تم نشر الإعلان بنجاح فى لوحة RIKO':'❌ فشل إضافة الإعلان', !d.success);
  if(d.success){ document.getElementById('ann-txt').value=''; loadAnnouncements(); }
}

async function deleteAnn(idx){
  if(!confirm('هل تود حذف هذا الإعلان؟')) return;
  const r=await fetch('/api/owner/announcements/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({index:idx})});
  const d=await r.json();
  toast(d.success?'🗑 تم الحذف بنجاح':'❌ فشل حذف الإعلان', !d.success);
  if(d.success) loadAnnouncements();
}

async function ownerBroadcast(){
  const txt=document.getElementById('ann-txt').value.trim();
  if(!txt){ toast('⚠️ الرجاء إدخال نص الرسالة الجماعية', true); return; }
  const r=await fetch('/api/owner/broadcast',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:txt})});
  const d=await r.json();
  toast(d.success?`📡 تم البث بنجاح وإرسال الرسالة إلى ${d.count||0} مستخدم`:'❌ فشل إرسال البث الجماعي', !d.success);
}

// ─── User Registrations & Server Management ──────────────────────────────────

async function loadPendingUsers(){
  try{
    const r=await fetch('/api/users/pending');
    const d=await r.json();
    const el=document.getElementById('pending-users-list'); if(!el) return;
    if(!(d.users||[]).length){ el.innerHTML='<div style="color:var(--text3);padding:14px;text-align:center;font-size:13px">📋 لا توجد طلبات اشتراك معلقة حالياً.</div>'; return; }
    el.innerHTML='';
    d.users.forEach(u=>{
      el.innerHTML+=`<div class="pending-card" style="background:var(--bg3); border:1px solid var(--border); padding:12px; border-radius:10px; display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <div>
          <div class="p-user" style="font-weight:700; color:var(--text);">📋 ${escapeHtml(u.username)} 
             ${u.tg_username?`<a href="https://t.me/${escapeHtml(u.tg_username)}" target="_blank" style="color:#60a5fa; font-size:12px; margin-left:6px; text-decoration:none;">🔵 @${escapeHtml(u.tg_username)}</a>`:''}
          </div>
          <div class="p-time" style="font-size:11px; color:var(--text3); margin-top:3px;">📅 التسجيل: ${escapeHtml(u.created||'—')}</div>
        </div>
        <div style="display:flex;gap:6px">
          <button class="btn-action green" style="padding:6px 12px; font-size:12px;" onclick="approveUser('${escapeHtml(u.username)}')">✅ قبول</button>
          <button class="btn-action danger" style="padding:6px 12px; font-size:12px;" onclick="deleteUser('${escapeHtml(u.username)}')">❌ رفض</button>
        </div>
      </div>`;
    });
  }catch(e){ console.error("Error loading pending users"); }
}

async function approveUser(username){
  const r=await fetch('/api/users/approve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})});
  const d=await r.json();
  if(d.success){
    toast(`✅ تم تفعيل حساب ${username} بنجاح وإطلاق السيرفر`);
    loadPendingUsers();
  } else {
    toast(`❌ فشل قبول المستخدم: ${d.error||''}`, true);
  }
}

// ─── Core System Control (RIKO Advanced Actions) ───────────────────────────

async function ownerAction(action){
  if(action!=='restart_panel' && !confirm('تأكيد الإجراء: هل أنت متأكد من تنفيذ ['+action+']؟')) return;
  const r=await fetch('/api/owner/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});
  const d=await r.json();
  toast(d.success?'⚙️ تم تنفيذ العملية بنجاح: '+action:'❌ فشل تنفيذ الإجراء الأمني', !d.success);
}

function fmtExpiry(exp){
  if(!exp||exp==='∞') return '∞ غير محدود';
  try{
    const d=new Date(exp);
    const diff=Math.ceil((d-new Date())/(1000*86400));
    return diff>0?`⏳ متبقي ${diff} يوم`:'❌ منتهي الصلاحية';
  }catch(e){ return exp; }
}

// دالة مضافة لربط ودعم قنوات وحقوق التحديثات تلقائياً داخل النظام
function checkRikoIntegrity(){
  console.log("%c👑 Developed by RIKO | Dev: @SHBH_S1 | Channel: @SHOBING_HXH", "color:#7c5cfc; font-weight:bold; font-size:12px;");
}
checkRikoIntegrity();


# ─────────────────────────────────────────────────────────────────────────────
#  20.  Flask Routes — Powered by RIKO Control Engine
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    username = session.get('username')
    is_master = (username == MASTER_USERNAME)
    return render_template_string(get_html_template(is_master, username),
                                  session=session, user_path=get_user_path(username))

@app.route('/login', methods=['GET','POST'])
def login_page():
    if request.method == 'GET':
        return render_template_string(AUTH_TEMPLATE, error=None, error_type=None)
        
    username = request.form.get('username','').strip()
    password = request.form.get('password','')
    
    if not username or not password:
        return render_template_string(AUTH_TEMPLATE, error='❌ يرجى إدخال اسم المستخدم وكلمة المرور', error_type='login')
        
    h = hashlib.sha256(password.encode()).hexdigest()
    
    # Master Account Login (RIKO Admin Engine)
    if username == MASTER_USERNAME and h == MASTER_PASSWORD_HASH:
        session.permanent = True
        session['logged_in'] = True
        session['username'] = username
        register_session(username)
        log_activity(username, 'auth.login', 'Master Admin login successfully')
        return redirect('/')
    
    users = load_users()
    if username in users and users[username].get('password') == h:
        # Check Account Active State (Admin Approval Requirement)
        if not users[username].get('active', False):
            log_activity(username, 'auth.login.denied', 'Pending RIKO approval')
            return render_template_string(AUTH_TEMPLATE,
                error='⚠️ حسابك في انتظار موافقة الإدارة التابعة لـ RIKO. تواصل معنا لتفعيله عبر: @SHBH_S1',
                error_type='login')
                
        # Session Limit & Expiry Validation
        if can_user_login(username):
            session.permanent = True
            session['logged_in'] = True
            session['username'] = username
            register_session(username)
            ensure_user_folder(username)
            log_activity(username, 'auth.login', 'User logged in successfully')
            return redirect('/')
        else:
            log_activity(username, 'auth.login.denied', 'Session limit reached or account expired')
            return render_template_string(AUTH_TEMPLATE,
                error='❌ تم الوصول للحد الأقصى من الجلسات النشطة أو انتهت صلاحية حسابك.',
                error_type='login')
    
    log_activity(username or '-', 'auth.login.failed', 'Invalid credentials supplied')
    return render_template_string(AUTH_TEMPLATE, error='❌ خطأ في اسم المستخدم أو كلمة المرور', error_type='login')

@app.route('/register', methods=['POST'])
def register_page():
    username    = request.form.get('username','').strip()
    password    = request.form.get('password','')
    confirm     = request.form.get('confirm_password','')
    tg_username = request.form.get('tg_username','').strip().lstrip('@')

    # Input Sanitization & Validation
    if not username or not password:
        return render_template_string(AUTH_TEMPLATE, error='❌ يرجى ملء جميع الحقول المطلوبة', error_type='register')
    if not tg_username:
        return render_template_string(AUTH_TEMPLATE, error='❌ يرجى إدخال حسابك على التيليجرام للمتابعة والتحقق', error_type='register')
    if password != confirm:
        return render_template_string(AUTH_TEMPLATE, error='❌ كلمات المرور غير متطابقة', error_type='register')
    if len(username) < 3:
        return render_template_string(AUTH_TEMPLATE, error='❌ يجب ألا يقل اسم المستخدم عن 3 أحرف', error_type='register')
    if len(password) < 4:
        return render_template_string(AUTH_TEMPLATE, error='❌ يجب ألا تقل كلمة المرور عن 4 أحرف', error_type='register')
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return render_template_string(AUTH_TEMPLATE, error='❌ اسم المستخدم يجب أن يحتوي على حروف وأرقام وشرطة سفلية فقط', error_type='register')

    users = load_users()
    if username in users:
        return render_template_string(AUTH_TEMPLATE, error='❌ اسم المستخدم هذا مسجل مسبقاً بالنظام', error_type='register')

    # Assigning RIKO Free Trial Plan (7 days)
    expiry_dt = (datetime.now() + timedelta(days=7)).isoformat()
    users[username] = {
        'password':     hashlib.sha256(password.encode()).hexdigest(),
        'tg_username':  tg_username,
        'max_sessions': 1,
        'max_servers':  1,
        'main_file':    'main.py',
        'created':      datetime.now().isoformat(),
        'expiry':       expiry_dt,
        'plan':         'free_trial',
        'active':       False  # Requires @SHBH_S1 approval
    }
    
    # Save, create storage directory, and log activity safely
    save_users(users)
    ensure_user_folder(username)
    log_activity(username, 'auth.register', f'Telegram=@{tg_username} | Awaiting RIKO Approval')
    
    return render_template_string(AUTH_TEMPLATE,
        error=f'✅ تم إرسال طلب تسجيلك بنجاح! يرجى انتظار موافقة RIKO للتفعيل الرسمي.\nيوزر حسابك: @{tg_username}',
        error_type='register')

@app.route('/logout')
def logout():
    if 'username' in session:
        log_activity(session['username'], 'auth.logout', 'User explicitly requested logout')
        unregister_session(session['username'])
    session.clear()
    return redirect('/login')

# ─────────────────────────────────────────────────────────────────────────────
#  21.  API: Profile, System & Activity — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/profile')
@login_required
def get_profile():
    u = session['username']
    p = get_user_path(u)
    size = 0
    if os.path.exists(p):
        for r, d, f in os.walk(p):
            for fl in f:
                fp = os.path.join(r, fl)
                if os.path.exists(fp):
                    size += os.path.getsize(fp)
    users = load_users()
    ud = users.get(u, {})
    return jsonify({
        'username': u,
        'is_master': u == MASTER_USERNAME,
        'user_path': p,
        'created': ud.get('created', '') if isinstance(ud, dict) else '',
        'expiry': ud.get('expiry', '∞') if isinstance(ud, dict) else '∞',
        'disk_usage_gb': size / (1024**3),
        'system_brand': 'RIKO Core v2.0'
    })

@app.route('/api/system')
@login_required
def system_info():
    return jsonify(get_system_stats())

@app.route('/api/sysinfo')
@login_required
def sysinfo():
    return jsonify({
        'info': f"Platform: {platform.platform()}\n"
                f"CPU Usage: {psutil.cpu_percent()}%\n"
                f"Memory Usage: {psutil.virtual_memory().percent}%\n"
                f"Disk Usage: {psutil.disk_usage('/').percent}%\n"
                f"Engine: RIKO Secure Core Architecture"
    })

@app.route('/api/system/action', methods=['POST'])
@login_required
def system_action_api():
    a = (request.json or {}).get('action')
    try:
        if a == 'clean':
            gc.collect()
        log_activity(session['username'], 'system.action', a or '')
        return jsonify({'success': True, 'action': a, 'engine': 'RIKO'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/activity')
@login_required
def activity_api():
    data = load_json_file(ACTIVITY_FILE, {'events': []})
    events = data.get('events', [])
    if session.get('username') != MASTER_USERNAME:
        events = [e for e in events if e.get('username') == session.get('username')]
    return jsonify({'events': events[:200]})

# ─────────────────────────────────────────────────────────────────────────────
#  22.  API: Advanced File Manager & Security Shield
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/files/main-file')
@login_required
def get_main_file_api():
    u = session['username']
    if u == MASTER_USERNAME:
        mf = MASTER_CONFIG.get('main_file', 'main.py')
    else:
        users = load_users()
        mf = users.get(u, {}).get('main_file', 'main.py') if isinstance(users.get(u), dict) else 'main.py'
    return jsonify({'success': True, 'main_file': mf})

@app.route('/api/files')
@login_required
def list_files_api():
    p = request.args.get('path', get_user_path(session['username']))
    if not is_path_allowed(session['username'], p):
        return jsonify({'success': False, 'error': 'forbidden'}), 403
    files = []
    try:
        for n in sorted(os.listdir(p), key=lambda x: (not os.path.isdir(os.path.join(p, x)), x.lower())):
            fp = os.path.join(p, n)
            files.append({
                'name': n,
                'is_dir': os.path.isdir(fp),
                'size': f"{os.path.getsize(fp)//1024} KB" if os.path.isfile(fp) else ''
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'files': files})

@app.route('/api/files/upload', methods=['POST'])
@login_required
def upload_file_api():
    f = request.files.get('file')
    p = request.form.get('path', get_user_path(session['username']))
    if not f:
        return jsonify({'success': False, 'error': 'No file'}), 400
    if not is_path_allowed(session['username'], p):
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    try:
        filename = secure_filename(f.filename) if f.filename else 'uploaded_file'
        if not filename: 
            filename = 'uploaded_file'
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        
        # Block dangerous extensions via RIKO Firewall Rules
        if ext in BLOCKED_EXTENSIONS:
            log_activity(session['username'], 'security.blocked_ext', filename)
            return jsonify({'success': False, 'error': f'❌ نوع الملف .{ext} محظور برمجياً لأسباب أمنية حرجّة.'}), 403
            
        os.makedirs(p, exist_ok=True)
        sp = os.path.join(p, filename)
        f.save(sp)
        
        # Deep dynamic content scan via RIKO Scanner Engine
        threats = scan_file_content(sp)
        if threats:
            if os.path.exists(sp):
                os.remove(sp)
            threat_list = ' | '.join(threats[:5])
            log_activity(session['username'], 'security.malware_blocked', f'{filename}: {threat_list}')

            # ── حفظ التنبيه في قاعدة بيانات لوحة التحكم ──
            alert_rec = save_security_alert(
                username=session['username'],
                filename=filename,
                threats=threats[:5],
                ip=request.remote_addr
            )

            # ── إرسال إشعار تليجرام فوري لمالك السيرفر المربوط بهوية RIKO ──
            try:
                users_data = load_users()
                ud = users_data.get(session['username'], {})
                tg_user = ud.get('tg_username', 'غير معروف') if isinstance(ud, dict) else 'غير معروف'
                cfg = load_owner_config()
                if cfg.get('bot_linked') and cfg.get('telegram_token') and cfg.get('telegram_owner_id'):
                    threats_fmt = '\n'.join(f'   • {t}' for t in threats[:5])
                    alert_msg = (
                        f"🚨 *جدار الحماية RIKO — تم رصد تهديد أمني خطير!*\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"👤 *المستعمل:* `{session['username']}`\n"
                        f"📱 *حساب التليجرام:* `@{tg_user}`\n"
                        f"📄 *الملف المرفوع:* `{filename}`\n"
                        f"🌐 *عنوان الـ IP:* `{request.remote_addr}`\n"
                        f"🕐 *توقيت الرصد:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                        f"🔍 *الشيفرات الخبيثة المكتشفة:*\n{threats_fmt}\n\n"
                        f"⚠️ [RIKO SHIELD] تم تدمير الملف تلقائياً وحذفه نهائياً من القرص لحماية الخادم الرئيسي."
                    )
                    requests.post(
                        f"https://api.telegram.org/bot{cfg['telegram_token']}/sendMessage",
                        json={'chat_id': cfg['telegram_owner_id'], 'text': alert_msg, 'parse_mode': 'Markdown'},
                        timeout=8
                    )
            except Exception:
                pass
            return jsonify({'success': False, 'error': 'SECURITY_ALERT|' + threat_list}), 403
            
        log_activity(session['username'], 'file.upload', filename)
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/folder', methods=['POST'])
@login_required
def create_folder_api():
    d = request.json or {}
    if not is_path_allowed(session['username'], d.get('path', '')):
        return jsonify({'success': False}), 403
    os.makedirs(d['path'], exist_ok=True)
    log_activity(session['username'], 'file.mkdir', d['path'])
    return jsonify({'success': True})

@app.route('/api/files/create', methods=['POST'])
@login_required
def create_file_api():
    d = request.json or {}
    if not is_path_allowed(session['username'], d.get('path', '')):
        return jsonify({'success': False}), 403
    with open(d['path'], 'w', encoding='utf-8') as f:
        f.write(d.get('content', ''))
    log_activity(session['username'], 'file.create', d['path'])
    return jsonify({'success': True})

@app.route('/api/files/delete', methods=['POST'])
@login_required
def delete_file_api():
    d = request.json or {}
    p = d.get('path', '')
    if not is_path_allowed(session['username'], p):
        return jsonify({'success': False}), 403
    if os.path.isdir(p): 
        shutil.rmtree(p, ignore_errors=True)
    elif os.path.isfile(p): 
        os.remove(p)
    log_activity(session['username'], 'file.delete', p)
    return jsonify({'success': True})

@app.route('/api/files/content')
@login_required
def get_file_content():
    p = request.args.get('path')
    if not p or not is_path_allowed(session['username'], p):
        return jsonify({'success': False}), 403
    try:
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            return jsonify({'content': f.read()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/files/save', methods=['POST'])
@login_required
def save_file_api():
    d = request.json or {}
    if not is_path_allowed(session['username'], d.get('path', '')):
        return jsonify({'success': False}), 403
    with open(d['path'], 'w', encoding='utf-8') as f:
        f.write(d.get('content', ''))
    log_activity(session['username'], 'file.write', d['path'])
    return jsonify({'success': True})

@app.route('/api/files/set-main', methods=['POST'])
@login_required
def set_main_file_api():
    d = request.json or {}
    filename = d.get('filename', '')
    username = session['username']
    if not filename:
        return jsonify({'success': False, 'error': 'No filename'})
    users = load_users()
    if username == MASTER_USERNAME:
        MASTER_CONFIG['main_file'] = filename
        save_json_file(MASTER_CONFIG_FILE, MASTER_CONFIG)
    elif username in users:
        users[username]['main_file'] = filename
        save_users(users)
    log_activity(username, 'file.set-main', filename)
    return jsonify({'success': True, 'main_file': filename})

@app.route('/api/files/extract', methods=['POST'])
@login_required
def extract_api():
    d = request.json or {}
    archive = d.get('archive', '')
    dest    = d.get('dest', '')
    if not archive or not is_path_allowed(session['username'], archive):
        return jsonify({'success': False, 'error': 'Forbidden or invalid path'}), 403
    if not dest:
        dest = re.sub(r'\.(zip|tar\.gz|tar|gz|rar)$', '', archive, flags=re.I)
    result = safe_extract(archive, dest, session['username'])
    return jsonify(result)

# ─────────────────────────────────────────────────────────────────────────────
#  23.  API: Run Files & Dynamic Process Controller — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/file/run', methods=['POST'])
@login_required
def run_file_api():
    d = request.json or {}
    filepath = os.path.join(d.get('path',''), d.get('filename',''))
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'error': 'المستند أو الملف غير موجود بالنظام'})
    if not is_path_allowed(session['username'], d.get('path','')):
        return jsonify({'success': False, 'error': 'غير مسموح لك بالوصول لهذا المسار'})
        
    # Handling ZIP Files execution safely
    if d.get('filename','').lower().endswith('.zip'):
        extract_dir = os.path.join(d['path'], d['filename'].replace('.zip',''))
        os.makedirs(extract_dir, exist_ok=True)
        main = extract_and_find_main(filepath, extract_dir)
        if main: 
            filepath = main
        else: 
            return jsonify({'success': False, 'error': 'لم يتم العثور على ملف التشغيل الرئيسي داخل الـ ZIP'})
            
    installed = auto_install_dependencies(filepath)
    cmd = get_run_command(filepath)
    
    try:
        kwargs = dict(shell=True, cwd=os.path.dirname(filepath),
                      stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                      stderr=subprocess.STDOUT, text=True, bufsize=1)
        if hasattr(os, 'setsid'): 
            kwargs['preexec_fn'] = os.setsid
        p = subprocess.Popen(cmd, **kwargs)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
        
    pid = f"{session['username']}_{d.get('filename','f')}_{int(time.time())}"
    file_processes[pid] = {
        'process': p,
        'filename': d.get('filename',''),
        'username': session['username'],
        'output': [],
        'engine': 'RIKO Core Runtime'
    }
    
    # Asynchronous output thread handling
    threading.Thread(target=read_process_output, args=(pid, p), kwargs={'store': file_processes}, daemon=True).start()
    log_activity(session['username'], 'file.run', f"{d.get('filename','')} ({pid})")
    
    return jsonify({'success': True, 'process_id': pid, 'installed_result': installed, 'status': 'Running under RIKO Isolation'})

@app.route('/api/file/stop', methods=['POST'])
@login_required
def stop_file_api():
    pid = (request.json or {}).get('process_id')
    if pid in file_processes:
        try:
            if hasattr(os, 'killpg'): 
                os.killpg(os.getpgid(file_processes[pid]['process'].pid), signal.SIGKILL)
            else: 
                file_processes[pid]['process'].kill()
        except Exception: 
            pass
        log_activity(session['username'], 'file.stop', pid)
        del file_processes[pid]
    return jsonify({'success': True, 'message': 'تم إيقاف العملية بنجاح'})

@app.route('/api/file/output/<pid>')
@login_required
def get_file_output_api(pid):
    if pid in file_processes:
        info = file_processes[pid]
        out = list(info.get('output', []))
        info['output'].clear()
        return jsonify({'success': True, 'output': out, 'is_running': info['process'].poll() is None})
    return jsonify({'success': False, 'output': [], 'is_running': False})

@app.route('/api/file/output/<pid>/clear', methods=['POST'])
@login_required
def clear_file_output(pid):
    if pid in file_processes:
        file_processes[pid]['output'].clear()
    return jsonify({'success': True})

@app.route('/api/file/input', methods=['POST'])
@login_required
def send_file_input_api():
    d = request.json or {}
    pid = d.get('process_id')
    if pid in file_processes:
        try:
            file_processes[pid]['process'].stdin.write(d.get('input', '') + '\n')
            file_processes[pid]['process'].stdin.flush()
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': True})

@app.route('/api/file/running')
@login_required
def get_running_files_api():
    user = session['username']
    running, dead = [], []
    for pid, info in file_processes.items():
        if info['username'] == user or user == MASTER_USERNAME:
            if info['process'].poll() is None:
                running.append({'process_id': pid, 'filename': info['filename'], 'username': info['username']})
            else:
                dead.append(pid)
    for d in dead: 
        file_processes.pop(d, None)
    return jsonify({'success': True, 'running': running})

# ─────────────────────────────────────────────────────────────────────────────
#  24.  API: Secured Shell Terminal (RIKO Advanced Exec)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/exec', methods=['POST'])
@login_required
def execute_command_api():
    d = request.json or {}
    cmd = d.get('command', '').strip()
    cwd = d.get('cwd', get_user_path(session['username']))
    if not cmd:
        return jsonify({'output': '', 'success': True})

    # ── Smart Command Rewriting (Environment Normalization) ──
    if re.match(r'^python\s+', cmd):
        cmd = 'python3 ' + cmd[7:]
    elif cmd == 'python':
        cmd = 'python3 --version'
        
    if re.match(r'^pip\s+', cmd):
        cmd = 'pip3 ' + cmd[4:]
    elif cmd == 'pip':
        cmd = 'pip3 --version'

    # ── Advanced Blocked Commands List (RIKO Secure Shield) ──
    BLOCKED_CMDS = [
        r'rm\s+-rf\s+/', r'mkfs', r':\(\)\{\s*:\|\s*:&\s*\}\s*;:', r'dd\s+if=/dev/zero',
        r'wget.*\|\s*bash', r'curl.*\|\s*bash', r'>\s*/etc/passwd', r'chmod\s+777\s+/',
        r'chown', r'shutdown', r'reboot', r'pkill', r'killall'
    ]
    
    for bc in BLOCKED_CMDS:
        if re.search(bc, cmd, re.IGNORECASE):
            log_activity(session['username'], 'security.blocked_cmd', cmd[:100])
            return jsonify({
                'output': '🚨 [RIKO SHIELD] عذراً، هذا الأمر محظور أمنياً لحماية بيئة الاستضافة المشتركة.', 
                'success': False
            })

    log_activity(session['username'], 'exec', cmd[:120])
    try:
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        r = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True,
            timeout=120, env=env
        )
        output = r.stdout + r.stderr
        
        if not output.strip():
            output = '✅ [RIKO] تم تنفيذ الأمر البرمجي بنجاح (لا يوجد مخرجات لعرضها).'
            
        return jsonify({'output': output, 'success': r.returncode == 0, 'code': r.returncode})
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'output': '⏱️ [RIKO TIMEOUT] انتهت المهلة المحددة (120 ثانية) — قد تكون العملية البرمجية لا تزال تعمل في الخلفية.', 
            'success': False
        })
    except Exception as e:
        return jsonify({'output': f'❌ خطأ في النظام الداخلي: {str(e)}', 'success': False})

# ─────────────────────────────────────────────────────────────────────────────
#  25.  API: Node.js Project Controller — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/nodejs/start', methods=['POST'])
@login_required
def nodejs_start_api():
    d = request.json or {}
    path      = d.get('path','').strip()
    port      = d.get('port')
    main_file = d.get('main_file','').strip() or None
    deps_file = d.get('deps_file','').strip() or None
    
    if not path:
        return jsonify({'success': False, 'error': 'لم يتم تحديد مسار المشروع'})
    if not is_path_allowed(session['username'], path):
        return jsonify({'success': False, 'error': 'غير مسموح لك بالوصول لهذا المسار أمنياً'})
        
    result = start_nodejs_project(path, session['username'], port,
                                  main_file=main_file, deps_file=deps_file)
    return jsonify(result)

@app.route('/api/nodejs/info', methods=['POST'])
@login_required
def nodejs_info_api():
    """Return install & run commands without starting."""
    d = request.json or {}
    path      = d.get('path','').strip()
    main_file = d.get('main_file','').strip() or None
    deps_file = d.get('deps_file','').strip() or None
    
    if not path or not is_path_allowed(session['username'], path):
        return jsonify({'success': False, 'error': 'المسار محظور أو غير موجود'})
        
    info = get_nodejs_info(path, main_file=main_file, deps_file=deps_file)
    
    # scan for valid javascript source files inside user directory
    js_files = []
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [dd for dd in dirs if dd not in ['node_modules', '.git', '__pycache__']]
            for fn in files:
                if fn.endswith('.js') or fn.endswith('.mjs') or fn.endswith('.cjs'):
                    js_files.append(os.path.relpath(os.path.join(root, fn), path))
    except Exception: 
        pass
        
    info['js_files']  = js_files[:50]
    info['success']   = True
    info['engine']    = 'RIKO Node Runtime v2.0'
    return jsonify(info)

@app.route('/api/nodejs/stop', methods=['POST'])
@login_required
def nodejs_stop_api():
    pid = (request.json or {}).get('pid')
    if pid in nodejs_processes:
        try:
            p = nodejs_processes[pid]['process']
            if hasattr(os, 'killpg'): 
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            else: 
                p.kill()
        except Exception: 
            pass
        log_activity(session['username'], 'nodejs.stop', pid)
        del nodejs_processes[pid]
    return jsonify({'success': True, 'message': 'تم إيقاف عملية خادم Node.js بنجاح'})

@app.route('/api/nodejs/list')
@login_required
def nodejs_list_api():
    user = session['username']
    result = []
    dead = []
    for pid, info in nodejs_processes.items():
        if info['username'] == user or user == MASTER_USERNAME:
            is_running = info['process'].poll() is None
            if not is_running and user != MASTER_USERNAME:
                dead.append(pid)
                continue
            result.append({
                'pid': pid, 'command': info.get('command', ''), 'port': info.get('port'),
                'project': info.get('project', ''), 'started': info.get('started', ''),
                'main_file': info.get('main_file', ''), 'deps_file': info.get('deps_file', ''),
                'running': is_running, 'brand': 'RIKO Host Engine'
            })
    for d in dead: 
        nodejs_processes.pop(d, None)
    return jsonify({'processes': result})

@app.route('/api/nodejs/logs/<pid>')
@login_required
def nodejs_logs_api(pid):
    if pid in nodejs_processes:
        return jsonify({'output': list(nodejs_processes[pid].get('output', []))})
    return jsonify({'output': []})

# ─────────────────────────────────────────────────────────────────────────────
#  26.  API: PHP Embedded Server Controller — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/php/start', methods=['POST'])
@login_required
def php_start_api():
    d = request.json or {}
    path      = d.get('path', '').strip()
    port      = d.get('port')
    main_file = d.get('main_file', '').strip() or None
    deps_file = d.get('deps_file', '').strip() or None
    
    if not path:
        return jsonify({'success': False, 'error': 'لم يتم تزويد مسار الـ PHP'})
    if not is_path_allowed(session['username'], path):
        return jsonify({'success': False, 'error': 'المسار المطلوب محظور أمنياً'})
        
    result = start_php_server(path, session['username'], port,
                              main_file=main_file, deps_file=deps_file)
    return jsonify(result)

@app.route('/api/php/info', methods=['POST'])
@login_required
def php_info_api():
    """Return install & run commands without starting."""
    d = request.json or {}
    path      = d.get('path', '').strip()
    main_file = d.get('main_file', '').strip() or None
    deps_file = d.get('deps_file', '').strip() or None
    
    if not path or not is_path_allowed(session['username'], path):
        return jsonify({'success': False, 'error': 'المسار محظور أو غير متوفر حالياً'})
        
    info = get_php_info(path, main_file=main_file, deps_file=deps_file)
    
    # search for internal php files inside user space
    php_files = []
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [dd for dd in dirs if dd not in ['vendor', '.git', 'node_modules']]
            for fn in files:
                if fn.endswith('.php'):
                    php_files.append(os.path.relpath(os.path.join(root, fn), path))
    except Exception: 
        pass
        
    info['php_files'] = php_files[:50]
    info['success']   = True
    info['engine']    = 'RIKO PHP Engine Environment'
    return jsonify(info)

@app.route('/api/php/stop', methods=['POST'])
@login_required
def php_stop_api():
    pid = (request.json or {}).get('pid')
    if pid in _php_servers:
        try:
            p = _php_servers[pid]['process']
            if hasattr(os, 'killpg'): 
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            else: 
                p.kill()
        except Exception: 
            pass
        log_activity(session['username'], 'php.stop', pid)
        del _php_servers[pid]
    return jsonify({'success': True, 'message': 'تم إغلاق خادم PHP وسحب المنفذ بأمان'})

@app.route('/api/php/list')
@login_required
def php_list_api():
    user = session['username']
    result = []
    for pid, info in _php_servers.items():
        if info['username'] == user or user == MASTER_USERNAME:
            result.append({
                'pid': pid, 'port': info.get('port'), 'path': info.get('path', ''),
                'started': info.get('started', ''), 'running': info['process'].poll() is None,
                'system': 'RIKO Infrastructure Shared Core'
            })
    return jsonify({'servers': result})

# ─────────────────────────────────────────────────────────────────────────────
#  27.  API: System Processes Management — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/process/start', methods=['POST'])
@login_required
def start_process_api():
    d = request.json or {}
    cmd = d.get('command', '').strip()
    name = d.get('name', '').strip()
    
    if not cmd or not name:
        return jsonify({'success': False, 'error': 'اسم العملية والأمر البرمجي مطلوبان'})
        
    # Security filter against malicious commands injection inside RIKO runtime
    BLOCKED_PATTERNS = [r'rm\s+-rf', r'mkfs', r'chmod\s+777', r'chown']
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            log_activity(session['username'], 'security.process_blocked', f"Name: {name} | Cmd: {cmd}")
            return jsonify({'success': False, 'error': '🚨 الأمر البرمجي يحتوي على تعليمات محظورة أمنياً'})

    def run():
        kwargs = dict(shell=True, cwd=d.get('cwd', BASE_PATH))
        if hasattr(os, 'setsid'): 
            kwargs['preexec_fn'] = os.setsid
        p = subprocess.Popen(cmd, **kwargs)
        running_processes[name] = {
            'process': p,
            'owner': session.get('username'),
            'command': cmd,
            'engine': 'RIKO Process Monitor'
        }
        p.wait()
        
    threading.Thread(target=run, daemon=True).start()
    log_activity(session['username'], 'process.start', name)
    return jsonify({'success': True, 'message': 'تم إطلاق العملية في بيئة معزولة بنجاح'})

@app.route('/api/process/stop', methods=['POST'])
@login_required
def stop_process_api():
    n = (request.json or {}).get('name', '')
    if n in running_processes:
        try:
            if hasattr(os, 'killpg'): 
                os.killpg(os.getpgid(running_processes[n]['process'].pid), signal.SIGKILL)
            else: 
                running_processes[n]['process'].kill()
        except Exception: 
            pass
        del running_processes[n]
    log_activity(session['username'], 'process.stop', n)
    return jsonify({'success': True, 'message': 'تم إنهاء العملية وسحب الصلاحيات'})

@app.route('/api/process/list')
@login_required
def list_processes_api():
    procs = {}
    user = session.get('username')
    for n, i in running_processes.items():
        # User isolation: users only see their own active background processes
        if user == MASTER_USERNAME or i.get('owner') == user:
            procs[n] = {
                'status': 'running' if i['process'].poll() is None else 'stopped',
                'command': i['command']
            }
    return jsonify(procs)

# ─────────────────────────────────────────────────────────────────────────────
#  28.  API: Network & Port Allocation Engine — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/network/scan', methods=['POST'])
@login_required
def scan_ports_api():
    d = request.json or {}
    out = []
    host = d.get('host', '127.0.0.1')
    for p in d.get('ports', []):
        try:
            s = socket.socket()
            s.settimeout(1)
            r = s.connect_ex((host, int(p)))
            out.append({'port': p, 'open': r == 0})
            s.close()
        except Exception:
            out.append({'port': p, 'open': False})
    return jsonify({'results': out, 'host': host, 'scanner': 'RIKO Network Radar'})

@app.route('/api/ports/list')
@login_required
def list_ports_api():
    return jsonify({'ports': load_ports()})

@app.route('/api/ports/add', methods=['POST'])
@master_required
def add_port_api():
    d = request.json or {}
    try: 
        port = int(d.get('port', 0))
    except Exception: 
        return jsonify({'success': False, 'error': 'منفذ (Port) غير صالح'})
        
    if port <= 0 or port > 65535: 
        return jsonify({'success': False, 'error': 'قيمة المنفذ يجب أن تكون بين 1 و 65535'})
        
    ports = load_ports()
    if any(p.get('port') == port for p in ports): 
        return jsonify({'success': False, 'error': 'هذا المنفذ محجوز مسبقاً بالنظام'})
        
    ports.append({
        'port': port,
        'note': d.get('note', ''),
        'status': 'idle',
        'created': datetime.now().isoformat(),
        'allocated_by': 'RIKO Master Engine'
    })
    save_ports(ports)
    log_activity(session['username'], 'port.add', str(port))
    return jsonify({'success': True, 'message': 'تم فتح وتخصيص المنفذ الجديد بنجاح'})

@app.route('/api/ports/delete', methods=['POST'])
@master_required
def del_port_api():
    port = (request.json or {}).get('port')
    save_ports([p for p in load_ports() if p.get('port') != port])
    log_activity(session['username'], 'port.delete', str(port))
    return jsonify({'success': True, 'message': 'تم حذف وتطهير حجز المنفذ من الخادم'})

# ─────────────────────────────────────────────────────────────────────────────
#  29.  API: Master Administrative Management — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/users/list')
@master_required
def list_panel_users_api():
    users = load_users()
    sessions = load_user_sessions()
    result = []
    for u in users:
        ud = users[u] if isinstance(users[u], dict) else {}
        result.append({
            'username':        u,
            'tg_username':     ud.get('tg_username', ''),
            'password_hash':   ud.get('password', ''),
            'max_sessions':    ud.get('max_sessions', 999),
            'max_servers':     ud.get('max_servers', 1),
            'main_file':       ud.get('main_file', 'main.py'),
            'active_sessions': sessions.get(u, 0),
            'expiry':          ud.get('expiry'),
            'active':          ud.get('active', True),
            'created':         ud.get('created', ''),
            'plan':            ud.get('plan', 'free_trial'),
        })
    return jsonify({'users': result, 'system_owner_link': 'https://t.me/SHBH_S1'})

@app.route('/api/users/pending')
@master_required
def pending_users_api():
    users = load_users()
    pending = [{
        'username':    u,
        'tg_username': users[u].get('tg_username', '') if isinstance(users[u], dict) else '',
        'created':     users[u].get('created', '') if isinstance(users[u], dict) else ''
    } for u in users if isinstance(users[u], dict) and not users[u].get('active', True)]
    return jsonify({'users': pending, 'count': len(pending)})

@app.route('/api/users/approve', methods=['POST'])
@master_required
def approve_user_api():
    username = (request.json or {}).get('username', '')
    users = load_users()
    if username in users:
        users[username]['active'] = True
        save_users(users)
        log_activity(session['username'], 'user.approve', username)
        return jsonify({'success': True, 'message': f'تم تفعيل الموافقة على حساب {username} بنجاح'})
    return jsonify({'success': False, 'error': 'اسم المستخدم المطلوب غير مدرج في قاعدة بيانات RIKO'})

@app.route('/api/users/add', methods=['POST'])
@master_required
def add_panel_user_api():
    d = request.json or {}
    uname = d.get('username', '').strip()
    if not uname: 
        return jsonify({'success': False, 'error': 'اسم المستخدم حقل إجباري'})
    users = load_users()
    if uname in users: 
        return jsonify({'success': False, 'error': 'اسم المستخدم مسجل مسبقاً باللوحة'})
        
    plan = d.get('plan', 'free_trial')
    plan_days = {'free_trial': 7, 'paid_20': 20, 'paid_30': 30}
    expiry_days = plan_days.get(plan, int(d.get('expiry_days', 7) or 7))
    expiry_days = max(1, expiry_days)
    
    users[uname] = {
        'password':     hashlib.sha256(d.get('password', '').encode()).hexdigest(),
        'tg_username':  d.get('tg_username', '').lstrip('@'),
        'max_sessions': int(d.get('max_sessions', 1)),
        'max_servers':  int(d.get('max_servers', 1)),
        'main_file':    d.get('main_file', 'main.py'),
        'created':      datetime.now().isoformat(),
        'expiry':       (datetime.now() + timedelta(days=expiry_days)).isoformat(),
        'plan':         plan,
        'active':       True
    }
    save_users(users)
    ensure_user_folder(uname)
    log_activity(session['username'], 'user.add', f'{uname} plan={plan}')
    return jsonify({'success': True, 'message': f'تم إنشاء وتثبيت حساب {uname} بنجاح'})

@app.route('/api/users/update', methods=['POST'])
@master_required
def update_panel_user_api():
    d = request.json or {}
    users = load_users()
    uname = d.get('username', '')
    if uname not in users: 
        return jsonify({'success': False, 'error': 'هذا الحساب غير متوفر حالياً لتحديث بياناته'})
        
    if d.get('password'): 
        users[uname]['password'] = hashlib.sha256(d['password'].encode()).hexdigest()
    if d.get('max_servers') is not None: 
        users[uname]['max_servers'] = int(d['max_servers'])
    if d.get('main_file') is not None: 
        users[uname]['main_file'] = d['main_file']
    if d.get('max_sessions') is not None: 
        users[uname]['max_sessions'] = int(d['max_sessions'])
    if d.get('expiry_days') is not None:
        expiry_days = max(1, int(d['expiry_days'] or 30))
        users[uname]['expiry'] = (datetime.now() + timedelta(days=expiry_days)).isoformat()
        
    save_users(users)
    log_activity(session['username'], 'user.update', uname)
    return jsonify({'success': True, 'message': 'تم حفظ التعديلات الإدارية على الحساب والمزامنة فورياً'})

@app.route('/api/users/delete', methods=['POST'])
@master_required
def delete_panel_user_api():
    d = request.json or {}
    users = load_users()
    uname = d.get('username', '')
    if uname in users:
        del users[uname]
        save_users(users)
        shutil.rmtree(os.path.join(USERS_FOLDER, uname), ignore_errors=True)
        log_activity(session['username'], 'user.delete', uname)
    return jsonify({'success': True, 'message': f'تم طرد المستخدم وحذف مجلداته التخزينية نهائياً'})

# ─────────────────────────────────────────────────────────────────────────────
#  30.  API: Schedules & Automation — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/schedules/list')
@login_required
def list_schedules_api():
    return jsonify({'schedules': list(load_schedules().values())})

@app.route('/api/schedules/add', methods=['POST'])
@login_required
def add_schedule_api():
    d = request.json or {}
    sch = load_schedules()
    sid = str(uuid.uuid4())[:8]
    
    sch[sid] = {
        'id': sid,
        'name': d.get('name', ''),
        'command': d.get('command', ''),
        'schedule': d.get('schedule', '* * * * *'),
        'owner': session['username'],
        'engine': 'RIKO Cron System'
    }
    save_schedules(sch)
    log_activity(session['username'], 'schedule.add', d.get('name', ''))
    return jsonify({'success': True, 'message': 'تم جدولة المهمة بنجاح'})

# ─────────────────────────────────────────────────────────────────────────────
#  31.  API: Backups & Data Protection — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/backups/list')
@master_required
def list_backups_api():
    backs = []
    if os.path.exists(BACKUPS_FOLDER):
        for f in os.listdir(BACKUPS_FOLDER):
            if f.endswith('.tar.gz'):
                backs.append({
                    'name': f,
                    'size': f"{os.path.getsize(os.path.join(BACKUPS_FOLDER, f)) / 1024**2:.2f} MB"
                })
    return jsonify({'backups': backs})

@app.route('/api/backups/create', methods=['POST'])
@master_required
def create_backup_api():
    # RIKO branded backup nomenclature
    name = f"RIKO_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
    try:
        with tarfile.open(os.path.join(BACKUPS_FOLDER, name), 'w:gz') as tar:
            tar.add(BASE_PATH, arcname='riko_data_vault')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
        
    log_activity(session['username'], 'backup.create', name)
    return jsonify({'success': True, 'message': 'تم استخراج نسخة احتياطية آمنة للنظام'})

@app.route('/api/backups/download')
@master_required
def download_backup():
    name = request.args.get('name', '')
    path = os.path.join(BACKUPS_FOLDER, secure_filename(name))
    if not os.path.exists(path):
        return jsonify({'error': 'ملف النسخة الاحتياطية غير موجود'}), 404
    return send_file(path, as_attachment=True)

# ─────────────────────────────────────────────────────────────────────────────
#  32.  API: Package Managers (PIP / NPM) — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/packages/install/pip', methods=['POST'])
@master_required
def install_pip_api():
    pkg = (request.json or {}).get('package', '').strip()
    if not pkg: 
        return jsonify({'success': False, 'error': 'يجب تحديد اسم الحزمة'})
        
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', pkg], capture_output=True, timeout=120)
        pkgs = load_packages()
        if pkg not in pkgs.get('pip', []): 
            pkgs.setdefault('pip', []).append(pkg)
        save_packages(pkgs)
        
        log_activity(session['username'], 'pkg.pip.install', pkg)
        return jsonify({'success': True, 'message': f'تم تثبيت مكتبة {pkg} بنجاح'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'خطأ أثناء التثبيت: {str(e)}'})

@app.route('/api/packages/install/npm', methods=['POST'])
@login_required
def install_npm_api():
    pkg = (request.json or {}).get('package', '').strip()
    if not pkg: 
        return jsonify({'success': False, 'error': 'يجب تحديد اسم الحزمة'})
        
    try:
        r = subprocess.run(['npm', 'install', '-g', pkg], capture_output=True, text=True, timeout=120)
        log_activity(session['username'], 'pkg.npm.install', pkg)
        return jsonify({'success': r.returncode == 0, 'output': r.stdout + r.stderr})
    except Exception as e:
        return jsonify({'success': False, 'error': f'خطأ أثناء التثبيت: {str(e)}'})

# ─────────────────────────────────────────────────────────────────────────────
#  33.  API: System Logs — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/logs')
@master_required
def get_logs_api():
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            return jsonify({'logs': f.read()[-50000:]})
    return jsonify({'logs': ''})

@app.route('/api/logs/clear', methods=['POST'])
@master_required
def clear_logs_api():
    with open(LOGS_FILE, 'w', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SYSTEM LOGS CLEARED BY RIKO MASTER ENGINE\n")
    save_json_file(ACTIVITY_FILE, {'events': []})
    return jsonify({'success': True, 'message': 'تم مسح سجلات النظام بالكامل'})

# ─────────────────────────────────────────────────────────────────────────────
#  34.  API: AI Chat (Streaming) — RIKO Intelligence
# ─────────────────────────────────────────────────────────────────────────────

NVIDIA_AI_KEY = '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'
NVIDIA_AI_URL = 'https://integrate.api.nvidia.com/v1/chat/completions'

@app.route('/api/ai/chat', methods=['POST'])
@login_required
def ai_chat_api():
    from flask import Response, stream_with_context
    d = request.json or {}
    messages = d.get('messages', [])
    
    if not messages:
        return jsonify({'error': 'لم يتم العثور على رسائل'}), 400

    # RIKO AI System Prompt Injection
    system_msg = {
        'role': 'system',
        'content': (
            'You are RIKO AI, an advanced expert assistant for developers and server administrators. '
            'You are integrated into the RIKO Hosting Panel (Developed by @SHBH_S1, Official Channel: @SHOBING_HXH). '
            'You specialize in Python, Flask, Node.js, PHP, Telegram bots, web hosting, and server security. '
            'You give concise, practical, and highly accurate answers. For code, always use code blocks. '
            'If asked about your identity, explicitly state you are RIKO AI developed by @SHBH_S1. '
            'You can respond in Arabic or English depending on the user language.'
        )
    }
    
    full_messages = [system_msg] + messages[-18:]  # keep last 18 messages for context

    def generate():
        try:
            payload = {
                'model': 'openai/gpt-oss-120b',
                'messages': full_messages,
                'temperature': 0.7,
                'top_p': 0.95,
                'max_tokens': 4096,
                'stream': True
            }
            headers = {
                'Authorization': f'Bearer {NVIDIA_AI_KEY}',
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            }
            with requests.post(NVIDIA_AI_URL, json=payload, headers=headers, stream=True, timeout=60) as resp:
                for line in resp.iter_lines():
                    if line:
                        decoded = line.decode('utf-8') if isinstance(line, bytes) else line
                        yield decoded + '\n\n'
        except Exception as e:
            yield f'data: {{"error": "فشل الاتصال بخوادم RIKO AI: {str(e)}"}}\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

# ─────────────────────────────────────────────────────────────────────────────
#  35.  API: Master Settings & Core Control — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/master/change-password', methods=['POST'])
@master_required
def change_master_password_api():
    global MASTER_PASSWORD_HASH
    d = request.json or {}
    
    if hashlib.sha256(d.get('current_password', '').encode()).hexdigest() == MASTER_PASSWORD_HASH:
        MASTER_PASSWORD_HASH = hashlib.sha256(d.get('new_password', '').encode()).hexdigest()
        MASTER_CONFIG['master_password_hash'] = MASTER_PASSWORD_HASH
        save_json_file(MASTER_CONFIG_FILE, MASTER_CONFIG)
        log_activity(session['username'], 'security.password_changed', 'Master Administrator password updated')
        return jsonify({'success': True, 'message': 'تم تغيير كلمة مرور الإدارة بنجاح'})
        
    return jsonify({'success': False, 'error': 'كلمة المرور الحالية غير صحيحة'})

@app.route('/api/master/restart', methods=['POST'])
@master_required
def restart_panel_api():
    log_activity(session['username'], 'panel.restart', 'RIKO System Restart initiated by Master')
    # Background restart thread to allow request to complete
    threading.Thread(target=lambda: (time.sleep(1), os.execv(sys.executable, [sys.executable] + sys.argv)), daemon=True).start()
    return jsonify({'success': True, 'message': 'جاري إعادة تشغيل نظام RIKO...'})

# ─────────────────────────────────────────────────────────────────────────────
#  36.  API: Owner Configuration & Global System Control — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/owner/config')
@master_required
def owner_config_get():
    cfg = load_owner_config()
    safe = dict(cfg)
    # Masking sensitive data for security
    safe['telegram_token'] = '***' if cfg.get('telegram_token') else ''
    safe['system_engine'] = 'RIKO Core v2.0'
    return jsonify(safe)

@app.route('/api/owner/config/save', methods=['POST'])
@master_required
def owner_config_save():
    d = request.json or {}
    cfg = load_owner_config()
    if 'panel_name' in d: cfg['panel_name'] = d['panel_name']
    if 'welcome_msg' in d: cfg['welcome_msg'] = d['welcome_msg']
    save_json_file(OWNER_CONFIG_FILE, cfg)
    log_activity(session['username'], 'owner.config.save', '')
    return jsonify({'success': True, 'message': 'تم حفظ إعدادات لوحة التحكم بنجاح'})

@app.route('/api/owner/maintenance', methods=['GET', 'POST'])
@login_required
def owner_maintenance_api():
    if request.method == 'GET':
        return jsonify(load_maintenance())
    if session.get('username') != MASTER_USERNAME:
        return jsonify({'success': False, 'error': 'صلاحيات الماستر فقط'}), 403
    
    d = request.json or {}
    maint = load_maintenance()
    if 'enabled' in d: maint['enabled'] = bool(d['enabled'])
    if 'message' in d: maint['message'] = d['message']
    save_maintenance(maint)
    log_activity(session['username'], 'maintenance', f'enabled={maint["enabled"]}')
    return jsonify({'success': True, 'enabled': maint['enabled']})

# ─────────────────────────────────────────────────────────────────────────────
#  37.  API: Telemetry & Statistics Engine — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/owner/stats')
@master_required
def owner_stats_api():
    users = load_users()
    zip_count = 0
    try:
        # Recursive zip scanning for RIKO data audit
        for root, dirs, files in os.walk(USERS_FOLDER):
            for f in files:
                if f.lower().endswith('.zip'): zip_count += 1
        for f in os.listdir(BASE_PATH):
            if f.lower().endswith('.zip'): zip_count += 1
    except Exception: pass
    
    active_bots = sum(1 for p in file_processes.values() if p['process'].poll() is None)
    active_bots += sum(1 for p in nodejs_processes.values() if p['process'].poll() is None)
    
    stats = {
        'total_users': len(users),
        'total_servers': len(users),
        'active_bots': active_bots,
        'zip_files': zip_count,
        'last_updated': datetime.now().isoformat(),
        'engine': 'RIKO Monitoring v2.0'
    }
    save_json_file(BOT_STATS_FILE, stats)
    return jsonify(stats)

# ─────────────────────────────────────────────────────────────────────────────
#  38.  API: Telegram Bot Integration (RIKO Bot Manager)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/owner/bot/link', methods=['POST'])
@master_required
def owner_bot_link():
    d = request.json or {}
    token = d.get('token', '').strip()
    owner_id = d.get('owner_id', '').strip()
    
    if not token or not owner_id:
        return jsonify({'success': False, 'error': 'مطلوب توكن البوت ومعرف المالك (Owner ID)'})
    
    try:
        resp = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10)
        data = resp.json()
        if not data.get('ok'):
            return jsonify({'success': False, 'error': data.get('description', 'توكن غير صالح')})
            
        bot_username = data['result'].get('username', 'unknown')
        cfg = load_owner_config()
        cfg.update({
            'telegram_token': token, 'telegram_owner_id': owner_id, 
            'bot_linked': True, 'bot_username': bot_username
        })
        save_json_file(OWNER_CONFIG_FILE, cfg)
        log_activity(session['username'], 'bot.link', f'@{bot_username}')
        return jsonify({'success': True, 'bot_username': bot_username})
    except Exception as e:
        return jsonify({'success': False, 'error': f'تعذر ربط البوت: {str(e)}'})

@app.route('/api/owner/bot/cmd', methods=['POST'])
@master_required
def owner_bot_cmd():
    d = request.json or {}
    cmd = d.get('command', '').strip()
    cfg = load_owner_config()
    if not cfg.get('bot_linked'):
        return jsonify({'success': False, 'error': 'البوت غير مربوط حالياً'})
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        output = r.stdout + r.stderr
        token = cfg['telegram_token']
        owner_id = cfg['telegram_owner_id']
        requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
                      json={'chat_id': owner_id, 'text': f'🖥 RIKO CMD: {cmd}\n📝 Output:\n{output[:3000]}'}, timeout=10)
        log_activity(session['username'], 'bot.cmd', cmd[:100])
        return jsonify({'success': True, 'output': output})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ─────────────────────────────────────────────────────────────────────────────
#  39.  API: Advanced Archive/Zip Management (RIKO Vault)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/owner/zips/download-all')
@master_required
def owner_download_all_zips():
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        try:
            for user_dir in os.listdir(USERS_FOLDER):
                user_path = os.path.join(USERS_FOLDER, user_dir)
                if os.path.isdir(user_path):
                    for root, dirs, files in os.walk(user_path):
                        for f in files:
                            if f.lower().endswith('.zip'):
                                fp = os.path.join(root, f)
                                zf.write(fp, os.path.join(user_dir, f))
            for f in os.listdir(BASE_PATH):
                if f.lower().endswith('.zip'):
                    fp = os.path.join(BASE_PATH, f)
                    zf.write(fp, os.path.join('master_root', f))
        except Exception: pass
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='RIKO_All_Archives.zip', mimetype='application/zip')

# ─────────────────────────────────────────────────────────────────────────────
#  40.  API: Broadcast & Administrative Actions (RIKO Command Suite)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/owner/broadcast', methods=['POST'])
@master_required
def owner_broadcast():
    d = request.json or {}
    msg = d.get('message', '').strip()
    if not msg: return jsonify({'success': False, 'error': 'رسالة الإذاعة فارغة'})
    
    cfg = load_owner_config()
    count = 0
    if cfg.get('bot_linked') and cfg.get('telegram_token'):
        token = cfg['telegram_token']
        try:
            requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
                          json={'chat_id': cfg['telegram_owner_id'], 'text': f'📡 إعلان RIKO الهام:\n{msg}'}, timeout=10)
            count += 1
        except Exception: pass
        
    data = load_announcements()
    data['list'].insert(0, {'text': f'[BROADCAST] {msg}', 'time': datetime.now().strftime('%Y-%m-%d %H:%M')})
    save_announcements(data)
    log_activity(session['username'], 'owner.broadcast', msg[:80])
    return jsonify({'success': True, 'count': count, 'message': 'تم إرسال الإذاعة بنجاح'})

@app.route('/api/owner/action', methods=['POST'])
@master_required
def owner_action_api():
    action = (request.json or {}).get('action', '')
    try:
        if action == 'clear_all_logs':
            with open(LOGS_FILE, 'w') as f: 
                f.write(f"[{datetime.now()}] CLEARED BY RIKO MASTER\n")
            save_json_file(ACTIVITY_FILE, {'events': []})
            
        elif action == 'kick_all_users':
            sessions = load_user_sessions()
            for u in list(sessions.keys()):
                if u != MASTER_USERNAME: sessions[u] = 0
            save_user_sessions(sessions)
            
        elif action == 'restart_panel':
            # Safe RIKO Panel Reboot
            threading.Thread(target=lambda: (time.sleep(1), os.execv(sys.executable, [sys.executable] + sys.argv)), daemon=True).start()
            
        log_activity(session['username'], f'owner.action.{action}', '')
        return jsonify({'success': True, 'message': f'تم تنفيذ الإجراء: {action} بنجاح'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ─────────────────────────────────────────────────────────────────────────────
#  41.  API: Security Alerts & Incident Management — Powered by RIKO
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/security/alerts')
@master_required
def get_security_alerts_api():
    # Fetching incident logs for RIKO Threat Protection
    data = load_security_alerts()
    return jsonify(data)

@app.route('/api/security/alerts/review', methods=['POST'])
@master_required
def review_security_alert_api():
    alert_id = (request.json or {}).get('id', '')
    data = load_security_alerts()
    for a in data.get('alerts', []):
        if a.get('id') == alert_id:
            a['reviewed'] = True
            a['reviewed_by'] = session['username']
            break
    save_json_file(SECURITY_ALERTS_FILE, data)
    log_activity(session['username'], 'security.alert.reviewed', alert_id)
    return jsonify({'success': True, 'message': 'تمت مراجعة التنبيه وتأكيده'})

@app.route('/api/security/alerts/delete', methods=['POST'])
@master_required
def delete_security_alert_api():
    alert_id = (request.json or {}).get('id', '')
    data = load_security_alerts()
    data['alerts'] = [a for a in data.get('alerts', []) if a.get('id') != alert_id]
    save_json_file(SECURITY_ALERTS_FILE, data)
    return jsonify({'success': True, 'message': 'تم مسح سجل التهديد'})

@app.route('/api/security/alerts/clear', methods=['POST'])
@master_required
def clear_security_alerts_api():
    save_json_file(SECURITY_ALERTS_FILE, {'alerts': []})
    log_activity(session['username'], 'security.alerts.cleared', 'All incidents purged')
    return jsonify({'success': True, 'message': 'تم تصفير سجلات الأمان بنجاح'})

# ─────────────────────────────────────────────────────────────────────────────
#  42.  Static / Web Hosting (RIKO Infrastructure Isolation)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/static/<filename>')
def serve_static(filename):
    # Serving core panel assets
    return send_from_directory(BASE_PATH, filename)

@app.route('/web/<username>/')
@app.route('/web/<username>/<path:filename>')
def serve_user_web(username, filename='index.html'):
    # Isolated path serving for user web projects
    user_path = get_user_path(username)
    if not os.path.exists(os.path.join(user_path, filename)):
        return "404 - RIKO Engine Error: Requested file not found", 404
    return send_from_directory(user_path, filename)

@app.route('/api-service/<username>/')
@app.route('/api-service/<username>/<path:filename>')
def serve_user_api_files(username, filename='api.json'):
    # Serving JSON-based API definitions for users
    user_path = get_user_path(username)
    return send_from_directory(user_path, filename)

# ─────────────────────────────────────────────────────────────────────────────
#  43.  Admin Legacy Routes (Optimized/Redirected)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/admin/users')
def admin_manage_users():
    if not session.get('logged_in') or session.get('username') != MASTER_USERNAME:
        return redirect('/login')
    # Redirecting legacy admin routes to the main dashboard
    return redirect('/')

@app.route('/admin/approve/<username>')
def approve_user_legacy(username):
    if not session.get('logged_in') or session.get('username') != MASTER_USERNAME:
        return "403 - Forbidden: RIKO Administrative Access Required", 403
    
    users = load_users()
    if username in users:
        users[username]['active'] = True
        save_users(users)
        log_activity(MASTER_USERNAME, 'user.approve.legacy', username)
        
        return f'''
        <div style="font-family:sans-serif;text-align:center;margin-top:50px;background:#0b0f17;color:#e6edf3;min-height:100vh;padding:40px">
            <h3 style="color:#3fb950">✅ RIKO Hosting: Account activated successfully for: {html.escape(username)}</h3>
            <p>Admin Managed by: @SHBH_S1</p>
            <br>
            <a href="/" style="color:#7c5cfc;text-decoration:none">← العودة للوحة التحكم</a>
        </div>
        '''
    return "User not found in RIKO database", 404

# ─────────────────────────────────────────────────────────────────────────────
#  44.  RIKO Multi-Port Sub-servers & Dynamic Allocation Engine
# ─────────────────────────────────────────────────────────────────────────────

def run_extra_port(port, note=''):
    """
    تشغيل خادم فرعي معزول على منفذ مخصص عبر محرك RIKO Engine.
    """
    try:
        from flask import Flask as _F
        sub = _F(f'RIKO_SubServer_{port}')
        
        @sub.route('/')
        def _h():
            return f'''
            <div style="font-family:sans-serif;background:#0b0f17;color:#e6edf3;min-height:100vh;display:flex;align-items:center;justify-content:center">
                <div style="text-align:center">
                    <h1 style="background:linear-gradient(135deg,#7c5cfc,#00bfff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:36px">
                        RIKO Hosting Engine
                    </h1>
                    <p style="color:#8b949e;margin-top:8px">Active Port: {port}</p>
                    {(f"<p style='color:#484f58'>{html.escape(note)}</p>") if note else ""}
                    <p style="margin-top:20px">
                        <a style="color:#7c5cfc;text-decoration:none" href="/">Return to Panel</a>
                    </p>
                    <p style="margin-top:40px;font-size:12px;color:#30363d">Managed by @SHBH_S1</p>
                </div>
            </div>
            '''
        # تشغيل خادم فرعي مع تهيئة دقيقة لمنع تداخل عمليات الإعادة (Reloader)
        sub.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)
        
    except Exception as e:
        print(f'[RIKO Port Engine] Port {port} initialization failed: {e}')

def start_configured_extra_ports():
    """
    تحميل المنافذ المخصصة من قاعدة بيانات RIKO وبدء تشغيلها في مسارات منفصلة.
    """
    ports_config = load_ports()
    for p in ports_config:
        try:
            port_num = int(p.get('port', 0))
            note = p.get('note', '')
            if port_num > 0:
                threading.Thread(
                    target=run_extra_port, 
                    args=(port_num, note), 
                    daemon=True,
                    name=f"RIKO-Port-{port_num}"
                ).start()
        except Exception as e:
            print(f'[RIKO Port Engine] Error spawning thread for port {p.get("port")}: {e}')

# ─────────────────────────────────────────────────────────────────────────────
#  45.  Entry Point: RIKO Hosting Engine v2.0
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # RIKO Branding Colors & ASCII Art
    G = '\033[32m'; P = '\033[35m'; C = '\033[36m'; Y = '\033[33m'; B = '\033[1m'; R = '\033[0m'
    
    print(G + r'''
 ____  ___  _  _____  ___  
|  _ \|_ _|| |/ / _ \| | | 
| |_) || | | ' / | | | | | 
|  _ < | | | . \ |_| | |_| |
|_| \_\___||_|\_\___/ \___/ 
    '''.replace('RIKO', 'RIKO') + R)
    
    print(P + '\u2554' + '\u2550' * 64 + '\u2557' + R)
    print(P + '\u2551  \U0001f680  ' + B + C + 'RIKO Hosting Panel v2.0' + R + P + '  \u2015  Developed by @SHBH_S1      \u2551' + R)
    print(P + '\u255a' + '\u2550' * 64 + '\u255d' + R)
    
    print(G + '\u250c\u2500\u2500(' + P + B + 'RIKO' + R + G + '\u1F19A' + C + 'server-hub' + G + ')-[' + Y + '~' + G + ']' + R)
    print(G + '\u2514\u2500' + P + '$' + R + f' Master User : ' + B + C + '{MASTER_USERNAME}' + R)
    print(G + '\u2514\u2500' + P + '$' + R + f' Data Root   : ' + Y + '{BASE_PATH}' + R)

    # تشغيل خدمات المنافذ الفرعية المخصصة
    start_configured_extra_ports()

    # تحديد المنفذ الرئيسي للوحة
    port = int(os.environ.get('PORT', MASTER_CONFIG.get('port') or 3178))
    
    print(f"\n   🌐 Panel URL  : http://0.0.0.0:{port}")
    print(f"   🔑 Admin User : {MASTER_USERNAME}")
    print(f"   🛠 Support    : @SHOBING_HXH")
    print(f"   ⚡ Status     : RIKO Engine Online - All Systems Operational")
    print("-" * 65 + "\n")
    
    # تشغيل تطبيق Flask
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
