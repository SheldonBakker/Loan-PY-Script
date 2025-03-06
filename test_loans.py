import os
import logging
import calendar
from dotenv import load_dotenv
from datetime import datetime
import sys
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("SUPABASE_URL and SUPABASE_KEY must be set in the environment variables.")
    sys.exit(1)

def is_third_last_day_of_month() -> bool:
    """Check if today is the 3rd last day of the month."""
    today = datetime.now()
    # Get the last day of the current month
    last_day = calendar.monthrange(today.year, today.month)[1]
    # Calculate the 3rd last day
    third_last_day = last_day - 2
    
    return today.day == third_last_day

def test_supabase_connection():
    """Test the connection to Supabase."""
    try:
        logging.info(f"Connecting to Supabase at: {SUPABASE_URL}")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Try a simple query to test the connection
        response = supabase.table('clients').select('count', count='exact').limit(1).execute()
        
        logging.info(f"Successfully connected to Supabase")
        logging.info(f"Found {response.count} clients in the database")
        
        return True
    except Exception as e:
        logging.error(f"Failed to connect to Supabase: {e}")
        return False

def calculate_third_last_day():
    """Calculate and display the 3rd last day of the current month."""
    today = datetime.now()
    last_day = calendar.monthrange(today.year, today.month)[1]
    third_last_day = last_day - 2
    
    logging.info(f"Current month: {today.strftime('%B %Y')}")
    logging.info(f"Last day of the month: {last_day}")
    logging.info(f"3rd last day of the month: {third_last_day}")
    
    if today.day == third_last_day:
        logging.info("Today IS the 3rd last day of the month.")
    else:
        logging.info(f"Today ({today.day}) is NOT the 3rd last day of the month.")

def main():
    """Run basic tests."""
    logging.info("Starting test script")
    
    # Test Supabase connection
    if test_supabase_connection():
        logging.info("Supabase connection test: PASSED")
    else:
        logging.error("Supabase connection test: FAILED")
    
    # Calculate 3rd last day of the month
    calculate_third_last_day()
    
    logging.info("Test script completed")

if __name__ == "__main__":
    main() 