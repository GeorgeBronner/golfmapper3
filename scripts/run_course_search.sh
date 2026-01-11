#!/bin/bash

echo "Starting Golf Course Search Application..."
echo ""
echo "Database: ../dbs/golf_mapper_sqlite.db"
echo "Server will be available at: http://localhost:8888"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

python course_search_app.py
