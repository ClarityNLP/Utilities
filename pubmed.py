from Bio import Entrez
import requests
import time
from bs4 import BeautifulSoup
import json
import csv
import random
import sys
import html


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
    "karnofsky",
    "brca",
    "breast cancer",
    "suicide",
    "death",
    "murder",
    "autopsy",
    "mortality",
    "overdose",
    "drug use",
    "illicit",
    "drug abuse",
    "addiction",
    "addict"
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
    time.sleep(random.uniform(0.5, 3.0))
    Entrez.email = 'cah@gatech.edu'
    handle = Entrez.esearch(db='pubmed',
                            retmax='10000',
                            retmode='xml',
                            term=query)
    results = Entrez.read(handle)
    handle.close()
    return results


if __name__ == "__main__":
    max_len = 100
    try:
        if len(sys.argv) > 1:
            start_at = int(sys.argv[1])
        else:
            start_at = 0
    except:
        start_at = 0
    new_terms = set()
    from requests.auth import HTTPBasicAuth
    auth = HTTPBasicAuth('admin', 'u0z4@VpPE')
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
                if len(diagnosis_name) < max_len:
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
                if len(name) < max_len:
                    new_terms.add(name)

    with open('./general/terms.txt') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='|')
        for row in csv_reader:
            line_count += 1
            name = row[0]
            if len(name) < max_len:
                new_terms.add(name)

    terms.extend(list(new_terms))
    terms = sorted(terms)
    result_list = list()
    print(len(terms))

    solr_url = "https://solr.internal.claritynlp.cloud/solr/sample"
    solr_url = solr_url + '/update?commit=true'
    headers = {
        'Content-type': 'application/json',
    }

    for i in range(len(terms)):
        if i < start_at:
            continue
        t = terms[i]
        print('querying term={}, id={}'.format(t, i))
        id_list = search(t)

        for j in range(len(id_list['IdList'])):
            id = id_list['IdList'][j]
            # print('querying id={}, term={}, term_index={}, id_index={}'.format(id, t, i, j))
            time.sleep(random.uniform(0.4, 5.0))
            url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=' + str(id) + \
                             '&tool=my_tool&email=cah@gatech.edu&rettype=abstract'
            try:
                r = requests.get(url)
            except:
                time.sleep(random.uniform(0.1, 10.0))
                try:
                    r = requests.get(url)
                except:
                    continue

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
                    keywords = list()
                    for k in soup.find_all('keyword'):
                        keywords.append(k.getText())
                    country = ''
                    countries = soup.find_all('country')
                    if len(countries) > 0:
                        country = countries[0].getText()
                    authors = list()
                    for a in soup.find_all('author'):
                        authors.append('{}, {}'.format(a.lastname.getText(), a.forename.getText()))
                    affiliations = list()
                    for a in soup.find_all('affiliation'):
                        affiliations.append(a.getText())
                    cr = ''
                    crs = soup.find_all('copyrightinformation')
                    if len(crs) > 0:
                        cr = crs[0].getText()
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
                    if not report_text or len(report_text.strip()) == 0:
                        continue

                    doc = {
                        'query_term_attr': t,
                        'subject': journal_title,
                        'report_id': report_id,
                        "report_date": "{}-{}-{}T00:00:00Z".format(year, month, day),
                        'report_type': 'Journal Abstract',
                        'id': report_id,
                        'source': source,
                        'report_text': report_text.strip(),
                        'title_attr': title_attr,
                        'keyword_attrs': keywords,
                        'country_attr': country,
                        'copyright_attr': cr,
                        'authors_attrs': authors,
                        'affiliations_attrs': affiliations,
                        'term_index_attr': i
                    }

                    result_list = [doc]
                    data = json.dumps(result_list, indent=4)
                    print(data)
                    response2 = requests.post(solr_url, headers=headers, data=data, auth=auth)

                    if response2.status_code == 200:
                        print('SUCCESS', response2)
                    else:
                        print('RETRYING', response2)
                        time.sleep(random.uniform(0.1, 10.0))
                        response2 = requests.post(solr_url, headers=headers, data=data, auth=auth)
                        if response2.status_code == 200:
                            print('SUCCESS', response2)
                        else:
                            print('FAIL', response2)
                except Exception as exc:
                    print(exc)

        if len(result_list) > 0:
            data = json.dumps(result_list)
            response2 = requests.post(solr_url, headers=headers, data=data, auth=auth)

            if response2.status_code == 200:
                print("Uploaded pubmed batch")
            else:
                print('upload to solr failed')
            result_list = list()

    if len(result_list) > 0:
        data = json.dumps(result_list)
        response2 = requests.post(solr_url, headers=headers, data=data, auth=auth)

        if response2.status_code == 200:
            print("Uploaded pubmed batch")
        else:
            print('upload to solr failed')

