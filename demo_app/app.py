"""Demo legacy banking application - intentionally hostile UI."""
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
import random

app = Flask(__name__)

# Mock member database
MEMBERS = {
    "12345": {
        "id": "12345",
        "name": "John Doe",
        "savings_balance": "$5,432.10",
        "checking_balance": "$1,234.56"
    },
    "67890": {
        "id": "67890",
        "name": "Jane Smith",
        "savings_balance": "$12,345.67",
        "checking_balance": "$3,456.78"
    }
}

# Mock transaction data
TRANSACTIONS = {
    "12345": [
        {"date": "2024-01-15", "time": "09:23:45", "description": "Direct Deposit - Payroll", "account": "Checking", "type": "credit", "amount": "+$2,500.00", "balance": "$1,234.56"},
        {"date": "2024-01-14", "time": "14:32:11", "description": "ATM Withdrawal", "account": "Checking", "type": "debit", "amount": "-$100.00", "balance": "$-1,265.44"},
        {"date": "2024-01-12", "time": "10:15:22", "description": "Transfer to Savings", "account": "Checking", "type": "debit", "amount": "-$500.00", "balance": "$-1,165.44"},
        {"date": "2024-01-12", "time": "10:15:22", "description": "Transfer from Checking", "account": "Savings", "type": "credit", "amount": "+$500.00", "balance": "$5,432.10"},
        {"date": "2024-01-10", "time": "16:45:33", "description": "Interest Payment", "account": "Savings", "type": "credit", "amount": "+$12.10", "balance": "$4,932.10"},
    ],
    "67890": [
        {"date": "2024-01-16", "time": "11:20:15", "description": "Check Deposit", "account": "Checking", "type": "credit", "amount": "+$1,200.00", "balance": "$3,456.78"},
        {"date": "2024-01-15", "time": "08:30:45", "description": "Online Bill Payment", "account": "Checking", "type": "debit", "amount": "-$150.00", "balance": "$2,256.78"},
        {"date": "2024-01-13", "time": "13:12:00", "description": "Dividend Payment", "account": "Savings", "type": "credit", "amount": "+$45.67", "balance": "$12,345.67"},
    ]
}


@app.route('/')
def index():
    """Landing page."""
    return render_template('index.html')


@app.route('/search')
def search():
    """Member search page."""
    return render_template('search.html')


@app.route('/member/<member_id>')
def member_detail(member_id):
    """Member detail page."""
    member = MEMBERS.get(member_id)
    
    if not member:
        return render_template('search.html', error="Member not found"), 404
    
    return render_template('member_detail.html', member=member)


@app.route('/add-account', methods=['GET', 'POST'])
def add_account():
    """Add new account page."""
    if request.method == 'POST':
        member_id = request.form.get('member_id', '').strip()
        account_type = request.form.get('account_type', '')
        initial_deposit = request.form.get('initial_deposit', '')
        
        # Validate member exists
        if member_id not in MEMBERS:
            return render_template('add_account.html', error="Member not found. Please verify the Member ID.")
        
        # Validate account type
        if not account_type:
            return render_template('add_account.html', error="Please select an account type.")
        
        # Validate initial deposit
        try:
            deposit_amount = float(initial_deposit)
            if deposit_amount < 0:
                return render_template('add_account.html', error="Initial deposit cannot be negative.")
            
            # Business rules
            if account_type == 'savings' and deposit_amount < 25:
                return render_template('add_account.html', error="Savings accounts require a minimum deposit of $25.00")
            
            if account_type == 'cd' and deposit_amount < 1000:
                return render_template('add_account.html', error="Certificate of Deposit requires a minimum deposit of $1,000.00")
            
        except ValueError:
            return render_template('add_account.html', error="Invalid deposit amount.")
        
        # Success - in real app, would create account in database
        success_msg = f"Account application submitted successfully for Member {member_id}. Account Type: {account_type.replace('_', ' ').title()}, Initial Deposit: ${deposit_amount:.2f}"
        return render_template('add_account.html', success=success_msg)
    
    return render_template('add_account.html')


@app.route('/transactions')
def transactions():
    """Transaction history page."""
    member_id = request.args.get('member_id', '').strip()
    account_type = request.args.get('account_type', '')
    
    if not member_id:
        return render_template('transactions.html', transactions=None, member_id=None)
    
    # Validate member exists
    if member_id not in MEMBERS:
        return render_template('transactions.html', error="Member not found", member_id=member_id)
    
    # Get transactions for member
    txns = TRANSACTIONS.get(member_id, [])
    
    # Filter by account type if specified
    if account_type:
        txns = [t for t in txns if t['account'].lower() == account_type.lower()]
    
    return render_template('transactions.html', 
                         transactions=txns, 
                         member_id=member_id,
                         account_type=account_type)


if __name__ == '__main__':
    app.run(port=5000, debug=True)