#!/usr/bin/env python3
"""
Log Analyzer for Loan Management System

This script analyzes the structured JSON logs produced by the loan management system
and generates reports and insights.
"""

import os
import json
import argparse
from datetime import datetime, timedelta
from collections import Counter
import sys

# Check for required dependencies and provide helpful error messages
MISSING_DEPENDENCIES = []

try:
    import pandas as pd
except ImportError:
    MISSING_DEPENDENCIES.append("pandas")

try:
    import matplotlib.pyplot as plt
except ImportError:
    MISSING_DEPENDENCIES.append("matplotlib")

def check_dependencies():
    """Check if all required dependencies are installed."""
    if MISSING_DEPENDENCIES:
        print("Error: Missing required dependencies.")
        print("Please install the following packages:")
        for dep in MISSING_DEPENDENCIES:
            print(f"  - {dep}")
        print("\nYou can install them using pip:")
        print(f"  pip install {' '.join(MISSING_DEPENDENCIES)}")
        print("\nOr install all dependencies with:")
        print("  pip install -r requirements.txt")
        return False
    return True

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

def convert_to_dataframe(logs):
    """Convert logs to a pandas DataFrame for easier analysis."""
    if "pandas" in MISSING_DEPENDENCIES:
        print("Error: Cannot convert logs to DataFrame without pandas.")
        return None
        
    # Flatten nested structures
    flattened_logs = []
    for log in logs:
        flat_log = {
            'timestamp': log.get('timestamp'),
            'level': log.get('level'),
            'message': log.get('message'),
            'module': log.get('module'),
            'function': log.get('function'),
            'line': log.get('line'),
            'session_id': log.get('session_id')
        }
        
        # Add extra fields if they exist
        if 'extra' in log:
            for key, value in log['extra'].items():
                # Handle nested dictionaries in extra
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        flat_log[f"{key}_{subkey}"] = subvalue
                else:
                    flat_log[key] = value
        
        flattened_logs.append(flat_log)
    
    # Create DataFrame
    df = pd.DataFrame(flattened_logs)
    
    # Convert timestamp to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    return df

def generate_basic_report(logs):
    """Generate a basic report without pandas."""
    # Count log levels
    levels = Counter(log.get('level') for log in logs if 'level' in log)
    
    # Count operations
    operations = Counter(
        log.get('extra', {}).get('operation') 
        for log in logs 
        if 'extra' in log and 'operation' in log['extra']
    )
    
    # Count errors
    errors = [log for log in logs if log.get('level') == 'ERROR']
    error_types = Counter(
        log.get('extra', {}).get('error_type') 
        for log in errors 
        if 'extra' in log and 'error_type' in log['extra']
    )
    
    # Generate report
    report = "=== BASIC LOG REPORT ===\n\n"
    
    report += "Log Levels:\n"
    for level, count in levels.items():
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
            key=lambda x: datetime.fromisoformat(x.get('timestamp').replace(',', '.')) if x.get('timestamp') else datetime.min,
            reverse=True
        )[:5]
    except (ValueError, AttributeError):
        recent_errors = errors[:5]
        
    for error in recent_errors:
        timestamp = error.get('timestamp', 'Unknown time')
        message = error.get('message', 'No message')
        report += f"  [{timestamp}] {message}\n"
    
    return report

def generate_error_report(df):
    """Generate a report of errors."""
    if df is None:
        return "Cannot generate error report without pandas."
        
    if 'level' not in df.columns:
        return "No log level information found in logs."
    
    error_logs = df[df['level'] == 'ERROR']
    if error_logs.empty:
        return "No errors found in logs."
    
    report = "=== ERROR REPORT ===\n"
    report += f"Total errors: {len(error_logs)}\n\n"
    
    # Group errors by type
    if 'error_type' in error_logs.columns:
        error_types = error_logs['error_type'].value_counts()
        report += "Error types:\n"
        for error_type, count in error_types.items():
            report += f"  {error_type}: {count}\n"
        report += "\n"
    
    # Group errors by operation
    if 'operation' in error_logs.columns:
        operations = error_logs['operation'].value_counts()
        report += "Operations with errors:\n"
        for operation, count in operations.items():
            report += f"  {operation}: {count}\n"
        report += "\n"
    
    # Most recent errors
    report += "Most recent errors:\n"
    for _, row in error_logs.sort_values('timestamp', ascending=False).head(5).iterrows():
        report += f"  [{row.get('timestamp')}] {row.get('message')}\n"
    
    return report

def generate_operation_report(df):
    """Generate a report of operations."""
    if df is None:
        return "Cannot generate operation report without pandas."
        
    if 'operation' not in df.columns:
        return "No operation information found in logs."
    
    report = "=== OPERATION REPORT ===\n"
    
    # Count operations
    operations = df['operation'].value_counts()
    report += "Operations count:\n"
    for operation, count in operations.items():
        report += f"  {operation}: {count}\n"
    report += "\n"
    
    # Success rate by operation
    if 'success' in df.columns:
        report += "Operation success rates:\n"
        for operation in operations.index:
            op_logs = df[df['operation'] == operation]
            success_count = op_logs[op_logs['success'] == True].shape[0]
            total_count = op_logs.shape[0]
            success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
            report += f"  {operation}: {success_rate:.1f}% ({success_count}/{total_count})\n"
        report += "\n"
    
    return report

def generate_email_report(df):
    """Generate a report of email operations."""
    if df is None:
        return "Cannot generate email report without pandas."
        
    if 'operation' not in df.columns or 'recipient' not in df.columns:
        return "No email information found in logs."
    
    email_logs = df[df['operation'] == 'send_email']
    if email_logs.empty:
        return "No email operations found in logs."
    
    report = "=== EMAIL REPORT ===\n"
    report += f"Total emails: {len(email_logs)}\n"
    
    # Count emails by success/failure
    success_count = email_logs[email_logs['level'] == 'INFO'].shape[0]
    error_count = email_logs[email_logs['level'] == 'ERROR'].shape[0]
    report += f"Successful emails: {success_count}\n"
    report += f"Failed emails: {error_count}\n"
    
    # Most common recipients
    recipients = email_logs['recipient'].value_counts().head(5)
    report += "\nTop recipients:\n"
    for recipient, count in recipients.items():
        report += f"  {recipient}: {count}\n"
    
    return report

def generate_database_report(df):
    """Generate a report of database operations."""
    if df is None:
        return "Cannot generate database report without pandas."
        
    db_ops = ['check_database_connection', 'check_loans_table', 'query_loans', 'query_payments']
    db_logs = df[df['operation'].isin(db_ops)]
    
    if db_logs.empty:
        return "No database operation information found in logs."
    
    report = "=== DATABASE REPORT ===\n"
    
    # Count operations by type
    operations = db_logs['operation'].value_counts()
    report += "Database operations:\n"
    for operation, count in operations.items():
        report += f"  {operation}: {count}\n"
    report += "\n"
    
    # Error rate
    error_count = db_logs[db_logs['level'] == 'ERROR'].shape[0]
    total_count = db_logs.shape[0]
    error_rate = (error_count / total_count) * 100 if total_count > 0 else 0
    report += f"Database error rate: {error_rate:.1f}% ({error_count}/{total_count})\n"
    
    # Record counts if available
    if 'record_count' in db_logs.columns:
        record_counts = db_logs.groupby('table')['record_count'].max()
        if not record_counts.empty:
            report += "\nRecord counts by table:\n"
            for table, count in record_counts.items():
                report += f"  {table}: {count}\n"
    
    return report

def plot_operations_over_time(df, output_file):
    """Plot operations over time."""
    if "matplotlib" in MISSING_DEPENDENCIES or df is None:
        return "Cannot generate plot without matplotlib and pandas."
        
    if 'timestamp' not in df.columns or 'operation' not in df.columns:
        return "Cannot generate plot: missing timestamp or operation data."
    
    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # Group by hour and operation
    df['hour'] = df['timestamp'].dt.floor('H')
    hourly_ops = df.groupby(['hour', 'operation']).size().unstack().fillna(0)
    
    # Plot
    plt.figure(figsize=(12, 6))
    hourly_ops.plot(kind='line', ax=plt.gca())
    plt.title('Operations Over Time')
    plt.xlabel('Time')
    plt.ylabel('Count')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file)
    
    return f"Plot saved to {output_file}"

def main():
    parser = argparse.ArgumentParser(description='Analyze loan management system logs')
    parser.add_argument('log_file', nargs='?', help='Path to the log file')
    parser.add_argument('--output', '-o', help='Output directory for reports', default='.')
    parser.add_argument('--plot', '-p', action='store_true', help='Generate plots')
    parser.add_argument('--check-deps', action='store_true', help='Check dependencies and exit')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    
    # Enable more verbose output if debug is enabled
    if args.debug:
        print("Debug mode enabled")
    
    # Check dependencies if requested
    if args.check_deps:
        if check_dependencies():
            print("All dependencies are installed.")
            return 0
        else:
            return 1
    
    # Check if log file is provided
    if not args.log_file:
        parser.print_help()
        print("\nError: Log file path is required.")
        return 1
    
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
    
    # Check dependencies for advanced analysis
    if not check_dependencies():
        print("\nFalling back to basic analysis without pandas and matplotlib.")
        try:
            basic_report = generate_basic_report(logs)
            output_path = os.path.join(args.output, 'basic_report.txt')
            with open(output_path, 'w') as f:
                f.write(basic_report)
            print(f"Wrote basic report to {output_path}")
        except Exception as e:
            print(f"Error generating basic report: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
        return 1
    
    # Convert to DataFrame
    try:
        df = convert_to_dataframe(logs)
        if args.debug:
            print("\nDataFrame info:")
            print(f"Shape: {df.shape}")
            print(f"Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Error converting logs to DataFrame: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    # Generate reports
    reports = {
        'error_report.txt': generate_error_report(df),
        'operation_report.txt': generate_operation_report(df),
        'email_report.txt': generate_email_report(df),
        'database_report.txt': generate_database_report(df)
    }
    
    # Write reports to files
    for filename, content in reports.items():
        try:
            output_path = os.path.join(args.output, filename)
            with open(output_path, 'w') as f:
                f.write(content)
            print(f"Wrote report to {output_path}")
        except Exception as e:
            print(f"Error writing {filename}: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
    
    # Generate plots if requested
    if args.plot:
        try:
            plot_file = os.path.join(args.output, 'operations_over_time.png')
            result = plot_operations_over_time(df, plot_file)
            print(result)
        except Exception as e:
            print(f"Error generating plot: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
    
    print("Analysis complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 