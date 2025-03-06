import logging
from datetime import datetime
import calendar
import os
import base64

def create_invoice_email(loan: dict, is_quote=True) -> str:
    """
    Create an HTML email for a loan payment statement or invoice.
    
    Args:
        loan: Dictionary containing loan and client information
        is_quote: If True, generate a statement email. If False, generate an invoice email (for fully paid loans)
    """
    client = loan['client']
    due_date = datetime.fromisoformat(loan['payment_due_date'].replace('Z', '+00:00'))
    
    # Set the due date to the 28th of the month
    last_day = calendar.monthrange(due_date.year, due_date.month)[1]
    due_date = due_date.replace(day=min(28, last_day))
    
    formatted_due_date = due_date.strftime('%B %d, %Y')
    
    # Document type
    document_type = "Statement" if is_quote else "Invoice"
    
    # Email subject prefix
    email_subject_prefix = "Gunnery Payment Due Quote" if is_quote else "Gunnery Payment Confirmation"
    
    # Calculate the payment amount
    # Base payment is loan amount divided by 3
    loan_amount = float(loan['loan_amount'])
    base_payment = round(loan_amount / 3, 2)
    
    # Check if there are penalties (missed payments)
    penalties = loan.get('penalties', 0)
    missed_payment_amount = 0
    
    # If there are penalties, add 10% to the amount due plus the missed payment amount
    if penalties > 0:
        missed_payment_amount = penalties * base_payment
        penalty_amount = missed_payment_amount * 0.1  # 10% penalty
        payment_amount = base_payment + missed_payment_amount + penalty_amount
    else:
        payment_amount = base_payment
    
    # Round the final payment amount
    payment_amount = round(payment_amount, 2)
    
    # Get loan start date
    start_date = datetime.fromisoformat(loan['start_date'].replace('Z', '+00:00'))
    
    # Calculate payment schedule dates
    first_payment_month = start_date.replace(month=start_date.month+1 if start_date.month < 12 else 1, 
                                         year=start_date.year if start_date.month < 12 else start_date.year+1)
    second_payment_month = first_payment_month.replace(month=first_payment_month.month+1 if first_payment_month.month < 12 else 1,
                                                  year=first_payment_month.year if first_payment_month.month < 12 else first_payment_month.year+1)
    third_payment_month = second_payment_month.replace(month=second_payment_month.month+1 if second_payment_month.month < 12 else 1,
                                                 year=second_payment_month.year if second_payment_month.month < 12 else second_payment_month.year+1)
    
    # Email intro based on document type
    if is_quote:
        email_intro = f"This is a notification regarding your upcoming loan payment due on <strong>{formatted_due_date}</strong>."
    else:
        email_intro = "Thank you for your loan payments. This email contains your official invoice confirming the loan has been paid in full."
    
    # Get weapon description - use make from gun_licences if available
    weapon_make = loan.get('gun_licence_make', '')
    weapon_type = loan.get('gun_licence_type', '')
    weapon_caliber = loan.get('gun_licence_caliber', '')
    
    # Create a more detailed weapon description if we have the gun licence data
    if weapon_make and weapon_type:
        if weapon_caliber:
            weapon_description = f"{weapon_make} {weapon_type} {weapon_caliber}"
        else:
            weapon_description = f"{weapon_make} {weapon_type}"
    else:
        # Fallback to the generic description
        weapon_description = loan.get('weapon_description', 'Firearm Loan')
    
    loan_amount = float(loan['loan_amount'])
    remaining_balance = float(loan['remaining_balance'])
    
    # Use the deposit_amount calculated in loans.py
    deposit_amount = loan.get('deposit_amount', 0)
    
    # Calculate payment per period
    payment_per_period = remaining_balance / 2 if remaining_balance > 0 else 0
    
    # Use the logo directly from the website URL
    logo_url = "https://web.gunneryguns.com/gunnery_logo.png"
    
    penalties_html = f"""
    <div style="padding: 12px; color: #666; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
        <div style="font-weight: bold; margin-bottom: 5px;">Payment Breakdown:</div>
        <div style="color: #333; font-size: 15px; margin-top: 8px;"><strong>Regular Payment:</strong> R {base_payment:,.2f}</div>
        <div style="color: #333; font-size: 15px; margin-top: 5px;"><strong>Missed Payments ({penalties}):</strong> R {missed_payment_amount:,.2f}</div>
        <div style="color: #333; font-size: 15px; margin-top: 5px;"><strong>Penalty (10%):</strong> R {penalty_amount:,.2f}</div>
        <div style="color: #333; font-size: 15px; margin-top: 8px; font-weight: bold; color: #d9534f;">Total Due: R {payment_amount:,.2f}</div>
    </div>
    """ if penalties > 0 else ''
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{email_subject_prefix}: {loan['invoice_number']}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 20px;
                padding-bottom: 10px;
            }}
            .logo {{
                max-width: 200px;
                height: auto;
            }}
            .details {{
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .detail-row {{
                margin-bottom: 10px;
            }}
            .detail-label {{
                font-weight: bold;
            }}
            .bank-details {{
                background-color: #f9f9f9;
                padding: 15px;
                border-radius: 5px;
                margin-top: 20px;
                border-left: 4px solid #333;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 12px;
                color: #777;
                border-top: 1px solid #ddd;
                padding-top: 10px;
            }}
            .amount {{
                font-size: 18px;
                font-weight: bold;
                color: #d9534f;
            }}
            .content-box {{
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border: 1px solid #eee;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
            .terms-box {{
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border: 1px solid #eee;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{logo_url}" alt="Gunnery Arms & Ammo" class="logo">
            </div>
            
            <p style="color: #555; margin-bottom: 15px;">Dear {client['first_name']} {client['last_name']},</p>
            
            <p style="color: #555; margin-bottom: 15px;">{email_intro}</p>
            
            <div class="content-box">
                <h3 style="color: #333; margin-top: 0; font-size: 18px;">Payment Plan:</h3>
                <div style="padding: 12px; color: #666; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
                    <div style="font-weight: bold; margin-bottom: 5px;">Item</div>
                    <div style="color: #333; font-size: 15px;">{weapon_description}</div>
                </div>
            </div>
            
            <h3 style="color: #333; margin-top: 20px; font-size: 18px;">Payment Summary:</h3>
            <!-- Mobile-friendly display for small screens -->
            <div style="display: block; margin-bottom: 20px;">
                <div style="padding: 12px; color: #666; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
                    <div style="font-weight: bold; margin-bottom: 5px;">Total Loan Amount</div>
                    <div style="color: #333; font-size: 15px;">R {loan_amount:,.2f}</div>
                </div>
                <div style="padding: 12px; color: #666; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
                    <div style="font-weight: bold; margin-bottom: 5px;">#1 Payment Made</div>
                    <div style="color: #333; font-size: 15px;">R {deposit_amount:,.2f}</div>
                </div>
                <div style="padding: 12px; color: #666; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
                    <div style="font-weight: bold; margin-bottom: 5px;">Remaining Balance</div>
                    <div style="color: #333; font-size: 15px;">R {remaining_balance:,.2f}</div>
                </div>
                <div style="padding: 12px; color: #666; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
                    <div style="font-weight: bold; margin-bottom: 5px;">Payment Due Date</div>
                    <div style="color: #333; font-size: 15px;">{formatted_due_date}</div>
                </div>
                <div style="padding: 12px; color: #666; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
                    <div style="font-weight: bold; margin-bottom: 5px;">Payment Amount</div>
                    <div style="color: #333; font-size: 15px;">R {base_payment if penalties == 0 else payment_amount:,.2f}</div>
                </div>
                {penalties_html}
            </div>
            
            <h3 style="color: #333; margin-top: 20px; font-size: 18px;">Bank Details:</h3>
            <div style="padding: 12px; color: #666; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
                <p style="margin: 5px 0;"><strong>Bank:</strong> Standard Bank-Helderberg</p>
                <p style="margin: 5px 0;"><strong>Account Type:</strong> BUSINESS CURRENT ACCOUNT</p>
                <p style="margin: 5px 0;"><strong>Account Number:</strong> 07 243 9351</p>
                <p style="margin: 5px 0;"><strong>Branch Code:</strong> 03-30-12</p>
                <p style="margin: 5px 0;"><strong>Reference:</strong> QUO{loan['invoice_number']}</p>
            </div>
            
            <!-- Terms & Conditions in its own container -->
            <div class="terms-box">
                <h3 style="color: #333; margin-top: 0; font-size: 18px;">Terms & Conditions:</h3>
                <div style="padding: 12px; color: #666; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
                    <p style="margin: 5px 0;">Please use your quote number as the payment reference (accounts@gunneryguns.com). Quotes are valid for 12 hours.</p>
                    <p style="margin: 10px 0;">Firearms will be stored for a period of 12 months from date of sale, thereafter a storage fee of R190.00 per month applies. To refund a firearm (new or used) that is stored at Gunnery Arms & Ammo from date of sale, 25% of the total purchase price will be deducted from the refundable amount.</p>
                    <p style="margin: 10px 0;">Firearms purchased on payment plans will strictly be three months/90 days. Thereafter, a 10% penalty increase on the total amount will be applicable per month.</p>
                    <p style="margin: 10px 0;">Shipping is at clients own risk.</p>
                    <p style="margin: 10px 0;">There is a 50% cancellation fee on all proficiency courses, and all proficiency courses will expire after 12 months from date of purchase. No-shows and cancellations within 72 hours of the class will lead to a penalty fee.</p>
                    <p style="margin: 10px 0;">Goods remain property of Gunnery Arms & Ammo until paid in full. Thank you for the support!</p>
                </div>
            </div>
            
            <p style="color: #555; margin-top: 30px; margin-bottom: 15px;">Thank you,<br>Gunnery Arms & Ammo<br>Contact: 021 851 6548</p>
            
            <div style="margin-top: 30px; font-size: 12px; color: #999; border-top: 1px solid #eee; padding-top: 15px;">
                <p style="margin: 5px 0;">This is an automated email. Please do not reply to this message.</p>
                <p style="margin: 5px 0;">© {due_date.year} Gunnery Arms & Ammo</p>
            </div>
        </div>
    </body>
    </html>
    """ 