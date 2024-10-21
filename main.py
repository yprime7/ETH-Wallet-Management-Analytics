import sqlite3
import requests
from datetime import datetime
from tabulate import tabulate
import matplotlib.pyplot as plt

API_KEY = "Enter Etherscan your API key here"
BASE_URL = "https://api.etherscan.io/api"
ETHER_VALUE = 1e18

def fetch_data(module, action, address, **kwargs):
    # Constructs and fetches data from the Etherscan API
    url = f"{BASE_URL}?module={module}&action={action}&address={address}&apikey={API_KEY}"
    url += ''.join([f"&{key}={value}" for key, value in kwargs.items()])
    response = requests.get(url)
    
    try:
        data = response.json()
        # Ensure that 'result' is a list before returning
        if isinstance(data.get("result"), list):
            return data["result"]
        else:
            print(f"Unexpected response format: {data}")
            return []
    except ValueError:
        print("Error: Could not decode JSON from response.")
        return []

def fetch_transactions(address):
    # Fetches normal and internal transactions for an Ethereum address
    transactions = fetch_data("account", "txlist", address, startblock=0, endblock=99999999, page=1, offset=10000, sort="asc")
    internal_transactions = fetch_data("account", "txlistinternal", address, startblock=0, endblock=99999999, page=1, offset=10000, sort="asc")
    
    # Combine and sort transactions if both lists are valid
    if transactions and internal_transactions:
        return sorted(transactions + internal_transactions, key=lambda x: int(x.get('timeStamp', 0)))
    else:
        print("Error: Failed to fetch transactions.")
        return []

def save_transactions_to_db(address):
    # Fetches transactions and saves them to an SQLite database
    data = fetch_transactions(address)

    if not data:
        print("No transactions found or an error occurred.")
        return

    with sqlite3.connect('transactions.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                     (to_address text, from_address text, value real, gas_cost real, time timestamp)''')

        for tx in data:
            to_address = tx.get("to", "")
            from_address = tx.get("from", "")
            value = int(tx.get("value", 0)) / ETHER_VALUE
            gas_cost = int(tx.get("gasUsed", 0)) * int(tx.get("gasPrice", 0)) / ETHER_VALUE if "gasPrice" in tx else int(tx.get("gasUsed", 0)) / ETHER_VALUE
            timestamp = datetime.fromtimestamp(int(tx.get('timeStamp', 0)))

            c.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?)", 
                      (to_address, from_address, value, gas_cost, timestamp))
        conn.commit()

def display_transactions():
    # Displays transaction data from the SQLite database in a tabular format
    with sqlite3.connect('transactions.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM transactions")
        rows = c.fetchall()

    headers = ["To Address", "From Address", "Value", "Gas Cost", "Time"]
    formatted_rows = [(row[0], row[1], f"{row[2]:.8f}", f"{row[3]:.8f}", row[4]) for row in rows]
    print(tabulate(formatted_rows, headers=headers, tablefmt="grid"))

def plot_balance_over_time():
    # Plots the account balance over time using transaction data
    with sqlite3.connect('transactions.db') as conn:
        c = conn.cursor()
        c.execute("SELECT time, value, gas_cost FROM transactions ORDER BY time")
        rows = c.fetchall()

    balances = []
    times = []
    current_balance = 0

    for time, value, gas_cost in rows:
        current_balance += value - gas_cost
        balances.append(current_balance)
        times.append(time)

    plt.plot(times, balances)
    plt.xlabel('Time')
    plt.ylabel('Account Value')
    plt.title('Account Value Over Time')
    plt.show()

# Example usage
address = "0x5d1831d8e81e7897450685a302dbd7df0cd8349faca87722af0bcaa1d38b24a2"
save_transactions_to_db(address)
display_transactions()
plot_balance_over_time()
