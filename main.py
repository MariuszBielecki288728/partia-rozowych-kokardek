import argparse
import json
import sys
import psycopg2
import typing
from pprint import pprint
import logging
import queries

parser = argparse.ArgumentParser()
parser.add_argument("--init", help="run app in init mode", action="store_true")
args = parser.parse_args()

class API:

    def __init__(self, init_mode: bool):
        self.init_mode = init_mode

    @staticmethod
    def _success() -> dict:
        return {"status": "OK"}

    @staticmethod
    def _error(debug: str) -> dict:
        return {
            "status": "Error",
            "debug": debug
        }

    def open(self, database: str, login: str, password: str) -> dict:
        try:
            self.conn = psycopg2.connect(
                dbname=database, user=login, password=password)
        except psycopg2.Error as e:
            return self._error(str(e))
        if not self.init_mode:
            print("program in non-init mode, open won't prepare db")
            return self._success()

        cur = self.conn.cursor()
            
        try:
            with open("drop.pgsql", "r") as f:
                cur.execute(f.read())
            with open("prepare_database.pgsql", "r") as f:
                cur.execute(f.read())
        finally:
            cur.close()
        self.conn.commit()
        return self._success()

    def leader(self, timestamp: int, password: str, member: int):
        if not self.init_mode:
            return self._error("application is running in non-init mode")
        cur = self.conn.cursor()
        try:
            cur.execute(queries.ADD_MEMBER,
                        {
                            "member_id": member,
                            "password": password,
                            "timestamp": timestamp
                        })
            cur.execute(queries.ADD_LEADER,
                        {
                            "member_id": member
                        })
        except psycopg2.Error as e:
            self.conn.rollback()
            print("error occured in leader", e)
            return self._error(e.pgerror)
        else:
            self.conn.commit()
            return self._success()
        finally:
            cur.close()


if __name__ == "__main__":
    api = API(bool(args.init))
    for line in sys.stdin:
        api_call = json.loads(line)
        [(function, kwargs)] = api_call.items()
        pprint(getattr(api, function)(**kwargs))
