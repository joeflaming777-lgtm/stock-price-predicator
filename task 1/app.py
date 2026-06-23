import subprocess
import sys
import os

if __name__ == "__main__":
    # Path to the virtual environment's python interpreter and the actual app.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(current_dir, "Stock-Price-Predictor", "venv", "Scripts", "python.exe")
    app_script = os.path.join(current_dir, "Stock-Price-Predictor", "app.py")
    
    if os.path.exists(venv_python) and os.path.exists(app_script):
        # Change working directory to Stock-Price-Predictor so templates, static files, and database csv files resolve correctly
        os.chdir(os.path.dirname(app_script))
        
        # Execute the real app.py using the virtual environment's python interpreter
        try:
            result = subprocess.run([venv_python, "app.py"] + sys.argv[1:])
            sys.exit(result.returncode)
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            sys.exit(0)
    else:
        print(f"Error: Could not find virtual environment or app.py in Stock-Price-Predictor folder.")
        sys.exit(1)
