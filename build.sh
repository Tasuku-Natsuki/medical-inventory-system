#!/usr/bin/env bash
# Renderのビルドスクリプト

# Render環境であることを示す環境変数を設定
export RENDER=true

# Pythonパッケージのインストール
pip install -r requirements.txt

# データベースの初期化
python init_db.py
