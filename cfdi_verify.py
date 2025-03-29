import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom

def consult_cfdi(uuid, emisor_rfc, receptor_rfc, total):
    # Endpoint URL for the SAT CFDI consultation service
    url = "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc"
    
    # Headers for the SOAP request
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
    
    # Send the SOAP request
    try:
        response = requests.post(url, headers=headers, data=soap_envelope.encode('utf-8'), timeout=10)
        
        # Print status code and response content
        print(f"Status Code: {response.status_code}")
        
        # Parse and pretty print the XML response
        if response.status_code == 200:
            # Pretty print the response for readability
            pretty_xml = minidom.parseString(response.content).toprettyxml()
            print("Response XML:")
            print(pretty_xml)
            
            # Extract and display the key information
            try:
                # Parse the XML manually since namespaces can be complex in SOAP responses
                root = ET.fromstring(response.content)
                
                # Find direct paths by checking the XML structure
                # Based on the printed XML, extract elements directly
                # Find all elements with 'a:' prefix in their tag
                a_elements = []
                for elem in root.findall(".//*"):
                    if '}' in elem.tag:  # Indicates a namespaced element
                        tag_name = elem.tag.split('}', 1)[1]  # Get tag name without namespace
                        if tag_name in ['CodigoEstatus', 'EsCancelable', 'Estado', 'EstatusCancelacion', 'ValidacionEFOS']:
                            print(f"{tag_name}: {elem.text if elem.text else 'Not found or empty'}")
                            a_elements.append((tag_name, elem.text))
                
                if not a_elements:
                    print("No CFDI data elements found. The XML structure might have changed.")
                    
            except Exception as e:
                print(f"Error extracting specific data: {e}")
        else:
            print(f"Error Response Content: {response.text}")
            
    except Exception as e:
        print(f"Error during request: {e}")

# The data from your CFDI XML
uuid = "6128396f-c09b-4ec6-8699-43c5f7e3b230"
emisor_rfc = "CDZ050722LA9"
receptor_rfc = "XIN06112344A"
total = "12000.00"

# Send the request
consult_cfdi(uuid, emisor_rfc, receptor_rfc, total)