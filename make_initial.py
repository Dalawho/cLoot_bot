"""
Script to generate initial svg pictures, metadata and a list with everything to be used by the bot

"""


import json
import subprocess

import pandas as pd
import pickle
import tqdm

import text_to_svg as tts

inp = pd.read_pickle("name_list.pkl")
inp = inp[0].to_list()

df = pd.DataFrame(columns = ["text", "numbers", "ipfs", "metadata" , "policy_id", "sold", "pic"])
token_pics = pd.DataFrame(columns = ["word", "hash", "pic"])

for i, word in enumerate(tqdm.tqdm(inp)):
    if word not in token_pics["word"].to_list():
        tts.make_svg([word], str(i))
        file_hash = tts.ipfs_upload(f"pics/{i}.svg")
        token_pics = token_pics.append({"word": word, "hash" : file_hash, "pic" : f"pics/{i}.svg"}, ignore_index = True)
    else:
        file_hash = token_pics.loc[token_pics["word"] == word]["hash"].to_list()[0]
    pic = token_pics.loc[token_pics["word"] == word]["pic"].to_list()[0]
    df = df.append({"text": word, "numbers": i, "ipfs": file_hash, "metadata": f"metadata/meta-{i}.json","policy_id" :"policyID", "sold" : 0,"pic" : pic}, ignore_index = True)
    d = tts.build_ingredient_dict("<policyID>", word, i, f"{file_hash}")
    with open(f"metadata/meta-{i}.json", 'w') as f:
        json.dump(d, f)
df.to_pickle("df.pkl")
