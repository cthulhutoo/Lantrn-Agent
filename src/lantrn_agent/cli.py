"""CLI interface for Lantrn Agent Builder.

Usage:
    lantrn init                    Initialize a new workspace
    lantrn plan "user request"     Run the Plan phase
    lantrn build <blueprint_id>    Run the Build phase
    lantrn verify <run_id>         Run the Verify phase
    lantrn run "user request"      Run full pipeline
    lantrn agents list             List available agents
    lantrn models list             List available models
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

from .core.config import ConfigManager, init_config
from .core.pipeline import Pipeline
from .models.llm import OllamaAdapter

app = typer.Typer(
    name="lantrn",
    help="Lantrn Agent Builder - On-prem deployable AI agent system",
)
console = Console()


@app.command()
def init(
    workspace: Path = typer.Option(
        Path("./workspace"),
        "--workspace", "-w",
        help="Path to workspace directory",
    ),
):
    """Initialize a new Lantrn workspace."""
    console.print(Panel.fit(
        "🚀 [bold blue]Lantrn Agent Builder[/bold blue] 🚀",
        subtitle="Initializing workspace",
    ))
    
    # Create directory structure
    dirs = [
        workspace,
        workspace / ".bmad" / "profiles",
        workspace / ".bmad" / "blueprints",
        workspace / ".bmad" / "runs",
        workspace / "agents",
        workspace / "policies",
        workspace / "services",
        workspace / "logs",
    ]
    
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        console.print(f"  [green]✓[/green] Created {d}")
    
    # Create default config
    config_dir = workspace / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create default policy
    policy_content = '''# Default Policy
version: "1.0"
name: default-policy

file_access:
  default: deny
  allow:
    - workspace/**
    - /tmp/**
  deny:
    - ~/.ssh/**
    - **/.credentials

network_access:
  default: deny
  allow:
    - localhost:11434
    - 127.0.0.1:11434
  deny:
    - "*"

budgets:
  max_tokens_per_task: 100000
  max_file_size_mb: 50
  max_execution_time_minutes: 30
'''
    with open(workspace / "policies" / "default.yaml", "w") as f:
        f.write(policy_content)
    console.print(f"  [green]✓[/green] Created default policy")
    
    # Create default model profiles
    profiles = {
        "fast": {
            "provider": "ollama",
            "model": "llama3.2:3b",
            "ctx_length": 128000,
            "temperature": 0.7,
        },
        "hq": {
            "provider": "ollama",
            "model": "llama3.1:70b",
            "ctx_length": 128000,
            "temperature": 0.3,
        },
    }
    
    import yaml
    for name, profile in profiles.items():
        with open(workspace / ".bmad" / "profiles" / f"{name}.yaml", "w") as f:
            yaml.dump(profile, f)
    console.print(f"  [green]✓[/green] Created model profiles")
    
    console.print()
    console.print(Panel(
        f"[bold green]Workspace initialized![/bold green]\n\n"
        f"Workspace: {workspace.absolute()}\n\n"
        f"Next steps:\n"
        f"1. Add agent definitions to {workspace}/agents/\n"
        f"2. Run 'lantrn plan \"your request\"' to start",
        title="✨ Ready!",
    ))


@app.command()
def plan(
    request: str = typer.Argument(..., help="User request to plan"),
    workspace: Path = typer.Option(
        Path("./workspace"),
        "--workspace", "-w",
        help="Path to workspace directory",
    ),
    profile: str = typer.Option(
        "fast",
        "--profile", "-p",
        help="Model profile to use",
    ),
):
    """Run the Plan phase (Analyst → PM → Architect)."""
    console.print(Panel.fit(
        f"📋 [bold blue]Plan Phase[/bold blue]\n\n[dim]{request}[/dim]",
    ))
    
    init_config(workspace / "config")
    pipeline = Pipeline(workspace)
    
    async def run_plan():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running Analyst...", total=None)
            
            try:
                blueprint = await pipeline.plan(request)
                progress.update(task, description="[green]✓[/green] Plan complete!")
                return blueprint
            except Exception as e:
                progress.update(task, description=f"[red]✗[/red] Plan failed: {e}")
                raise
    
    blueprint = asyncio.run(run_plan())
    
    console.print()
    console.print(Panel(
        f"[bold]Blueprint ID:[/bold] {blueprint.id}\n"
        f"[bold]Created:[/bold] {blueprint.created_at}\n\n"
        f"[bold]Requirements:[/bold]\n{blueprint.requirements.get('requirements_doc', 'N/A')[:500]}...",
        title="📄 Blueprint Generated",
    ))


@app.command()
def build(
    blueprint_id: str = typer.Argument(..., help="Blueprint ID to build"),
    workspace: Path = typer.Option(
        Path("./workspace"),
        "--workspace", "-w",
        help="Path to workspace directory",
    ),
):
    """Run the Build phase (Dev agent)."""
    console.print(Panel.fit(
        f"🔨 [bold blue]Build Phase[/bold blue]\n\n[dim]Blueprint: {blueprint_id}[/dim]",
    ))
    
    init_config(workspace / "config")
    pipeline = Pipeline(workspace)
    
    # Load blueprint
    import yaml
    blueprint_path = workspace / ".bmad" / "blueprints" / f"{blueprint_id}.yaml"
    if not blueprint_path.exists():
        console.print(f"[red]Error: Blueprint not found: {blueprint_path}[/red]")
        raise typer.Exit(1)
    
    with open(blueprint_path) as f:
        data = yaml.safe_load(f)
    
    from .core.pipeline import Blueprint
    blueprint = Blueprint(**data)
    
    async def run_build():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running Dev agent...", total=None)
            
            try:
                manifest = await pipeline.build(blueprint)
                progress.update(task, description="[green]✓[/green] Build complete!")
                return manifest
            except Exception as e:
                progress.update(task, description=f"[red]✗[/red] Build failed: {e}")
                raise
    
    manifest = asyncio.run(run_build())
    
    console.print()
    console.print(Panel(
        f"[bold]Run ID:[/bold] {manifest.id}\n"
        f"[bold]Status:[/bold] {manifest.status}\n"
        f"[bold]Phase:[/bold] {manifest.phase}",
        title="🔧 Build Complete",
    ))


@app.command()
def run(
    request: str = typer.Argument(..., help="User request to process"),
    workspace: Path = typer.Option(
        Path("./workspace"),
        "--workspace", "-w",
        help="Path to workspace directory",
    ),
):
    """Run the full pipeline (Plan → Build → Verify)."""
    console.print(Panel.fit(
        f"🚀 [bold blue]Full Pipeline[/bold blue]\n\n[dim]{request}[/dim]",
    ))
    
    init_config(workspace / "config")
    pipeline = Pipeline(workspace)
    
    async def run_pipeline():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running Plan phase...", total=None)
            
            try:
                blueprint, build_manifest, verify_manifest = await pipeline.run(request)
                progress.update(task, description="[green]✓[/green] Pipeline complete!")
                return blueprint, build_manifest, verify_manifest
            except Exception as e:
                progress.update(task, description=f"[red]✗[/red] Pipeline failed: {e}")
                raise
    
    blueprint, build_manifest, verify_manifest = asyncio.run(run_pipeline())
    
    console.print()
    console.print(Panel(
        f"[bold]Blueprint:[/bold] {blueprint.id}\n"
        f"[bold]Build Status:[/bold] {build_manifest.status}\n"
        f"[bold]Verify Status:[/bold] {verify_manifest.status}\n",
        title="✨ Pipeline Complete",
    ))


@app.command()
def agents(
    workspace: Path = typer.Option(
        Path("./workspace"),
        "--workspace", "-w",
        help="Path to workspace directory",
    ),
):
    """List available agents."""
    agents_dir = workspace / "agents"
    
    table = Table(title="Available Agents")
    table.add_column("Role", style="cyan")
    table.add_column("Profile", style="green")
    table.add_column("Phase", style="yellow")
    
    if agents_dir.exists():
        import yaml
        for agent_file in agents_dir.glob("*.bmad.yaml"):
            with open(agent_file) as f:
                data = yaml.safe_load(f)
            table.add_row(
                data.get("role", "unknown"),
                data.get("model_profile", "default"),
                "Plan" if data.get("role") in ["analyst", "pm", "architect"] else "Build",
            )
    
    console.print(table)


@app.command()
def models(
    workspace: Path = typer.Option(
        Path("./workspace"),
        "--workspace", "-w",
        help="Path to workspace directory",
    ),
):
    """List available models from Ollama."""
    console.print("[bold]Checking Ollama models...[/bold]\n")
    
    async def list_models():
        try:
            adapter = OllamaAdapter()
            models = await adapter.list_models()
            return models
        except Exception as e:
            console.print(f"[red]Error connecting to Ollama: {e}[/red]")
            return []
    
    models_list = asyncio.run(list_models())
    
    if models_list:
        table = Table(title="Ollama Models")
        table.add_column("Model", style="cyan")
        
        for model in models_list:
            table.add_row(model)
        
        console.print(table)
    else:
        console.print("[yellow]No models found. Make sure Ollama is running.[/yellow]")
        console.print("Run 'ollama serve' and 'ollama pull llama3.2:3b'")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
    workspace: Path = typer.Option(
        Path("./workspace"),
        "--workspace", "-w",
        help="Path to workspace directory",
    ),
):
    """Start the API server."""
    import uvicorn
    from .api import create_app
    
    console.print(Panel.fit(
        f"🌐 [bold blue]Starting API Server[/bold blue]\n\n"
        f"Host: {host}\n"
        f"Port: {port}\n"
        f"Workspace: {workspace}",
    ))
    
    init_config(workspace / "config")
    app = create_app(workspace)
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    app()
