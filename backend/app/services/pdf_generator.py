from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Line
from io import BytesIO
from datetime import datetime
import locale

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    pass


def format_currency(value: float) -> str:
    """Formata valor como moeda brasileira"""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_cpf(cpf: str) -> str:
    """Formata CPF com máscara"""
    cpf = ''.join(filter(str.isdigit, str(cpf)))
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    return cpf


def format_cnpj(cnpj: str) -> str:
    """Formata CNPJ com máscara"""
    cnpj = ''.join(filter(str.isdigit, str(cnpj)))
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj


def generate_receipt_pdf(data: dict) -> bytes:
    """
    Gera um PDF de recibo de pagamento profissional.
    data: {
        "company_name": str,
        "company_cnpj": str,
        "employee_name": str,
        "employee_cpf": str,
        "employee_email": str,
        "amount": float,
        "reference_month": str, # "12/2025"
        "payment_date": str,
        "description": str,
        "title": str (opcional)
    }
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=5*mm,
        textColor=colors.HexColor('#1a1a2e'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#666666'),
        spaceAfter=10*mm
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#2c3e50'),
        spaceBefore=8*mm,
        spaceAfter=3*mm,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        leading=14,
        textColor=colors.HexColor('#333333')
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#666666')
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a1a2e')
    )
    
    amount_style = ParagraphStyle(
        'Amount',
        parent=styles['Normal'],
        fontSize=16,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        textColor=colors.HexColor('#27ae60'),
        spaceBefore=5*mm,
        spaceAfter=5*mm
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#999999')
    )
    
    elements = []
    
    # ========== CABEÇALHO ==========
    elements.append(Paragraph("RECIBO DE PAGAMENTO", title_style))
    
    ref_month = data.get('reference_month', datetime.now().strftime('%m/%Y'))
    elements.append(Paragraph(f"Competência: {ref_month}", subtitle_style))
    
    # Linha separadora
    elements.append(Spacer(1, 2*mm))
    
    # ========== DADOS DA EMPRESA ==========
    elements.append(Paragraph("DADOS DO EMPREGADOR", section_title_style))
    
    company_data = [
        [
            Paragraph("<b>Razão Social:</b>", label_style),
            Paragraph(data.get('company_name', '-'), value_style)
        ],
        [
            Paragraph("<b>CNPJ:</b>", label_style),
            Paragraph(format_cnpj(data.get('company_cnpj', '')), value_style)
        ]
    ]
    
    t_company = Table(company_data, colWidths=[40*mm, 130*mm])
    t_company.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#dee2e6')),
    ]))
    elements.append(t_company)
    
    # ========== DADOS DO COLABORADOR ==========
    elements.append(Paragraph("DADOS DO COLABORADOR", section_title_style))
    
    employee_data = [
        [
            Paragraph("<b>Nome Completo:</b>", label_style),
            Paragraph(data.get('employee_name', '-'), value_style)
        ],
        [
            Paragraph("<b>CPF:</b>", label_style),
            Paragraph(format_cpf(data.get('employee_cpf', '')), value_style)
        ],
        [
            Paragraph("<b>E-mail:</b>", label_style),
            Paragraph(data.get('employee_email', '-'), value_style)
        ]
    ]
    
    t_employee = Table(employee_data, colWidths=[40*mm, 130*mm])
    t_employee.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#dee2e6')),
    ]))
    elements.append(t_employee)
    
    # ========== VALOR ==========
    elements.append(Paragraph("VALOR DO PAGAMENTO", section_title_style))
    
    amount = data.get('amount', 0)
    amount_formatted = format_currency(amount)
    
    # Box de valor destacado
    value_box_data = [[Paragraph(amount_formatted, amount_style)]]
    t_value = Table(value_box_data, colWidths=[170*mm])
    t_value.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f5e9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#27ae60')),
        ('TOPPADDING', (0, 0), (-1, -1), 5*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5*mm),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(t_value)
    
    # ========== DESCRIÇÃO ==========
    elements.append(Spacer(1, 5*mm))
    
    description = data.get('description', 'Pagamento de salário')
    payment_date = data.get('payment_date', datetime.now().strftime('%d/%m/%Y'))
    
    declaracao = f"""
    Declaro ter recebido de <b>{data.get('company_name', '-')}</b>, inscrita no CNPJ sob nº 
    <b>{format_cnpj(data.get('company_cnpj', ''))}</b>, a importância líquida de <b>{amount_formatted}</b> 
    ({valor_por_extenso(amount)}), referente a <b>{data.get('rubrica_name') or description}</b>, competência <b>{ref_month}</b>, 
    realizado em <b>{payment_date}</b>.
    """
    
    elements.append(Paragraph(declaracao.strip(), body_style))
    
    # ========== DADOS DO PAGAMENTO ==========
    elements.append(Paragraph("DETALHES DO PAGAMENTO", section_title_style))
    
    payment_details = [
        [
            Paragraph("<b>Descrição:</b>", label_style),
            Paragraph(description, value_style)
        ],
        [
            Paragraph("<b>Competência:</b>", label_style),
            Paragraph(ref_month, value_style)
        ],
        [
            Paragraph("<b>Data Pagamento:</b>", label_style),
            Paragraph(payment_date, value_style)
        ]
    ]
    
    t_details = Table(payment_details, colWidths=[40*mm, 130*mm])
    t_details.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#dee2e6')),
    ]))
    elements.append(t_details)
    
    # ========== ASSINATURA ==========
    elements.append(Spacer(1, 15*mm))
    
    signature_style = ParagraphStyle(
        'Signature',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#333333')
    )
    
    sig_data = [
        [Paragraph("_" * 50, signature_style)],
        [Paragraph(f"<b>{data.get('employee_name', '-')}</b>", signature_style)],
        [Paragraph(f"CPF: {format_cpf(data.get('employee_cpf', ''))}", label_style)],
    ]
    
    t_sig = Table(sig_data, colWidths=[170*mm])
    t_sig.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (0, 0), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    elements.append(t_sig)
    
    # ========== LOCAL E DATA ==========
    elements.append(Spacer(1, 10*mm))
    
    today = datetime.now()
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 
             'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    local_data = f"__________________, {today.day} de {meses[today.month-1]} de {today.year}"
    
    elements.append(Paragraph(local_data, signature_style))
    
    # ========== RODAPÉ ==========
    elements.append(Spacer(1, 15*mm))
    
    doc_id = data.get('doc_id', datetime.now().strftime('%Y%m%d%H%M%S'))
    elements.append(Paragraph(f"Documento gerado eletronicamente em {today.strftime('%d/%m/%Y às %H:%M')}", footer_style))
    elements.append(Paragraph(f"ID: {doc_id}", footer_style))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def valor_por_extenso(valor: float) -> str:
    """Converte valor numérico para extenso em português"""
    unidades = ['', 'um', 'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove',
                'dez', 'onze', 'doze', 'treze', 'quatorze', 'quinze', 'dezesseis', 'dezessete', 'dezoito', 'dezenove']
    dezenas = ['', '', 'vinte', 'trinta', 'quarenta', 'cinquenta', 'sessenta', 'setenta', 'oitenta', 'noventa']
    centenas = ['', 'cento', 'duzentos', 'trezentos', 'quatrocentos', 'quinhentos', 'seiscentos', 'setecentos', 'oitocentos', 'novecentos']
    
    def extenso_ate_999(n):
        if n == 0:
            return ''
        if n == 100:
            return 'cem'
        
        resultado = []
        
        # Centenas
        c = n // 100
        if c > 0:
            resultado.append(centenas[c])
        
        # Dezenas e unidades
        resto = n % 100
        if resto > 0:
            if resto < 20:
                resultado.append(unidades[resto])
            else:
                d = resto // 10
                u = resto % 10
                if u == 0:
                    resultado.append(dezenas[d])
                else:
                    resultado.append(dezenas[d] + ' e ' + unidades[u])
        
        return ' e '.join(resultado)
    
    if valor == 0:
        return 'zero reais'
    
    inteiro = int(valor)
    centavos = int(round((valor - inteiro) * 100))
    
    resultado = []
    
    # Milhões
    milhoes = inteiro // 1000000
    if milhoes > 0:
        if milhoes == 1:
            resultado.append('um milhão')
        else:
            resultado.append(extenso_ate_999(milhoes) + ' milhões')
        inteiro %= 1000000
    
    # Milhares
    milhares = inteiro // 1000
    if milhares > 0:
        if milhares == 1:
            resultado.append('mil')
        else:
            resultado.append(extenso_ate_999(milhares) + ' mil')
        inteiro %= 1000
    
    # Centenas, dezenas e unidades
    if inteiro > 0:
        resultado.append(extenso_ate_999(inteiro))
    
    texto_reais = ' '.join(resultado)
    
    if texto_reais:
        if int(valor) == 1:
            texto_reais += ' real'
        else:
            texto_reais += ' reais'
    
    if centavos > 0:
        if texto_reais:
            texto_reais += ' e '
        texto_centavos = extenso_ate_999(centavos)
        if centavos == 1:
            texto_reais += texto_centavos + ' centavo'
        else:
            texto_reais += texto_centavos + ' centavos'
    
    return texto_reais if texto_reais else 'zero reais'


def generate_payslip_pdf(data: dict) -> bytes:
    """
    Gera um contracheque/holerite completo.
    data: {
        "company_name": str,
        "company_cnpj": str,
        "employee_name": str,
        "employee_cpf": str,
        "employee_role": str,
        "reference_month": str,
        "items": [{"description": str, "type": "provento"|"desconto", "value": float}],
        "total_proventos": float,
        "total_descontos": float,
        "liquido": float
    }
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=3*mm,
        textColor=colors.HexColor('#1a1a2e')
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#333333')
    )
    
    elements = []
    
    # Cabeçalho
    elements.append(Paragraph("DEMONSTRATIVO DE PAGAMENTO", title_style))
    elements.append(Paragraph(f"Competência: {data.get('reference_month', '-')}", header_style))
    elements.append(Spacer(1, 5*mm))
    
    # Dados empresa/colaborador
    header_data = [
        ['EMPRESA', 'COLABORADOR'],
        [data.get('company_name', '-'), data.get('employee_name', '-')],
        [f"CNPJ: {data.get('company_cnpj', '-')}", f"CPF: {data.get('employee_cpf', '-')}"],
        ['', f"Cargo: {data.get('employee_role', '-')}"]
    ]
    
    t_header = Table(header_data, colWidths=[90*mm, 90*mm])
    t_header.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 5*mm))
    
    # Itens
    items = data.get('items', [])
    table_data = [['DESCRIÇÃO', 'TIPO', 'PROVENTOS', 'DESCONTOS']]
    
    for item in items:
        tipo = 'Provento' if item.get('type') == 'provento' else 'Desconto'
        provento = format_currency(item.get('value', 0)) if item.get('type') == 'provento' else ''
        desconto = format_currency(item.get('value', 0)) if item.get('type') == 'desconto' else ''
        table_data.append([item.get('description', '-'), tipo, provento, desconto])
    
    # Totais
    table_data.append(['', '', '', ''])
    table_data.append(['TOTAL PROVENTOS', '', format_currency(data.get('total_proventos', 0)), ''])
    table_data.append(['TOTAL DESCONTOS', '', '', format_currency(data.get('total_descontos', 0))])
    table_data.append(['LÍQUIDO A RECEBER', '', format_currency(data.get('liquido', 0)), ''])
    
    t_items = Table(table_data, colWidths=[70*mm, 30*mm, 40*mm, 40*mm])
    t_items.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ecf0f1')),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#27ae60')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
    ]))
    elements.append(t_items)
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
