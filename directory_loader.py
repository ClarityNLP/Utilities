import sys
from requests.auth import HTTPBasicAuth
from tika import parser
import os
import json
import requests
import uuid
from string import printable


def get_file_content(_file_name):
    content = parser.from_file(_file_name)
    if 'content' in content:
        text = content['content']
    else:
        print('No content from file {}'.format(_file_name))
        return '', '', ''
    metadata = content['metadata']
    safe_text = str(text)
    safe_text = safe_text.encode('utf-8', errors='ignore')
    safe_text = safe_text.decode("utf-8")
    safe_text = ''.join(char for char in safe_text if char in printable)
    print('Content found from file {}, length={}'.format(_file_name, len(safe_text)))
    try:
        creation_date = metadata['Creation-Date']
        if not type(creation_date) == str:
            creation_date = creation_date[0]
    except Exception as ex:
        creation_date = "2019-01-01T00:00:00Z"
    try:
        report_type = metadata['Content-Type']
        if not type(report_type) == str:
            report_type = report_type[0]
    except Exception as ex:
        report_type = "Content-Type"

    return safe_text, creation_date, report_type


if __name__ == "__main__":

    batch = 10
    solr_url = "http://localhost:8983/solr/sample"
    auth = None
    dir_name = '.'
    source = "Uploads"
    headers = {
        'Content-type': 'application/json',
    }
    try:
        if len(sys.argv) < 2:
            print()
            print('Please run with the following command line args:')
            print('\tpython3 directory_loader.py <solr_url> <solr_user> <solr_password> <dir_path>')
            print()
            print('e.g.:')
            print('\tpython3 directory_loader.py https://solr.internal.claritynlp.cloud/solr/sample admin test "/Home/MyFiles"')
            print()

            sys.exit(0)

        if len(sys.argv) > 4:
            dir_name = sys.argv[4]

        if len(sys.argv) > 3:
            solr_user = sys.argv[2]
            solr_password = sys.argv[3]
            auth = HTTPBasicAuth(solr_user, solr_password)

        if len(sys.argv) > 2:
            solr_url = sys.argv[1]
    except Exception as ex1:
        print(ex1)

    directory = os.fsencode(dir_name)

    upload_list = list()
    solr_url = solr_url + '/update?commit=true'

    for file in os.listdir(directory):
        file_name = os.fsdecode(file)
        subject = file_name
        file_name = dir_name + os.path.sep + file_name
        if file_name.endswith('py'):
            continue
        else:
            txt, date, report_type = get_file_content(file_name)
            if len(txt) > 0:
                rpt_id = str(uuid.uuid1())
                d = {
                        "subject": subject,
                        "source": source,
                        "report_type": report_type,
                        "report_text": txt,
                        "report_id": rpt_id,
                        "id": rpt_id,
                        "report_date": date
                     }
                upload_list.append(d)

            if len(upload_list) > 0 and len(upload_list) % batch == 0:
                data = json.dumps(upload_list)
                response2 = requests.post(solr_url, headers=headers, data=data, auth=auth)

                if response2.status_code == 200:
                    print("Uploaded batch")
                else:
                    print('upload to solr failed')
                    print(response2.reason)
                    print(response2.content)
                upload_list = list()

    if len(upload_list) > 0 and len(upload_list) % batch == 0:
        data = json.dumps(upload_list)
        response2 = requests.post(solr_url, headers=headers, data=data, auth=auth)

        if response2.status_code == 200:
            print("Uploaded batch")
        else:
            print('upload to solr failed')
        upload_list = list()
