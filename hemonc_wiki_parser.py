from mwparserfromhell import parse
from mwparserfromhell.nodes import *
from mwparserfromhell.nodes.external_link import ExternalLink
from mwparserfromhell.nodes.wikilink import Wikilink
from mwparserfromhell.nodes.comment import Comment
from anytree import Node, RenderTree
from pathlib import Path
import json

treatment_names = ['Chemoradiotherapy', 'Supportive medications', 'Chemotherapy', 'Immunosuppressive therapy',
                   'CNS prophylaxis', 'Chemotherapy, part 1', 'Chemotherapy, part 2', 'Primary therapy',
                   'Immunotherapy', 'Anticoagulation']
nlpql_template = '''
// Phenotype library name
phenotype "{}" version "1";

// Phenotype library description 
description "Generated query for cancer treatment based on https://hemonc.org/wiki/Main_Page";

// # Referenced libraries #
include ClarityCore version "1.0" called Clarity;

documentset Docs:
    Clarity.createReportTypeList(["Nursing/other", "Nursing", "Physician ", "Discharge summary", "Radiology",
         "General", "ECG", "Pathology", "Echo"]);

// Medication(s) inclusion criteria termset, if medication criteria present
{}

// Results
{}
 
'''


def title_text(parent):
    if not parent.title:
        return ''
    title = ''
    for t1 in parent.title.nodes:
        title += (pretty_text(t1) + ' ')
    return title.strip()


def contents_text(parent):
    if not parent.contents:
        return ''
    title = ''
    for t1 in parent.contents.nodes:
        title += (pretty_text(t1) + ' ')
    return title.strip()


def pretty_text(thing):
    txt = ''
    if isinstance(thing, Text):
        txt = str(thing)
    elif isinstance(thing, ExternalLink):
        txt = title_text(thing)
    elif isinstance(thing, Wikilink):
        txt = title_text(thing)
    elif isinstance(thing, Tag):
        txt = contents_text(thing)
    elif isinstance(thing, Template) or isinstance(thing, Comment):
        txt = ''
        # ignore for now
    elif isinstance(thing, Heading):
        txt = (title_text(thing) + ": ")
    else:
        print('what is this thing {}'.format(type(thing)))
    return txt.strip()


def normalize_drug(d):
    return ' '.join(d.split('_')).lower()


def generate_medications(brands, drugs):
    define_str = ''
    keys = []

    if len(brands) > 1:
        n = 0
        for b in brands:
            terms = '"{}", "{}"'.format(normalize_drug(b), normalize_drug(drugs[n]))
            nlpql = '''
    
termset MedicationTerms%d:[
    %s
];

define Medications%d:
  Clarity.ProviderAssertion({
    termset:[MedicationTerms%d],
    documentset:[Docs]
   }); 
        
            ''' % (n, terms, n, n)
            keys.append('Medications{}'.format(n))
            n += 1
            define_str += nlpql

        return define_str, keys
    else:
        terms = '"{}", "{}"'.format(normalize_drug(brands[0]), normalize_drug(drugs[0]))
        nlpql = '''

termset MedicationTerms:[
    %s
];

define final ReceivedTherapy:
  Clarity.ProviderAssertion({
    termset:[MedicationTerms],
    documentset:[Docs]
   }); 

                ''' % terms
        return nlpql, []


def generate_results(keys):
    clause = " AND ".join(keys)
    return '''

define final ReceivedAllTherapies:
    where %s;
        ''' % clause


def generate_nlpql(cancer, treatments):
    # 'drugs': cn.drugs,
    # 'brands': cn.brands,
    # 'regimen': cn.regimen,
    # 'regimen_type': cn.regimen_type,
    # 'cancer_type': oncology_class
    i = 0
    for k in treatments.keys():
        obj = treatments[k]
        regimen = k
        regimen_type = obj['regimen_type']
        if regimen_type == '':
            nlpql_name = 'Regimen for {}, {}'.format(cancer, regimen)
        else:
            nlpql_name = 'Regimen for {}, {} ({})'.format(cancer, regimen, regimen_type)
        nlpql_name = " ".join(nlpql_name.replace('"', "'").split("_"))
        define_str, keys = generate_medications(obj['brands'], obj['drugs'])
        if len(obj['brands']) > 1:
            result_str = generate_results(keys)
        else:
            result_str = ''
        print('nlpql for ', nlpql_name)
        with open('./cancer_nlpql/{}_{}.nlpql'.format(cancer, i), 'w') as file:
            file.write(nlpql_template.format(nlpql_name, define_str, result_str))
            i += 1


if __name__ == "__main__":
    path_list = Path('./cancer_wiki').glob('**/*.txt')
    for p in path_list:
        # because path is object not string
        path_str = str(p)
        """
        Wiki source here: https://hemonc.org/wiki/Main_Page
        """
        last_nodes = dict()
        nodes = list()
        treatment_nodes = list()
        is_treatment = False

        with open('./' + path_str) as f:
            wikicode = parse(f.read())
            oncology_class = f.name.split('/')[-1].split('.')[0]
            # print(oncology_class)
            cur_level = 0
            cur_title = None
            cur_node = None
            for n in wikicode.nodes:
                if isinstance(n, Heading):
                    cur_title = title_text(n)
                    is_treatment = cur_title in treatment_names and n.level >= 3

                    if cur_level == 0:
                        if is_treatment:
                            cur_node = Node(cur_title, drugs=list(), brands=list(), instructions=list(),
                                            regimen='', variant='', regimen_type='')
                        else:
                            cur_node = Node(cur_title, data=list(), drugs=list(), brands=list(), instructions=list(),
                                            regimen='', variant='', regimen_type='')

                    else:
                        parent_level = n.level - 1
                        if parent_level in last_nodes:
                            parent = last_nodes[parent_level]

                            if is_treatment:
                                if parent_level - 1 >= 0:
                                    grandparent = last_nodes[parent_level-1].name
                                else:
                                    grandparent = ''
                                if parent_level - 2 >= 0:
                                    g_grandparent = last_nodes[parent_level-2].name
                                else:
                                    g_grandparent = ''
                                if parent.name != 'Regimen':
                                    variant = parent.name
                                else:
                                    variant = ''
                                cur_node = Node(cur_title, parent=parent, drugs=list(), brands=list(),
                                                regimen=grandparent, variant=variant, regimen_type=g_grandparent)
                            else:
                                cur_node = Node(cur_title, parent=last_nodes[parent_level], data=list(),
                                                drugs=list(), brands=list(), regimen='', variant='', regimen_type='')
                        else:
                            cur_node = Node(cur_title, data=list(), drugs=list(), brands=list(), regimen='', variant='',
                                            regimen_type='')

                    cur_level = n.level
                    last_nodes[cur_level] = cur_node
                    nodes.append(cur_node)

                    if is_treatment:
                        treatment_nodes.append(cur_node)

                    # print(cur_title, cur_level)
                else:
                    if cur_level > 0:
                        text = pretty_text(n)
                        if len(text) > 0:
                            if is_treatment:
                                if isinstance(n, Wikilink):
                                    spl = text.split('(')
                                    drug = spl[0].strip()
                                    cur_node.drugs.append(drug)
                                    if len(spl) == 1:
                                        cur_node.brands.append(drug)
                                    else:
                                        cur_node.brands.append(spl[1].split(')')[0].strip())
                                else:
                                    # cur_node.instructions.append(text)
                                    pass
                            else:
                                if len(cur_node.data) > 0:
                                    cur_node.data[-1] = (cur_node.data[-1] + ' ' + text).strip()
                                else:
                                    cur_node.data.append(text)
                        else:
                            if is_treatment:
                                pass
                            elif len(cur_node.data) > 0:
                                # don't just keep adding empty ones
                                if cur_node.data[-1] != '':
                                    cur_node.data.append('')
                            else:
                                cur_node.data.append('')

        treatment_map = dict()
        for cn in treatment_nodes:
            # print('--------------------------')
            # print(RenderTree(cn))
            try:
                if cn.regimen not in treatment_map:
                    if len(cn.drugs) == 0:
                        continue
                    treatment_map[cn.regimen] = {
                        'drugs': cn.drugs,
                        'brands': cn.brands,
                        'regimen': cn.regimen,
                        'regimen_type': cn.regimen_type,
                        'cancer_type': oncology_class
                    }
            except Exception as e:
                print(e)

        if len(treatment_map.items()) > 0:
            generate_nlpql(oncology_class, treatment_map)
        else:
            print('no treatment for ', oncology_class)
        # json_string = json.dumps(treatment_map, indent=4)
        # print(json_string)
