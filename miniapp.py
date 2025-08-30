import os
import sqlite3
from urllib.parse import quote
from datetime import datetime
from flask import Flask, request, render_template_string

try:
    from config import DB_PATH
    from database import is_subscription_active_check
except Exception:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'users.db')

    def is_subscription_active_check(expiry_date_str: str) -> bool:
        if not expiry_date_str:
            return False
        for fmt in ('%d.%m.%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                expiry_date = datetime.strptime(expiry_date_str, fmt)
                return datetime.now() < expiry_date
            except ValueError:
                continue
        return False


app = Flask(__name__)


def fetch_user_row(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT subscribed, expiry_date, config FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            'subscribed': bool(row[0]),
            'expiry_date': row[1],
            'config_id': (row[2] or '').strip('"\'')
        }
    finally:
        conn.close()


PAGE_TEMPLATE = """
<!doctype html>
<html lang=\"ru\">
<head>
  <meta charset=\"utf-8\"/>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
  <title>Shard VPN — Мини‑приложение</title>
  <style>
    :root { color-scheme: light dark; }
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif; margin: 0; padding: 0; }
    .wrap { max-width: 720px; margin: 0 auto; padding: 24px; }
    .card { border: 1px solid rgba(0,0,0,.1); border-radius: 12px; padding: 20px; backdrop-filter: blur(6px); }
    h1 { margin: 0 0 8px; font-size: 22px; }
    .muted { opacity: .8; }
    .status { margin: 16px 0; padding: 12px 14px; border-radius: 10px; font-weight: 600; }
    .ok { background: #e8fff0; color: #0a7a3d; border: 1px solid #b8f0cf; }
    .bad { background: #fff0f0; color: #a30d0d; border: 1px solid #f0c0c0; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
    .btn { display: inline-block; text-decoration: none; border: none; cursor: pointer; padding: 14px 16px; border-radius: 10px; font-weight: 600; }
    .btn-primary { background: #2b6fff; color: #fff; }
    .btn-secondary { background: #eef2ff; color: #2b3a55; }
    .code { word-break: break-all; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace; background: rgba(0,0,0,.06); padding: 12px; border-radius: 8px; }
    footer { margin-top: 20px; font-size: 12px; opacity: .7; }
  </style>
  <script>
    function copyConfig() {
      const el = document.getElementById('cfg');
      if (!el) return;
      navigator.clipboard.writeText(el.innerText).then(() => {
        const btn = document.getElementById('copyBtn');
        if (btn) { btn.innerText = 'Скопировано ✔'; setTimeout(()=>btn.innerText='Скопировать конфиг', 1600); }
      });
    }
  </script>
  <meta property=\"og:title\" content=\"Shard VPN — Мини‑приложение\" />
  <meta property=\"og:description\" content=\"Статус подписки и подключение в один клик\" />
  <meta property=\"og:type\" content=\"website\" />
  <meta property=\"og:image\" content=\"https://unpkg.com/emoji-datasource-apple/img/apple/64/1f310.png\" />
  <meta name=\"telegram:channel\" content=\"Shard VPN\" />
  <meta name=\"format-detection\" content=\"telephone=no\"/>
  <style> @media (prefers-color-scheme: dark){ .card{ border-color: rgba(255,255,255,.12);} .btn-secondary{ background:#1f2333; color:#e8eaff;} .code{ background: rgba(255,255,255,.06);} .ok{ background:#0f2f20; color:#abf2c1; border-color:#1f5a38;} .bad{ background:#3a1717; color:#ffc5c5; border-color:#613333;} } </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <h1>🌐 Shard VPN</h1>
      <div class=\"muted\">Профиль пользователя <b>{{ user_id }}</b></div>

      {% if exists %}
        <div class=\"status {{ 'ok' if active else 'bad' }}\">
          Статус подписки: {{ 'активна ✅' if active else 'не активна ⛔' }}
        </div>
        {% if expiry_date %}
          <div class=\"muted\">Дата окончания: <b>{{ expiry_date }}</b></div>
        {% endif %}
      {% else %}
        <div class=\"status bad\">Пользователь не найден в базе</div>
      {% endif %}

      {% if config_str %}
        <h2 style=\"margin-top:18px; font-size:18px;\">VPN‑конфигурация</h2>
        <div id=\"cfg\" class=\"code\">{{ config_str }}</div>
      {% endif %}

      <div class=\"row\">
        {% if deep_link %}
          <a class=\"btn btn-primary\" href=\"{{ deep_link }}\">🔌 Установить VPN</a>
        {% endif %}
        {% if config_str %}
          <button id=\"copyBtn\" class=\"btn btn-secondary\" onclick=\"copyConfig()\">Скопировать конфиг</button>
        {% endif %}
        <a class=\"btn btn-secondary\" href=\"https://t.me/SHARDPROB_bot\">Открыть бота</a>
      </div>
    </div>
    <footer>
      Если кнопка не сработала, скопируйте конфиг и вставьте в приложение V2RayTun вручную.
    </footer>
  </div>
  
</body>
</html>
"""


@app.get("/")
def index():
    return "OK", 200


@app.get("/u/<int:user_id>")
def user_page(user_id: int):
    config_str = request.args.get('config', default='', type=str).strip()
    deep_link = ''

    row = fetch_user_row(user_id)
    if row is None:
        active = False
        expiry_date = ''
        exists = False
    else:
        expiry_date = row['expiry_date'] or ''
        active = bool(row['subscribed'] and is_subscription_active_check(expiry_date))
        exists = True

    if config_str:
        deep_link = f"v2raytun://import/{quote(config_str, safe=':/?&=#@._-')}"

    return render_template_string(
        PAGE_TEMPLATE,
        user_id=user_id,
        active=active,
        expiry_date=expiry_date,
        config_str=config_str,
        deep_link=deep_link,
        exists=exists
    )


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8081"))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)


