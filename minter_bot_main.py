# -*- coding: utf-8 -*-
"""
Bot that listens to a cardano address and:
- Returns Ada if < 19ADA and no NFTs are attached
- Sends 10 NFTs to sender if 19 ADA is send
- Sends 20 NFTS to sender if 24 ADA is send
- Sends a combined NFT if NFTs + 4 ADA is recieved
"""

import os
import subprocess
import time
import random
import json
import re
import requests

import pandas as pd

import text_to_svg as tts

# Some global parameters
CARDANO_CLI_PATH = "../cardano-cli" #edit
CARDANO_KEYS_DIR = "keys" #edit

def build_raw_mint(fee, txhash, txix, out_addr1, out_addr2, in_lovelace,
                   policy_id, tokens, script, metadata, out_file = "matx.raw", burn_tokens = []):
    """
    Generates the raw transaction for sending newly minted ingredients.
    Always sends along 2 Ada, to be on the safe side for the minimal transfer amount
    Can also burn tokens
    """
    for i, token in enumerate(tokens):
        if i == 0:
            mint = f"1 {policy_id}.{token}"
        else:
            mint = mint + f" +1 {policy_id}.{token}"
    command =[CARDANO_CLI_PATH, "transaction", "build-raw",
    '--fee', str(fee),
    '--tx-in', f"{txhash}#{txix}",
    '--tx-out', f"{out_addr1}+{in_lovelace - 4000000}",
    '--tx-out', f"{out_addr2}+{4000000 - fee}+{mint}",
    '--minting-script-file', script,
    '--metadata-json-file', metadata,
    '--invalid-hereafter', "48716321",
    '--out-file', out_file]
    if len(burn_tokens) > 0:
        for btoken in burn_tokens:
            mint = mint + f" +-1 {policy_id}.{btoken}"
    command.append(f"--mint={mint}")    
    _ = subprocess.check_output(command)

def build_raw_bake(fee, txhash, txix, out_addr1, out_addr2, in_lovelace,
                   policy_id, tokens, script, metadata, out_file = "matx.raw", burn_tokens = []):
    """
    Generates raw transaction if ingredients are send to be baked into a cake
    Sends all ADA back (min is around 1.8), mints a cake and burns all ingredients
    out_addr1 is not actually used... 
    """
    for i, token in enumerate(tokens):
        if i == 0:
            mint = f"1 {policy_id}.{token}"
        else:
            mint = mint + f" +1 {policy_id}.{token}"
    command =[CARDANO_CLI_PATH, "transaction", "build-raw",
    '--fee', str(fee),
    '--tx-in', f"{txhash}#{txix}",
    '--tx-out', f"{out_addr2}+{in_lovelace - fee}+{mint}",
    '--minting-script-file', script,
    '--metadata-json-file', metadata,
    '--invalid-hereafter', "48716321",
    '--out-file', out_file]
    if len(burn_tokens) > 0:
        for btoken in burn_tokens:
            mint = mint + f" +-1 {policy_id}.{btoken}"
    command.append(f"--mint={mint}")    
    _ = subprocess.check_output(command)

def build_raw_send(fee, txhash, txix, out_addr1, in_lovelace, out_file = "matx.raw"):
    """
    only send ada, use to get money to nami or other wallets from the main payment addr
    """
    command =[CARDANO_CLI_PATH, "transaction", "build-raw",
    '--fee', str(fee),
    '--tx-in', f"{txhash}#{txix}",
    '--tx-out', f"{out_addr1}+{in_lovelace - fee}",
    '--out-file', out_file]
    _ = subprocess.check_output(command)
    
def get_fee(tx_body_file = "matx.raw", tx_in = 1, tx_out = 2, witness_count = 1, protocol_params = "mainnet-protocol.json"):
    """
    Calulcates the fee on mainnet for a given transaction
    """
    fee = subprocess.check_output([
    CARDANO_CLI_PATH, "transaction", "calculate-min-fee",
    '--tx-body-file', tx_body_file,
    "--tx-in-count", str(tx_in),
    "--tx-out-count", str(tx_out),
    "--witness-count", str(witness_count),
    "--protocol-params-file", protocol_params,
    "--mainnet"])
    return int(fee.split()[0])

def sign_tx(pay_key = "keys/payment.skey", policy_key = "policy/policy.skey",
            tx_body = "matx.raw", out_file = "matx.signed"):
    """
    Signs a raw transcation 
    """
    _ = subprocess.check_output([
    CARDANO_CLI_PATH, "transaction", "sign",
    "--signing-key-file", pay_key,
    "--signing-key-file", policy_key,
    '--tx-body-file', tx_body,
    "--out-file", out_file,
    "--mainnet"])

def sign_tx_only_ada(pay_key = "keys/payment.skey", tx_body = "matx.raw", out_file = "matx.signed"):
    """
    Signs a raw transcation 
    """
    _ = subprocess.check_output([
    CARDANO_CLI_PATH, "transaction", "sign",
    "--signing-key-file", pay_key,
    '--tx-body-file', tx_body,
    "--out-file", out_file,
    "--mainnet"])

def submit_tx(tx_file = "matx.signed"):
    """
    Submits the signed transaction to testnet
    """
    answer = subprocess.check_output([
    CARDANO_CLI_PATH, "transaction", "submit",
    "--tx-file", tx_file, "--mainnet"])
    print(answer)

def get_utxo(walletAddress, line = 2):
    """
    Gets one line (2 is the latest utxo) utxo and returns the transaction hash, txix and lovelace amount
    """
    rawUtxoTable = subprocess.check_output([
    CARDANO_CLI_PATH,
    'query', 'utxo',
    "--mainnet", '--address', walletAddress])
    utxo_line = rawUtxoTable.strip().splitlines()[line].split()
    #print(utxo_line)
    return str(utxo_line[0].decode("utf-8")), str(utxo_line[1].decode("utf-8")), int(utxo_line[2].decode("utf-8"))

def get_full_utxo(walletAddress, line = 2):
    """
    Gets all utxos sitting a certain address.
    Currently the bot is setup to process all incoming utxos and leave no dangling ends at it's own address
    """
    rawUtxoTable = subprocess.check_output([
    CARDANO_CLI_PATH,
    'query', 'utxo',
    "--mainnet",
    '--address', walletAddress])
    utxo_line = rawUtxoTable.strip().splitlines()[line].split()
    return [x.decode("utf-8") for x in utxo_line]

def get_all_utxos(walletAddress):
    """
    Gets all utxos sitting a certain address.
    Currently the bot is setup to process all incoming utxos and leave no dangling ends at it's own address
    """
    rawUtxoTable = subprocess.check_output([
    CARDANO_CLI_PATH,
    'query', 'utxo',
    "--mainnet",
    '--address', walletAddress])
    full_utxo = rawUtxoTable.strip().splitlines()[2:]
    return [x.decode("utf-8") for x in full_utxo]
    
def mint_tokens(tokens, metadata, out_addr1, out_addr2, policy_id,
               script, walletAddress, txhash, txix, in_lovelace, burn_tokens = []):
    """
    Combines above functions to mint new tokens. 
    """
    #fee starts out as 0 and gets calucated once we have the transaction
    fee = 0
    #get utxo data
    #txhash, txix, in_lovelace = get_utxo(walletAddress)
    #make raw minting transcation
    build_raw_mint(fee, txhash, txix, out_addr1, out_addr2, in_lovelace,
                   policy_id, tokens, script, metadata, burn_tokens = burn_tokens)
    #calulcate fee based on above transaction
    fee = get_fee()
    #makes a new transcation wit hthe right fee
    build_raw_mint(fee, txhash, txix, out_addr1, out_addr2, in_lovelace,
                   policy_id, tokens, script, metadata, burn_tokens = burn_tokens)
    #Sign and
    sign_tx(pay_key = "keys/minter.skey")
    #Deliver
    submit_tx()

def bake_cake(tokens, metadata, out_addr1, out_addr2, policy_id,
               script, walletAddress, txhash, txix, in_lovelace, burn_tokens = []):
    fee = 0
    build_raw_bake(fee, txhash, txix, out_addr1, out_addr2, in_lovelace,
                   policy_id, tokens, script, metadata, burn_tokens = burn_tokens)
    fee = get_fee(tx_out = 1)
    build_raw_bake(fee, txhash, txix, out_addr1, out_addr2, in_lovelace,
                   policy_id, tokens, script, metadata, burn_tokens = burn_tokens)
    sign_tx(pay_key = "keys/minter.skey")
    submit_tx()

def combine_meta(send_df, policy_id):
    t = {}
    for i, row in send_df.iterrows():
        with open(row["metadata"], "r") as json_file:
            token_dict = json.load(json_file)
        t = {**t, **token_dict["721"][policy_id]}
    res = {"721" : {policy_id : t}}
    path = f"send_meta/meta-{'-'.join([str(x) for x in send_df.index])}.json"
    with open(path, "w") as json_file:
        json.dump(res, json_file)
    return path

def make_poem(token_nums, df, new_rowi):
    """
    should return a series to be put at the end of the dataframe
    Having a list in a df cell is apparently a pain so words are joined with "_" 
    """
    print(token_nums)
    words = df.iloc[token_nums,0].to_list()
    words_out = []
    for word in words:
        print(word)
        if "_" in word:
            j = word.rsplit("_")
            print(j)
            words_out = words_out + j
        else:
            words_out.append(word)
    print(words_out)
    tts.make_svg(words_out, str(new_rowi))
    file_hash = tts.ipfs_upload(f"pics/{new_rowi}.svg")
    tts.pin(file_hash, f"{new_rowi}.svg")
    ser = pd.DataFrame({"text": "_".join(words_out), "numbers": new_rowi, "ipfs": file_hash, "metadata": f"metadata/meta-{new_rowi}.json",
                    "policy_id" :"<policyID>", "sold" : 1, "pic" : f"pics/{new_rowi}.svg"}, index = [new_rowi])
    d = tts.build_ingredient_dict("<policyID>", words_out, new_rowi, f"{file_hash}")
    with open(f"metadata/meta-{new_rowi}.json", 'w') as f:
        json.dump(d, f)
    return ser 
        
def get_send_addr(txhash):
    url = f"https://cardano-mainnet.blockfrost.io/api/v0/txs/{txhash}/utxos"
    headers = {'project_id': '<project_id>'}
    r = requests.get(url, headers=headers)
    d = r.json()
    inp = d["inputs"][0]
    return(inp["address"])

def tokens_purchased(token_nr, txhash, txix, in_lovelace):
    print("purchased one bag!")
    send_df = pd.DataFrame(columns = df.columns)
    print("slecting guys")
    for i in range(token_nr):
        token = random.choice(df.loc[df.sold == 0].index)
        send_df = send_df.append(df.iloc[token])
        df.iloc[token,5] = 1
    print("loop run")
    meta_to_send = combine_meta(send_df, policy_id)
    print("combine meta run")
    out_addr2 = get_send_addr(txhash)
    mint_tokens([f"cLoot{x}" for x in send_df.numbers.to_list()], meta_to_send, out_addr1, out_addr2, policy_id, script, minterAddress, txhash, txix, in_lovelace)

def return_ada(txhash, txix, in_lovelace):
    #fee starts out as 0 and gets calucated once we have the transaction
    fee = 0
    #make raw minting transcation
    out_addr1 = get_send_addr(txhash)
    build_raw_send(fee, txhash, txix, out_addr1, in_lovelace)
    #calulcate fee based on above transaction
    fee = get_fee(tx_out = 1)
    #makes a new transcation wit hthe right fee
    build_raw_send(fee, txhash, txix, out_addr1, in_lovelace)
    #Sign and
    sign_tx_only_ada(pay_key = "keys/minter.skey")
    #Deliver
    submit_tx()

#This whole block needs to be automated 

out_addr1 = "<mainwallet_addr>" #payment key addr
policy_id = "<policyID>"
script = "policy/policy.script"
                                
# Read wallet address value from payment.addr file
with open(os.path.join(CARDANO_KEYS_DIR, "minter.addr"), 'r') as file:
    minterAddress = file.read()

#df = pd.read_pickle("df.pkl")
df = pd.read_pickle("df_back.pkl")

base_name = "cLoot"

n = 0
tx_processed = []
while 1:
    time.sleep(60)
    print(f"checking {n}")
    all_utxos = get_all_utxos(minterAddress)
    print(all_utxos)
    if len(all_utxos) > 0:
        for full_utxo in all_utxos:
            full_utxo = full_utxo.split()
            in_lovelace = int(full_utxo[2])
            filt_utxo = [x for x in full_utxo if policy_id in x]
            txhash, txix, in_lovelace = [full_utxo[0], str(full_utxo[1]), int(full_utxo[2])]
            if txhash in tx_processed:
                continue
            tx_processed.append(txhash)
            
            if in_lovelace >= 19000000 and in_lovelace < 24000000 and len(df.loc[df.sold == 0]) >= 10: #removed 1 0
                print("purchased 10 tokens")
                tokens_purchased(10, txhash, txix, in_lovelace)
            elif in_lovelace >= 24000000 and len(df.loc[df.sold == 0]) >= 20:
                print("purchase 20 tokens")
                tokens_purchased(20, txhash, txix, in_lovelace)
            elif len(filt_utxo) != 0:
                print("Something to combine")
                strip_utxo = [x.rsplit(".")[1] for x in filt_utxo]
                token_nums = [int(re.findall(r'\d+', x)[0]) for x in strip_utxo]
                new_rowi = len(df)
                df = df.append(make_poem(token_nums, df, new_rowi))
                out_addr2 = get_send_addr(txhash)
                bake_cake([f"{base_name}{new_rowi}"], df.iloc[new_rowi,3], out_addr1, out_addr2, policy_id, script, minterAddress, txhash, txix, in_lovelace, burn_tokens = strip_utxo)
            else:
                print("returning ada")
                return_ada(txhash, txix, in_lovelace)
            df.to_pickle(f"back/df{n}_back.pkl")
    n += 1
