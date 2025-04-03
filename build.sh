#!/usr/bin/env bash
# Renderのビルドスクリプト

# Pythonパッケージのインストール
pip install -r requirements.txt

# データベースの初期化（必要に応じて）
python init_db.py
