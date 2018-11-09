import pandas as pd
import os
from glob import iglob
import requests
import json
from datetime import datetime

solr_url = "http://localhost:8983/solr/sample"

url = solr_url + '/update?commit=true'
headers = {
    'Content-type': 'application/json',
}


def load_vaers(path=''):
    rootdir = path + '/**/*'
    file_list = [f for f in iglob(rootdir, recursive=True) if os.path.isfile(f)]
    print(file_list)
    for f in file_list:
        if f.endswith('DATA.csv'):
            try:
                data_file = f
                symptom_file = f.replace('DATA', 'SYMPTOMS')
                vax_file = f.replace('DATA', 'VAX')

                print('loading data from ' + f)
                data = pd.read_csv(data_file,  encoding ="latin-1", low_memory=False)
                print('loading vax from ' + f)
                vax = pd.read_csv(vax_file, encoding ="latin-1", low_memory=False)
                # print('loading symptom from ' + f)
                # symptom = pd.read_csv(symptom_file)
                df = pd.merge(data, vax, how='inner', on='VAERS_ID')
                obj = dict()
                cols = [l for l in list(df.columns)]
                # ['vaers_id', 'recvdate', 'state', 'age_yrs', 'cage_yr', 'cage_mo', 'sex', 'rpt_date', 'symptom_text',
                # 'died', 'datedied', 'l_threat', 'er_visit', 'hospital', 'hospdays', 'x_stay', 'disable', 'recovd',
                # 'vax_date', 'onset_date', 'numdays', 'lab_data', 'v_adminby', 'v_fundby', 'other_meds', 'cur_ill',
                # 'history', 'prior_vax', 'splttype', 'form_vers', 'todays_date', 'birth_defect', 'ofc_visit',
                # 'er_ed_visit', 'allergies', 'vax_type', 'vax_manu', 'vax_lot', 'vax_dose_series', 'vax_route',
                # 'vax_site', 'vax_name']
                print(cols)
                # print(df.head())
                results = list()
                reserved_cols = ['VAERS_ID', 'RECVDATE', 'SYMPTOM_TEXT']
                for index, row in df.iterrows():
                    # print(row)
                    obj = dict()
                    datetime_object = datetime.strptime(row['RECVDATE'], '%m/%d/%Y')
                    obj['id'] = row['VAERS_ID']
                    obj['report_id'] = row['VAERS_ID']
                    obj['report_date'] = str(datetime_object.isoformat())
                    obj['report_type'] = "VAERS Report"
                    obj['report_text'] = row['SYMPTOM_TEXT']
                    obj['source'] = 'CDC/FDA'
                    obj['subject'] = row['VAERS_ID']

                    for col in cols:
                        if col not in reserved_cols:
                            if str(row[col]) != 'nan':
                                new_col = col.lower() + '_attr'
                                obj[new_col] = row[col]
                    results.append(obj)
                json_data = json.dumps(results)
                response = requests.post(url, headers=headers, data=json_data)

                if response.status_code != 200:
                    print(response.reason)
                print(response)
            except Exception as e:
                print(e)


if __name__ == "__main__":
    load_vaers('/Downloads/vaers')
