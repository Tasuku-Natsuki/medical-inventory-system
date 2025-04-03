#!/usr/bin/env bash
# Renderのビルドスクリプト

# Render環境であることを示す環境変数を設定
export RENDER=true

# Flaskの環境設定
export FLASK_ENV=production
export FLASK_DEBUG=0

# 一時ディレクトリに書き込み権限を確保
mkdir -p /tmp
chmod 777 /tmp

# Pythonパッケージのインストール
pip install -r requirements.txt

# データベースの初期化
python init_db.py

echo "ビルドプロセスが完了しました"
