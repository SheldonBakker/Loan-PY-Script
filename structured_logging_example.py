#!/usr/bin/env python3
"""
Structured Logging Example

This script demonstrates how to use the structured logging functionality
implemented in the loan management system.
"""

import os
import logging
import json
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
import uuid
import socket
import platform
import sys
import random

def setup_logging():
    """Configure structured logging with rotation."""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    class JsonFormatter(logging.Formatter):
        """Format log records as JSON objects."""
        def __init__(self):
            super().__init__()
            self.hostname = socket.gethostname()
            self.app_name = "structured_logging_example"
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
        'logs/example.log',
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

def simulate_loan_operations():
    """Simulate various loan operations with structured logging."""
    # Simulate loan data
    loan_ids = [f"LOAN-{i:04d}" for i in range(1, 6)]
    client_ids = [f"CLIENT-{i:04d}" for i in range(1, 10)]
    operations = ["payment_reminder", "due_date_reminder", "apply_penalty", "send_statement", "record_payment"]
    
    # Simulate a series of operations
    for _ in range(20):
        # Pick a random loan and operation
        loan_id = random.choice(loan_ids)
        client_id = random.choice(client_ids)
        operation = random.choice(operations)
        
        # Simulate success or failure
        success = random.random() > 0.2  # 80% success rate
        
        # Create context data
        loan_data = {
            "loan_id": loan_id,
            "amount": round(random.uniform(1000, 10000), 2),
            "remaining_balance": round(random.uniform(0, 5000), 2),
            "status": random.choice(["active", "overdue", "completed"])
        }
        
        client_data = {
            "client_id": client_id,
            "name": f"Client {client_id[-4:]}",
            "email": f"client{client_id[-4:]}@example.com"
        }
        
        operation_data = {
            "operation_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "duration_ms": random.randint(10, 500)
        }
        
        # Log the operation
        if success:
            logging.info_with_context(
                f"Successfully performed {operation} for loan {loan_id}",
                operation=operation,
                loan=loan_data,
                client=client_data,
                performance=operation_data,
                success=True
            )
        else:
            error_types = ["DatabaseError", "ConnectionError", "ValidationError", "TimeoutError"]
            error_type = random.choice(error_types)
            error_message = f"Failed to perform {operation}: {error_type}"
            
            logging.error_with_context(
                error_message,
                operation=operation,
                loan=loan_data,
                client=client_data,
                performance=operation_data,
                success=False,
                error_type=error_type,
                error=error_message
            )
        
        # Sleep briefly to space out the logs
        time.sleep(0.1)

def simulate_database_operations():
    """Simulate database operations with structured logging."""
    tables = ["loans", "clients", "payments", "gun_licences"]
    operations = ["query", "insert", "update", "delete"]
    
    for _ in range(10):
        table = random.choice(tables)
        operation = random.choice(operations)
        record_count = random.randint(1, 100)
        duration_ms = random.randint(5, 200)
        success = random.random() > 0.1  # 90% success rate
        
        if success:
            logging.info_with_context(
                f"Database {operation} on {table} table completed",
                operation=f"db_{operation}",
                table=table,
                record_count=record_count,
                duration_ms=duration_ms,
                success=True
            )
        else:
            error_message = f"Database error during {operation} on {table}"
            logging.error_with_context(
                error_message,
                operation=f"db_{operation}",
                table=table,
                duration_ms=duration_ms,
                success=False,
                error_type="DatabaseError",
                error=error_message
            )
        
        time.sleep(0.1)

def simulate_email_operations():
    """Simulate email operations with structured logging."""
    email_types = ["payment_reminder", "due_date_reminder", "overdue_notice", "statement", "receipt"]
    recipients = [f"client{i:02d}@example.com" for i in range(1, 6)] + ["admin@example.com"]
    
    for _ in range(15):
        email_type = random.choice(email_types)
        recipient = random.choice(recipients)
        subject = f"{email_type.replace('_', ' ').title()} - {datetime.now().strftime('%Y-%m-%d')}"
        size_kb = random.randint(5, 50)
        success = random.random() > 0.15  # 85% success rate
        
        if success:
            logging.info_with_context(
                f"Email sent to {recipient}",
                operation="send_email",
                email_type=email_type,
                recipient=recipient,
                subject=subject,
                size_kb=size_kb,
                success=True
            )
        else:
            error_types = ["SMTPError", "ConnectionError", "TimeoutError"]
            error_type = random.choice(error_types)
            error_message = f"Failed to send email: {error_type}"
            
            logging.error_with_context(
                error_message,
                operation="send_email",
                email_type=email_type,
                recipient=recipient,
                subject=subject,
                size_kb=size_kb,
                success=False,
                error_type=error_type,
                error=error_message
            )
        
        time.sleep(0.1)

def main():
    """Run the structured logging example."""
    setup_logging()
    
    logging.info("Starting structured logging example")
    
    # Simulate different types of operations
    simulate_loan_operations()
    simulate_database_operations()
    simulate_email_operations()
    
    logging.info("Structured logging example completed")
    
    print("\nExample completed. Check the logs/example.log file for structured JSON logs.")
    print("You can analyze these logs with the log_analyzer.py script.")

if __name__ == "__main__":
    main() 