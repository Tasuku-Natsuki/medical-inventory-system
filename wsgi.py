import os
from app import app, db

# Render環境変数の設定
os.environ['RENDER'] = 'true'

# アプリケーション起動前にデータベースの初期化を確認
with app.app_context():
    try:
        # データベースファイルが存在しなければ作成
        db.create_all()
        print("データベースの初期化を確認しました")
    except Exception as e:
        print(f"データベース初期化エラー: {e}")

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0')
