#!/usr/bin/env python3
"""
Fix the problematic Stamen Terrain tile layer in the notebook
"""
import json

def fix_notebook():
    notebook_file = 'vehicle_01_day_analysis.ipynb'
    
    try:
        # Read the notebook
        with open(notebook_file, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        # Find and fix the problematic line
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                for i, line in enumerate(cell['source']):
                    if "folium.TileLayer('Stamen Terrain')" in line:
                        print(f"Found problematic line: {line.strip()}")
                        # Replace with a working alternative
                        cell['source'][i] = "    # folium.TileLayer('Stamen Terrain').add_to(m)  # Commented out - Stamen tiles discontinued\n"
                        # Add a working alternative on the next line
                        cell['source'].insert(i+1, "    folium.TileLayer('CartoDB Dark_Matter').add_to(m)  # Working alternative\n")
                        print("Fixed the problematic tile layer!")
                        break
        
        # Write the fixed notebook back
        with open(notebook_file, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=1, ensure_ascii=False)
        
        print(f"Successfully fixed {notebook_file}")
        
    except Exception as e:
        print(f"Error fixing notebook: {e}")

if __name__ == "__main__":
    fix_notebook() 