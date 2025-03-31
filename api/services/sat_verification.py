"""
SAT Verification Service

Functions for verifying CFDIs with the SAT service and checking EFOS status.
"""
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_cfdi(uuid: str, emisor_rfc: str, receptor_rfc: str, total: str) -> Dict[str, Any]:
    """
    Verify a CFDI with the SAT service
    
    Args:
        uuid: The UUID of the CFDI
        emisor_rfc: The RFC of the emisor
        receptor_rfc: The RFC of the receptor
        total: The total amount of the CFDI
        
    Returns:
        A dictionary with the verification results
    """
    # SAT verification endpoint
    url = "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc"
    
    # Headers for SOAP request
    headers = {
        'Content-Type': 'text/xml;charset=UTF-8',
        'SOAPAction': 'http://tempuri.org/IConsultaCFDIService/Consulta'
    }
    
    # SOAP envelope template
    soap_envelope = f'''
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
       <soap:Header/>
       <soap:Body>
          <tem:Consulta>
             <tem:expresionImpresa>?re={emisor_rfc}&amp;rr={receptor_rfc}&amp;tt={total}&amp;id={uuid}</tem:expresionImpresa>
          </tem:Consulta>
       </soap:Body>
    </soap:Envelope>
    '''
    
    result = {
        "estado": None,
        "es_cancelable": None, 
        "estatus_cancelacion": None,
        "codigo_estatus": None,
        "validacion_efos": None,
        "efos_emisor": None,
        "efos_receptor": None,
        "raw_response": None
    }
    
    # Send request to SAT service
    try:
        logger.info(f"Verifying CFDI: UUID={uuid}, Emisor={emisor_rfc}, Receptor={receptor_rfc}")
        response = requests.post(url, headers=headers, data=soap_envelope.encode('utf-8'), timeout=15)
        
        if response.status_code == 200:
            # Save raw response
            result["raw_response"] = minidom.parseString(response.content).toprettyxml()
            
            try:
                # Parse XML response
                root = ET.fromstring(response.content)
                
                # Extract data from namespaced XML
                for elem in root.findall(".//*"):
                    if '}' in elem.tag:
                        tag_name = elem.tag.split('}', 1)[1]
                        if tag_name == 'CodigoEstatus':
                            result["codigo_estatus"] = elem.text
                        elif tag_name == 'EsCancelable':
                            result["es_cancelable"] = elem.text
                        elif tag_name == 'Estado':
                            result["estado"] = elem.text
                        elif tag_name == 'EstatusCancelacion':
                            result["estatus_cancelacion"] = elem.text if elem.text else "No disponible"
                        elif tag_name == 'ValidacionEFOS':
                            result["validacion_efos"] = elem.text
                
                # Check EFOS status (mock for now - would actually check against EFOS database)
                # In a real implementation, this would check the database for EFOS status
                
                logger.info(f"CFDI verification successful: UUID={uuid}, Estado={result['estado']}")
            except Exception as e:
                logger.error(f"Error parsing SAT response: {str(e)}")
                raise Exception(f"Error parsing SAT response: {str(e)}")
        else:
            logger.error(f"SAT service error: {response.status_code} - {response.text}")
            raise Exception(f"SAT service error: {response.status_code} - {response.text}")
    
    except requests.RequestException as e:
        logger.error(f"Error connecting to SAT service: {str(e)}")
        raise Exception(f"Error connecting to SAT service: {str(e)}")
    
    return result 