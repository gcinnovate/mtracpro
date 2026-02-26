import requests
import psycopg2
from psycopg2.extras import DictCursor
from webapp.settings import config

def sync_facilities(
        dhis2_url,
        dhis2_auth,
        pg_conn_params,
        start_level = 3,
        end_level = 5
):
    """
    Synchronize organisation units from DHIS2 into a PostgreSQL DB using psycopg2.

    Args:
        dhis2_url: DHIS2 base URL (e.g., 'https://my-dhis2-instance')
        dhis2_auth: (username, password) tuple for DHIS2
        pg_conn_params: dict with psycopg2 connection params, e.g.
                        {'dbname': '...', 'user': '...', 'password': '...', 'host': '...'}
        start_level: DHIS2 org unit starting level
        end_level: DHIS2 org unit ending level (inclusive)
    """
    conn = psycopg2.connect(**pg_conn_params)
    conn.autocommit = False
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        added_orgunits = 0
        for level in range(start_level, end_level + 1):
            # Fetch org units at this level
            print("Fetching org units at level {0}".format(level))
            resp = requests.get(
                "{0}/api/organisationUnits".format(dhis2_url),
                params={
                    "level": level,
                    "fields": "id,name,code,parent[id]",
                    "paging": "false"
                },
                auth=dhis2_auth,
                timeout=30)
            resp.raise_for_status()
            orgunits = resp.json().get("organisationUnits", [])
            for ou in orgunits:
                orgunit_id = ou["id"]
                parent_id = ou.get("parent", {}).get("id")
                # Check if exists
                cur.execute("SELECT 1 FROM locations WHERE dhis2id=%s", (orgunit_id,))
                exists = cur.fetchone()
                if not exists:
                    # search for parent by id in DB
                    cur.execute("SELECT id FROM locations WHERE dhis2id=%s", (parent_id,))
                    parent_dhis2id = cur.fetchone()
                    if parent_dhis2id:
                        # insert not using add_node postgresql function
                        # log what we're adding, show ou name and id, parent name and id
                        print(u"Adding {0} ({1}) to {2} ({3})".format(
                            ou['name'], orgunit_id, parent_dhis2id["id"], parent_id).encode('utf-8'))

                        cur.execute(
                            """
                            SELECT add_node(%s, %s, %s) AS id
                            """, (1, ou["name"], parent_dhis2id[0])
                        )
                        new_orgunit_id = cur.fetchone()
                        if new_orgunit_id:
                            added_orgunits += 1
                            cur.execute(
                                "UPDATE locations SET dhis2id=%s WHERE id=%s",
                                (ou["id"], new_orgunit_id["id"]))
            conn.commit()  # Commit after each level
            # update paths for the entire tree
        if added_orgunits > 0:
            print("Updating paths for all org units")
            cur.execute("SELECT refresh_hierarchy();")
            conn.commit()
            # log the count of those to potentially add
            print("Added {0} new org units".format(added_orgunits))
        cur.close()
    finally:
        conn.close()


# Example usage:
conn_params = {
    'dbname': config["db_name"],
    'user': config["db_user"],
    'password': config["db_passwd"],
    'host': config["db_host"],
    'port': config["db_port"]
}
dhis2_url = config["base_url"]
dhis2_creds = (config["dhis2_user"], config["dhis2_passwd"])

print(conn_params)
sync_facilities(dhis2_url, dhis2_creds, conn_params)
