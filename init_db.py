from app import db, Supplier, ClinicInfo, app

def init_database():
    # アプリケーションコンテキストを設定
    with app.app_context():
        # データベーステーブルの作成
        db.create_all()
        
        # 基本的な発注先の追加
        if Supplier.query.count() == 0:
            suppliers = [
                Supplier(name="サンプル医療機器", fax_number="03-1234-5678", address="東京都千代田区1-1", email="info@sample-medical.co.jp"),
                Supplier(name="メディカルサプライ", fax_number="06-8765-4321", address="大阪府大阪市中央区2-2", email="contact@medicalsupply.co.jp")
            ]
            for supplier in suppliers:
                db.session.add(supplier)
        
        # クリニック情報の初期設定
        if ClinicInfo.query.count() == 0:
            clinic = ClinicInfo(
                name="訪問診療クリニック",
                address="東京都新宿区西新宿1-1-1",
                phone="03-1111-2222",
                fax="03-3333-4444",
                email="info@clinic.example.com",
                website="https://clinic.example.com",
                director="山田 太郎"
            )
            db.session.add(clinic)
        
        db.session.commit()
        print("データベースを初期化しました。")

if __name__ == "__main__":
    init_database()
