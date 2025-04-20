from app import app, db

with app.app_context():
    print('データベース初期化中...')
    db.create_all()
    print('データベース初期化完了')
