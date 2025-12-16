"""
Serviço para geração de PDF de NF-e (DANFE)
"""
from io import BytesIO
from datetime import datetime
from typing import Optional
import xml.etree.ElementTree as ET
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
import barcode
from barcode.writer import ImageWriter


class NFePDFGenerator:
    """Gerador de DANFE (Documento Auxiliar da Nota Fiscal Eletrônica)"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configura estilos customizados"""
        self.styles.add(ParagraphStyle(
            name='SmallBold',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='Small',
            parent=self.styles['Normal'],
            fontSize=7,
            fontName='Helvetica'
        ))
        self.styles.add(ParagraphStyle(
            name='Tiny',
            parent=self.styles['Normal'],
            fontSize=6,
            fontName='Helvetica'
        ))
        self.styles.add(ParagraphStyle(
            name='Title',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER
        ))
    
    def parse_xml(self, xml_content: str) -> dict:
        """Extrai dados do XML da NF-e"""
        try:
            root = ET.fromstring(xml_content)
            
            # Namespace da NF-e
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            # Busca elementos principais
            inf_nfe = root.find('.//nfe:infNFe', ns)
            ide = root.find('.//nfe:ide', ns)
            emit = root.find('.//nfe:emit', ns)
            dest = root.find('.//nfe:dest', ns)
            total = root.find('.//nfe:total/nfe:ICMSTot', ns)
            transp = root.find('.//nfe:transp', ns)
            items = root.findall('.//nfe:det', ns)
            
            # Extrai chave de acesso
            chave = inf_nfe.get('Id', '').replace('NFe', '') if inf_nfe is not None else ''
            
            # Dados da nota
            data = {
                'chave': chave,
                'numero': self._get_text(ide, 'nfe:nNF', ns),
                'serie': self._get_text(ide, 'nfe:serie', ns),
                'data_emissao': self._get_text(ide, 'nfe:dhEmi', ns),
                'data_saida': self._get_text(ide, 'nfe:dhSaiEnt', ns),
                'natureza': self._get_text(ide, 'nfe:natOp', ns),
                'tipo_nf': 'ENTRADA' if self._get_text(ide, 'nfe:tpNF', ns) == '0' else 'SAÍDA',
                'modelo': self._get_text(ide, 'nfe:mod', ns),
                
                # Emitente
                'emit_cnpj': self._get_text(emit, 'nfe:CNPJ', ns),
                'emit_nome': self._get_text(emit, 'nfe:xNome', ns),
                'emit_fantasia': self._get_text(emit, 'nfe:xFant', ns),
                'emit_endereco': self._format_endereco(emit, ns),
                'emit_ie': self._get_text(emit, 'nfe:IE', ns),
                
                # Destinatário
                'dest_cnpj': self._get_text(dest, 'nfe:CNPJ', ns) or self._get_text(dest, 'nfe:CPF', ns),
                'dest_nome': self._get_text(dest, 'nfe:xNome', ns),
                'dest_endereco': self._format_endereco(dest, ns),
                'dest_ie': self._get_text(dest, 'nfe:IE', ns),
                
                # Totais
                'bc_icms': self._get_text(total, 'nfe:vBC', ns),
                'valor_icms': self._get_text(total, 'nfe:vICMS', ns),
                'valor_produtos': self._get_text(total, 'nfe:vProd', ns),
                'valor_frete': self._get_text(total, 'nfe:vFrete', ns),
                'valor_seguro': self._get_text(total, 'nfe:vSeg', ns),
                'valor_desconto': self._get_text(total, 'nfe:vDesc', ns),
                'valor_total': self._get_text(total, 'nfe:vNF', ns),
                
                # Transporte
                'transp_modalidade': self._get_modalidade_frete(transp, ns),
                
                # Itens
                'items': self._parse_items(items, ns)
            }
            
            return data
        except Exception as e:
            raise ValueError(f"Erro ao parsear XML: {str(e)}")
    
    def _get_text(self, element, tag: str, ns: dict) -> str:
        """Extrai texto de um elemento XML"""
        if element is None:
            return ''
        found = element.find(tag, ns)
        return found.text if found is not None and found.text else ''
    
    def _format_endereco(self, element, ns: dict) -> str:
        """Formata endereço completo"""
        if element is None:
            return ''
        
        ender = element.find('nfe:enderEmit', ns) or element.find('nfe:enderDest', ns)
        if ender is None:
            return ''
        
        logradouro = self._get_text(ender, 'nfe:xLgr', ns)
        numero = self._get_text(ender, 'nfe:nro', ns)
        complemento = self._get_text(ender, 'nfe:xCpl', ns)
        bairro = self._get_text(ender, 'nfe:xBairro', ns)
        municipio = self._get_text(ender, 'nfe:xMun', ns)
        uf = self._get_text(ender, 'nfe:UF', ns)
        cep = self._get_text(ender, 'nfe:CEP', ns)
        
        endereco = f"{logradouro}, {numero}"
        if complemento:
            endereco += f", {complemento}"
        endereco += f" - {bairro}, {municipio}/{uf} - CEP: {cep}"
        
        return endereco
    
    def _get_modalidade_frete(self, transp, ns: dict) -> str:
        """Retorna modalidade de frete"""
        if transp is None:
            return 'SEM FRETE'
        
        mod = self._get_text(transp, 'nfe:modFrete', ns)
        modalidades = {
            '0': 'POR CONTA DO EMITENTE',
            '1': 'POR CONTA DO DESTINATÁRIO',
            '2': 'POR CONTA DE TERCEIROS',
            '9': 'SEM FRETE'
        }
        return modalidades.get(mod, 'NÃO INFORMADO')
    
    def _parse_items(self, items, ns: dict) -> list:
        """Extrai itens da nota"""
        result = []
        for item in items:
            prod = item.find('nfe:prod', ns)
            if prod is None:
                continue
            
            result.append({
                'codigo': self._get_text(prod, 'nfe:cProd', ns),
                'descricao': self._get_text(prod, 'nfe:xProd', ns),
                'ncm': self._get_text(prod, 'nfe:NCM', ns),
                'cfop': self._get_text(prod, 'nfe:CFOP', ns),
                'unidade': self._get_text(prod, 'nfe:uCom', ns),
                'quantidade': self._get_text(prod, 'nfe:qCom', ns),
                'valor_unitario': self._get_text(prod, 'nfe:vUnCom', ns),
                'valor_total': self._get_text(prod, 'nfe:vProd', ns),
            })
        
        return result
    
    def generate_pdf(self, xml_content: str) -> BytesIO:
        """Gera PDF (DANFE) a partir do XML da NF-e"""
        # Parse XML
        data = self.parse_xml(xml_content)
        
        # Cria buffer para o PDF
        buffer = BytesIO()
        
        # Cria documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=10*mm,
            leftMargin=10*mm,
            topMargin=10*mm,
            bottomMargin=10*mm
        )
        
        # Conteúdo
        story = []
        
        # Cabeçalho
        story.extend(self._build_header(data))
        story.append(Spacer(1, 5*mm))
        
        # Emitente e Destinatário
        story.extend(self._build_parties(data))
        story.append(Spacer(1, 3*mm))
        
        # Itens
        story.extend(self._build_items(data))
        story.append(Spacer(1, 3*mm))
        
        # Totais
        story.extend(self._build_totals(data))
        story.append(Spacer(1, 3*mm))
        
        # Informações adicionais
        story.extend(self._build_footer(data))
        
        # Gera PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer
    
    def _build_header(self, data: dict) -> list:
        """Constrói cabeçalho do DANFE"""
        elements = []
        
        # Título
        elements.append(Paragraph('DANFE', self.styles['Title']))
        elements.append(Paragraph(
            'Documento Auxiliar da Nota Fiscal Eletrônica',
            self.styles['Small']
        ))
        elements.append(Spacer(1, 3*mm))
        
        # Informações principais
        header_data = [
            ['CHAVE DE ACESSO', data['chave']],
            ['NÚMERO', data['numero']],
            ['SÉRIE', data['serie']],
            ['DATA EMISSÃO', self._format_datetime(data['data_emissao'])],
            ['NATUREZA', data['natureza']],
            ['TIPO', data['tipo_nf']],
        ]
        
        t = Table(header_data, colWidths=[40*mm, 140*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t)
        
        return elements
    
    def _build_parties(self, data: dict) -> list:
        """Constrói seção de emitente e destinatário"""
        elements = []
        
        # Emitente
        elements.append(Paragraph('<b>EMITENTE</b>', self.styles['SmallBold']))
        emit_data = [
            ['Razão Social', data['emit_nome']],
            ['CNPJ', self._format_cnpj(data['emit_cnpj'])],
            ['Inscrição Estadual', data['emit_ie']],
            ['Endereço', data['emit_endereco']],
        ]
        
        t = Table(emit_data, colWidths=[40*mm, 140*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 3*mm))
        
        # Destinatário
        elements.append(Paragraph('<b>DESTINATÁRIO</b>', self.styles['SmallBold']))
        dest_data = [
            ['Razão Social', data['dest_nome']],
            ['CNPJ/CPF', self._format_cnpj(data['dest_cnpj'])],
            ['Inscrição Estadual', data['dest_ie']],
            ['Endereço', data['dest_endereco']],
        ]
        
        t = Table(dest_data, colWidths=[40*mm, 140*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t)
        
        return elements
    
    def _build_items(self, data: dict) -> list:
        """Constrói tabela de itens"""
        elements = []
        
        elements.append(Paragraph('<b>PRODUTOS / SERVIÇOS</b>', self.styles['SmallBold']))
        
        # Cabeçalho da tabela
        items_data = [[
            'Cód', 'Descrição', 'NCM', 'CFOP', 'UN', 'Qtd', 'Vl. Unit', 'Vl. Total'
        ]]
        
        # Itens
        for item in data['items']:
            items_data.append([
                item['codigo'][:10],
                item['descricao'][:40],
                item['ncm'],
                item['cfop'],
                item['unidade'],
                self._format_number(item['quantidade'], 2),
                self._format_currency(item['valor_unitario']),
                self._format_currency(item['valor_total']),
            ])
        
        t = Table(items_data, colWidths=[20*mm, 60*mm, 15*mm, 15*mm, 10*mm, 15*mm, 20*mm, 20*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
        ]))
        elements.append(t)
        
        return elements
    
    def _build_totals(self, data: dict) -> list:
        """Constrói seção de totais"""
        elements = []
        
        elements.append(Paragraph('<b>CÁLCULO DO IMPOSTO</b>', self.styles['SmallBold']))
        
        totals_data = [
            ['Base de Cálculo ICMS', self._format_currency(data['bc_icms'])],
            ['Valor do ICMS', self._format_currency(data['valor_icms'])],
            ['Valor dos Produtos', self._format_currency(data['valor_produtos'])],
            ['Valor do Frete', self._format_currency(data['valor_frete'])],
            ['Valor do Seguro', self._format_currency(data['valor_seguro'])],
            ['Desconto', self._format_currency(data['valor_desconto'])],
            ['VALOR TOTAL DA NOTA', self._format_currency(data['valor_total'])],
        ]
        
        t = Table(totals_data, colWidths=[80*mm, 100*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.grey),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 8),
            ('FONTSIZE', (0, -1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        elements.append(t)
        
        return elements
    
    def _build_footer(self, data: dict) -> list:
        """Constrói rodapé com informações adicionais"""
        elements = []
        
        elements.append(Paragraph('<b>DADOS ADICIONAIS</b>', self.styles['SmallBold']))
        elements.append(Paragraph(
            f'Modalidade do Frete: {data["transp_modalidade"]}',
            self.styles['Small']
        ))
        
        return elements
    
    def _format_datetime(self, dt_str: str) -> str:
        """Formata data/hora"""
        if not dt_str:
            return ''
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.strftime('%d/%m/%Y %H:%M:%S')
        except:
            return dt_str
    
    def _format_cnpj(self, cnpj: str) -> str:
        """Formata CNPJ/CPF"""
        if not cnpj:
            return ''
        cnpj = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj) == 14:
            return f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}'
        elif len(cnpj) == 11:
            return f'{cnpj[:3]}.{cnpj[3:6]}.{cnpj[6:9]}-{cnpj[9:]}'
        return cnpj
    
    def _format_currency(self, value: str) -> str:
        """Formata valor monetário"""
        if not value:
            return 'R$ 0,00'
        try:
            return f'R$ {float(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        except:
            return value
    
    def _format_number(self, value: str, decimals: int = 2) -> str:
        """Formata número"""
        if not value:
            return '0'
        try:
            return f'{float(value):,.{decimals}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        except:
            return value
