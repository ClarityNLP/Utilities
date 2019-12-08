import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import time
import csv

API_URL = 'https://openi.nlm.nih.gov/api'
IMAGE_URL = 'https://openi.wip.nlm.nih.gov/{}'
RESULT_URL = 'https://openi.wip.nlm.nih.gov/detailedresult?img={}'
# imgs/512/1/1/CXR1_1_IM-0001-3001.png?keywords=normal


def search_images(curr_min, curr_max, collection='cxr'):
    _image_json = requests.get('https://openi.nlm.nih.gov/api/search?coll={}&m={}&n={}'.format(collection, curr_min,
                                                                                               curr_max))
    _list = _image_json.json().get('list', list())
    return _list


def get_abstract_note(_driver, result_url, sleep=0.5):
    _driver.get(result_url)
    _driver.execute_script("window.scrollTo(0, 100)")
    time.sleep(sleep)
    note = ''
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    text_divs = soup.findAll("div", {"class": "collapsible"})
    for t in text_divs:
        _text = t.text.strip()
        if _text.startswith('Abstract'):
            for ch in t.children:
                if hasattr(ch, 'children'):
                    for ch_1 in ch.children:
                        if ch_1.name == 'p':
                            for ch_2 in ch_1.children:
                                if hasattr(ch_2, 'text'):
                                    note += ch_2.text.strip() + ' '
                                else:
                                    note += str(ch_2) + '\n'
                            note += '\n'
            break
    return note.replace('Abstract', '', 1).strip()


def parse_nlm(l, _driver, default_type='Chest X-ray'):
    csv_row = dict()

    image_url = IMAGE_URL.format(l.get('imgLarge'))
    image_key = image_url.split('/')[-1].split('.')[0]
    result_url = RESULT_URL.format(image_key)
    print(result_url)
    note = get_abstract_note(_driver, result_url)
    if note == '':
        note = get_abstract_note(_driver, result_url, sleep=10)
        if note == '':
            print('no text found')

    image_info = l.get('image', {
        'caption': 'CXR'
    })
    caption = image_info.get('caption', default_type)
    if caption.lower().startswith('not available'):
        caption = ''
    csv_row['subject'] = 'cxr_subject_{}'.format(l.get('pmcid'), str(n))
    csv_row['report_id'] = image_key
    csv_row['id'] = image_key
    csv_row['source'] = 'NLM_image_collection'
    csv_row['title_attr'] = l.get('title', '')
    doc_source = l.get('docSource', default_type)
    report_text = (note + '\n\n' + caption).strip()
    report_text = ''.join([i if ord(i) < 128 else ' ' for i in report_text])
    csv_row['report_text'] = report_text
    csv_row['report_type'] = doc_source
    csv_row['description_attr'] = caption
    csv_row['image_url_attr'] = image_url
    csv_row['author_attr'] = l.get('authors', '')
    csv_row['resource_url_attr'] = result_url
    csv_row['problems_attr'] = l.get('Problems', '')

    dt = l.get('journal_date', {
        'day': '01',
        'month': '01',
        'year': '2019'
    })
    yr = dt.get('year', '2019')
    mo = dt.get('month', '01')
    da = dt.get('day', '01')

    if yr.strip() == '':
        yr = '2019'
    if mo.strip() == '':
        mo = '01'
    if len(mo) == 1:
        mo = "0{}".format(mo)
    if da.strip() == '':
        da = '01'
    if len(da) == 1:
        da = "0{}".format(da)
    csv_row['report_date'] = "{}-{}-{}T00:00:00Z".format(yr, mo, da)
    print(csv_row['report_date'])
    return csv_row


def get_total(collection='cxr'):
    url = 'https://openi.nlm.nih.gov/api/search?coll={}&m=1'.format(collection)
    res = requests.get(url)
    _json = res.json()
    _total = _json.get('total', 0)
    return _total


if __name__ == "__main__":
    driver = webdriver.Chrome()
    driver.set_page_load_timeout(30)

    colls = ['mpx', 'cxr']
    for c in colls:
        total = get_total(collection=c)
        n = 0
        rows_added = 0
        print(total)
        f_name = '/Users/charityhilton/Downloads/nlm_{}_images.csv'.format(c)
        print(f_name)
        with open(f_name, 'w') as csvfile:
            fieldnames = ['report_id', 'id', 'subject', 'report_type', 'report_date', 'source', 'author_attr',
                          'resource_url_attr', 'description_attr', 'problems_attr', 'image_url_attr', 'title_attr',
                          'report_text']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            start = 0
            for i in range(start, total, 10):
                images = search_images(i+1, i+9, collection=c)

                for l in images:
                    csv_row = parse_nlm(l, driver)

                    if csv_row:
                        txt = csv_row.get('report_text', '')
                        if len(txt) > 0:
                            writer.writerow(csv_row)
                            rows_added += 1
                        else:
                            print('row not written')
                        if n % 5 == 0:
                            print('rows added {}'.format(rows_added))
                            csvfile.flush()
                        n += 1
