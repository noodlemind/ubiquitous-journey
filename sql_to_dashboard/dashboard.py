"""Dashboard template generator with D3.js - Version 2.0"""


def generate_dashboard_html(title: str = "Data Dashboard", theme: str = "light") -> str:
    """
    Generate a complete dashboard HTML that auto-loads data.json.
    D3.js handles all visualizations and transformations client-side.
    """
    
    dark_mode_styles = """
        body.dark { background: #1a1a1a; color: #e0e0e0; }
        .dark .card { background: #2a2a2a; border-color: #444; }
        .dark h1, .dark h2 { color: #fff; }
    """ if theme == "dark" else ""
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ 
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        .dashboard {{ 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        .card:hover {{ transform: translateY(-5px); }}
        .card h2 {{ 
            color: #333;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        .loading {{
            text-align: center;
            padding: 100px;
            color: white;
            font-size: 1.5em;
        }}
        .error {{ 
            background: #ff6b6b;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px;
        }}
        svg {{ width: 100%; height: 300px; }}
        {dark_mode_styles}
    </style>
</head>
<body class="{theme}">
    <div class="container">
        <h1>📊 {title}</h1>
        <div id="loading" class="loading">
            <div>⏳ Loading data...</div>
            <div style="font-size: 0.8em; margin-top: 10px;">Waiting for data.json</div>
        </div>
        <div id="dashboard" class="dashboard" style="display: none;"></div>
        <div id="error" class="error" style="display: none;"></div>
    </div>

    <script>
        let data = [];
        let retryCount = 0;
        const maxRetries = 30; // Try for 60 seconds
        
        // Auto-load data.json
        async function loadData() {{
            try {{
                const response = await fetch('data.json');
                if (!response.ok) throw new Error('data.json not found');
                
                const jsonData = await response.json();
                data = jsonData.data || jsonData;
                
                if (Array.isArray(data) && data.length > 0) {{
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('dashboard').style.display = 'grid';
                    createVisualizations(data);
                }} else {{
                    throw new Error('No data in file');
                }}
            }} catch (error) {{
                retryCount++;
                if (retryCount < maxRetries) {{
                    setTimeout(loadData, 2000); // Retry every 2 seconds
                }} else {{
                    showError('Could not load data.json. Please ensure the query has been executed.');
                }}
            }}
        }}
        
        function showError(message) {{
            document.getElementById('loading').style.display = 'none';
            document.getElementById('error').style.display = 'block';
            document.getElementById('error').innerHTML = `❌ ${{message}}`;
        }}
        
        function createVisualizations(data) {{
            const dashboard = d3.select('#dashboard');
            dashboard.selectAll('*').remove();
            
            // Get column types
            const columns = Object.keys(data[0]);
            const numericCols = columns.filter(col => 
                data.some(d => !isNaN(parseFloat(d[col])) && isFinite(d[col]))
            );
            const categoricalCols = columns.filter(col => !numericCols.includes(col));
            const dateCols = columns.filter(col => 
                col.toLowerCase().includes('date') || col.toLowerCase().includes('time')
            );
            
            // 1. Summary Statistics Card
            createSummaryCard(dashboard, data, numericCols);
            
            // 2. Bar Chart - Top categories
            if (categoricalCols.length > 0 && numericCols.length > 0) {{
                createBarChart(dashboard, data, categoricalCols[0], numericCols[0]);
            }}
            
            // 3. Line Chart - Time series if dates exist
            if (dateCols.length > 0 && numericCols.length > 0) {{
                createLineChart(dashboard, data, dateCols[0], numericCols[0]);
            }}
            
            // 4. Pie Chart - Distribution
            if (categoricalCols.length > 0) {{
                createPieChart(dashboard, data, categoricalCols[0]);
            }}
            
            // 5. Data Table - Sample
            createDataTable(dashboard, data.slice(0, 10), columns);
        }}
        
        function createSummaryCard(container, data, numericCols) {{
            const card = container.append('div').attr('class', 'card');
            card.append('h2').text('📈 Summary Statistics');
            
            const stats = card.append('div');
            stats.append('p').html(`<strong>Total Records:</strong> ${{data.length.toLocaleString()}}`);
            
            numericCols.slice(0, 3).forEach(col => {{
                const values = data.map(d => parseFloat(d[col])).filter(v => !isNaN(v));
                if (values.length > 0) {{
                    const sum = d3.sum(values);
                    const avg = d3.mean(values);
                    stats.append('p').html(`<strong>${{col}}:</strong> Avg: ${{avg.toFixed(2)}}, Total: ${{sum.toFixed(2)}}`);
                }}
            }});
        }}
        
        function createBarChart(container, data, catCol, numCol) {{
            const card = container.append('div').attr('class', 'card');
            card.append('h2').text(`📊 ${{catCol}} by ${{numCol}}`);
            
            // Aggregate data
            const grouped = d3.rollup(data, 
                v => d3.sum(v, d => parseFloat(d[numCol]) || 0),
                d => d[catCol]
            );
            const chartData = Array.from(grouped, ([key, value]) => ({{key, value}}))
                .sort((a, b) => b.value - a.value)
                .slice(0, 10);
            
            const svg = card.append('svg');
            const margin = {{top: 20, right: 20, bottom: 40, left: 60}};
            const width = 400 - margin.left - margin.right;
            const height = 300 - margin.top - margin.bottom;
            
            const g = svg.append('g')
                .attr('transform', `translate(${{margin.left}},${{margin.top}})`);
            
            const x = d3.scaleBand()
                .domain(chartData.map(d => d.key))
                .range([0, width])
                .padding(0.1);
            
            const y = d3.scaleLinear()
                .domain([0, d3.max(chartData, d => d.value)])
                .range([height, 0]);
            
            g.selectAll('.bar')
                .data(chartData)
                .enter().append('rect')
                .attr('class', 'bar')
                .attr('x', d => x(d.key))
                .attr('y', d => y(d.value))
                .attr('width', x.bandwidth())
                .attr('height', d => height - y(d.value))
                .attr('fill', '#667eea');
            
            g.append('g')
                .attr('transform', `translate(0,${{height}})`)
                .call(d3.axisBottom(x));
            
            g.append('g')
                .call(d3.axisLeft(y));
        }}
        
        function createLineChart(container, data, dateCol, numCol) {{
            const card = container.append('div').attr('class', 'card');
            card.append('h2').text(`📈 ${{numCol}} over Time`);
            
            // Parse dates and aggregate
            const parseTime = d3.timeParse("%Y-%m-%d");
            const timeData = data.map(d => ({{
                date: parseTime(d[dateCol]) || new Date(d[dateCol]),
                value: parseFloat(d[numCol]) || 0
            }})).filter(d => d.date);
            
            if (timeData.length === 0) return;
            
            const svg = card.append('svg');
            const margin = {{top: 20, right: 20, bottom: 40, left: 60}};
            const width = 400 - margin.left - margin.right;
            const height = 300 - margin.top - margin.bottom;
            
            const g = svg.append('g')
                .attr('transform', `translate(${{margin.left}},${{margin.top}})`);
            
            const x = d3.scaleTime()
                .domain(d3.extent(timeData, d => d.date))
                .range([0, width]);
            
            const y = d3.scaleLinear()
                .domain([0, d3.max(timeData, d => d.value)])
                .range([height, 0]);
            
            const line = d3.line()
                .x(d => x(d.date))
                .y(d => y(d.value));
            
            g.append('path')
                .datum(timeData)
                .attr('fill', 'none')
                .attr('stroke', '#764ba2')
                .attr('stroke-width', 2)
                .attr('d', line);
            
            g.append('g')
                .attr('transform', `translate(0,${{height}})`)
                .call(d3.axisBottom(x));
            
            g.append('g')
                .call(d3.axisLeft(y));
        }}
        
        function createPieChart(container, data, catCol) {{
            const card = container.append('div').attr('class', 'card');
            card.append('h2').text(`🥧 ${{catCol}} Distribution`);
            
            const counts = d3.rollup(data, v => v.length, d => d[catCol]);
            const pieData = Array.from(counts, ([key, value]) => ({{key, value}}))
                .sort((a, b) => b.value - a.value)
                .slice(0, 8);
            
            const svg = card.append('svg');
            const width = 400;
            const height = 300;
            const radius = Math.min(width, height) / 2 - 20;
            
            const g = svg.append('g')
                .attr('transform', `translate(${{width/2}},${{height/2}})`);
            
            const color = d3.scaleOrdinal(d3.schemeCategory10);
            
            const pie = d3.pie().value(d => d.value);
            const arc = d3.arc().innerRadius(0).outerRadius(radius);
            
            const arcs = g.selectAll('.arc')
                .data(pie(pieData))
                .enter().append('g')
                .attr('class', 'arc');
            
            arcs.append('path')
                .attr('d', arc)
                .attr('fill', d => color(d.data.key));
            
            arcs.append('text')
                .attr('transform', d => `translate(${{arc.centroid(d)}})`)
                .attr('text-anchor', 'middle')
                .text(d => d.data.key);
        }}
        
        function createDataTable(container, data, columns) {{
            const card = container.append('div').attr('class', 'card');
            card.append('h2').text('📋 Sample Data (First 10 Rows)');
            
            const table = card.append('table')
                .style('width', '100%')
                .style('border-collapse', 'collapse');
            
            // Header
            table.append('thead').append('tr')
                .selectAll('th')
                .data(columns.slice(0, 5)) // Show first 5 columns
                .enter().append('th')
                .text(d => d)
                .style('border', '1px solid #ddd')
                .style('padding', '8px')
                .style('background', '#f4f4f4');
            
            // Rows
            table.append('tbody')
                .selectAll('tr')
                .data(data)
                .enter().append('tr')
                .selectAll('td')
                .data(d => columns.slice(0, 5).map(c => d[c]))
                .enter().append('td')
                .text(d => d)
                .style('border', '1px solid #ddd')
                .style('padding', '8px');
        }}
        
        // Start loading data
        loadData();
    </script>
</body>
</html>"""