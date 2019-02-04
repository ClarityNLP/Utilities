import json
from datetime import datetime

import pandas as pd
import requests

path = '/Users/charityhilton/Documents/'
lit_file = 'death_lit.csv'
stat_file = 'death_stat.csv'
additional_columns = [
    "Education",
    "Occupation",
    "Industry",
    "Race White",
    "Race Black",
    "Race Amer Indian Alaskan",
    "Race Asian Indian",
    "Race Chinese",
    "Race Filipino",
    "Race Japanese",
    "Race Korean",
    "Race Vietnamese",
    "Race Other Asian",
    "Race Hawaiian",
    "Race Guamanian or Chamorro",
    "Race Samoan",
    "Race Other Pacific Islander",
    "Race Other",
    "Race Tribe First",
    "Race Tribe Second",
    "Race Other Asian First",
    "Race Other Asian Second",
    "Race Other PI First",
    "Race Other PI Second",
    "Race Other First",
    "Race Other Second",
    "Bridge Race",
    "Race Summary Code",
    "Race Calculation",
    "Hispanic No",
    "Hispanic Mexican",
    "Hispanic Puerto Rican",
    "Hispanic Cuban",
    "Hispanic Other",
    "Hispanic NCHS Bridge",
    "Autopsy",
    "Autopsy Available",
    "Pregnancy",
    "Tobacco",
    "Manner",
    "Disposition",
    "Injury at Work",
    "Injury Transportation",
    "Drug All",
    "Opioid",
    "Heroin",
    "Natural Semisynthetic Opioid",
    "Methadone",
    "Synthetic Opioid",
    "Cocaine",
    "Prescription Opioid",
    "Psychostimulant",
    "Suicide All",
    "Suicide Firearm",
    "Suicide Asphyxia",
    "Suicide Poisoning",
    "Suicide Other",
    "Firearm All",
    "Firearm Unintentional",
    "Firearm Homicide",
    "Firearm Undetermined",
    "Firearm Suicide",
    "Firearm Legal",
    "Malignant Neoplasm",
    "Heart Disease",
    "Alzheimers",
    "Unintentional Injury",
    "Chronic Lower Respiratory",
    "Cerebrovascular Disease",
    "Diabetes",
    "Chronic Liver Disease",
    "Influenza Pneumonia",
    "Parkinsons",
    "Essential Hypertension",
    "Pneumonitis"]


def make_text(row):
    txt = ''
    keys = ['A', 'B', 'C', 'D']

    for k in keys:
        cause = 'Cause of Death Line {}'.format(k)
        interval = 'Interval Line {}'.format(k)
        if not pd.isna(row[cause]) and len(str(row[cause]).strip()) > 0:
            txt += '''
Cause of Death {}:
{}


Interval of Death {}:
{}

            '''.format(k, row[cause], k, row[interval])

    if not pd.isna(row['Conditions Part II']) and len(str(row['Conditions Part II']).strip()) > 0:
        txt += '''
Additional Conditions:
{}

                '''.format(row['Conditions Part II'])

    if not pd.isna(row['Injury Description']) and len(str(row['Injury Description']).strip()) > 0:
        txt += '''
Injury Description:
{}

                        '''.format(row['Injury Description'])

    if not pd.isna(row['Injury Place_y']) and len(str(row['Injury Place_y']).strip()) > 0:
        txt += '''
        
Injury Place:
{}
                        '''.format(row['Injury Place_y'])

    return txt.strip()


def load_files():
    lit_df = pd.read_csv('{}{}'.format(path, lit_file))
    stats_df = pd.read_csv('{}{}'.format(path, stat_file))

    df = pd.merge(stats_df, lit_df, on='State File Number')
    # cols = df.columns
    # for c in cols:
    #     print('"' + c + '",')

    results = list()
    n = 0
    for index, row in df.iterrows():
        dt = datetime.strptime(row['Date of Death'], '%m/%d/%Y').isoformat()
        d = {"subject": row['State File Number'],
             "source": "WA_Death_Records",
             "report_type": "Death Record",
             "report_text": make_text(row),
             "report_id": 'WA_DR_{}'.format(row['State File Number']),
             "id": 'WA_DR_{}'.format(row['State File Number']),
             "report_date": dt,
             "age_attr": row['Age'],
             "sex_attr": row['Sex'],
             "birthpace_country_attr": row['Birthplace Country'],
             "armed_forces_attr": row['Armed Forces'],
             "marital_status_attr": row['Marital Status']
             }
        for ac in additional_columns:
            key = ("_".join(ac.split(' '))).lower() + '_attr'
            val = row[ac]
            if isinstance(val, str):
                if len(val.strip()) > 0:
                    d[key] = val
            else:
                if not pd.isna(val):
                    d[key] = val
        results.append(d)
        if len(results) % 10 == 0:
            n += 10
            write_results(results)
            results = list()
            print('loaded {} records'.format(n))
    n += (len(results))
    write_results(results)
    print('DONE - loaded {} records'.format(n))


def write_results(results):
    if len(results) == 0:
        return

    solr_url = "http://18.220.133.76:8983/solr/sample"
    url = solr_url + '/update?commit=true'
    headers = {
        'Content-type': 'application/json',
    }

    data = json.dumps(results)
    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 200:
        print('fail')
    else:
        print('ok')


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    load_files()
