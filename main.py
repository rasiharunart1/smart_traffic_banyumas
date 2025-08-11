"""
Entry point for Smart Traffic Counter Application
Refactored modular architecture version
Updated: 2025-12-19 by Smart Traffic Counter Refactoring
"""

import sys
import argparse
from app_controller import create_app
from cli import main as cli_main


def main():
    """Main entry point with CLI argument support"""
    parser = argparse.ArgumentParser(description="Smart Traffic Counter Application")
    parser.add_argument('--headless', action='store_true', 
                       help='Run in headless mode (use CLI interface)')
    parser.add_argument('--cli', action='store_true',
                       help='Use CLI interface directly')
    
    # Parse only known args to allow CLI args to pass through
    args, unknown = parser.parse_known_args()
    
    if args.cli:
        # Pass control to CLI main
        sys.argv = [sys.argv[0]] + unknown
        return cli_main()
    elif args.headless:
        # Create headless app controller
        app = create_app(headless=True)
        print("Headless mode: Use --cli flag for command-line interface")
        return 0
    else:
        # Create and run GUI application
        app = create_app(headless=False)
        app.run()
        return 0


if __name__ == "__main__":
    sys.exit(main())