from mwparserfromhell import parse
from mwparserfromhell.nodes import *
from mwparserfromhell.nodes.external_link import ExternalLink
from mwparserfromhell.nodes.wikilink import Wikilink
from mwparserfromhell.nodes.comment import Comment
from anytree import Node, RenderTree
from pathlib import Path
from urllib.parse import unquote_plus
import json

treatment_names = ['Chemoradiotherapy', 'Supportive medications', 'Chemotherapy', 'Immunosuppressive therapy',
                   'CNS prophylaxis', 'Chemotherapy, part 1', 'Chemotherapy, part 2', 'Primary therapy',
                   'Immunotherapy', 'Anticoagulation', 'Cellular therapy', 'Therapy', 'Anticoagulation']
supportive_meds = ['Supportive medications']
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

// Regimen names
{}

// Results
{}

// Comments
/***
{}
***/
 
'''
keep_characters = ('-', '_')


def title_text(parent):
    if not parent.title:
        return ''
    title = ''
    for t1 in parent.title.nodes:
        title += (pretty_text(t1) + ' ')
    return title.replace('#top ', '').strip()


def contents_text(parent):
    if not parent.contents:
        return ''
    title = ''
    for t1 in parent.contents.nodes:
        title += (pretty_text(t1) + ' ')
    return title.replace('#top ', '').strip()


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

    return txt.replace('#top ', '').strip()


def normalize_drug(d):
    return ' '.join(d.split('_')).lower()


def generate_medications(brands, drugs):
    define_str = ''
    keys = []

    n = 0
    single = len(brands) == 1
    if single:
        final_str = 'final'
    else:
        final_str = ''
    for b in brands:
        main_name = safe_name(drugs[n], no_punc=True)
        drug_b = normalize_drug(b)
        drug_n = normalize_drug(drugs[n])
        if drug_b != drug_n:
            terms = '"{}", "{}"'.format(drug_b, drug_n)
        else:
            terms = '"{}"'.format(drug_n)
        nlpql = '''
termset TreatmentTerms%d:[
    %s
];

define %s %sTreatment:
    Clarity.ProviderAssertion({
        termset:[TreatmentTerms%d],
        documentset:[Docs]
}); 

        ''' % (n, terms, final_str, main_name, n)
        keys.append('{}Treatment'.format(main_name))
        n += 1
        define_str += nlpql

    return define_str, keys


def generate_regimens(main_reg_name, regimens):

    if len(regimens) > 0:
        main_name = safe_name(main_reg_name, no_punc=True)
        regimen_str = '"' + '", "'.join(regimens) + '"'
        nlpql = '''
termset RegimenTerms:[
    %s
];

define final %sRegimen:
  Clarity.ProviderAssertion({
    termset:[RegimenTerms],
    documentset:[Docs]
   }); 
''' % (regimen_str, main_name)

        return nlpql, '%sRegimen' % main_name
    return '', ''


def generate_results(regimen_name, med_keys, regimen_key):
    med_clause = " AND ".join(med_keys)
    if len(med_keys) == 1:
        return ''
    else:
        return '''
        
define final %sTreatments:
    where %s;
          
        
        
        ''' % (regimen_name, med_clause)


def safe_name(name, no_punc=False):
    if no_punc:
        txt = "".join(c for c in unquote_plus(name.replace(" ", '_')).replace('/wiki/', '') if c.isalnum()).rstrip()
    else:
        txt = "".join(c for c in unquote_plus(name.replace(" ", '_')).replace('/wiki/', '') if c.isalnum() or c in
                               keep_characters).rstrip()
    txt = txt.replace('__', '_')
    return txt


def generate_regiment_nlpql(treatments):
    # 'drugs': cn.drugs,
    # 'brands': cn.brands,
    # 'regimen': cn.regimen,
    # 'regimen_type': cn.regimen_type,
    # 'cancers': oncology_class
    i = 0
    for k in treatments.keys():
        obj = treatments[k]
        comment_str = ''
        regimen = k
        nlpql_name = 'Regimen for {}'.format(regimen)
        nlpql_name = " ".join(nlpql_name.replace('"', "'").split("_"))
        med_define_str, med_keys = generate_medications(obj['brands'], obj['drugs'])
        reg_define_str, reg_key = generate_regimens(regimen, obj['regimen_names'])
        cancers = list(set(obj['cancers']))
        cancer_str = ", ".join(cancers)

        if len(obj['supportive_drugs']) > 0:
            supportive_meds_str = ", ".join(obj['supportive_drugs'])
            support_drugs_comment = "Supportive Medications: {}".format(supportive_meds_str)
        else:
            support_drugs_comment = ""
        comment_str += ("""
Known regimen for: {}

{}

""").format(cancer_str, support_drugs_comment)
        filename = safe_name(regimen)
        regimen_final_name= safe_name(regimen, no_punc=True)
        result_str = generate_results(regimen_final_name, med_keys, reg_key)
        print('nlpql for ', nlpql_name)

        if len(filename) > 0:
            with open('./regimen_nlpql/{}.nlpql'.format(filename), 'w') as file:
                file.write(nlpql_template.format(nlpql_name, med_define_str, reg_define_str, result_str, comment_str))
                i += 1


if __name__ == "__main__":
    treatment_map = dict()
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
            oncology_class = (f.name.split('/')[-1].split('.')[0]).replace('ö', 'o')
            # print(oncology_class)
            cur_level = 0
            cur_title = None
            cur_node = None
            for n in wikicode.nodes:
                if isinstance(n, Heading):
                    cur_title = title_text(n)
                    is_treatment = cur_title in treatment_names and n.level >= 3
                    is_supportive_med = cur_title in supportive_meds and n.level >= 3

                    if cur_level == 0:
                        if is_treatment:
                            cur_node = Node(cur_title, drugs=list(), brands=list(), instructions=list(),
                                            regimen='', variant='', regimen_type='', regimen_names=list(),
                                            supportive_brands=list(), supportive_drugs=list(), data=list())
                        else:
                            cur_node = Node(cur_title, data=list(), drugs=list(), brands=list(), instructions=list(),
                                            regimen='', variant='', regimen_type='', regimen_names=list(),
                                            supportive_brands=list(), supportive_drugs=list())

                    else:
                        parent_level = n.level - 1
                        if parent_level in last_nodes:
                            parent = last_nodes[parent_level]

                            if is_treatment:
                                if parent_level - 1 >= 0:
                                    grandparent_node = last_nodes[parent_level - 1]
                                    grandparent = grandparent_node.name
                                else:
                                    grandparent = ''
                                    grandparent_node = None
                                if parent_level - 2 >= 0:
                                    g_grandparent_node = last_nodes[parent_level-2]
                                    g_grandparent = g_grandparent_node.name
                                else:
                                    g_grandparent = ''
                                    g_grandparent_node = None
                                if parent.name != 'Regimen':
                                    variant = parent.name
                                else:
                                    variant = ''
                                regimen_names = list()
                                if len(grandparent) > 0:
                                    regimen_names.append(grandparent)
                                if grandparent_node and grandparent_node.data:
                                    for d in grandparent_node.data:
                                        if ':' in d:
                                            reg_name = d.split(':')
                                            if len(reg_name[0]) > 2:
                                                regimen_names.append(reg_name[0])
                                alternate_regimens = list()
                                for r in regimen_names:
                                    if 'monotherapy' in r.lower():
                                        continue
                                    if len(r) > 20:
                                        continue
                                    if len(r) < 10:
                                        alternate_regimens.append(safe_name(r, no_punc=True))

                                    if '&' in r:
                                        alternate_regimens.append(r.replace(' & ', ' and '))
                                        alternate_regimens.append(r.replace(' & ', '/'))
                                        alternate_regimens.append(r.replace(' & ', '+'))
                                        alternate_regimens.append(r.replace('&', ' and '))
                                        alternate_regimens.append(r.replace('&', '/'))
                                        alternate_regimens.append(r.replace('&', '+'))

                                    if len(r) > 10:
                                        continue
                                    if '-' in r:
                                        alternate_regimens.append(r.replace('-', ''))
                                        alternate_regimens.append(r.replace('-', '/'))
                                    if ' and ' in r:
                                        alternate_regimens.append(r.replace(' and ', '&'))
                                        alternate_regimens.append(r.replace(' and ', ' & '))
                                        alternate_regimens.append(r.replace(' and ', ' / '))
                                        alternate_regimens.append(r.replace(' and ', '/'))
                                    if '+' in r:
                                        alternate_regimens.append(r.replace('+', ' and '))
                                        alternate_regimens.append(r.replace('+', '&'))
                                        alternate_regimens.append(r.replace('+', ' & '))
                                        alternate_regimens.append(r.replace('+', ' / '))
                                        alternate_regimens.append(r.replace('+', '/'))
                                        alternate_regimens.append(r.replace('+', ''))
                                for ar in alternate_regimens:
                                    if len(ar) > 2:
                                        regimen_names.append(ar)
                                regimen_names = sorted(list(set(regimen_names)))
                                cur_node = Node(cur_title, parent=parent, drugs=list(), brands=list(),
                                                regimen=grandparent, variant=variant, regimen_type=g_grandparent,
                                                regimen_names=regimen_names,
                                                supportive_brands=list(), supportive_drugs=list(), data=list())
                            else:
                                cur_node = Node(cur_title, parent=last_nodes[parent_level], data=list(),
                                                drugs=list(), brands=list(), regimen='', variant='', regimen_type='',
                                                regimen_names=list(),
                                                supportive_brands=list(), supportive_drugs=list())
                        else:
                            cur_node = Node(cur_title, data=list(), drugs=list(), brands=list(), regimen='', variant='',
                                            regimen_type='', regimen_names=list(), supportive_brands=list(),
                                            supportive_drugs=list())

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
                            if is_treatment and not is_supportive_med:
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
                            if is_supportive_med:
                                if isinstance(n, Wikilink):
                                    if len(treatment_nodes) > 0:
                                        spl = text.split('(')
                                        drug = spl[0].strip()
                                        treatment_nodes[-1].supportive_drugs.append(drug)
                                        if len(spl) == 1:
                                            treatment_nodes[-1].supportive_brands.append(drug)
                                        else:
                                            treatment_nodes[-1].supportive_brands.append(spl[1].split(')')[0].strip())
                            else:
                                if len(cur_node.data) > 0:
                                    cur_node.data[-1] = (cur_node.data[-1] + ' ' + text).strip()
                                else:
                                    cur_node.data.append(text)
                        else:
                            if is_treatment or is_supportive_med:
                                pass
                            elif cur_node.data and len(cur_node.data) > 0:
                                # don't just keep adding empty ones
                                if cur_node.data[-1] != '':
                                    cur_node.data.append('')
                            else:
                                cur_node.data.append('')

        print("found regimens for ", oncology_class)
        for cn in treatment_nodes:
            # print('--------------------------')
            # print(RenderTree(cn))
            try:
                if cn.regimen not in treatment_map:
                    if len(cn.drugs) == 0 or len(cn.regimen_names) == 0:
                        continue
                    doc = {
                        'drugs': cn.drugs,
                        'brands': cn.brands,
                        'regimen': cn.regimen,
                        'regimen_type': cn.regimen_type,
                        'cancers': list(),
                        'regimen_names': cn.regimen_names,
                        'supportive_drugs': cn.supportive_drugs,
                        'supportive_brands': cn.supportive_brands

                    }
                    doc['cancers'].append(oncology_class)
                    treatment_map[cn.regimen] = doc
                else:
                    treatment_map[cn.regimen]['cancers'].append(oncology_class)
            except Exception as e:
                print(e)

    if len(treatment_map.items()) > 0:
        generate_regiment_nlpql(treatment_map)
        with open('./tree.json', 'w') as json_file:
            json_file.write(json.dumps(treatment_map, indent=4, sort_keys=True))
