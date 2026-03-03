
import sys
import os
import time

# Get absolute path to project root
PROJECT_ROOT = os.getcwd()

# backend path
BACKEND_PATH = os.path.join(PROJECT_ROOT, "App", "webview_ui", "backend")

# agent path (parent of menubar?)
# actually agent is a package inside the root?
# Let's see file structure:
# root/agent/__init__.py ?
# root/menubar/settings.py ?

# Add App directory to sys.path so we can import 'menubar'
# The directory structure is: OpenCode.../App/menubar
# So if we add .../App to sys.path, we can import menubar
APP_PATH = os.path.join(PROJECT_ROOT, "App")
sys.path.insert(0, APP_PATH)
sys.path.insert(0, BACKEND_PATH)

try:
    # Just import db_read to test DB access
    import db_read
    # Mock Settings if needed, or just don't use it in test
    class MockSettings:
        def calculate_cost(self, stats, model, provider):
            return 0.0
    
    Settings = MockSettings
    
except ImportError as e:
    print(f"Import Error: {e}")
    print("sys.path:", sys.path)
    sys.exit(1)
except ImportError as e:
    print(f"Import Error: {e}")
    # Print sys.path for debugging
    print("sys.path:", sys.path)
    sys.exit(1)

def test_trend():
    print("Testing get_raw_trend_data...")
    try:
        # Test 'today' scope
        start_ts, end_ts = db_read.get_time_range("today")
        print(f"Time Range: {start_ts} to {end_ts}")
        
        rows = db_read.get_raw_trend_data(start_ts, end_ts)
        print(f"Rows fetched: {len(rows)}")
        
        if rows:
            print("First row sample:", rows[0])
            
        # Simulate processing
        bucket_stats = {}
        for row in rows:
            # ts, role, provider, model, input, output, reasoning, cache_r, cache_w
            try:
                ts = row[0]
                role = row[1]
                provider_id = row[2]
                model_id = row[3]
                inp = row[4]
                out = row[5]
                reason = row[6]
                
                # Check types
                # print(f"Row types: {type(ts)}, {type(role)}, {type(inp)}")
                
            except Exception as e:
                print(f"Error processing row {row}: {e}")
                break
        
        print("Data processing check passed.")
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_trend()
