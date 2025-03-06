import os
import logging
from dotenv import load_dotenv
import time
from datetime import datetime, timedelta
from supabase import create_client, Client
from loans import create_invoice_email, send_email, generate_pdf_invoice, SENDER_EMAIL

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_sample_loan():
    """
    Get a sample loan for testing purposes.
    If no loan is found, create a mock loan object.
    """
    try:
        # Try to get a real loan from the database
        response = supabase.table('loans').select(
            'id, invoice_number, loan_amount, remaining_balance, interest_rate, payment_due_date, client_id, status, start_date'
        ).eq('status', 'active').limit(1).execute()
        
        # Check if we got a valid response with loans
        if response.data and len(response.data) > 0:
            loan = response.data[0]
            
            # Check if start_date is present, if not set it to a month ago
            if 'start_date' not in loan or not loan['start_date']:
                loan['start_date'] = (datetime.now() - timedelta(days=30)).isoformat()
            
            # Get client information for this loan
            client_response = supabase.table('clients').select(
                'id, first_name, last_name, email, phone'
            ).eq('id', loan['client_id']).execute()
            
            if client_response.data and len(client_response.data) > 0:
                loan['client'] = client_response.data[0]
                return loan
    except Exception as e:
        logging.error(f"Error fetching sample loan: {e}")
    
    # If we couldn't get a real loan, create a mock one
    # Create a date 30 days ago for start date
    start_date = datetime.now() - timedelta(days=30)
    # Set payment due date to first day of next month
    payment_due_date = datetime.now().replace(day=1) + timedelta(days=32)
    payment_due_date = payment_due_date.replace(day=1)
    
    # Create mock loan with different status options to test both quote and invoice
    status_options = ['active', 'paid']
    
    mock_loan = {
        'id': '123e4567-e89b-12d3-a456-426614174000',
        'invoice_number': 'INV-3434',
        'loan_amount': 10000.00,
        'remaining_balance': 7500.00,
        'interest_rate': 12.0,
        'payment_due_date': payment_due_date.isoformat(),
        'start_date': start_date.isoformat(),
        'status': status_options[int(datetime.now().timestamp()) % 2],
        'client': {
            'id': '123e4567-e89b-12d3-a456-426614174001',
            'first_name': 'Sheldon',
            'last_name': 'Bakker',
            'email': 'acum3n@protonmail.com',  # Use the desired test email
            'phone': '+27 123 456 789'
        }
    }
    
    return mock_loan

def main():
    """
    Send a test email with a PDF invoice to acum3n@protonmail.com.
    """
    logging.info("Starting test email process")
    
    # Get sample loan
    loan = get_sample_loan()
    
    if not loan:
        logging.error("Could not get a sample loan. Exiting.")
        return
    
    try:
        # Use alternating behavior to test both quotes and invoices
        # Comment this out to get the natural behavior from the database:
        loan['status'] = status_options[int(datetime.now().timestamp()) % 2]
        
        # Determine if this is a quote or invoice based on loan status
        is_quote = loan['status'] != 'paid'
        document_type = "Quote" if is_quote else "Invoice"
        email_subject_prefix = "Payment Due" if is_quote else "Payment Confirmation"
        
        logging.info(f"Testing with a {document_type.lower()} for a loan with status: {loan['status']}")
        
        # Create email
        email_subject = f"{email_subject_prefix}: {document_type} {loan['invoice_number']}"
        email_body = create_invoice_email(loan, is_quote)
        
        # Generate PDF
        pdf_data = generate_pdf_invoice(loan, is_quote)
        pdf_filename = f"{document_type}_{loan['invoice_number']}.pdf"
        
        # Save the PDF locally for testing
        with open(pdf_filename, 'wb') as f:
            f.write(pdf_data)
        logging.info(f"PDF saved as {pdf_filename}")
        
        # Send email
        client_full_name = f"{loan['client']['first_name']} {loan['client']['last_name']}"
        send_email(loan['client']['email'], email_subject, email_body, pdf_data, pdf_filename, client_full_name)
        logging.info(f"Test {document_type.lower()} email sent to {loan['client']['email']}")
        
        # Log that no admin summary email is sent
        logging.info("No admin summary email was sent (not enabled for test script)")
        
    except Exception as e:
        logging.error(f"Error in test email process: {e}")
    
    logging.info("Test email process completed")

if __name__ == "__main__":
    main() 