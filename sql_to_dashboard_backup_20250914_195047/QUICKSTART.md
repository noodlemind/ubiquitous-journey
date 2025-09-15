# 🚀 SQL-to-Dashboard Quick Start Guide

## Installation

1. **Install dependencies:**
```bash
cd sql_to_dashboard
pip install -r requirements.txt
```

## Basic Workflow

### Option 1: Using the CLI (Recommended)

#### Step 1: Parse your schema and get SQL queries
```bash
python client/mcp_client.py parse \
  --input examples/ecommerce_schema.sql \
  --output queries.json
```

This will:
- Parse your DDL schema
- Generate optimized SQL queries for visualizations
- Save queries to `queries.json`

#### Step 2: Execute queries in your database
Copy the generated SQL queries and run them in your database tool of choice:
- SQLite Browser
- pgAdmin (PostgreSQL)
- MySQL Workbench
- DBeaver (universal)
- Command line tools

Save the results as JSON format.

#### Step 3: Generate dashboard from data
```bash
python client/mcp_client.py dashboard \
  --data examples/sample_data.json \
  --output my_dashboard.html \
  --title "Sales Analytics Dashboard"
```

#### Step 4: View your dashboard
Open `my_dashboard.html` in any web browser!

### Option 2: Complete Workflow Command

If you have both schema and data ready:
```bash
python client/mcp_client.py workflow \
  --schema examples/ecommerce_schema.sql \
  --data examples/sample_data.json \
  --output dashboard.html
```

### Option 3: Python Script

```python
from ddl_parser_mcp import DDLParserMCPServer, DDLParserRequest, InputFormat
from dashboard_generator_mcp import DashboardGeneratorMCPServer, DashboardGeneratorRequest

# Parse schema
parser = DDLParserMCPServer()
parse_req = DDLParserRequest(
    task="parse_schema",
    input=open("schema.sql").read(),
    format=InputFormat.DDL,
    database_type="sqlite"
)
parse_resp = parser.handle_request(parse_req)

# Get SQL queries
for query in parse_resp.suggested_queries:
    print(f"{query.description}:\n{query.query}\n")

# Generate dashboard from data
dashboard = DashboardGeneratorMCPServer()
dash_req = DashboardGeneratorRequest(
    task="generate_dashboard",
    data=json.load(open("data.json")),
    auto_detect=True
)
dash_resp = dashboard.handle_request(dash_req)

# Save dashboard
with open("dashboard.html", "w") as f:
    f.write(dash_resp.dashboard.html)
```

## Examples

### View available examples:
```bash
python client/mcp_client.py examples
```

### Test with provided examples:
```bash
python test_workflow.py
```

This will create `test_dashboard.html` using the example e-commerce schema and sample data.

## Data Format

Your query results should be in JSON format:
```json
[
  {
    "column1": "value1",
    "column2": 123,
    "column3": "2024-01-15"
  },
  {
    "column1": "value2",
    "column2": 456,
    "column3": "2024-01-16"
  }
]
```

## Chart Types

The dashboard generator automatically detects the best chart type based on your data:

- **Bar Chart**: Categorical data with values
- **Line Chart**: Time series data
- **Pie Chart**: Distribution with few categories (≤8)
- **Table**: Raw data view
- **Scatter Plot**: Correlation between numeric values (coming soon)
- **Heatmap**: Matrix data (coming soon)

## Customization

### Specify chart types:
```bash
python client/mcp_client.py dashboard \
  --data data.json \
  --output dashboard.html \
  --charts bar --charts line --charts table
```

### Choose theme:
```bash
python client/mcp_client.py dashboard \
  --data data.json \
  --output dashboard.html \
  --theme dark
```

### Set responsive layout:
```bash
python client/mcp_client.py dashboard \
  --data data.json \
  --output dashboard.html \
  --responsive
```

## Tips

1. **Start simple**: Use the table visualization first to verify your data
2. **Clean data**: Ensure consistent column names and data types
3. **Limit rows**: For better performance, limit initial queries to <10,000 rows
4. **Use sampling**: For large datasets, use SQL sampling (e.g., `LIMIT`, `SAMPLE`)
5. **Save queries**: Keep successful queries for reuse

## Troubleshooting

### "No tables found in DDL"
- Check your DDL syntax
- Ensure CREATE TABLE statements are present
- Try simplifying complex DDL first

### "Data validation error"
- Verify JSON format is valid
- Check for consistent column names across rows
- Ensure data is an array of objects

### Dashboard not displaying correctly
- Check browser console for errors
- Verify D3.js is loading (requires internet for CDN)
- Try a different browser

## Next Steps

- Explore generated SQL queries to understand your data better
- Customize chart configurations in the code
- Combine multiple datasets in one dashboard
- Export dashboards as PDF from your browser
- Share HTML files with colleagues (they're standalone!)

## Need Help?

- Run `python client/mcp_client.py --help` for CLI options
- Check `examples/` directory for sample files
- Review the main README.md for architecture details

Happy dashboarding! 📊✨
