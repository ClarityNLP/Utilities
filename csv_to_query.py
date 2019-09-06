import ast
import csv
import json
import os
import string

import nltk
import requests
import tika
from bs4 import BeautifulSoup
from nltk.corpus import stopwords

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
phenotype "Form {}, Bundle {}" version "1";

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
termset {}_terms: [
    {}
];

'''

basic_data_entity_template = '''
define final {}:
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

# +
cql_concept_template = '''
        define "%s_concept": Concept {
            %s
        }

'''


cql_result_template = '''
        define "{}":
            [{}: Code in "{}_concept"]
'''

cql_task_template = '''
define final %s:
    Clarity.CQLExecutionTask({
        "task_index": 0,
        cql: \"\"\"
                %s
             \"\"\"
    });
'''


def merger(dict1, dict2):
    res = {**dict1, **dict2}
    return res


def parse_questions_from_feature_csv(folder_prefix='output',
                                     form_name="My Custom Form",
                                     file_name='./custom_query/sample.csv',
                                     output_dir='./custom_query'):
    if not os.path.exists(os.path.join(output_dir, folder_prefix)):
        os.mkdir(os.path.join(output_dir, folder_prefix))

    with open(file_name, 'r', encoding='utf-8', errors='ignore') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',', quotechar='"')

        form_data = {
            "name": form_name,
            "owner": "gatech",
            "allocated_users": ["admin"],
            "groups": list(),
            "questions": list(),
            "evidence_bundles": list()
        }

        n = 0

        groups = set()
        grouping = None
        new_grouping = False
        last_question = None
        new_question = False
        question_num = None
        termsets = list()
        entities = list()
        operations = list()
        concepts = list()
        comment = ''
        group_number = 1
        evidence_count = 0

        evidence = dict()
        evidence_bundles = set()

        name = None
        group = None
        q_type = None
        evidence_bundle = None
        map_qs = list()

        last_row = None
        for r in reader:
            row = json.loads(json.dumps(r, indent=4, sort_keys=True).replace('\\u00a0', ' ').replace('\\u00ad', '-')
                             .replace('\\u2265', '>=').replace('\\u2264', '<=').replace('\\u00b3', '3').replace(
                '\\u00b0', ' degrees')
                             .replace('\\u03b3', 'gamma').replace('\\u03b1', 'alpha').replace('\\u00b5', 'u'))

            if len(row['evidence_bundle']) > 0 and len(row['#']) == 0:

                if last_row:
                    print('no question, using last {}'.format(last_row['#']))
                    row['#'] = last_row['#']
                    row['group'] = last_row.get('group')
                    row['name'] = last_row['name']
                    row['type'] = last_row.get('type')
                else:
                    print('no question')

            last_row = row
            if row['#'] == '':
                continue

            if grouping and grouping != row['evidence_bundle']:
                new_grouping = True

            old_grouping = grouping
            if question_num and last_question and str(last_question) != str(row['#'].strip()):
                if question_num in map_qs:
                    for i in range(len(form_data['questions'])):
                        q = form_data['questions'][i]
                        if q['question_number'] == question_num:
                            merged = merger(q['evidence_bundle'], evidence)
                            form_data['questions'][i]['evidence_bundle'] = merged

                else:
                    print('saving question ', last_question)
                    q = {
                        "name": name,
                        "question_type": q_type,
                        "question_number": question_num,
                        "group": group,
                        "evidence_bundle": evidence,
                        "nlpql_grouping": grouping
                    }
                    map_qs.append(question_num)
                    form_data['questions'].append(q)
                    evidence = dict()

            last_question = question_num

            if not old_grouping:
                old_grouping = row['evidence_bundle'].strip()

            question_num = row['#'].strip()
            grouping = row['evidence_bundle'].strip()
            feature_name = row['feature_name'].strip()
            name = row['name'].strip()
            q_type = row['type'].strip()
            group = row['group'].strip()
            evidence_bundle = row['evidence_bundle'].strip()
            fhir_resource_type = row['fhir_resource_type'].strip()
            code_sys = row['code_system'].strip()
            codes = [x.strip() for x in row['codes'].strip().split(',')]
            valueset_oid = row['valueset_oid'].strip()
            nlp_task_type = row['nlp_task_type'.strip()].lower()
            terms = [x.strip() for x in row['text_terms'].strip().split(',')]
            value_min = row['value_min'].strip()
            value_max = row['value_max'].strip()
            value_enum_set = row['value_enum_set'].strip().split(',')
            logic = row['logic'].strip()
            group_formatted = '_'.join(old_grouping.strip().lower().split(' ')).replace(',', '').replace('_/_', '_')

            no_evidence = False
            if len(row['evidence_bundle']) == 0 or len(row['feature_name']) == 0:
                print('no evidence for question {}'.format(question_num))
                new_grouping = True
                no_evidence = True

            if new_grouping:
                if len(termsets) == 0 and len(entities) == 0 and len(operations) == 0 and len(concepts) == 0:
                    print('no query for grouping {}'.format(group_formatted))
                else:
                    with open('{}/{}/{}.nlpql'.format(output_dir, folder_prefix,
                                                      group_formatted),
                              'w') as f:
                        ts_string = '\n\n'.join(termsets)
                        de_string = '\n\n'.join(entities)
                        op_string = '\n\n'.join(operations)
                        query = nlpql_template2.format(form_name, old_grouping, ts_string, de_string, op_string,
                                                       comment)
                        f.write(query)

                group_number += 1
                termsets = list()
                entities = list()
                operations = list()
                concepts = list()
                comment = ''
                new_grouping = False
                # form, group, termsets, data entities, operations, comments

            if not no_evidence:
                valid = list(string.digits)
                valid.extend(list(string.ascii_letters))
                valid.append('_')

                feature_name = ''.join([t for t in feature_name if t in valid])
                if len(name.strip()) == 0:
                    continue

                if q_type == 'MS':
                    q_type = 'MULTIPLE_SELECT'
                if q_type == 'MC':
                    q_type = 'MULTIPLE_CHOICE'
                if q_type == 'TEXT+MC':
                    q_type = 'TEXT_WITH_MULTIPLE_CHOICE'

                features = list()
                if len(group) > 0:
                    groups.add(group)
                if len(evidence_bundle) > 0:
                    evidence_bundles.add(evidence_bundle)

                if len(feature_name) == 0 or len(evidence_bundle) == 0 or len(nlp_task_type) == 0:
                    continue
                comment += '\n\n'
                comment += json.dumps(row, indent=4, sort_keys=True)

                if len(terms) > 0 and 'assertion' in nlp_task_type:
                    term_string = '", "'.join(terms)
                    if term_string.strip() != '':
                        term_string = '"' + term_string + '"'
                        term_string = term_string.replace(', " unspecified",', ',')
                        termsets.append(termset_template.format(feature_name, term_string))
                        pq = '''Clarity.ProviderAssertion({
          termset: [%s_terms]
        });
                        ''' % feature_name
                        pa = basic_data_entity_template.format(feature_name, pq)
                        features.append(feature_name)
                        entities.append(pa)

                if len(terms) > 0 and 'value' in nlp_task_type:
                    term_string = '", "'.join(terms)
                    if term_string.strip() != '':
                        term_string = '"' + term_string + '"'
                        term_string = term_string.replace(', " unspecified",', ',')
                        termsets.append(termset_template.format(feature_name, term_string))

                        v_min = ''
                        v_max = ''
                        v_enum_string = ''

                        if len(value_min) > 0:
                            v_min = ',minimum_value: "{}"'.format(value_min)
                        if len(value_max) > 0:
                            v_max = ',maximum_value: "{}"'.format(value_max)
                        if len(value_enum_set) > 0:
                            v_enum = ''
                            for v in value_enum_set:
                                if len(v) == 0:
                                    continue
                                if len(v_enum) > 0:
                                    v_enum += ', '
                                v = v.replace('?', '').replace('"', '').replace("'", '')
                                v_enum += ('"{}"'.format(v))
                            if len(v_enum) > 0:
                                v_enum_string = ', enum_list: [{}]'.format(v_enum)
                        pq = '''Clarity.ValueExtraction({
                  termset: [%s_terms]
                  %s
                  %s
                  %s
                });
                                ''' % (feature_name, v_min, v_max, v_enum_string)
                        pa = basic_data_entity_template.format(feature_name, pq)
                        features.append(feature_name)
                        entities.append(pa)

                if (len(codes) > 0 or len(valueset_oid) > 0) and 'cql' in nlp_task_type:
                    c_string = ''
                    for c in codes:
                        if len(c_string) > 0:
                            c_string += ', \n            '
                        code = c.replace('?', '').replace('"', '').replace("'", '')
                        c_string += 'Code \'{}\' from "{}"'.format(code, code_sys)
                    cql_concept = cql_concept_template % (feature_name, c_string)
                    concepts.append(cql_concept)
                    resource = fhir_resource_type

                    cql_res = cql_result_template.format(feature_name, resource, feature_name)
                    cql = cql_template.format(cql_concept, cql_res)
                    entities.append(cql_task_template % (feature_name, cql))
                    features.append(feature_name)

                if evidence_bundle not in evidence:
                    evidence[evidence_bundle] = list()
                evidence[evidence_bundle].append(feature_name)
                if new_question:
                    evidence_count += 1

            n += 1

        form_data['groups'] = list(groups)
        form_data['evidence_bundles'] = list(evidence_bundles)
        with open('{}/{}/questions.json'.format(output_dir, folder_prefix),
                  'w') as f:
            form_data['questions_with_evidence_count'] = evidence_count
            f.write(json.dumps(form_data, indent=4))
        print(evidence_count)
        return form_data


if __name__ == "__main__":
    nltk.download('stopwords')
    parse_questions_from_feature_csv()

