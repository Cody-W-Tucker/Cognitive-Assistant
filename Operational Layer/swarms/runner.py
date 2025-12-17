#!/usr/bin/env python3
"""
Swarm Runner CLI

Command-line interface to run different swarm architectures.
Uses typer for modern CLI with type hints.
"""

import typer
from swarm_config import SWARM_CONFIG, SwarmFactory

app = typer.Typer()

@app.command()
def run_swarm(
    task: str = typer.Argument(..., help="The task or question for the swarm to process"),
    arch: str = typer.Option("moa", help="Swarm architecture to use (hierarchical or moa)"),
    model: str = typer.Option(None, help="Override the default agent model name"),
    aggregator_model: str = typer.Option(None, help="Override the aggregator model (for MoA)"),
    layers: int = typer.Option(None, help="Override number of layers (for MoA)")
):
    """
    Run a swarm with the specified task and architecture.
    """
    # Override models if specified
    if model:
        SWARM_CONFIG["defaults"]["model_name"] = model
    
    # Override aggregator model if specified and relevant to the architecture
    if aggregator_model and "aggregator_model_name" in SWARM_CONFIG["types"][arch]:
         SWARM_CONFIG["types"][arch]["aggregator_model_name"] = aggregator_model

    # Override layers for MoA if specified
    if layers is not None and "layers" in SWARM_CONFIG["types"][arch]:
        SWARM_CONFIG["types"][arch]["layers"] = layers

    # Create and run swarm
    try:
        swarm = SwarmFactory.create_swarm(arch)
        typer.echo(f"Running {arch} swarm with task: {task}")
        result = swarm.run(task=task)
        typer.echo(result)
    except Exception as e:
        typer.echo(f"Error running swarm: {e}", err=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
