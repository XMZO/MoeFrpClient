# config.py
# 应用的所有全局常量和配置
 
# --- 服务器与版本 ---
import os

CLOUD_SERVER_URL = "http://127.0.0.1:5000" # 自己改
CLIENT_VERSION = ""  # 用于和服务器比较的整数版本号
CLIENT_VERSION_STR = "" # 用于UI显示的字符串版本号
VERSION_SECRET = ""
 
# --- 图片获取 ---
IMAGE_SOURCES = [
  {
    "url": "https://api.lolicon.app/setu/v2?r18=0&num=1&size=regular&proxy=i.pixiv.re&excludeAI=true",
    "weight": 7,
    "is_api": True,
    "json_path": "data.0.urls.regular"
  },
  {
    "url": "https://image.anosu.top/pixiv/json?r18=0&size=regular&num=1&keyword=loli",
    "weight": 2,
    "is_api": True,
    "json_path": "0.url"
  },
  {
    "url": "https://moe.jitsu.top/img",
    "weight": 1,
    "is_api": False
  }
]
IMAGE_REFRESH_INTERVAL_MS = 20000 # 图片刷新间隔（毫秒）
IMAGE_FETCH_GLOBAL_TIMEOUT_MS = 15000 # 全局获取超时（15秒）
# --- 应用基本信息 ---
APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 图标存储
CUTE_SAVE_ICON_BASE64 = b'iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAACxMAAAsTAQCanBgAAAH8SURBVHhe7dsxSh1hGEbhq1uwEkREm6AIFtE6ImQB6SRWl2wgrYWFhW02IFZKuiwgIFpHC0EMNorIBaugrkAtvjJe/uKF/xTnAfHtZuAowzAzE1+OVl8Gwpis34IwCIxBYAwCYxAYg8AYBMYgMAaBMQiMQWAMAmMQGIPAGATGIDAGgTEIjEFg4s/Ur08eamV8WJ+ulUE/v3iQPwe3tTLWhvO1MujnFw/y6+tZrYy386uVQT8/ryEwBoExCIxBYAwCYxAYg8AYBMYgMAaBMQiMQWAMAmMQGIPAGATGIDDxJ4YfV5ZrZRz++F0rY+v751oZ5xeXtTLiQRbmZmtl/Nw5rZWxufupVsbN3X2tjHiQNPoz8DSvITAGgTEIjEFgDAJjEBiDwHS7D2l9C/3v/qhWxuK3mVrjpd9qb9UtSOtb6KPjf7UyZjamao2Xfqu9Vbcg6TvwtF539F5DYAwCYxAYg8AYBMYgMAaBMQiMQWAMAmMQGIPAGATGIDAGgTEIjEFg8E8M966GtTK2lw5qjecTw3c8Pj1Hf+jw/yHpv9Rex23lNQTGIDAGgTEIjEFgDAJjEJhu9yGt37OnvwPvddxW3YK0fs+e/g6813FbdQui//MaAmMQGIPAGATGIDAGgTEIjEFgDAJjEBiDwBgExiAwBoExCIxBYAyCMhi8AuPjoX9v8qVkAAAAAElFTkSuQmCC'
CUTE_COPY_ICON_BASE64 = b'UklGRq4AAABXRUJQVlA4TKIAAAAvD8ADEJegIADIxqd/DmWkYTeHoraNmNsQj//nMOyT1Ma2Df19oyf9lyITyfgE2TalmL/eTxHpawepMCWc/4q5OKRPmJBNxEzoQWbycoBrNajY9TfMo78ZGDSSpOj4nsm/XJTQHdH/CdhYVFgFCHzLViLdervxDXZORyZ05x+9GIELXf0jOTg7Ukj+ke2ODB42IxvfViPpttJd/LaxCllefgE='
# Dialogs

CUTE_SAVE_AS_ICON_BASE64 = b'iVBORw0KGgoAAAANSUhEUgAAAGAAAABgBAMAAAAQtmoLAAAABGdBTUEAALGPC/xhBQAAAAFzUkdCAdnJLH8AAAAgY0hSTQAAeiYAAICEAAD6AAAAgOgAAHUwAADqYAAAOpgAABdwnLpRPAAAABVQTFRF/9OH+vn/2djcvr3B96h2xG9R0UVCsUrbXwAAAGdJREFUeNrt17EJwDAMRFGvkBW0glfwCloh+48QODWCI8aFy//Lg9cKe1SrNVq+AwC++5Q/rRYAsAepHitUKgBgD6oOXhVqqlRDAQDnIFQxAOAc9EMWalr9kAEABngkAu4CfruAW+ADwtG8bhnpZqgAAAAASUVORK5CYII='
# MainWindow