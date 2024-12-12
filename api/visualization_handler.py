import subprocess
import tempfile
import os
from pathlib import Path
import ast
import sys
import base64




class VisualizationHandler:
    """Handles execution of visualization code in a controlled environment."""
    
    ALLOWED_IMPORTS = {
        'pandas', 'matplotlib.pyplot', 'seaborn', 
        'numpy', 'matplotlib', 'io', 'base64','decimal'
    }
    
    TEMPLATE = '''
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import io
import base64
from decimal import Decimal

sns.set_theme(style="whitegrid")
sns.set_palette("husl")
plt.switch_backend('Agg')

{code}

# Save plot to bytes buffer
buffer = io.BytesIO()
plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300)
plt.close()
buffer.seek(0)
print(base64.b64encode(buffer.getvalue()).decode())
'''

    def __init__(self, work_dir: str = None):
        """Initialize with optional working directory."""
        self.current_visualization = None
        self.work_dir = work_dir or tempfile.gettempdir()
        self.work_dir = self.work_dir.replace("\\","\\\\")
        os.makedirs(self.work_dir, exist_ok=True)
    
    def validate_code(self, code: str) -> bool:
        """Validate visualization code for security."""
        if not code or not isinstance(code, str):
            print("Invalid code: Code must be a non-empty string")
            return False
            
        code = code.strip()
        if not code:
            print("Invalid code: Code is empty after stripping")
            return False
            
        try:
            # Parse the code into an AST
            tree = ast.parse(code)
            
            # Check all imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name.split('.')[0] not in self.ALLOWED_IMPORTS:
                            raise ValueError(f"Import not allowed: {name.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] not in self.ALLOWED_IMPORTS:
                        raise ValueError(f"Import not allowed: {node.module}")
                
                # Prevent file operations
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id == 'open':
                            raise ValueError("File operations not allowed")
                        if node.func.id == '__import__':
                            raise ValueError("Dynamic imports are not allowed")
                
                # Prevent exec/eval
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in ['exec', 'eval']:
                        raise ValueError("exec/eval not allowed")
                    
                # Prevent function/class definitions
                elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    raise ValueError("Function and class definitions are not allowed")
            
            return True
        except SyntaxError as e:
            print(f"Syntax error in code: {str(e)}")
            return False
        except Exception as e:
            print(f"Code validation error: {str(e)}")
            return False
    
    def execute_visualization(self, code: str, data: str) -> bytes:
        """Execute visualization code and return image as bytes."""
        if not self.validate_code(code):
            raise ValueError("Invalid visualization code")
            
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "visualization.py"
            
            full_code = f"data = {data}\n" + code
            script_content = self.TEMPLATE.format(code=full_code)
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            try:
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    cwd=temp_dir
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"Visualization failed: {result.stderr}")
                
                # Decode base64 output to bytes
                return base64.b64decode(result.stdout.strip())
                    
            except Exception as e:
                print(f"Error executing visualization: {str(e)}")
                raise