#!/bin/bash
# Execute the master query and save results as data.json

echo "🔧 Executing master query..."

# For SQLite example (adjust for your database)
sqlite3 your_database.db <<EOF
.mode json
.output test_output/data.json
SELECT * FROM customers LIMIT 10;
EOF

echo "✅ Data saved to test_output/data.json"
echo "🌐 Open test_output/dashboard.html in your browser"
