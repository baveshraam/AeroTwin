import re
import time
import sys

log_path = 'runs/train_base.log'

with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    f.seek(0, 2)  # go to end
    last_print = ""
    print("=== LIVE TRAINING OUTPUT ===")
    print("(epoch 14/40, ~2.4 it/s on RTX 4060)")
    print("Press Ctrl+C to stop\n")
    sys.stdout.flush()
    
    while True:
        line = f.readline()
        if line:
            cleaned = re.sub(r'\x1b\[[0-9;]*[mK]', '', line).rstrip()
            if cleaned and cleaned != last_print:
                # Only show epoch headers, validation results, and progress
                if any(kw in cleaned for kw in ['Epoch', '/40', 'all', 'mAP50', 'Class']):
                    last_print = cleaned
                    # Strip any remaining non-ASCII that might cause issues
                    safe = cleaned.encode('ascii', errors='replace').decode('ascii')
                    print(safe)
                    sys.stdout.flush()
        else:
            time.sleep(0.5)