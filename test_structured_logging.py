#!/usr/bin/env python3
"""
Test script for structured logging in the loan management system.
"""

import os
import sys
import logging
import json
from datetime import datetime

# Import the setup_logging function from loans.py
from loans import setup_logging

def test_structured_logging():
    """Test the structured logging functionality."""
    # Initialize structured logging
    setup_logging()
    
    print("Testing structured logging...")
    
    # Test basic logging
    logging.info("Basic log message")
    
    # Test structured logging with context
    logging.info_with_context(
        "Structured log message with context",
        operation="test_logging",
        test_id="TEST-001",
        timestamp=datetime.now().isoformat()
    )
    
    # Test error logging with context
    try:
        # Simulate an error
        result = 1 / 0
    except Exception as e:
        logging.error_with_context(
            f"Error occurred: {e}",
            operation="test_error_logging",
            error_type=type(e).__name__,
            error=str(e)
        )
    
    # Test database operation logging
    logging.info_with_context(
        "Database query completed",
        operation="db_query",
        table="loans",
        record_count=42,
        query_duration_ms=15
    )
    
    # Test email operation logging
    logging.info_with_context(
        "Email sent successfully",
        operation="send_email",
        recipient="test@example.com",
        subject="Test Email",
        email_size=1024
    )
    
    # Check if log file was created
    log_file = "logs/loan_system.log"
    if os.path.exists(log_file):
        print(f"Log file created: {log_file}")
        
        # Read and display the first few log entries
        with open(log_file, 'r') as f:
            lines = f.readlines()
            print(f"\nFirst log entry (parsed):")
            try:
                first_log = json.loads(lines[0])
                print(json.dumps(first_log, indent=2))
            except (IndexError, json.JSONDecodeError) as e:
                print(f"Error parsing log: {e}")
    else:
        print(f"Log file not found: {log_file}")
    
    print("\nStructured logging test completed.")

if __name__ == "__main__":
    test_structured_logging() 