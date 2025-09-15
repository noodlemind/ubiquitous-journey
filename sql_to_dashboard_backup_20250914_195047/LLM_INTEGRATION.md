# 🤖 LLM Integration for SQL-to-Dashboard

## Overview

The SQL-to-Dashboard system now includes powerful LLM (Large Language Model) integration using Ollama for local, privacy-preserving AI capabilities. This enhancement brings intelligent query generation, natural language processing, and smart visualization recommendations.

## 🌟 Key Features

### 1. **Intelligent SQL Generation**
- Convert natural language requests to SQL queries
- Understand business context from database schemas
- Generate optimized queries based on intent

### 2. **Business Context Analysis**
- Automatically detect business domain (e-commerce, finance, healthcare, etc.)
- Identify key entities and relationships
- Suggest relevant business metrics and KPIs

### 3. **Smart Visualization Recommendations**
- Analyze data patterns to recommend best chart types
- Suggest appropriate axes and groupings
- Provide reasoning for visualization choices

### 4. **Query Optimization**
- Analyze and improve existing SQL queries
- Suggest performance optimizations
- Recommend appropriate indexes

## 🚀 Quick Start

### Prerequisites

1. **Install Ollama**
   ```bash
   # macOS
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Start Ollama Service**
   ```bash
   ollama serve
   ```

3. **Pull a Model**
   ```bash
   # Recommended models
   ollama pull llama3       # Best overall performance
   ollama pull codellama    # Specialized for code
   ollama pull mistral      # Fast and efficient
   ```

4. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 📖 Usage Examples

### Basic Usage with LLM

```python
from ddl_parser_mcp.enhanced_server import EnhancedDDLParserMCPServer
from ddl_parser_mcp.schema import DDLParserRequest, InputFormat

# Initialize with LLM
server = EnhancedDDLParserMCPServer(use_llm=True, llm_model="llama3")

# Your DDL schema
ddl = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(255),
    country VARCHAR(50)
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    order_date DATE,
    total_amount DECIMAL(10,2),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
"""

# Create request
request = DDLParserRequest(
    task="parse_schema",
    input=ddl,
    format=InputFormat.DDL,
    database_type="sqlite",
    visualization_intents=["overview", "distribution", "time_series"]
)

# Process with LLM enhancement
response = server.handle_request(request)

# Access intelligent suggestions
for query in response.suggested_queries:
    print(f"Query: {query.description}")
    print(f"SQL: {query.query}")
    print(f"Visualization: {query.visualization_type}")
    print(f"Confidence: {query.metadata.get('confidence', 0):.0%}")
```

### Natural Language to SQL

```python
from llm.sql_intelligence import SQLIntelligenceAgent

# Initialize agent
agent = SQLIntelligenceAgent(llm_model="llama3")

# Your schema (as dict)
schema = {
    "tables": [...],  # Your table definitions
    "relationships": [...]  # Your relationships
}

# Natural language queries
queries = [
    "Show me top selling products by category",
    "Calculate monthly revenue growth",
    "Find customers who haven't ordered in 30 days",
    "What's the average order value by country?"
]

for nl_query in queries:
    query_plan = agent.generate_query_from_intent(nl_query, schema)
    print(f"Intent: {nl_query}")
    print(f"Generated SQL: {query_plan.query}")
    print(f"Explanation: {query_plan.explanation}")
```

### Smart Visualization Recommendations

```python
from llm.ollama_connector import OllamaConnector

connector = OllamaConnector()

# Your query results
data = [
    {"month": "2024-01", "sales": 45000, "category": "Electronics"},
    {"month": "2024-02", "sales": 48000, "category": "Electronics"},
    # ... more data
]

# Get visualization recommendation
recommendation = connector.recommend_visualization(
    data_sample=data,
    query_metadata={"intent_type": "time_series"}
)

print(f"Recommended Chart: {recommendation['primary']}")
print(f"Reason: {recommendation['reason']}")
print(f"X-Axis: {recommendation['x_axis']}")
print(f"Y-Axis: {recommendation['y_axis']}")
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_llm_integration.py
```

This will test:
- ✅ Ollama connection
- ✅ LLM connector functionality
- ✅ Schema analysis
- ✅ Natural language to SQL conversion
- ✅ Visualization recommendations
- ✅ Enhanced DDL parser

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│         User Request                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Enhanced DDL Parser             │
│  ┌─────────────────────────────┐    │
│  │   Schema Analysis (LLM)     │    │
│  └─────────────────────────────┘    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    SQL Intelligence Agent           │
│  ┌─────────────────────────────┐    │
│  │  Natural Language → SQL     │    │
│  │  Query Optimization         │    │
│  │  Business Context Analysis  │    │
│  └─────────────────────────────┘    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Ollama Connector               │
│  ┌─────────────────────────────┐    │
│  │   Local LLM (llama3, etc.)  │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

## 🔧 Configuration

### Environment Variables

```bash
# Ollama configuration
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="llama3"

# Enable/disable LLM features
export USE_LLM="true"

# LLM temperature (0.0-1.0, lower = more deterministic)
export LLM_TEMPERATURE="0.3"
```

### Supported Models

| Model | Size | Best For | Speed |
|-------|------|----------|-------|
| llama3 | 8B | General purpose, best quality | Medium |
| llama3:70b | 70B | Complex queries, highest quality | Slow |
| codellama | 7B | SQL and code generation | Fast |
| mistral | 7B | Quick responses, good quality | Fast |
| gemma:7b | 7B | Balanced performance | Medium |

## 📊 Performance Comparison

| Feature | Without LLM | With LLM |
|---------|------------|----------|
| Query Generation | Rule-based templates | Context-aware, intelligent |
| Business Understanding | None | Domain detection, entity recognition |
| Natural Language Support | ❌ | ✅ Full support |
| Visualization Selection | Basic heuristics | Data-driven recommendations |
| Query Optimization | ❌ | ✅ Performance suggestions |
| Adaptation | Fixed rules | Learns from context |

## 🛠️ Troubleshooting

### Common Issues

1. **Ollama not running**
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # Start Ollama
   ollama serve
   ```

2. **Model not available**
   ```bash
   # List available models
   ollama list
   
   # Pull required model
   ollama pull llama3
   ```

3. **Slow response times**
   - Use a smaller model (mistral, gemma:2b)
   - Reduce temperature for faster generation
   - Consider GPU acceleration if available

4. **Memory issues**
   - Use quantized models (e.g., llama3:7b-q4_0)
   - Limit context window size
   - Close other applications

## 🔒 Privacy & Security

- **100% Local**: All LLM processing happens on your machine
- **No Data Sharing**: Your schemas and queries never leave your system
- **Secure by Design**: No external API calls or cloud dependencies
- **Compliance Ready**: Suitable for sensitive business data

## 🚧 Roadmap

- [ ] Support for more LLM providers (OpenAI, Anthropic)
- [ ] Fine-tuning on SQL datasets
- [ ] Query result caching
- [ ] Multi-model ensemble for better accuracy
- [ ] Interactive query refinement
- [ ] Automatic dashboard layout generation

## 📚 Resources

- [Ollama Documentation](https://ollama.ai/docs)
- [Model Library](https://ollama.ai/library)
- [SQL Best Practices](https://www.sqlstyle.guide/)
- [D3.js Visualization Guide](https://d3js.org/)

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional LLM providers
- Better prompt engineering
- More visualization types
- Performance optimizations
- Test coverage

## 📄 License

MIT License - See LICENSE file for details