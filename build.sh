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

# バックアップファイルのパス
BACKUP_FILE="/tmp/medical_inventory_backup.json"

# Pythonパッケージのインストール
pip install -r requirements.txt

# 既存のデータをバックアップする（存在する場合）
if [ -f /tmp/inventory.db ]; then
    echo "既存のデータをバックアップしています..."
    python -c '
import sys, os, json
sys.path.append(".")
os.environ["RENDER"] = "true"
try:
    from app import app, db, ClinicInfo, Item, Supplier, Patient, PatientSet, ItemSet, SetItem
    
    with app.app_context():
        # データベースの内容を取得
        clinic_data = ClinicInfo.query.first()
        items_data = Item.query.all()
        suppliers_data = Supplier.query.all()
        patients_data = Patient.query.all()
        patient_sets_data = PatientSet.query.all()
        item_sets_data = ItemSet.query.all()
        set_items_data = SetItem.query.all()
        
        # JSONに変換するための辞書を作成
        backup = {
            "clinic": {} if not clinic_data else {
                "name": clinic_data.name,
                "address": clinic_data.address,
                "phone": clinic_data.phone,
                "fax": clinic_data.fax,
                "email": clinic_data.email,
                "website": clinic_data.website,
                "director": clinic_data.director
            },
            "suppliers": [{
                "id": s.id, 
                "name": s.name, 
                "fax_number": s.fax_number,
                "address": s.address,
                "email": s.email
            } for s in suppliers_data],
            "items": [{
                "id": i.id,
                "name": i.name,
                "unit_type": i.unit_type,
                "items_per_box": i.items_per_box,
                "minimum_stock": i.minimum_stock,
                "current_stock": i.current_stock,
                "supplier_id": i.supplier_id
            } for i in items_data],
            "patients": [{
                "id": p.id,
                "name": p.name,
                "patient_id": p.patient_id,
                "address": p.address,
                "phone": p.phone
            } for p in patients_data],
            "patient_sets": [{
                "id": ps.id,
                "name": ps.name,
                "patient_id": ps.patient_id
            } for ps in patient_sets_data],
            "item_sets": [{
                "id": its.id,
                "name": its.name,
                "description": its.description
            } for its in item_sets_data],
            "set_items": [{
                "id": si.id,
                "patient_set_id": si.patient_set_id,
                "item_set_id": si.item_set_id,
                "item_id": si.item_id,
                "quantity": si.quantity
            } for si in set_items_data]
        }
        
        # JSONファイルに保存
        with open("/tmp/medical_inventory_backup.json", "w", encoding="utf-8") as f:
            json.dump(backup, f, ensure_ascii=False, indent=2)
        
        print("バックアップが正常に作成されました")
except Exception as e:
    print(f"バックアップ中にエラーが発生しました: {e}")
'
fi

# データベースの初期化
python init_db.py

# バックアップからデータを復元（バックアップが存在する場合）
if [ -f "$BACKUP_FILE" ]; then
    echo "バックアップからデータを復元しています..."
    python -c '
import sys, os, json
sys.path.append(".")
os.environ["RENDER"] = "true"
try:
    from app import app, db, ClinicInfo, Item, Supplier, Patient, PatientSet, ItemSet, SetItem
    
    # バックアップファイルを読み込む
    with open("/tmp/medical_inventory_backup.json", "r", encoding="utf-8") as f:
        backup_data = json.load(f)
    
    with app.app_context():
        # クリニック情報の復元
        if backup_data.get("clinic"):
            clinic = ClinicInfo.query.first()
            if not clinic:
                clinic = ClinicInfo()
                db.session.add(clinic)
            
            clinic_data = backup_data["clinic"]
            clinic.name = clinic_data.get("name", "クリニック名")
            clinic.address = clinic_data.get("address")
            clinic.phone = clinic_data.get("phone")
            clinic.fax = clinic_data.get("fax")
            clinic.email = clinic_data.get("email")
            clinic.website = clinic_data.get("website")
            clinic.director = clinic_data.get("director")
        
        # 発注先情報の復元
        if backup_data.get("suppliers"):
            for supplier_data in backup_data["suppliers"]:
                supplier_id = supplier_data.get("id")
                supplier = Supplier.query.get(supplier_id)
                if not supplier:
                    supplier = Supplier()
                    db.session.add(supplier)
                
                supplier.name = supplier_data.get("name")
                supplier.fax_number = supplier_data.get("fax_number")
                supplier.address = supplier_data.get("address")
                supplier.email = supplier_data.get("email")
        
        # 備品情報の復元
        if backup_data.get("items"):
            for item_data in backup_data["items"]:
                item_id = item_data.get("id")
                item = Item.query.get(item_id)
                if not item:
                    item = Item()
                    db.session.add(item)
                
                item.name = item_data.get("name")
                item.unit_type = item_data.get("unit_type")
                item.items_per_box = item_data.get("items_per_box")
                item.minimum_stock = item_data.get("minimum_stock")
                item.current_stock = item_data.get("current_stock")
                item.supplier_id = item_data.get("supplier_id")
        
        # 患者情報の復元
        if backup_data.get("patients"):
            for patient_data in backup_data["patients"]:
                patient_id = patient_data.get("id")
                patient = Patient.query.get(patient_id)
                if not patient:
                    patient = Patient()
                    db.session.add(patient)
                
                patient.name = patient_data.get("name")
                patient.patient_id = patient_data.get("patient_id")
                patient.address = patient_data.get("address")
                patient.phone = patient_data.get("phone")
        
        # 患者セット情報の復元
        if backup_data.get("patient_sets"):
            for ps_data in backup_data["patient_sets"]:
                ps_id = ps_data.get("id")
                ps = PatientSet.query.get(ps_id)
                if not ps:
                    ps = PatientSet()
                    db.session.add(ps)
                
                ps.name = ps_data.get("name")
                ps.patient_id = ps_data.get("patient_id")
        
        # 備品セット情報の復元
        if backup_data.get("item_sets"):
            for its_data in backup_data["item_sets"]:
                its_id = its_data.get("id")
                its = ItemSet.query.get(its_id)
                if not its:
                    its = ItemSet()
                    db.session.add(its)
                
                its.name = its_data.get("name")
                its.description = its_data.get("description")
        
        # セット内容の復元
        if backup_data.get("set_items"):
            for si_data in backup_data["set_items"]:
                si_id = si_data.get("id")
                si = SetItem.query.get(si_id)
                if not si:
                    si = SetItem()
                    db.session.add(si)
                
                si.patient_set_id = si_data.get("patient_set_id")
                si.item_set_id = si_data.get("item_set_id")
                si.item_id = si_data.get("item_id")
                si.quantity = si_data.get("quantity")
        
        # 変更をコミット
        db.session.commit()
        print("データが正常に復元されました")
except Exception as e:
    print(f"データ復元中にエラーが発生しました: {e}")
'
fi

echo "ビルドプロセスが完了しました"
