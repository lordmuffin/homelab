#!/usr/bin/env python3
"""
Main CLI interface for the Automation Orchestrator.

This script provides a comprehensive command-line interface for all orchestrator operations:
- Seed inventory processing
- Network discovery
- Asset management
- Ansible inventory generation
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, List
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich.panel import Panel
from rich.text import Text

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.orchestrator import AutomationOrchestrator
from core.logger import setup_logging
from seed.seed_parser import SeedParser
from seed.validator import SeedValidator

console = Console()


@click.group()
@click.option('--config-dir', type=click.Path(exists=True, path_type=Path), help='Configuration directory')
@click.option('--log-level', default='INFO', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), help='Logging level')
@click.option('--log-file', type=click.Path(path_type=Path), help='Log file path')
@click.pass_context
def cli(ctx, config_dir: Optional[Path], log_level: str, log_file: Optional[Path]):
    """
    Automation Orchestrator - Infrastructure Discovery and Management
    
    This tool provides comprehensive infrastructure discovery, asset management,
    and dynamic Ansible inventory generation capabilities.
    """
    # Setup logging
    setup_logging(log_level, log_file)
    
    # Initialize orchestrator
    ctx.ensure_object(dict)
    ctx.obj['orchestrator'] = AutomationOrchestrator(config_dir)
    ctx.obj['config_dir'] = config_dir
    
    console.print(Panel.fit("🚀 [bold blue]Automation Orchestrator[/bold blue]", border_style="blue"))


@cli.command()
@click.argument('seed_file', type=click.Path(exists=True, path_type=Path))
@click.option('--validate-only', is_flag=True, help='Only validate seed file without discovery')
@click.option('--generate-inventory', is_flag=True, default=True, help='Generate Ansible inventory after discovery')
@click.option('--output-dir', type=click.Path(path_type=Path), help='Output directory for generated files')
@click.pass_context
async def discover(ctx, seed_file: Path, validate_only: bool, generate_inventory: bool, output_dir: Optional[Path]):
    """
    Run discovery from seed inventory file.
    
    This command implements the complete discovery pipeline:
    1. Parse and validate seed inventory
    2. Discover network assets
    3. Store in centralized database
    4. Generate Ansible inventory
    """
    orchestrator: AutomationOrchestrator = ctx.obj['orchestrator']
    
    try:
        # Initialize orchestrator
        orchestrator.initialize()
        
        console.print(f"📋 Processing seed file: [cyan]{seed_file}[/cyan]")
        
        # Validate seed file first
        seed_parser = SeedParser()
        validator = SeedValidator()
        
        with console.status("[bold green]Validating seed file..."):
            seed_data = seed_parser.parse_seed_file(seed_file)
            is_valid, errors, warnings = validator.comprehensive_validation(seed_data)
        
        # Display validation results
        if warnings:
            console.print("⚠️  [yellow]Validation Warnings:[/yellow]")
            for warning in warnings:
                console.print(f"  • {warning}")
        
        if errors:
            console.print("❌ [red]Validation Errors:[/red]")
            for error in errors:
                console.print(f"  • {error}")
            
            if not is_valid:
                console.print("\n[red]Cannot proceed with discovery due to validation errors.[/red]")
                return
        
        if validate_only:
            console.print("✅ [green]Seed file validation completed.[/green]")
            return
        
        # Run discovery
        with Progress() as progress:
            task = progress.add_task("[cyan]Running discovery pipeline...", total=4)
            
            result = await orchestrator.run_full_discovery(seed_file, generate_inventory)
            
            progress.update(task, completed=4)
        
        # Display results
        _display_discovery_results(result)
        
        if output_dir and result.inventory_path:
            # Copy inventory to output directory if specified
            import shutil
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(result.inventory_path, output_dir)
            console.print(f"📄 Inventory copied to: [cyan]{output_dir}[/cyan]")
    
    except Exception as e:
        console.print(f"❌ [red]Discovery failed: {e}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.option('--output-dir', type=click.Path(path_type=Path), help='Output directory for inventory')
@click.option('--format', default='yaml', type=click.Choice(['yaml', 'json', 'ini']), help='Inventory format')
@click.pass_context
async def generate_inventory(ctx, output_dir: Optional[Path], format: str):
    """
    Generate Ansible inventory from existing assets.
    
    This command generates an Ansible inventory file from the current
    centralized asset database without running new discovery.
    """
    orchestrator: AutomationOrchestrator = ctx.obj['orchestrator']
    
    try:
        orchestrator.initialize()
        
        # Update config format if specified
        if format != orchestrator.get_config().ansible.output_format:
            orchestrator.config.ansible.output_format = format
        
        with console.status("[bold green]Generating Ansible inventory..."):
            result = await orchestrator.generate_inventory_only()
        
        if result.success:
            console.print("✅ [green]Inventory generated successfully![/green]")
            if result.inventory_path:
                console.print(f"📄 Inventory file: [cyan]{result.inventory_path}[/cyan]")
                
                if output_dir:
                    import shutil
                    output_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(result.inventory_path, output_dir)
                    console.print(f"📄 Copied to: [cyan]{output_dir}[/cyan]")
        else:
            console.print("❌ [red]Inventory generation failed[/red]")
            for error in result.errors:
                console.print(f"  • {error}")
    
    except Exception as e:
        console.print(f"❌ [red]Inventory generation failed: {e}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.option('--format', default='table', type=click.Choice(['table', 'json', 'yaml']), help='Output format')
@click.option('--filter-type', help='Filter by asset type')
@click.option('--filter-location', help='Filter by location')
@click.option('--filter-group', help='Filter by Ansible group')
@click.pass_context
async def list_assets(ctx, format: str, filter_type: Optional[str], filter_location: Optional[str], filter_group: Optional[str]):
    """
    List discovered assets.
    
    Display all assets currently stored in the centralized database
    with optional filtering capabilities.
    """
    orchestrator: AutomationOrchestrator = ctx.obj['orchestrator']
    
    try:
        orchestrator.initialize()
        
        with console.status("[bold green]Loading assets..."):
            assets = await orchestrator.asset_store.get_all_assets()
        
        # Apply filters
        filtered_assets = assets
        if filter_type:
            filtered_assets = [a for a in filtered_assets if a.get('type') == filter_type or a.get('classification') == filter_type]
        if filter_location:
            filtered_assets = [a for a in filtered_assets if a.get('location') == filter_location]
        
        if format == 'table':
            _display_assets_table(filtered_assets)
        elif format == 'json':
            import json
            console.print(json.dumps(filtered_assets, indent=2, default=str))
        elif format == 'yaml':
            import yaml
            console.print(yaml.dump(filtered_assets, default_flow_style=False))
    
    except Exception as e:
        console.print(f"❌ [red]Failed to list assets: {e}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.pass_context
async def status(ctx):
    """
    Show orchestrator status and statistics.
    
    Display current status of the orchestrator including:
    - Asset storage statistics
    - Recent discovery activity
    - System health
    """
    orchestrator: AutomationOrchestrator = ctx.obj['orchestrator']
    
    try:
        orchestrator.initialize()
        
        with console.status("[bold green]Gathering system status..."):
            # Get asset summary
            asset_summary = await orchestrator.get_asset_summary()
            
            # Get storage statistics
            storage_stats = await orchestrator.asset_store.get_storage_statistics()
        
        # Display status information
        _display_status_information(asset_summary, storage_stats)
    
    except Exception as e:
        console.print(f"❌ [red]Failed to get status: {e}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--format', default='json', type=click.Choice(['json', 'yaml', 'csv']), help='Export format')
@click.pass_context
async def export(ctx, output_file: Path, format: str):
    """
    Export assets to external file.
    
    Export the complete asset database to various formats for
    external processing or backup purposes.
    """
    orchestrator: AutomationOrchestrator = ctx.obj['orchestrator']
    
    try:
        orchestrator.initialize()
        
        with console.status(f"[bold green]Exporting assets to {format.upper()}..."):
            success = await orchestrator.asset_store.export_assets(output_file, format)
        
        if success:
            console.print(f"✅ [green]Assets exported to: [cyan]{output_file}[/cyan][/green]")
        else:
            console.print("❌ [red]Export failed[/red]")
    
    except Exception as e:
        console.print(f"❌ [red]Export failed: {e}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.argument('output_file', type=click.Path(path_type=Path))
@click.pass_context
def create_seed(ctx, output_file: Path):
    """
    Create sample seed inventory file.
    
    Generate a sample seed inventory file with examples and documentation
    to help users get started with the orchestrator.
    """
    try:
        seed_parser = SeedParser()
        created_file = seed_parser.create_sample_seed_file(output_file)
        
        console.print(f"✅ [green]Sample seed file created: [cyan]{created_file}[/cyan][/green]")
        console.print("\n📝 [blue]Next steps:[/blue]")
        console.print("1. Edit the seed file to match your infrastructure")
        console.print("2. Run: [cyan]orchestrate discover <seed_file>[/cyan]")
        console.print("3. Generated Ansible inventory will be ready for use!")
    
    except Exception as e:
        console.print(f"❌ [red]Failed to create seed file: {e}[/red]")
        raise click.ClickException(str(e))


@cli.command()
@click.argument('seed_file', type=click.Path(exists=True, path_type=Path))
@click.option('--show-suggestions', is_flag=True, help='Show improvement suggestions')
@click.pass_context
def validate(ctx, seed_file: Path, show_suggestions: bool):
    """
    Validate seed inventory file.
    
    Perform comprehensive validation of a seed inventory file including:
    - Schema validation
    - Network overlap detection
    - Consistency checks
    - Security assessment
    """
    try:
        seed_parser = SeedParser()
        validator = SeedValidator()
        
        console.print(f"🔍 [blue]Validating seed file: [cyan]{seed_file}[/cyan][/blue]")
        
        with console.status("[bold green]Parsing and validating..."):
            seed_data = seed_parser.parse_seed_file(seed_file)
            is_valid, errors, warnings = validator.comprehensive_validation(seed_data)
        
        # Display results
        if is_valid:
            console.print("✅ [green]Validation passed![/green]")
        else:
            console.print("❌ [red]Validation failed![/red]")
        
        if errors:
            console.print("\n🚫 [red]Errors:[/red]")
            for error in errors:
                console.print(f"  • {error}")
        
        if warnings:
            console.print("\n⚠️  [yellow]Warnings:[/yellow]")
            for warning in warnings:
                console.print(f"  • {warning}")
        
        if show_suggestions:
            suggestions = validator.suggest_fixes(seed_data)
            if suggestions:
                console.print("\n💡 [blue]Suggestions:[/blue]")
                for suggestion in suggestions:
                    console.print(f"  • {suggestion}")
    
    except Exception as e:
        console.print(f"❌ [red]Validation failed: {e}[/red]")
        raise click.ClickException(str(e))


def _display_discovery_results(result):
    """Display discovery results in a formatted table."""
    if result.success:
        console.print("✅ [green]Discovery completed successfully![/green]")
    else:
        console.print("❌ [red]Discovery failed![/red]")
    
    # Create results table
    table = Table(title="Discovery Results", show_header=True, header_style="bold blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Assets Discovered", str(result.assets_discovered))
    table.add_row("Assets Updated", str(result.assets_updated))
    table.add_row("Execution Time", f"{result.execution_time:.2f}s")
    table.add_row("Inventory Generated", "Yes" if result.inventory_generated else "No")
    
    if result.inventory_path:
        table.add_row("Inventory File", str(result.inventory_path))
    
    console.print(table)
    
    # Display errors and warnings
    if result.errors:
        console.print("\n🚫 [red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  • {error}")
    
    if result.warnings:
        console.print("\n⚠️  [yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  • {warning}")


def _display_assets_table(assets: List[dict]):
    """Display assets in a formatted table."""
    if not assets:
        console.print("📭 [yellow]No assets found.[/yellow]")
        return
    
    table = Table(title=f"Discovered Assets ({len(assets)} total)", show_header=True, header_style="bold blue")
    table.add_column("IP Address", style="cyan")
    table.add_column("Hostname", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Services", style="magenta")
    table.add_column("GPU", style="red")
    table.add_column("Last Updated", style="blue")
    
    for asset in assets:
        ip = asset.get('ip', 'N/A')
        hostname = asset.get('hostname', 'N/A')
        asset_type = asset.get('type') or asset.get('classification', 'unknown')
        
        services = asset.get('services', [])
        service_names = ', '.join([s.get('name', 'unknown') for s in services[:3]])
        if len(services) > 3:
            service_names += f" (+{len(services) - 3})"
        
        gpu_info = asset.get('gpu_info', {})
        gpu_status = "✓" if gpu_info.get('has_gpu') else "✗"
        
        last_updated = asset.get('last_updated', 'N/A')
        if last_updated != 'N/A':
            # Format timestamp
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                last_updated = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        
        table.add_row(ip, hostname, asset_type, service_names, gpu_status, last_updated)
    
    console.print(table)


def _display_status_information(asset_summary: dict, storage_stats: dict):
    """Display status information."""
    # Asset summary table
    table = Table(title="Asset Summary", show_header=True, header_style="bold blue")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="green")
    
    table.add_row("Total Assets", str(asset_summary.get('total_assets', 0)))
    
    # By type
    for asset_type, count in asset_summary.get('by_type', {}).items():
        table.add_row(f"  └─ {asset_type}", str(count))
    
    # By location
    if asset_summary.get('by_location'):
        table.add_row("", "")  # Separator
        for location, count in asset_summary.get('by_location', {}).items():
            table.add_row(f"📍 {location}", str(count))
    
    # Hardware summary
    if asset_summary.get('by_hardware'):
        table.add_row("", "")  # Separator
        for hardware_type, info in asset_summary.get('by_hardware', {}).items():
            if isinstance(info, dict):
                for subtype, count in info.items():
                    table.add_row(f"🔧 {hardware_type} ({subtype})", str(count))
            else:
                table.add_row(f"🔧 {hardware_type}", str(info))
    
    console.print(table)
    
    # Storage statistics
    if storage_stats:
        storage_table = Table(title="Storage Statistics", show_header=True, header_style="bold blue")
        storage_table.add_column("Metric", style="cyan")
        storage_table.add_column("Value", style="green")
        
        storage_table.add_row("Storage Path", str(storage_stats.get('storage_path', 'N/A')))
        storage_table.add_row("Version Control", "Enabled" if storage_stats.get('version_control_enabled') else "Disabled")
        storage_table.add_row("Backup Retention", f"{storage_stats.get('backup_retention_days', 0)} days")
        storage_table.add_row("Backup Count", str(storage_stats.get('backup_count', 0)))
        
        if storage_stats.get('last_updated'):
            storage_table.add_row("Last Updated", storage_stats['last_updated'])
        
        console.print(storage_table)


def main():
    """Main entry point for CLI."""
    # Handle async commands
    def async_wrapper(func):
        def wrapper(*args, **kwargs):
            return asyncio.run(func(*args, **kwargs))
        return wrapper
    
    # Wrap async commands
    discover.callback = async_wrapper(discover.callback)
    generate_inventory.callback = async_wrapper(generate_inventory.callback)
    list_assets.callback = async_wrapper(list_assets.callback)
    status.callback = async_wrapper(status.callback)
    export.callback = async_wrapper(export.callback)
    
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n⚠️  [yellow]Operation cancelled by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ [red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()