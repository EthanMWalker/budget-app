import json

import mysql.connector
import numpy as np
import pandas as pd
import transactions

SQL_CONFIG_FILE = "data/sql_config.json"
AUTO_CAT_RULES = "data/auto_cat_rules.json"


def load_sql_cfg():
    with open(SQL_CONFIG_FILE, "r") as in_file:
        return json.load(in_file)


class AutoCatRule:
    def __init__(
        self,
        category: str,
        description_contains: list[str],
        account_contains: list[str] = None,
        amount_min: float = -float("inf"),
        amount_max: float = float("inf"),
    ):
        self.category = category
        self.description_contains = np.array(description_contains)
        self.account_contains = np.array(account_contains)
        self.amount_min = amount_min
        self.amount_max = amount_max

    def match(self, df: pd.DataFrame):
        uncat_mask = df.loc[:, "Category"].isna()
        descr_match = df.loc[:, "Description"].str.contains(
            "|".join(self.description_contains)
        )
        acct_match = df.loc[:, "Account"].str.contains("|".join(self.account_contains))
        ammt_match = self.amount_min <= df.loc[:, "Amount"] <= self.amount_max

        df.loc[uncat_mask & descr_match & acct_match & ammt_match] = self.category

        return df


def load_autocat_rules():
    with open(AUTO_CAT_RULES, "r") as in_file:
        rules = json.load(in_file)
    return [AutoCatRule(**rule) for rule in rules]


def auto_cat(df: pd.DataFrame):
    rules = load_autocat_rules()
    for rule in rules:
        df = rule.match(df)
    return df


def ingest_new_transactions():
    transactions_df = transactions.load_transactions()
    raw_transactions_df = transactions.load_raw_transactions()

    last_upload_date = transactions_df.Date.max()

    new_transactions = raw_transactions_df[raw_transactions_df.Date > last_upload_date]
    new_transactions = auto_cat(new_transactions)

    transactions_df = pd.concat([transactions_df, new_transactions], ignore_index=True)

    transactions.write_to_csv(transactions_df)


def write_to_sql():
    cnx = mysql.connector.connect(**load_sql_cfg())