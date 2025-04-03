// 数量入力の制御
document.addEventListener('DOMContentLoaded', function() {
    // 数量調整ボタン
    const decrementButtons = document.querySelectorAll('.decrement-btn');
    const incrementButtons = document.querySelectorAll('.increment-btn');
    
    decrementButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentNode.querySelector('.quantity-input');
            let value = parseInt(input.value);
            if (value > 1) {
                input.value = value - 1;
            }
        });
    });
    
    incrementButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentNode.querySelector('.quantity-input');
            let value = parseInt(input.value);
            input.value = value + 1;
        });
    });
    
    // 患者選択時にセットを読み込む
    const patientSelect = document.getElementById('patient-select');
    if (patientSelect) {
        patientSelect.addEventListener('change', function() {
            const patientId = this.value;
            if (patientId) {
                window.location.href = `/use_set?patient_id=${patientId}`;
            }
        });
    }
    
    // フラッシュメッセージの自動消去
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert) {
                const closeButton = alert.querySelector('.btn-close');
                if (closeButton) {
                    closeButton.click();
                }
            }
        }, 5000);
    });
});

// 印刷機能
function printOrder() {
    window.print();
}
