import csv
import json
import os

import requests
import tika
from bs4 import BeautifulSoup

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

nlpql_template2 = '''
// Phenotype library name
phenotype "Form {}, Group {}" version "1";

// # Referenced libraries #
include ClarityCore version "1.0" called Clarity;

// Termsets
{}

// Data Entities
{}

// Operations
{}

// Comments
/*
{}

*/

'''

termset_template = '''
termset question_{}_terms: [
    {}
];

'''

provider_assertion_template = '''
define final question_{}_assertion:
    {}
'''

cql_template = '''
library Retrieve2 version '1.0'

using FHIR version '3.0.0'

include FHIRHelpers version '3.0.0' called FHIRHelpers

codesystem "LOINC": 'http://loinc.org'
codesystem "SNOMED-CT": 'urn:oid:2.16.840.1.113883.6.96'
codesystem "RxNorm": 'http://www.nlm.nih.gov/research/umls/rxnorm'

context Patient

{}

{}

'''

cql_concept_template = '''
define "question_%s_concept": Concept {
    %s
}

'''

# Code '26464-8' from "LOINC",
# Code '804-5' from "LOINC",
# Code '6690-2' from "LOINC",
# Code '49498-9' from "LOINC"

cql_result_template = '''
define "question_{}_cql":
[{}: Code in "question_{}_concept"]
'''

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


def parse_questions_from_csv(folder_prefix='4100r4',
                             feature_prefix='form_4100_',
                             form_name="Form 4100 R4.0",
                             file_name='/Users/charityhilton/Box/Form4100_analysis_cibmtr.csv'):
    with open(file_name, 'r', encoding='utf-8-sig', errors='ignore') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',', quotechar='"', dialect='excel')

        form_data = {
            "name": form_name,
            "owner": "gatech",
            "allocated_users": ["admin"],
            "groups": [],
            "questions": []
        }

        n = 0

        groups = set()
        group = None
        new_group = False
        termsets = list()
        entities = list()
        operations = list()
        concepts = list()
        results = list()
        comment = ''
        group_number = 1

        for r in reader:
            row = json.loads(json.dumps(r, indent=4, sort_keys=True).replace('\\u00a0', ' ').replace('\\u00ad', '-')
                             .replace('\\u2265', '>=').replace('\\u2264', '<=').replace('\\u00b3', '3').replace(
                '\\u00b0', ' degrees')
                             .replace('\\u03b3', 'gamma').replace('\\u03b1', 'alpha').replace('\\u00b5', 'u'))
            if group and group != row['Group']:
                new_group = True
            old_group = group
            is_cql = row['CQL'] == 'TRUE'
            is_nlpql = row['NLPQL'] == 'TRUE'
            question_num = row['Question']
            group = row['Group']
            name = row['Name']
            answers = row['Answers'].split(',')
            codes = row['Code(s)'].split(',')
            code_sys = row['Code System']
            q_type = row['Type']
            terms = row['Terms'].split(',')
            # notes = row['Notes (If data present)']

            if len(name.strip()) == 0:
                continue

            if q_type == 'MS':
                q_type = 'MULTIPLE_SELECT'
            if q_type == 'MC':
                q_type = 'MULTIPLE_CHOICE'
            if q_type == 'TEXT+MC':
                q_type = 'TEXT_WITH_MULTIPLE_CHOICE'

            answer_sets = list()
            if q_type != 'DATE' and q_type != 'TEXT':
                for a in answers:
                    answer_sets.append({
                        'text': a.replace('\n', ' ').strip(),
                        'value': '_'.join(a.split(' ')).lower().replace('(', '').replace(')', '').replace('.', '')
                            .replace('\n', ' ').strip()
                    })
            question = {
                "question_name": name,
                "question_type": q_type,
                "question_number": question_num,
                "has_cql": is_cql,
                "has_nlpql": is_nlpql,
                "group": group,
                "answers": answer_sets,
                "nlpql_feature": '{}question_{}'.format(feature_prefix, question_num)
            }
            if len(group) > 0:
                groups.add(group)
            form_data['questions'].append(question)
            comment += '\n\n'
            comment += json.dumps(row, indent=4, sort_keys=True)

            if len(terms) > 0:
                term_string = '", "'.join(terms)
                if term_string.strip() != '':
                    term_string = '"' + term_string + '"'
                    term_string = term_string.replace(', " unspecified",', ',')
                    termsets.append(termset_template.format(str(question_num), term_string))
                    pq = '''Clarity.ProviderAssertion({
      termset: [question_%s_terms]
    });
                    ''' % str(question_num)
                    pa = provider_assertion_template.format(question_num, pq)
                    entities.append(pa)
            if len(codes) > 0:
                if len(codes) == 1 and codes[0].strip() == '':
                    pass
                else:
                    c_string = ''
                    for c in codes:
                        c_string += 'Code \'{}\' from "{}"\n'.format(c, code_sys)
                    concepts.append(cql_concept_template % (question_num, c_string))
                    resource = 'Observation'
                    if code_sys == 'RxNorm':
                        resource = 'Medication'

                    results.append(cql_result_template.format(question_num, resource, question_num))

            if new_group:
                group_formatted = '_'.join(old_group.strip().lower().split(' ')).replace(',', '').replace('_/_', '_')
                with open('/Users/charityhilton/repos/CIBMTR_knowledge_base/{}/group_{}_{}.nlpql'.format(folder_prefix,
                                                                                                         group_number,
                                                                                                      group_formatted),
                          'w') as f:
                    ts_string = '\n\n'.join(termsets)
                    de_string = '\n\n'.join(entities)
                    op_string = '\n\n'.join(operations)
                    query = nlpql_template2.format(form_name, old_group, ts_string, de_string, op_string, comment)
                    f.write(query)
                with open('/Users/charityhilton/repos/CIBMTR_knowledge_base/{}/group_{}_{}.cql'.format(folder_prefix,
                                                                                                         group_number,
                                                                                                         group_formatted),
                          'w') as f:
                    cs_string = '\n\n'.join(concepts)
                    rs_string = '\n\n'.join(results)
                    query = cql_template.format(cs_string, rs_string)
                    f.write(query)
                group_number += 1
                termsets = list()
                entities = list()
                operations = list()
                concepts = list()
                results = list()
                comment = ''
                new_group = False
                # form, group, termsets, data entities, operations, comments

            n += 1

        form_data['groups'] = list(groups)
        with open('/Users/charityhilton/repos/CIBMTR_knowledge_base/{}/questions.nlpql'.format(folder_prefix),
                  'w') as f:
            f.write(json.dumps(form_data, indent=4))
        return form_data


if __name__ == "__main__":
    # get_pdfs()
    # form_data = parse_questions()
    # for file in os.listdir("./cimbtr_forms/"):
    #     if file.endswith(".txt"):
    #         stubs(form=file.split('.')[0], form_data=form_data)
    parse_questions_from_csv()
