#!/usr/bin/env python
"""
Client script to demonstrate using the XML processing API
"""
import os
import sys
import json
import base64
import argparse
import requests

# Default API settings
API_URL = "https://validcfdi-api-be42092ab7e2.herokuapp.com"
API_TOKEN = "c822cf5ee82316013d21d912d95c5a770f86bd4ed278a8a33e729609e387efa4"

def setup_argparse():
    """Set up command line argument parsing"""
    parser = argparse.ArgumentParser(description='Process CFDI XML files using the ValidCFDI API')
    parser.add_argument('--file', '-f', type=str, required=True, help='Path to the XML file to process')
    parser.add_argument('--base64', '-b', action='store_true', help='Send XML as base64 encoded')
    parser.add_argument('--extract-only', '-e', action='store_true', help='Only extract data without verification')
    parser.add_argument('--url', '-u', type=str, default=API_URL, help=f'API URL (default: {API_URL})')
    parser.add_argument('--token', '-t', type=str, default=API_TOKEN, help='API token')
    parser.add_argument('--output', '-o', type=str, help='Output file for JSON response')
    parser.add_argument('--verbose', '-v', action='store_true', help='Display verbose output')
    
    return parser.parse_args()

def read_xml_file(file_path):
    """Read XML file and return its content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

def process_xml(xml_content, args):
    """Process XML using the API"""
    headers = {
        "Authorization": f"Bearer {args.token}",
        "Content-Type": "application/json"
    }
    
    # Prepare request data
    xml_data = xml_content
    if args.base64:
        xml_data = base64.b64encode(xml_content.encode('utf-8')).decode('utf-8')
    
    request_data = {
        "xml_content": xml_data,
        "is_base64": args.base64
    }
    
    # Determine endpoint
    endpoint = "/xml/extract-only" if args.extract_only else "/xml/process"
    url = f"{args.url}{endpoint}"
    
    if args.verbose:
        print(f"Sending request to {url}")
        if args.base64:
            print("XML content is base64 encoded")
        else:
            print("XML content is being sent as plain text")
    
    # Send request
    try:
        response = requests.post(url, headers=headers, json=request_data)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Error communicating with API: {e}")
        sys.exit(1)

def display_results(results, is_extract_only):
    """Display processing results"""
    if is_extract_only:
        # Extract-only results
        print("\n===== CFDI XML Data =====")
        print(f"Version: {results.get('version', 'N/A')}")
        print(f"UUID: {results.get('uuid', 'N/A')}")
        print(f"Total: {results.get('total', 'N/A')}")
        print(f"Fecha: {results.get('fecha', 'N/A')}")
        print(f"Serie-Folio: {results.get('serie', 'N/A')}-{results.get('folio', 'N/A')}")
        
        # Emisor details
        emisor = results.get('emisor', {})
        print("\n----- Emisor -----")
        print(f"RFC: {emisor.get('rfc', 'N/A')}")
        print(f"Nombre: {emisor.get('nombre', 'N/A')}")
        
        # Receptor details
        receptor = results.get('receptor', {})
        print("\n----- Receptor -----")
        print(f"RFC: {receptor.get('rfc', 'N/A')}")
        print(f"Nombre: {receptor.get('nombre', 'N/A')}")
        
        # Conceptos summary
        conceptos = results.get('conceptos', [])
        print(f"\n----- Conceptos ({len(conceptos)}) -----")
        for i, concepto in enumerate(conceptos, 1):
            print(f"{i}. {concepto.get('descripcion', 'N/A')} - ${concepto.get('importe', 'N/A')}")
    else:
        # Process results with verification
        verification_data = results.get("verification_data", {})
        parsed_data = results.get("parsed_data", {})
        sat_verification = results.get("sat_verification", {})
        
        # Basic CFDI info
        print("\n===== CFDI Information =====")
        print(f"UUID: {verification_data.get('uuid', 'N/A')}")
        print(f"Emisor RFC: {verification_data.get('emisor_rfc', 'N/A')}")
        print(f"Receptor RFC: {verification_data.get('receptor_rfc', 'N/A')}")
        print(f"Total: ${verification_data.get('total', 'N/A')}")
        
        # SAT Verification results
        print("\n===== SAT Verification =====")
        print(f"Estado: {sat_verification.get('estado', 'N/A')}")
        print(f"Es Cancelable: {sat_verification.get('es_cancelable', 'N/A')}")
        print(f"Estatus Cancelación: {sat_verification.get('estatus_cancelacion', 'N/A')}")
        
        # EFOS information
        efos_emisor = sat_verification.get('efos_emisor')
        efos_receptor = sat_verification.get('efos_receptor')
        
        if efos_emisor:
            print("\n⚠️ EMISOR is in EFOS list (blacklisted company):")
            print(f"   Situación: {efos_emisor.get('situacion_contribuyente', 'N/A')}")
            print(f"   Publicación DOF: {efos_emisor.get('fecha_publicacion_dof', 'N/A')}")
        
        if efos_receptor:
            print("\n⚠️ RECEPTOR is in EFOS list (blacklisted company):")
            print(f"   Situación: {efos_receptor.get('situacion_contribuyente', 'N/A')}")
            print(f"   Publicación DOF: {efos_receptor.get('fecha_publicacion_dof', 'N/A')}")
        
        if not efos_emisor and not efos_receptor:
            print("\n✅ Neither Emisor nor Receptor are in the EFOS list.")

def main():
    """Main function"""
    args = setup_argparse()
    
    # Read XML file
    xml_content = read_xml_file(args.file)
    
    # Process XML
    results = process_xml(xml_content, args)
    
    # Display results
    display_results(results, args.extract_only)
    
    # Save results to file if specified
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to {args.output}")
        except Exception as e:
            print(f"Error saving results to file: {e}")

if __name__ == "__main__":
    main() 