import sys
import os
import shutil
import re

CONFIG_PATH = "../config.py"
BACKUP_PATH = "../config.py.bak"

def disable_model(model_name):
    print(f"Attempting to safely disable model: {model_name}")
    
    # 1. Create a secure backup
    shutil.copy(CONFIG_PATH, BACKUP_PATH)
    print(f"Backup created at {BACKUP_PATH}")
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # 2. Advanced Bracket-Matching Algorithm (100% accurate for nested dicts)
    start_idx = -1
    for i, line in enumerate(lines):
        if f'"{model_name}":' in line and '{' in line:
            start_idx = i
            break
            
    if start_idx == -1:
        print(f"Error: Model '{model_name}' not found in config.py!")
        return False
        
    bracket_count = 0
    end_idx = -1
    
    for i in range(start_idx, len(lines)):
        bracket_count += lines[i].count('{')
        bracket_count -= lines[i].count('}')
        
        if bracket_count == 0:
            end_idx = i
            break
            
    if end_idx == -1:
        print("CRITICAL ERROR: Malformed dictionary. Could not find closing bracket.")
        return False
        
    # 3. Safely comment out the exact block
    for i in range(start_idx, end_idx + 1):
        lines[i] = f"# {lines[i]}"
        
    new_content = "".join(lines)
    
    # 4. Write changes
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    # 5. Compile check (AST verification)
    if os.system(f"{sys.executable} -m py_compile {CONFIG_PATH}") != 0:
        print("CRITICAL ERROR: The modification caused a Python syntax error!")
        print("Reverting from backup instantly...")
        shutil.copy(BACKUP_PATH, CONFIG_PATH)
        return False
        
    print(f"Success! '{model_name}' has been securely disabled.")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python config_manager.py disable <model_name>")
        sys.exit(1)
        
    command = sys.argv[1]
    target = sys.argv[2]
    
    if command == "disable":
        disable_model(target)
    else:
        print("Unknown command. Only 'disable' is supported.")
