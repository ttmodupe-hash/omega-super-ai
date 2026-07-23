# This file is Part 2 of 2 for omega_ai.py
# Run: python reassemble_v37.py
# =========================================

# ═══════════════════════════════════════════════════════════════════════════════
#  COMMAND REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

COMMAND_REGISTRY: dict[str, Callable[[list[str]], str]] = {
    "/help": cmd_help,
    "/version": cmd_version,
    "/status": cmd_status,
    "/learn": cmd_learn,
    "/predict": cmd_predict,
    "/memory": cmd_memory,
    "/history": cmd_history,
    "/clear": cmd_clear,
    "/save": cmd_save,
    "/server": cmd_server,
    "/server-stop": cmd_server_stop,
    "/server-status": cmd_server_status,
    "/plugins": cmd_plugins,
    "/plugin-install": cmd_plugin_install,
    "/plugin-uninstall": cmd_plugin_uninstall,
    "/config": cmd_config,
    "/config-set": cmd_config_set,
    "/export": cmd_export,
    "/import": cmd_import_data,
    "/analytics": cmd_analytics,
    "/wisdom": cmd_wisdom,
    "/repair": cmd_repair,
    "/repair-heal": cmd_repair_heal,
    "/repair-clear": cmd_repair_clear,
    "/memory-manager": cmd_memory_manager,
    "/mm-cleanup": cmd_mm_cleanup,
    "/mm-approve": cmd_mm_approve,
    "/mm-reject": cmd_mm_reject,
    "/mm-recover": cmd_mm_recover,
    "/ped-diagnostic": cmd_ped_diagnostic,
    "/ped-progress": cmd_ped_progress,
}


# ═══════════════════════════════════════════════════════════════════════════════
#  INPUT PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════════


def process_input(user_input: str) -> str:
    """Process user input — command or natural language."""
    user_input = user_input.strip()
    if not user_input:
        return ""

    _add_to_history("user", user_input)

    # Command detection
    if user_input.startswith("/"):
        parts = user_input.split()
        cmd = parts[0].lower()
        args = parts[1:]
        handler = COMMAND_REGISTRY.get(cmd)
        if handler:
            try:
                result = handler(args)
            except Exception as e:
                result = f"Command error: {e}"
            _add_to_history("assistant", result)
            return result
        return f"Unknown command: {cmd}. Type /help for available commands."

    # Natural language — route through brain
    brain = get_brain()
    try:
        result = brain.chat(user_input)
        _add_to_history("assistant", result)
        return result
    except Exception as e:
        error_msg = f"Error: {e}"
        _add_to_history("assistant", error_msg)
        return error_msg


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description=f"Omega AI v{VERSION}")
    parser.add_argument("--server", action="store_true", help="Start API server")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--command", "-c", help="Execute single command and exit")
    parser.add_argument("--no-banner", action="store_true", help="Skip banner")
    parser.add_argument("--version", "-v", action="store_true", help="Show version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"Omega AI v{VERSION} \"{CODENAME}\"")
        sys.exit(0)

    if args.server:
        print(f"Starting API server on port {args.port}...")
        try:
            import api_server
            api_server.start_server(port=args.port)
        except Exception as e:
            print(f"Server failed: {e}")
            sys.exit(1)
        return

    if args.command:
        result = process_input(args.command)
        print(result)
        sys.exit(0)

    # Interactive mode
    if not args.no_banner:
        print_banner()

    # Setup readline history
    histfile = DATA_DIR / ".omega_history"
    try:
        readline.read_history_file(str(histfile))
        readline.set_history_length(1000)
    except (FileNotFoundError, OSError):
        pass

    try:
        while True:
            try:
                user_input = input("\u03A9> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
                print("Goodbye!")
                break

            result = process_input(user_input)
            if result:
                print(result)

    finally:
        try:
            readline.write_history_file(str(histfile))
        except OSError:
            pass
        _save_history()


if __name__ == "__main__":
    main()
