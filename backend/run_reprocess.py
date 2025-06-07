#!/usr/bin/env python3
"""
Wrapper script to run GPS reprocessing with automated inputs
"""

import subprocess
import sys
import time

def main():
    print("🚀 Starting GPS Data Reprocessing...")
    print("This will run in REAL mode and process all files")
    print("=" * 60)
    
    try:
        # Start the reprocessing script
        process = subprocess.Popen(
            [sys.executable, 'reprocess_gps_data.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Send the mode selection
        process.stdin.write("real\n")
        process.stdin.flush()
        
        # Read output line by line
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
                # Auto-confirm file processing
                if "Proceed? (yes/no):" in output:
                    print("⚡ Auto-confirming: yes")
                    process.stdin.write("yes\n")
                    process.stdin.flush()
        
        # Wait for completion
        process.wait()
        
        print("\n🎉 GPS reprocessing completed!")
        return process.returncode
        
    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        if process:
            process.terminate()
        return 1
    except Exception as e:
        print(f"\n❌ Error running reprocessing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 