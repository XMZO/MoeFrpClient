import sqlite3
import json
import time
import uuid
import os
import re
import datetime
import string
import secrets
import bleach
import threading
import hashlib
from flask import Flask, request, jsonify, g, abort, make_response
from werkzeug.middleware.proxy_fix import ProxyFix
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import logging
from logging.handlers import RotatingFileHandler
from collections import OrderedDict
from functools import wraps

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address




TRUSTED_CLIENTS = [
    {
        "version": "999",
        "secret": "999",

        "dll_hash": "999"
    },
    {
        "version": "999",
        "secret": "999",

        "dll_hash": "999"
    },
]
TRUSTED_SECRET_MAP = {client['secret']: client for client in TRUSTED_CLIENTS}
MIN_CLIENT_VERSION = 999
LATEST_CLIENT_VERSION = 999
LATEST_CLIENT_VERSION_STR = "v9.9.9"

one_time_configs = {}
configs_lock = threading.Lock()

reset_tokens = {}
reset_tokens_lock = threading.Lock()

login_challenges = {}
challenges_lock = threading.Lock()

rate_limit_tracker = {}
rate_limit_lock = threading.Lock()


app = Flask(__name__)
DATABASE = 'users.db'





app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1
)


limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://",
    strategy="fixed-window"
)


ph = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,
    parallelism=2,
    hash_len=32,
    salt_len=16
)


class RequestContextFilter(logging.Filter):
    def filter(self, record):

        if request:
            record.remote_addr = request.remote_addr
        else:

            record.remote_addr = '-'
        return True


if not app.debug:

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [IP: %(remote_addr)s]'
    )
    handler = RotatingFileHandler('server.log', maxBytes=102400, backupCount=10)
    handler.setFormatter(formatter)


    handler.addFilter(RequestContextFilter())

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    app.logger.info('FRP Server Started')


CUSTOM_CHARSET = string.ascii_uppercase.replace('I', '').replace('L', '').replace('O', '') + '23456789'
def luhn_checksum(code_str):
    digits=[CUSTOM_CHARSET.find(c)for c in code_str];s=0;p=len(digits)%2;[s:=s+((d*2-len(CUSTOM_CHARSET)+1)if d*2>=len(CUSTOM_CHARSET)else d*2)if i%2==p else s+d for i,d in enumerate(digits)];return CUSTOM_CHARSET[(s*9)%len(CUSTOM_CHARSET)]
def validate_invite_code_format(code):
    if not re.match(r'^FRPT-[A-Z2-9]{4}-[A-Z2-9]{4}$',code):return False,"邀请码格式不正确。"
    body=code.replace('FRPT-','').replace('-','');base=body[:-1];checksum=body[-1]
    if luhn_checksum(base)!=checksum:return False,"邀请码校验失败，请检查是否输入错误。"
    return True,"验证通过"


def get_db():
    db = sqlite3.connect(DATABASE, timeout=15);db.row_factory = sqlite3.Row;db.execute("PRAGMA foreign_keys = ON");return db
def init_db():
    if not os.path.exists(DATABASE):
        with app.app_context():
            db=get_db()
            db.execute()
            db.execute('CREATE TABLE personal_configs (config_id TEXT PRIMARY KEY, owner_uuid TEXT NOT NULL, profile_name TEXT NOT NULL, config_json TEXT NOT NULL, FOREIGN KEY (owner_uuid) REFERENCES users (uuid) ON DELETE CASCADE);')
            db.execute('CREATE TABLE shares (share_id TEXT PRIMARY KEY, owner_uuid TEXT NOT NULL, share_name TEXT NOT NULL, is_template BOOLEAN NOT NULL, config_data_json TEXT NOT NULL, FOREIGN KEY (owner_uuid) REFERENCES users (uuid) ON DELETE CASCADE);')
            db.execute('CREATE TABLE subscriptions (subscription_id TEXT PRIMARY KEY, user_uuid TEXT NOT NULL, share_id TEXT NOT NULL, user_params_json TEXT, FOREIGN KEY (user_uuid) REFERENCES users (uuid) ON DELETE CASCADE, FOREIGN KEY (share_id) REFERENCES shares (share_id) ON DELETE CASCADE);')
            db.execute('CREATE TABLE invitation_codes (code TEXT PRIMARY KEY, is_used BOOLEAN NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, used_by_uuid TEXT, used_at TIMESTAMP, FOREIGN KEY (used_by_uuid) REFERENCES users (uuid) ON DELETE SET NULL);')
            db.execute()
            db.commit();print("Database initialized (simplified for 'Remember Password' feature).")


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            app.logger.warning(f"Auth header missing from IP: {request.remote_addr}")
            return jsonify({"error": "需要认证"}), 401

        try:
            token = auth_header.split(" ")[1]
        except IndexError:
            token = auth_header

        db = None
        try:
            db = get_db()
            user = db.execute('SELECT * FROM users WHERE current_session_token = ?', (token,)).fetchone()

            if user is None:
                app.logger.warning(f"无效的Token被使用: {token[:8]}...")
                app.logger.warning(f"Invalid token used from IP: {request.remote_addr}")
                return jsonify({"error": "会话无效或已过期"}), 401

            session_expiry_str = user['session_token_expiry']
            if not session_expiry_str:
                app.logger.error(f"用户(uuid:{user['uuid']})缺少会话过期时间。")
                app.logger.error(f"Missing session expiry for user: {user['nickname']}")
                return jsonify({"error": "会话状态异常，请重新登录"}), 401


            expiry_time = datetime.datetime.fromisoformat(session_expiry_str)
            if expiry_time.tzinfo is None:
                expiry_time = expiry_time.replace(tzinfo=datetime.timezone.utc)

            current_time_utc = datetime.datetime.now(datetime.timezone.utc)

            if expiry_time < current_time_utc:
                app.logger.info(f"用户(uuid:{user['uuid']}, name:{user['nickname']})的会话已过期。")
                app.logger.info(f"Session expired for user: {user['nickname']}")
                return jsonify({"error": "会话已过期，请重新登录"}), 401



            if expiry_time - current_time_utc < datetime.timedelta(hours=6):
                new_expiry_date = current_time_utc + datetime.timedelta(hours=12)
                db.execute('UPDATE users SET session_token_expiry = ? WHERE uuid = ?',
                           (new_expiry_date.isoformat(), user['uuid']))
                db.commit()
                app.logger.info(f"为用户(uuid:{user['uuid']}, name:{user['nickname']})的会话(session:{token[:8]}...)自动续期。")
                app.logger.info(f"Session for user '{user['nickname']}' has been refreshed (slid forward).")



            return f(user, *args, **kwargs)

        except (ValueError, TypeError) as e:

            app.logger.error(f"Invalid session expiry format for user: {user.get('nickname', 'Unknown')}, format: '{session_expiry_str}', error: {e}")
            return jsonify({"error": "会话状态异常，请重新登录"}), 401
        except Exception as e:

            app.logger.error(f"An unexpected error occurred during token verification: {e}", exc_info=True)
            return jsonify({"error": "服务器内部错误"}), 500
        finally:

            if db:
                db.close()

    return decorated_function

def admin_required(f):

    @wraps(f)

    def decorated_function(user, *args, **kwargs):

        if user['role'] != 'admin':
            app.logger.warning(f"非管理员用户(name:{user['nickname']}, uuid:{user['uuid']})尝试访问管理员接口。")

            return jsonify({"error": "权限不足，需要管理员权限。"}), 403


        return f(user, *args, **kwargs)
    return decorated_function


def clean_proxies(proxies_list):
    if not isinstance(proxies_list,list):return[]
    for proxy in proxies_list:
        if isinstance(proxy,dict)and'name'in proxy:proxy['name']=bleach.clean(proxy.get('name',''))[:50]
    return proxies_list



@app.route('/api/login/get_challenge', methods=['POST'])
@limiter.limit("20/minute")
def get_login_challenge():
    data = request.get_json()
    nickname = data.get('nickname')
    if not nickname:
        return jsonify({"error": "需要提供用户名以获取挑战码。"}), 400

    challenge_string = secrets.token_hex(32)
    with challenges_lock:
        login_challenges[challenge_string] = {
            "nickname": nickname,
            "expires_at": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=60)
        }
    return jsonify({"challenge": challenge_string})

@app.route('/api/register', methods=['POST'])
@limiter.limit("5/hour; 2/minute")
def register():
    data = request.get_json();
    if not data: return jsonify({"error": "请求体不能为空"}), 400
    nickname = data.get('nickname'); password = data.get('password'); invite_code = data.get('invite_code', '').strip().upper()
    nickname = bleach.clean(nickname).strip()
    if nickname.lower() == 'all': return jsonify({"error": "昵称 'all' 是保留关键字，不允许注册。"}), 400
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', nickname): return jsonify({"error": "昵称格式不正确，只允许3-20位的字母、数字和下划线。"}), 400
    is_valid, message = validate_invite_code_format(invite_code)
    if not is_valid: return jsonify({"error": message}), 403
    db=get_db();code_row = db.execute('SELECT * FROM invitation_codes WHERE code = ?', (invite_code,)).fetchone()
    if code_row is None: db.close(); return jsonify({"error": "邀请码无效或不存在"}), 403
    if code_row['is_used']: db.close(); return jsonify({"error": "此邀请码已被使用"}), 403
    if db.execute('SELECT uuid FROM users WHERE nickname = ?', (nickname,)).fetchone() is not None: db.close(); return jsonify({"error": "此昵称已被注册"}), 409
    password_hash = ph.hash(password); new_uuid = str(uuid.uuid4())
    db.execute('INSERT INTO users (uuid, nickname, password_hash) VALUES (?, ?, ?)', (new_uuid, nickname, password_hash))
    default_config_id = f'conf-{uuid.uuid4()}'; default_profile_name = '我的云端配置'; default_config_json = '{}'
    db.execute('INSERT INTO personal_configs (config_id, owner_uuid, profile_name, config_json) VALUES (?, ?, ?, ?)', (default_config_id, new_uuid, default_profile_name, default_config_json))
    db.execute('UPDATE invitation_codes SET is_used = 1, used_by_uuid = ?, used_at = CURRENT_TIMESTAMP WHERE code = ?', (new_uuid, invite_code))
    db.commit(); db.close()
    app.logger.info(f"新用户注册成功: {nickname} (uuid: {new_uuid})")
    app.logger.info(f"New user registered: {nickname}")
    return jsonify({"success": True, "message": "注册成功"})

@app.route('/api/perform_password_reset', methods=['POST'])
@limiter.limit("5/minute")
def perform_password_reset():
    data = request.get_json()
    nickname = bleach.clean(data.get('nickname', '')).strip()
    reset_token = data.get('reset_token', '').strip()
    new_password = data.get('new_password')

    if not (nickname and reset_token and new_password):
        return jsonify({"error": "所有字段均不能为空。"}), 400

    db = get_db()

    token_data = db.execute("SELECT user_uuid, expires_at FROM password_reset_tokens WHERE token = ?", (reset_token,)).fetchone()

    if not token_data:
        db.close(); return jsonify({"error": "密码重置令牌无效或已使用。"}), 404


    expiry_time = datetime.datetime.fromisoformat(token_data['expires_at'])
    if expiry_time < datetime.datetime.now(datetime.timezone.utc):
        db.execute("DELETE FROM password_reset_tokens WHERE token = ?", (reset_token,)); db.commit(); db.close()
        return jsonify({"error": "密码重置令牌已过期。"}), 410


    user = db.execute("SELECT nickname FROM users WHERE uuid = ?", (token_data['user_uuid'],)).fetchone()
    if not user or user['nickname'] != nickname:
        db.close(); return jsonify({"error": "令牌与用户信息不匹配。"}), 403


    new_password_hash = ph.hash(new_password)
    db.execute("UPDATE users SET password_hash = ? WHERE uuid = ?", (new_password_hash, token_data['user_uuid']))
    db.execute("DELETE FROM password_reset_tokens WHERE token = ?", (reset_token,))
    db.commit()
    db.close()

    app.logger.info(f"用户 {nickname} 成功使用令牌重置了密码。")
    return jsonify({"success": True, "message": "密码已成功重置！请使用新密码登录。"})

@app.route('/api/initiate_password_reset', methods=['POST'])
@token_required
@admin_required
def initiate_password_reset(user):

    data = request.get_json()
    target_nickname = data.get('nickname')

    db = get_db()
    target_user = db.execute("SELECT uuid FROM users WHERE nickname = ?", (target_nickname,)).fetchone()
    db.close()

    if not target_user:
        return jsonify({"error": "目标用户不存在"}), 404

    reset_token = f"RESET-{secrets.token_hex(16)}"
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)

    with reset_tokens_lock:



        db = get_db()

        db.execute("DELETE FROM password_reset_tokens WHERE user_uuid = ?", (target_user['uuid'],))
        db.execute("INSERT INTO password_reset_tokens (token, user_uuid, expires_at) VALUES (?, ?, ?)",
                   (reset_token, target_user['uuid'], expires_at.isoformat()))
        db.commit()
        db.close()

    app.logger.info(f"管理员 '{user['nickname']}' 为用户 '{target_nickname}' 创建了密码重置令牌并清理了旧令牌。")
    return jsonify({"success": True, "reset_token": reset_token})

def set_new_session(db, user_uuid):
    session_token = str(uuid.uuid4())

    expiry_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)
    db.execute('UPDATE users SET current_session_token = ?, session_token_expiry = ? WHERE uuid = ?',
               (session_token, expiry_date.isoformat(), user_uuid))
    return session_token

@app.route('/api/login', methods=['POST'])
@limiter.limit("20/minute")
def login():
    data = request.get_json()
    if not data: return jsonify({"error": "请求体不能为空"}), 400


    challenge = data.get('challenge')
    client_proof = data.get('proof')
    client_secret = data.get('version_secret')
    client_dll_hash = data.get('dll_hash')
    client_claimed_version_str = str(data.get('version', ''))


    client_claimed_version_str = str(data.get('version', ''))

    if not all([challenge, client_proof, client_secret, client_dll_hash]):
        return jsonify({"error": "登录请求缺少必要的校验信息。"}), 400


    server_record = TRUSTED_SECRET_MAP.get(client_secret)
    if not server_record:
        app.logger.error(f"登录失败：未知的版本秘密！用户: {data.get('nickname')}")
        return jsonify({"error": "客户端版本不受信任或已作废。"}), 403


    real_version_str = str(server_record['version'])
    real_dll_hash = server_record['dll_hash']


    if client_claimed_version_str != real_version_str:
        app.logger.error(f"版本声明不匹配！用户: {data.get('nickname')}, 声称版本: {client_claimed_version_str}, 真实版本: {real_version_str}")
        return jsonify({"error": "客户端版本信息与身份不符。"}), 403


    if client_dll_hash != real_dll_hash:
        app.logger.error(f"DLL哈希与版本记录不匹配！用户: {data.get('nickname')}")
        return jsonify({"error": "核心组件与客户端版本不匹配。"}), 403


    with challenges_lock:
        challenge_data = login_challenges.pop(challenge, None)
    if not challenge_data or datetime.datetime.now(datetime.timezone.utc) > challenge_data['expires_at']:
        return jsonify({"error": "无效或已过期的挑战码。"}), 403


    message_to_hash = f"{client_secret}:{client_dll_hash}:{client_claimed_version_str}:{challenge}"
    h = hashlib.sha256()
    h.update(message_to_hash.encode('utf-8'))
    server_proof = h.hexdigest()

    if server_proof != client_proof:
        app.logger.error(f"登录证明(proof)校验失败！用户: {data.get('nickname')}")
        return jsonify({"error": "客户端身份证明校验失败。"}), 403


    try:

        client_version_num = int(re.search(r'\d+', client_claimed_version_str).group())
    except (TypeError, AttributeError):

        client_version_num = 0

    if client_version_num < MIN_CLIENT_VERSION:
        error_message = f"客户端版本过低，当前最新版本为 {LATEST_CLIENT_VERSION_STR}，请更新！"
        app.logger.warning(f"用户 '{data.get('nickname')}' 使用过低版本({client_claimed_version_str})尝试登录被拒绝。")
        return jsonify({"error": error_message, "latest_version": LATEST_CLIENT_VERSION_STR}), 426




    nickname = data.get('nickname')
    password = data.get('password')

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE nickname = ?', (nickname,)).fetchone()

    if user is None:
        db.close()
        app.logger.warning(f"不存在的用户 '{nickname}' 尝试登录。")
        app.logger.warning(f"Login failed for non-existent user: {nickname}")
        return jsonify({"error": "昵称或密码错误"}), 401

    try:

        ph.verify(user['password_hash'], password)


        if ph.check_needs_rehash(user['password_hash']):
            new_hash = ph.hash(password)
            db.execute('UPDATE users SET password_hash = ? WHERE uuid = ?', (new_hash, user['uuid']))
            db.commit()
            app.logger.info(f"Password hash rehashed for user: {user['nickname']}")
    except VerifyMismatchError:
        db.close()
        app.logger.warning(f"用户(uuid:{user['uuid']}, name:{user['nickname']})登录时密码错误。")
        app.logger.warning(f"Login failed (wrong password) for user: {nickname}")
        return jsonify({"error": "昵称或密码错误"}), 401


    session_token = set_new_session(db, user['uuid'])
    response_data = {"success": True, "session_token": session_token}

    db.commit()
    db.close()
    app.logger.info(
        f"用户成功登录并通过所有安全校验: name='{nickname}', "
        f"uuid='{user['uuid']}', "
        f"session_id='{session_token[:8]}...'"
    )
    return jsonify(response_data)

@app.route('/api/session/check', methods=['POST'])
@token_required
def check_session(user): return jsonify({"valid": True})

@app.route('/api/configs', methods=['GET', 'POST'])
@token_required
def handle_configs(user):
    db = get_db()
    if request.method == 'GET':
        configs_cursor=db.execute('SELECT * FROM personal_configs WHERE owner_uuid = ?',(user['uuid'],));personal_configs=[dict(row)for row in configs_cursor];subs_cursor=db.execute('SELECT T1.subscription_id, T1.share_id, T1.user_params_json, T2.share_name, T2.is_template, T2.config_data_json as share_config_json FROM subscriptions T1 JOIN shares T2 ON T1.share_id = T2.share_id WHERE T1.user_uuid = ?',(user['uuid'],));subscriptions=[dict(row)for row in subs_cursor];db.close();return jsonify({'personal_configs':personal_configs,'subscriptions':subscriptions})
    if request.method == 'POST':
        data=request.get_json();personal_configs=data.get('personal_configs',[]);subscriptions=data.get('subscriptions',{})
        for config in personal_configs:
            if'profile_name'in config:config['profile_name']=bleach.clean(config.get('profile_name',''))[:50]
            if'config_json'in config:
                try:
                    config_data=json.loads(config['config_json'])
                    if'nodes'in config_data:
                        for node in config_data.get('nodes',[]):
                            if'remark'in node:node['remark']=bleach.clean(node.get('remark',''))[:50]
                    if'proxies'in config_data:config_data['proxies']=clean_proxies(config_data.get('proxies',[]))
                    config['config_json']=json.dumps(config_data)
                except json.JSONDecodeError:config['config_json']='{}'
        for sub_id,sub_data in subscriptions.items():
            if'user_params'in sub_data:
                user_params=sub_data['user_params']
                if'proxies'in user_params:user_params['proxies']=clean_proxies(user_params.get('proxies',[]))
                sub_data['user_params']=user_params
        db.execute('DELETE FROM personal_configs WHERE owner_uuid = ?',(user['uuid'],));db.execute('DELETE FROM subscriptions WHERE user_uuid = ?',(user['uuid'],))
        for config in personal_configs:db.execute('INSERT INTO personal_configs (config_id, owner_uuid, profile_name, config_json) VALUES (?, ?, ?, ?)',(config['config_id'],user['uuid'],config['profile_name'],config['config_json']))
        for sub_id,sub_data in subscriptions.items():db.execute('INSERT INTO subscriptions (subscription_id, user_uuid, share_id, user_params_json) VALUES (?, ?, ?, ?)',(sub_id,user['uuid'],sub_data.get('share_id'),json.dumps(sub_data.get('user_params',{}))))
        db.commit();db.close();return jsonify({"success":True,"message":"配置已成功保存"})

@app.route('/api/share/create', methods=['POST'])
@token_required
def create_share(user):
    data=request.get_json();share_name=bleach.clean(data.get('share_name',''))[:50];is_template=data.get('is_template',False);config_data=data.get('config_data')
    if not(share_name and config_data is not None):return jsonify({"error":"缺少分享名称或配置数据"}),400
    if isinstance(config_data,dict):
        if'nodes'in config_data:
            for node in config_data.get('nodes',[]):
                if'remark'in node:node['remark']=bleach.clean(node.get('remark',''))[:50]
        if'proxies'in config_data:config_data['proxies']=clean_proxies(config_data.get('proxies',[]))
    share_id=f"share-{uuid.uuid4()}";owner_uuid=user['uuid'];config_data_json=json.dumps(config_data);db=get_db()
    db.execute('INSERT INTO shares (share_id, owner_uuid, share_name, is_template, config_data_json) VALUES (?, ?, ?, ?, ?)',(share_id,owner_uuid,share_name,is_template,config_data_json));db.commit();db.close();return jsonify({"success":True,"share_id":share_id})

@app.route('/api/share/list', methods=['GET'])
@token_required
def list_shares(user):db=get_db();shares=db.execute('SELECT share_id, share_name, is_template FROM shares WHERE owner_uuid = ?',(user['uuid'],)).fetchall();db.close();return jsonify([dict(row)for row in shares])
@app.route('/api/share/revoke', methods=['POST'])
@token_required
def revoke_share(user): data = request.get_json(); share_id = data.get('share_id') or abort(make_response(jsonify({"error": "缺少 share_id"}), 400)); db = get_db(); db.execute('DELETE FROM shares WHERE share_id = ? AND owner_uuid = ?', (share_id, user['uuid'])); db.commit(); db.close(); return jsonify({"success": True})
@app.route('/api/share/get_public_info/<string:share_id>', methods=['GET'])
def get_share_public_info(share_id):
    db=get_db();share=db.execute('SELECT share_name, is_template, config_data_json FROM shares WHERE share_id = ?',(share_id,)).fetchone();db.close()
    if not share:return jsonify({"error":"分享不存在或已撤销"}),404
    config_data=json.loads(share['config_data_json']);public_info={"share_name":share['share_name'],"is_template":share['is_template']}
    if share['is_template']:public_info['nodes']=[{"remark":node.get("remark"),"server_addr":node.get("server_addr"),"server_port":node.get("server_port")}for node in config_data.get('nodes',[])]
    return jsonify(public_info)
@app.route('/api/share/use', methods=['POST'])
def use_share():
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    share_id = data.get('share_id')
    user_params = data.get('user_params') or {}
    if not share_id:
        return jsonify({"error": "缺少share_id"}), 400

    db = get_db()
    share = db.execute('SELECT is_template, config_data_json FROM shares WHERE share_id = ?', (share_id,)).fetchone()
    db.close()
    if not share:
        return jsonify({"error": "分享不存在或已撤销"}), 404

    try:
        config_data = json.loads(share['config_data_json'])
    except json.JSONDecodeError:
        return jsonify({"error": "分享配置已损坏"}), 500


    final_config = OrderedDict()

    if share['is_template']:

        selected_node_remark = user_params.get('node_remark')
        if not selected_node_remark:
            return jsonify({"error": "模板分享需要选择一个节点"}), 400

        selected_node_info = next((n for n in config_data.get('nodes', []) if n.get('remark') == selected_node_remark), None)
        if not selected_node_info:
            return jsonify({"error": f"选择的节点 '{selected_node_remark}' 无效"}), 400


        final_config['serverAddr'] = str(selected_node_info.get('server_addr', ''))
        final_config['serverPort'] = int(selected_node_info.get('server_port', 0))
        final_config['auth'] = {'token': str(selected_node_info.get('token', ''))}


        final_proxies = []
        for p_in in user_params.get('proxies', []):
            p_out = {}
            p_out['name'] = p_in.get('name')
            p_out['type'] = p_in.get('type')
            if not all([p_out['name'], p_out['type']]): continue

            p_out['localIP'] = p_in.get('local_ip', '127.0.0.1')
            p_out['localPort'] = int(p_in.get('local_port', 0))
            if p_out['type'] in ['http', 'https']:
                if p_in.get('custom_domains'): p_out['custom_domains'] = [d.strip() for d in str(p_in['custom_domains']).split(',') if d.strip()]
            else:
                p_out['remotePort'] = int(p_in.get('remote_port', 0))
            final_proxies.append(p_out)

        if final_proxies:
            final_config['proxies'] = final_proxies

    else:


        final_config['serverAddr'] = str(config_data.get('serverAddr', config_data.get('server_addr', '')))
        final_config['serverPort'] = int(config_data.get('serverPort', config_data.get('server_port', 0)))
        auth_info = config_data.get('auth', {})
        final_config['auth'] = {'token': str(auth_info.get('token', ''))}


        final_proxies = []
        for p_in in config_data.get('proxies', []):
            p_out = {}
            p_out['name'] = p_in.get('name')
            p_out['type'] = p_in.get('type')
            if not all([p_out['name'], p_out['type']]): continue

            p_out['localIP'] = p_in.get('localIP', p_in.get('local_ip', '127.0.0.1'))
            try: p_out['localPort'] = int(p_in.get('localPort', p_in.get('local_port', 0)))
            except (ValueError, TypeError): p_out['localPort'] = 0

            if p_out['type'] in ['http', 'https']:
                custom_domains_val = p_in.get('custom_domains', [])
                if isinstance(custom_domains_val, str): p_out['custom_domains'] = [d.strip() for d in custom_domains_val.split(',') if d.strip()]
                else: p_out['custom_domains'] = custom_domains_val
            else:
                try: p_out['remotePort'] = int(p_in.get('remotePort', p_in.get('remote_port', 0)))
                except (ValueError, TypeError): p_out['remotePort'] = 0

            final_proxies.append(p_out)

        if final_proxies:
            final_config['proxies'] = final_proxies


    if not final_config or not final_config.get('serverAddr'):
        return jsonify({"error": "生成最终配置失败"}), 500

    return jsonify({"final_toml_data": dict(final_config)})

@app.route('/api/request_config_ticket', methods=['POST'])
@token_required
def request_config_ticket(user):




    user_uuid = user['uuid']
    current_time = datetime.datetime.now(datetime.timezone.utc)

    with rate_limit_lock:
        last_request_time = rate_limit_tracker.get(user_uuid)


        if last_request_time:
            time_since_last_request = (current_time - last_request_time).total_seconds()


            if time_since_last_request < 3.0:
                wait_time = 3.0 - time_since_last_request
                app.logger.warning(f"用户 '{user['nickname']}' (UUID: {user_uuid}) 触发速率限制，需等待 {wait_time:.1f} 秒。")

                return jsonify({"error": f"请求过于频繁，请在 {wait_time:.1f} 秒后重试。"}), 429


        rate_limit_tracker[user_uuid] = current_time


    data = request.get_json()
    config_content = data.get('config_content')
    if not config_content:

        with rate_limit_lock:
            if user_uuid in rate_limit_tracker:
                 del rate_limit_tracker[user_uuid]
        return jsonify({"error": "缺少配置内容"}), 400

    config_id = str(uuid.uuid4())

    with configs_lock:
        one_time_configs[config_id] = {
            "content": config_content,
            "expires_at": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=10),
            "uses_left": 2,
            "history": [],
            "first_use_time": None
        }

    app.logger.info(
        f"为用户(uuid:{user['uuid']}, name:{user['nickname']}) "
        f"创建了配置票据(ID: {config_id})"
    )
    return jsonify({"success": True, "config_id": config_id})



@app.route('/api/get_temp_config/<string:config_id>', methods=['GET'])
def get_temp_config(config_id):

    with configs_lock:
        config_data = one_time_configs.get(config_id)

        if not config_data:
            return "Configuration not found, expired, or already used.", 404

        current_time = datetime.datetime.now(datetime.timezone.utc)


        if current_time > config_data['expires_at']:

            history_log = ", ".join([f"于{h['time'].strftime('%H:%M:%S')}被IP {h['ip']} 使用" for h in config_data.get('history', [])])
            if not history_log: history_log = "但从未使用过"
            app.logger.warning(f"对已超时的票据(ID: {config_id})的访问被拒绝。该票据的历史: {history_log}。")
            del one_time_configs[config_id]
            return "Configuration link has expired.", 410




        first_use_time = config_data.get('first_use_time')

        if first_use_time:

            SECONDS_TO_SECOND_USE = 2.0
            time_since_first_use = (current_time - first_use_time).total_seconds()

            if time_since_first_use > SECONDS_TO_SECOND_USE:

                history_log = f"于{first_use_time.strftime('%H:%M:%S')}被IP {config_data['history'][0]['ip']} 首次使用"
                app.logger.warning(f"票据(ID: {config_id})因首次使用后超时而被拒绝。历史: {history_log}。")
                del one_time_configs[config_id]
                return "Secondary use window for configuration link has expired.", 410



        if config_data['uses_left'] > 0:
            config_data['uses_left'] -= 1


            if config_data.get('first_use_time') is None:
                config_data['first_use_time'] = current_time



            real_ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
            usage_record = {
                "ip": real_ip,
                "time": datetime.datetime.now(datetime.timezone.utc)
            }
            config_data['history'].append(usage_record)

            use_count = len(config_data['history'])
            app.logger.info(f"票据(ID: {config_id})被IP {request.remote_addr} 成功使用第 {use_count} 次。")

            content = config_data['content']
            response = make_response(content)
            response.mimetype = "text/plain; charset=utf-8"

            if config_data['uses_left'] == 0:
                app.logger.info(f"票据(ID: {config_id})已用尽，将被删除。")
                del one_time_configs[config_id]

            return response
        else:


            history_log = ", ".join([f"于{h['time'].strftime('%H:%M:%S')}被IP {h['ip']} 使用" for h in config_data.get('history', [])])
            app.logger.error(f"对已用尽次数的票据(ID: {config_id})的异常访问！访问IP: {request.remote_addr}。该票据的历史: {history_log}。")

            if config_id in one_time_configs:
                del one_time_configs[config_id]
            return "Configuration not found, expired, or already used.", 404


def cleanup_rate_limit_tracker():
    while True:

        time.sleep(300)
        with rate_limit_lock:
            current_time = datetime.datetime.now(datetime.timezone.utc)

            keys_to_delete = [
                uuid for uuid, last_time in rate_limit_tracker.items()
                if (current_time - last_time).total_seconds() > 900
            ]


            for key in keys_to_delete:
                del rate_limit_tracker[key]

            if keys_to_delete:
                app.logger.info(f"后台清理：移除了 {len(keys_to_delete)} 个旧的速率限制记录。")

if __name__ == '__main__':
    init_db()


    cleanup_thread = threading.Thread(target=cleanup_rate_limit_tracker, daemon=True)
    cleanup_thread.start()

    app.run(host='127.0.0.1', port=5000)