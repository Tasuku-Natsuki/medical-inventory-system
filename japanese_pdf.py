"""
日本語PDFを生成するためのユーティリティモジュール
ReportLab用に最適化されています
"""
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph

# 日本語フォントを登録
def setup_japanese_fonts():
    """日本語フォントを登録する"""
    # 東アジア言語のサポートフォントを登録
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
    
    # カスタムスタイルシートを返す
    styles = getSampleStyleSheet()
    
    # 日本語用のスタイルを追加
    styles.add(ParagraphStyle(
        name='JapaneseNormal',
        fontName='HeiseiKakuGo-W5',
        fontSize=10,
        leading=12
    ))
    
    styles.add(ParagraphStyle(
        name='JapaneseHeading1',
        fontName='HeiseiKakuGo-W5',
        fontSize=18,
        leading=22,
        alignment=1  # 中央揃え
    ))
    
    styles.add(ParagraphStyle(
        name='JapaneseHeading2',
        fontName='HeiseiKakuGo-W5',
        fontSize=14,
        leading=17
    ))
    
    styles.add(ParagraphStyle(
        name='JapaneseRight',
        fontName='HeiseiKakuGo-W5',
        fontSize=10,
        leading=12,
        alignment=2  # 右揃え
    ))
    
    return styles

# 日本語テキストをParagraphでラップする
def japanese_paragraph(text, style):
    """日本語テキストをParagraphオブジェクトにラップする"""
    return Paragraph(text, style)
