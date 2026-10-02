#!/bin/bash
# ============================================================
#  Network Automation 라이센스 서버 설치 스크립트
#  서버에서 실행: bash install.sh
# ============================================================

set -e

echo "=== 1. 패키지 업데이트 ==="
apt-get update -y
apt-get install -y python3 python3-pip python3-venv nginx

echo "=== 2. 디렉터리 생성 ==="
mkdir -p /opt/license_server
cp main.py database.py requirements.txt /opt/license_server/

echo "=== 3. Python 가상환경 설치 ==="
cd /opt/license_server
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

echo "=== 4. 환경변수 설정 (.env) ==="
cat > /opt/license_server/.env << 'EOF'
# !! 반드시 아래 두 값을 변경하세요 !!
APP_SECRET=anta_net_2026_secret_key_CHANGE_ME
ADMIN_TOKEN=my_super_secret_admin_token_CHANGE_ME
DB_PATH=/opt/license_server/licenses.db
EOF

chmod 600 /opt/license_server/.env
echo "[주의] /opt/license_server/.env 파일을 열어 APP_SECRET, ADMIN_TOKEN 을 변경하세요!"

echo "=== 5. systemd 서비스 등록 ==="
cat > /etc/systemd/system/license-server.service << 'EOF'
[Unit]
Description=Network Automation License Server
After=network.target

[Service]
User=root
WorkingDirectory=/opt/license_server
EnvironmentFile=/opt/license_server/.env
ExecStart=/opt/license_server/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable license-server
systemctl start license-server

echo "=== 6. Nginx 리버스 프록시 설정 ==="
cat > /etc/nginx/sites-available/license-api << 'EOF'
server {
    listen 80;
    server_name auto-network.co.kr;

    # 기존 웹사이트는 그대로 /로 서빙
    # 라이센스 API만 /api/ 경로로 프록시
    location /api/ {
        proxy_pass         http://127.0.0.1:8765/api/;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 30s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8765/health;
    }

    # 나머지는 기존 웹사이트로
    location / {
        try_files $uri $uri/ =404;
        root /var/www/html;
    }
}
EOF

# 기존 default 설정과 충돌 방지
ln -sf /etc/nginx/sites-available/license-api \
       /etc/nginx/sites-enabled/license-api
nginx -t && systemctl reload nginx

echo ""
echo "=============================================="
echo " 설치 완료!"
echo "=============================================="
echo ""
echo " 반드시 할 일:"
echo "   1. nano /opt/license_server/.env  (APP_SECRET, ADMIN_TOKEN 변경)"
echo "   2. systemctl restart license-server"
echo ""
echo " 동작 확인:"
echo "   curl http://auto-network.co.kr/health"
echo ""
echo " 서비스 상태 확인:"
echo "   systemctl status license-server"
echo "   journalctl -u license-server -f"
echo "=============================================="
