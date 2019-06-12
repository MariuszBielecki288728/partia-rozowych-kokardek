import argparse
import json
import sys
import psycopg2
import typing
from pprint import pprint

import queries


class API:
    def __init__(self, init_mode: bool):
        self.init_mode = init_mode

    @staticmethod
    def _success() -> dict:
        return {"status": "OK"}

    @staticmethod
    def _error(debug: str) -> dict:
        return {"status": "Error", "debug": debug}

    def open(self, database: str, login: str, password: str) -> dict:
        try:
            self.conn = psycopg2.connect(dbname=database,
                                         user=login,
                                         password=password)
        except psycopg2.Error as e:
            return self._error(str(e))
        if not self.init_mode:
            return self._success()
        print("Begin preparation of database")
        try:
            self._prepare_database()
        except psycopg2.Error as e:
            print("Error occured during database preparation", e)
            return self._error(str(e))
        return self._success()

    def _prepare_database(self):
        cur = self.conn.cursor()
        try:
            print("dropping existing tables...")
            with open("drop.pgsql", "r") as f:
                cur.execute(f.read())
            print("no error. Preparing database...")
            with open("prepare_database.pgsql", "r") as f:
                cur.execute(f.read())
            print("no error.")
        finally:
            cur.close()
        self.conn.commit()

    def leader(self, timestamp: int, password: str, member: int):
        if not self.init_mode:
            return self._error(
                "unauthorized leader call. Application is running in non-init mode"
            )
        cur = self.conn.cursor()
        try:
            cur.execute(
                queries.ADD_MEMBER,
                {
                    "member_id": member,
                    "password": password,
                    "timestamp": timestamp
                },
            )
            cur.execute(queries.ADD_LEADER, {"member_id": member})
        except psycopg2.Error as e:
            print("error occured in leader", e)
            return self._error(str(e))
        else:
            self.conn.commit()
            return self._success()
        finally:
            cur.close()

    def support(self,
                timestamp,
                member,
                password,
                action,
                project,
                authority=None):
        try:
            return self._action(timestamp,
                                member,
                                password,
                                action,
                                project,
                                authority,
                                is_support=True)
        except psycopg2.Error as e:
            self.conn.rollback()
            return self._error(str(e))

    def protest(self,
                timestamp,
                member,
                password,
                action,
                project,
                authority=None):
        try:
            return self._action(
                timestamp,
                member,
                password,
                action,
                project,
                authority,
                is_support=False,
            )
        except psycopg2.Error as e:
            self.conn.rollback()
            return self._error(str(e))

    def _action(
            self,
            timestamp: int,
            member: int,
            password: str,
            action: int,
            project: int,
            authority: typing.Optional[int],
            is_support: bool,
    ):

        self._handle_member(member, password, timestamp)

        result = self._search_for_project(project)
        if not result and not authority:
            self.conn.rollback()
            return self._error("authority not provided")
        authority = result or authority
        if not result:
            self._add_authority(authority)
            self._add_project(project, authority)
        self._add_action(action, member, is_support, project)

        self.conn.commit()
        return self._success()

    def _handle_member(self, member, password, timestamp):
        if self._is_member(member):
            print(f"{member} is a member!")
            if not self._is_member_active(member, timestamp):
                raise Exception(f"member {member} is frozen")

            if not self._validate(member, password):
                return self._error(
                    f"password authorization failed for {member}")
            self._update_member_last_act(member, timestamp)
        else:
            print(f"id {member} is not a member")
            self._add_member(timestamp, member, password)

    def _is_member(self, member):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.FIND_MEMBER, {"member_id": member})
            return bool(cursor.fetchall())

    def _is_member_active(self, member, timestamp):
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.VALIDATE_ACTIVE_STATUS,
                {
                    "member_id": member,
                    "current_timestamp": timestamp
                },
            )
            return cursor.fetchone()[0]

    def _update_member_last_act(self, member, timestamp):
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.UPDATE_MEMBER_LAST_ACT,
                {
                    "member_id": member,
                    "timestamp": timestamp
                },
            )

    def _validate(self, member, password):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.VALIDATE_PASSWORD, {
                "password": password,
                "member_id": member
            })
            (result) = cursor.fetchone()
        return result

    def _add_member(self, timestamp, member, password):
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.ADD_MEMBER,
                {
                    "member_id": member,
                    "password": password,
                    "timestamp": timestamp
                },
            )

    def _search_for_project(self, project: int) -> typing.Optional[int]:
        with self.conn.cursor() as cursor:
            cursor.execute(queries.FIND_PROJECT, {"project_id": project})
            result = cursor.fetchmany()
            if result:
                return result[0][0]
            else:
                return None

    def _add_action(self, action: int, member: int, is_support: bool,
                    project: int):
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.ADD_ACTION,
                {
                    "action_id": action,
                    "owner_id": member,
                    "is_support": is_support,
                    "project_id": project,
                },
            )

    def _add_authority(self, authority: int):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.ADD_AUTHORITY, {"authority_id": authority})

    def _add_project(self, project, authority):
        with self.conn.cursor() as cursor:
            cursor.execute(queries.ADD_PROJECT, {
                "project_id": project,
                "authority_id": authority
            })


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
            [(function, kwargs)] = api_call.items()
            pprint(getattr(api, function)(**kwargs))
    finally:
        api.conn.close()
