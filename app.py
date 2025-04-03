import os
from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
import json
import csv
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '4ELMydzP8QszZd9yXG3U')

# データベース設定
# 本番環境では環境変数からURLを取得し、開発環境ではSQLiteを使用
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///inventory.db')
# SQLite URLの修正（PostgreSQLとの互換性のため）
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# テンプレートにグローバル変数を追加
@app.context_processor
def inject_now():
    return {
        'now': datetime.now(),
        'current_year': datetime.now().year
    }

# モデル定義
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    unit_type = db.Column(db.String(10), nullable=False)  # 'individual' or 'box'
    items_per_box = db.Column(db.Integer, nullable=True)  # 箱あたりの個数
    minimum_stock = db.Column(db.Integer, default=0)  # 最低在庫数
    current_stock = db.Column(db.Integer, default=0)  # 現在の在庫数
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    
    def __repr__(self):
        return f'<Item {self.name}>'

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    fax_number = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    items = db.relationship('Item', backref='supplier', lazy=True)
    
    def __repr__(self):
        return f'<Supplier {self.name}>'

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    patient_id = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    sets = db.relationship('PatientSet', backref='patient', lazy=True)
    
    def __repr__(self):
        return f'<Patient {self.name}>'

class PatientSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    
    def __repr__(self):
        return f'<PatientSet {self.name}>'

class ItemSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<ItemSet {self.name}>'

class SetItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_set_id = db.Column(db.Integer, db.ForeignKey('patient_set.id'), nullable=True)
    item_set_id = db.Column(db.Integer, db.ForeignKey('item_set.id'), nullable=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    patient_set = db.relationship('PatientSet', backref='set_items', foreign_keys=[patient_set_id])
    item_set = db.relationship('ItemSet', backref='set_items', foreign_keys=[item_set_id])
    item = db.relationship('Item', backref='set_items')
    
    def __repr__(self):
        return f'<SetItem {self.id}>'

class Usage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    usage_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    item = db.relationship('Item', backref='usages')
    patient = db.relationship('Patient', backref='usages')
    
    def __repr__(self):
        return f'<Usage {self.id}>'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, sent, received
    supplier = db.relationship('Supplier', backref='orders')
    items = db.relationship('OrderItem', backref='order', lazy=True)
    
    def __repr__(self):
        return f'<Order {self.id}>'

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    item = db.relationship('Item', backref='order_items')
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'

# クリニック情報モデル
class ClinicInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default="訪問診療クリニック")
    address = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    fax = db.Column(db.String(20))
    email = db.Column(db.String(100))
    website = db.Column(db.String(100))
    director = db.Column(db.String(50))  # 院長名
    
    def __repr__(self):
        return f'<ClinicInfo {self.name}>'

# ルート
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/items')
def items():
    all_items = Item.query.all()
    return render_template('items.html', items=all_items)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    suppliers = Supplier.query.all()
    if request.method == 'POST':
        name = request.form['name']
        unit_type = request.form['unit_type']
        items_per_box = request.form.get('items_per_box', type=int) if unit_type == 'box' else None
        minimum_stock = request.form.get('minimum_stock', 0, type=int)
        current_stock = request.form.get('current_stock', 0, type=int)
        supplier_id = request.form.get('supplier_id', type=int)
        
        new_item = Item(
            name=name,
            unit_type=unit_type,
            items_per_box=items_per_box,
            minimum_stock=minimum_stock,
            current_stock=current_stock,
            supplier_id=supplier_id
        )
        db.session.add(new_item)
        db.session.commit()
        flash('備品を追加しました', 'success')
        return redirect(url_for('items'))
    return render_template('add_item.html', suppliers=suppliers)

@app.route('/suppliers')
def suppliers():
    all_suppliers = Supplier.query.all()
    return render_template('suppliers.html', suppliers=all_suppliers)

@app.route('/add_supplier', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        name = request.form['name']
        fax_number = request.form['fax_number']
        address = request.form.get('address', '')
        email = request.form.get('email', '')
        
        new_supplier = Supplier(
            name=name,
            fax_number=fax_number,
            address=address,
            email=email
        )
        db.session.add(new_supplier)
        db.session.commit()
        flash('発注先を追加しました', 'success')
        return redirect(url_for('suppliers'))
    return render_template('add_supplier.html')

@app.route('/patients')
def patients():
    all_patients = Patient.query.all()
    return render_template('patients.html', patients=all_patients)

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        name = request.form['name']
        
        new_patient = Patient(name=name)
        db.session.add(new_patient)
        db.session.commit()
        flash('患者を追加しました', 'success')
        return redirect(url_for('patients'))
    return render_template('add_patient.html')

@app.route('/item_sets')
def item_sets():
    all_item_sets = ItemSet.query.all()
    return render_template('item_sets.html', item_sets=all_item_sets)

@app.route('/add_item_set', methods=['GET', 'POST'])
def add_item_set():
    all_items = Item.query.all()
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        
        # 新しい汎用セットを作成
        new_item_set = ItemSet(
            name=name,
            description=description
        )
        db.session.add(new_item_set)
        db.session.flush()  # IDを取得するためにフラッシュ
        
        # セットアイテムの登録
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        
        for i in range(len(item_ids)):
            if i < len(quantities) and item_ids[i] and quantities[i]:
                try:
                    item_id = int(item_ids[i])
                    quantity = int(quantities[i])
                    
                    if quantity > 0:
                        set_item = SetItem(
                            item_set_id=new_item_set.id,
                            item_id=item_id,
                            quantity=quantity
                        )
                        db.session.add(set_item)
                except (ValueError, TypeError):
                    continue
        
        db.session.commit()
        flash('汎用セットを追加しました', 'success')
        return redirect(url_for('item_sets'))
        
    return render_template('add_item_set.html', items=all_items)

@app.route('/patient_sets')
def patient_sets():
    all_patient_sets = PatientSet.query.all()
    return render_template('patient_sets.html', patient_sets=all_patient_sets)

@app.route('/add_patient_set', methods=['GET', 'POST'])
def add_patient_set():
    patients = Patient.query.all()
    all_items = Item.query.all()
    
    # URLパラメータから患者IDを取得
    pre_selected_patient_id = request.args.get('patient_id')
    
    if request.method == 'POST':
        name = request.form['name']
        patient_id = request.form.get('patient_id', type=int)
        
        new_patient_set = PatientSet(
            name=name,
            patient_id=patient_id
        )
        db.session.add(new_patient_set)
        db.session.flush()  # IDを取得するためにフラッシュ
        
        # セットアイテムの登録
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        
        for i in range(len(item_ids)):
            if i < len(quantities) and item_ids[i] and quantities[i]:
                try:
                    item_id = int(item_ids[i])
                    quantity = int(quantities[i])
                    
                    if quantity > 0:
                        set_item = SetItem(
                            patient_set_id=new_patient_set.id,
                            item_id=item_id,
                            quantity=quantity
                        )
                        db.session.add(set_item)
                except (ValueError, TypeError):
                    continue
        
        db.session.commit()
        flash('患者セットを追加しました', 'success')
        
        # セット追加後、患者のセット管理画面にリダイレクト
        if patient_id:
            return redirect(url_for('patient_sets_manage', patient_id=patient_id))
        else:
            return redirect(url_for('patient_sets'))
    
    return render_template('add_patient_set.html', 
                          patients=patients, 
                          items=all_items, 
                          pre_selected_patient_id=pre_selected_patient_id)

@app.route('/use_item', methods=['GET', 'POST'])
def use_item():
    all_items = Item.query.all()
    patients = Patient.query.all()
    
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        
        if not item_ids or not quantities or len(item_ids) != len(quantities):
            flash('備品と数量を正しく選択してください', 'danger')
            return redirect(url_for('use_item'))
        
        # 発注情報を集約するための辞書
        orders_by_supplier = {}
        
        for i in range(len(item_ids)):
            item_id = item_ids[i]
            quantity = int(quantities[i])
            
            if not item_id or quantity <= 0:
                continue
                
            item = Item.query.get_or_404(item_id)
            
            # 使用記録を保存
            usage = Usage(
                item_id=item.id,
                quantity=quantity,
                patient_id=patient_id if patient_id else None,
                usage_date=datetime.utcnow()
            )
            db.session.add(usage)
            
            # 在庫を減らす
            item.current_stock = max(0, item.current_stock - quantity)
            
            # 在庫が最低在庫数を下回ったら発注
            if item.current_stock <= item.minimum_stock and item.supplier_id:
                supplier_id = item.supplier_id
                
                # 今日の発注がすでにあるか確認
                if supplier_id in orders_by_supplier:
                    order = orders_by_supplier[supplier_id]
                else:
                    existing_order = Order.query.filter_by(
                        supplier_id=supplier_id,
                        status='pending'
                    ).order_by(Order.order_date.desc()).first()
                    
                    if existing_order:
                        order = existing_order
                    else:
                        # 新しい発注を作成
                        new_order = Order(
                            supplier_id=supplier_id,
                            status='pending',
                            order_date=datetime.utcnow()
                        )
                        db.session.add(new_order)
                        db.session.flush()
                        order = new_order
                    
                    orders_by_supplier[supplier_id] = order
                
                # 同じアイテムの発注がすでにあるか確認
                existing_order_item = OrderItem.query.filter_by(
                    order_id=order.id,
                    item_id=item.id
                ).first()
                
                if existing_order_item:
                    existing_order_item.quantity += quantity
                else:
                    new_order_item = OrderItem(
                        order_id=order.id,
                        item_id=item.id,
                        quantity=quantity
                    )
                    db.session.add(new_order_item)
        
        db.session.commit()
        
        if orders_by_supplier:
            flash('備品を使用登録し、発注書を生成しました', 'success')
            # 最初の発注を表示
            first_order = list(orders_by_supplier.values())[0]
            return redirect(url_for('view_order', order_id=first_order.id))
        else:
            flash('備品を使用登録しました', 'success')
            return redirect(url_for('items'))
    
    return render_template('use_item.html', items=all_items, patients=patients)

@app.route('/use_set', methods=['GET', 'POST'])
def use_set():
    patients = Patient.query.all()
    all_item_sets = ItemSet.query.all()
    selected_patient_id = None
    patient_sets = []
    
    # POSTから患者IDを取得
    patient_id = request.args.get('patient_id') or (request.form.get('patient_id') if request.method == 'POST' else None)
    
    # 患者が選択されている場合、その患者のセットを取得
    if patient_id:
        try:
            patient_id = int(patient_id)
            selected_patient_id = patient_id
            patient_sets = PatientSet.query.filter_by(patient_id=patient_id).all()
        except (ValueError, TypeError):
            flash('無効な患者IDです', 'warning')
            patient_sets = []
    
    if request.method == 'POST':
        patient_set_id = request.form.get('patient_set_id')
        item_set_id = request.form.get('item_set_id')
        
        # どちらのセットも選択されていない場合
        if not (patient_set_id or item_set_id):
            flash('セットを1つ選択してください', 'warning')
            return redirect(url_for('use_set'))
            
        # 患者固有セットが選択された場合（患者IDの選択が必要）
        if patient_set_id:
            if not patient_id:
                flash('患者固有セットを使用するには、患者を選択してください', 'warning')
                return redirect(url_for('use_set'))
            return redirect(url_for('use_patient_set', set_id=patient_set_id))
            
        # 汎用セットが選択された場合（患者IDは任意）
        if item_set_id:
            return redirect(url_for('use_item_set', set_id=item_set_id, patient_id=patient_id or 0))
    
    return render_template('use_set.html', 
                          patients=patients, 
                          patient_sets=patient_sets, 
                          item_sets=all_item_sets, 
                          selected_patient_id=selected_patient_id)

@app.route('/use_patient_set/<int:set_id>', methods=['GET', 'POST'])
def use_patient_set(set_id):
    patient_set = PatientSet.query.get_or_404(set_id)
    set_items = SetItem.query.filter_by(patient_set_id=set_id).all()
    
    if not set_items:
        flash('このセットには備品が登録されていません', 'warning')
        return redirect(url_for('patient_sets'))
    
    # 発注が必要な備品を追跡
    orders_created = {}
    
    for set_item in set_items:
        item = Item.query.get(set_item.item_id)
        if not item:
            continue
            
        # 使用記録を保存
        usage = Usage(
            item_id=item.id,
            quantity=set_item.quantity,
            patient_id=patient_set.patient_id,
            usage_date=datetime.utcnow()
        )
        db.session.add(usage)
        
        # 在庫を減らす
        item.current_stock = max(0, item.current_stock - set_item.quantity)
        
        # 在庫が最低在庫数を下回り、供給元がある場合、発注を生成
        if item.current_stock <= item.minimum_stock and item.supplier_id:
            supplier_id = item.supplier_id
            
            # この供給元の発注がすでに処理されているか確認
            if supplier_id not in orders_created:
                # 未処理の発注を検索
                existing_order = Order.query.filter_by(
                    supplier_id=supplier_id,
                    status='pending'
                ).order_by(Order.order_date.desc()).first()
                
                if existing_order:
                    orders_created[supplier_id] = existing_order
                else:
                    # 新しい発注を作成
                    new_order = Order(
                        supplier_id=supplier_id,
                        status='pending',
                        order_date=datetime.utcnow()
                    )
                    db.session.add(new_order)
                    db.session.flush()
                    orders_created[supplier_id] = new_order
            
            # この発注に備品を追加
            order = orders_created[supplier_id]
            
            # 同じアイテムの発注がすでにあるか確認
            existing_order_item = OrderItem.query.filter_by(
                order_id=order.id,
                item_id=item.id
            ).first()
            
            if existing_order_item:
                existing_order_item.quantity += set_item.quantity
            else:
                new_order_item = OrderItem(
                    order_id=order.id,
                    item_id=item.id,
                    quantity=set_item.quantity
                )
                db.session.add(new_order_item)
    
    db.session.commit()
    
    if orders_created:
        flash(f'患者セット {patient_set.name} を使用し、発注書を生成しました', 'success')
        # 最初の発注のIDを使用してリダイレクト
        first_order = next(iter(orders_created.values()))
        return redirect(url_for('view_order', order_id=first_order.id))
    else:
        flash(f'患者セット {patient_set.name} を使用しました', 'success')
        return redirect(url_for('patient_sets'))

@app.route('/use_item_set/<int:set_id>', methods=['GET'])
def use_item_set(set_id):
    item_set = ItemSet.query.get_or_404(set_id)
    set_items = SetItem.query.filter_by(item_set_id=set_id).all()
    
    # 患者IDの取得（存在しない場合はNone）
    patient_id = request.args.get('patient_id')
    if patient_id:
        try:
            patient_id = int(patient_id)
            if patient_id == 0:
                patient_id = None
        except (ValueError, TypeError):
            patient_id = None
    
    if not set_items:
        flash('このセットには備品が登録されていません', 'warning')
        return redirect(url_for('item_sets'))
    
    # 発注が必要な備品を追跡
    orders_created = {}
    
    for set_item in set_items:
        item = Item.query.get(set_item.item_id)
        if not item:
            continue
            
        # 使用記録を保存
        usage = Usage(
            item_id=item.id,
            quantity=set_item.quantity,
            patient_id=patient_id,  # 患者IDが指定されていない場合はNoneになる
            usage_date=datetime.utcnow()
        )
        db.session.add(usage)
        
        # 在庫を減らす
        item.current_stock = max(0, item.current_stock - set_item.quantity)
        
        # 在庫が最低在庫数を下回り、供給元がある場合、発注を生成
        if item.current_stock <= item.minimum_stock and item.supplier_id:
            supplier_id = item.supplier_id
            
            # この供給元の発注がすでに処理されているか確認
            if supplier_id not in orders_created:
                # 未処理の発注を検索
                existing_order = Order.query.filter_by(
                    supplier_id=supplier_id,
                    status='pending'
                ).order_by(Order.order_date.desc()).first()
                
                if existing_order:
                    orders_created[supplier_id] = existing_order
                else:
                    # 新しい発注を作成
                    new_order = Order(
                        supplier_id=supplier_id,
                        status='pending',
                        order_date=datetime.utcnow()
                    )
                    db.session.add(new_order)
                    db.session.flush()
                    orders_created[supplier_id] = new_order
            
            # この発注に備品を追加
            order = orders_created[supplier_id]
            
            # 必要発注数を計算（適切な数量に戻すため）
            order_quantity = max(1, item.minimum_stock * 2 - item.current_stock)
            
            # この発注にこの備品がすでに含まれているか確認
            existing_item = OrderItem.query.filter_by(
                order_id=order.id,
                item_id=item.id
            ).first()
            
            if existing_item:
                # 数量を更新
                existing_item.quantity += order_quantity
            else:
                # 新しいオーダーアイテムを作成
                new_order_item = OrderItem(
                    order_id=order.id,
                    item_id=item.id,
                    quantity=order_quantity
                )
                db.session.add(new_order_item)
    
    db.session.commit()
    
    flash(f'汎用セット「{item_set.name}」を使用登録しました', 'success')
    
    # 発注書があれば、最初の発注書を表示
    if orders_created:
        first_order = list(orders_created.values())[0]
        flash('一部の備品が最低在庫数を下回ったため、自動発注されました', 'info')
        return redirect(url_for('view_order', order_id=first_order.id))
    
    return redirect(url_for('index'))

@app.route('/orders')
def orders():
    all_orders = Order.query.order_by(Order.order_date.desc()).all()
    return render_template('orders.html', orders=all_orders)

@app.route('/view_order/<int:order_id>')
def view_order(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('view_order.html', order=order)

# CSVファイルからの物品インポート
@app.route('/import_items', methods=['GET', 'POST'])
def import_items():
    suppliers = Supplier.query.all()
    
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('CSVファイルがありません', 'danger')
            return redirect(request.url)
        
        file = request.files['csv_file']
        
        if file.filename == '':
            flash('ファイルが選択されていません', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                # CSVファイルを読み込む
                stream = io.StringIO(file.stream.read().decode('utf-8-sig', errors='replace'))
                csv_data = list(csv.reader(stream))
                
                if len(csv_data) < 2:  # ヘッダー行 + 少なくとも1行のデータ
                    flash('CSVファイルにデータが含まれていません', 'warning')
                    return redirect(request.url)
                
                # ヘッダー行をスキップ
                csv_data = csv_data[1:]
                items_added = 0
                errors = 0
                
                for row in csv_data:
                    # 空行はスキップ
                    if not row or not any(row):
                        continue
                        
                    if len(row) < 5:  # 最低限必要な列数
                        errors += 1
                        continue
                    
                    try:
                        name = row[0].strip()
                        if not name:  # 備品名が空の場合はスキップ
                            errors += 1
                            continue
                            
                        unit_type = row[1].strip().lower() if len(row) > 1 and row[1] else 'individual'
                        
                        # 単位タイプの確認
                        if unit_type not in ['individual', 'box']:
                            unit_type = 'individual'  # デフォルトは個別
                        
                        try:
                            if unit_type == 'box' and len(row) > 2 and row[2]:
                                items_per_box = int(row[2])
                            else:
                                items_per_box = None if unit_type == 'individual' else 1
                                
                            minimum_stock = int(row[3]) if len(row) > 3 and row[3] else 1
                            current_stock = int(row[4]) if len(row) > 4 and row[4] else 0
                        except ValueError:
                            # 数値変換エラー
                            errors += 1
                            continue
                            
                        # 発注先IDの取得（あれば）
                        supplier_id = None
                        if len(row) > 5 and row[5]:
                            supplier_name = row[5].strip()
                            supplier = Supplier.query.filter_by(name=supplier_name).first()
                            if supplier:
                                supplier_id = supplier.id
                        
                        # 物品の追加
                        item = Item(
                            name=name,
                            unit_type=unit_type,
                            items_per_box=items_per_box,
                            minimum_stock=minimum_stock,
                            current_stock=current_stock,
                            supplier_id=supplier_id
                        )
                        db.session.add(item)
                        items_added += 1
                        
                    except Exception as e:
                        app.logger.error(f"行の処理エラー: {str(e)}, 行データ: {row}")
                        errors += 1
                        continue
                
                db.session.commit()
                
                if items_added > 0:
                    success_msg = f'{items_added}個の物品をインポートしました'
                    if errors > 0:
                        success_msg += f'（{errors}行は処理できませんでした）'
                    flash(success_msg, 'success')
                    return redirect(url_for('items'))
                else:
                    flash('インポート可能な物品データがありませんでした', 'warning')
                    return redirect(request.url)
                
            except Exception as e:
                app.logger.error(f"CSVインポートエラー: {str(e)}")
                flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('CSVファイル形式のみ対応しています', 'warning')
            return redirect(request.url)
    
    return render_template('import_items.html', suppliers=suppliers)

# 既存データの削除
@app.route('/clear_all_data', methods=['GET', 'POST'])
def clear_all_data():
    if request.method == 'POST':
        try:
            # 削除する順序を考慮して実行
            Usage.query.delete()
            OrderItem.query.delete()
            SetItem.query.delete()
            Order.query.delete()
            Item.query.delete()
            PatientSet.query.delete()
            ItemSet.query.delete()
            Patient.query.delete()
            ClinicInfo.query.delete()
            
            # Supplierは削除しないオプションもある
            if request.form.get('clear_suppliers') == 'yes':
                Supplier.query.delete()
            
            db.session.commit()
            flash('全てのデータを正常に削除しました', 'success')
            return redirect(url_for('import_items'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"データ削除エラー: {str(e)}")
            flash(f'データ削除中にエラーが発生しました: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
    return render_template('clear_all_data.html')

# フォントの登録
# 日本語フォントのパス（MS Gothicを使用）
font_path = os.path.join(os.environ['WINDIR'], 'Fonts', 'msgothic.ttc')
pdfmetrics.registerFont(TTFont('MS-Gothic', font_path))

@app.route('/generate_pdf/<int:order_id>')
def generate_pdf(order_id):
    order = Order.query.get_or_404(order_id)
    supplier = order.supplier
    order_items = OrderItem.query.filter_by(order_id=order.id).all()
    
    # クリニック情報を取得
    clinic_info = ClinicInfo.query.first()
    if not clinic_info:
        clinic_info = ClinicInfo(name="訪問診療クリニック")
        db.session.add(clinic_info)
        db.session.commit()
    
    # PDF生成
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    
    # 日本語フォントを使用
    p.setFont("MS-Gothic", 18)
    p.drawString(50, 800, "発注書")
    
    # 発注日（右上）
    p.setFont("MS-Gothic", 12)
    p.drawString(400, 800, f"発注日: {order.order_date.strftime('%Y年%m月%d日')}")
    p.drawString(400, 780, f"発注番号: {order.id}")
    
    # 発注先情報（左上）
    y_supplier = 750
    p.drawString(50, y_supplier, f"【発注先】")
    p.drawString(50, y_supplier - 20, f"{supplier.name}")
    
    if supplier.address:
        p.drawString(50, y_supplier - 40, f"住所: {supplier.address}")
        y_supplier -= 20
    
    if supplier.fax_number:
        p.drawString(50, y_supplier - 40, f"FAX: {supplier.fax_number}")
        y_supplier -= 20
    
    if supplier.email:
        p.drawString(50, y_supplier - 40, f"メール: {supplier.email}")
    
    # 発注元クリニック情報（右下）
    y_clinic = 650
    p.drawString(350, y_clinic, f"【発注元】")
    p.drawString(350, y_clinic - 20, f"{clinic_info.name}")
    
    if clinic_info.director:
        p.drawString(350, y_clinic - 40, f"院長: {clinic_info.director}")
        y_clinic -= 20
        
    if clinic_info.address:
        p.drawString(350, y_clinic - 40, f"住所: {clinic_info.address}")
        y_clinic -= 20
    
    if clinic_info.phone:
        p.drawString(350, y_clinic - 40, f"TEL: {clinic_info.phone}")
        y_clinic -= 20
    
    if clinic_info.fax:
        p.drawString(350, y_clinic - 40, f"FAX: {clinic_info.fax}")
    
    # 区切り線
    p.line(50, 580, 550, 580)
    
    # テーブルヘッダー
    p.setFont("MS-Gothic", 12)
    p.drawString(50, 560, "商品名")
    p.drawString(300, 560, "数量")
    p.drawString(400, 560, "単位")
    p.line(50, 550, 550, 550)
    
    # テーブル内容
    y = 530
    p.setFont("MS-Gothic", 12)
    for order_item in order_items:
        item = order_item.item
        p.drawString(50, y, item.name)
        p.drawString(300, y, str(order_item.quantity))
        unit = "箱" if item.unit_type == "box" else "個"
        p.drawString(400, y, unit)
        y -= 20
    
    # 備考
    p.drawString(50, 100, "備考:")
    p.drawString(50, 80, "このFAXは自動生成されています。")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    
    # 発注のステータスを更新
    order.status = 'sent'
    db.session.commit()
    
    return send_file(buffer, as_attachment=True, download_name=f"order_{order_id}.pdf", mimetype='application/pdf')

@app.route('/monthly_report', methods=['GET', 'POST'])
def monthly_report():
    year = datetime.now().year
    month = datetime.now().month
    
    if request.method == 'POST':
        year = request.form.get('year', type=int)
        month = request.form.get('month', type=int)
    
    # 月初と月末
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # 使用量集計
    usages = db.session.query(
        Item.name,
        db.func.sum(Usage.quantity).label('total_quantity')
    ).join(
        Usage, Usage.item_id == Item.id
    ).filter(
        Usage.usage_date >= start_date,
        Usage.usage_date < end_date
    ).group_by(
        Item.id
    ).all()
    
    # 発注量集計
    orders = db.session.query(
        Item.name,
        db.func.sum(OrderItem.quantity).label('total_quantity')
    ).join(
        OrderItem, OrderItem.item_id == Item.id
    ).join(
        Order, Order.id == OrderItem.order_id
    ).filter(
        Order.order_date >= start_date,
        Order.order_date < end_date
    ).group_by(
        Item.id
    ).all()
    
    return render_template('monthly_report.html', 
                          usages=usages, 
                          orders=orders, 
                          year=year, 
                          month=month)

@app.route('/patient_set/<int:set_id>', methods=['GET', 'POST'])
def patient_set_detail(set_id):
    patient_set = PatientSet.query.get_or_404(set_id)
    all_items = Item.query.all()
    
    if request.method == 'POST':
        # 既存のアイテムをすべて削除
        SetItem.query.filter_by(patient_set_id=set_id).delete()
        
        # POSTデータから複数のアイテムと数量を取得
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        
        # 各アイテムをセットに追加
        for i in range(len(item_ids)):
            if i < len(quantities) and item_ids[i] and quantities[i]:
                try:
                    item_id = int(item_ids[i])
                    quantity = int(quantities[i])
                    
                    if quantity > 0:
                        set_item = SetItem(
                            patient_set_id=set_id,
                            item_id=item_id,
                            quantity=quantity
                        )
                        db.session.add(set_item)
                except (ValueError, TypeError):
                    continue
        
        db.session.commit()
        flash('患者セットを更新しました', 'success')
        return redirect(url_for('patient_set_detail', set_id=set_id))
    
    # 現在のセットアイテムを取得
    set_items = SetItem.query.filter_by(patient_set_id=set_id).all()
    
    return render_template(
        'patient_set_detail.html', 
        patient_set=patient_set,
        all_items=all_items,
        set_items=set_items
    )

@app.route('/item_set/<int:set_id>', methods=['GET', 'POST'])
def item_set_detail(set_id):
    item_set = ItemSet.query.get_or_404(set_id)
    all_items = Item.query.all()
    
    if request.method == 'POST':
        # 既存のアイテムをすべて削除
        SetItem.query.filter_by(item_set_id=set_id).delete()
        
        # POSTデータから複数のアイテムと数量を取得
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        
        # 各アイテムをセットに追加
        for i in range(len(item_ids)):
            if i < len(quantities) and item_ids[i] and quantities[i]:
                try:
                    item_id = int(item_ids[i])
                    quantity = int(quantities[i])
                    
                    if quantity > 0:
                        set_item = SetItem(
                            item_set_id=set_id,
                            item_id=item_id,
                            quantity=quantity
                        )
                        db.session.add(set_item)
                except (ValueError, TypeError):
                    continue
        
        db.session.commit()
        flash('汎用セットを更新しました', 'success')
        return redirect(url_for('item_set_detail', set_id=set_id))
    
    # 現在のセットアイテムを取得
    set_items = SetItem.query.filter_by(item_set_id=set_id).all()
    
    return render_template(
        'item_set_detail.html', 
        item_set=item_set,
        all_items=all_items,
        set_items=set_items
    )

@app.route('/bulk_use_items', methods=['GET', 'POST'])
def bulk_use_items():
    """複数備品を一括で使用登録する機能"""
    items = Item.query.all()
    patients = Patient.query.all()
    
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        
        # 発注情報を集約するための辞書
        orders_by_supplier = {}
        
        for i in range(len(item_ids)):
            item_id = item_ids[i]
            quantity = int(quantities[i])
            
            if not item_id or quantity <= 0:
                continue
                
            item = Item.query.get_or_404(item_id)
            
            # 使用記録を保存
            usage = Usage(
                item_id=item.id,
                quantity=quantity,
                patient_id=patient_id if patient_id else None,
                usage_date=datetime.utcnow()
            )
            db.session.add(usage)
            
            # 在庫を減らす
            item.current_stock = max(0, item.current_stock - quantity)
            
            # 在庫が最低在庫数を下回ったら発注
            if item.current_stock <= item.minimum_stock and item.supplier_id:
                supplier_id = item.supplier_id
                
                # 今日の発注がすでにあるか確認
                if supplier_id in orders_by_supplier:
                    order = orders_by_supplier[supplier_id]
                else:
                    existing_order = Order.query.filter_by(
                        supplier_id=supplier_id,
                        status='pending'
                    ).order_by(Order.order_date.desc()).first()
                    
                    if existing_order:
                        order = existing_order
                    else:
                        # 新しい発注を作成
                        new_order = Order(
                            supplier_id=supplier_id,
                            status='pending',
                            order_date=datetime.utcnow()
                        )
                        db.session.add(new_order)
                        db.session.flush()
                        order = new_order
                    
                    orders_by_supplier[supplier_id] = order
                
                # 同じアイテムの発注がすでにあるか確認
                existing_order_item = OrderItem.query.filter_by(
                    order_id=order.id,
                    item_id=item.id
                ).first()
                
                if existing_order_item:
                    existing_order_item.quantity += quantity
                else:
                    new_order_item = OrderItem(
                        order_id=order.id,
                        item_id=item.id,
                        quantity=quantity
                    )
                    db.session.add(new_order_item)
        
        db.session.commit()
        
        if orders_by_supplier:
            flash('備品を使用登録し、発注書を生成しました', 'success')
            # 最初の発注を表示
            first_order = list(orders_by_supplier.values())[0]
            return redirect(url_for('view_order', order_id=first_order.id))
        else:
            flash('備品を使用登録しました', 'success')
            return redirect(url_for('items'))
    
    return render_template('bulk_use_items.html', items=items, patients=patients)

@app.route('/patient_sets_manage/<int:patient_id>')
def patient_sets_manage(patient_id):
    # 患者情報を取得
    patient = Patient.query.get_or_404(patient_id)
    
    # この患者に関連付けられたセットを取得
    patient_sets = PatientSet.query.filter_by(patient_id=patient_id).all()
    
    # 全ての備品を取得（新規セット追加用）
    all_items = Item.query.all()
    
    return render_template(
        'patient_sets_manage.html', 
        patient=patient, 
        patient_sets=patient_sets, 
        items=all_items
    )

@app.route('/delete_patient_set/<int:set_id>')
def delete_patient_set(set_id):
    # 患者セットを取得
    patient_set = PatientSet.query.get_or_404(set_id)
    patient_id = patient_set.patient_id
    
    # セットに紐づく備品アイテムを削除
    SetItem.query.filter_by(patient_set_id=set_id).delete()
    
    # セット自体を削除
    db.session.delete(patient_set)
    db.session.commit()
    
    flash(f'セット「{patient_set.name}」を削除しました', 'success')
    return redirect(url_for('patient_sets_manage', patient_id=patient_id))

@app.route('/clinic_settings', methods=['GET', 'POST'])
def clinic_settings():
    # クリニック情報を取得、なければ作成
    clinic_info = ClinicInfo.query.first()
    if not clinic_info:
        clinic_info = ClinicInfo(name="訪問診療クリニック")
        db.session.add(clinic_info)
        db.session.commit()
    
    if request.method == 'POST':
        clinic_info.name = request.form['name']
        clinic_info.address = request.form['address']
        clinic_info.phone = request.form['phone']
        clinic_info.fax = request.form['fax']
        clinic_info.email = request.form['email']
        clinic_info.website = request.form['website']
        clinic_info.director = request.form['director']
        
        db.session.commit()
        flash('クリニック情報を更新しました', 'success')
        return redirect(url_for('clinic_settings'))
    
    return render_template('clinic_settings.html', clinic=clinic_info)

# データベース初期化
@app.route('/initialize_db')
def initialize_db():
    db.drop_all()
    db.create_all()
    
    # ダミーデータの作成
    # 1. 発注先
    supplier1 = Supplier(name='サンプル医療機器', fax_number='03-1234-5678', address='東京都千代田区1-1', email='contact@sample-med.co.jp')
    supplier2 = Supplier(name='メディカルサプライ', fax_number='06-8765-4321', address='大阪府大阪市中央区2-2', email='info@medical-supply.co.jp')
    db.session.add_all([supplier1, supplier2])
    db.session.commit()
    
    # 2. 備品
    items = [
        Item(name='ディスポ手袋 Mサイズ', unit_type='box', items_per_box=100, minimum_stock=5, current_stock=10, supplier_id=supplier1.id),
        Item(name='ディスポ手袋 Lサイズ', unit_type='box', items_per_box=100, minimum_stock=5, current_stock=7, supplier_id=supplier1.id),
        Item(name='消毒用アルコール', unit_type='individual', minimum_stock=10, current_stock=15, supplier_id=supplier1.id),
        Item(name='血圧計', unit_type='individual', minimum_stock=2, current_stock=3, supplier_id=supplier2.id),
        Item(name='体温計', unit_type='individual', minimum_stock=5, current_stock=6, supplier_id=supplier2.id),
        Item(name='聴診器', unit_type='individual', minimum_stock=2, current_stock=2, supplier_id=supplier2.id),
        Item(name='注射針 23G', unit_type='box', items_per_box=100, minimum_stock=3, current_stock=4, supplier_id=supplier1.id),
        Item(name='注射針 25G', unit_type='box', items_per_box=100, minimum_stock=3, current_stock=2, supplier_id=supplier1.id),
        Item(name='シリンジ 10ml', unit_type='box', items_per_box=50, minimum_stock=3, current_stock=5, supplier_id=supplier1.id)
    ]
    db.session.add_all(items)
    db.session.commit()
    
    # 3. 患者
    patients = [
        Patient(name='佐藤太郎', patient_id='P001', address='東京都新宿区1-1', phone='090-1111-2222'),
        Patient(name='鈴木花子', patient_id='P002', address='東京都渋谷区2-2', phone='090-3333-4444'),
        Patient(name='田中一郎', patient_id='P003', address='東京都中野区3-3', phone='090-5555-6666')
    ]
    db.session.add_all(patients)
    db.session.commit()
    
    # 4. 患者セット
    patient_sets = [
        PatientSet(name='基本セット', patient_id=patients[0].id),
        PatientSet(name='糖尿病ケアセット', patient_id=patients[1].id),
        PatientSet(name='高血圧ケアセット', patient_id=patients[2].id)
    ]
    db.session.add_all(patient_sets)
    db.session.commit()
    
    # 5. セットアイテム
    set_items = [
        # 基本セット
        SetItem(patient_set_id=patient_sets[0].id, item_id=items[0].id, quantity=2),  # 手袋 M
        SetItem(patient_set_id=patient_sets[0].id, item_id=items[2].id, quantity=1),  # 消毒用アルコール
        SetItem(patient_set_id=patient_sets[0].id, item_id=items[4].id, quantity=1),  # 体温計
        
        # 糖尿病ケアセット
        SetItem(patient_set_id=patient_sets[1].id, item_id=items[0].id, quantity=2),  # 手袋 M
        SetItem(patient_set_id=patient_sets[1].id, item_id=items[2].id, quantity=1),  # 消毒用アルコール
        SetItem(patient_set_id=patient_sets[1].id, item_id=items[6].id, quantity=1),  # 注射針 23G
        SetItem(patient_set_id=patient_sets[1].id, item_id=items[8].id, quantity=1),  # シリンジ 10ml
        
        # 高血圧ケアセット
        SetItem(patient_set_id=patient_sets[2].id, item_id=items[0].id, quantity=1),  # 手袋 M
        SetItem(patient_set_id=patient_sets[2].id, item_id=items[3].id, quantity=1),  # 血圧計
        SetItem(patient_set_id=patient_sets[2].id, item_id=items[5].id, quantity=1)   # 聴診器
    ]
    db.session.add_all(set_items)
    db.session.commit()
    
    flash('データベースを初期化し、サンプルデータを追加しました', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')
