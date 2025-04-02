# 訪問診療クリニック向け備品管理システム

## システム概要
このシステムは訪問診療クリニック向けの備品管理システムです。診療に必要な消耗品を簡単に記録・発注できる仕組みを提供し、使用後すぐに発注書を自動作成してFAX送信可能にすることで、在庫切れや手間を削減します。

## 主な機能
- 備品使用登録・発注機能
- 患者別セット登録・使用機能
- 管理者用マスタ管理機能
- 使用履歴・月次レポート機能

## 技術スタック
- Python 3.9+
- Flask (Webフレームワーク)
- SQLite (データベース)
- SQLAlchemy (ORMマッパー)
- Bootstrap 5 (フロントエンドフレームワーク)
- ReportLab (PDFレンダリング)

## インストール方法

### 1. リポジトリをクローン
```
git clone [リポジトリURL]
cd [プロジェクトディレクトリ]
```

### 2. 仮想環境の作成と有効化
```
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 依存パッケージのインストール
```
pip install -r requirements.txt
```

### 4. アプリケーションの実行
```
python app.py
```

## 使用方法
1. ブラウザで http://localhost:5000 にアクセス
2. 初期設定として備品マスタを登録
3. 患者別セットを設定
4. 備品使用を記録すると自動的に発注書が生成される

## ライセンス
All Rights Reserved
