import csv
import json
import gzip

import requests
from requests.auth import HTTPBasicAuth

if __name__ == "__main__":

    # User fed parameters - example here with localhost
    # Assumes mimic-iii noteevent data structure
    file = "./NOTEEVENTS.csv.gz"
    solr_url = "http://localhost/solr/sample"
    auth = HTTPBasicAuth('admin', '')
    # If you have a subset of rows you want to enter, put those here
    # If all rows, set start_at to 0 and end_at to -1
    start_at = 0
    end_at = -1


    # Constructing solr_url
    url = solr_url + '/update?commit=true'
    headers = {
        'Content-type': 'application/json',
    }

    # to keep track of the number of rows which have been passed
    count = 0

    # Keeping track of chunk statistics
    chunk = 0
    chunk_size = 10
    num_chunk_failed = 0

    # Pushing data to Solr
    try:
        total = 0
        data = ''
        # read in large csv file
        csvfile = gzip.open(file, 'rt')
        reader = csv.DictReader(csvfile)
        # Uploading file in chunks to server
        s = []
        failed = []
        for row in reader:
            total += 1
            if total % 10 == 0:
                print('read up to row {}'.format(total))
            if total < start_at:
                continue
            if (end_at > 0) and (total > end_at):
                break

            d = {'subject': row['SUBJECT_ID'],
                 'description_attr': row['DESCRIPTION'],
                 'source': 'MIMICiii',
                 'report_type': row['CATEGORY'],
                 'report_text': row['TEXT'],
                 'cg_id': row['CGID'],
                 'report_id': row['ROW_ID'],
                 'is_error_attr': row['ISERROR'],
                 'id': row['ROW_ID'],
                 'store_time_attr': row['STORETIME'],
                 'chart_time_attr': row['CHARTTIME'],
                 'admission_id': row['HADM_ID'],
                 'report_date': row['CHARTDATE']
                 }
            s.append(d)

            # Chunking
            count += 1
            if count == chunk_size:
                rowstart = (chunk_size*chunk)+1
                rowend = (chunk_size*chunk)+chunk_size
                print("Uploading chunk (rows " + str(rowstart) + " to "+ str(rowend) + ")")
                data = json.dumps(s)
                response = requests.post(url, headers=headers, data=data, auth=auth)
                chunk += 1
                print("Chunk " + str(chunk) + " HTTP Resp:" + str(response.status_code) + "\n\n")
                if response.status_code != 200:
                    num_chunk_failed += 1
                    failed.append((rowstart,rowend))
                s.clear()
                count = 0

        # Upload any remnant rows
        if len(s) > 0:
            response = requests.post(url, headers=headers, data=data, auth=auth)
            chunk += 1
            print("Chunk " + str(chunk) + " HTTP Resp:" + str(response.status_code) + "\n\n")
            if response.status_code != 200:
                num_chunk_failed += 1

        # Close file connection
        csvfile.close()

        # Printing statistics
        print("\n\nFINAL STATISTICS\n")
        print("\nChunk size = " + str(chunk_size))
        print("\nNumber of chunks = " + str(chunk))
        print("\nNumber of failed chunk uploads = " + str(num_chunk_failed))
        if num_chunk_failed > 0:
            print("Range of rows in failed chunks",failed)
        print("\n\n")

    except Exception as ex:
        print("\n")
        print(ex)
        print("\n")
