#!/usr/bin/env python3
"""
Simple Log Analyzer for Loan Management System

This script analyzes the structured JSON logs produced by the loan management system
and generates basic reports without requiring pandas or matplotlib.
"""

import os
import json
import argparse
from datetime import datetime
from collections import Counter, defaultdict

def load_logs(log_file):
    """Load JSON logs from file into a list of dictionaries."""
    logs = []
    line_count = 0
    error_count = 0
    
    print(f"Opening log file: {log_file}")
    with open(log_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line_count += 1
            try:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                log_entry = json.loads(line)
                logs.append(log_entry)
            except json.JSONDecodeError as e:
                error_count += 1
                print(f"Error parsing line {line_num}: {e}")
                print(f"Line content: {line[:100]}...")
                # Skip lines that aren't valid JSON
                continue
    
    print(f"Processed {line_count} lines, found {len(logs)} valid log entries, {error_count} errors")
    return logs

def get_nested_value(log, path):
    """Safely get a nested value from a dictionary using a path."""
    current = log
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

def generate_basic_report(logs):
    """Generate a basic report without pandas."""
    # Count log levels
    levels = Counter(log.get('level') for log in logs if 'level' in log)
    
    # Count operations
    operations = Counter(
        get_nested_value(log, ['extra', 'operation']) 
        for log in logs
    )
    
    # Count errors
    errors = [log for log in logs if log.get('level') == 'ERROR']
    error_types = Counter(
        get_nested_value(log, ['extra', 'error_type']) 
        for log in errors
    )
    
    # Generate report
    report = "=== BASIC LOG REPORT ===\n\n"
    
    report += "Log Levels:\n"
    for level, count in levels.items():
        if level:
            report += f"  {level}: {count}\n"
    report += "\n"
    
    report += "Operations:\n"
    for operation, count in operations.most_common(10):
        if operation:
            report += f"  {operation}: {count}\n"
    report += "\n"
    
    report += "Error Types:\n"
    for error_type, count in error_types.most_common():
        if error_type:
            report += f"  {error_type}: {count}\n"
    report += "\n"
    
    report += "Recent Errors:\n"
    # Sort errors by timestamp if available
    try:
        recent_errors = sorted(
            errors, 
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )[:5]
    except (ValueError, AttributeError):
        recent_errors = errors[:5]
        
    for error in recent_errors:
        timestamp = error.get('timestamp', 'Unknown time')
        message = error.get('message', 'No message')
        report += f"  [{timestamp}] {message}\n"
    
    return report

def generate_email_report(logs):
    """Generate a report of email operations."""
    email_logs = [log for log in logs if get_nested_value(log, ['extra', 'operation']) == 'send_email']
    
    if not email_logs:
        return "No email operations found in logs."
    
    report = "=== EMAIL REPORT ===\n"
    report += f"Total emails: {len(email_logs)}\n"
    
    # Count emails by success/failure
    success_count = len([log for log in email_logs if log.get('level') == 'INFO'])
    error_count = len([log for log in email_logs if log.get('level') == 'ERROR'])
    report += f"Successful emails: {success_count}\n"
    report += f"Failed emails: {error_count}\n"
    
    # Most common recipients
    recipients = Counter(get_nested_value(log, ['extra', 'recipient']) for log in email_logs)
    report += "\nTop recipients:\n"
    for recipient, count in recipients.most_common(5):
        if recipient:
            report += f"  {recipient}: {count}\n"
    
    return report

def generate_database_report(logs):
    """Generate a report of database operations."""
    db_ops = ['check_database_connection', 'check_loans_table', 'query_loans', 'query_payments', 'db_query']
    db_logs = [log for log in logs if get_nested_value(log, ['extra', 'operation']) in db_ops]
    
    if not db_logs:
        return "No database operation information found in logs."
    
    report = "=== DATABASE REPORT ===\n"
    
    # Count operations by type
    operations = Counter(get_nested_value(log, ['extra', 'operation']) for log in db_logs)
    report += "Database operations:\n"
    for operation, count in operations.most_common():
        if operation:
            report += f"  {operation}: {count}\n"
    report += "\n"
    
    # Error rate
    error_count = len([log for log in db_logs if log.get('level') == 'ERROR'])
    total_count = len(db_logs)
    error_rate = (error_count / total_count) * 100 if total_count > 0 else 0
    report += f"Database error rate: {error_rate:.1f}% ({error_count}/{total_count})\n"
    
    # Record counts if available
    table_counts = defaultdict(int)
    for log in db_logs:
        table = get_nested_value(log, ['extra', 'table'])
        record_count = get_nested_value(log, ['extra', 'record_count'])
        if table and record_count is not None:
            table_counts[table] = max(table_counts[table], record_count)
    
    if table_counts:
        report += "\nRecord counts by table:\n"
        for table, count in sorted(table_counts.items()):
            report += f"  {table}: {count}\n"
    
    return report

def main():
    parser = argparse.ArgumentParser(description='Simple log analyzer for loan management system')
    parser.add_argument('log_file', help='Path to the log file')
    parser.add_argument('--output', '-o', help='Output directory for reports', default='.')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    
    # Enable more verbose output if debug is enabled
    if args.debug:
        print("Debug mode enabled")
    
    # Check if log file exists
    if not os.path.exists(args.log_file):
        print(f"Error: Log file {args.log_file} not found.")
        return 1
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    if args.debug:
        print(f"Output directory: {os.path.abspath(args.output)}")
    
    # Load and process logs
    print(f"Loading logs from {args.log_file}...")
    logs = load_logs(args.log_file)
    print(f"Loaded {len(logs)} log entries.")
    
    if not logs:
        print("No logs found. Exiting.")
        return 1
    
    # Print sample log entry if in debug mode
    if args.debug and logs:
        print("\nSample log entry:")
        print(json.dumps(logs[0], indent=2))
    
    # Generate reports
    try:
        reports = {
            'basic_report.txt': generate_basic_report(logs),
            'email_report.txt': generate_email_report(logs),
            'database_report.txt': generate_database_report(logs)
        }
        
        # Write reports to files
        for filename, content in reports.items():
            output_path = os.path.join(args.output, filename)
            with open(output_path, 'w') as f:
                f.write(content)
            print(f"Wrote report to {output_path}")
            
            # Print report summary if in debug mode
            if args.debug:
                print(f"\nSummary of {filename}:")
                print(content.split('\n\n')[0])
                print("...")
        
        print("Analysis complete.")
        return 0
    except Exception as e:
        print(f"Error generating reports: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 