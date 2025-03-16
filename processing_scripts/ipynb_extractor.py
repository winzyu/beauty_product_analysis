#!/usr/bin/env python3
import json
import os
import sys
import nbformat
from pathlib import Path

# Project directory structure constants
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RITEAID_DIR = os.path.join(PROJECT_ROOT, 'riteaid')
RITEAID_NOTEBOOK = os.path.join(RITEAID_DIR, 'FinalProject (1).ipynb')

def extract_outputs(notebook_path, output_path=None):
    """
    Extract all outputs from a Jupyter notebook and optionally save to a file.
    
    Args:
        notebook_path (str): Path to the .ipynb file
        output_path (str, optional): Path to save the outputs. If None, prints to console.
    
    Returns:
        list: List of extracted outputs
    """
    try:
        # Load the notebook
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        # Extract all outputs with cell numbers and execution counts
        all_outputs = []
        for cell_idx, cell in enumerate(notebook['cells']):
            if cell['cell_type'] == 'code' and 'outputs' in cell and cell['outputs']:
                exec_count = cell.get('execution_count', 'N/A')
                
                # Get the cell's source code
                source_code = ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']
                source_code = source_code.strip()
                
                # Process each output in the cell
                for output_idx, output in enumerate(cell['outputs']):
                    output_content = None
                    output_type = output.get('output_type', 'unknown')
                    
                    if output_type == 'stream':
                        if 'text' in output:
                            content = output['text']
                            if isinstance(content, list):
                                content = ''.join(content)
                            output_content = content
                    
                    elif output_type == 'execute_result' or output_type == 'display_data':
                        if 'data' in output:
                            if 'text/plain' in output['data']:
                                content = output['data']['text/plain']
                                if isinstance(content, list):
                                    content = ''.join(content)
                                output_content = content
                            # Handle other data types like images, HTML, etc.
                            elif 'text/html' in output['data']:
                                output_content = f"[HTML output]"
                            elif 'image/png' in output['data']:
                                output_content = f"[Image output]"
                    
                    elif output_type == 'error':
                        if 'traceback' in output:
                            content = output['traceback']
                            if isinstance(content, list):
                                content = '\n'.join(content)
                            output_content = f"ERROR: {content}"
                    
                    if output_content is not None:
                        all_outputs.append({
                            'cell_number': cell_idx + 1,
                            'execution_count': exec_count,
                            'output_number': output_idx + 1,
                            'output_type': output_type,
                            'content': output_content
                        })
        
        # Format and save/print outputs
        formatted_output = ""
        for item in all_outputs:
            formatted_output += f"Cell {item['cell_number']} [Execution Count: {item['execution_count']}] Output {item['output_number']}:\n"
            formatted_output += f"{item['content']}\n"
            formatted_output += "-" * 80 + "\n\n"
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_output)
            print(f"Outputs extracted and saved to {output_path}")
        else:
            print(formatted_output)
        
        return all_outputs
    
    except Exception as e:
        print(f"Error extracting outputs from notebook: {str(e)}")
        return []

def find_notebook(directory, notebook_name):
    """
    Find a notebook with the given name in the directory.
    
    Args:
        directory (str): Directory to search
        notebook_name (str): Name of the notebook (with or without .ipynb extension)
    
    Returns:
        str or None: Path to the notebook if found, None otherwise
    """
    if not notebook_name.endswith('.ipynb'):
        notebook_name += '.ipynb'
    
    for root, _, files in os.walk(directory):
        if notebook_name in files:
            return os.path.join(root, notebook_name)
    
    return None

if __name__ == "__main__":
    parser_type = None
    
    if len(sys.argv) >= 2:
        parser_type = sys.argv[1].lower()
    
    # Default to riteaid if no argument provided
    if parser_type is None or parser_type == 'riteaid':
        # Use the predefined RiteAid notebook path
        notebook_path = RITEAID_NOTEBOOK
        if not os.path.exists(notebook_path):
            print(f"RiteAid notebook not found at expected path: {notebook_path}")
            sys.exit(1)
    elif parser_type == 'ulta':
        # Look in the ulta directory
        ulta_dir = os.path.join(PROJECT_ROOT, 'ulta')
        notebook_path = find_notebook(ulta_dir, "ulta")
        if not notebook_path:
            print(f"Ulta notebook not found in directory: {ulta_dir}")
            sys.exit(1)
    elif os.path.isfile(parser_type) and parser_type.endswith('.ipynb'):
        # If the argument is a direct path to a notebook
        notebook_path = parser_type
    else:
        # Try to find a notebook with the provided name
        directory = os.getcwd()
        notebook_path = find_notebook(directory, parser_type)
        
    if not notebook_path:
        # If no specific notebook found, list available notebooks
        print("No notebook specified or found. Available notebooks:")
        found_notebooks = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.ipynb'):
                    rel_path = os.path.relpath(os.path.join(root, file), directory)
                    found_notebooks.append(rel_path)
        
        for i, notebook in enumerate(found_notebooks):
            print(f"{i+1}. {notebook}")
        
        if found_notebooks:
            try:
                choice = int(input("\nSelect a notebook by number: "))
                if 1 <= choice <= len(found_notebooks):
                    notebook_path = os.path.join(directory, found_notebooks[choice-1])
                else:
                    print("Invalid selection.")
                    sys.exit(1)
            except ValueError:
                print("Invalid input.")
                sys.exit(1)
        else:
            print("No Jupyter notebooks found in the directory.")
            sys.exit(1)
    
    # Define output path based on the notebook type
    notebook_basename = os.path.basename(notebook_path).replace('.ipynb', '')
    
    if 'riteaid' in notebook_path.lower():
        output_dir = os.path.join(RITEAID_DIR, "extracted_outputs")
    elif 'ulta' in notebook_path.lower():
        output_dir = os.path.join(PROJECT_ROOT, 'ulta')
    else:
        # For any other notebook, create an extracted_outputs folder in its directory
        output_dir = os.path.join(os.path.dirname(notebook_path), "extracted_outputs")
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{notebook_basename}_outputs.txt")
    
    # Extract outputs
    extract_outputs(notebook_path, output_path)
