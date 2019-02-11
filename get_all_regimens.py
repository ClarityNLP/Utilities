import json
import csv

if __name__ == "__main__":
    with open('./cancer/regimen_tree.json', mode='r') as r:
        txt = r.read()
        regimens = json.loads(txt)

        with open('./cancer/regimen_names.csv', mode='w') as c:
            writer = csv.writer(c, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            writer.writerow(
                ['regimen', 'alternate_name', 'regimen_type', 'cancers'])

            for k in regimens.keys():
                obj = regimens[k]
                cancers = ",".join(list(set(obj['cancers'])))
                regimen_type = obj['regimen_type']
                regimen = obj['regimen']
                regimen_names = list(set(obj['regimen_names']))
                for n in regimen_names:
                    writer.writerow([regimen, n, regimen_type, cancers])


