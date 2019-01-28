import requests
import sys
from os import listdir
from os.path import isfile, join
import time

max_workers = 4
max_jobs = 100
cur_job = 0

ip = '18.220.133.76'
# ip = 'localhost'

url = 'http://' + ip + ':5000/'
nlpql_url = url + 'nlpql'
delete_url = url + 'delete_job/'
nlpql_path = './regimen_nlpql/'


def get_active_workers():
    res = requests.get("http://" + ip + ":8082/api/task_list?data={%22status%22:%22RUNNING%22}")
    if res.status_code == 200:
        json_res = res.json()
        keys = (json_res['response'].keys())
        return len(keys)

    return 0


def run_nlpql(i, filename='query'):
    with open('{}{}'.format(nlpql_path, filename), "r") as file:
        nlpql = file.read()

        res = requests.post(nlpql_url, data=nlpql, headers={'content-type': 'text/plain'})
        if res.ok:
            print("Running job %d" % i)
            time.sleep(30)
        else:
            print('Failed to run job %d' % i)
            sys.exit(1)


def cleanup(job_id):
    res = requests.get(delete_url + str(job_id), data={})
    if res.ok:
        print('successfully deleted job ' + str(job_id))
    else:
        print('delete the job ' + str(job_id))


def has_data(job_id):
    # http://18.220.133.76:5000/phenotype_subjects/1397/true
    res = requests.get("http://{}:5000/phenotype_subjects/{}/true".format(ip, job_id))
    if res.status_code == 200:
        json_res = res.json()
        return len(json_res)
    return 0


def job_runner(i, fname):
    print('Attempting job %d' % i)
    if get_active_workers() < max_workers:
        run_nlpql(i, filename=fname)
        time.sleep(60)
    else:
        while get_active_workers() >= max_workers:
            print('At max workers for job %d sleeping for 60 secs...' % i)
            time.sleep(60)
        run_nlpql(i, filename=fname)


if __name__ == "__main__":

    run_jobs = True
    if run_jobs:
        files = sorted([f for f in listdir(nlpql_path) if isfile(join(nlpql_path, f))])
        n = 0
        for f in files:
            if n >= cur_job:
                job_runner(n, f)
            n += 1
    else:
        startid = 0
        for n in range(startid, startid + 2000):
            patient_count = has_data(n)
            if patient_count == 0:
                cleanup(n)
            else:
                print("job {} has {} patients".format(n, patient_count))

