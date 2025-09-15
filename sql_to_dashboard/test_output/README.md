# Generated Dashboard Package

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
- **Description**: Comprehensive dataset for D3.js dashboard (all tables joined)
- **Database Type**: sqlite
- **Visualization Intents**: sales trends, customer segmentation, product performance
- **Tables Used**: customers

## Dashboard Features:
- Auto-loads data.json when available
- D3.js handles all visualizations
- Client-side data transformations
- Interactive filtering and grouping

## Notes:
The dashboard will automatically reload data.json every 2 seconds until it finds the file.
Once loaded, all visualizations will populate automatically.
