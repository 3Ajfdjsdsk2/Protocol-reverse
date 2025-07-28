import json
import os
from pathlib import Path

def convert_json_format(input_file: str) -> list:
    """
    Convert JSON files with CSV content to the required JSON array format
    
    Args:
        input_file: Path to input JSON file
        
    Returns:
        List of messages in format [{"Hexstream": "..."}, ...]
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, dict) or 'content' not in data:
        raise ValueError("Input JSON must contain 'content' field")
    
    # Parse CSV content
    csv_lines = data['content'].split('\n')
    messages = []
    
    # Skip header row, process each data line
    for line in csv_lines[1:]:  # Skip header row
        if not line.strip():
            continue
        
        # Extract Hexstream (first CSV field)
        hexstream = line.split(',')[0].strip('"')
        if hexstream:
            messages.append({"Hexstream": hexstream})
    
    return messages

def process_directory(input_dir: str, output_dir: str):
    """
    Process all JSON files in directory and convert format
    
    Args:
        input_dir: Path to input directory
        output_dir: Path to output directory
    """
    # Create output directory if needed
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Process all JSON files in input directory
    for filename in os.listdir(input_dir):
        if filename.lower().endswith('.json'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            
            try:
                # Convert file format
                converted_data = convert_json_format(input_path)
                
                # Write output file
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(converted_data, f, indent=4)
                
                print(f"Converted successfully: {filename}")
                
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    # Configure command line arguments
    parser = argparse.ArgumentParser(description='Convert JSON file format')
    parser.add_argument('input_dir', help='Input directory containing original JSON files')
    parser.add_argument('output_dir', help='Output directory for converted JSON files')
    
    args = parser.parse_args()
    
    # Execute conversion
    process_directory(args.input_dir, args.output_dir)