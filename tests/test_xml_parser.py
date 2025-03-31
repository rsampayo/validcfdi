"""
Test script for CFDI XML parser
"""
import os
import base64
import unittest
from utils.cfdi_xml_parser import (
    parse_xml_from_string,
    parse_xml_from_base64,
    get_cfdi_version,
    get_emisor_details,
    get_receptor_details,
    get_uuid,
    get_total,
    extract_cfdi_data,
    validate_cfdi_structure
)

class TestCfdiXmlParser(unittest.TestCase):
    """Test cases for CFDI XML parser utility"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sample_path_40 = os.path.join('tests', 'xml_samples', 'sample_cfdi.xml')
        self.sample_path_33 = os.path.join('tests', 'xml_samples', 'sample_cfdi33.xml')
        
        # Read sample files
        with open(self.sample_path_40, 'r', encoding='utf-8') as f:
            self.sample_xml_40 = f.read()
            
        with open(self.sample_path_33, 'r', encoding='utf-8') as f:
            self.sample_xml_33 = f.read()
            
        # Create base64 encoded versions
        self.sample_xml_40_base64 = base64.b64encode(self.sample_xml_40.encode('utf-8')).decode('utf-8')
        self.sample_xml_33_base64 = base64.b64encode(self.sample_xml_33.encode('utf-8')).decode('utf-8')
        
    def test_parse_xml_from_string(self):
        """Test parsing XML from string"""
        # CFDI 4.0
        root = parse_xml_from_string(self.sample_xml_40)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, '{http://www.sat.gob.mx/cfd/4}Comprobante')
        
        # CFDI 3.3
        root = parse_xml_from_string(self.sample_xml_33)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, '{http://www.sat.gob.mx/cfd/3}Comprobante')
        
    def test_parse_xml_from_base64(self):
        """Test parsing XML from base64 encoded string"""
        # CFDI 4.0
        root = parse_xml_from_base64(self.sample_xml_40_base64)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, '{http://www.sat.gob.mx/cfd/4}Comprobante')
        
        # CFDI 3.3
        root = parse_xml_from_base64(self.sample_xml_33_base64)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, '{http://www.sat.gob.mx/cfd/3}Comprobante')
        
    def test_get_cfdi_version(self):
        """Test getting CFDI version"""
        # CFDI 4.0
        root = parse_xml_from_string(self.sample_xml_40)
        version = get_cfdi_version(root)
        self.assertEqual(version, '4.0')
        
        # CFDI 3.3
        root = parse_xml_from_string(self.sample_xml_33)
        version = get_cfdi_version(root)
        self.assertEqual(version, '3.3')
        
    def test_get_emisor_details(self):
        """Test getting emisor details"""
        # CFDI 4.0
        root = parse_xml_from_string(self.sample_xml_40)
        emisor = get_emisor_details(root)
        self.assertEqual(emisor['rfc'], 'CDZ050722LA9')
        self.assertEqual(emisor['nombre'], 'EMPRESA DEMO SA DE CV')
        
        # CFDI 3.3
        root = parse_xml_from_string(self.sample_xml_33)
        emisor = get_emisor_details(root)
        self.assertEqual(emisor['rfc'], 'MAG041126GT8')
        self.assertEqual(emisor['nombre'], 'EMPRESA CFDI 3.3 SA DE CV')
        
    def test_get_receptor_details(self):
        """Test getting receptor details"""
        # CFDI 4.0
        root = parse_xml_from_string(self.sample_xml_40)
        receptor = get_receptor_details(root)
        self.assertEqual(receptor['rfc'], 'XIN06112344A')
        self.assertEqual(receptor['nombre'], 'CLIENTE DEMO SA DE CV')
        
        # CFDI 3.3
        root = parse_xml_from_string(self.sample_xml_33)
        receptor = get_receptor_details(root)
        self.assertEqual(receptor['rfc'], 'MALD940906KJ8')
        self.assertEqual(receptor['nombre'], 'DAVID MARTINEZ LOPEZ')
        
    def test_get_uuid(self):
        """Test getting UUID"""
        # CFDI 4.0
        root = parse_xml_from_string(self.sample_xml_40)
        uuid = get_uuid(root)
        self.assertEqual(uuid, '6128396f-c09b-4ec6-8699-43c5f7e3b230')
        
        # CFDI 3.3
        root = parse_xml_from_string(self.sample_xml_33)
        uuid = get_uuid(root)
        self.assertEqual(uuid, 'aa36c339-492c-4126-9c1a-5e4c12882486')
        
    def test_get_total(self):
        """Test getting total amount"""
        # CFDI 4.0
        root = parse_xml_from_string(self.sample_xml_40)
        total = get_total(root)
        self.assertEqual(total, '11600.00')
        
        # CFDI 3.3
        root = parse_xml_from_string(self.sample_xml_33)
        total = get_total(root)
        self.assertEqual(total, '5800.00')
        
    def test_extract_cfdi_data(self):
        """Test extracting CFDI data"""
        # CFDI 4.0
        data = extract_cfdi_data(self.sample_xml_40)
        self.assertEqual(data['version'], '4.0')
        self.assertEqual(data['uuid'], '6128396f-c09b-4ec6-8699-43c5f7e3b230')
        self.assertEqual(data['emisor']['rfc'], 'CDZ050722LA9')
        self.assertEqual(data['receptor']['rfc'], 'XIN06112344A')
        self.assertEqual(data['total'], '11600.00')
        self.assertEqual(len(data['conceptos']), 1)
        
        # CFDI 3.3
        data = extract_cfdi_data(self.sample_xml_33)
        self.assertEqual(data['version'], '3.3')
        self.assertEqual(data['uuid'], 'aa36c339-492c-4126-9c1a-5e4c12882486')
        self.assertEqual(data['emisor']['rfc'], 'MAG041126GT8')
        self.assertEqual(data['receptor']['rfc'], 'MALD940906KJ8')
        self.assertEqual(data['total'], '5800.00')
        self.assertEqual(len(data['conceptos']), 1)
        
        # Base64 encoded
        data = extract_cfdi_data(self.sample_xml_40_base64, is_base64=True)
        self.assertEqual(data['version'], '4.0')
        self.assertEqual(data['uuid'], '6128396f-c09b-4ec6-8699-43c5f7e3b230')
        
    def test_validate_cfdi_structure(self):
        """Test validating CFDI structure"""
        # Valid CFDI 4.0
        is_valid, error = validate_cfdi_structure(self.sample_xml_40)
        self.assertTrue(is_valid)
        self.assertEqual(error, '')
        
        # Valid CFDI 3.3
        is_valid, error = validate_cfdi_structure(self.sample_xml_33)
        self.assertTrue(is_valid)
        self.assertEqual(error, '')
        
        # Invalid XML
        is_valid, error = validate_cfdi_structure('<invalid>xml</invalid>')
        self.assertFalse(is_valid)
        self.assertIn('XML is not a valid CFDI document', error)
        
        # Valid base64 encoded
        is_valid, error = validate_cfdi_structure(self.sample_xml_40_base64, is_base64=True)
        self.assertTrue(is_valid)
        self.assertEqual(error, '')

if __name__ == '__main__':
    unittest.main() 