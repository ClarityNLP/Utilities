from Bio import Entrez
import requests
import time
from bs4 import BeautifulSoup
import json
import csv

terms = [
    "nyha",
    "cancer",
    "carcinoma",
    "prostate",
    "depression",
    "anxiety",
    "ptsd",
    "ejection fraction",
    "chf",
    "congestive heart failure",
    "Orthopnea",
    "karnofsky"
]

months = {
    'Jan': '01',
    'Feb': '02',
    'Mar': '03',
    'Apr': '04',
    'May': '05',
    'Jun': '06',
    'Jul': '07',
    'Aug': '08',
    'Sep': '09',
    'Oct': '10',
    'Nov': '11',
    'Dec': '12'
}


def get_month(string):
    if string in months:
        return months[string]
    else:
        try:
            val = int(string)
            if val < 10:
                return '0' + str(val)
            else:
                return str(val)
        except Exception as ex:
            return '01'


def get_text(item):
    if not item:
        return ''
    if not isinstance(item, str):
        return item.getText()
    else:
        return item


def search(query):
    Entrez.email = 'cah@gatech.edu'
    handle = Entrez.esearch(db='pubmed',
                            retmax='1000',
                            retmode='xml',
                            term=query)
    results = Entrez.read(handle)
    handle.close()
    return results


if __name__ == "__main__":
    new_terms = set()
    with open('./cancer/cancer_tree.json', 'r') as ct:
        tree = json.loads(ct.read())
        for k in tree.keys():
            c = tree[k]
            for cancer in c:
                syns = cancer['synonyms']
                regimens = cancer['regimen_names']
                new_terms.update(syns)
                new_terms.update(regimens)

    with open('./general/diagnosis.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = -1
        for row in csv_reader:
            line_count += 1
            if line_count == 0:
                continue
            else:
                diagnosis_name = row[1]
                if len(diagnosis_name) < 50:
                    new_terms.add(diagnosis_name)

    with open('./drugs/drugs.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = -1
        for row in csv_reader:
            line_count += 1
            if line_count == 0:
                continue
            else:
                name = row[1]
                if len(name) < 50:
                    new_terms.add(name)
    terms.extend(list(new_terms))
    result_list = list()

    solr_url = "http://18.220.133.76:8983/solr/sample"
    url = solr_url + '/update?commit=true'
    headers = {
        'Content-type': 'application/json',
    }

    for t in terms:
        print('querying term', t)
        id_list = search(t)

        for id in id_list['IdList']:
            print('querying id ', id)
            r = requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=' +
                             str(id) +
                             '&tool=my_tool&email=cah@gatech.edu&rettype=abstract')

            soup = BeautifulSoup(r.content, 'html.parser')
            for art in soup.find_all('pubmedarticle'):
                try:
                    # subject,report_id,report_date,report_type,id,source,report_text
                    source = "PubMed"
                    citation = art.medlinecitation
                    report_id = 'pmid_' + citation.pmid.getText()
                    data = art.pubmeddata
                    art_info = art.article
                    journal = art_info.journal
                    journal_title = get_text(journal.title)
                    journal_issue = journal.journalissue
                    pubdate = journal_issue.pubdate
                    if not pubdate:
                        year = '2019'
                        month = '01'
                        day = '01'
                    else:
                        year = get_text(pubdate.year)
                        month = get_month(get_text(pubdate.month))
                        day = get_text(pubdate.day)
                    if not year or len(year) == 0:
                        year = 2019
                    if not month or len(month) == 0:
                        month = '01'
                    if not day or len(day) == 0:
                        day = '01'

                    title_attr = get_text(art_info.articletitle)
                    report_text = get_text(art_info.abstract)
                    if not report_text:
                        continue

                    doc = {
                        'subject': journal_title,
                        'report_id': report_id,
                        "report_date": "{}-{}-{}T00:00:00Z".format(year, month, day),
                        'report_type': 'Journal Abstract',
                        'id': report_id,
                        'source': source,
                        'report_text': report_text,
                        'title_attr': title_attr
                    }

                    result_list.append(doc)
                    if len(result_list) % 10 == 0:
                        data = json.dumps(result_list)
                        response2 = requests.post(url, headers=headers, data=data)

                        if response2.status_code == 200:
                            print("Uploaded pubmed batch")
                        result_list = list()
                except Exception as exc:
                    print(exc)

            time.sleep(0.4)

    data = json.dumps(result_list)
    response2 = requests.post(url, headers=headers, data=data)

    if response2.status_code == 200:
        print("Uploaded pubmed batch")

