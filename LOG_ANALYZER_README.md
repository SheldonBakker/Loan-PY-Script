# Log Analyzer for Loan Management System

A powerful tool for analyzing structured JSON logs produced by the loan management system. This tool helps you gain insights into system operations, track errors, monitor email deliveries, and analyze database activities.

## Features

- Parses structured JSON logs with rich contextual information
- Generates comprehensive reports on system operations
- Analyzes error patterns and frequencies
- Tracks email delivery success rates and recipients
- Monitors database operations and performance
- Creates visualizations of system activity over time (with matplotlib)
- Works with or without pandas/matplotlib dependencies
- Handles large log files efficiently

## Installation

### Prerequisites

- Python 3.6 or higher
- Optional dependencies for advanced features:
  - pandas (for advanced data analysis)
  - matplotlib (for visualizations)

### Setup

1. Clone the repository or download the log analyzer scripts
2. Install optional dependencies for advanced features:

```bash
pip install pandas matplotlib
```

## Usage

### Basic Usage

```bash
python simple_log_analyzer.py path/to/your/logfile.json
```

This will:
1. Load and parse the JSON log entries from your log file
2. Generate several reports in the current directory
3. Display a summary of the analysis process

### Command Line Options

```
usage: simple_log_analyzer.py [-h] [--output OUTPUT] [--debug] log_file

Simple log analyzer for loan management system

positional arguments:
  log_file              Path to the log file

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output directory for reports (default: current directory)
  --debug, -d           Enable debug output
```

### Advanced Usage (with pandas/matplotlib)

If you have pandas and matplotlib installed, you can use the full log analyzer which provides more advanced analysis and visualization:

```bash
python log_analyzer.py logs/loan_system.log --plot
```

Additional options for the full analyzer:

```
usage: log_analyzer.py [-h] [--output OUTPUT] [--plot] [--check-deps] [--debug] [log_file]

Analyze loan management system logs

positional arguments:
  log_file              Path to the log file

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output directory for reports
  --plot, -p            Generate plots
  --check-deps          Check dependencies and exit
  --debug, -d           Enable debug output
```

### Example Commands

Check if you have the required dependencies:
```bash
python log_analyzer.py --check-deps
```

Analyze logs with debug output:
```bash
python simple_log_analyzer.py logs/loan_system.log --debug
```

Generate reports in a specific directory:
```bash
python simple_log_analyzer.py logs/loan_system.log --output reports
```

Generate reports and visualizations:
```bash
python log_analyzer.py logs/loan_system.log --output reports --plot
```

## Generated Reports

### Simple Log Analyzer Reports

The simple log analyzer generates several report files:

1. **basic_report.txt**: Overview of log levels, operations, and recent errors
2. **email_report.txt**: Statistics about email operations, success rates, and recipients
3. **database_report.txt**: Information about database operations, error rates, and record counts

### Full Log Analyzer Reports (with pandas/matplotlib)

The full log analyzer generates additional reports:

1. **error_report.txt**: Detailed analysis of errors by type and operation
2. **operation_report.txt**: Comprehensive statistics on operations and success rates
3. **email_report.txt**: Detailed email delivery statistics and recipient analysis
4. **database_report.txt**: In-depth database operation analysis and performance metrics
5. **operations_over_time.png**: Visualization of operations frequency over time

## Example Report Contents

### Basic Report
```
=== BASIC LOG REPORT ===

Log Levels:
  INFO: 3
  ERROR: 2

Operations:
  send_email: 2
  check_database_connection: 1
  apply_penalty: 1
  db_query: 1

Error Types:
  SMTPError: 1
  ConnectionError: 1

Recent Errors:
  [2025-03-06 14:29:29,143] Error querying payments for loan LOAN-5678: Connection timeout
  [2025-03-06 14:29:27,141] Failed to send email: Connection refused
```

### Email Report
```
=== EMAIL REPORT ===
Total emails: 2
Successful emails: 1
Failed emails: 1

Top recipients:
  client@example.com: 1
  client2@example.com: 1
```

### Database Report
```
=== DATABASE REPORT ===
Database operations:
  check_database_connection: 1
  db_query: 1

Database error rate: 50.0% (1/2)

Record counts by table:
  loans: 2
```

## Log Format Requirements

The log analyzer expects logs in JSON format, with one complete JSON object per line. Each log entry should include the following fields:

- **timestamp**: When the log entry was created
- **level**: Log level (INFO, ERROR, WARNING, etc.)
- **message**: The log message
- **extra**: A nested object containing contextual information:
  - **operation**: The type of operation being performed
  - Additional context fields specific to the operation

Example log entry:
```json
{"timestamp": "2025-03-06 14:29:25,139", "level": "INFO", "logger": "root", "message": "Database connection test successful. Found 2 loans.", "module": "loans", "function": "check_loans_table", "line": 150, "hostname": "DESKTOP-ABC123", "app": "loan_management_system", "session_id": "550e8400-e29b-41d4-a716-446655440000", "extra": {"operation": "check_database_connection", "table": "loans", "record_count": 2}}
```

## Integrating with Your Workflow

### Scheduled Analysis

Set up a scheduled task to analyze logs daily:

#### Linux/Mac (cron)
```
0 7 * * * cd /path/to/scripts && python log_analyzer.py /path/to/logs/loan_system.log --output /path/to/reports
```

#### Windows (Task Scheduler)
Create a task that runs daily:
- Program: `python`
- Arguments: `log_analyzer.py C:\path\to\logs\loan_system.log --output C:\path\to\reports`
- Start in: `C:\path\to\scripts`

### Email Reports

Combine with an email script to send reports to administrators:

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

# First run the log analyzer
os.system('python log_analyzer.py logs/loan_system.log --output reports')

# Then email the reports
# ... (email sending code)
```

## Troubleshooting

### Common Issues

1. **Invalid JSON format**: Ensure your log file contains valid JSON entries, one per line
   ```bash
   python -c "import json; print(json.loads(open('logs/loan_system.log').readline()))"
   ```

2. **Missing dependencies**: Check if you have the required dependencies for advanced features
   ```bash
   python log_analyzer.py --check-deps
   ```

3. **Empty reports**: Verify that your log file contains the expected structured data
   ```bash
   python simple_log_analyzer.py logs/loan_system.log --debug
   ```

### Creating Test Logs

If you need to test the log analyzer with sample data, you can use the `test_structured_logging.py` script:

```bash
python test_structured_logging.py
```

This will generate sample log entries that can be used to test the analyzer.

## Advanced Analysis Techniques

### Filtering Logs Before Analysis

You can pre-filter your logs using standard command-line tools:

```bash
# Analyze only ERROR logs
grep '"level": "ERROR"' logs/loan_system.log > logs/errors_only.log
python log_analyzer.py logs/errors_only.log

# Analyze logs from a specific date range
grep '2025-03-06' logs/loan_system.log > logs/specific_date.log
python log_analyzer.py logs/specific_date.log

# Analyze specific operations
grep '"operation": "send_email"' logs/loan_system.log > logs/email_ops.log
python log_analyzer.py logs/email_ops.log
```

### Combining Multiple Log Files

You can combine multiple log files for analysis:

```bash
# Combine logs from multiple days
cat logs/loan_system_day1.log logs/loan_system_day2.log > logs/combined.log
python log_analyzer.py logs/combined.log
```

## Contributing

Contributions to the log analyzer are welcome! Here are some ways you can contribute:

1. Report bugs and issues
2. Suggest new features or improvements
3. Submit pull requests with bug fixes or new features
4. Improve documentation

## License

This project is licensed under the MIT License - see the LICENSE file for details. 