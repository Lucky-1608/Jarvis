"""
Jarvis OS — Command-Line Interface.

Commands:
  jarvis chat     — Interactive terminal chat with Jarvis
  jarvis serve    — Start the API server
  jarvis status   — Check system health
  jarvis tools    — List available tools
"""

from __future__ import annotations

import traceroot
from dotenv import load_dotenv

load_dotenv()
traceroot.initialize()

import asyncio

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


# ---------------------------------------------------------------------------
# ASCII banner
# ---------------------------------------------------------------------------
BANNER = r"""
       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
       ██║███████║██████╔╝██║   ██║██║███████╗
  ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
                   O S  v0.1.0
"""


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------
@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Jarvis OS — AI Operating System."""
    if ctx.invoked_subcommand is None:
        # Default to chat mode
        ctx.invoke(chat)


# ---------------------------------------------------------------------------
# jarvis chat
# ---------------------------------------------------------------------------
@main.command()
def chat():
    """Start an interactive chat session with Jarvis."""
    console.print(Panel(
        Text(BANNER, style="cyan bold"),
        title="[bold white]AI Operating System[/bold white]",
        border_style="cyan",
        padding=(0, 2),
    ))
    console.print(
        "[dim]Type your message and press Enter. "
        "Type 'exit' or 'quit' to leave. "
        "Type '/tools' to list tools. "
        "Type '/status' to check health.[/dim]\n"
    )

    asyncio.run(_chat_loop())


async def _chat_loop():
    """Async chat loop."""
    from jarvis.brain.jarvis_brain import JarvisBrain

    brain = JarvisBrain()

    with console.status("[cyan]Initializing Jarvis...[/cyan]", spinner="dots"):
        await brain.initialize()

    console.print("[green]✓ Jarvis is ready.[/green]\n")

    while True:
        try:
            user_input = console.input("[bold cyan]You ▸ [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue

        # Commands
        if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
            console.print("[dim]Shutting down...[/dim]")
            await brain.shutdown()
            break

        if user_input.lower() == "/tools":
            _show_tools(brain)
            continue

        if user_input.lower() == "/status":
            await _show_status(brain)
            continue

        if user_input.lower() == "/memory":
            _show_memory(brain)
            continue

        if user_input.lower() == "/clear":
            brain.memory.clear_conversation()
            console.print("[dim]Conversation cleared.[/dim]\n")
            continue

        # Process with Jarvis
        try:
            with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                response = await brain.process(user_input)

            # Show tool results if any
            if response.tool_results:
                for tr in response.tool_results:
                    status_icon = "✓" if tr["status"] == "completed" else "✗"
                    style = "green" if tr["status"] == "completed" else "red"
                    console.print(
                        f"  [{style}]{status_icon}[/{style}] "
                        f"[dim]{tr.get('tool', 'AI')}[/dim]: "
                        f"{tr.get('description', '')}"
                    )
                console.print()

            # Show response as rendered Markdown
            console.print(Panel(
                Markdown(response.content),
                title="[bold green]Jarvis[/bold green]",
                border_style="green",
                padding=(1, 2),
            ))

            # Show metadata
            console.print(
                f"  [dim]{response.provider}/{response.model} • "
                f"{round(response.latency_ms)}ms[/dim]\n"
            )

        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]\n")


def _show_tools(brain):
    """Display registered tools as a table."""
    table = Table(title="Registered Tools", border_style="cyan")
    table.add_column("Name", style="bold cyan")
    table.add_column("Category", style="dim")
    table.add_column("Description")
    table.add_column("⚠", justify="center")

    for meta in brain.tools.list_all():
        table.add_row(
            meta.name,
            meta.category.value,
            meta.description[:60],
            "⚠" if meta.dangerous else "",
        )

    console.print(table)
    console.print()


async def _show_status(brain):
    """Display system health status."""
    with console.status("[cyan]Checking health...[/cyan]", spinner="dots"):
        health = await brain.get_health()

    console.print(Panel(
        f"[bold]Status:[/bold] {health['status']}\n"
        f"[bold]Tools:[/bold]  {health.get('tools_registered', 0)} registered\n"
        f"[bold]Memory:[/bold] {health.get('memory_stats', {}).get('conversation_buffer_size', 0)} messages in buffer",
        title="[bold cyan]System Health[/bold cyan]",
        border_style="cyan",
    ))

    # Provider status
    for name, info in health.get("providers", {}).items():
        status = "[green]●[/green]" if info.get("available") else "[red]●[/red]"
        latency = f"{info.get('latency_ms', 0):.0f}ms"
        error = f" — [red]{info.get('error', '')}[/red]" if info.get("error") else ""
        console.print(f"  {status} {name}: {latency}{error}")

    console.print()


def _show_memory(brain):
    """Display memory statistics."""
    stats = brain.memory.get_stats()
    console.print(Panel(
        f"[bold]Working Memory:[/bold] {stats['working_memory_keys']} keys\n"
        f"[bold]Conversation:[/bold]   {stats['conversation_buffer_size']} messages\n"
        f"[bold]Collections:[/bold]\n"
        + "\n".join(
            f"  • {name}: {info['count']} entries"
            for name, info in stats.get("collections", {}).items()
        ),
        title="[bold cyan]Memory Stats[/bold cyan]",
        border_style="cyan",
    ))
    console.print()


# ---------------------------------------------------------------------------
# jarvis serve
# ---------------------------------------------------------------------------
@main.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, type=int, help="Server port")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool):
    """Start the Jarvis OS API server."""
    import uvicorn

    console.print(Panel(
        Text(BANNER, style="cyan bold"),
        title="[bold white]API Server[/bold white]",
        border_style="cyan",
    ))
    console.print(f"[green]Starting server on {host}:{port}[/green]")
    console.print(f"[dim]API docs: http://localhost:{port}/docs[/dim]\n")

    uvicorn.run(
        "jarvis.server.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ---------------------------------------------------------------------------
# jarvis status
# ---------------------------------------------------------------------------
@main.command()
def status():
    """Check Jarvis system health."""
    asyncio.run(_quick_status())


async def _quick_status():
    from jarvis.brain.jarvis_brain import JarvisBrain

    brain = JarvisBrain()
    await brain.initialize()
    await _show_status(brain)
    await brain.shutdown()


# ---------------------------------------------------------------------------
# jarvis tools
# ---------------------------------------------------------------------------
@main.command(name="tools")
def list_tools():
    """List all available tools."""
    asyncio.run(_quick_tools())


async def _quick_tools():
    from jarvis.brain.jarvis_brain import JarvisBrain

    brain = JarvisBrain()
    await brain.initialize()
    _show_tools(brain)
    await brain.shutdown()


# ---------------------------------------------------------------------------
# jarvis voice
# ---------------------------------------------------------------------------
@main.command()
@click.option(
    "--mode",
    type=click.Choice(["push-to-talk", "wake-word", "continuous"]),
    default="push-to-talk",
    help="Voice interaction mode",
)
def voice(mode: str):
    """Start the voice assistant."""
    console.print(Panel(
        Text(BANNER, style="cyan bold"),
        title="[bold white]Voice Assistant[/bold white]",
        border_style="magenta",
    ))
    console.print(f"[magenta]Mode: {mode}[/magenta]\n")
    asyncio.run(_voice_loop(mode))


async def _voice_loop(mode: str):
    from jarvis.voice.assistant import VoiceAssistant

    assistant = VoiceAssistant()

    if mode == "wake-word":
        console.print("[dim]Say 'Jarvis' to activate. Ctrl+C to exit.[/dim]\n")
        try:
            await assistant.start_wake_word_mode()
        except KeyboardInterrupt:
            pass

    elif mode == "continuous":
        console.print("[dim]Continuous mode — always listening. Say 'exit' or Ctrl+C to stop.[/dim]\n")
        try:
            await assistant.start_continuous_mode()
        except KeyboardInterrupt:
            pass

    else:  # push-to-talk (default)
        console.print(
            "[dim]Push-to-talk mode.\n"
            "Press Enter to start recording, speak, then wait for silence.\n"
            "Type 'exit' to quit.[/dim]\n"
        )
        try:
            while True:
                user = console.input("[bold magenta]Press Enter to speak (or 'exit') ▸ [/bold magenta]").strip()
                if user.lower() in ("exit", "quit"):
                    break

                console.print("[cyan]🎤 Listening...[/cyan]")
                result = await assistant.listen_and_respond()

                if result.get("error"):
                    console.print(f"[yellow]⚠ {result['error']}[/yellow]\n")
                    continue

                console.print(f"[dim]You said: {result.get('text', '')}[/dim]")
                console.print(Panel(
                    Markdown(result.get("response", "")),
                    title="[bold green]Jarvis[/bold green]",
                    border_style="green",
                    padding=(1, 2),
                ))
                console.print(
                    f"  [dim]{result.get('provider', '')}/{result.get('model', '')} • "
                    f"{result.get('latency_ms', 0)}ms[/dim]\n"
                )
        except (KeyboardInterrupt, EOFError):
            pass

    await assistant.shutdown()
    console.print("[dim]Voice assistant stopped.[/dim]")


if __name__ == "__main__":
    main()
