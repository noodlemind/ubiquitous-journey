# SQL to Dashboard v2.0 - Simplified Edition

Transform your database schema into interactive dashboards with a single command!

## 🚀 What's New in v2.0?

- **75% less code** - From 5,198 lines to just ~900 lines
- **Single command** - One command generates everything
- **One LLM call** - Efficient single-shot query generation  
- **D3.js powered** - All visualizations handled client-side
- **Zero complexity** - No validators, no parsers, just results

## 📦 Installation

```bash
# 1. Install dependencies
pip install click pydantic sqlglot requests

# 2. Ensure Ollama is running with llama3
ollama serve
ollama pull llama3
```

## 🎯 Usage

### Basic Usage

```bash
python client.py -s your_schema.sql -i "sales trends" -i "customer insights"
```

### Examples

```bash
# E-commerce dashboard
python client.py \
  -s examples/ecommerce.sql \
  -i "revenue analysis" \
  -i "customer segmentation" \
  -i "product performance"

# PostgreSQL database
python client.py \
  -s schema.sql \
  -i "key metrics" \
  -d postgres \
  -o ./dashboards

# Simple overview
python client.py -s schema.sql -i "overview"
```

## 📁 What Gets Generated?

Running the command creates these files in your output directory:

```
output/
├── query.sql        # Master SQL query joining all tables
├── dashboard.html   # Interactive D3.js dashboard
├── execute.sh       # Script to execute the query
└── README.md        # Instructions for your dashboard
```

## 🔄 Complete Workflow

```bash
# 1. Generate everything
python client.py -s schema.sql -i "analytics"

# 2. Execute the query
cd output
./execute.sh  # This creates data.json

# 3. View dashboard
open dashboard.html  # Opens in browser
```

The dashboard automatically loads `data.json` and creates visualizations!

## 🏗️ Architecture (Simplified!)

```
sql_to_dashboard_v2/
├── client.py      # CLI interface (172 lines)
├── server.py      # Unified server (254 lines)
├── llm.py         # LLM integration (135 lines)
├── dashboard.py   # Dashboard template (344 lines)
├── schemas.py     # Data models (26 lines)
└── test.py        # Test suite (153 lines)

Total: ~900 lines (was 5,198 lines in v1)
```

## 🎨 How It Works

1. **Parse DDL** - Extract table structure from your schema
2. **Generate Master Query** - One LLM call creates a comprehensive query
3. **Create Dashboard** - HTML template with D3.js for visualizations
4. **Execute & View** - Run query, dashboard auto-loads the data

### The Magic: Single Master Query

Instead of multiple complex queries, we generate ONE query that:
- JOINs all related tables
- Returns ALL columns (flat, denormalized)
- No aggregations (D3.js handles that)
- Limited to 10,000 rows for performance

D3.js then transforms this data into multiple visualizations client-side!

## 📊 Dashboard Features

The generated dashboard includes:
- **Summary Statistics** - Key metrics and totals
- **Bar Charts** - Category distributions
- **Line Charts** - Time series analysis
- **Pie Charts** - Proportional breakdowns
- **Data Table** - Sample of raw data
- **Auto-refresh** - Updates when data.json changes

## 🛠️ Customization

### Different Databases

```bash
# SQLite (default)
python client.py -s schema.sql -i "insights"

# PostgreSQL
python client.py -s schema.sql -i "insights" -d postgres

# MySQL
python client.py -s schema.sql -i "insights" -d mysql
```

### Custom Output Directory

```bash
python client.py -s schema.sql -i "insights" -o ./my-dashboards
```

## 🧪 Testing

```bash
# Run test suite
python test.py

# Test with sample schema
python server.py  # Runs built-in test
```

## 🤝 Contributing

This is the simplified version focused on what works. Key principles:
- Keep it simple
- One way to do things
- Minimal dependencies
- Clear, readable code

## 📝 License

MIT License - Use freely!

## 🙏 Credits

- **Ollama** - Local LLM inference
- **D3.js** - Data visualizations
- **SQLGlot** - SQL parsing
- **Click** - CLI framework

---

**v2.0 Philosophy:** *"Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away."* - Antoine de Saint-Exupéry