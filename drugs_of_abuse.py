import csv
import json


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    # pdf2txt.py -p 15,16,17,18,19,20,21,22,23,24,25,26,27,28,29 -o ~/repos/Utilities/drugs/drugs_of_abuse.txt ~/repos/Utilities/drugs/drug_of_abuse.pdf

    drug_map = dict()
    drugs = list()
    schedule = ""
    start_drugs = False
    start_narcotic = False
    start_dea = False
    start_others = False
    max_other = 0

    with open('./drugs/drugs_of_abuse.txt', 'r') as file_name:
        lines = file_name.readlines()
        i = 0
        for l in lines:
            val = l.strip()
            if val == '':
                continue
            if val.startswith('DRUGS OF ABUSE'):
                continue
            if val.startswith('SCHEDULE'):
                if schedule != '':
                    if schedule in drug_map:
                        drug_map[schedule].extend(drugs)
                    else:
                        drug_map[schedule] = drugs
                schedule = val
                start_narcotic = False
                start_drugs = False
                start_dea = False
                start_others = False
                drugs = list()
                i = -1
            if schedule == '':
                continue
            if val.startswith("OTHER NAMES") or start_others:
                drugs.append({})
                start_drugs = True
                start_others = False
                i += 1

                if val.startswith("OTHER NAMES"):
                    continue
            elif is_int(val) and start_drugs:
                start_drugs = False
                start_dea = True
            elif (val == "Y" or val == "N") and start_dea:
                start_narcotic = True
                start_dea = False
            elif start_narcotic and val != "Y" and val != "N":
                start_others = True
                start_narcotic = False

            if start_drugs or start_narcotic or start_others or start_dea:
                value = drugs[i]
                if start_drugs:
                    value['drug'] = val
                    drugs.append({})
                if start_dea:
                    value['dea'] = val
                if start_narcotic:
                    value['narcotic'] = val
                if start_others:
                    if 'NA' == val:
                        value['other_drugs'] = list()
                    else:
                        others = val.split(', ')
                        others = [x.strip() for x in others]
                        value['other_drugs'] = others
                        if len(others) > max_other:
                            max_other = len(others)

                drugs[i] = value

        if schedule in drug_map:
            drug_map[schedule].extend(drugs)
        else:
            drug_map[schedule] = drugs

    with open('./drugs/drugs.csv', mode='w') as c:
        writer = csv.writer(c, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(
            ['schedule', 'name', 'dea_number', 'narcotic', 'other_1', 'other_2', 'other_3', 'other_4', 'other_5',
             'other_6'])

        for s in drug_map.keys():
            drugs = drug_map[s]
            for d in drugs:
                row = list()
                if 'drug' not in d:
                    continue
                row.append(s)
                row.append(d['drug'])
                row.append(d['dea'])
                row.append(d['narcotic'])
                others = d['other_drugs']
                for o in range(0, 6):
                    if o < len(others):
                        row.append(others[o])
                    else:
                        row.append('')
                writer.writerow(row)

    unique_drugs = dict()
    for s in drug_map.keys():
        unique_drugs[s] = set()
        drugs = drug_map[s]
        for d in drugs:
            if 'drug' not in d:
                continue
            unique_drugs[s].add(d['drug'])
            others = d['other_drugs']
            for o in others:
                unique_drugs[s].add(o)

    with open('./drugs/unique_drugs.csv', mode='w') as c:
        writer = csv.writer(c, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        writer.writerow(
            ['schedule', 'name'])

        for s in drug_map.keys():
            drugs = unique_drugs[s]
            for d in drugs:
                row = list()
                row.append(s)
                row.append(d)
                writer.writerow(row)

    with open('./drugs/drugs.json', 'w') as f:
        f.write(json.dumps(drug_map, indent=4))
