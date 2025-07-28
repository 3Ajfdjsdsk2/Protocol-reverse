import os
import json
from pathlib import Path

def out_to_json(input_path: str, output_path: str) -> None:
    """
    Convert all .out files in input directory to .json files in output directory
    
    Args:
        input_path: Path to directory containing .out files
        output_path: Path to directory where .json files will be saved
    """
    # Create output directory if it doesn't exist
    Path(output_path).mkdir(parents=True, exist_ok=True)
    
    # Process each file in input directory
    for filename in os.listdir(input_path):
        if filename.endswith('.out'):
            input_file = os.path.join(input_path, filename)
            output_file = os.path.join(output_path, f"{Path(filename).stem}.json")
            
            try:
                # Read .out file content
                with open(input_file, 'r') as f:
                    content = f.read().strip()
                
                # Convert content to JSON structure
                # (Modify this based on actual .out file format)
                if content.startswith('{') and content.endswith('}'):
                    # If already in JSON format
                    data = json.loads(content)
                else:
                    # If plain text, store as single field
                    data = {"content": content}
                
                # Write JSON file
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=4)
                
                print(f"Converted: {input_file} -> {output_file}")
                
            except Exception as e:
                print(f"Error processing {input_file}: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Convert .out files to .json files')
    parser.add_argument('input_dir', help='Input directory containing .out files')
    parser.add_argument('output_dir', help='Output directory for .json files')
    
    args = parser.parse_args()
    
    # Execute conversion
    out_to_json(args.input_dir, args.output_dir)