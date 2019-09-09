import json
import sys

import psycopg2.extras
import pyodbc
import requests
from requests.auth import HTTPBasicAuth

if __name__ == "__main__":
    solr_url = "http://localhost:8983/solr/sample"
    auth = None
    db_host = 'localhost'
    db_port = '5432'
    db_name = 'omop'
    db_user = 'pg'
    db_password = 'pg'
    db_dialect = 'postgresql'
    conn = None
    cursor = None
    try:
        if len(sys.argv) < 2:
            print()
            print('Please run with the following command line args:')
            print('\tpython3 omop_ingest.py <solr_url> <solr_user> <solr_password> <db_host> <db_name> '
                  '<db_user> <db_password> <db_dialect> <db_port>')
            print()
            print('e.g.:')
            print('\tpython3 omop_ingest.py https://solr.internal.claritynlp.cloud/solr/sample admin test mydb.org '
                  ' mimic admin password postgresql 5432')
            print()

            sys.exit(0)

        if len(sys.argv) > 3:
            solr_user = sys.argv[2]
            solr_password = sys.argv[3]
            if len(solr_user) == 0 and len(solr_password) == 0:
                auth = None
            else:
                auth = HTTPBasicAuth(solr_user, solr_password)

        if len(sys.argv) > 9:
            db_host = sys.argv[4]
            db_name = sys.argv[5]
            db_user = sys.argv[6]
            db_password = sys.argv[7]
            db_dialect = sys.argv[8]
            db_port = sys.argv[9]
        else:
            db_host = 'localhost'
            db_port = '5432'
            db_name = 'omop'
            db_user = 'pg'
            db_password = 'pg'
            db_dialect = 'postgresql'

        if len(sys.argv) > 2:
            solr_url = sys.argv[1]

        if db_dialect == 'sql_server':
            conn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                  "Server=%s;"
                                  "Database=%s;"
                                  "uid=%s;pwd=%s" % (db_host, db_name, db_user, db_password))

            cursor = conn.cursor()
        elif db_dialect.startswith('postgres') or db_dialect == 'pg':
            conn_string = "host='%s' dbname='%s' user='%s' password='%s' port=%s" % (db_host,
                                                                                     db_name,
                                                                                     db_user,
                                                                                     db_password,
                                                                                     db_port)

            # Connecting to the OMOP DB
            conn = psycopg2.connect(conn_string)
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else:
            dialects = ['sql_server', 'postgresql']
            dialect_str = ', '.join(dialects)
            print('please select a valid dialect, Options are:', dialect_str)

        if cursor:
            # SOLR upload headers
            # url = solr_url + '/update/json'
            url = solr_url + '/update?commit=true'
            headers = {
                'Content-type': 'application/json',
            }

            # Extracting information - detailed_descriptions
            cursor.execute(
                """
                select c.concept_name as report_type, n.* from note n
                LEFT OUTER JOIN concept c
                on n.note_type_concept_id = c.concept_id
                """)
            result = cursor.fetchall()

            result_list = []
            for i in result:
                d = {"subject": i['person_id'],
                     "source": "OMOP Database",
                     "report_type": i['report_type'],
                     "report_text": i['note_text'],
                     "report_id": i['note_id'],
                     "id": i['note_id'],
                     "report_date": str(i['note_date'])
                     }

                result_list.append(d)

            # Pushing data to Solr
            data = json.dumps(result_list)
            response = requests.post(url, headers=headers, data=data)

            # Verifying upload
            if response.status_code == 200:
                print("Uploaded OMOP notes")
            else:
                print("Couldn't upload OMOP notes. Reason: " + str(response.reason))
    except Exception as ex1:
        print(ex1)
    finally:
        if conn:
            conn.close()
