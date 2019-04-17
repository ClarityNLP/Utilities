from bs4 import BeautifulSoup
import requests
import os

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
pdfs = list()
for file in os.listdir("./cimbtr_forms/"):
    if file.endswith(".txt"):
        pdfs.append(file)

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
    forms = {}
    for p in pdfs:
        name = p.split('.')[-2]
        question_dict = {}
        with open('./cimbtr_forms/{}'.format(p), 'r') as txt_file:
            lines = txt_file.readlines()
            questions = list()
            header = 'UNKNOWN'
            txt = ''
            last_question = 0
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
                    if q_number and last_question < q_number and q_number > 1:
                        last_question = q_number
                        if len(txt) > 0:
                            out_txt = "{} {}\n\n{}".format(q_number, q_text, txt)
                            question_dict[q_number] = out_txt
                        # print('is_a_new_question', q_number)
                        txt = ''
                    else:
                        txt += l

        forms[name] = question_dict
    return forms


def stubs(form="4100R4", form_data=None):

    if not form_data:
        form_data = dict()
    nlpql_template = '''
// Phenotype library name
phenotype "Form {}, Question {}" version "1";

// # Referenced libraries #
include ClarityCore version "1.0" called Clarity;

// Data Entities
{}

// Operations
{}

// Comments
/*
{}

*/
 
'''

    form_questions = form_data[form]
    if not form_questions:
        form_questions = dict()
    new_dir = '/Users/charityhilton/repos/CIBMTRaaS/forms/{}/'.format(form)
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    max_questions = 300
    keys = list(form_questions.keys())
    if len(keys) > 0:
        max_questions = max(keys) + 1
    for i in range(1, max_questions):
        print('form {}, question {}'.format(file, i))
        with open('/Users/charityhilton/repos/CIBMTRaaS/forms/{}/question_{}.nlpql'.format(form, i), 'w') as f:
            entities = ""
            operations = ""
            if i in form_questions:
                comments = form_questions[i]
            else:
                comments = ""
            f.write(nlpql_template.format(form, i, entities, operations, comments))


if __name__ == "__main__":
    # get_pdfs()
    form_data = parse_questions()
    for file in os.listdir("./cimbtr_forms/"):
        if file.endswith(".txt"):
            stubs(form=file.split('.')[0], form_data=form_data)
