"""
CFDI XML Parser Utility

This module provides functions to parse CFDI XML files and extract relevant information.
"""
import xml.etree.ElementTree as ET
import base64
import re
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# XML namespaces used in CFDI documents
NAMESPACES = {
    'cfdi': 'http://www.sat.gob.mx/cfd/4',
    'cfdi33': 'http://www.sat.gob.mx/cfd/3',
    'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
    'pago20': 'http://www.sat.gob.mx/Pagos20',
    'pago10': 'http://www.sat.gob.mx/Pagos',
    'nomina12': 'http://www.sat.gob.mx/nomina12',
    'implocal': 'http://www.sat.gob.mx/implocal',
}

def register_namespaces():
    """Register XML namespaces to make xpath queries cleaner."""
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)


def parse_xml_from_string(xml_string: str) -> Optional[ET.Element]:
    """
    Parse XML string and return the root element.
    
    Args:
        xml_string: String containing XML data
        
    Returns:
        XML root element or None if parsing fails
    """
    try:
        # Register namespaces for proper xpath handling
        register_namespaces()
        
        # Parse the XML string
        return ET.fromstring(xml_string)
    except ET.ParseError as e:
        logger.error(f"Failed to parse XML: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing XML: {e}")
        return None


def parse_xml_from_base64(base64_string: str) -> Optional[ET.Element]:
    """
    Parse base64-encoded XML and return the root element.
    
    Args:
        base64_string: Base64-encoded XML data
        
    Returns:
        XML root element or None if parsing fails
    """
    try:
        # Decode base64 to string
        xml_string = base64.b64decode(base64_string).decode('utf-8')
        return parse_xml_from_string(xml_string)
    except Exception as e:
        logger.error(f"Failed to decode or parse base64 XML: {e}")
        return None


def get_cfdi_version(root: ET.Element) -> str:
    """
    Get the CFDI version from the XML root element.
    
    Args:
        root: XML root element
        
    Returns:
        CFDI version as string (e.g., "3.3", "4.0")
    """
    # Check if it's CFDI 4.0
    if root.tag.endswith('}Comprobante') and '{http://www.sat.gob.mx/cfd/4}' in root.tag:
        return root.get('Version', '4.0')
    
    # Check if it's CFDI 3.3
    if root.tag.endswith('}Comprobante') and '{http://www.sat.gob.mx/cfd/3}' in root.tag:
        return root.get('Version', '3.3')
    
    # Default for older or unknown versions
    return root.get('version', root.get('Version', 'unknown'))


def get_complementos(root: ET.Element) -> Dict[str, ET.Element]:
    """
    Extract all complementos from CFDI.
    
    Args:
        root: XML root element
        
    Returns:
        Dictionary mapping complemento type to complemento element
    """
    complementos = {}
    
    # Look for the Complemento node
    complemento_node = root.find('.//cfdi:Complemento', NAMESPACES) or root.find('.//cfdi33:Complemento', NAMESPACES)
    
    if complemento_node is None:
        return complementos
    
    # TimbreFiscalDigital
    tfd = complemento_node.find('.//tfd:TimbreFiscalDigital', NAMESPACES)
    if tfd is not None:
        complementos['TimbreFiscalDigital'] = tfd
    
    # Pagos (both versions)
    pagos20 = complemento_node.find('.//pago20:Pagos', NAMESPACES)
    if pagos20 is not None:
        complementos['Pagos20'] = pagos20
    
    pagos10 = complemento_node.find('.//pago10:Pagos', NAMESPACES)
    if pagos10 is not None:
        complementos['Pagos10'] = pagos10
    
    # Nomina
    nomina = complemento_node.find('.//nomina12:Nomina', NAMESPACES)
    if nomina is not None:
        complementos['Nomina12'] = nomina
    
    # ImpuestosLocales
    imp_local = complemento_node.find('.//implocal:ImpuestosLocales', NAMESPACES)
    if imp_local is not None:
        complementos['ImpuestosLocales'] = imp_local
    
    return complementos


def get_uuid(root: ET.Element) -> Optional[str]:
    """
    Extract UUID from CFDI's TimbreFiscalDigital complemento.
    
    Args:
        root: XML root element
        
    Returns:
        UUID as string or None if not found
    """
    complementos = get_complementos(root)
    tfd = complementos.get('TimbreFiscalDigital')
    
    if tfd is not None:
        return tfd.get('UUID')
    
    return None


def get_emisor_details(root: ET.Element) -> Dict[str, str]:
    """
    Extract emisor (issuer) details from CFDI.
    
    Args:
        root: XML root element
        
    Returns:
        Dictionary with emisor RFC and name
    """
    version = get_cfdi_version(root)
    
    if version.startswith('4'):
        emisor = root.find('.//cfdi:Emisor', NAMESPACES)
    else:
        emisor = root.find('.//cfdi33:Emisor', NAMESPACES)
    
    if emisor is None:
        return {'rfc': '', 'nombre': ''}
    
    return {
        'rfc': emisor.get('Rfc', ''),
        'nombre': emisor.get('Nombre', '')
    }


def get_receptor_details(root: ET.Element) -> Dict[str, str]:
    """
    Extract receptor (receiver) details from CFDI.
    
    Args:
        root: XML root element
        
    Returns:
        Dictionary with receptor RFC and name
    """
    version = get_cfdi_version(root)
    
    if version.startswith('4'):
        receptor = root.find('.//cfdi:Receptor', NAMESPACES)
    else:
        receptor = root.find('.//cfdi33:Receptor', NAMESPACES)
    
    if receptor is None:
        return {'rfc': '', 'nombre': ''}
    
    return {
        'rfc': receptor.get('Rfc', ''),
        'nombre': receptor.get('Nombre', '')
    }


def get_total(root: ET.Element) -> str:
    """
    Extract total amount from CFDI.
    
    Args:
        root: XML root element
        
    Returns:
        Total amount as string
    """
    return root.get('Total', '0.00')


def get_verification_data(root: ET.Element) -> Dict[str, str]:
    """
    Extract data needed for SAT verification.
    
    Args:
        root: XML root element
        
    Returns:
        Dictionary with UUID, emisor RFC, receptor RFC, and total
    """
    uuid = get_uuid(root)
    emisor = get_emisor_details(root)
    receptor = get_receptor_details(root)
    total = get_total(root)
    
    return {
        'uuid': uuid,
        'emisor_rfc': emisor['rfc'],
        'receptor_rfc': receptor['rfc'],
        'total': total
    }


def extract_cfdi_data(xml_content: str, is_base64: bool = False) -> Dict[str, Any]:
    """
    Extract all relevant data from a CFDI XML.
    
    Args:
        xml_content: XML content as string or base64-encoded string
        is_base64: Flag indicating if content is base64-encoded
        
    Returns:
        Dictionary with extracted CFDI data
    """
    if is_base64:
        root = parse_xml_from_base64(xml_content)
    else:
        root = parse_xml_from_string(xml_content)
    
    if root is None:
        return {'error': 'Failed to parse XML'}
    
    version = get_cfdi_version(root)
    complementos = get_complementos(root)
    verification_data = get_verification_data(root)
    
    emisor = get_emisor_details(root)
    receptor = get_receptor_details(root)
    
    # General CFDI data
    result = {
        'version': version,
        'fecha': root.get('Fecha', ''),
        'serie': root.get('Serie', ''),
        'folio': root.get('Folio', ''),
        'tipo_comprobante': root.get('TipoDeComprobante', ''),
        'subtotal': root.get('SubTotal', '0.00'),
        'total': verification_data['total'],
        'moneda': root.get('Moneda', 'MXN'),
        'tipo_cambio': root.get('TipoCambio', '1.0'),
        'metodo_pago': root.get('MetodoPago', ''),
        'forma_pago': root.get('FormaPago', ''),
        'regimen_fiscal': emisor.get('RegimenFiscal', ''),
        'uso_cfdi': receptor.get('UsoCFDI', ''),
        'emisor': emisor,
        'receptor': receptor,
        'uuid': verification_data['uuid'],
        'verification_data': verification_data,
        'tiene_complemento_pago': 'Pagos20' in complementos or 'Pagos10' in complementos,
        'tiene_complemento_nomina': 'Nomina12' in complementos,
        'tiene_complemento_implocal': 'ImpuestosLocales' in complementos,
    }
    
    # Extract Conceptos (line items)
    conceptos = []
    conceptos_nodes = root.findall('.//cfdi:Conceptos/cfdi:Concepto', NAMESPACES) or root.findall('.//cfdi33:Conceptos/cfdi33:Concepto', NAMESPACES)
    
    for concepto in conceptos_nodes:
        conceptos.append({
            'clave_prod_serv': concepto.get('ClaveProdServ', ''),
            'cantidad': concepto.get('Cantidad', '1'),
            'unidad': concepto.get('Unidad', ''),
            'descripcion': concepto.get('Descripcion', ''),
            'valor_unitario': concepto.get('ValorUnitario', '0.00'),
            'importe': concepto.get('Importe', '0.00'),
        })
    
    result['conceptos'] = conceptos
    
    return result


def validate_cfdi_structure(xml_content: str, is_base64: bool = False) -> Tuple[bool, str]:
    """
    Validate basic CFDI structure and required elements.
    
    Args:
        xml_content: XML content as string or base64-encoded string
        is_base64: Flag indicating if content is base64-encoded
        
    Returns:
        Tuple containing (is_valid, error_message)
    """
    if is_base64:
        root = parse_xml_from_base64(xml_content)
    else:
        root = parse_xml_from_string(xml_content)
    
    if root is None:
        return False, "Could not parse XML content"
    
    # Check if it's a CFDI document
    if not (root.tag.endswith('}Comprobante') and 
            ('{http://www.sat.gob.mx/cfd/4}' in root.tag or 
             '{http://www.sat.gob.mx/cfd/3}' in root.tag)):
        return False, "XML is not a valid CFDI document"
    
    # Check for required elements
    version = get_cfdi_version(root)
    if version == 'unknown':
        return False, "Missing CFDI version"
    
    # Check Emisor
    emisor = get_emisor_details(root)
    if not emisor['rfc']:
        return False, "Missing Emisor RFC"
    
    # Check Receptor
    receptor = get_receptor_details(root)
    if not receptor['rfc']:
        return False, "Missing Receptor RFC"
    
    # Check UUID
    uuid = get_uuid(root)
    if uuid is None:
        return False, "Missing TimbreFiscalDigital or UUID"
    
    return True, ""


def get_cfdi_type(root: ET.Element) -> str:
    """
    Determine the CFDI type (Ingreso, Egreso, Traslado, Pago, Nomina).
    
    Args:
        root: XML root element
        
    Returns:
        CFDI type as string
    """
    tipo_comprobante = root.get('TipoDeComprobante', '')
    complementos = get_complementos(root)
    
    # Complemento de Pago takes precedence
    if 'Pagos20' in complementos or 'Pagos10' in complementos:
        return 'Pago'
    
    # Complemento de Nómina
    if 'Nomina12' in complementos:
        return 'Nomina'
    
    # Regular CFDI types
    tipo_map = {
        'I': 'Ingreso',
        'E': 'Egreso',
        'T': 'Traslado',
        'P': 'Pago',
        'N': 'Nomina'
    }
    
    return tipo_map.get(tipo_comprobante, 'Desconocido') 