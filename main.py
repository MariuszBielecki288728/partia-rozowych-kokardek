import argparse
import json
import sys

from api import API

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--init",
                        help="run app in init mode",
                        action="store_true")

    args = parser.parse_args()
    api = API(bool(args.init))
    try:
        for line in sys.stdin:
            api_call = json.loads(line)
            print(json.dumps(api.call(api_call)))
    finally:
        api.close()
