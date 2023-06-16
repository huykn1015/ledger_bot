import pandas as pd
from dataclasses import dataclass, asdict, field

@dataclass
class account:
    owner: str
    balance: str


accounts = pd.read_csv('accounts.csv')

def get_account(account_name):
    if(account_name in set(accounts['account'])):
        return None
    account_balance = df.loc[account_name, 'balance']

def update_account(account_update):
