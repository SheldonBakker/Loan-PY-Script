import os
import logging
import calendar
import argparse
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from supabase import create_client, Client
import time
import json
from logging.handlers import RotatingFileHandler
import uuid
import socket
import platform
import sys

# Import the template functions

def setup_logging():
    """Configure structured logging with rotation."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    class JsonFormatter(logging.Formatter):
        """Format log records as JSON objects."""
        def __init__(self):
            super().__init__()
            self.hostname = socket.gethostname()
            self.app_name = "loan_management_system"
            self.session_id = str(uuid.uuid4())
            self.platform_info = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "python": sys.version
            }
        
        def format(self, record):
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "hostname": self.hostname,
                "app": self.app_name,
                "session_id": self.session_id,
                "platform": self.platform_info
            }
            
            # Add extra contextual information if available
            if hasattr(record, 'extra'):
                log_record.update(record.extra)
                
            # Add exception info if available
            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)
                
            return json.dumps(log_record)
    
    # Set up file handler with rotation (10MB max size, keep 5 backup files)
    file_handler = RotatingFileHandler(
        'logs/loan_system.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(JsonFormatter())
    file_handler.setLevel(logging.INFO)
    
    # Set up console handler with standard formatting for readability
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Add our handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Create a logger function that adds context
    def log_with_context(level, message, **context):
        """
        Log a message with additional context.
        
        Args:
            level: Logging level (e.g., logging.INFO, logging.ERROR)
            message: The log message
            **context: Additional contextual information to include in the log
        """
        extra = {'extra': context}
        logging.log(level, message, extra=extra)
    
    # Add convenience methods to the logging module
    logging.info_with_context = lambda message, **context: log_with_context(logging.INFO, message, **context)
    logging.error_with_context = lambda message, **context: log_with_context(logging.ERROR, message, **context)
    logging.warning_with_context = lambda message, **context: log_with_context(logging.WARNING, message, **context)
    logging.debug_with_context = lambda message, **context: log_with_context(logging.DEBUG, message, **context)
    
    logging.info("Structured logging initialized")

def retry_with_backoff(func, max_retries=3, initial_delay=1, backoff_factor=2, exceptions_to_retry=(Exception,)):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions_to_retry: Tuple of exceptions that should trigger a retry
    
    Returns:
        Result of the function call
    
    Raises:
        The last exception encountered if all retries fail
    """
    retries = 0
    delay = initial_delay
    last_exception = None
    
    while retries < max_retries:
        try:
            return func()
        except exceptions_to_retry as e:
            retries += 1
            last_exception = e
            
            if retries >= max_retries:
                logging.error_with_context(
                    f"Maximum retries ({max_retries}) reached. Last error: {e}",
                    operation="retry_with_backoff",
                    function=func.__name__,
                    retry_count=retries,
                    max_retries=max_retries,
                    error=str(e)
                )
                break
                
            wait_time = delay * (backoff_factor ** (retries - 1))
            logging.warning_with_context(
                f"Retry {retries}/{max_retries} after error: {e}. Waiting {wait_time:.2f}s before next attempt.",
                operation="retry_with_backoff",
                function=func.__name__,
                retry_count=retries,
                max_retries=max_retries,
                wait_time=wait_time,
                error=str(e)
            )
            time.sleep(wait_time)
    
    if last_exception:
        raise last_exception
    
    return None

# Call setup_logging instead of basicConfig
setup_logging()

# Load environment variables from .env file
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("URL and KEY must be set in the environment variables.")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# SMTP credentials
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = "accounts@gunneryguns.com"
ADMIN_EMAIL = "acum3n@protonmail.com"

def send_email(recipient_email: str, email_subject: str, email_body: str) -> None:
    """
    Send an HTML email using SMTP.
    
    Args:
        recipient_email: Email recipient
        email_subject: Email subject line
        email_body: HTML content of the email
    """
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient_email
        msg["Subject"] = email_subject

        # Attach HTML body
        msg.attach(MIMEText(email_body, "html"))

        def send_smtp_email():
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
            return True
        
        # Use retry mechanism for SMTP operations
        retry_with_backoff(
            send_smtp_email,
            max_retries=3,
            initial_delay=2,
            exceptions_to_retry=(
                smtplib.SMTPException, 
                ConnectionError, 
                TimeoutError
            )
        )
            
        logging.info_with_context(
            f"Email sent to {recipient_email}",
            operation="send_email",
            recipient=recipient_email,
            subject=email_subject,
            email_size=len(email_body),
            smtp_server=SMTP_SERVER
        )
    except Exception as e:
        logging.error_with_context(
            f"Failed to send email: {e}",
            operation="send_email",
            recipient=recipient_email,
            subject=email_subject,
            error=str(e),
            error_type=type(e).__name__
        )
        raise

def is_third_last_day_of_month() -> bool:
    """Check if today is the 3rd last day of the month."""
    today = datetime.now()
    # Get the last day of the current month
    last_day = calendar.monthrange(today.year, today.month)[1]
    # Calculate the 3rd last day
    third_last_day = last_day - 2
    
    return today.day == third_last_day

def is_22nd_of_month() -> bool:
    """Check if today is the 22nd day of the month."""
    today = datetime.now()
    return today.day == 22

def is_28th_of_month() -> bool:
    """Check if today is the 28th day of the month."""
    today = datetime.now()
    return today.day == 28

def check_loans_table():
    """Check if the loans table exists and has data."""
    try:
        # Define function to query loans table
        def query_loans_table():
            return supabase.table('loans').select('count', count='exact').limit(1).execute()
        
        # Use retry mechanism for database query
        response = retry_with_backoff(query_loans_table, max_retries=3, initial_delay=1)
        
        logging.info_with_context(
            f"Found {response.count} loans in the database",
            operation="check_loans_table",
            record_count=response.count
        )
        return response.count > 0
    except Exception as e:
        logging.error_with_context(
            f"Error checking loans table: {e}",
            operation="check_loans_table",
            error=str(e),
            error_type=type(e).__name__
        )
        return False

def get_loans_due_next_month() -> list:
    """
    Get all loans with payments due in the next month.
    """
    try:
        # Get current date
        now = datetime.now()
        
        # Calculate the first day of next month
        if now.month == 12:
            next_month_start = datetime(now.year + 1, 1, 1)
        else:
            next_month_start = datetime(now.year, now.month + 1, 1)
            
        # Calculate the last day of next month
        last_day = calendar.monthrange(next_month_start.year, next_month_start.month)[1]
        next_month_end = datetime(next_month_start.year, next_month_start.month, last_day, 23, 59, 59)
        
        # Set the due date to the 28th of next month
        next_month_28th = datetime(next_month_start.year, next_month_start.month, 
                                  min(28, last_day), 23, 59, 59)
        
        # Define function to query loans
        def query_loans():
            return supabase.table('loans').select(
                'id, invoice_number, loan_amount, remaining_balance, interest_rate, payment_due_date, client_id, status, start_date, weapon_cost, license_id, penalties'
            ).eq('status', 'active').gte(
                'payment_due_date', next_month_start.isoformat()
            ).lte(
                'payment_due_date', next_month_end.isoformat()
            ).execute()
        
        # Use retry mechanism for database query
        response = retry_with_backoff(query_loans, max_retries=3, initial_delay=1)
        
        if response.data:
            # For each loan, get the client information
            loans_with_clients = []
            for loan in response.data:
                # Define function to query client
                def query_client(loan_id=loan['client_id']):
                    return supabase.table('clients').select(
                        'id, first_name, last_name, email, phone'
                    ).eq('id', loan_id).execute()
                
                # Use retry mechanism for client query
                client_response = retry_with_backoff(query_client, max_retries=3, initial_delay=1)
                
                if client_response.data:
                    client = client_response.data[0]
                    loan['client'] = client
                    
                    # Calculate deposit amount (weapon cost - loan amount)
                    if loan['weapon_cost'] is not None and loan['loan_amount'] is not None:
                        loan['deposit_amount'] = loan['weapon_cost'] - loan['loan_amount']
                    else:
                        loan['deposit_amount'] = 0
                    
                    # Get gun licence information if license_id is available
                    if loan.get('license_id'):
                        # Define function to query licence
                        def query_licence(license_id=loan['license_id']):
                            return supabase.table('gun_licences').select(
                                'make, type, caliber, serial_number'
                            ).eq('id', license_id).execute()
                        
                        # Use retry mechanism for licence query
                        licence_response = retry_with_backoff(query_licence, max_retries=3, initial_delay=1)
                        
                        if licence_response.data:
                            licence = licence_response.data[0]
                            loan['gun_licence_make'] = licence.get('make', '')
                            loan['gun_licence_type'] = licence.get('type', '')
                            loan['gun_licence_caliber'] = licence.get('caliber', '')
                            loan['gun_licence_serial'] = licence.get('serial_number', '')
                        
                    # Set payment due date to the 28th of the month
                    due_date = datetime.fromisoformat(loan['payment_due_date'].replace('Z', '+00:00'))
                    last_day = calendar.monthrange(due_date.year, due_date.month)[1]
                    due_date = due_date.replace(day=min(28, last_day))
                    loan['payment_due_date'] = due_date.isoformat()
                    
                    loans_with_clients.append(loan)
            
            return loans_with_clients
        
        return []
    except Exception as e:
        logging.error(f"Error getting loans due next month: {e}")
        return []

def send_admin_summary(loans_count: int, success_count: int, overdue_count: int = 0, overdue_notifications: int = 0, 
                      penalty_count: int = 0, skipped_penalties: int = 0) -> None:
    """
    Send a summary email to the admin.
    
    Args:
        loans_count: Total number of loans processed
        success_count: Number of successful notifications
        overdue_count: Number of loans marked as overdue
        overdue_notifications: Number of overdue notifications sent
        penalty_count: Number of loans that had penalties applied
        skipped_penalties: Number of loans that were skipped for penalty due to recent payments
    """
    now = datetime.now()
    subject = f"Loan Payment Notifications Summary - {now.strftime('%Y-%m-%d')}"
    
    # Add overdue information to the summary
    overdue_section = ""
    if overdue_count > 0 or overdue_notifications > 0 or penalty_count > 0 or skipped_penalties > 0:
        penalty_info = ""
        if penalty_count > 0 or skipped_penalties > 0:
            penalty_info = f"""
            <p style="margin: 10px 0;"><strong>Penalties applied:</strong> {penalty_count}</p>
            """
            
            if skipped_penalties > 0:
                penalty_info += f"""
                <p style="margin: 10px 0;"><strong>Penalties skipped (recent payments):</strong> {skipped_penalties}</p>
                """
                
            penalty_info += f"""
            <p style="margin: 10px 0; color: #721c24;"><strong>Note:</strong> 10% penalty based on the total loan amount has been applied to overdue loans without sufficient payments.</p>
            """
            
        overdue_section = f"""
        <div style="margin: 20px 0; padding: 15px; border-radius: 5px; background-color: #f8d7da; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <h3 style="color: #721c24; margin-top: 0;">Overdue Loans</h3>
            <p style="margin: 10px 0;"><strong>Loans marked as overdue:</strong> {overdue_count}</p>
            <p style="margin: 10px 0;"><strong>Overdue notifications sent:</strong> {overdue_notifications}</p>
            {penalty_info}
        </div>
        """
    
    body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Loan Payment Notifications Summary</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; font-size: 16px; line-height: 1.5; color: #333; -webkit-text-size-adjust: 100%;">
        <div style="width: 100% !important; max-width: 600px; margin: 0 auto; padding: 20px; box-sizing: border-box;">
            <h2 style="color: #333; margin-bottom: 20px; font-size: 22px;">Loan Payment Notifications Summary</h2>
            
            <p style="margin-bottom: 15px;">Date: {now.strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div style="margin: 20px 0; padding: 15px; border-radius: 5px; background-color: #f0f0f0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <p style="margin: 10px 0;"><strong>Total loans processed:</strong> {loans_count}</p>
                <p style="margin: 10px 0;"><strong>Successful notifications:</strong> {success_count}</p>
                <p style="margin: 10px 0;"><strong>Failed notifications:</strong> {loans_count - success_count}</p>
            </div>
            
            {overdue_section}
            
            <p style="margin-top: 20px;">This is an automated notification from the loan payment notification system.</p>
            
            <div style="margin-top: 30px; font-size: 12px; color: #999; border-top: 1px solid #eee; padding-top: 15px;">
                <p style="margin: 5px 0;">© {now.year} Loan Payment System</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        send_email(ADMIN_EMAIL, subject, body)
        logging.info(f"Admin summary email sent to {ADMIN_EMAIL}")
    except Exception as e:
        logging.error(f"Failed to send admin summary: {e}")

def main(test_mode=False, send_emails=True, send_admin_summary_email=False) -> None:
    """
    Main function to send loan payment notifications.
    
    Args:
        test_mode: If True, bypasses the date check and sends a test email even if no loans are found
        send_emails: If True, sends emails (otherwise just logs)
        send_admin_summary_email: If True, sends summary email to admin
    """
    start_time = datetime.now()
    logging.info_with_context(
        f"Starting loan payment notification process at {start_time.strftime('%Y-%m-%d %H:%M:%S')}",
        operation="main",
        test_mode=test_mode,
        send_emails=send_emails,
        send_admin_summary=send_admin_summary_email,
        start_time=start_time.isoformat()
    )
    
    # Initialize counters
    overdue_notifications = 0
    penalty_count = 0
    skipped_count = 0
    overdue_count = 0
    success_count = 0
    payment_reminders_count = 0
    due_date_reminders_count = 0
    loans = []
    
    try:
        # Check if Supabase connection is working
        try:
            test_response = supabase.table('loans').select('count', count='exact').limit(1).execute()
            logging.info(f"Supabase connection test successful")
        except Exception as e:
            logging.error(f"Supabase connection test failed: {e}")
            raise ConnectionError(f"Failed to connect to Supabase: {e}")
        
        # First, update any overdue loans
        try:
            overdue_count = update_overdue_loans()
            logging.info(f"Updated {overdue_count} loans to overdue status")
        except Exception as e:
            logging.error(f"Error updating overdue loans: {e}")
            overdue_count = 0
        
        # Apply penalties to overdue loans on the 3rd of the month
        if test_mode or is_3rd_of_month():
            try:
                penalty_count, skipped_count = apply_penalties_to_overdue_loans(bypass_date_check=test_mode)
                logging.info(f"Applied penalties to {penalty_count} overdue loans, skipped {skipped_count} loans with sufficient payments")
            except Exception as e:
                logging.error(f"Error applying penalties to overdue loans: {e}")
                penalty_count, skipped_count = 0, 0
        
        # Send notifications for overdue loans
        if overdue_count > 0 or test_mode:
            try:
                overdue_notifications = notify_overdue_loans(send_emails=send_emails)
                logging.info(f"Sent {overdue_notifications} overdue notifications")
            except Exception as e:
                logging.error(f"Error sending overdue notifications: {e}")
                overdue_notifications = 0
        
        # Send payment reminders on the 22nd of the month
        if test_mode or is_22nd_of_month():
            try:
                payment_reminders_count = send_payment_reminders(send_emails=send_emails)
                logging.info(f"Sent {payment_reminders_count} payment reminders")
            except Exception as e:
                logging.error(f"Error sending payment reminders: {e}")
                payment_reminders_count = 0
        
        # Send due date reminders on the 28th of the month
        if test_mode or is_28th_of_month():
            try:
                due_date_reminders_count = send_due_date_reminders(send_emails=send_emails)
                logging.info(f"Sent {due_date_reminders_count} due date reminders")
            except Exception as e:
                logging.error(f"Error sending due date reminders: {e}")
                due_date_reminders_count = 0
        
        # Check if loans table has records
        has_loans = check_loans_table()
        if not has_loans:
            logging.warning("No loans found in the database. Make sure the loans table is set up correctly.")
        
        # Only proceed if today is the 22nd day of the month or test_mode is True
        if not test_mode and not is_22nd_of_month():
            logging.info("Today is not the 22nd day of the month. Use --test to run anyway. Exiting.")
            # Send summary to admin before exiting if requested
            if send_emails and send_admin_summary_email:
                try:
                    send_admin_summary(0, 0, overdue_count, overdue_notifications, penalty_count, skipped_count)
                    logging.info("Admin summary email sent")
                except Exception as e:
                    logging.error(f"Failed to send admin summary: {e}")
            return
        
        # Get loans due next month
        try:
            loans = get_loans_due_next_month()
            logging.info(f"Found {len(loans)} loans with payments due next month")
            
            # If no loans found, log and continue to summary
            if not loans:
                logging.info("No loans found with payments due next month.")
                loans = []
        except Exception as e:
            logging.error(f"Error getting loans due next month: {e}")
            loans = []
        
        success_count = 0
        
        # Send notifications for each loan
        for loan in loans:
            try:
                if 'client' not in loan or not loan['client']:
                    logging.warning(f"Skipping loan {loan.get('id', 'unknown')} - missing client information")
                    continue
                    
                client = loan['client']
                
                # Validate required loan fields
                required_fields = ['invoice_number', 'loan_amount', 'remaining_balance']
                missing_fields = [field for field in required_fields if field not in loan or loan[field] is None]
                if missing_fields:
                    logging.warning(f"Skipping loan {loan.get('id', 'unknown')} - missing required fields: {', '.join(missing_fields)}")
                    continue
                
                # Determine if this should be a statement or invoice based on remaining balance
                # Only send invoice if the loan is fully paid (remaining balance is 0)
                is_statement = loan['remaining_balance'] > 0
                document_type = "Statement" if is_statement else "Invoice"
                
                # Use the new subject format for statements
                if is_statement:
                    email_subject_prefix = f"Gunnery Payment Due Quote: {loan['invoice_number']}"
                else:
                    email_subject_prefix = "Loan Paid"
                
                # Add TEST indicator in the subject when in test mode
                test_prefix = "[TEST] " if test_mode else ""
                
                # For statements, use just the prefix (which now includes the quote number)
                # For invoices, keep the old format
                if is_statement:
                    email_subject = f"{test_prefix}{email_subject_prefix}"
                else:
                    email_subject = f"{test_prefix}{email_subject_prefix}: {document_type} {loan['invoice_number']} - {client['first_name']} {client['last_name']}"
                
                # Generate email body with error handling
                try:
                    from loan_templates import create_invoice_email
                    email_body = create_invoice_email(loan, is_statement)
                except Exception as template_error:
                    logging.error(f"Error generating email template for loan {loan['invoice_number']}: {template_error}")
                    continue
                
                # Log the email details
                logging.info(f"Preparing {document_type.lower()} email for {client['first_name']} {client['last_name']} ({client['email']})")
                
                # Send the email if send_emails is True
                if send_emails:
                    try:
                        # Send to client
                        send_email(client['email'], email_subject, email_body)
                        
                        # Also send a copy to accounts@gunneryguns.com
                        send_email("acum3n@protonmail.com", f"COPY: {email_subject}", email_body)
                        success_count += 1
                        
                        # Sleep briefly to avoid overwhelming the SMTP server
                        time.sleep(1)
                    except Exception as email_error:
                        logging.error(f"Failed to send email for loan {loan['invoice_number']}: {email_error}")
                else:
                    logging.info("Email sending is disabled, just logging email content.")
                    success_count += 1
            except Exception as e:
                logging.error(f"Error processing loan {loan.get('id', 'unknown')}: {e}")
        
        # Send summary to admin if send_emails and send_admin_summary_email are both True
        if send_emails and send_admin_summary_email:
            try:
                send_admin_summary(len(loans), success_count, overdue_count, overdue_notifications, penalty_count, skipped_count)
                logging.info("Admin summary email sent")
            except Exception as e:
                logging.error(f"Failed to send admin summary: {e}")
        else:
            logging.info(f"Processed {len(loans)} loans with {success_count} successful notifications")
            logging.info(f"Sent {payment_reminders_count} payment reminders and {due_date_reminders_count} due date reminders")
    
    except Exception as e:
        logging.error(f"Unexpected error in main process: {e}")
        # Send a failure notification to admin if send_emails is True
        if send_emails and send_admin_summary_email:
            try:
                send_email(
                    ADMIN_EMAIL,
                    "ERROR: Loan Payment Notification System Failure",
                    f"<p>The loan payment notification system encountered an error:</p><p>{str(e)}</p>"
                )
                logging.info("Error notification sent to admin")
            except Exception as email_error:
                logging.error(f"Failed to send error notification to admin: {email_error}")
    
    finally:
        end_time = datetime.now()
        duration = end_time - start_time
        logging.info(f"Loan payment notification process completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"Total execution time: {duration.total_seconds():.2f} seconds")
        logging.info(f"Summary: {len(loans)} loans processed, {success_count} successful notifications, {overdue_count} loans marked as overdue, {penalty_count} penalties applied")
        logging.info(f"Reminders: {payment_reminders_count} payment reminders, {due_date_reminders_count} due date reminders, {overdue_notifications} overdue notifications")

def update_overdue_loans() -> int:
    """
    Check for loans that have passed their due date and update their status to 'overdue'.
    Only marks loans as overdue if the total payments made in the current month
    don't match or exceed the amount due.
    
    Returns:
        int: Number of loans updated to overdue status
    """
    try:
        # Get current date
        now = datetime.now()
        logging.info(f"Running update_overdue_loans at {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calculate first day of the current month for payment calculation
        first_day_of_month = datetime(now.year, now.month, 1)
        
        try:
            # Define function to query potentially overdue loans
            def query_overdue_loans():
                return supabase.table('loans').select(
                    'id, payment_due_date, client_id, invoice_number, loan_amount, remaining_balance'
                ).eq('status', 'active').lt(
                    'payment_due_date', now.isoformat()
                ).execute()
            
            # Use retry mechanism for database query
            response = retry_with_backoff(query_overdue_loans, max_retries=3, initial_delay=1)
            
            if not response:
                logging.warning("Empty response from Supabase when querying overdue loans")
                return 0
                
            logging.info(f"Found {len(response.data)} potentially overdue loans")
        except Exception as query_error:
            logging.error(f"Error querying overdue loans: {query_error}")
            return 0
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        if response.data:
            for loan in response.data:
                try:
                    # Validate required loan fields
                    if not all(key in loan and loan[key] is not None for key in ['id', 'payment_due_date', 'loan_amount']):
                        missing_fields = [key for key in ['id', 'payment_due_date', 'loan_amount'] if key not in loan or loan[key] is None]
                        logging.warning(f"Skipping loan {loan.get('id', 'unknown')} - missing required fields: {', '.join(missing_fields)}")
                        error_count += 1
                        continue
                    
                    # Get the due date for comparison
                    try:
                        due_date = datetime.fromisoformat(loan['payment_due_date'].replace('Z', '+00:00'))
                    except (ValueError, TypeError) as date_error:
                        logging.warning(f"Invalid payment_due_date for loan {loan['id']}: {date_error}")
                        error_count += 1
                        continue
                    
                    # Calculate the expected payment amount (loan amount / 3)
                    try:
                        loan_amount = float(loan['loan_amount'])
                        expected_payment = round(loan_amount / 3, 2)
                    except (ValueError, TypeError) as amount_error:
                        logging.warning(f"Invalid loan_amount for loan {loan['id']}: {amount_error}")
                        error_count += 1
                        continue
                    
                    # Define function to query payments
                    def query_payments(loan_id=loan['id']):
                        return supabase.table('loan_payments').select(
                            'payment_date, amount'
                        ).eq('loan_id', loan_id).gte(
                            'payment_date', first_day_of_month.isoformat()
                        ).lte(
                            'payment_date', now.isoformat()
                        ).execute()
                    
                    # Get all payments made in the current month for this loan
                    try:
                        # Use retry mechanism for payment query
                        payment_response = retry_with_backoff(query_payments, max_retries=3, initial_delay=1)
                    except Exception as payment_query_error:
                        logging.error(f"Error querying payments for loan {loan['id']}: {payment_query_error}")
                        error_count += 1
                        continue
                    
                    # Calculate total payments made this month
                    total_payments_this_month = 0
                    if payment_response.data:
                        for payment in payment_response.data:
                            try:
                                total_payments_this_month += float(payment['amount'])
                            except (ValueError, TypeError):
                                logging.warning(f"Invalid payment amount in payment record for loan {loan['id']}")
                    
                    # If total payments this month meet or exceed the expected payment, don't mark as overdue
                    if total_payments_this_month >= expected_payment:
                        logging.info(f"Skipping overdue status for loan {loan['invoice_number']} as sufficient payments (R {total_payments_this_month:.2f}) were made this month (expected: R {expected_payment:.2f})")
                        skipped_count += 1
                        continue
                    
                    # Define function to update loan status
                    def update_loan_status(loan_id=loan['id']):
                        return supabase.table('loans').update(
                            {'status': 'overdue'}
                        ).eq('id', loan_id).execute()
                    
                    # If we get here, the loan should be marked as overdue
                    try:
                        # Use retry mechanism for update operation
                        update_response = retry_with_backoff(update_loan_status, max_retries=3, initial_delay=1)
                        
                        if update_response.data:
                            updated_count += 1
                            logging.info(f"Loan {loan['invoice_number']} marked as overdue. Payments this month: R {total_payments_this_month:.2f}, Expected: R {expected_payment:.2f}")
                            
                            # Define function to get client information
                            def get_client_info(client_id=loan['client_id']):
                                return supabase.table('clients').select(
                                    'first_name, last_name, email'
                                ).eq('id', client_id).execute()
                            
                            # Get client information for logging
                            try:
                                # Use retry mechanism for client query
                                client_response = retry_with_backoff(get_client_info, max_retries=3, initial_delay=1)
                                
                                if client_response.data:
                                    client = client_response.data[0]
                                    logging.info(f"Client {client['first_name']} {client['last_name']} ({client['email']}) has an overdue loan")
                                    
                                    # Log payment details
                                    if payment_response.data:
                                        payment_dates = [datetime.fromisoformat(payment['payment_date'].replace('Z', '+00:00')).strftime('%Y-%m-%d') for payment in payment_response.data]
                                        logging.info(f"Payments were made on {', '.join(payment_dates)}, but total (R {total_payments_this_month:.2f}) was less than required (R {expected_payment:.2f})")
                                    else:
                                        logging.info(f"No payments were made this month (required: R {expected_payment:.2f})")
                            except Exception as client_error:
                                logging.warning(f"Error getting client information for loan {loan['id']}: {client_error}")
                        else:
                            logging.warning(f"Failed to update loan {loan['id']} to overdue status")
                    except Exception as update_error:
                        logging.error(f"Error updating loan {loan['id']} to overdue status: {update_error}")
                        error_count += 1
                
                except Exception as loan_error:
                    logging.error(f"Error processing loan {loan.get('id', 'unknown')} for penalty: {loan_error}")
                    error_count += 1
        
        logging.info(f"Updated {updated_count} loans to overdue status, skipped {skipped_count} loans with sufficient payments, encountered {error_count} errors")
        return updated_count
    except Exception as e:
        logging.error(f"Error in update_overdue_loans: {e}")
        return 0

def notify_overdue_loans(send_emails=True) -> int:
    """
    Send notifications to clients with overdue loans.
    Includes information about insufficient payments in the notification email.
    
    Args:
        send_emails: If True, sends emails (otherwise just logs)
        
    Returns:
        int: Number of notifications sent
    """
    try:
        # Get current date
        now = datetime.now()
        logging.info(f"Running notify_overdue_loans at {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calculate first day of the current month for payment calculation
        first_day_of_month = datetime(now.year, now.month, 1)
        
        try:
            # Define function to query overdue loans
            def query_overdue_loans():
                return supabase.table('loans').select(
                    'id, invoice_number, loan_amount, remaining_balance, interest_rate, payment_due_date, client_id, status, start_date, weapon_cost, license_id, penalties'
                ).eq('status', 'overdue').execute()
            
            # Use retry mechanism for database query
            response = retry_with_backoff(query_overdue_loans, max_retries=3, initial_delay=1)
            
            if not response:
                logging.warning("Empty response from Supabase when querying overdue loans for notifications")
                return 0
                
            logging.info(f"Found {len(response.data)} overdue loans for notification")
            
            if not response.data:
                logging.info("No overdue loans found")
                return 0
        except Exception as query_error:
            logging.error(f"Error querying overdue loans for notifications: {query_error}")
            return 0
        
        success_count = 0
        error_count = 0
        
        # For each overdue loan, get the client information and send a notification
        for loan in response.data:
            try:
                # Validate required loan fields
                required_fields = ['id', 'invoice_number', 'loan_amount', 'remaining_balance', 'client_id']
                if not all(key in loan and loan[key] is not None for key in required_fields):
                    missing_fields = [key for key in required_fields if key not in loan or loan[key] is None]
                    logging.warning(f"Skipping loan {loan.get('id', 'unknown')} - missing required fields: {', '.join(missing_fields)}")
                    error_count += 1
                    continue
                
                # Define function to get client information
                def get_client_info(client_id=loan['client_id']):
                    return supabase.table('clients').select(
                        'id, first_name, last_name, email, phone'
                    ).eq('id', client_id).execute()
                
                # Get client information
                try:
                    # Use retry mechanism for client query
                    client_response = retry_with_backoff(get_client_info, max_retries=3, initial_delay=1)
                    
                    if not client_response.data:
                        logging.warning(f"Client not found for loan {loan['id']}")
                        error_count += 1
                        continue
                    
                    client = client_response.data[0]
                    
                    # Validate client email
                    if 'email' not in client or not client['email']:
                        logging.warning(f"Missing email for client {client.get('id', 'unknown')} (loan {loan['id']})")
                        error_count += 1
                        continue
                        
                    loan['client'] = client
                except Exception as client_error:
                    logging.error(f"Error getting client information for loan {loan['id']}: {client_error}")
                    error_count += 1
                    continue
                
                # Calculate deposit amount
                try:
                    if loan['weapon_cost'] is not None and loan['loan_amount'] is not None:
                        loan['deposit_amount'] = loan['weapon_cost'] - loan['loan_amount']
                    else:
                        loan['deposit_amount'] = 0
                except (ValueError, TypeError, KeyError) as deposit_error:
                    logging.warning(f"Error calculating deposit amount for loan {loan['id']}: {deposit_error}")
                    loan['deposit_amount'] = 0
                
                # Get gun licence information if license_id is available
                if loan.get('license_id'):
                    try:
                        # Define function to get licence information
                        def get_licence_info(license_id=loan['license_id']):
                            return supabase.table('gun_licences').select(
                                'make, type, caliber, serial_number'
                            ).eq('id', license_id).execute()
                        
                        # Use retry mechanism for licence query
                        licence_response = retry_with_backoff(get_licence_info, max_retries=3, initial_delay=1)
                        
                        if licence_response.data:
                            licence = licence_response.data[0]
                            loan['gun_licence_make'] = licence.get('make', '')
                            loan['gun_licence_type'] = licence.get('type', '')
                            loan['gun_licence_caliber'] = licence.get('caliber', '')
                            loan['gun_licence_serial'] = licence.get('serial_number', '')
                    except Exception as licence_error:
                        logging.warning(f"Error getting licence information for loan {loan['id']}: {licence_error}")
                
                # Set payment due date to the 28th of the month
                try:
                    due_date = datetime.fromisoformat(loan['payment_due_date'].replace('Z', '+00:00'))
                    last_day = calendar.monthrange(due_date.year, due_date.month)[1]
                    due_date = due_date.replace(day=min(28, last_day))
                    loan['payment_due_date'] = due_date.isoformat()
                except (ValueError, TypeError) as date_error:
                    logging.warning(f"Invalid payment_due_date for loan {loan['id']}: {date_error}")
                    # Use current date + 28 days as fallback
                    fallback_date = now + timedelta(days=28)
                    loan['payment_due_date'] = fallback_date.isoformat()
                
                # Calculate the expected payment amount (loan amount / 3)
                try:
                    loan_amount = float(loan['loan_amount'])
                    expected_payment = round(loan_amount / 3, 2)
                except (ValueError, TypeError) as amount_error:
                    logging.warning(f"Invalid loan_amount for loan {loan['id']}: {amount_error}")
                    expected_payment = 0
                
                # Define function to query payments
                def query_payments(loan_id=loan['id']):
                    return supabase.table('loan_payments').select(
                        'payment_date, amount'
                    ).eq('loan_id', loan_id).gte(
                        'payment_date', first_day_of_month.isoformat()
                    ).lte(
                        'payment_date', now.isoformat()
                    ).execute()
                
                # Get all payments made in the current month for this loan
                try:
                    # Use retry mechanism for payment query
                    payment_response = retry_with_backoff(query_payments, max_retries=3, initial_delay=1)
                except Exception as payment_query_error:
                    logging.error(f"Error querying payments for loan {loan['id']}: {payment_query_error}")
                    payment_response = None
                
                # Calculate total payments made this month
                total_payments_this_month = 0
                if payment_response and payment_response.data:
                    for payment in payment_response.data:
                        try:
                            total_payments_this_month += float(payment['amount'])
                        except (ValueError, TypeError):
                            logging.warning(f"Invalid payment amount in payment record for loan {loan['id']}")
                
                # Create overdue notification email
                email_subject = f"OVERDUE PAYMENT NOTICE: {loan['invoice_number']} - {client['first_name']} {client['last_name']}"
                
                # Create payment info message
                payment_info = ""
                if total_payments_this_month > 0:
                    payment_info = f"Your total payments this month (R {total_payments_this_month:.2f}) were less than the required amount (R {expected_payment:.2f})."
                else:
                    payment_info = f"No payments were received this month. Required payment: R {expected_payment:.2f}."
                
                # Create penalty warning message
                try:
                    penalty_amount = float(loan.get('penalties', 0))
                    has_penalties = penalty_amount > 0
                except (ValueError, TypeError):
                    has_penalties = False
                
                if has_penalties:
                    try:
                        penalty_amount = float(loan.get('penalties', 0))
                        loan_amount = float(loan['loan_amount'])
                        penalty_percentage = round((penalty_amount / loan_amount) * 100)
                        penalty_warning = f"""
                        <div style="background-color: #d9534f; color: white; padding: 10px; text-align: center; margin-bottom: 20px;">
                            <h2 style="margin: 0;">OVERDUE PAYMENT NOTICE</h2>
                            <p style="margin: 5px 0;">A 10% penalty (R {penalty_amount:.2f}) based on your total loan amount has been applied to your account.</p>
                            <p style="margin: 5px 0;">{payment_info}</p>
                        </div>
                        """
                    except (ValueError, TypeError, ZeroDivisionError):
                        penalty_warning = f"""
                        <div style="background-color: #d9534f; color: white; padding: 10px; text-align: center; margin-bottom: 20px;">
                            <h2 style="margin: 0;">OVERDUE PAYMENT NOTICE</h2>
                            <p style="margin: 5px 0;">A 10% penalty based on your total loan amount has been applied to your account.</p>
                            <p style="margin: 5px 0;">{payment_info}</p>
                        </div>
                        """
                else:
                    try:
                        loan_amount = float(loan['loan_amount'])
                        potential_penalty = round(loan_amount * 0.1, 2)
                        penalty_warning = f"""
                        <div style="background-color: #d9534f; color: white; padding: 10px; text-align: center; margin-bottom: 20px;">
                            <h2 style="margin: 0;">OVERDUE PAYMENT NOTICE</h2>
                            <p style="margin: 5px 0;">Please note: A 10% penalty (R {potential_penalty:.2f}) based on your total loan amount will be applied if payment is not received by the 3rd of next month.</p>
                            <p style="margin: 5px 0;">{payment_info}</p>
                        </div>
                        """
                    except (ValueError, TypeError):
                        penalty_warning = f"""
                        <div style="background-color: #d9534f; color: white; padding: 10px; text-align: center; margin-bottom: 20px;">
                            <h2 style="margin: 0;">OVERDUE PAYMENT NOTICE</h2>
                            <p style="margin: 5px 0;">Please note: A 10% penalty based on your total loan amount will be applied if payment is not received by the 3rd of next month.</p>
                            <p style="margin: 5px 0;">{payment_info}</p>
                        </div>
                        """
                
                # Generate email body with error handling
                try:
                    from loan_templates import create_invoice_email
                    email_body = create_invoice_email(loan, is_quote=True)  # Reuse the invoice email template
                    
                    # Add overdue notice to the email subject and body
                    email_body = email_body.replace(
                        '<div class="header">',
                        f'{penalty_warning}<div class="header">'
                    )
                except Exception as template_error:
                    logging.error(f"Error generating email template for loan {loan['invoice_number']}: {template_error}")
                    error_count += 1
                    continue
                
                if send_emails:
                    try:
                        # Send to client
                        send_email(client['email'], email_subject, email_body)
                        
                        # Also send a copy to accounts@gunneryguns.com
                        send_email("acum3n@protonmail.com", f"COPY: {email_subject}", email_body)
                        
                        success_count += 1
                        logging.info(f"Overdue notification sent to {client['first_name']} {client['last_name']} ({client['email']})")
                        logging.info(f"Payment info: {payment_info}")
                        
                        # Sleep briefly to avoid overwhelming the SMTP server
                        time.sleep(1)
                    except Exception as email_error:
                        logging.error(f"Failed to send email for loan {loan['invoice_number']}: {email_error}")
                        error_count += 1
                else:
                    logging.info(f"Would send overdue notification to {client['first_name']} {client['last_name']} ({client['email']})")
                    logging.info(f"Payment info: {payment_info}")
                    success_count += 1
            
            except Exception as loan_error:
                logging.error(f"Error processing overdue loan {loan.get('id', 'unknown')}: {loan_error}")
                error_count += 1
        
        logging.info(f"Sent {success_count} overdue notifications, encountered {error_count} errors")
        return success_count
    
    except Exception as e:
        logging.error(f"Error in notify_overdue_loans: {e}")
        return 0

def is_3rd_of_month() -> bool:
    """Check if today is the 3rd day of the month."""
    today = datetime.now()
    return today.day == 3

def apply_penalties_to_overdue_loans(bypass_date_check=False) -> tuple:
    """
    Apply penalties to loans that are still overdue by the 3rd of the month.
    Adds a 10% penalty to the remaining balance.
    Only applies penalties if the total payments made in the current month
    don't match or exceed the amount due.
    
    Args:
        bypass_date_check: If True, apply penalties regardless of the date
    
    Returns:
        tuple: (Number of loans that had penalties applied, Number of loans skipped due to sufficient payments)
    """
    try:
        # Only run this function on the 3rd of the month unless bypass_date_check is True
        if not bypass_date_check and not is_3rd_of_month():
            logging.info_with_context(
                "Today is not the 3rd day of the month. Skipping penalty application.",
                operation="apply_penalties_to_overdue_loans",
                date_check=False,
                bypass_date_check=bypass_date_check
            )
            return (0, 0)
            
        # Get current date
        now = datetime.now()
        logging.info_with_context(
            f"Running apply_penalties_to_overdue_loans at {now.strftime('%Y-%m-%d %H:%M:%S')}",
            operation="apply_penalties_to_overdue_loans",
            timestamp=now.isoformat(),
            bypass_date_check=bypass_date_check
        )
        
        # Calculate first day of the current month for payment calculation
        first_day_of_month = datetime(now.year, now.month, 1)
        
        try:
            # Define function to query overdue loans
            def query_overdue_loans():
                return supabase.table('loans').select(
                    'id, invoice_number, loan_amount, remaining_balance, penalties, client_id, payment_due_date'
                ).eq('status', 'overdue').execute()
            
            # Use retry mechanism for database query
            response = retry_with_backoff(query_overdue_loans, max_retries=3, initial_delay=1)
            
            if not response:
                logging.warning_with_context(
                    "Empty response from Supabase when querying overdue loans for penalties",
                    operation="apply_penalties_to_overdue_loans",
                    query="overdue_loans"
                )
                return (0, 0)
                
            logging.info_with_context(
                f"Found {len(response.data)} overdue loans to check for penalty application",
                operation="apply_penalties_to_overdue_loans",
                overdue_loans_count=len(response.data)
            )
            
            if not response.data:
                logging.info_with_context(
                    "No overdue loans found for penalty application",
                    operation="apply_penalties_to_overdue_loans",
                    overdue_loans_count=0
                )
                return (0, 0)
        except Exception as query_error:
            logging.error_with_context(
                f"Error querying overdue loans for penalties: {query_error}",
                operation="apply_penalties_to_overdue_loans",
                error=str(query_error),
                error_type=type(query_error).__name__
            )
            return (0, 0)
        
        penalty_count = 0
        skipped_count = 0
        error_count = 0
        
        for loan in response.data:
            try:
                # Validate required loan fields
                required_fields = ['id', 'payment_due_date', 'loan_amount', 'remaining_balance']
                if not all(key in loan and loan[key] is not None for key in required_fields):
                    missing_fields = [key for key in required_fields if key not in loan or loan[key] is None]
                    logging.warning(f"Skipping loan {loan.get('id', 'unknown')} - missing required fields: {', '.join(missing_fields)}")
                    error_count += 1
                    continue
                
                # Get the due date for comparison
                try:
                    due_date = datetime.fromisoformat(loan['payment_due_date'].replace('Z', '+00:00'))
                except (ValueError, TypeError) as date_error:
                    logging.warning(f"Invalid payment_due_date for loan {loan['id']}: {date_error}")
                    error_count += 1
                    continue
                
                # Calculate the expected payment amount (loan amount / 3)
                try:
                    loan_amount = float(loan['loan_amount'])
                    expected_payment = round(loan_amount / 3, 2)
                except (ValueError, TypeError) as amount_error:
                    logging.warning(f"Invalid loan_amount for loan {loan['id']}: {amount_error}")
                    error_count += 1
                    continue
                
                # Define function to query payments
                def query_payments(loan_id=loan['id']):
                    return supabase.table('loan_payments').select(
                        'payment_date, amount'
                    ).eq('loan_id', loan_id).gte(
                        'payment_date', first_day_of_month.isoformat()
                    ).lte(
                        'payment_date', now.isoformat()
                    ).execute()
                
                # Get all payments made in the current month for this loan
                try:
                    # Use retry mechanism for payment query
                    payment_response = retry_with_backoff(query_payments, max_retries=3, initial_delay=1)
                except Exception as payment_query_error:
                    logging.error(f"Error querying payments for loan {loan['id']}: {payment_query_error}")
                    error_count += 1
                    continue
                
                # Calculate total payments made this month
                total_payments_this_month = 0
                payment_dates = []
                if payment_response.data:
                    for payment in payment_response.data:
                        try:
                            payment_amount = float(payment['amount'])
                            total_payments_this_month += payment_amount
                            
                            # Store payment date for logging
                            try:
                                payment_date = datetime.fromisoformat(payment['payment_date'].replace('Z', '+00:00'))
                                payment_dates.append(payment_date.strftime('%Y-%m-%d'))
                            except (ValueError, TypeError):
                                pass
                        except (ValueError, TypeError):
                            logging.warning(f"Invalid payment amount in payment record for loan {loan['id']}")
                
                # If total payments this month meet or exceed the expected payment, don't apply penalty
                if total_payments_this_month >= expected_payment:
                    logging.info(f"Skipping penalty for loan {loan['invoice_number']} as sufficient payments (R {total_payments_this_month:.2f}) were made this month (expected: R {expected_payment:.2f})")
                    skipped_count += 1
                    continue
                
                # Calculate the penalty (10% of total loan amount)
                try:
                    loan_amount = float(loan['loan_amount'])
                    remaining_balance = float(loan['remaining_balance'])
                    current_penalties = float(loan.get('penalties', 0))
                    
                    # Calculate new penalty (10% of total loan amount)
                    new_penalty = round(loan_amount * 0.1, 2)
                    total_penalties = current_penalties + new_penalty
                    
                    # Define function to update loan with penalty
                    def update_loan_penalty(loan_id=loan['id'], penalties=total_penalties):
                        return supabase.table('loans').update({
                            'penalties': penalties
                        }).eq('id', loan_id).execute()
                    
                    # Use retry mechanism for update operation
                    update_response = retry_with_backoff(update_loan_penalty, max_retries=3, initial_delay=1)
                    
                    if update_response.data:
                        penalty_count += 1
                        logging.info(f"Applied penalty of R {new_penalty:.2f} (10% of loan amount R {loan_amount:.2f}) to loan {loan['invoice_number']}. Total penalties: R {total_penalties:.2f}")
                        logging.info(f"Payments this month: R {total_payments_this_month:.2f}, Expected: R {expected_payment:.2f}")
                        
                        # Define function to get client information
                        def get_client_info(client_id=loan['client_id']):
                            return supabase.table('clients').select(
                                'first_name, last_name, email'
                            ).eq('id', client_id).execute()
                        
                        # Get client information for logging
                        try:
                            # Use retry mechanism for client query
                            client_response = retry_with_backoff(get_client_info, max_retries=3, initial_delay=1)
                            
                            if client_response.data:
                                client = client_response.data[0]
                                logging.info(f"Applied penalty to loan for client {client['first_name']} {client['last_name']} ({client['email']})")
                                
                                # Log payment details
                                if payment_dates:
                                    logging.info(f"Payments were made on {', '.join(payment_dates)}, but total (R {total_payments_this_month:.2f}) was less than required (R {expected_payment:.2f})")
                                else:
                                    logging.info(f"No payments were made this month (required: R {expected_payment:.2f})")
                        except Exception as client_error:
                            logging.warning(f"Error getting client information for loan {loan['id']}: {client_error}")
                    else:
                        logging.warning(f"Failed to update penalties for loan {loan['id']}")
                except Exception as penalty_error:
                    logging.error(f"Error calculating or applying penalty for loan {loan['id']}: {penalty_error}")
                    error_count += 1
            
            except Exception as loan_error:
                logging.error(f"Error processing loan {loan.get('id', 'unknown')} for penalty: {loan_error}")
                error_count += 1
        
        logging.info(f"Applied penalties to {penalty_count} overdue loans, skipped {skipped_count} loans with sufficient payments, encountered {error_count} errors")
        return (penalty_count, skipped_count)
    
    except Exception as e:
        logging.error(f"Error in apply_penalties_to_overdue_loans: {e}")
        return (0, 0)

def check_database_connection() -> bool:
    """
    Check if the database connection is working properly.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        # Define functions for each database check
        def check_loans_table():
            response = supabase.table('loans').select('count', count='exact').limit(1).execute()
            logging.info_with_context(
                f"Database connection test successful. Found {response.count} loans.",
                operation="check_database_connection",
                table="loans",
                record_count=response.count
            )
            return response
            
        def check_clients_table():
            clients_response = supabase.table('clients').select('count', count='exact').limit(1).execute()
            logging.info_with_context(
                f"Clients table accessible. Found {clients_response.count} clients.",
                operation="check_database_connection",
                table="clients",
                record_count=clients_response.count
            )
            return clients_response
            
        def check_payments_table():
            payments_response = supabase.table('loan_payments').select('count', count='exact').limit(1).execute()
            logging.info_with_context(
                f"Loan payments table accessible. Found {payments_response.count} payment records.",
                operation="check_database_connection",
                table="loan_payments",
                record_count=payments_response.count
            )
            return payments_response
            
        def check_licences_table():
            licences_response = supabase.table('gun_licences').select('count', count='exact').limit(1).execute()
            logging.info_with_context(
                f"Gun licences table accessible. Found {licences_response.count} licence records.",
                operation="check_database_connection",
                table="gun_licences",
                record_count=licences_response.count
            )
            return licences_response
        
        # Use retry mechanism for database operations
        retry_with_backoff(check_loans_table, max_retries=3, initial_delay=1)
        retry_with_backoff(check_clients_table, max_retries=3, initial_delay=1)
        retry_with_backoff(check_payments_table, max_retries=3, initial_delay=1)
        retry_with_backoff(check_licences_table, max_retries=3, initial_delay=1)
        
        return True
    except Exception as e:
        logging.error_with_context(
            f"Database connection test failed: {e}",
            operation="check_database_connection",
            error=str(e),
            error_type=type(e).__name__
        )
        return False

def run_cli():
    """
    Run the command-line interface for the loan script.
    Handles argument parsing and calls the appropriate functions.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Send loan payment notifications.')
    parser.add_argument('--test', action='store_true', help='Run in test mode (bypasses date check, always sends emails, and creates a test loan if none found)')
    parser.add_argument('--no-send', action='store_true', help='Do not actually send emails, just log')
    parser.add_argument('--admin-summary', action='store_true', help='Send summary email to admin')
    parser.add_argument('--apply-penalties', action='store_true', help='Force apply penalties to overdue loans (bypasses date check)')
    parser.add_argument('--payment-reminders', action='store_true', help='Force send payment reminders (bypasses 22nd day check)')
    parser.add_argument('--due-date-reminders', action='store_true', help='Force send due date reminders (bypasses 28th day check)')
    parser.add_argument('--check-db', action='store_true', help='Check database connection and exit')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Verbose logging enabled")
    
    try:
        # Check database connection if requested
        if args.check_db:
            logging.info("Checking database connection...")
            if check_database_connection():
                logging.info("Database connection check passed. All tables are accessible.")
                return 0
            else:
                logging.error("Database connection check failed. Please check your configuration.")
                return 1
        
        # Check database connection before proceeding
        logging.info("Performing initial database connection check...")
        if not check_database_connection():
            logging.error("Database connection check failed. Exiting.")
            send_emails = not args.no_send
            if send_emails:
                try:
                    send_email(
                        ADMIN_EMAIL,
                        "ERROR: Loan Payment System - Database Connection Failure",
                        "<p>The loan payment system could not connect to the database. Please check the configuration and logs.</p>"
                    )
                    logging.info("Database connection error notification sent to admin")
                except Exception as email_error:
                    logging.error(f"Failed to send database error notification: {email_error}")
            return 1
        
        # If test mode is enabled, force send_emails to be True regardless of --no-send
        send_emails = True if args.test else not args.no_send
        
        # If apply-penalties is specified, apply penalties to overdue loans
        if args.apply_penalties:
            logging.info("Manually applying penalties to overdue loans")
            penalty_count, skipped_count = apply_penalties_to_overdue_loans(bypass_date_check=True)
            logging.info(f"Applied penalties to {penalty_count} overdue loans, skipped {skipped_count} loans with sufficient payments")
        # If payment-reminders is specified, send payment reminders
        elif args.payment_reminders:
            logging.info("Manually sending payment reminders")
            # Create a modified version of send_payment_reminders that bypasses the date check
            def send_payment_reminders_bypass():
                # Store the original function
                original_is_22nd = globals()['is_22nd_of_month']
                try:
                    # Replace the function temporarily to always return True
                    globals()['is_22nd_of_month'] = lambda: True
                    # Call the function
                    count = send_payment_reminders(send_emails=send_emails)
                    return count
                finally:
                    # Restore the original function
                    globals()['is_22nd_of_month'] = original_is_22nd
            
            reminders_count = send_payment_reminders_bypass()
            logging.info(f"Sent {reminders_count} payment reminders")
        # If due-date-reminders is specified, send due date reminders
        elif args.due_date_reminders:
            logging.info("Manually sending due date reminders")
            # Create a modified version of send_due_date_reminders that bypasses the date check
            def send_due_date_reminders_bypass():
                # Store the original function
                original_is_28th = globals()['is_28th_of_month']
                try:
                    # Replace the function temporarily to always return True
                    globals()['is_28th_of_month'] = lambda: True
                    # Call the function
                    count = send_due_date_reminders(send_emails=send_emails)
                    return count
                finally:
                    # Restore the original function
                    globals()['is_28th_of_month'] = original_is_28th
            
            reminders_count = send_due_date_reminders_bypass()
            logging.info(f"Sent {reminders_count} due date reminders")
        else:
            main(test_mode=args.test, send_emails=send_emails, send_admin_summary_email=args.admin_summary)
        
        return 0
    except Exception as e:
        logging.error(f"Unexpected error in main script: {e}")
        # Send a failure notification to admin if not in no-send mode
        send_emails = True if args.test else not args.no_send
        if send_emails:
            try:
                send_email(
                    ADMIN_EMAIL,
                    "ERROR: Loan Payment Notification System Failure",
                    f"<p>The loan payment notification system encountered an error:</p><p>{str(e)}</p>"
                )
                logging.info("Error notification sent to admin")
            except Exception as email_error:
                logging.error(f"Failed to send error notification to admin: {email_error}")
        return 1

def send_payment_reminders(send_emails=True) -> int:
    """
    Send payment reminder emails to clients with payments due next month.
    This function runs on the 22nd of each month.
    
    Args:
        send_emails: If True, sends emails (otherwise just logs)
        
    Returns:
        int: Number of reminders sent
    """
    try:
        # Only run this function on the 22nd of the month
        if not is_22nd_of_month():
            logging.info("Today is not the 22nd day of the month. Skipping payment reminders.")
            return 0
            
        # Get current date
        now = datetime.now()
        logging.info(f"Running send_payment_reminders at {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get loans due next month
        loans = get_loans_due_next_month()
        
        if not loans:
            logging.info("No loans found with payments due next month")
            return 0
            
        logging.info(f"Found {len(loans)} loans with payments due next month for reminder")
        
        success_count = 0
        error_count = 0
        
        for loan in loans:
            try:
                # Validate required loan fields
                required_fields = ['invoice_number', 'loan_amount', 'remaining_balance', 'client']
                if not all(key in loan and loan[key] is not None for key in required_fields):
                    missing_fields = [key for key in required_fields if key not in loan or loan[key] is None]
                    logging.warning(f"Skipping loan {loan.get('id', 'unknown')} - missing required fields: {', '.join(missing_fields)}")
                    error_count += 1
                    continue
                
                # Validate client information
                client = loan['client']
                if not client.get('email'):
                    logging.warning(f"Missing email for client {client.get('id', 'unknown')} (loan {loan['id']})")
                    error_count += 1
                    continue
                
                # Calculate the expected payment amount (loan amount / 3)
                try:
                    loan_amount = float(loan['loan_amount'])
                    expected_payment = round(loan_amount / 3, 2)
                except (ValueError, TypeError) as amount_error:
                    logging.warning(f"Invalid loan_amount for loan {loan['id']}: {amount_error}")
                    error_count += 1
                    continue
                
                # Format the payment due date
                try:
                    due_date = datetime.fromisoformat(loan['payment_due_date'].replace('Z', '+00:00'))
                    formatted_due_date = due_date.strftime('%d %B %Y')
                except (ValueError, TypeError) as date_error:
                    logging.warning(f"Invalid payment_due_date for loan {loan['id']}: {date_error}")
                    formatted_due_date = "next month"
                
                # Create reminder email
                email_subject = f"Payment Reminder: {loan['invoice_number']} - {client['first_name']} {client['last_name']}"
                
                reminder_message = f"""
                <div style="background-color: #5bc0de; color: white; padding: 10px; text-align: center; margin-bottom: 20px;">
                    <h2 style="margin: 0;">PAYMENT REMINDER</h2>
                    <p style="margin: 5px 0;">Your monthly payment of R {expected_payment:.2f} is due on {formatted_due_date}.</p>
                    <p style="margin: 5px 0;">Please ensure your payment is made on time to avoid overdue status and penalties.</p>
                </div>
                """
                
                # Generate email body with error handling
                try:
                    from loan_templates import create_invoice_email
                    email_body = create_invoice_email(loan, is_quote=True)  # Reuse the invoice email template
                    
                    # Add reminder notice to the email body
                    email_body = email_body.replace(
                        '<div class="header">',
                        f'{reminder_message}<div class="header">'
                    )
                except Exception as template_error:
                    logging.error(f"Error generating email template for loan {loan['invoice_number']}: {template_error}")
                    error_count += 1
                    continue
                
                if send_emails:
                    try:
                        # Send to client
                        send_email(client['email'], email_subject, email_body)
                        
                        # Also send a copy to accounts@gunneryguns.com
                        send_email("acum3n@protonmail.com", f"COPY: {email_subject}", email_body)
                        
                        success_count += 1
                        logging.info(f"Payment reminder sent to {client['first_name']} {client['last_name']} ({client['email']})")
                        logging.info(f"Payment due: R {expected_payment:.2f} on {formatted_due_date}")
                        
                        # Sleep briefly to avoid overwhelming the SMTP server
                        time.sleep(1)
                    except Exception as email_error:
                        logging.error(f"Failed to send email for loan {loan['invoice_number']}: {email_error}")
                        error_count += 1
                else:
                    logging.info(f"Would send payment reminder to {client['first_name']} {client['last_name']} ({client['email']})")
                    logging.info(f"Payment due: R {expected_payment:.2f} on {formatted_due_date}")
                    success_count += 1
            
            except Exception as loan_error:
                logging.error(f"Error processing loan {loan.get('id', 'unknown')} for payment reminder: {loan_error}")
                error_count += 1
        
        logging.info(f"Sent {success_count} payment reminders, encountered {error_count} errors")
        return success_count
    
    except Exception as e:
        logging.error(f"Error in send_payment_reminders: {e}")
        return 0

def send_due_date_reminders(send_emails=True) -> int:
    """
    Send due date reminder emails to clients with payments due in the next few days.
    This function runs on the 28th of each month.
    
    Args:
        send_emails: If True, sends emails (otherwise just logs)
        
    Returns:
        int: Number of reminders sent
    """
    try:
        # Only run this function on the 28th of the month
        if not is_28th_of_month():
            logging.info("Today is not the 28th day of the month. Skipping due date reminders.")
            return 0
            
        # Get current date
        now = datetime.now()
        logging.info(f"Running send_due_date_reminders at {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calculate the first day of next month
        if now.month == 12:
            next_month_start = datetime(now.year + 1, 1, 1)
        else:
            next_month_start = datetime(now.year, now.month + 1, 1)
            
        # Calculate the last day of next month
        last_day = calendar.monthrange(next_month_start.year, next_month_start.month)[1]
        next_month_end = datetime(next_month_start.year, next_month_start.month, last_day, 23, 59, 59)
        
        # Define function to query active loans with payments due in the next few days
        def query_active_loans():
            return supabase.table('loans').select(
                'id, invoice_number, loan_amount, remaining_balance, interest_rate, payment_due_date, client_id, status, start_date, weapon_cost, license_id, penalties'
            ).eq('status', 'active').gte(
                'payment_due_date', now.isoformat()
            ).lte(
                'payment_due_date', next_month_start.isoformat()
            ).execute()
        
        # Use retry mechanism for database query
        try:
            response = retry_with_backoff(query_active_loans, max_retries=3, initial_delay=1)
            
            if not response:
                logging.warning("Empty response from Supabase when querying loans for due date reminders")
                return 0
                
            logging.info(f"Found {len(response.data)} loans with payments due in the next few days")
            
            if not response.data:
                logging.info("No loans found with payments due in the next few days")
                return 0
        except Exception as query_error:
            logging.error(f"Error querying loans for due date reminders: {query_error}")
            return 0
        
        success_count = 0
        error_count = 0
        
        # Calculate first day of the current month for payment calculation
        first_day_of_month = datetime(now.year, now.month, 1)
        
        # For each loan, get the client information and send a reminder
        for loan in response.data:
            try:
                # Validate required loan fields
                required_fields = ['id', 'invoice_number', 'loan_amount', 'remaining_balance', 'client_id']
                if not all(key in loan and loan[key] is not None for key in required_fields):
                    missing_fields = [key for key in required_fields if key not in loan or loan[key] is None]
                    logging.warning(f"Skipping loan {loan.get('id', 'unknown')} - missing required fields: {', '.join(missing_fields)}")
                    error_count += 1
                    continue
                
                # Define function to get client information
                def get_client_info(client_id=loan['client_id']):
                    return supabase.table('clients').select(
                        'id, first_name, last_name, email, phone'
                    ).eq('id', client_id).execute()
                
                # Get client information
                try:
                    # Use retry mechanism for client query
                    client_response = retry_with_backoff(get_client_info, max_retries=3, initial_delay=1)
                    
                    if not client_response.data:
                        logging.warning(f"Client not found for loan {loan['id']}")
                        error_count += 1
                        continue
                    
                    client = client_response.data[0]
                    
                    # Validate client email
                    if 'email' not in client or not client['email']:
                        logging.warning(f"Missing email for client {client.get('id', 'unknown')} (loan {loan['id']})")
                        error_count += 1
                        continue
                        
                    loan['client'] = client
                except Exception as client_error:
                    logging.error(f"Error getting client information for loan {loan['id']}: {client_error}")
                    error_count += 1
                    continue
                
                # Calculate deposit amount
                try:
                    if loan['weapon_cost'] is not None and loan['loan_amount'] is not None:
                        loan['deposit_amount'] = loan['weapon_cost'] - loan['loan_amount']
                    else:
                        loan['deposit_amount'] = 0
                except (ValueError, TypeError, KeyError) as deposit_error:
                    logging.warning(f"Error calculating deposit amount for loan {loan['id']}: {deposit_error}")
                    loan['deposit_amount'] = 0
                
                # Get gun licence information if license_id is available
                if loan.get('license_id'):
                    try:
                        # Define function to get licence information
                        def get_licence_info(license_id=loan['license_id']):
                            return supabase.table('gun_licences').select(
                                'make, type, caliber, serial_number'
                            ).eq('id', license_id).execute()
                        
                        # Use retry mechanism for licence query
                        licence_response = retry_with_backoff(get_licence_info, max_retries=3, initial_delay=1)
                        
                        if licence_response.data:
                            licence = licence_response.data[0]
                            loan['gun_licence_make'] = licence.get('make', '')
                            loan['gun_licence_type'] = licence.get('type', '')
                            loan['gun_licence_caliber'] = licence.get('caliber', '')
                            loan['gun_licence_serial'] = licence.get('serial_number', '')
                    except Exception as licence_error:
                        logging.warning(f"Error getting licence information for loan {loan['id']}: {licence_error}")
                
                # Format the payment due date
                try:
                    due_date = datetime.fromisoformat(loan['payment_due_date'].replace('Z', '+00:00'))
                    formatted_due_date = due_date.strftime('%d %B %Y')
                    days_until_due = (due_date.date() - now.date()).days
                except (ValueError, TypeError) as date_error:
                    logging.warning(f"Invalid payment_due_date for loan {loan['id']}: {date_error}")
                    formatted_due_date = "in the next few days"
                    days_until_due = 3  # Default assumption
                
                # Calculate the expected payment amount (loan amount / 3)
                try:
                    loan_amount = float(loan['loan_amount'])
                    expected_payment = round(loan_amount / 3, 2)
                except (ValueError, TypeError) as amount_error:
                    logging.warning(f"Invalid loan_amount for loan {loan['id']}: {amount_error}")
                    expected_payment = 0
                
                # Define function to query payments
                def query_payments(loan_id=loan['id']):
                    return supabase.table('loan_payments').select(
                        'payment_date, amount'
                    ).eq('loan_id', loan_id).gte(
                        'payment_date', first_day_of_month.isoformat()
                    ).lte(
                        'payment_date', now.isoformat()
                    ).execute()
                
                # Get all payments made in the current month for this loan
                try:
                    # Use retry mechanism for payment query
                    payment_response = retry_with_backoff(query_payments, max_retries=3, initial_delay=1)
                except Exception as payment_query_error:
                    logging.error(f"Error querying payments for loan {loan['id']}: {payment_query_error}")
                    payment_response = None
                
                # Calculate total payments made this month
                total_payments_this_month = 0
                if payment_response and payment_response.data:
                    for payment in payment_response.data:
                        try:
                            total_payments_this_month += float(payment['amount'])
                        except (ValueError, TypeError):
                            logging.warning(f"Invalid payment amount in payment record for loan {loan['id']}")
                
                # Create payment info message
                if total_payments_this_month > 0:
                    if total_payments_this_month >= expected_payment:
                        payment_info = f"Your total payments this month (R {total_payments_this_month:.2f}) have met the required amount (R {expected_payment:.2f}). Thank you for your payment!"
                    else:
                        payment_info = f"Your total payments this month (R {total_payments_this_month:.2f}) are less than the required amount (R {expected_payment:.2f}). Please make an additional payment of R {expected_payment - total_payments_this_month:.2f}."
                else:
                    payment_info = f"No payments have been received this month. Required payment: R {expected_payment:.2f}."
                
                # Create due date reminder email
                email_subject = f"PAYMENT DUE SOON: {loan['invoice_number']} - {client['first_name']} {client['last_name']}"
                
                # Create urgency level based on days until due and payment status
                if days_until_due <= 1:
                    urgency_color = "#d9534f"  # Red for very urgent (tomorrow or today)
                    urgency_message = "URGENT: PAYMENT DUE TOMORROW"
                    if days_until_due == 0:
                        urgency_message = "URGENT: PAYMENT DUE TODAY"
                else:
                    urgency_color = "#f0ad4e"  # Yellow/orange for less urgent
                    urgency_message = f"PAYMENT DUE IN {days_until_due} DAYS"
                
                reminder_message = f"""
                <div style="background-color: {urgency_color}; color: white; padding: 10px; text-align: center; margin-bottom: 20px;">
                    <h2 style="margin: 0;">{urgency_message}</h2>
                    <p style="margin: 5px 0;">Your monthly payment of R {expected_payment:.2f} is due on {formatted_due_date}.</p>
                    <p style="margin: 5px 0;">{payment_info}</p>
                    <p style="margin: 5px 0;">Please ensure your payment is made on time to avoid overdue status and penalties.</p>
                </div>
                """
                
                # Generate email body with error handling
                try:
                    from loan_templates import create_invoice_email
                    email_body = create_invoice_email(loan, is_quote=True)  # Reuse the invoice email template
                    
                    # Add reminder notice to the email body
                    email_body = email_body.replace(
                        '<div class="header">',
                        f'{reminder_message}<div class="header">'
                    )
                except Exception as template_error:
                    logging.error(f"Error generating email template for loan {loan['invoice_number']}: {template_error}")
                    error_count += 1
                    continue
                
                if send_emails:
                    try:
                        # Send to client
                        send_email(client['email'], email_subject, email_body)
                        
                        # Also send a copy to accounts@gunneryguns.com
                        send_email("acum3n@protonmail.com", f"COPY: {email_subject}", email_body)
                        
                        success_count += 1
                        logging.info(f"Due date reminder sent to {client['first_name']} {client['last_name']} ({client['email']})")
                        logging.info(f"Payment due: R {expected_payment:.2f} on {formatted_due_date} (in {days_until_due} days)")
                        logging.info(f"Payment info: {payment_info}")
                        
                        # Sleep briefly to avoid overwhelming the SMTP server
                        time.sleep(1)
                    except Exception as email_error:
                        logging.error(f"Failed to send email for loan {loan['invoice_number']}: {email_error}")
                        error_count += 1
                else:
                    logging.info(f"Would send due date reminder to {client['first_name']} {client['last_name']} ({client['email']})")
                    logging.info(f"Payment due: R {expected_payment:.2f} on {formatted_due_date} (in {days_until_due} days)")
                    logging.info(f"Payment info: {payment_info}")
                    success_count += 1
            
            except Exception as loan_error:
                logging.error(f"Error processing loan {loan.get('id', 'unknown')} for due date reminder: {loan_error}")
                error_count += 1
        
        logging.info(f"Sent {success_count} due date reminders, encountered {error_count} errors")
        return success_count
    
    except Exception as e:
        logging.error(f"Error in send_due_date_reminders: {e}")
        return 0

def log_loan_operation(operation_name, loan_data, client_data=None, success=True, error=None, **additional_context):
    """
    Log a loan operation with structured data.
    
    Args:
        operation_name: Name of the operation (e.g., "payment_reminder", "apply_penalty")
        loan_data: Dictionary containing loan information
        client_data: Optional dictionary containing client information
        success: Whether the operation was successful
        error: Error message if the operation failed
        **additional_context: Additional contextual information
    """
    # Extract key loan information
    loan_context = {
        "loan_id": loan_data.get("id"),
        "invoice_number": loan_data.get("invoice_number"),
        "loan_amount": loan_data.get("loan_amount"),
        "remaining_balance": loan_data.get("remaining_balance"),
        "status": loan_data.get("status")
    }
    
    # Extract key client information if available
    client_context = {}
    if client_data:
        client_context = {
            "client_id": client_data.get("id"),
            "client_name": f"{client_data.get('first_name', '')} {client_data.get('last_name', '')}".strip(),
            "client_email": client_data.get("email")
        }
    
    # Combine all context
    context = {
        "operation": operation_name,
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "loan": loan_context,
        "client": client_context
    }
    
    # Add any additional context
    context.update(additional_context)
    
    # Add error information if provided
    if error:
        context["error"] = str(error)
        context["error_type"] = type(error).__name__ if isinstance(error, Exception) else "str"
        logging.error_with_context(
            f"Loan operation '{operation_name}' failed: {error}",
            **context
        )
    else:
        logging.info_with_context(
            f"Loan operation '{operation_name}' completed successfully",
            **context
        )
    
    return context

if __name__ == "__main__":
    exit_code = run_cli()
    exit(exit_code)
