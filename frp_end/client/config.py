



import os


CLOUD_SERVER_URL = "http://127.0.0.1:5000"
CLIENT_VERSION = "999"
CLIENT_VERSION_STR = "v9.9.9"
VERSION_SECRET = "999"


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
IMAGE_REFRESH_INTERVAL_MS = 20000
IMAGE_FETCH_GLOBAL_TIMEOUT_MS = 15000


APP_BASE_DIR = os.path.dirname(os.path.abspath(__file__))