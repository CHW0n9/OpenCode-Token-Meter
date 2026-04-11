"""Module entry point"""
import argparse
import sys


def _parse_args():
    parser = argparse.ArgumentParser(description="OpenCode Token Meter")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--stats-worker", action="store_true", help="Run stats worker")
    parser.add_argument("--agent", action="store_true", help="Run agent process")
    parser.add_argument("--webview", action="store_true", help="Run webview process")
    parser.add_argument("--page", default="dashboard", help="Initial page for webview")
    args, _ = parser.parse_known_args()
    return args


def main():
    args = _parse_args()
    
    if args.agent:
        import agent.uds_server
        # Override sys.argv to avoid argument parsing issues in agent
        sys.argv = [sys.argv[0]]
        agent.uds_server.main()
        return
    
    if args.webview:
        import os
        # Ensure we can find 'main.py' regardless of how we are launched
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            
        try:
            import main as webview_main
        except ImportError:
            from . import main as webview_main
            
        webview_main.main(debug=args.debug, initial_page=args.page)
        return

    if args.stats_worker:
        import stats_worker
        stats_worker.main()
        return

    import main_tray
    main_tray.main(debug=args.debug)


if __name__ == "__main__":
    main()
