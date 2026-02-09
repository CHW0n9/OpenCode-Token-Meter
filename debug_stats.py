
import sys
import os
import json

# Add module path
sys.path.insert(0, os.getcwd())

try:
    from App.webview_ui.backend.api import JsApi
    
    api = JsApi()
    print("Testing get_stats('today')...")
    res = api.get_stats('today')
    print(json.dumps(res, indent=2, default=str))
    
    print("\nTesting get_stats('month')...")
    res_month = api.get_stats('month')
    # print(json.dumps(res_month, indent=2, default=str))
    if not res_month.get('success'):
        print("Month failed:", res_month.get('error'))
    else:
        print("Month success.")

except Exception as e:
    import traceback
    traceback.print_exc()
