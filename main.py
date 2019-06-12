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

    def call(self, api_call: dict):
        try:
            [(function, kwargs)] = api_call.items()
            data = getattr(api, function)(**kwargs)
        except Exception as e:
            self.conn.rollback()
            return self._error(str(e))
        else:
            self.conn.commit()
            return self._success(data)

    @staticmethod
    def _success(data: typing.Optional[list] = None) -> dict:
        if data is None:
            return {"status": "OK"}
        else:
            return {"status": "OK", "data": data}

    @staticmethod
    def _error(debug: str) -> dict:
        return {"status": "Error", "debug": debug}

    def open(self, database: str, login: str, password: str) -> dict:
        self.conn = psycopg2.connect(dbname=database,
                                     user=login,
                                     password=password)
        if not self.init_mode:
            return None
        self._prepare_database()
        return None

    def _prepare_database(self):
        with self.conn.cursor() as cursor:
            print("dropping existing tables...")
            with open("drop.pgsql", "r") as f:
                cursor.execute(f.read())
            print("no error. Preparing database...")
            with open("prepare_database.pgsql", "r") as f:
                cursor.execute(f.read())
            print("no error.")

    def leader(self, timestamp: int, password: str, member: int):
        if not self.init_mode:
            raise Exception(
                "unauthorized leader call. Application is running in non-init mode"
            )
        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.ADD_MEMBER,
                {
                    "member_id": member,
                    "password": password,
                    "timestamp": timestamp
                },
            )
            cursor.execute(queries.ADD_LEADER, {"member_id": member})
        return None

    def support(self,
                timestamp,
                member,
                password,
                action,
                project,
                authority=None):
        self._action(timestamp,
                     member,
                     password,
                     action,
                     project,
                     authority,
                     is_support=True)
        return None

    def protest(self,
                timestamp,
                member,
                password,
                action,
                project,
                authority=None):
        self._action(
            timestamp,
            member,
            password,
            action,
            project,
            authority,
            is_support=False,
        )
        return None

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
            raise Exception("Authority not provided")
        authority = result or authority
        if not result:
            self._add_authority(authority)
            self._add_project(project, authority)
        self._add_action(action, member, is_support, project)

        return None

    def _handle_member(self, member, password, timestamp):
        if self._is_member(member):
            print(f"{member} is a member!")
            if not self._is_member_active(member, timestamp):
                raise Exception(f"member {member} is frozen")

            if not self._validate(member, password):
                raise Exception(f"password authorization failed for {member}")
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

    def upvote(self, timestamp, member, password, action):
        self._vote(timestamp, member, password, action, 1)
        return None

    def downvote(self, timestamp, member, password, action):
        self._vote(timestamp, member, password, action, -1)
        return None

    def _vote(self, timestamp, member, password, action, value):
        self._handle_member(member, password, timestamp)
        with self.conn.cursor() as cursor:
            cursor.execute(queries.ADD_VOTE, {
                "member_id": member,
                "action_id": action,
                "value": value
            })

    def actions(self, timestamp, member, password,
                type=None, project=None, authority=None):
        if project and authority:
            raise Exception(
                "project and authority can't be passed to actions together")
        cond = " AND ".join(
            elem[0] for elem in 
                [("support = %(is_support)s", type),
                 ("project_id = %(project_id)s", project),
                 ("authority_id = %(authority_id)s", authority)] if elem[1])

        with self.conn.cursor() as cursor:
            cursor.execute(
                queries.SELECT_ACTIONS.format("WHERE" if cond else '', cond),
                {
                    "is_support": type == "support",
                    "project_id": project,
                    "aauthority_id": authority
                }
            )
            return cursor.fetchall()

    def close(self):
        self.conn.close()


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
            print(api_call)
            pprint(api.call(api_call))
            print()
    finally:
        api.close()
