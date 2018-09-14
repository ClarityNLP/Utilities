import json
import psycopg2
import psycopg2.extras
import requests

solr_url = "";
conn_string = "host='%s' dbname='%s' user='%s' password='%s' port=%s" % ('aact-db.ctti-clinicaltrials.org',
                                                                         'aact',
                                                                         'aact',
                                                                         'aact',
                                                                         '5432')

# Connecting to the AACT DB
conn = psycopg2.connect(conn_string)
cursor = conn.cursor()

# SOLR upload headers
# url = solr_url + '/update/json'
url = solr_url + '/update?commit=true'
headers = {
    'Content-type': 'application/json',
}

# Extracting information - detailed_descriptions
cursor.execute(
    """SELECT * FROM detailed_descriptions INNER JOIN studies ON studies.nct_id = detailed_descriptions.nct_id WHERE studies.first_received_date > '2018-01-01' LIMIT 1000""")
result = cursor.fetchall()

result_list = []
for i in result:
    d = {"subject": i[1],
         "description_attr": "AACT Clinical Trials",
         "source": "AACT",
         "report_type": "Clinical Trial Description",
         "report_text": i[2],
         "cg_id": "",
         "report_id": i[0],
         "is_error_attr": "",
         "id": i[0],
         "store_time_attr": "",
         "chart_time_attr": "",
         "admission_id": "",
         "report_date": str(i[5])
         }

    result_list.append(d)

# Pushing data to Solr
data = json.dumps(result_list)
response = requests.post(url, headers=headers, data=data)

# Verifying upload
if response.status_code == 200:
    print("Uploaded AACT detailed_descriptions")
else:
    print("Couldn't upload AACT detailed_descriptions. Reason: " + str(response.reason))

# Extracting information - Interventions
cursor.execute(
    """SELECT * FROM interventions INNER JOIN studies ON studies.nct_id = interventions.nct_id WHERE studies.first_received_date > '2018-01-01' AND interventions.description IS NOT NULL LIMIT 1000 """)
result = cursor.fetchall()

result_list = []
for i in result:
    d = {"subject": i[1],
         "description_attr": "AACT Clinical Trials",
         "source": "AACT",
         "report_type": "Clinical Trial Interventions",
         "report_text": str(i[4]),
         "cg_id": "",
         "report_id": i[0],
         "is_error_attr": "",
         "id": i[0],
         "store_time_attr": "",
         "chart_time_attr": "",
         "admission_id": "",
         "report_date": str(i[7])
         }

    result_list.append(d)

# Pushing data to Solr
data = json.dumps(result_list)
response2 = requests.post(url, headers=headers, data=data)

# Verifying upload
if response2.status_code == 200:
    print("Uploaded AACT interventions")
else:
    print("Couldn't upload AACT interventions. Reason: " + str(response2.reason))

# Extracting information - Eligibilities
cursor.execute(
    """SELECT eligibilities.id, eligibilities.nct_id, eligibilities.criteria, studies.first_received_date FROM eligibilities INNER JOIN studies ON studies.nct_id = eligibilities.nct_id WHERE studies.first_received_date > '2018-01-01' LIMIT 1000 """)
result = cursor.fetchall()

result_list = []
for i in result:
    # Encoding as ASCII - Criteria field contains non ASCII characters
    report_text = i[2].encode('ascii', 'ignore')

    d = {"subject": i[1],
         "description_attr": "AACT Clinical Trials",
         "source": "AACT",
         "report_type": "Clinical Trial Criteria",
         "report_text": str(report_text),
         "cg_id": "",
         "report_id": i[0],
         "is_error_attr": "",
         "id": i[0],
         "store_time_attr": "",
         "chart_time_attr": "",
         "admission_id": "",
         "report_date": str(i[3])
         }

    result_list.append(d)

# Pushing data to Solr
data = json.dumps(result_list)
response3 = requests.post(url, headers=headers, data=data)

# Verifying upload
if response3.status_code == 200:
    print("Uploaded AACT eligibilities")
else:
    print("Couldn't upload AACT eligibilities. Reason: " + str(response3.reason))


conn.close()
