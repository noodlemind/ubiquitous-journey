# 🧠 Trip-Planner MCP Demo

A self-contained demo showing how Model Context Protocol (MCP) servers, agents, tools, and local LLMs work together to create a natural language travel assistant.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install and Start Ollama

#### Mac Installation (Homebrew)
```bash
# Install Ollama via Homebrew
brew install ollama

# Or download directly from https://ollama.ai
# curl -fsSL https://ollama.ai/install.sh | sh
```

#### Alternative Mac Installation (Direct Download)
```bash
# Download and install manually
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Start Ollama Service
```bash
# Start the Ollama service (runs in background)
ollama serve

# In a new terminal, download and run the llama3 model
ollama run llama3

# Verify installation
curl http://localhost:11434/api/tags
```

### 3. Start the Interactive CLI
```bash
# From the trip_planner_mcp directory
python client/mcp_client.py

# This will start an interactive session where you can type queries:
# Your query > weather in Kyoto
# Your query > 3-day Tokyo itinerary
# Your query > exit

# For one-off queries (old style):
python client/mcp_client.py query "weather in Kyoto" --verbose

# Get help
python client/mcp_client.py --help
```

## 📁 Project Structure

```
trip_planner_mcp/
├── mcp_server/          # MCP protocol handling
│   ├── server.py        # Main server logic
│   └── schema.py        # Request/Response models
├── agent/               # Agent with LLM reasoning
│   └── trip_planner_agent.py
├── tools/               # Data fetching tools
│   ├── weather_tool.py
│   ├── hotspot_tool.py
│   └── restaurant_tool.py
├── llm/                 # LLM integration
│   └── ollama_connector.py
├── client/              # CLI interface
│   └── mcp_client.py
├── data/                # Static JSON data
│   ├── weather/
│   ├── hotspots/
│   └── restaurants/
└── tests/               # Test suite
    └── test_end_to_end.py
```

## 🎯 Supported Queries

- **Weather**: `"weather in Kyoto"`, `"what's the temperature in Tokyo?"`
- **Attractions**: `"top temples in Kyoto"`, `"must-see places in Tokyo"`
- **Restaurants**: `"best ramen in Kyoto"`, `"where to eat sushi in Tokyo"`
- **Trip Planning**: `"3-day Kyoto itinerary"`, `"plan a weekend trip to Tokyo"`

## 🔧 How It Works

### Process Flow Diagram

```mermaid
graph TD
    A[👤 User Query<br/>"weather in Kyoto"] --> B[📱 CLI Client<br/>mcp_client.py]
    B --> C[🌐 MCP Server<br/>server.py]
    C --> D{📋 Request Validation<br/>- Length < 2000 chars<br/>- Valid task type<br/>- Non-empty query}
    
    D -->|❌ Invalid| E[🚫 Error Response<br/>400 Bad Request]
    D -->|✅ Valid| F[🧠 Trip Planner Agent<br/>trip_planner_agent.py]
    
    F --> G[🤖 LLM Classification<br/>Ollama + llama3]
    G --> H{🔍 Intent Detection<br/>+ JSON Cleaning}
    
    H -->|🌤️ weather_lookup| I[🌦️ Weather Tool<br/>data/weather/]
    H -->|🏛️ hotspots_list| J[🗺️ Hotspot Tool<br/>data/hotspots/]
    H -->|🍜 food_reco| K[🍽️ Restaurant Tool<br/>data/restaurants/]
    H -->|📅 trip_plan| L[🗓️ Trip Planning<br/>Multi-tool coordination]
    H -->|❓ unknown| M[🤷 Unknown Handler<br/>Clarification request]
    
    I --> N[🤖 LLM Response Formatting<br/>Ollama + llama3]
    J --> N
    K --> N
    L --> N
    M --> N
    
    N --> O[📤 MCP Response<br/>Structured output]
    O --> P[🖥️ CLI Display<br/>Rich formatting]
    P --> Q[👤 User sees result]
    
    style A fill:#e1f5fe
    style Q fill:#e8f5e8
    style G fill:#fff3e0
    style N fill:#fff3e0
    style H fill:#f3e5f5
```

### Step-by-Step Process

1. **User Query** → CLI client wraps query in MCPRequest
2. **MCP Server** → Validates request and passes to Agent
3. **Agent** → Uses Ollama to classify intent (weather/food/etc)
4. **JSON Cleaning** → Fixes malformed LLM responses with regex
5. **Tools** → Fetch relevant data from JSON files
6. **Agent** → Uses Ollama again to format natural response
7. **MCP Server** → Returns structured MCPResponse
8. **CLI** → Displays formatted result to user

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ -v --cov=.
```

## 📝 Adding New Cities

1. Create JSON files in `data/weather/`, `data/hotspots/`, and `data/restaurants/`
2. Follow the existing format (see Kyoto/Tokyo examples)
3. The tools will automatically detect new cities

## 🛠️ Troubleshooting

### Common Issues
- **"Ollama request failed"**: Make sure Ollama is running (`ollama run llama3`)
- **"Cannot connect to Ollama"**: Verify Ollama is running on localhost:11434
- **"Weather data not available"**: Check that city name matches JSON filename (kyoto.json, tokyo.json)
- **"City name is required"**: Make sure to specify a city in your query
- **Import errors**: Run from the `trip_planner_mcp` directory

### Error Handling Features
The demo includes comprehensive error handling:
- **Input validation**: Prevents malformed requests and excessive query lengths
- **Path sanitization**: Protects against directory traversal attacks
- **LLM timeouts**: 30-second timeout prevents hanging requests
- **JSON cleaning**: Regex-based cleaning fixes malformed LLM responses (NEW!)
- **Graceful degradation**: Provides fallback responses when LLM formatting fails
- **Data validation**: Ensures JSON files are properly formatted
- **Connection resilience**: Clear error messages for Ollama connectivity issues

### Recent Improvements
- **Fixed "Classification failed" errors**: Added robust JSON cleaning to handle malformed LLM responses
- **Enhanced reliability**: System now handles explanatory text in JSON values like `"city": "KYOTO" (capitalized)`
- **Better debugging**: Improved logging shows raw LLM responses and cleaned JSON

## 🎓 Learning Points

This demo teaches:
- How MCP servers wrap and structure requests
- How agents coordinate LLM reasoning with tool calls
- How to use local LLMs (Ollama) for both classification and generation
- How to build modular, testable architectures
- End-to-end flow with no external APIs required