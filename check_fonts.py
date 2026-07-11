import tkinter as tk
import tkinter.font as tf

r = tk.Tk()
fams = sorted(tf.families())
print("Total fonts:", len(fams))
for f in fams:
    print(f"  {f}")

print("\n--- CJK check ---")
cjk_keywords = ['wenquan', 'micro', 'hei', 'cjk', 'noto']
found = [f for f in fams if any(k in f.lower() for k in cjk_keywords)]
if found:
    for f in found:
        print(f"  CJK font found: {f}")
        try:
            font = tf.Font(family=f, size=12)
            print(f"    actual: {font.actual()}")
        except Exception as e:
            print(f"    error: {e}")
else:
    print("  No CJK font found in tkinter!")

# Also check via fc-list
import subprocess
result = subprocess.run(['fc-list', ':lang=zh'], capture_output=True, text=True)
print(f"\n--- fc-list :lang=zh ---")
print(result.stdout[:500] if result.stdout else "(none)")

r.destroy()
