from bs4 import BeautifulSoup
import requests

import tika

headers = [
    'Key Fields',
    'Product',
    'Survival',
    'Recipient Demographics',
    'Cellular Therapy and HCT History',
    'Product Identification',
    'Indication for Cellular Therapy',
    'Infection',
    'Disease Assessment at Last Evaluation Prior to Cellular Therapy',
    'Systemic Therapy Prior to Cellular Therapy Questions',
    'Functional Status',
    'Comorbid Conditions',
    'Clinical Status of Recipient Prior to the Preparative Regimen (Conditioning)',
    'Organ Function Prior to the Preparative Regimen (Conditioning)',
    'Hematologic Findings Prior to the Preparative Regimen (Conditioning)',
    'Pre-HCT Preparative Regimen (Conditioning)',
    'Socioeconomic Information',
    'Toxicities'
]
pdfs = [
    '4100R4.txt'
]

questions_dict = dict()


def question_number(line):
    question_string = ''
    spl = line.split(':')
    try:
        n = int(spl[-1])
    except:
        n = -1

    if len(spl) > 1:
        question_string = spl[0]
    if n != -1 and n < 10000:
        return question_string, n
    else:
        return None, None


def get_pdfs():
    tika.initVM()
    from tika import parser

    page = requests.get('http://www.cibmtr.org/DataManagement/DataCollectionForms/Pages/index.aspx')
    soup = BeautifulSoup(page.text, 'html.parser')

    locs = soup.find_all('a')
    for loc in locs:
        href = loc.get('href', '')
        if href.startswith('javascript:WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions'):
            args = href.split('"')
            for a in args:
                if a.startswith('http') and a.endswith('pdf') and not a.endswith('EC.pdf') and not \
                        a.endswith('+.pdf') and 'Log' not in a:
                    print(a)
                    name = a.split('/')[-1]
                    if name.startswith('Form'):
                        continue
                    response = requests.get(a)

                    pdf_name = './cimbtr_forms/{}'.format(name)
                    with open(pdf_name, 'wb') as f:
                        f.write(response.content)

                    parsed = parser.from_file(pdf_name)
                    with open('./cimbtr_forms/{}.txt'.format(name.split('.')[0]), 'w') as f:
                        f.write(parsed['content'].strip())


def parse_questions():
    for p in pdfs:
        with open('./cimbtr_forms/{}'.format(p), 'r') as txt_file:
            lines = txt_file.readlines()
            questions = list()
            header = 'UNKNOWN'
            txt = ''
            for l in lines:
                if len(l.strip()) == 0:
                    continue
                is_header = False
                for h in headers:
                    if l.startswith(h):
                        header = h
                        is_header = True
                        break
                if not is_header:
                    q_text, q_number = question_number(l)
                    if q_number and q_number > 1:
                        print('is_a_new_question', q_number)
                    else:
                        txt += l


if __name__ == "__main__":
    # get_pdfs()
    parse_questions()
