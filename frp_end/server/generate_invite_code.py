import sqlite3
import sys
import os
import secrets
import string
import argparse
from datetime import datetime
import requests # 【新】用于API请求
import json
import hashlib
import getpass # 【新】用于安全地输入密码

# 确保脚本能找到数据库文件
APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(APP_BASE_DIR, 'users.db')
SERVER_URL = "http://127.0.0.1:5000"

# 【新】从服务器端复制过来的客户端识别信息，必须保持一致
# (在真实项目中，这些可以放到一个共享的配置文件中)
CLIENT_VERSION = "114514"
CLIENT_VERSION_STR = "v1.14.514"
VERSION_SECRET = "$argon2id$v=19$m=100000,t=20,p=10$bG9saWxvbGk$dc4K33OREII0AR0troSUvbgKFNBehW3bdsbpYY34NuRvJ0zoOEPsbTtHtuBkeleI/DSnaKs0GmBOr7O+X1w2IMnXWScflssGH6BtO+jpyB2ecmEl4d65uf3tiaFdAsEz1YFGEg"
# 在这个脚本中，我们不校验DLL，所以可以留空或填一个假值
DLL_HASH = "imwood"

# --- 邀请码生成逻辑 ---
CUSTOM_CHARSET = string.ascii_uppercase.replace('I', '').replace('L', '').replace('O', '') + '23456789'
def luhn_checksum(code_str):
    digits=[CUSTOM_CHARSET.find(c) for c in code_str]; s=0; p=len(digits)%2
    if any(d == -1 for d in digits): return 'X'
    for i, d in enumerate(digits):
        if i % 2 == p: d *= 2
        if d >= len(CUSTOM_CHARSET): d = (d % len(CUSTOM_CHARSET)) + (d // len(CUSTOM_CHARSET))
        s += d
    return CUSTOM_CHARSET[(s * 9) % len(CUSTOM_CHARSET)]

def generate_secure_code():
    code_body = ''.join(secrets.choice(CUSTOM_CHARSET) for _ in range(7))
    checksum = luhn_checksum(code_body)
    full_code = f"{code_body}{checksum}"
    return f"FRPT-{full_code[:4]}-{full_code[4:]}"

# --- 数据库操作函数 ---
def add_codes_to_db(db, count=1):
    if count<=0: return
    c=db.cursor(); g=[]
    print("-" * 30 + "\n[操作] 生成新邀请码")
    for _ in range(count):
        while True:
            new_code = generate_secure_code()
            try: c.execute("INSERT INTO invitation_codes (code) VALUES (?)", (new_code,)); g.append(new_code); break
            except sqlite3.IntegrityError: print("警告: 邀请码冲突，正在重新生成...")
    if g: print(f"成功生成 {len(g)} 个新邀请码:\n" + "\n".join([f"  {x}" for x in g]))
    else: print("未能生成新邀请码。")
    db.commit()

def display_codes_status(db):
    c=db.cursor(); c.execute("SELECT ic.code,ic.is_used,ic.created_at,ic.used_at,u.nickname FROM invitation_codes ic LEFT JOIN users u ON ic.used_by_uuid=u.uuid ORDER BY ic.created_at DESC")
    a=c.fetchall(); u=[r for r in a if not r[1]]; d=[r for r in a if r[1]]
    print("-" * 30 + f"\n[状态] 邀请码总览 (总数: {len(a)})\n" + "-" * 30)
    print(f"\n✅ 未使用 ({len(u)} 个):")
    if not u: print("  (无)")
    else:
        for code, _, created_at, _, _ in u:
            ct="时间未知";
            if created_at: ct=datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M')
            print(f"  {code:<20} (创建于: {ct})")
    print(f"\n❌ 已使用 ({len(d)} 个):")
    if not d: print("  (无)")
    else:
        for code, _, _, used_at, nickname in d:
            ui=nickname if nickname else "未知用户"; ut="时间未知"
            if used_at:
                try: ut=datetime.fromisoformat(used_at).strftime('%Y-%m-%d %H:%M')
                except (ValueError, TypeError): ut="格式错误"
            print(f"  {code:<20} (使用者: {ui}, 使用于: {ut})")
    print("\n" + "-" * 30)

def delete_code(db, target):
    cursor=db.cursor()
    if target.lower() == 'all':
        print("-" * 30 + "\n[操作] 删除所有未使用的邀请码")
        cursor.execute("SELECT COUNT(*) FROM invitation_codes WHERE is_used = 0")
        count = cursor.fetchone()[0]
        if count == 0: print("信息: 没有未使用的邀请码可以删除。"); return
        print("\n"+"!"*50+f"\n警告: 您即将永久删除 {count} 个未使用的邀请码！\n此操作无法撤销！\n"+"!"*50+"\n")
        confirm = input("请输入 'confirm' 以确认删除: ")
        if confirm.strip().lower() != 'confirm': print("输入不匹配，操作已取消。"); return
        cursor.execute("DELETE FROM invitation_codes WHERE is_used = 0"); db.commit()
        print(f"\n成功: {count} 个未使用的邀请码已被彻底删除。")
    else:
        code_to_delete = target.strip().upper()
        print("-" * 30 + f"\n[操作] 删除邀请码: {code_to_delete}")
        cursor.execute("SELECT is_used FROM invitation_codes WHERE code = ?", (code_to_delete,))
        result = cursor.fetchone()
        if result is None: print(f"错误: 找不到邀请码 '{code_to_delete}'。"); return
        if result[0]: print(f"错误: 邀请码 '{code_to_delete}' 已被使用，无法删除。"); return
        cursor.execute("DELETE FROM invitation_codes WHERE code = ?", (code_to_delete,)); db.commit()
        print(f"成功: 未使用的邀请码 '{code_to_delete}' 已被删除。")

def delete_user(db, target):
    cursor=db.cursor()
    if target.lower() == 'all':
        print("-" * 30 + "\n[操作] 删除所有用户")
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        if count == 0: print("信息: 数据库中没有用户可以删除。"); return
        print("\n"+"!"*60+"\n警告: 史诗级毁灭性操作！您即将删除所有 {count} 个用户！\n这将清除他们的所有数据和使用的邀请码！\n此操作无法撤销！\n"+"!"*60+"\n")
        confirm = input("请输入 'confirm' 以确认删除: ")
        if confirm.strip().lower() != 'confirm': print("输入不匹配，操作已取消。"); return
        cursor.execute("DELETE FROM invitation_codes WHERE is_used = 1"); cursor.execute("DELETE FROM users"); db.commit()
        print(f"\n成功: {count} 个用户及其所有数据均已被彻底清除。")
    else:
        nickname=target.strip()
        print("-" * 30 + f"\n[操作] 删除用户: {nickname}")
        cursor.execute("SELECT uuid, nickname FROM users WHERE nickname = ?", (nickname,))
        user = cursor.fetchone()
        if user is None: print(f"错误: 找不到用户 '{nickname}'。"); return
        user_uuid, user_nickname = user
        print("\n"+"!"*50+f"\n警告: 这是一个毁灭性操作！\n您即将永久删除用户 '{user_nickname}' (UUID: {user_uuid})及其所有数据和邀请码！\n此操作无法撤销！\n"+"!"*50+"\n")
        confirm = input(f"请输入用户昵称 '{user_nickname}' 以确认删除: ")
        if confirm.strip() != user_nickname: print("输入不匹配，操作已取消。"); return
        cursor.execute("DELETE FROM invitation_codes WHERE used_by_uuid = ?", (user_uuid,)); cursor.execute("DELETE FROM users WHERE uuid = ?", (user_uuid,)); db.commit()
        print(f"\n成功: 用户 '{user_nickname}' 及其所有关联数据已被彻底删除。")

# --- 【新】一个简化的 ApiClient ---
class SimpleApiClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.timeout = 10

    def _make_request(self, method, endpoint, **kwargs):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            if response.status_code >= 400:
                try: message = response.json().get('error', f"服务器错误 {response.status_code}")
                except json.JSONDecodeError: message = f"服务器返回错误 {response.status_code}"
                return False, message
            return True, response.json()
        except requests.RequestException as e:
            return False, f"网络错误: {e}"

    def get_login_challenge(self, nickname):
        return self._make_request('POST', '/api/login/get_challenge', json={'nickname': nickname})

    def login(self, nickname, password, version, version_secret, dll_hash, challenge, proof):
        return self._make_request('POST', '/api/login', json={
            'nickname': nickname, 'password': password, 'version': version,
            'version_secret': version_secret, 'dll_hash': dll_hash,
            'challenge': challenge, 'proof': proof
        })
    
    def initiate_password_reset(self, token, target_nickname):
        return self._make_request('POST', '/api/initiate_password_reset',
                                  headers={"Authorization": f"Bearer {token}"},
                                  json={"nickname": target_nickname})

# --- 重置密码函数，现在调用新的登录逻辑 ---
def reset_user_password(db, api_client):
    if not display_user_list(db):return
    target_nickname=input("\n请输入要重置密码的用户昵称:").strip()
    if not target_nickname:print("错误:未输入昵称。");return
    admin_token=admin_login_for_token(api_client)
    if not admin_token:return
    print(f"正在为'{target_nickname}'请求重置令牌...");success,data=api_client.initiate_password_reset(admin_token,target_nickname)
    if success:
        token=data.get("reset_token");print("\n"+"*"*60+f"\n  ✅已为用户'{target_nickname}'生成令牌。\n  请将此【令牌】作为【邀请码】发给用户，去【注册】页面重设密码。\n\n      {token}\n\n  此令牌24小时内有效，且只能使用一次。\n"+"*"*60+"\n")
    else:print(f"->操作失败:{data}")
    
def display_user_list(db):
    """一个专门用于显示用户列表的辅助函数"""
    cursor = db.cursor()
    cursor.execute("SELECT nickname, uuid FROM users ORDER BY nickname")
    users = cursor.fetchall()
    if users:
        print("-" * 30 + "\n当前用户列表:")
        for nickname, uuid_val in users: print(f"  - {nickname:<20} (uuid: {uuid_val})")
        print("-" * 30); return True
    else:
        print("当前没有用户。"); return False

def interactive_menu(db, api_client):
    api_client = SimpleApiClient(SERVER_URL)
    """交互式菜单"""
    while True:
        print("\n" + "=" * 50); print("    FRP高级客户端 - 服务端管理工具"); print("=" * 50)
        print("1. 查看邀请码状态"); print("2. 生成邀请码"); print("3. 删除邀请码")
        print("4. 删除用户"); print("5. 重置用户密码"); print("6. 退出"); print("-" * 50)
        choice = input("请选择操作 (1-6): ").strip()
        
        if choice == '1': display_codes_status(db)
        elif choice == '2':
            try:
                count = input("请输入要生成的邀请码数量 (回车默认1个): ").strip()
                count = int(count) if count else 1
                if count <= 0: print("错误: 数量必须大于0"); continue
                add_codes_to_db(db, count); display_codes_status(db)
            except ValueError: print("错误: 请输入有效数字")
        elif choice == '3':
            display_codes_status(db)
            target = input("\n请输入要删除的邀请码 (或 'all' 删除所有未使用): ").strip()
            if target: delete_code(db, target)
        elif choice == '4':
            if display_user_list(db):
                target = input("\n请输入要删除的用户昵称 (或 'all'): ").strip()
                if target: delete_user(db, target)
        elif choice=='5':reset_user_password(db, api_client)
        elif choice == '6':
            print("再见！"); wait_any_key(); break
        else:
            print("无效选择，请重新输入")

def wait_any_key(prompt="按任意键退出..."):
    try: import msvcrt; print(prompt, end='', flush=True); msvcrt.getch()
    except ImportError: input(prompt)

# --- 【全新】安全的管理员登录函数 ---
def admin_login_for_token(api_client):
    """使用完整的挑战-响应流程进行管理员登录"""
    print("\n[安全操作] 需要管理员权限，请登录服务器账户。")
    nickname = input("请输入您的管理员昵称: ").strip()
    password = getpass.getpass("请输入您的管理员密码: ")
    
    if not (nickname and password):
        print(" -> 错误: 昵称和密码不能为空。")
        return None

    try:
        # 1. 获取挑战码
        print(" -> 正在获取安全挑战码...")
        success, data = api_client.get_login_challenge(nickname)
        if not success: raise Exception(f"获取挑战码失败: {data}")
        challenge = data.get('challenge')
        
        # 2. 计算登录证明
        print(" -> 正在计算登录证明...")
        message_to_hash = f"{VERSION_SECRET}:{DLL_HASH}:{CLIENT_VERSION}:{challenge}"
        h = hashlib.sha256()
        h.update(message_to_hash.encode('utf-8'))
        proof = h.hexdigest()

        # 3. 执行登录
        print(" -> 正在发送登录请求...")
        success, data = api_client.login(
            nickname, password, CLIENT_VERSION, VERSION_SECRET, DLL_HASH, challenge, proof
        )
        if not success: raise Exception(f"{data}")
            
        session_token = data.get("session_token")
        print(" -> 管理员登录成功！")
        return session_token

    except Exception as e:
        print(f" -> 登录流程失败: {e}")
        return None

def request_password_reset_token(admin_session_token, target_nickname):
    """使用管理员的token，为目标用户请求一个重置令牌"""
    print(f"正在为用户 '{target_nickname}' 请求密码重置令牌...")
    try:
        response = requests.post(
            f"{SERVER_URL}/api/initiate_password_reset",
            headers={"Authorization": f"Bearer {admin_session_token}"},
            json={"nickname": target_nickname},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                reset_token = data.get("reset_token")
                print("\n" + "*" * 60)
                print(f"  ✅ 已为用户 '{target_nickname}' 生成一次性密码重置令牌。")
                print(f"  请将此【令牌】作为发给用户，让他去【忘记密码】页面重设密码。")
                print(f"\n      {reset_token}\n")
                print("  此令牌24小时内有效，且只能使用一次。")
                print("*" * 60 + "\n")
            else:
                print(f" -> 操作失败: {response.json().get('error', '未知错误')}")
        else:
            print(f" -> 服务器错误 (状态码: {response.status_code}): {response.text}")
            
    except requests.RequestException as e:
        print(f" -> 网络错误，无法连接到服务器: {e}")

def main():
    parser = argparse.ArgumentParser(description="FRP高级客户端 - 服务端管理脚本", formatter_class=argparse.RawTextHelpFormatter)
    api_client = SimpleApiClient(SERVER_URL) # 创建API客户端实例
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-g', '--generate', nargs='?', type=int, const=1, default=None, metavar='COUNT', help="生成邀请码。不带数量则生成1个。")
    group.add_argument('-s', '--status', action='store_true', help="显示邀请码和用户状态。")
    group.add_argument('-du', '--delete-user', metavar='TARGET', help="删除用户。TARGET可以是昵称或'all'。")
    group.add_argument('-dc', '--delete-code', metavar='TARGET', help="删除邀请码。TARGET可以是码或'all'。")
    parser.add_argument('-rp', '--reset-password', metavar='NICKNAME', help="为指定用户生成密码重置令牌。")

    if len(sys.argv) > 1:
        args = parser.parse_args()
        if not os.path.exists(DATABASE): print(f"错误: 数据库 '{DATABASE}' 不存在。"); return
        try:
            db = sqlite3.connect(DATABASE, timeout=10); db.execute("PRAGMA foreign_keys = ON")
            if args.delete_user: delete_user(db, args.delete_user)
            elif args.delete_code: delete_code(db, args.delete_code)
            elif args.status: display_codes_status(db)
            elif args.generate is not None: add_codes_to_db(db, args.generate); display_codes_status(db)
            if args.reset_password:
                # 【修改】命令行重置密码也需要登录，并传入api_client
                admin_token = admin_login_for_token(api_client)
                if admin_token:
                    # 注意：命令行模式下，我们直接调用API，不需要db对象
                    request_password_reset_token(admin_token, args.reset_password)
            else: parser.print_help()
            db.close()
        except sqlite3.Error as e: print(f"数据库操作失败: {e}")
    else:
        if not os.path.exists(DATABASE): print(f"错误: 数据库 '{DATABASE}' 不存在。"); return
        try:
            db = sqlite3.connect(DATABASE, timeout=10); db.execute("PRAGMA foreign_keys = ON"); interactive_menu(db, api_client); db.close()
        except sqlite3.Error as e: print(f"数据库操作失败: {e}")

if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: print("\n检测到 Ctrl+C，程序已终止。")