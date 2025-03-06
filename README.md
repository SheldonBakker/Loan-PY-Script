# Loan Payment Notification System

This script automates the process of sending loan payment notifications to clients with payments due next month, handling overdue loans, and applying penalties when necessary.

## Features

- Automatically sends payment quotes/invoices to clients with loans due next month
- Marks loans as overdue when payments are insufficient by the due date
- Applies 10% penalties to overdue loans on the 3rd of each month
- Sends overdue payment notifications with detailed payment information
- Sends payment reminders on the 22nd of each month
- Sends due date reminders on the 28th of each month
- Generates professional-looking email templates with company branding
- Provides comprehensive admin summary emails with detailed statistics
- Robust error handling and data validation for reliable operation
- Database connection testing and validation
- Advanced structured logging with JSON formatting and contextual data
- Log rotation and management for efficient storage
- Log analysis tools for monitoring and troubleshooting
- Can be run manually or automatically via GitHub Actions

## Setup

### Local Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   SUPABASE_URL=your-supabase-url
   SUPABASE_KEY=your-supabase-key
   
   SMTP_SERVER=your_smtp_server
   SMTP_PORT=your_smtp_port
   SMTP_USERNAME=your_smtp_username
   SMTP_PASSWORD=your_smtp_password
   ```
4. Run the script:
   ```
   python loans.py
   ```

### GitHub Actions Setup

This repository includes a GitHub Actions workflow that can run the script automatically or manually.

#### Setting up Secrets

For the GitHub Actions workflow to function properly, you need to add the following secrets to your repository:

1. Go to your repository on GitHub
2. Click on "Settings" > "Secrets and variables" > "Actions"
3. Click "New repository secret"
4. Add each of the following secrets:
   - `SUPABASE_URL`: Your Supabase URL
   - `SUPABASE_KEY`: Your Supabase API key
   - `SMTP_SERVER`: Your SMTP server address
   - `SMTP_PORT`: Your SMTP server port (typically 587)
   - `SMTP_USERNAME`: Your SMTP username
   - `SMTP_PASSWORD`: Your SMTP password

#### Schedule

The workflow is configured to run automatically on the 22nd day of each month at 8:00 AM SAST (South African Standard Time). This timing can be adjusted in the `.github/workflows/loan-process.yml` file.

#### Manual Trigger

You can also trigger the workflow manually:

1. Go to your repository on GitHub
2. Click on the "Actions" tab
3. Select the "Loan Payment Notification Process" workflow
4. Click "Run workflow"
5. Configure the options:
   - **Test mode**: When enabled, bypasses the date check
   - **Send emails**: When enabled, actually sends emails (otherwise just logs)
   - **Send admin summary**: When enabled, sends a summary email to the admin
   - **Apply penalties**: When enabled, applies penalties to overdue loans
6. Click "Run workflow" to start the process

## Command Line Arguments

The script supports the following command line arguments:

- `--test`: Run in test mode (bypasses date checks)
- `--no-send`: Don't send emails, just log what would be sent
- `--admin-summary`: Send admin summary email
- `--apply-penalties`: Force apply penalties to overdue loans (bypasses date check)
- `--payment-reminders`: Force send payment reminders (bypasses 22nd day check)
- `--due-date-reminders`: Force send due date reminders (bypasses 28th day check)
- `--check-db`: Check database connection and exit
- `--verbose`: Enable verbose logging for debugging

## Payment Structure

Each loan follows this payment structure:
1. The loan amount is divided into 3 equal monthly installments
2. Payments begin the month following the loan start date
3. Payment due dates are set to the 28th of each month
4. The system calculates and includes all payment dates in the invoice
5. Payments must meet or exceed the monthly installment amount to avoid being marked as overdue

## Reminder and Notification System

The system includes a comprehensive reminder and notification workflow:

1. **Payment Reminders (22nd of month)**:
   - Sent to all clients with payments due next month
   - Includes payment amount and due date
   - Provides clear instructions for payment

2. **Due Date Reminders (28th of month)**:
   - Sent to clients with payments due in the next few days
   - Includes urgency level based on proximity to due date
   - Shows payment status (paid/unpaid) and remaining amount due

3. **Overdue Detection**:
   - Loans are marked as overdue when:
     - The payment due date has passed
     - The total payments made in the current month are less than the required amount

4. **Penalty System**:
   - A 10% penalty based on the total loan amount is applied on the 3rd of each month
   - Penalties are only applied to loans that don't have sufficient payments
   - The penalty amount is clearly communicated to clients in overdue notifications

5. **Overdue Notifications**:
   - Overdue clients receive detailed notifications with:
     - The amount they've paid (if any)
     - The amount they should have paid
     - The penalty amount (if applied)
     - Clear instructions on how to avoid further penalties

## Quote vs. Invoice System

The system uses a clear document workflow:
1. **Quotes**: For active loans with pending payments, the system generates and sends **quotes** with the payment amount and due date.
2. **Invoices**: Only after a loan has been fully paid (status = 'paid'), the system generates and sends an **invoice** as a payment confirmation.

This approach provides clarity to clients about what they need to pay (quotes) and confirms what they have paid (invoices).

## Database Structure

The script works with the following database tables:

1. `loans` table with fields:
   - id (UUID, primary key)
   - client_id (UUID, foreign key)
   - license_id (UUID, foreign key)
   - invoice_number (text)
   - loan_amount (decimal)
   - remaining_balance (decimal)
   - interest_rate (decimal)
   - start_date (timestamp) - The date the loan was issued
   - payment_due_date (timestamp)
   - status (text: 'active', 'paid', 'overdue', 'defaulted')
   - penalties (decimal) - Accumulated penalties for overdue payments

2. `clients` table with fields:
   - id (UUID, primary key)
   - first_name (text)
   - last_name (text)
   - email (text)
   - phone (text)

3. `loan_payments` table with fields:
   - id (UUID, primary key)
   - loan_id (UUID, foreign key)
   - payment_date (timestamp)
   - amount (decimal)
   - penalties_paid (decimal)
   - payment_number (integer)
   - status (text: 'paid', 'due', 'overdue')

4. `gun_licences` table with fields:
   - id (UUID, primary key)
   - make (text)
   - type (text)
   - caliber (text)
   - serial_number (text)

## Error Handling and Resilience

The script includes comprehensive error handling to ensure reliable operation:

1. **Retry Mechanism with Exponential Backoff**:
   - Automatically retries failed operations with increasing delays
   - Configurable retry count, initial delay, and backoff factor
   - Targeted exception handling for specific error types

2. **Database Connection Validation**:
   - Checks database connectivity at startup
   - Verifies access to all required tables
   - Provides detailed error messages for connection issues

3. **Data Validation**:
   - Validates all required fields before processing
   - Handles missing or invalid data gracefully
   - Provides fallback values when possible

4. **Process Isolation**:
   - Each major function operates independently
   - Errors in one process don't affect others
   - Detailed logging of all errors for troubleshooting

5. **Email Delivery Reliability**:
   - Handles SMTP connection issues gracefully
   - Retries failed email deliveries
   - Logs all email successes and failures

## Structured Logging System

The script implements a comprehensive structured logging system:

1. **JSON-Formatted Logs**:
   - All logs are formatted as structured JSON objects
   - Includes standard fields like timestamp, level, module, function, line
   - Adds system metadata like hostname, app name, session ID
   - Includes operation-specific contextual data

2. **Log Rotation and Management**:
   - Automatic log rotation when files reach 10MB
   - Maintains 5 backup log files
   - Prevents logs from consuming excessive disk space

3. **Contextual Logging**:
   - Every log entry includes rich contextual information
   - Operation-specific fields for different types of actions
   - Standardized error reporting with error type and details
   - Performance metrics where applicable

4. **Log Analysis Tools**:
   - `log_analyzer.py` script for analyzing structured logs
   - Generates reports on errors, operations, emails, and database activity
   - Creates visualizations of system activity over time
   - Helps identify patterns and troubleshoot issues

5. **Integration with Monitoring Tools**:
   - JSON format compatible with ELK Stack, Grafana/Loki, Datadog, etc.
   - Enables real-time monitoring and alerting
   - Supports building custom dashboards

For more details on the structured logging system, see [STRUCTURED_LOGGING.md](STRUCTURED_LOGGING.md).

## Scheduling

For automated execution, set up a scheduled task (cron job on Linux/Mac or Task Scheduler on Windows) to run the script daily. The script will only perform its main functions on specific days:
- Payment reminders: 22nd of each month
- Due date reminders: 28th of each month
- Penalty application: 3rd of each month
- Overdue detection: Runs on every execution

### Cron Example (Linux/Mac)

```
0 9 * * * cd /path/to/script && python loans.py >> /path/to/logs/loans.log 2>&1
```

### Task Scheduler (Windows)

Create a task that:
1. Runs daily
2. Executes `python loans.py`
3. Starts in the script directory

## Troubleshooting

- Check logs for detailed error information
- Use the log analyzer to generate reports: `python log_analyzer.py logs/loan_system.log`
- Run with `--verbose` flag for more detailed logging
- Use `--check-db` to verify database connectivity
- Run with `--test --no-send` flags to debug without sending actual emails
- Verify database connection using the database connection test
- Ensure the SMTP server allows connections from your IP
- Check that all required environment variables are set correctly
