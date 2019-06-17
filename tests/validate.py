"""
Simple validator that compares (line-wise) files containing json encoded lines
"""
import argparse
import json
from termcolor import colored

parser = argparse.ArgumentParser()
parser.add_argument("test", help="data given to SUT")
parser.add_argument("actual", help="actual SUT output file")
parser.add_argument("expected", help="expected SUT output file")
args = parser.parse_args()
print(args.actual, args.expected)

print("NOTE: debug field is ignored\n")
with open(args.test, "r") as test,\
     open(args.actual, 'r') as actual,\
     open(args.expected, 'r') as expected:

    for test_line, actual_line, expected_line in zip(test, actual, expected):
        act = json.loads(actual_line)
        exp = json.loads(expected_line)
        debug = act.pop('debug', None)

        if not act == exp:
            print(colored(f"FAIL for {test_line.strip()}:\n  expected:\n"
                          f"    {exp}\n  got:\n    {act}\n  DEBUG: {debug}",
                          "red"))
        else:
            print(colored(f"OK for {test_line.strip()}", "green"))

