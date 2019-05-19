import json
import os
import tempfile
import zipfile

import pandas
import requests
from flask import *
from flask_cors import CORS
from werkzeug.utils import secure_filename

from cibmtr_scraper import parse_questions_from_feature_csv

UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = ['csv']

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

sample_patients = [
    "38587",
    "23907"
]

headers = {
    'Content-type': 'application/json',
}

template = '''
    <!doctype html>
    <html lang="en">
    <head>
    <style>
    /* Sticky footer styles
-------------------------------------------------- */
html {
  position: relative;
  min-height: 100%%;
}
body {
  margin-bottom: 60px; /* Margin bottom by footer height */
}




.footer {
  position: absolute;
  bottom: 0;
  width: 100%%;
  height: 60px; /* Set the fixed height of the footer here */
  line-height: 60px; /* Vertically center the text there */
  background-color: #f5f5f5;
}


/* Custom page CSS
-------------------------------------------------- */
/* Not required for template or sticky footer method. */

.container {
  width: auto;
  max-width: 680px;
  padding: 0 15px;
}
</style>    
        <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <meta name="description" content="">
    <meta name="author" content="">
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css" integrity="sha384-MCw98/SFnGE8fJT3GXwEOngsV7Zt27NXFoaoApmYm81iuXoPkFOJwJ8ERdknLPMO" crossorigin="anonymous">
<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js" integrity="sha384-ChfqqxuZUCnJSK3+MXmPNIyE6ZbWh2IMqE241rYiqJxyMiZ6OW/JmZQ5stwEULTy" crossorigin="anonymous"></script>
    <title>ClarityNLP Utilities</title>
    </head>
    <body>
    <main role="main" class="container">
    <br>
    <h1>%s</h1>
    %s
    </main>
       <footer class="footer">
      <div class="container">
        <span class="text-muted">
        <a href="/">Home</a> |
        <a href="https://github.com/ClarityNLP">ClarityNLP Source</a> | 
        <a href="https://claritynlp.readthedocs.io/en/latest/">ClarityNLP Docs</a>
        </span>
      </div>
    </footer>
    </body>
    </html>
    '''


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET'])
def home():
    body = '''
    <p>
    <a href="/cibmtr_parse">CIBMTR CSV Parser</a><br>
    <a href="/register_nlpql">Register Test NLPQL</a><br>
    <a href="/test_mimic_nlpql">Test with MIMIC-III</a><br>
    <a href="/test_text_nlpql">Test with Plain Text</a><br>
    </p>
    
    '''
    return template % ("ClarityNLP Utilities", body)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/cibmtr_parse', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            in_file = os.path.join(UPLOAD_FOLDER, filename)
            file.save(in_file)
            new_dir = tempfile.mkdtemp(prefix='cibmtr_form_queries_')
            if not os.path.exists(new_dir):
                os.mkdir(new_dir)
            parse_questions_from_feature_csv(file_name=in_file, output_dir=new_dir)
            zipped_file = os.path.join(UPLOAD_FOLDER, 'cibmtr_form_queries.zip')
            zipf = zipfile.ZipFile(zipped_file, 'w', zipfile.ZIP_DEFLATED)
            zipdir(new_dir, zipf)
            zipf.close()

            return redirect(url_for('uploaded_file',
                                    filename='cibmtr_form_queries.zip'))
    form = '''
    <form method=post enctype=multipart/form-data>
      <p><input type=file name="file" class="btn btn-default">
         <input type=submit value="Upload CSV" class="btn btn-success">
    </form>
    '''
    return template % ("CIBMTR Feature CSV Parser", form)


def get_test_template(action='/test_text_nlpql', patient=False, error=''):
    template = '''
    <p>
    Unable to get NLPQL jobs. Please try again later.
    </p>
    '''
    success = False
    response = requests.get('https://nlp.hdap.gatech.edu/job/list/all')
    if response.status_code == 200:
        jobs = response.json()
        job_html = ''
        for j in jobs:
            job_html += ('<option value="{}">{}</option>'.format(j, j))
        if patient:
            inputs = '''
                <div class="form-group">
                    <label>Patient ID</label><br>
                    <input type="text" class="form-control"  name="patient" placeholder="{}" value={} />
                </div>
            '''.format(",".join(sample_patients), sample_patients[0])
        else:
            inputs = '''
                <div class="form-group">
                    <label>Text</label><br>
                    <textarea class="form-control"  name="text" rows="5"></textarea>
                </div>
            '''
        template = '''
            <div class="container">
            <h4 class="text-danger">{}</h4><br>
            <form action="{}" method="POST">
            
              <div class="form-group">
                <label>NLPQL</label><br>
                <select class="form-control" name="nlpql">
                    {}
                </select>
              </div>
            {}
            <br>
             <div class="form-group">
                <input type="submit" value="Test NLPQL" class="btn btn-success">
              </div>
            </form>
            </div>
        '''.format(error, action, job_html, inputs)
    return template


@app.route('/test_text_nlpql', methods=['GET', 'POST'])
def test_text_nlpql():
    form = get_test_template('/test_text_nlpql', patient=False)
    if request.method == 'POST':
        nlpql = request.form['nlpql']
        text = request.form['text'].strip()

        if len(nlpql) == 0 or len(text) == 0:
            error = "Please fill out all fields!"
            form = get_test_template('/test_text_nlpql', patient=False, error=error)
        else:
            data = {'reports': [text]}
            url = 'https://nlp.hdap.gatech.edu/job/{}'.format(nlpql)
            res = requests.post(url, data=json.dumps(data), headers=headers)
            if res.status_code != 200:
                form = get_test_template('/test_text_nlpql', patient=False, error="Unable to process request!"
                                                                                  " Reason: {}".format(res.reason))
            else:
                df = pandas.read_json(res.text)
                nm = nlpql.split('/')[-1]
                fl = os.path.join(UPLOAD_FOLDER, '{}.csv'.format(nm))
                df.drop(columns="report_text")
                df.to_csv(fl)

                return redirect(url_for('uploaded_file',
                                        filename='{}.csv'.format(nm)))

    return template % ("Test NLPQL", form)


@app.route('/test_mimic_nlpql', methods=['GET', 'POST'])
def test_mimic_nlpql():
    form = get_test_template('/test_mimic_nlpql', patient=True)
    if request.method == 'POST':
        nlpql = request.form['nlpql']
        patient = request.form['patient'].strip()

        if len(nlpql) == 0 or len(patient) == 0:
            error = "Please fill out all fields!"
            form = get_test_template('/test_mimic_nlpql', patient=True, error=error)
        else:
            data = dict()
            res = requests.get(
                'https://apps.hdap.gatech.edu/gt-fhir/fhir/DocumentReference/?patient={}'.format(patient))
            if res.status_code != 200:
                error = "Unable to contact FHIR server or find patient: {}".format(patient)
                form = get_test_template('/test_mimic_nlpql', patient=True, error=error)
                return template % ("Test NLPQL", form)
            res_data = res.json()
            reports = res_data['entry']
            if len(reports) == 0:
                error = "Patient {} is missing documents.".format(patient)
                form = get_test_template('/test_mimic_nlpql', patient=True, error=error)
                return template % ("Test NLPQL", form)
            data['reports'] = [r['resource'] for r in reports]
            data['patient_id'] = str(patient)
            data['fhir'] = {"serviceUrl": "https://apps.hdap.gatech.edu/gt-fhir/fhir", "auth": {"type": "none"}}

            url = 'https://nlp.hdap.gatech.edu/job/{}'.format(nlpql)
            res2 = requests.post(url, data=json.dumps(data), headers=headers)
            if res2.status_code != 200:
                form = get_test_template('/test_mimic_nlpql', patient=True, error="Unable to process request!"
                                                                                  " Reason: {}".format(res.reason))
            else:
                df = pandas.read_json(res2.text)
                nm = nlpql.split('/')[-1]
                fl = os.path.join(UPLOAD_FOLDER, '{}.csv'.format(nm))
                df = df[df.nlpql_feature != "null"]
                df = df[df.nlpql_feature.notnull()]
                df.drop(columns="report_text")
                df.to_csv(fl)

                return redirect(url_for('uploaded_file',
                                        filename='{}.csv'.format(nm)))

    return template % ("Test NLPQL", form)


@app.route('/register_nlpql', methods=['GET', 'POST'])
def register_nlpql():
    error = ''
    info = ''
    form_info = '''
    <form action="/register_nlpql" method="POST">
    <div class="container">
        <div class="row">
        <label>NLPQL:</label>
        <textarea class="form-control"  name="nlpql" rows="15">
        
// Phenotype library name
phenotype "Kidneys_toxicities" version "1";

// # Referenced libraries #
include ClarityCore version "1.0" called Clarity;

// Termsets

termset kidneys_toxicities_unstructured_terms: [
    "grade 4 renal toxicity", "grade iv renal toxicity", "grade 4 toxicity of the kidneys", "grade iv toxicity of the kidneys"
];



// Data Entities

define final kidneys_toxicities_unstructured:
    Clarity.ProviderAssertion({
      termset: [kidneys_toxicities_unstructured_terms]
    });
                    

        </textarea>
        </div>
        <br>
      <div class="row">
        <input type="submit" value="Register NLPQL" class="btn btn-success">
      </div>
    </div>
</form>
    '''
    if request.method == 'POST':
        nlpql = request.form['nlpql']

        if len(nlpql) == 0:
            error = "Please fill out all fields!"

        register_url = 'https://nlp.hdap.gatech.edu/job/register_nlpql'
        response = requests.post(register_url, data=nlpql)

        if response.status_code != 200:
            error = "Unable to register NLPQL job."
        res = response.json()
        msg = res['message']
        if 'Your job is callable via the endpoint' not in msg:
            error = msg
        else:
            info = '''
            <h4>Job registered successfully</h4><br>
            <span>{}</span>
            <div>
               <a href="/test_mimic_nlpql">Test with MIMIC-III</a><br>
               <a href="/test_text_nlpql">Test with Plain Text</a><br>
           </div>
            '''.format(msg)
            form_info = ''

        # document_url = 'https://apps.hdap.gatech.edu/gt-fhir/fhir/DocumentReference?patient={}&_pretty=true'.format(patient)
    form = '''
<h4 class="text-danger">%s</h4>
<p class="text-primary">%s</p>
<br>
%s
    ''' % (error, info, form_info)
    return template % ("Register Custom NLPQL", form)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
