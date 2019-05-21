import json
from datetime import datetime

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

path = '/Users/home/Documents/WashingtonStateData/'
files = [
    ('DeathLitF2012.csv', 'DeathStatF2012.xlsx', 'ISO-8859-1', 'utf-8'),
    ('DeathLit2018Q4.csv', 'DeathStat2018Q4.csv', 'utf-8', 'utf-8'),
    ('DeathLitF2013.csv', 'DeathStatF2013.xlsx', 'ISO-8859-1', 'utf-8'),
    ('DeathLitF2014.csv', 'DeathStatF2014.xlsx', 'ISO-8859-1', 'utf-8'),
    ('DeathLitF2015.csv', 'DeathStatF2015.xlsx', 'ISO-8859-1', 'utf-8'),
    ('DeathLitF2016.csv', 'DeathStatF2016.xlsx', 'ISO-8859-1', 'utf-8'),
    ('DeathLitF2010.csv', 'DeathStatF2010.xlsx', 'ISO-8859-1', 'utf-8'),
    ('DeathLit2017Q3.csv', 'DeathStat2017Q3.xlsx', 'ISO-8859-1', 'utf-8'),
    ('DeathLitF2011.csv', 'DeathStatF2011.xlsx', 'ISO-8859-1', 'utf-8')
    ]

additional_columns = [
    "Age",
    "Sex",
    "Birthplace Country",
    "Armed Forces",
    "Marital Status",
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
        interval = 'Interval Time Line {}'.format(k)
        if not pd.isna(row[cause]) and len(str(row[cause]).strip()) > 0:
            txt += '''
Cause of Death {}:
{}.  


Interval of Death {}:
{}. 

            '''.format(k, row[cause], k, row[interval])

    if not pd.isna(row['Other Significant Conditions']) and len(str(row['Other Significant Conditions']).strip()) > 0:
        txt += '''
Additional Conditions:
{}. 

                '''.format(row['Other Significant Conditions'])

    if not pd.isna(row['How Injury Occurred']) and len(str(row['How Injury Occurred']).strip()) > 0:
        txt += '''
How Injury Occurred:
{}. 

                        '''.format(row['How Injury Occurred'])

    if 'Place of Injury' in row and not pd.isna(row['Place of Injury']) and len(
            str(row['Place of Injury']).strip()) > 0:
        txt += '''
        
Injury Place:
{}. 
                        '''.format(row['Place of Injury'])

    return txt.strip().replace('..', '.')


def load_files(lit_file, stat_file, enc1, enc2):
    print(lit_file, stat_file)
    if not lit_file.endswith('xlsx'):
        lit_df = pd.read_csv('{}{}'.format(path, lit_file), encoding=enc1)
        col_names = lit_df.columns
        print(col_names)
        if len(col_names) == 15:
            cols = ["State File Number", "Cause of Death Line A",
                    "Cause of Death Line B", "Cause of Death Line C",
                    "Cause of Death Line D", "Interval Time Line A",
                    "Interval Time Line B", "Interval Time Line C",
                    "Interval Time Line D", "Due to B", "Due to C", "Due to D",
                    "Other Significant Conditions",
                    "How Injury Occurred", "Place of Injury"]
        elif len(col_names) == 16:
            cols = ["State File Number", "Cause of Death Line A",
                    "Cause of Death Line B", "Cause of Death Line C",
                    "Cause of Death Line D", "Interval Time Line A",
                    "Interval Time Line B", "Interval Time Line C",
                    "Interval Time Line D", "Due to B", "Due to C", "Due to D",
                    "Other Significant Conditions",
                    "How Injury Occurred", "Place of Injury", ""]
        elif len(col_names) == 17:
            cols = ["State File Number", "Cause of Death Line A",
                    "Cause of Death Line B", "Cause of Death Line C",
                    "Cause of Death Line D", "Interval Time Line A",
                    "Interval Time Line B", "Interval Time Line C",
                    "Interval Time Line D", "Due to B", "Due to C", "Due to D",
                    "Other Significant Conditions",
                    "How Injury Occurred", "Place of Injury", "", ""]
        else:
            cols = ["State File Number", "Cause of Death Line A",
                    "Cause of Death Line B", "Cause of Death Line C",
                    "Cause of Death Line D", "Interval Time Line A",
                    "Interval Time Line B", "Interval Time Line C",
                    "Interval Time Line D",
                    "Other Significant Conditions",
                    "How Injury Occurred", "Place of Injury"]
        lit_df.columns = cols
    else:
        lit_df = None
    # if not stat_file.endswith('xlsx'):
    #     stats_df = pd.read_csv('{}{}'.format(path, stat_file), encoding=enc2)
    # else:
    #     stats_df = None

    df = lit_df
    # cols = df.columns
    # for c in cols:
    #     print('"' + c + '",')

    results = list()
    n = 0
    for index, row in df.iterrows():
        id = str(row['State File Number'])
        if 'Date of Death' in row:
            dt = datetime.strptime(row['Date of Death'], '%m/%d/%Y').isoformat()
        else:
            dt = "{}-01-01T00:00:00Z".format(id[0:4])
        report_text = make_text(row)
        if len(report_text) == 0:
            continue
        d = {"subject": id,
             "source": "WA_Death_Records",
             "report_type": "Death Record",
             "report_text": report_text,
             "report_id": 'WA_DR_{}'.format(id),
             "id": 'WA_DR_{}'.format(id),
             "report_date": dt
             }
        for ac in additional_columns:
            if ac not in row.index.values:
                continue
            key = ("_".join(ac.split(' '))).lower() + '_attr'
            val = row[ac]
            if isinstance(val, str):
                if len(val.strip()) > 0:
                    d[key] = val
            else:
                if not pd.isna(val):
                    d[key] = val
        results.append(d)
        if len(results) % 1000 == 0:
            n += 1000
            write_results(results)
            results = list()
            print('loaded {} records'.format(n))
    n += (len(results))
    write_results(results)
    print('DONE loaded {} records'.format(n))


def write_results(results):
    if len(results) == 0:
        return

    solr_url = "https://solr.internal.claritynlp.cloud/solr/sample"
    url = solr_url + '/update?commit=true'
    headers = {
        'Content-type': 'application/json',
    }

    ok = True
    data = json.dumps(results)
    try:
        response = requests.post(url, headers=headers, data=data, auth=HTTPBasicAuth('admin', '<password>'))
        if response.status_code != 200:
            ok = False
    except Exception as ex:
        print(ex)
    if not ok:
        try:
            response = requests.post(url, headers=headers, data=data, auth=HTTPBasicAuth('admin', '<password>'))
            if response.status_code != 200:
                print('retry fail')
            else:
                print('retry ok')
        except Exception as ex:
            print(ex)
    else:
        print('ok')


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    for f in files:
        load_files(f[0], f[1], f[2], f[3])
