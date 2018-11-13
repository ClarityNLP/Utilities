import os
from glob import iglob
import zipfile
import string
import xmltodict
from collections import OrderedDict
from datetime import datetime
import json
import requests

solr_url = "http://localhost:8983/solr/sample"

url = solr_url + '/update?commit=true'
headers = {
    'Content-type': 'application/json',
}
remove = string.punctuation
remove = remove.replace("_", "")
pattern = r"[{}]".format(remove)

valid_authors = ['document.author.assignedEntity.representedOrganization.name']

valid_titles = ['document.title.#text', 'document.title.content', 'document.title.content.#text',
                'document.code.@displayName', 'document.title.content', 'document.code.@displayName']

valid_keys = ['text', 'paragraph', '#text', 'text.paragraph', 'name', '@displayName', 'originalText', '@value',
              '@referencedObject', 'value', 'content', 'section', 'renderMultiMedia', 'component', 'numerator',
              'text.paragraph.content.#text', 'text.paragraph.#text', 'text.paragraph.content', 'reference',
              'text.list.item', 'text.paragraph.content.content.#text', 'component.section.text.paragraph',
              'linkHtml', 'excerpt.highlight.text.paragraph.#text', 'text.table.tbody.tr',
              'excerpt.highlight.text.paragraph', 'caption', 'component.section.text.list.item',
              'component.section.text.paragraph.content', 'text.content', 'component.observationMedia.text',
              'text.#text', 'value', 'text.table.tbody.tr.td.paragraph.#text', '@value', 'ingredient',
              ]
title_keys = [ 'title.content.#text', 'title', 'title.#text', 'title.text', 'title.content', 'title.content.#text']
secondary_keys = ['approval', 'author', 'code', '@code', 'observationMedia', 'list', 'item',
                  'component.section.component', 'routeCode', 'table', 'tbody', 'td', 'tr',
                  'subject.manufacturedProduct.manufacturedMedicine.asEntityWithGeneric.genericMedicine.name',
                  'substanceAdministration', 'subject.manufacturedProduct.manufacturedProduct.formCode.@displayName',
                  'marketingAct', 'characteristic', '@displayName', 'substanceAdministration', 'approval',
                  'territorialAuthority', 'territory', 'code.@code', '@name', 'asContent']
exclude_codes = ['@styleCode', '@ID', 'br', '@valign', '@align', '@xsi:type', '@colspan', '@nullFlavor', '@href', 'sup',
                 'sub']


def get_text(elem, txt=''):
    if not elem:
        pass
    elif isinstance(elem, list):
        for e in elem:
            new_line = get_text(e)
            if len(txt) > 0 and len(new_line) > 0 and not new_line.endswith('.') and not new_line.endswith(','):
                txt += ', '
            txt += new_line
    elif isinstance(elem, str):
        if len(txt) > 0 and len(elem) > 0:
            txt += ' \n'
        txt += elem
    elif isinstance(elem, OrderedDict):

        matched_keys = list()
        for k in valid_keys:
            if k in elem:
                matched_keys.append(k)
        if len(matched_keys) == 0:
            for k in secondary_keys:
                if k in elem:
                    matched_keys.append(k)
        if len(matched_keys) == 0:
            for k in title_keys:
                if k in elem:
                    matched_keys.append(k)
        if len(matched_keys) > 0:
            for lookup_key in matched_keys:
                val = elem[lookup_key]
                if not val:
                    continue
                if isinstance(val, str):
                    if len(txt) > 0 and len(val) > 0:
                        txt += ' \n'
                    txt += val
                    if lookup_key in title_keys:
                        txt += ': '
                    break
                else:
                    new_val = get_text(val)
                    if len(txt) > 0 and len(new_val) > 0:
                        txt += ' \n'
                    txt += new_val
                    if lookup_key in title_keys:
                        txt += ': '
                    break

        e_count = 0
        key_length = len(elem.keys())
        for k in exclude_codes:
            if k in elem:
                e_count += 1
        excluded = (e_count == key_length)

        if len(txt) == 0 and not excluded:
            print(elem)

    txt = ' '.join(txt.split(' '))
    return txt.strip()


def flatten_dict(d, flatten_list=False):
    def items():
        for key, value in d.items():
            if isinstance(value, dict):

                for subkey, subvalue in flatten_dict(value).items():
                    yield key + "." + subkey, subvalue
            elif isinstance(value, list) and flatten_list:
                n = 0
                for v in list(value):
                    if v:
                        print(v)
                        n += 1
            else:
                yield key, value

    return OrderedDict(items())


def load(path='', report_type="FDA Drug Label", default_name='Human Prescription Drug Label'):
    rootdir = path + '/**/*'
    file_list = [f for f in iglob(rootdir, recursive=True) if os.path.isfile(f)]
    for f in file_list:
        if f.endswith('zip'):
            print('unzipping')
            name = f.split('.')[-2].split('/')[-1]
            with zipfile.ZipFile(f, "r") as zip_ref:
                zip_ref.extractall(path + '/' + name)
                os.remove(f)
    file_list = [f for f in iglob(rootdir, recursive=True) if os.path.isfile(f)]
    file_list = sorted(file_list)
    results = list()
    uploaded = 0
    for f in file_list:
        if f.endswith('xml'):
            try:
                print('parsing ' + f)
                xml_data = open(f)
                lines = xml_data.readlines()
                txt = ''
                obj = dict()
                try:
                    for l in lines:
                        if not l.startswith('<?xml'):
                            txt = txt + l + '\n'

                    if not txt.startswith('<document'):
                        txt = '<document>' + txt
                    xml_content = xmltodict.parse(txt)
                    flattened_dict = flatten_dict(xml_content)
                except:
                    try:
                        xml_content = xmltodict.parse(xml_data.read())
                        flattened_dict = flatten_dict(xml_content)
                    except:
                        print('cant parse')
                        continue

                name = default_name
                for v in valid_titles:
                    if v in flattened_dict:
                        txt = get_text(flattened_dict[v])
                        if not txt.lower().startswith("these highlights"):
                            name = txt
                            name = ' '.join(name.split())
                            break

                if name == default_name:
                    print('no name')

                effective_time = flattened_dict['document.effectiveTime.@value']
                id = flattened_dict['document.id.@root']
                author = 'Unknown'
                for a in valid_authors:
                    if a in flattened_dict:
                        author = get_text(flattened_dict[a])
                        break
                version = flattened_dict['document.versionNumber.@value']

                datetime_object = datetime.strptime(effective_time, '%Y%m%d')
                obj['report_date'] = str(datetime_object.isoformat())
                obj['version_attr'] = version
                obj['id'] = id
                obj['report_id'] = id
                obj['author_attr'] = author
                obj['subject'] = name
                obj['report_type'] = report_type
                obj['source'] = "FDA Drug Labels"
                components = (flattened_dict['document.component.structuredBody.component'])
                label_text = ''
                for c in components:
                    section = flatten_dict(c['section'])
                    # s_id = section['id.@root']
                    # s_time = section['effectiveTime.@value']
                    if 'subject' in section:
                        subjects = section['subject']
                        for s in subjects:
                            product = s['manufacturedProduct']
                            product_flat = flatten_dict(product, flatten_list=False)
                            # print(product_flat.keys())
                            for key in product_flat.keys():
                                new_key = key.replace('@', '').replace('.', '_').replace('manufacturedProduct', '')\
                                    .replace('#', '')
                                new_key += '_attr'
                                if new_key.startswith("_"):
                                    new_key = new_key[1:]
                                new_key = new_key.lower()
                                val = product_flat[key]
                                if not isinstance(val, str):
                                    if isinstance(val, list):
                                        for v in val:
                                            if isinstance(v, OrderedDict):
                                                for od in v.keys():
                                                    od_key = new_key.replace('_attr', '') + '_' + od + '_attr'
                                                    od_text = get_text(v[od])
                                                    if od_key in obj:
                                                        txt = obj[od_key] + ', ' + od_text
                                                    else:
                                                        txt = od_text
                                                    obj[od_key] = txt
                                            else:
                                                print(v)
                                    else:
                                        val = get_text(val)
                                        obj[new_key] = val
                                else:
                                    obj[new_key] = val
                    elif 'title.#text' in section:
                        title = section['title.#text']
                        if not title.endswith(":"):
                            title += ':'
                        if 'text.paragraph' in section:
                            paragraph = section['text.paragraph']
                            p_text = get_text(paragraph)
                        elif 'component' in section:
                            p_text = get_text(section['component'])
                        elif 'component.section.text.paragraph' in section:
                            p_text = get_text(section['component.section.text.paragraph'])
                        else:
                            p_text = get_text(section)

                        p_text = ' '.join(p_text.split())
                        label_text += title + ' \n'
                        label_text += p_text + ' \n\n'
                    elif 'code.@displayName' in section:
                        title = section['code.@displayName']
                        if not title.endswith(":"):
                            title += ':'
                        if 'text.paragraph' in section:
                            paragraph = section['text.paragraph']
                            p_text = get_text(paragraph)
                        else:
                            p_text = get_text(section)
                        p_text = ' '.join(p_text.split())
                        label_text += title + ' \n'
                        label_text += p_text + ' \n\n'
                    else:
                        # print('unknown')
                        # print(section.keys())
                        pass
                # label_text = ' '.join(label_text.split())
                obj['report_text'] = label_text
                print('parsed %s' % obj['report_id'])
                results.append(obj)
                xml_data.close()

                if len(results) % 10 == 0:
                    print('uploading....')
                    json_data = json.dumps(results)
                    response = requests.post(url, headers=headers, data=json_data)

                    if response.status_code != 200:
                        print(response.reason)
                    else:
                        uploaded += 10
                        print('\n\n\nuploaded %d docs!\n\n\n' % uploaded)
                    results = list()
            except Exception as ex:
                print(ex)

    json_data = json.dumps(results)
    response = requests.post(url, headers=headers, data=json_data)
    if response.status_code != 200:
        print(response.reason)
    else:
        uploaded += len(results)
        print('\n\n\nuploaded %d docs!\n\n\n' % uploaded)
    print('DONE!!!')


if __name__ == "__main__":
    load('/Downloads/prescription', report_type='Human Prescription Labels',
         default_name='Human Prescription Drug Label')
