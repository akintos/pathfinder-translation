import argparse
import csv
import io
import json
import os
import sys

import urllib.request
from collections import namedtuple

import polib


EXCLUDE_CSV_PATH = "https://docs.google.com/spreadsheet/ccc?key=1DtLj9LBDBVUaljksJ6Rhidb1DiqON8aaM3cca08U-jM&output=csv"


class TranslationEntry:
    def __init__(self, key: str, source: str, target: str, fuzzy: bool, prefix: str):
        self.key = key
        self.source = source
        self.target = target
        self.fuzzy = fuzzy
        self.prefix = prefix
    
    @property
    def translated(self):
        return self.target != ""


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("-n", action='store_true',
        help="Append string number prefix to strings")

    parser.add_argument("-l", "--lang", required=True, metavar="LANGCODE",
        help="Translation language code")
    
    parser.add_argument("-i", "--input", required=True, metavar="INPUT_DIR",
        help="Input locale JSON file directory")

    parser.add_argument("-o", "--output", required=True, metavar="OUTPUT_DIR",
        help="Output locale JSON file directory")

    return parser.parse_args()


def load_exclude_keyset():
    exclude_keyset = set()

    response = urllib.request.urlopen(EXCLUDE_CSV_PATH)
    with io.TextIOWrapper(response, encoding="utf-8") as s:
        r = csv.reader(s)
        next(r)  # header
        for row in r:
            if row[0]:
                exclude_keyset.add(row[0])
    
    return exclude_keyset


def main():
    args = parse_arguments()

    n = args.n
    lang = args.lang
    in_path = args.input
    out_path = args.output

    if not os.path.isdir(lang):
        print(f"{lang} language translation directory does not exist.")
        sys.exit(1)
    
    if not os.path.isdir(in_path):
        print(f"Input locale directory {in_path} not found.")
        sys.exit(1)

    # load translations
    translation = {}

    for filename in os.listdir(lang):
        filepath = os.path.join(lang, filename)
        po = polib.pofile(filepath)
        p = filename[0].upper()
        for i in range(len(po)):
            entry: polib.POEntry = po[i]
            translation[entry.msgctxt] = TranslationEntry(entry.msgctxt, entry.msgid, entry.msgstr, entry.fuzzy, p+str(i+1))
    
    # print(f"Loaded {len(translation)} strings")

    exclude_keyset = set()
    # load string number exceptions
    if n:
        exclude_keyset = load_exclude_keyset()

    total = 0
    translated = 0
    missing = 0

    import collections
    missing_dict = collections.OrderedDict()
    
    for filename in os.listdir(in_path):
        if not filename.endswith(".json"):
            continue

        with open(os.path.join(in_path, filename), "r", encoding="utf-8") as f:
            j = json.load(f)

        for entry in j["strings"]:
            key = entry["Key"]
            if not key or not entry["Value"]:
                continue
            
            total += 1

            tr = translation.get(key, None)
            if not tr:
                missing += 1
                missing_dict[key] = entry["Value"]
                # print("Translation not found for " + entry["Value"])
                continue
            
            if tr.translated:
                value = tr.target
                translated += 1
            else:
                value = tr.source
            
            if n and key not in exclude_keyset and tr.source != tr.target:
                value = f"{value} ({tr.prefix})"

            entry["Value"] = value
        
        with open(os.path.join(out_path, "zhCN" + filename[4:]), "w", encoding="utf-8") as f:
            json.dump(j, f, ensure_ascii=False, indent=2)
    
    print(f"Translated {translated} of {total} strings ({translated * 100 / total:5.2f}%)")
    
    # print(f"{missing} missing translation.")
    # with open('missing.json', "w", encoding="utf-8") as f:
    #     json.dump(missing_dict, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
