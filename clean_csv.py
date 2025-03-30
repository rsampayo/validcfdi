#!/usr/bin/env python3
import csv
import sys
import argparse
import io
import os
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import time

class CSVCleaner:
    # Default configuration
    DEFAULT_CONFIG = {
        "header_keywords": {
            "no", "rfc", "nombre", "situación", "situacion", "fecha",
            "publicación", "publicacion", "sat", "dof", "contribuyente", 
            "oficio", "definitivo", "presunto", "desvirtuado"
        },
        "min_header_keywords_match": 3,
        "max_preamble_lines": 30,
        "chunk_size": 8192,  # Bytes to read at once when processing in chunks
        "encoding": "utf-8",
        "delimiter": ",",
        "quotechar": '"'
    }
    
    def __init__(self, config=None):
        """Initialize with custom configuration or defaults"""
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        # Performance metrics
        self.start_time = None
        self.stats = {
            "total_lines_read": 0,
            "valid_lines_written": 0,
            "skipped_lines": 0
        }
    
    def is_likely_header(self, row):
        """
        Determines if a row is likely the header based on keyword matching.
        Uses a more efficient approach with a counter to track matches.
        """
        if not row:
            return False
            
        # Skip comment lines and wrapped header notes
        if row[0].strip().startswith(('#', '!', '%', '/', '*')):
            return False
            
        # Skip rows that are part of wrapped header notes
        if len(row) > 1 and all(not cell.strip() or cell.strip() == ',' for cell in row[1:]):
            return False
            
        keywords = self.config["header_keywords"]
        min_matches = self.config["min_header_keywords_match"]
        
        # Count keyword occurrences across all fields
        found_keywords = set()
        
        for field in row:
            field_lower = field.strip().lower()
            if not field_lower:
                continue
                
            # Remove quotes and normalize Spanish characters
            field_lower = field_lower.strip('"\'')
            field_lower = field_lower.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
                
            for keyword in keywords:
                if keyword in field_lower:
                    found_keywords.add(keyword)
                    
        return len(found_keywords) >= min_matches
    
    def find_header_index(self, input_stream):
        """
        Identifies the header row in the preamble of the CSV file.
        Returns (header_index, preamble_lines, found_header_row)
        """
        max_lines = self.config["max_preamble_lines"]
        encoding = self.config["encoding"]
        
        header_index = -1
        preamble_lines = []
        header_row = None
        
        try:
            for i in range(max_lines):
                try:
                    line_bytes = input_stream.readline()
                    if not line_bytes:
                        break
                        
                    line = line_bytes.decode(encoding)
                    preamble_lines.append(line)
                    line_stripped = line.strip()
                    
                    if not line_stripped:
                        continue
                    
                    # Use CSV reader to properly handle quoted fields
                    try:
                        csv_dialect = csv.Sniffer().sniff(line_stripped) if i == 0 else None
                        if csv_dialect:
                            # If we successfully detected the dialect on the first line, use it
                            # But still respect user delimiter and quotechar if specified
                            if "delimiter" in self.config:
                                csv_dialect.delimiter = self.config["delimiter"]
                            if "quotechar" in self.config:
                                csv_dialect.quotechar = self.config["quotechar"]
                        else:
                            # Use specified dialect
                            csv_dialect = csv.excel
                            csv_dialect.delimiter = self.config["delimiter"]
                            csv_dialect.quotechar = self.config["quotechar"]
                            
                        row = next(csv.reader(io.StringIO(line_stripped), dialect=csv_dialect))
                        if self.is_likely_header(row):
                            header_index = i
                            header_row = row
                            break
                    except StopIteration:
                        continue
                    except csv.Error:
                        # Not a valid CSV line, which is expected in preamble
                        continue
                        
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"Warning: Error reading line {i+1}: {e}", file=sys.stderr)
                    break
                    
            self.stats["total_lines_read"] += len(preamble_lines)
                    
        except Exception as e:
            print(f"Error reading preamble: {e}", file=sys.stderr)
            
        return header_index, preamble_lines, header_row
    
    def process_csv(self, input_stream, output_stream):
        """
        Main processing function that reads a CSV, identifies and removes preamble,
        and writes clean data to output
        """
        self.start_time = time.time()
        encoding = self.config["encoding"]
        
        # Read the entire file into memory (since we need to handle wrapped lines)
        try:
            content = input_stream.read().decode(encoding)
        except UnicodeDecodeError:
            print(f"Warning: Failed to decode with {encoding}, trying windows-1252", file=sys.stderr)
            input_stream.seek(0)
            content = input_stream.read().decode('windows-1252')
        
        # Split into lines while preserving line endings
        lines = content.splitlines(True)
        
        # Find the header
        header_index = -1
        header_row = None
        
        for i, line in enumerate(lines[:self.config["max_preamble_lines"]]):
            try:
                row = next(csv.reader([line.strip()], 
                                    delimiter=self.config["delimiter"],
                                    quotechar=self.config["quotechar"]))
                if self.is_likely_header(row):
                    header_index = i
                    header_row = row
                    break
            except Exception:
                continue
        
        if header_index == -1:
            print(f"Error: Header row not found within the first {self.config['max_preamble_lines']} lines.", file=sys.stderr)
            print("Consider adjusting max_preamble_lines or header_keywords.", file=sys.stderr)
            return False
            
        print(f"Header found at line {header_index + 1}. Processing...", file=sys.stderr)
        
        # Setup CSV writer
        writer = csv.writer(output_stream, 
                           delimiter=self.config["delimiter"],
                           quotechar=self.config["quotechar"],
                           lineterminator='\n')
        
        # Write the header
        writer.writerow([field.replace('\n', ' ').strip() for field in header_row])
        self.stats["valid_lines_written"] += 1
        
        # Join all remaining lines
        remaining_content = ''.join(lines[header_index + 1:])
        
        # Process the remaining content
        try:
            csv_reader = csv.reader(io.StringIO(remaining_content),
                                  delimiter=self.config["delimiter"],
                                  quotechar=self.config["quotechar"])
            
            for row in csv_reader:
                if not row or (len(row) > 0 and row[0].strip().startswith('#')):
                    self.stats["skipped_lines"] += 1
                    continue
                    
                if any(field.strip() for field in row):
                    # Clean up each field
                    cleaned_row = []
                    for field in row:
                        # Replace newlines and multiple spaces with single spaces
                        cleaned_field = ' '.join(field.replace('\n', ' ').split())
                        cleaned_row.append(cleaned_field)
                        
                    writer.writerow(cleaned_row)
                    self.stats["valid_lines_written"] += 1
                else:
                    self.stats["skipped_lines"] += 1
                    
        except Exception as e:
            print(f"Error processing CSV data: {e}", file=sys.stderr)
            return False
            
        duration = time.time() - self.start_time
        print(f"Processing complete in {duration:.2f} seconds:", file=sys.stderr)
        print(f"  Total lines read: {len(lines)}", file=sys.stderr)
        print(f"  Valid lines written: {self.stats['valid_lines_written']}", file=sys.stderr)
        print(f"  Lines skipped: {self.stats['skipped_lines']}", file=sys.stderr)
        
        return True
    
    def preview_file(self, input_stream, num_lines=5):
        """
        Shows a preview of the file with line numbers and potential header detection
        """
        encoding = self.config["encoding"]
        lines = []
        header_index = -1
        
        original_pos = input_stream.tell()
        
        try:
            for i in range(num_lines):
                line_bytes = input_stream.readline()
                if not line_bytes:
                    break
                    
                try:
                    line = line_bytes.decode(encoding)
                    lines.append(line.rstrip())
                    
                    # Check if this could be a header
                    try:
                        row = next(csv.reader(io.StringIO(line), 
                                             delimiter=self.config["delimiter"],
                                             quotechar=self.config["quotechar"]))
                        if self.is_likely_header(row) and header_index == -1:
                            header_index = i
                    except Exception:
                        pass
                        
                except UnicodeDecodeError:
                    lines.append(f"[Line could not be decoded with {encoding}]")
                    
        except Exception as e:
            print(f"Error previewing file: {e}", file=sys.stderr)
            
        # Reset file pointer to original position
        input_stream.seek(original_pos)
        
        # Print preview
        print("\nFile Preview:", file=sys.stderr)
        for i, line in enumerate(lines):
            prefix = "→ " if i == header_index else "  "
            print(f"{prefix}{i+1}: {line[:80]}{'...' if len(line) > 80 else ''}", file=sys.stderr)
            
        if header_index != -1:
            print(f"\nPotential header detected at line {header_index + 1}", file=sys.stderr)
            
        return header_index != -1

def main():
    parser = argparse.ArgumentParser(
        description="CSV Cleaner - Removes metadata lines before CSV headers",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("input_file", nargs="?", 
                       help="Path to input CSV file. Reads from stdin if omitted.")
    parser.add_argument("-o", "--output_file", 
                       help="Path to output CSV file. Writes to stdout if omitted.")
    parser.add_argument("-e", "--encoding", default="utf-8",
                       help="File encoding")
    parser.add_argument("-d", "--delimiter", default=",",
                       help="CSV delimiter character")
    parser.add_argument("-q", "--quotechar", default='"',
                       help="CSV quote character")
    parser.add_argument("-m", "--min_matches", type=int, default=3,
                       help="Minimum keyword matches required to identify a header")
    parser.add_argument("-p", "--max_preamble", type=int, default=30,
                       help="Maximum lines to check for header")
    parser.add_argument("--preview", action="store_true",
                       help="Preview the file and exit without processing")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Display verbose processing information")

    args = parser.parse_args()
    
    # Configure the CSV cleaner
    config = {
        "encoding": args.encoding,
        "delimiter": args.delimiter,
        "quotechar": args.quotechar,
        "min_header_keywords_match": args.min_matches,
        "max_preamble_lines": args.max_preamble
    }
    
    cleaner = CSVCleaner(config)
    success = False
    input_handle = None
    output_handle = None
    
    try:
        # Setup input stream
        if args.input_file:
            input_handle = open(args.input_file, 'rb')
            input_stream = input_handle
        else:
            input_stream = sys.stdin.buffer
            
        # Preview mode
        if args.preview:
            cleaner.preview_file(input_stream, 10)
            if input_handle:
                input_handle.close()
            return 0
            
        # Setup output stream
        if args.output_file:
            output_handle = open(args.output_file, 'w', newline='', encoding=args.encoding)
            output_stream = output_handle
        else:
            # Reconfigure stdout for correct encoding if needed
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding=args.encoding)
            output_stream = sys.stdout
            
        # Process the file
        success = cleaner.process_csv(input_stream, output_stream)
        
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"Error: Permission denied when accessing files", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        if input_handle:
            input_handle.close()
        if output_handle:
            output_handle.close()
            
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 