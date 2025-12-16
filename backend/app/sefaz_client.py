"""
Cliente SOAP para SEFAZ - Distribuição DF-e (NFeDistribuicaoDFe)
Implementa comunicação com o serviço de distribuição de documentos fiscais
usando SOAP manual (sem dependência de WSDL) com certificado A1
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import base64
import gzip
import logging
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.backends import default_backend
from cryptography import x509
import httpx
import certifi
import ssl
import tempfile
import os
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DFeDocument:
    """Documento retornado pela SEFAZ"""
    nsu: str
    schema: str  # resNFe, procNFe, resEvento, etc.
    chave: str
    tipo_documento: str  # NF-e, Evento, Resumo
    xml_content: str  # XML base64 decodificado


class SefazDFeClient:
    """Cliente para comunicação com SEFAZ via NFeDistribuicaoDFe"""
    
    # URLs dos endpoints SOAP - Ambiente Nacional (AN) para Distribuição DF-e
    # O serviço de distribuição é CENTRALIZADO no AN, não é por UF
    ENDPOINTS_HOMOLOGACAO = [
        "https://hom1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
    ]
    
    ENDPOINTS_PRODUCAO = [
        "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
    ]
    
    # Namespaces
    NS_NFE = "http://www.portalfiscal.inf.br/nfe"
    NS_SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"  # SOAP 1.1
    NS_DIST_DFE = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe"
    
    # SOAPAction para o serviço
    SOAP_ACTION = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"
    
    # Mapa de códigos IBGE de UF
    UF_CODES = {
        "AC": "12", "AL": "27", "AP": "16", "AM": "13", "BA": "29",
        "CE": "23", "DF": "53", "ES": "32", "GO": "52", "MA": "21",
        "MT": "51", "MS": "50", "MG": "31", "PA": "15", "PB": "25",
        "PR": "41", "PE": "26", "PI": "22", "RJ": "33", "RN": "24",
        "RS": "43", "RO": "11", "RR": "14", "SC": "42", "SP": "35",
        "SE": "28", "TO": "17",
    }
    
    def __init__(
        self,
        cnpj: str,
        cert_pfx_data: bytes,
        cert_password: str,
        producao: bool = True,
        uf_code: str = None
    ):
        """
        Inicializa o cliente SEFAZ
        
        Args:
            cnpj: CNPJ da empresa (14 dígitos)
            cert_pfx_data: Dados do certificado .pfx
            cert_password: Senha do certificado
            producao: True para produção, False para homologação
            uf_code: Código IBGE da UF (ex: "52" para GO). Se None, detecta do certificado ou usa 91
        """
        self.cnpj = cnpj.replace(".", "").replace("/", "").replace("-", "")  # Apenas números
        self.producao = producao
        self.uf_code = uf_code or "91"  # 91 = Ambiente Nacional (padrão inicial)
        self.endpoints = self.ENDPOINTS_PRODUCAO if producao else self.ENDPOINTS_HOMOLOGACAO
        
        # Carrega o certificado (pode atualizar self.uf_code)
        self._load_certificate(cert_pfx_data, cert_password)
        
        logger.info(
            f"✅ Cliente SEFAZ inicializado - CNPJ: {self.cnpj}, "
            f"UF: {self.uf_code}, Ambiente: {'Produção' if producao else 'Homologação'}"
        )
    
    def _load_certificate(self, cert_pfx_data: bytes, password: str):
        """Carrega o certificado e chave privada do PFX"""
        try:
            self.private_key, self.certificate, additional_certs = pkcs12.load_key_and_certificates(
                cert_pfx_data,
                password.encode('utf-8'),
                backend=default_backend()
            )
            
            # Extrai informações do certificado para log
            subject = self.certificate.subject
            
            # Tenta detectar UF do certificado se ainda não foi especificado manualmente
            if self.uf_code == "91":
                for attr in subject:
                    if attr.oid._name in ['stateOrProvinceName', 'ST']:
                        uf_name = str(attr.value).upper()
                        if uf_name in self.UF_CODES:
                            self.uf_code = self.UF_CODES[uf_name]
                            logger.info(f"🔍 UF detectado do certificado: {uf_name} = {self.uf_code}")
                        break
            
            logger.info(
                f"✅ Certificado carregado - Subject: {subject.rfc4514_string()[:80]}..., "
                f"Validade: {self.certificate.not_valid_after}"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar certificado: {e}")
            raise ValueError(f"Certificado inválido: {e}")
    
    def _get_ssl_context(self) -> Tuple[str, str]:
        """
        Cria arquivos temporários PEM do certificado e chave
        
        Returns:
            Tupla (cert_file_path, key_file_path)
        """
        # Cria arquivo temporário para o certificado
        cert_pem = self.certificate.public_bytes(Encoding.PEM)
        cert_fd, cert_path = tempfile.mkstemp(suffix='.pem', prefix='sefaz_cert_')
        os.write(cert_fd, cert_pem)
        os.close(cert_fd)
        
        # Cria arquivo temporário para a chave privada
        key_pem = self.private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=NoEncryption()
        )
        key_fd, key_path = tempfile.mkstemp(suffix='.pem', prefix='sefaz_key_')
        os.write(key_fd, key_pem)
        os.close(key_fd)
        
        return cert_path, key_path

    def _build_soap_envelope(self, dist_dfe_xml: str) -> str:
        """
        Constrói o envelope SOAP 1.1 (sem CDATA - enviando XML direto)

        Args:
            dist_dfe_xml: XML do distDFeInt

        Returns:
            Envelope SOAP completo
        """
        # SOAP 1.1 - envelope em uma linha, sem CDATA
        # O XML é inserido diretamente no nfeDadosMsg
        envelope = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:nfed="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">'
            '<soapenv:Header/>'
            '<soapenv:Body>'
            '<nfed:nfeDistDFeInteresse>'
            f'<nfed:nfeDadosMsg>{dist_dfe_xml}</nfed:nfeDadosMsg>'
            '</nfed:nfeDistDFeInteresse>'
            '</soapenv:Body>'
            '</soapenv:Envelope>'
        )

        return envelope

    def _build_dist_dfe_xml(
        self,
        tipo_consulta: str = "ultNSU",
        valor: str = "0"
    ) -> str:
        """
        Constrói o XML de requisição para NFeDistribuicaoDFe
        
        Args:
            tipo_consulta: ultNSU, NSU, chNFe
            valor: Valor do NSU ou chave
            
        Returns:
            XML string limpo (sem declaração XML, será inserido em CDATA)
        """
        # Garante que ultNSU/NSU tem 15 dígitos
        if tipo_consulta in ["ultNSU", "NSU"]:
            valor = valor.zfill(15)
        
        tpAmb = "1" if self.producao else "2"
        
        # Gera XML como string pura - SEM quebras de linha dentro das tags
        # Formato exato esperado pela SEFAZ
        if tipo_consulta == "ultNSU":
            xml = f'<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00"><tpAmb>{tpAmb}</tpAmb><cUFAutor>{self.uf_code}</cUFAutor><CNPJ>{self.cnpj}</CNPJ><distNSU><ultNSU>{valor}</ultNSU></distNSU></distDFeInt>'
        elif tipo_consulta == "NSU":
            xml = f'<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00"><tpAmb>{tpAmb}</tpAmb><cUFAutor>{self.uf_code}</cUFAutor><CNPJ>{self.cnpj}</CNPJ><consNSU><NSU>{valor}</NSU></consNSU></distDFeInt>'
        elif tipo_consulta == "chNFe":
            xml = f'<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.00"><tpAmb>{tpAmb}</tpAmb><cUFAutor>{self.uf_code}</cUFAutor><CNPJ>{self.cnpj}</CNPJ><consChNFe><chNFe>{valor}</chNFe></consChNFe></distDFeInt>'
        else:
            raise ValueError(f"Tipo de consulta inválido: {tipo_consulta}")
        
        return xml
    
    async def _send_soap_request(
        self,
        soap_envelope: str,
        endpoint_url: str,
        timeout: int = 60
    ) -> str:
        """
        Envia requisição SOAP com certificado A1
        
        Args:
            soap_envelope: Envelope SOAP completo
            endpoint_url: URL do endpoint
            timeout: Timeout em segundos
            
        Returns:
            Resposta XML da SEFAZ
        """
        cert_path = None
        key_path = None
        
        try:
            # Cria arquivos temporários PEM
            cert_path, key_path = self._get_ssl_context()
            
            # Headers SOAP 1.1 (SOAPAction separado)
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": f'"{self.SOAP_ACTION}"',
                "User-Agent": "Mozilla/5.0 (compatible; SEFAZ-Client/1.0)",
            }
            
            logger.info(f"📤 Enviando requisição SOAP para: {endpoint_url}")
            print(f"🌐 ENDPOINT: {endpoint_url}")
            print(f"🔧 Ambiente: {'PRODUÇÃO' if self.producao else 'HOMOLOGAÇÃO'}")
            logger.debug(f"Headers: {headers}")
            logger.debug(f"SOAP Envelope: {soap_envelope[:800]}...")
            
            # Envia requisição com certificado mTLS
            async with httpx.AsyncClient(
                cert=(cert_path, key_path),
                verify=certifi.where(),  # Usa certificados confiáveis do certifi
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                response = await client.post(
                    endpoint_url,
                    content=soap_envelope.encode('utf-8'),
                    headers=headers,
                )
                
                logger.info(f"📥 Status HTTP: {response.status_code}")
                print(f"\n📥 RESPOSTA SEFAZ (HTTP {response.status_code}):")
                print(f"{response.text[:1500]}\n")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                # Só trata como erro HTTP se não for 200
                if response.status_code != 200:
                    logger.error(
                        f"❌ Erro HTTP {response.status_code} da SEFAZ\n"
                        f"URL: {endpoint_url}\n"
                        f"Corpo: {response.text[:1000]}"
                    )
                    raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")
                
                # HTTP 200 - retorna resposta para parse do cStat
                logger.info(f"✅ HTTP 200 recebido, parseando resposta SOAP...")
                return response.text
                
        finally:
            # Remove arquivos temporários
            if cert_path and os.path.exists(cert_path):
                os.unlink(cert_path)
            if key_path and os.path.exists(key_path):
                os.unlink(key_path)
    
    async def consultar_distribuicao(
        self,
        ultimo_nsu: str = "0",
        max_docs: int = 50
    ) -> Dict[str, Any]:
        """
        Consulta distribuição por último NSU (consulta incremental)
        
        Args:
            ultimo_nsu: Último NSU processado (0 = inicial)
            max_docs: Máximo de documentos a retornar
            
        Returns:
            Dict com status, maxNSU, ultNSU, documentos
        """
        # Constrói o XML de requisição
        dist_dfe_xml = self._build_dist_dfe_xml(
            tipo_consulta="ultNSU",
            valor=ultimo_nsu
        )
        
        # Constrói envelope SOAP
        soap_envelope = self._build_soap_envelope(dist_dfe_xml)
        
        # Log de debug (CNPJ mascarado)
        cnpj_masked = self.cnpj[:4] + "****" + self.cnpj[-4:] if len(self.cnpj) >= 8 else "****"
        logger.info(
            f"🔍 Consultando DF-e - "
            f"CNPJ: {cnpj_masked}, UF: {self.uf_code}, "
            f"tpAmb: {'1-Prod' if self.producao else '2-Hom'}, "
            f"ultNSU: {ultimo_nsu.zfill(15)}"
        )
        
        # Log do XML completo para debug
        print(f"\n{'='*80}")
        print(f"📝 CNPJ: {self.cnpj} | UF: {self.uf_code}")
        print(f"📝 distDFeInt XML:\n{dist_dfe_xml}")
        print(f"\n📦 SOAP Envelope Completo:\n{soap_envelope}")
        print(f"{'='*80}\n")
        logger.info(f"📝 distDFeInt XML:\n{dist_dfe_xml}")
        logger.info(f"📝 SOAP Envelope (500 chars):\n{soap_envelope[:500]}...")
        
        # Tenta endpoints com fallback
        last_error = None
        for i, endpoint in enumerate(self.endpoints, 1):
            try:
                logger.info(f"Tentativa {i}/{len(self.endpoints)}: {endpoint}")
                response_xml = await self._send_soap_request(soap_envelope, endpoint)
                return self._parse_response(response_xml)
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Falha no endpoint {endpoint}: {e}")
                if i < len(self.endpoints):
                    logger.info(f"Tentando próximo endpoint...")
                continue
        
        # Se chegou aqui, todos os endpoints falharam
        logger.error(f"❌ Todos os endpoints falharam. Último erro: {last_error}")
        raise last_error
    
    async def consultar_por_chave(self, chave: str) -> Dict[str, Any]:
        """
        Consulta distribuição por chave de acesso
        
        Args:
            chave: Chave de acesso da NF-e (44 dígitos)
            
        Returns:
            Dict com status e documentos
        """
        dist_dfe_xml = self._build_dist_dfe_xml(
            tipo_consulta="chNFe",
            valor=chave
        )
        
        soap_envelope = self._build_soap_envelope(dist_dfe_xml)
        
        logger.info(f"🔍 Consultando NF-e por chave: {chave}")
        
        # Tenta endpoints com fallback
        last_error = None
        for endpoint in self.endpoints:
            try:
                response_xml = await self._send_soap_request(soap_envelope, endpoint)
                return self._parse_response(response_xml)
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Falha no endpoint {endpoint}: {e}")
                continue
        
        raise last_error
    
    def _parse_response(self, response_xml: str) -> Dict[str, Any]:
        """
        Parse da resposta XML do serviço SEFAZ
        
        Returns:
            {
                'status': int,
                'motivo': str,
                'max_nsu': str,
                'ult_nsu': str,
                'documentos': List[DFeDocument]
            }
        """
        try:
            logger.debug(f"Parsing response (500 chars): {response_xml[:500]}")
            
            # Namespaces usados na resposta SEFAZ
            NS = {
                "soap": "http://schemas.xmlsoap.org/soap/envelope/",
                "soap12": "http://www.w3.org/2003/05/soap-envelope",
                "wsdl": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe",
                "nfe": "http://www.portalfiscal.inf.br/nfe",
            }
            
            # Parse do XML
            root = ET.fromstring(response_xml)
            
            # Busca retDistDFeInt com namespace nfe
            ret = root.find(".//nfe:retDistDFeInt", NS)
            
            # Fallback: buscar sem namespace (iteração)
            if ret is None:
                for elem in root.iter():
                    if elem.tag.endswith('retDistDFeInt'):
                        ret = elem
                        break
            
            if ret is None:
                logger.error(f"❌ Não encontrou retDistDFeInt no XML:\n{response_xml[:1000]}")
                return {
                    'status': 0,
                    'motivo': 'Resposta inválida: retDistDFeInt não encontrado',
                    'max_nsu': '0',
                    'ult_nsu': '0',
                    'documentos': []
                }
            
            # Extrai campos usando findtext com namespace nfe
            # Primeiro tenta com namespace, depois sem
            def get_text(elem, tag, default=""):
                # Tenta com namespace nfe
                val = elem.findtext(f"nfe:{tag}", namespaces=NS)
                if val is not None:
                    return val
                # Tenta sem namespace (busca direta)
                child = elem.find(f".//{{{NS['nfe']}}}{tag}")
                if child is not None and child.text:
                    return child.text
                # Busca por iteração
                for e in elem.iter():
                    if e.tag.endswith(tag) and e.text:
                        return e.text
                return default
            
            status_text = get_text(ret, "cStat", "0")
            status = int(status_text) if status_text.isdigit() else 0
            motivo = get_text(ret, "xMotivo", "Sem motivo")
            max_nsu = get_text(ret, "maxNSU", "0")
            ult_nsu = get_text(ret, "ultNSU", "0")
            
            # Log do resultado
            logger.info(f"📨 SEFAZ Response - cStat: {status}, xMotivo: {motivo}")
            logger.info(f"📊 NSUs - ultNSU: {ult_nsu}, maxNSU: {max_nsu}")
            
            if status == 137:
                logger.info(f"✅ cStat 137: Nenhum documento novo localizado")
            elif status == 138:
                logger.info(f"✅ cStat 138: Documento(s) localizado(s)")
            elif status == 243:
                print(f"\n{'='*80}")
                print(f"❌ ERRO cStat 243 - XML mal formado")
                print(f"Verificar o XML enviado acima")
                print(f"{'='*80}\n")
                logger.error(f"❌ cStat 243: XML mal formado - verificar estrutura do request")
            elif status not in [137, 138]:
                logger.warning(f"⚠️ cStat {status}: {motivo}")
            
            # Extrai documentos (busca em loteDistDFeInt ou diretamente)
            documentos = []
            
            # Tenta encontrar docZip em diferentes caminhos
            doc_zips = []
            for elem in ret.iter():
                if elem.tag.endswith('docZip'):
                    doc_zips.append(elem)
            
            for doc_zip in doc_zips:
                nsu = doc_zip.get('NSU', '')
                schema = doc_zip.get('schema', '')
                
                # Decodifica o conteúdo base64 e descompacta GZIP
                xml_b64 = doc_zip.text
                if xml_b64:
                    try:
                        # Remove whitespace e decodifica Base64
                        xml_b64_clean = xml_b64.strip()
                        compressed_data = base64.b64decode(xml_b64_clean)
                        
                        # Descompacta GZIP
                        xml_content = gzip.decompress(compressed_data).decode('utf-8')
                        
                        # Extrai a chave do XML
                        chave = self._extract_chave_from_xml(xml_content)
                        
                        tipo_documento = self._identify_document_type(schema, xml_content)
                        
                        documentos.append(DFeDocument(
                            nsu=nsu,
                            schema=schema,
                            chave=chave,
                            tipo_documento=tipo_documento,
                            xml_content=xml_content
                        ))
                        
                        print(f"\n✅ Documento descompactado!")
                        print(f"   NSU: {nsu}")
                        print(f"   Schema: {schema}")  
                        print(f"   Tipo: {tipo_documento}")
                        print(f"   Chave: {chave}")
                        print(f"   XML (primeiros 300 chars): {xml_content[:300]}\n")
                        
                    except Exception as e:
                        print(f"\n❌ ERRO ao decodificar NSU {nsu}: {e}\n")
                        logger.error(f"❌ Erro ao decodificar documento NSU {nsu}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
            
            logger.info(
                f"✅ Resposta SEFAZ - Status: {status} ({motivo}), "
                f"Docs: {len(documentos)}, maxNSU: {max_nsu}, ultNSU: {ult_nsu}"
            )
            
            return {
                'status': status,
                'motivo': motivo,
                'max_nsu': max_nsu,
                'ult_nsu': ult_nsu,
                'documentos': documentos
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao fazer parse da resposta: {e}")
            logger.debug(f"XML completo: {response_xml}")
            raise
    
    def _extract_chave_from_xml(self, xml_content: str) -> str:
        """Extrai a chave de acesso do XML"""
        try:
            root = ET.fromstring(xml_content)
            # Procura por chave em diferentes lugares possíveis
            
            # Busca com namespace
            chave_elem = root.find('.//{http://www.portalfiscal.inf.br/nfe}chNFe')
            if chave_elem is not None and chave_elem.text:
                return chave_elem.text
            
            # Busca sem namespace
            chave_elem = root.find('.//chNFe')
            if chave_elem is not None and chave_elem.text:
                return chave_elem.text
            
            # Tenta em infNFe@Id
            for elem in root.iter():
                if 'infNFe' in elem.tag:
                    id_attr = elem.get('Id', '')
                    if id_attr.startswith('NFe'):
                        return id_attr[3:]
            
            return ""
        except:
            return ""
    
    def _identify_document_type(self, schema: str, xml_content: str) -> str:
        """Identifica o tipo de documento baseado no schema"""
        if 'resNFe' in schema:
            return 'Resumo NF-e'
        elif 'procNFe' in schema:
            return 'NF-e Completa'
        elif 'resEvento' in schema or 'procEvento' in schema:
            return 'Evento'
        elif 'procCancNFe' in schema:
            return 'Cancelamento'
        else:
            return 'Desconhecido'
