import csv
import sys
import requests
import json
import psycopg2

# User fed parameters
file="pathology.json"
solr_url="<Enter Solr URL here>"
conn_string = "host='%s' dbname='%s' user='%s' password='%s' port=%s" % ('host',
                                                                             'dbname',
                                                                             'user',
                                                                             'password',
                                                                             'port')

# Constructing solr_url
url = solr_url + '/update?commit=true'
headers = {
'Content-type': 'application/json',
}

# Connecting to the database
conn = psycopg2.connect(conn_string)
cursor = conn.cursor()

# Extracting person_source_value -> person_id mapping information from the database
cursor.execute("""SELECT person_id, person_source_value from mimic_v5.person;""")
result = cursor.fetchall()
map = dict()
for i in result:
    pid = i[0]
    psv = str(i[1])
    if psv not in map:
        map[psv] = pid

# Pushing data to Solr

content = ""
with open(file, 'r') as f:
    for line in f.readlines():
        content += line

json_list = json.loads(content)
# Uploading file in chunks to server
s = []
for j in json_list:
    # Getting the person_source_value to person_id mapping
    if str(j['subject']) not in map:
        continue

    subject_id = map[str(j['subject'])]

    # Modifying input data with subject_id
    j['subject'] = subject_id

    # Appending to upload list
    s.append(j)

data = json.dumps(s)
response = requests.post(url, headers=headers, data=data)
if response.status_code != 200:
    print("Couldn't upload")
    print(response.reason)
else:
    print ("\n\nUploaded Gleason Pathology Reports\n\n")
