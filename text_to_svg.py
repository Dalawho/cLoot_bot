"""
Functions that:
- make the svg files from a string or array
- Uploads the pics to ipfs and returns the hash
- does the IPFS upload
- pins file to Pinata

"""

import subprocess
import requests
import pandas as pd
import tqdm

def make_svg(ingredients, file_name):
    svg = [
    "<svg xmlns=\"http://www.w3.org/2000/svg\" preserveAspectRatio=\"xMinYMin meet\" viewBox=\"0 0 350 350\">",
    "<style>.base { fill: white; font-family: serif; font-size: 14px; }</style>",
    "<rect width=\"100%\" height=\"100%\" fill=\"black\" />"]

    for  i, ing  in enumerate(ingredients):
        svg.append(f"<text x=\"10\" y=\"{i*20+20}\" class=\"base\">{ing}</text>")
    svg.append("</svg>")

    with open(f"pics/{file_name}.svg", "w") as f:
        f.write("".join(svg))
    
def ipfs_upload(file_to_upload, pinata = False):
    raw = subprocess.check_output([
    "/usr/local/bin/ipfs", "add", file_to_upload])
    raw = raw.decode("utf-8").split()
    if raw[0] == "added":
        file_hash = raw[1]
    else:
        print(f"SOMETHING WENT WRONG WITH IPFS during {file_to_upload}")
    _ = subprocess.check_output([
    "/usr/local/bin/ipfs", "pin", "add", file_hash])
    if pinata:
        t = subprocess.check_output([
        "/usr/local/bin/ipfs", "pin", "remote", "add",
        "--service=pinata", f"--name={file_to_upload.rsplit('/')[-1]}", file_hash])
        print(t)
    return file_hash

def build_ingredient_dict(policy_id, token_type, token_id, ipfs_hash):
    dic = {
        "721": {
            policy_id: {
              f"cLoot{token_id}": {
                "description": f"Never forget to bring your tokens on an adventure!",
                "name": f"cLoot #{token_id}",
                "id": token_id,
                "image": f"ipfs://{ipfs_hash}",
                "type": token_type
                }
            }
        }
    }
    return dic

def pin(ipfs_hash, name):

    url = "https://api.pinata.cloud/pinning/addHashToPinQueue"

    headers = {'pinata_api_key': "<pinata_api_key>",
               'pinata_secret_api_key': "<pinata_secret_api_key>"}

    body= {"hashToPin": ipfs_hash, 
        "host_nodes": [
            "</ip4/XXX>",
            "</ip4/XXX>"],
           "pinataMetadata" : {"name" : name}
            
        }
    p = requests.post(url, headers = headers, data = body)
    print(p.content)
