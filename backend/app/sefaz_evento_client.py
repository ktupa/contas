"""
Cliente SOAP para recepção de eventos (Manifestação do Destinatário)
"""
import logging
import os
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

import httpx
import certifi
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography import x509
from lxml import etree
from signxml import XMLSigner, methods

logger = logging.getLogger(__name__)


class SefazEventoClient:
    """Cliente para Recepção de Evento (Manifestação)"""

    # Mapeamento de UF para endpoints de produção (Recepcao Evento 4.00)
    ENDPOINTS_UF_PRODUCAO = {
        "AC": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "AL": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "AM": "https://nfe.sefaz.am.gov.br/services2/services/RecepcaoEvento4",
        "AP": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "BA": "https://nfe.sefaz.ba.gov.br/webservices/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
        "CE": "https://nfe.sefaz.ce.gov.br/nfe4/services/NFeRecepcaoEvento4",
        "DF": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "ES": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "GO": "https://nfe.sefaz.go.gov.br/nfe/services/NFeRecepcaoEvento4",
        "MA": "https://nfe.sefaz.ma.gov.br/wsdl/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
        "MG": "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeRecepcaoEvento4",
        "MS": "https://nfe.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4",
        "MT": "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NFeRecepcaoEvento4",
        "PA": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "PB": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "PE": "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeRecepcaoEvento4",
        "PI": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "PR": "https://nfe.sefa.pr.gov.br/nfe/NFeRecepcaoEvento4",
        "RJ": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "RN": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "RO": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "RR": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "RS": "https://nfe.sefazrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "SC": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "SE": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "SP": "https://nfe.fazenda.sp.gov.br/ws/recepcaoevento4.asmx",
        "TO": "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
    }

    # Endpoints de homologação (SVRS para maioria das UFs)
    ENDPOINTS_UF_HOMOLOGACAO = {
        "AC": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "AL": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "AM": "https://homnfe.sefaz.am.gov.br/services2/services/RecepcaoEvento4",
        "AP": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "BA": "https://hnfe.sefaz.ba.gov.br/webservices/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
        "CE": "https://nfeh.sefaz.ce.gov.br/nfe4/services/NFeRecepcaoEvento4",
        "DF": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "ES": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "GO": "https://homolog.sefaz.go.gov.br/nfe/services/NFeRecepcaoEvento4",
        "MA": "https://hom.sefazvirtual.fazenda.gov.br/NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx",
        "MG": "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeRecepcaoEvento4",
        "MS": "https://hom.nfe.sefaz.ms.gov.br/ws/NFeRecepcaoEvento4",
        "MT": "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NFeRecepcaoEvento4",
        "PA": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "PB": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "PE": "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeRecepcaoEvento4",
        "PI": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "PR": "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeRecepcaoEvento4",
        "RJ": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "RN": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "RO": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "RR": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "RS": "https://nfe-homologacao.sefazrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "SC": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "SE": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
        "SP": "https://homologacao.nfe.fazenda.sp.gov.br/ws/recepcaoevento4.asmx",
        "TO": "https://nfe-homologacao.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx",
    }

    SOAP_ACTION = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4/nfeRecepcaoEvento4"
    NS_NFE = "http://www.portalfiscal.inf.br/nfe"

    def __init__(self, cnpj: str, cert_pfx_data: bytes, cert_password: str, producao: bool = True, uf: Optional[str] = None):
        self.cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')
        self.producao = producao
        self.uf = uf or "GO"  # Default para Goiás
        
        # Mapeamento de UF para código IBGE
        uf_to_code = {
            "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
            "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27", "SE": "28", "BA": "29",
            "MG": "31", "ES": "32", "RJ": "33", "SP": "35",
            "PR": "41", "SC": "42", "RS": "43",
            "MS": "50", "MT": "51", "GO": "52", "DF": "53",
        }
        self.uf_code = uf_to_code.get(self.uf, "52")  # Default 52 = GO
        
        # Seleciona endpoint baseado na UF
        endpoints_map = self.ENDPOINTS_UF_PRODUCAO if producao else self.ENDPOINTS_UF_HOMOLOGACAO
        endpoint = endpoints_map.get(self.uf)
        if not endpoint:
            logger.warning(f"Endpoint não encontrado para UF {self.uf}, usando SVRS")
            endpoint = "https://nfe.svrs.rs.gov.br/ws/recepcaoevento/recepcaoevento4.asmx"
        
        self.endpoints = [endpoint]

        self._load_certificate(cert_pfx_data, cert_password)

    def _load_certificate(self, cert_pfx_data: bytes, password: str):
        self.private_key, self.certificate, _ = pkcs12.load_key_and_certificates(
            cert_pfx_data,
            password.encode("utf-8"),
            backend=default_backend()
        )
        subject = self.certificate.subject
        for attr in subject:
            if attr.oid._name in ['stateOrProvinceName', 'ST']:
                uf_name = str(attr.value).upper()
                break
        self.private_key_pem = self.private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=NoEncryption(),
        )
        self.cert_pem = self.certificate.public_bytes(Encoding.PEM)

    def _build_event_xml(self, chave: str, tp_evento: str = "210210", n_seq_evento: int = 1, x_just: Optional[str] = None) -> bytes:
        ns = self.NS_NFE
        env = etree.Element("{%s}envEvento" % ns, nsmap={None: ns}, versao="1.00")
        etree.SubElement(env, "idLote").text = str(n_seq_evento)  # Simplificado, sem zeros à esquerda

        evento = etree.SubElement(env, "evento", versao="1.00")
        inf = etree.SubElement(evento, "infEvento", Id=f"ID{tp_evento}{chave}{str(n_seq_evento).zfill(2)}")
        etree.SubElement(inf, "cOrgao").text = self.uf_code
        etree.SubElement(inf, "tpAmb").text = "1" if self.producao else "2"
        etree.SubElement(inf, "CNPJ").text = self.cnpj
        etree.SubElement(inf, "chNFe").text = chave
        # dhEvento no horário de Brasília (UTC - 3 horas)
        brasilia_tz = timezone(timedelta(hours=-3))
        dh_brasilia = datetime.now(brasilia_tz)
        # Formato: AAAA-MM-DDTHH:MM:SS-03:00
        etree.SubElement(inf, "dhEvento").text = dh_brasilia.strftime("%Y-%m-%dT%H:%M:%S-03:00")
        etree.SubElement(inf, "tpEvento").text = tp_evento
        etree.SubElement(inf, "nSeqEvento").text = str(n_seq_evento)
        etree.SubElement(inf, "verEvento").text = "1.00"

        # detEvento para manifestação - precisa ter estrutura específica
        det = etree.SubElement(inf, "detEvento", versao="1.00")
        
        # Para eventos de manifestação, descEvento vai direto (sem namespace adicional)
        desc_map = {
            "210210": "Ciencia da Operacao",
            "210200": "Confirmacao da Operacao", 
            "210220": "Desconhecimento da Operacao",
            "210240": "Operacao nao Realizada",
        }
        etree.SubElement(det, "descEvento").text = desc_map.get(tp_evento, "Ciencia da Operacao")
        
        # xJust é obrigatório para eventos 210220 e 210240
        if tp_evento in ["210220", "210240"] and x_just:
            etree.SubElement(det, "xJust").text = x_just

        signer = XMLSigner(
            method=methods.enveloped,
            digest_algorithm="sha256",
            signature_algorithm="rsa-sha256",
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
        )
        signed = signer.sign(
            inf,
            key=self.private_key_pem,
            cert=self.cert_pem,
            reference_uri=f"#{inf.get('Id')}",
        )
        # Replace unsigned inf with signed version
        evento.remove(inf)
        evento.append(signed)

        return etree.tostring(env, encoding="utf-8", xml_declaration=False)

    def _build_soap_envelope(self, xml_payload: bytes) -> str:
        # Remove any existing XML declaration from payload
        payload_str = xml_payload.decode('utf-8')
        if payload_str.startswith('<?xml'):
            payload_str = payload_str.split('?>', 1)[1].strip()
        
        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope" '
            'xmlns:nfed="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">'
            '<soap12:Header/>'
            '<soap12:Body>'
            '<nfed:nfeDadosMsg>'
            f"{payload_str}"
            '</nfed:nfeDadosMsg>'
            '</soap12:Body>'
            '</soap12:Envelope>'
        )

    async def _send(self, soap_envelope: str, endpoint_url: str, timeout: int = 60) -> str:
        cert_path = key_path = None
        try:
            cert_fd, cert_path = tempfile.mkstemp(suffix='.pem', prefix='sefaz_evt_cert_')
            os.write(cert_fd, self.cert_pem)
            os.close(cert_fd)

            key_fd, key_path = tempfile.mkstemp(suffix='.pem', prefix='sefaz_evt_key_')
            os.write(key_fd, self.private_key_pem)
            os.close(key_fd)

            headers = {
                "Content-Type": "application/soap+xml; charset=utf-8; action=\"http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4/nfeRecepcaoEvento\"",
            }

            async with httpx.AsyncClient(
                cert=(cert_path, key_path),
                verify=False,  # Desabilita verificação SSL (temporário para teste)
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                response = await client.post(endpoint_url, content=soap_envelope.encode('utf-8'), headers=headers)
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")
                return response.text
        finally:
            if cert_path and os.path.exists(cert_path):
                os.unlink(cert_path)
            if key_path and os.path.exists(key_path):
                os.unlink(key_path)

    def _parse_response(self, response_xml: str) -> Dict[str, Any]:
        NS = {
            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
            "nfe": self.NS_NFE,
        }
        root = etree.fromstring(response_xml.encode('utf-8'))
        ret_env = None
        for elem in root.iter():
            if elem.tag.endswith('retEnvEvento'):
                ret_env = elem
                break
        if ret_env is None:
            return {"status": 0, "motivo": "retEnvEvento não encontrado"}

        def find_text(elem, tag):
            # search with namespace or suffix
            res = elem.find(f"nfe:{tag}", namespaces=NS)
            if res is not None and res.text:
                return res.text
            for e in elem.iter():
                if e.tag.endswith(tag) and e.text:
                    return e.text
            return ""

        cstat = find_text(ret_env, "cStat")
        motivo = find_text(ret_env, "xMotivo")
        ret_evento = None
        for e in ret_env.iter():
            if e.tag.endswith('retEvento'):
                ret_evento = e
                break
        evento_info = {}
        if ret_evento is not None:
            inf = None
            for e in ret_evento.iter():
                if e.tag.endswith('infEvento'):
                    inf = e
                    break
            if inf is not None:
                evento_info = {
                    "chNFe": find_text(inf, "chNFe"),
                    "cStat": find_text(inf, "cStat"),
                    "xMotivo": find_text(inf, "xMotivo"),
                    "nProt": find_text(inf, "nProt"),
                }
        return {
            "status": int(cstat) if cstat.isdigit() else 0,
            "motivo": motivo,
            "evento": evento_info,
        }

    async def manifestar(self, chave: str, tp_evento: str = "210210", n_seq_evento: int = 1, x_just: Optional[str] = None) -> Dict[str, Any]:
        xml_payload = self._build_event_xml(chave, tp_evento=tp_evento, n_seq_evento=n_seq_evento, x_just=x_just)
        soap_envelope = self._build_soap_envelope(xml_payload)
        
        print(f"📤 [EVENTO XML] Payload:")
        print(xml_payload.decode('utf-8')[:2000])
        print(f"📤 [SOAP] Envelope:")
        print(soap_envelope[:2000])

        last_error = None
        for endpoint in self.endpoints:
            try:
                response_xml = await self._send(soap_envelope, endpoint)
                print(f"📥 [RESPOSTA SEFAZ COMPLETA]:")
                print(response_xml)
                parsed = self._parse_response(response_xml)
                logger.info(
                    "manifestacao_response",
                    extra={"chave": chave, "tp_evento": tp_evento, "status": parsed.get("status"), "motivo": parsed.get("motivo"), "evento": parsed.get("evento")},
                )
                return parsed
            except Exception as e:
                last_error = e
                logger.warning(f"Manifestacao falhou no endpoint {endpoint}: {e}")
                continue
        raise last_error if last_error else Exception("Falha na manifestação")
