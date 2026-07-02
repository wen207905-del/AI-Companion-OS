import sys, os, traceback
sys.path.insert(0, r"D:\AI-Companion-OS\v2\backend")
os.chdir(r"D:\AI-Companion-OS\v2\backend")
try:
    import main
except Exception as e:
    traceback.print_exc()
