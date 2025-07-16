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