import requests
import sys
from os import listdir
from os.path import isfile, join
import time

max_workers = 4
max_jobs = 100
cur_job = 409
viewed_jobs = list()

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
    filepath = '{}{}'.format(nlpql_path, filename)
    print('opening file ', filepath)
    with open(filepath, "r") as file:
        nlpql = file.read()
        sleepy_time = 60

        res = requests.post(nlpql_url, data=nlpql, headers={'content-type': 'text/plain'})
        if res.ok:
            print("Running job {} and then sleeping for {} seconds".format(i, sleepy_time))
            time.sleep(sleepy_time)
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


def cleanup_empty_jobs():
    # 5000/phenotype_jobs/ALL
    print('cleanup empty jobs...')
    res = requests.get("http://{}:5000/phenotype_jobs/COMPLETED".format(ip))
    if res.status_code == 200:
        json_res = res.json()
        for j in json_res:
            nlp_job_id = j['nlp_job_id']
            if nlp_job_id in viewed_jobs:
                continue

            if not has_data(nlp_job_id):
                viewed_jobs.append(nlp_job_id)
                cleanup(nlp_job_id)


def job_runner(i, fname):
    print('Attempting job %d' % i)

    if get_active_workers() < max_workers:
        run_nlpql(i, filename=fname)
        cleanup_empty_jobs()
    else:
        while get_active_workers() >= max_workers:
            cleanup_empty_jobs()
            print('At max workers for job %d sleeping for 30 secs...' % i)
            time.sleep(30)
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
        startid = 1711
        for n in range(startid, startid + 100):
            cleanup(n)
            # patient_count = has_data(n)
            # if patient_count == 0:
            #     cleanup(n)
            # else:
            #     print("job {} has {} patients".format(n, patient_count))

