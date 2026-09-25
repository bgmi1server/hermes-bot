import sys
import os

LOG_PATH = "bot.log"

def read_logs(lines=50):
    if not os.path.exists(LOG_PATH):
        print(f"Error: Log file not found at {LOG_PATH}")
        return

    try:
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            content = f.readlines()
            # Ensure we don't request more lines than exist
            num_lines = min(lines, len(content))
            tail = content[-num_lines:]
            print("".join(tail))
    except Exception as e:
        print(f"Error reading logs: {e}")

if __name__ == "__main__":
    num_lines = 50
    if len(sys.argv) > 1:
        try:
            num_lines = int(sys.argv[1])
        except ValueError:
            pass
    read_logs(num_lines)
