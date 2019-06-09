BEGIN;

CREATE TABLE member (
  member_id int PRIMARY KEY,
  password bytea NOT NULL,
  upvoted_count int DEFAULT 0,
  downvoted_count int DEFAULT 0,
  last_act_time timestamp NOT NULL
);

CREATE TABLE leader (
  member_id int PRIMARY KEY,
  CONSTRAINT leader_id_member_id_fkey FOREIGN KEY (member_id)
    REFERENCES member (member_id)
);

CREATE TABLE authority (
  authority_id int PRIMARY KEY
);


CREATE TABLE project (
  project_id int PRIMARY KEY,
  authority_id int NOT NULL,
  CONSTRAINT authority_id_fkey FOREIGN KEY (authority_id)
    REFERENCES authority (authority_id)
);

CREATE TABLE action (
  action_id int PRIMARY KEY,
  owner_id int NOT NULL,
  support boolean NOT NULL,
  project_id int NOT NULL,
  CONSTRAINT owner_id_member_id_fkey FOREIGN KEY (owner_id)
      REFERENCES member (member_id),
  CONSTRAINT project_id_fkey FOREIGN KEY (project_id)
      REFERENCES project (project_id)
);

CREATE TABLE member_votes_for (
  member_id int,
  action_id int,
  value int CHECK (value = -1 OR value = 1),
  CONSTRAINT member_id_fk FOREIGN KEY (member_id)
      REFERENCES member (member_id),
  CONSTRAINT action_id_fkey FOREIGN KEY (action_id)
      REFERENCES action (action_id)
);

CREATE TABLE all_id (
  id int PRIMARY KEY
);

INSERT INTO all_id VALUES (123);
SELECT * FROM all_id


ROLLBACK;