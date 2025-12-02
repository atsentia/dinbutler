"""CLI entry point for DinButler."""

import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DinButler - Your Butler for AI sandboxes"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Server command
    server_parser = subparsers.add_parser("server", help="Start the API server")
    server_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # Build templates command
    build_parser = subparsers.add_parser("build-templates", help="Build Docker templates")
    build_parser.add_argument("--template", help="Specific template to build")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove all sandboxes")

    # List command
    list_parser = subparsers.add_parser("list", help="List running sandboxes")

    args = parser.parse_args()

    if args.command == "server":
        run_server(args)
    elif args.command == "build-templates":
        build_templates(args)
    elif args.command == "cleanup":
        cleanup_sandboxes()
    elif args.command == "list":
        list_sandboxes()
    else:
        parser.print_help()


def run_server(args):
    """Run the API server."""
    try:
        import uvicorn
        uvicorn.run(
            "dinbutler.server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)


def build_templates(args):
    """Build Docker templates."""
    from dinbutler.services.docker_client import get_docker_client
    import os

    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    if not os.path.exists(templates_dir):
        templates_dir = "templates"

    templates = ["default", "python", "node", "gemini"]
    if args.template:
        templates = [args.template]

    client = get_docker_client()

    for template in templates:
        template_path = os.path.join(templates_dir, template)
        if os.path.exists(template_path):
            print(f"Building template: {template}")
            try:
                client.build_image(template_path, f"dinbutler-{template}:latest")
                print(f"  ✓ Built dinbutler-{template}:latest")
            except Exception as e:
                print(f"  ✗ Failed: {e}")
        else:
            print(f"  ✗ Template directory not found: {template_path}")


def cleanup_sandboxes():
    """Remove all sandboxes."""
    from dinbutler.services.sandbox_manager import get_sandbox_manager

    manager = get_sandbox_manager()
    count = manager.cleanup_all()
    print(f"Removed {count} sandbox(es)")


def list_sandboxes():
    """List running sandboxes."""
    from dinbutler.services.sandbox_manager import get_sandbox_manager

    manager = get_sandbox_manager()
    sandboxes = manager.list()

    if not sandboxes:
        print("No sandboxes running")
        return

    print(f"{'SANDBOX ID':<26} {'TEMPLATE':<10} {'STATE':<8} {'STARTED':<17} {'TIMEOUT':<17}")
    print("-" * 80)
    for s in sandboxes:
        started = s.started_at.strftime("%Y%m%d %H:%M:%S") if s.started_at else "-"
        timeout = s.end_at.strftime("%Y%m%d %H:%M:%S") if s.end_at else "-"
        print(f"{s.sandbox_id:<26} {s.template_id:<10} {s.state.value:<8} {started:<17} {timeout:<17}")


if __name__ == "__main__":
    main()
