#!/usr/bin/env python3
"""CLI client for SQL-to-Dashboard MCP tools."""

import click
import json
import sys
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from ddl_parser_mcp.server import DDLParserMCPServer
from ddl_parser_mcp.schema import DDLParserRequest, InputFormat
from dashboard_generator_mcp.server import DashboardGeneratorMCPServer
from dashboard_generator_mcp.schema import DashboardGeneratorRequest, ChartConfig, ChartType

console = Console()


@click.group()
def cli():
    """SQL-to-Dashboard MCP Tool - Transform schemas into interactive dashboards."""
    pass


@cli.command()
@click.option('--input', '-i', 'input_file', required=True, type=click.Path(exists=True),
              help='Input file containing DDL or Mermaid diagram')
@click.option('--format', '-f', type=click.Choice(['ddl', 'mermaid', 'auto']), default='auto',
              help='Input format (auto-detect by default)')
@click.option('--database', '-d', type=click.Choice(['sqlite', 'postgres', 'mysql']), default='sqlite',
              help='Target database type for SQL generation')
@click.option('--output', '-o', 'output_file', type=click.Path(),
              help='Output file for SQL queries')
@click.option('--intents', '-t', multiple=True, 
              help='Visualization intents (overview, distributions, relationships, time_series)')
def parse(input_file, format, database, output_file, intents):
    """Parse DDL/Mermaid schema and generate SQL queries."""
    
    console.print(Panel.fit("🔍 [bold cyan]DDL Parser MCP[/bold cyan]", title="Starting"))
    
    # Read input file
    with open(input_file, 'r') as f:
        content = f.read()
    
    # Auto-detect format if needed
    if format == 'auto':
        if 'CREATE TABLE' in content.upper() or 'ALTER TABLE' in content.upper():
            format = 'ddl'
        elif 'erDiagram' in content:
            format = 'mermaid'
        else:
            console.print("[red]❌ Could not auto-detect format. Please specify --format[/red]")
            return
    
    console.print(f"📄 Input: {input_file} ([yellow]{format.upper()}[/yellow])")
    console.print(f"🎯 Target database: [green]{database}[/green]")
    
    # Create parser server
    parser_server = DDLParserMCPServer()
    
    # Prepare request
    request = DDLParserRequest(
        task="parse_schema",
        input=content,
        format=InputFormat(format),
        database_type=database,
        visualization_intents=list(intents) if intents else None
    )
    
    # Process request
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Parsing schema...", total=None)
        response = parser_server.handle_request(request)
        progress.update(task, completed=True)
    
    if response.status == "error":
        console.print(f"[red]❌ Error: {response.error}[/red]")
        return
    
    # Display results
    if response.schema:
        console.print(f"\n✅ Found [green]{len(response.schema.tables)}[/green] table(s) and "
                     f"[green]{len(response.schema.relationships)}[/green] relationship(s)")
        
        # Show tables
        table = Table(title="📊 Database Schema")
        table.add_column("Table", style="cyan")
        table.add_column("Columns", style="yellow")
        table.add_column("Primary Keys", style="green")
        
        for tbl in response.schema.tables:
            cols = ", ".join([col.name for col in tbl.columns])
            pks = ", ".join(tbl.primary_keys) if tbl.primary_keys else "-"
            table.add_row(tbl.name, cols, pks)
        
        console.print(table)
    
    # Display SQL queries
    if response.suggested_queries:
        console.print(f"\n🔧 Generated [green]{len(response.suggested_queries)}[/green] SQL queries")
        
        for i, query in enumerate(response.suggested_queries[:5], 1):
            console.print(f"\n[bold]Query {i}:[/bold] {query.description}")
            console.print(f"[dim]Visualization:[/dim] {query.visualization_type}")
            syntax = Syntax(query.query, "sql", theme="monokai", line_numbers=False)
            console.print(syntax)
    
    # Save to file if requested
    if output_file:
        output_data = {
            "schema": response.schema.model_dump() if response.schema else None,
            "queries": [q.model_dump() for q in response.suggested_queries] if response.suggested_queries else [],
            "sql_statements": response.sql_statements
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        console.print(f"\n💾 Saved to: [green]{output_file}[/green]")
    
    # Display instructions
    if response.instructions:
        console.print(Panel(response.instructions, title="📝 Next Steps", border_style="blue"))


@cli.command()
@click.option('--data', '-d', 'data_file', required=True, type=click.Path(exists=True),
              help='JSON file containing query results')
@click.option('--output', '-o', 'output_file', required=True, type=click.Path(),
              help='Output HTML file for dashboard')
@click.option('--title', '-t', default='Data Dashboard',
              help='Dashboard title')
@click.option('--theme', type=click.Choice(['light', 'dark']), default='light',
              help='Dashboard theme')
@click.option('--charts', '-c', multiple=True,
              type=click.Choice(['bar', 'line', 'pie', 'scatter', 'table']),
              help='Chart types to generate (auto-detect if not specified)')
@click.option('--responsive/--fixed', default=True,
              help='Make dashboard responsive')
def dashboard(data_file, output_file, title, theme, charts, responsive):
    """Generate an interactive dashboard from data."""
    
    console.print(Panel.fit("📊 [bold cyan]Dashboard Generator MCP[/bold cyan]", title="Starting"))
    
    # Read data file
    console.print(f"📄 Reading data from: [yellow]{data_file}[/yellow]")
    
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    # Create dashboard server
    dashboard_server = DashboardGeneratorMCPServer()
    
    # Prepare chart configurations if specified
    chart_configs = None
    if charts:
        chart_configs = []
        for chart_type in charts:
            chart_configs.append(ChartConfig(
                type=ChartType(chart_type),
                title=f"{title} - {chart_type.capitalize()} Chart",
                data=data
            ))
    
    # Create request
    from dashboard_generator_mcp.schema import DashboardConfig, ThemeType
    
    config = None
    if chart_configs:
        config = DashboardConfig(
            title=title,
            theme=ThemeType(theme),
            responsive=responsive,
            charts=chart_configs
        )
    
    request = DashboardGeneratorRequest(
        task="generate_dashboard",
        data=data,
        config=config,
        auto_detect=not bool(charts)
    )
    
    # Generate dashboard
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Generating dashboard...", total=None)
        response = dashboard_server.handle_request(request)
        progress.update(task, completed=True)
    
    if response.status == "error":
        console.print(f"[red]❌ Error: {response.error}[/red]")
        return
    
    # Save HTML
    if response.dashboard:
        with open(output_file, 'w') as f:
            f.write(response.dashboard.html)
        
        console.print(f"✅ Dashboard saved to: [green]{output_file}[/green]")
        
        # Display metadata
        if response.metadata:
            console.print(f"📈 Charts: {response.metadata.get('chart_count', 0)}")
            console.print(f"🎨 Theme: {response.metadata.get('theme', 'light')}")
            console.print(f"📱 Responsive: {'Yes' if response.metadata.get('responsive') else 'No'}")
    
    # Display instructions
    if response.instructions:
        console.print(Panel(response.instructions, title="📝 Next Steps", border_style="green"))


@cli.command()
@click.option('--schema', '-s', 'schema_file', required=True, type=click.Path(exists=True),
              help='DDL schema file')
@click.option('--data', '-d', 'data_file', required=True, type=click.Path(exists=True),
              help='JSON data file (query results)')
@click.option('--output', '-o', 'output_file', required=True, type=click.Path(),
              help='Output HTML dashboard file')
@click.option('--database', '-db', type=click.Choice(['sqlite', 'postgres', 'mysql']), default='sqlite',
              help='Database type')
def workflow(schema_file, data_file, output_file, database):
    """Complete workflow: Parse schema → Generate dashboard from data."""
    
    console.print(Panel.fit("🚀 [bold cyan]Complete SQL-to-Dashboard Workflow[/bold cyan]", title="Starting"))
    
    # Step 1: Parse schema
    console.print("\n[bold]Step 1:[/bold] Parsing schema...")
    
    with open(schema_file, 'r') as f:
        schema_content = f.read()
    
    parser_server = DDLParserMCPServer()
    parse_request = DDLParserRequest(
        task="parse_schema",
        input=schema_content,
        format=InputFormat.DDL,
        database_type=database
    )
    
    parse_response = parser_server.handle_request(parse_request)
    
    if parse_response.status == "error":
        console.print(f"[red]❌ Schema parsing failed: {parse_response.error}[/red]")
        return
    
    console.print(f"✅ Parsed {len(parse_response.schema.tables)} tables")
    
    # Display suggested queries
    if parse_response.suggested_queries:
        console.print(f"\n💡 Suggested queries for your schema:")
        for i, query in enumerate(parse_response.suggested_queries[:3], 1):
            console.print(f"  {i}. {query.description}")
    
    # Step 2: Generate dashboard
    console.print("\n[bold]Step 2:[/bold] Generating dashboard from data...")
    
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    dashboard_server = DashboardGeneratorMCPServer()
    dashboard_request = DashboardGeneratorRequest(
        task="generate_dashboard",
        data=data,
        auto_detect=True
    )
    
    dashboard_response = dashboard_server.handle_request(dashboard_request)
    
    if dashboard_response.status == "error":
        console.print(f"[red]❌ Dashboard generation failed: {dashboard_response.error}[/red]")
        return
    
    # Save dashboard
    with open(output_file, 'w') as f:
        f.write(dashboard_response.dashboard.html)
    
    console.print(f"\n✅ Dashboard saved to: [green]{output_file}[/green]")
    console.print("\n🎉 [bold green]Workflow complete![/bold green]")
    console.print(f"\n💡 Open [cyan]{output_file}[/cyan] in your browser to view the dashboard")


@cli.command()
@click.option('--schema', '-s', 'schema_file', required=True, type=click.Path(exists=True),
              help='DDL schema file')
@click.option('--intents', '-i', multiple=True, required=True,
              help='What insights you want (e.g., "sales trends", "customer analytics")')
@click.option('--output-dir', '-o', default='./output', type=click.Path(),
              help='Output directory for generated files')
@click.option('--database', '-d', type=click.Choice(['sqlite', 'postgres', 'mysql']), default='sqlite',
              help='Target database type')
def generate_all(schema_file, intents, output_dir, database):
    """Generate everything at once: query + dashboard template ready for data."""
    
    console.print(Panel.fit("🚀 [bold cyan]One-Shot SQL-to-Dashboard Generation[/bold cyan]", title="Starting"))
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Step 1: Parse schema and generate master query
    console.print("\n📋 Step 1: Parsing schema and generating master query...")
    
    with open(schema_file, 'r') as f:
        schema_content = f.read()
    
    parser_server = DDLParserMCPServer()
    parse_request = DDLParserRequest(
        task="parse_schema",
        input=schema_content,
        format=InputFormat.DDL,
        database_type=database,
        visualization_intents=list(intents)
    )
    
    parse_response = parser_server.handle_request(parse_request)
    
    if parse_response.status == "error":
        console.print(f"[red]❌ Schema parsing failed: {parse_response.error}[/red]")
        return
    
    console.print(f"✅ Schema parsed: {len(parse_response.schema.tables)} tables found")
    console.print(f"🤖 Business domain: {parse_response.metadata.get('business_analysis', {}).get('business_domain', 'Unknown')}")
    
    # Get the master query
    if not parse_response.suggested_queries:
        console.print("[red]❌ No queries generated[/red]")
        return
        
    master_query = parse_response.suggested_queries[0]
    
    # Save the query
    query_file = output_path / "master_query.sql"
    with open(query_file, 'w') as f:
        f.write(f"-- {master_query.description}\n")
        f.write(f"-- Result Key: {master_query.result_key}\n")
        f.write(f"-- Visualization Type: {master_query.visualization_type}\n\n")
        f.write(master_query.query)
    
    console.print(f"💾 Query saved to: [green]{query_file}[/green]")
    
    # Step 2: Generate dashboard template
    console.print("\n📋 Step 2: Generating dashboard template...")
    
    # Create a sample data structure that matches what the query would return
    sample_data = {
        "metadata": {
            "source": "master_query",
            "query_description": master_query.description,
            "visualization_intents": list(intents),
            "schema_tables": [t.name for t in parse_response.schema.tables],
            "expected_columns": master_query.expected_columns
        },
        "data": []  # Will be filled when query is executed
    }
    
    # Generate dashboard with placeholder for data
    dashboard_server = DashboardGeneratorMCPServer()
    dashboard_request = DashboardGeneratorRequest(
        task="generate_dashboard",
        data=[],  # Empty data - will be filled via JavaScript
        auto_detect=True,
        metadata={
            "title": f"Dashboard for {parse_response.metadata.get('business_analysis', {}).get('business_domain', 'Data')} Analytics",
            "description": f"Insights: {', '.join(intents)}",
            "data_source": "master_query",
            "expected_columns": master_query.expected_columns,
            "visualization_intents": list(intents),
            "note": "Load data.json to populate this dashboard"
        }
    )
    
    dashboard_response = dashboard_server.handle_request(dashboard_request)
    
    if dashboard_response.status == "error":
        console.print(f"[red]❌ Dashboard generation failed: {dashboard_response.error}[/red]")
        return
    
    # Modify dashboard HTML to load data dynamically
    dashboard_html = dashboard_response.dashboard.html
    
    # Insert data loading script
    data_loader_script = """
    <script>
    // Load data.json when available
    async function loadData() {
        try {
            const response = await fetch('data.json');
            const jsonData = await response.json();
            
            // Update visualizations with loaded data
            if (jsonData.data && jsonData.data.length > 0) {
                window.dashboardData = jsonData.data;
                
                // Trigger D3 visualizations update
                if (window.updateVisualizations) {
                    window.updateVisualizations(jsonData.data);
                }
                
                console.log(`Loaded ${jsonData.data.length} rows of data`);
            } else {
                console.log('No data found in data.json');
            }
        } catch (error) {
            console.log('Waiting for data.json...', error);
            // Retry after 2 seconds
            setTimeout(loadData, 2000);
        }
    }
    
    // Start loading when page is ready
    document.addEventListener('DOMContentLoaded', loadData);
    </script>
    """
    
    # Insert before closing body tag
    dashboard_html = dashboard_html.replace('</body>', f'{data_loader_script}</body>')
    
    # Save dashboard
    dashboard_file = output_path / "dashboard.html"
    with open(dashboard_file, 'w') as f:
        f.write(dashboard_html)
    
    console.print(f"🌐 Dashboard saved to: [green]{dashboard_file}[/green]")
    
    # Step 3: Create execution script
    console.print("\n📋 Step 3: Creating execution helper...")
    
    exec_script = f"""#!/bin/bash
# Execute the master query and save results as data.json

echo "🔧 Executing master query..."

# For SQLite example (adjust for your database)
sqlite3 your_database.db <<EOF
.mode json
.output {output_path}/data.json
{master_query.query}
EOF

echo "✅ Data saved to {output_path}/data.json"
echo "🌐 Open {output_path}/dashboard.html in your browser"
"""
    
    exec_file = output_path / "execute_query.sh"
    with open(exec_file, 'w') as f:
        f.write(exec_script)
    
    import os
    os.chmod(exec_file, 0o755)
    
    console.print(f"🔧 Execution script saved to: [green]{exec_file}[/green]")
    
    # Step 4: Create README with instructions
    readme_content = f"""# Generated Dashboard Package

## Files Generated:
- `master_query.sql` - The comprehensive query to get all data
- `dashboard.html` - Interactive D3.js dashboard (auto-loads data.json)
- `execute_query.sh` - Helper script to execute query
- `data.json` - (You need to create this by executing the query)

## How to Use:

### Option 1: Using the execution script
```bash
# Edit execute_query.sh to point to your database
./execute_query.sh
# Then open dashboard.html in your browser
```

### Option 2: Manual execution
1. Execute the query in `master_query.sql` against your database
2. Save the results as `data.json` in this directory
3. Open `dashboard.html` in your browser

## Query Details:
- **Description**: {master_query.description}
- **Database Type**: {database}
- **Visualization Intents**: {', '.join(intents)}
- **Tables Used**: {', '.join(master_query.tables_used) if master_query.tables_used else 'All tables'}

## Dashboard Features:
- Auto-loads data.json when available
- D3.js handles all visualizations
- Client-side data transformations
- Interactive filtering and grouping

## Notes:
The dashboard will automatically reload data.json every 2 seconds until it finds the file.
Once loaded, all visualizations will populate automatically.
"""
    
    readme_file = output_path / "README.md"
    with open(readme_file, 'w') as f:
        f.write(readme_content)
    
    console.print(f"📝 README saved to: [green]{readme_file}[/green]")
    
    # Display summary
    console.print(Panel(f"""
🎉 [bold green]Success! Everything generated in one shot![/bold green]

📁 Output directory: [cyan]{output_path}[/cyan]

✅ Generated files:
   • master_query.sql - Your comprehensive query
   • dashboard.html - Pre-configured D3.js dashboard
   • execute_query.sh - Query execution helper
   • README.md - Complete instructions

🚀 Next steps:
   1. Execute the query: [cyan]./output/execute_query.sh[/cyan]
   2. Open dashboard: [cyan]open ./output/dashboard.html[/cyan]
   
The dashboard will auto-load data.json and create all visualizations!
""", title="✨ Complete Package Generated", border_style="green"))


@cli.command()
def examples():
    """Show example usage and sample data formats."""
    
    console.print(Panel.fit("📚 [bold cyan]SQL-to-Dashboard Examples[/bold cyan]"))
    
    # Example DDL
    ddl_example = """CREATE TABLE sales (
    id INTEGER PRIMARY KEY,
    product_id INTEGER,
    quantity INTEGER,
    sale_date DATE,
    amount DECIMAL(10,2),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10,2)
);"""
    
    console.print("\n[bold]Example DDL Schema:[/bold]")
    syntax = Syntax(ddl_example, "sql", theme="monokai", line_numbers=True)
    console.print(syntax)
    
    # Example data
    data_example = """[
  {
    "category": "Electronics",
    "total_sales": 45000,
    "month": "2024-01"
  },
  {
    "category": "Clothing",
    "total_sales": 32000,
    "month": "2024-01"
  },
  {
    "category": "Electronics",
    "total_sales": 48000,
    "month": "2024-02"
  }
]"""
    
    console.print("\n[bold]Example Data (JSON):[/bold]")
    syntax = Syntax(data_example, "json", theme="monokai", line_numbers=True)
    console.print(syntax)
    
    # Example commands
    console.print("\n[bold]Example Commands:[/bold]")
    console.print("\n1. Parse schema and generate queries:")
    console.print("   [cyan]python client/mcp_client.py parse -i schema.sql -o queries.json[/cyan]")
    
    console.print("\n2. Generate dashboard from data:")
    console.print("   [cyan]python client/mcp_client.py dashboard -d data.json -o dashboard.html[/cyan]")
    
    console.print("\n3. Complete workflow:")
    console.print("   [cyan]python client/mcp_client.py workflow -s schema.sql -d data.json -o dashboard.html[/cyan]")
    
    console.print("\n[dim]For more help on any command, use: python client/mcp_client.py COMMAND --help[/dim]")


if __name__ == "__main__":
    cli()
