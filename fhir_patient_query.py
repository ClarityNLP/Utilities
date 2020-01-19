#!/usr/bin/env python3
"""



OVERVIEW:



This is a command-line tool for building a FHIR query URL, submitting it to
a FHIR server, and returning patient_ids and timestamps from all resources
satisfying the query.

The supported resources are 'Procedure' and 'Observation', which must be
specified with the --resource_type argument.

The base URL of the FHIR server is specified with the --base_url argument.

Users can restrict the dates of the returned resources with the --start_date
and --end_date arguments. The date range is interpreted as closed on the left
side, i.e. [start_date, end_date), or start_date <= timestamp < end_date.

The supported date formats are:

    YYYY
    YYYY-MM
    YYYY-MM-DD

If these date params are not specified, all matching data is returned.

A comma-separated list of codes can be provided with the --code_list argument.
DO NOT insert a space after the commas, or the python command-line parser will
misinterpret the list of codes. This is what a proper list of codes looks like:

    1234567,2345678,22114453

A more extensive list of codes (including codes from different codesystems) can
be provided with the --code_file argument. The code_file is a CSV-formatted
array of codesystem URLs and codes.  An example using both LOINC and SNOMED
codes is as follows:


    codesystem,codelist
    http://loinc.org,26464-8,804-5,6690-2,49498-9
    http://snomed.info/sct,271737000,40172005


Extensive debugging info can be displayed with the --debug flag.

Version information is available with the --version argument.
Use the --help argument to display the command-line help.



OUTPUT:



The patient IDs and associated start/end timestamps from the returned resources
are written to a CSV file called 'out.csv', unless the --output_file argument
is used to specify the output filename.



EXAMPLES:

Here are some examples using a publicly-available FHIR server. The command-line
arguments have been listed on different lines for clarity. The --debug option
has also been used, so that the actual data returned will be sent to stdout.


1. Find all patients on this FHIR server who have had a colonoscopy procedure.

    python3 ./fhir_patient_query.py --base_url http://hapi.fhir.org/baseDstu2
                                    --resource_type Procedure
                                    --code_list 73761001
                                    --debug

        <results written to out.csv>

2. Find all patients on this FHIR server who have had a colonoscopy procedure
   during the first six months of 2015:

    python3 ./fhir_patient_query.py --base_url http://hapi.fhir.org/baseDstu2
                                    --resource_type Procedure
                                    --code_list 73761001
                                    --start_date 2015-01-01
                                    --end_date   2015-07-01
                                    --debug
        
        <results written to out.csv>

3. Find all patients on this FHIR server with WBC observations prior to
   January 2017:

    
    python3 ./fhir_patient_query.py --base_url http://hapi.fhir.org/baseDstu2
                                    --resource_type Observation
                                    --code_list 26464-8,804-5,6690-2,49498-9
                                    --end_date 2017-01-01
                                    --debug
 
        <results written to out.csv>

4.  Find all patients on this FHIR server who have had any procedures whose
    codes are listed in the file 'codes.csv'. The procedure dates should 
    occur on or after October 2016. Write results to the file query_results.csv.

     python3 ./fhir_patient_query.py --base_url http://hapi.fhir.org/baseDstu2
                                     --resource_type Procedure
                                     --code_file codes.csv
                                     --start_date 2016-10-01
                                     --output_file query_results.csv

        <results written to query_results.csv>


"""

import re
import os
import csv
import sys
import json
import argparse
import requests
from collections import namedtuple

# this module returns a list of object of this type
PatientQueryResult = namedtuple('PatientQueryResult', [
    'patient_id', 'datetime_start', 'datetime_end'
])


_VERSION_MAJOR = 0
_VERSION_MINOR = 1
_MODULE_NAME   = 'fhir_patient_query.py'

# set to True to enable debug output
_TRACE = False

_EMPTY_STRING = ''


###############################################################################
def _enable_debug():

    global _TRACE
    _TRACE = True
    

###############################################################################
def _to_fhir_resource(resource_type):
    """
    Convert a resource type string in any case to a properly-cased FHIR 
    resource type string.
    """

    assert resource_type is not None

    rt = resource_type.lower()

    result = None
    if 'observation' == rt:
        result = 'Observation'
    elif 'procedure' == rt:
        result = 'Procedure'

    return result
    

###############################################################################
def _load_code_file(code_file):
    """
    Load a CSV file of coding info. Each row of the file should contain the
    codesystem URL as the first element followed by a list of codes.

    Here is an example that includes a header row:

        codesystem,codelist
        http://loinc.org,26464-8,804-5,6690-2,49498-9
        http://snomed.info/sct,271737000,40172005

    This function returns an empty list if the file cannot be read.
    """

    lineno = -1
    coding_list = []
    with open(code_file, 'rt') as infile:
        csv_reader = csv.reader(infile, delimiter=',')
        for item in csv_reader:
            lineno += 1
            if 0 == lineno:
                continue
            assert len(item) >= 2
            codesys = item[0]
            code_list = item[1:]
            coding_list.append( (codesys, code_list) )
                   
    return coding_list


###############################################################################
def _build_code_string(coding_list):
    """
    Convert a coding list extracted from the coding file to the 'code' portion
    of a FHIR search query. Each code is prefixed with the codesystem, which
    must be supplied in the code_file.
    """

    substrings = []
    for codesys,code_list in coding_list:
        codes = [c.strip('\"\'') for c in code_list]    
        for code in codes:
            substr = '{0}|{1}'.format(codesys, code)
            substrings.append(substr)

    joined = ','.join(substrings)
    result = 'code=' + joined
    return result


###############################################################################
def build_query_url(base_url,
                    resource_type,
                    str_code_list=None,
                    str_code_file=None,
                    start_date=None,
                    end_date=None):
    """
    Construct the FHIR query from the provided args.
    """

    # must have either a code_file or a list of codes
    if str_code_list is None and str_code_file is None:
        print('{0}: Either a code_list or a code_file must be provided.'.
              format(_MODULE_NAME))
        return _EMPTY_STRING

    # cannot have both
    if str_code_list is not None and str_code_file is not None:
        print('{0}: The code_list and code_file args cannot both be present.'.
              format(_MODULE_NAME))
        return _EMPTY_STRING
    
    assert str_code_list is not None or str_code_file is not None
    
    query_url = _EMPTY_STRING
    
    # get the desired FHIR resource, properly capitalized
    fhir_resource = _to_fhir_resource(resource_type)
    if fhir_resource is None:
        print('Unsupported resource type: "{0}"'.format(resource_type))
        return query_url

    if str_code_list is not None:
        code_list = str_code_list.split(',')
        code_list = [c.strip('\"\'') for c in code_list]
        joined = ','.join(code_list)
        code_str = 'code=' + joined
    
    if str_code_file is not None:
        # load the code info from the code_file
        if not os.path.exists(str_code_file):
            print('File not found: "{0}"'.format(str_code_file))
            return query_url

        coding_list = _load_code_file(str_code_file)
        if 0 == len(coding_list):
            print('No codes were found in the code_file "{0}"'.format(str_code_file))
            return query_url

        # build the code portion of the query URL
        code_str = _build_code_string(coding_list)

    # build the portions of the query URL that are independent of date and code(s)
    query_url = '{0}/{1}?'.format(base_url, fhir_resource)

    # add the date portions
    if start_date is not None:
        query_url += 'date=ge{0}&'.format(start_date)
    if end_date is not None:
        query_url += 'date=lt{0}&'.format(end_date)

    query_url += '{0}'.format(code_str)
    
    return query_url


###############################################################################
def _submit_query(query_url):
    """
    Perform an HTTP GET on the query url and return the page of results.
    """

    has_error = False
    r = None
    try:
        r = requests.get(query_url)
    except requests.exceptions.HTTPError as e:
        print('\n*** HTTP error: "{0}" ***\n'.format(e))
        has_error = True
    except requests.exceptions.ConnectionError as e:
        print('\n*** ConnectionError: "{0}" ***\n'.format(e))
        has_error = True
    except requests.exceptions.Timeout as e:
        print('\n*** Timeout: "{0}" ***\n'.format(e))
        has_error = True
    except requests.exceptions.RequestException as e:
        print('\n*** RequestException: "{0}" ***\n'.format(e))
        has_error = True

    if has_error:
        print('HTTP error, terminating...')
        if r:
            print('RESPONSE CONTENT')
            print(r.content)
            print('RESPONSE HEADERS')
            print(r.headers)
        return

    if _TRACE:
        print('Response status code: {0}'.format(r.status_code))

    if 200 == r.status_code:
        json_results = r.json()
        if _TRACE:
            print('\n*** QUERY RESULTS ***\n')
            print(json_results)
            print()
        # returns a dict
        return json_results
    else:
        return None
    

###############################################################################
def run(query_url):
    """
    Submit the FHIR query and extract patient and date data from all pages.
    """

    RT_OBS  = 'Observation'
    RT_PROC = 'Procedure'

    results = []

    # loop until all pages have been processed
    url = query_url
    while True:
        if _TRACE:
            print(url)
        json_data = _submit_query(url)
        next_url = None
        if json_data is not None:
            for key in json_data:
                if 'link' == key:
                    link_list = json_data[key]
                    for obj in link_list:
                        if 'relation' in obj and 'next' == obj['relation']:
                            next_url = obj['url']
                if 'entry' == key:
                    entry_list = json_data[key]
                    for entry in entry_list:
                        if 'resource' in entry:
                            start = None
                            end   = None
                            patient_id = None
                            resource = entry['resource']
                            if 'subject' in resource:
                                # 'subject appears in Observation and Procedure
                                patient_ref = resource['subject']['reference']
                                # of the form Patient/<number>, keep the number
                                pos = patient_ref.find('/')
                                if -1 == pos:
                                    patient_id = patient_ref
                                else:
                                    patient_id = patient_ref[pos+1:]
                            if 'resourceType' in resource:
                                resource_type = resource['resourceType']
                                prefix = None
                                if RT_PROC == resource_type:
                                    prefix = 'performed'
                                elif RT_OBS == resource_type:
                                    prefix = 'effective'

                                if prefix is not None:
                                    # check for a time period
                                    field_name = '{0}Period'.format(prefix)
                                    if field_name in resource:
                                            period = resource[field_name]
                                            if 'start' in period:
                                                start = period['start']
                                            if 'end' in period:
                                                end = period['end']

                                    field_name = '{0}DateTime'.format(prefix)
                                    if field_name in resource:
                                            start = resource[field_name]
                                        
                            pqr = PatientQueryResult(patient_id, start, end)
                            results.append(pqr)

                            
        if next_url is not None:
            url = next_url
        else:
            break

    return results
    

###############################################################################
def _is_valid_date(str_date):
    """
    Check that the date string has one of these formats: 
        YYYY
        YYYY-MM
        YYYY-MM-DD

    Accept any digits for the year, since de-identification of medical data
    often produces dates in the future.
    """
    
    match = re.match(r'\A\d\d\d\d\-(0[1-9]|1[0-2])\-' +\
                     r'(0[1-9]|1[0-9]|2[0-9]|3[0-1])\Z', str_date)
    if match:
        return True

    match = re.match(r'\A\d\d\d\d\-(0[1-9]|1[0-2])\Z', str_date)
    if match:
        return True

    match = re.match(r'\A\d\d\d\d\Z', str_date)
    if match:
        return True

    print('Invalid date format: "{0}".'.format(str_date))
    print('Valid date formats are YYYY, YYYY-MM, YYYY-MM-DD.')
    return False
    

###############################################################################
def _get_version():
    return '{0} {1}.{2}'.format(_MODULE_NAME, _VERSION_MAJOR, _VERSION_MINOR)


###############################################################################
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='build FHIR API query, run the query, and find patients')

    parser.add_argument('-v', '--version',
                        action='store_true',
                        help='print version info and exit')
    parser.add_argument('--base_url',
                        help='the base URL of the FHIR server to be queried')
    parser.add_argument('--resource_type',
                        help='the FHIR resourceType to be queried')
    parser.add_argument('--start_date',
                        help='return resources with timestamps >= start_date; '
                        'valid formats are YYYY, YYYY-MM, YYYY-MM-DD')
    parser.add_argument('--end_date',
                        help='return resources with timestamps < end_date; '
                        'formats are YYYY, YYYY-MM, YYYY-MM-DD')
    parser.add_argument('--code_list',
                        help='comma-separated list of codes with NO spaces')
    parser.add_argument('--code_file',
                        help='CSV file with codesystems and codes')
    parser.add_argument('--output_file',
                       help='write results to this file in CSV format')
    parser.add_argument('--debug',
                        action='store_true',
                        help='print debugging information to stdout')
    
    args = parser.parse_args()

    if 'version' in args and args.version:
        print(_get_version())
        sys.exit(0)

    if 'debug' in args and args.debug:
        _enable_debug()

    base_url = None
    if 'base_url' in args and args.base_url:
        base_url = args.base_url
    else:
        print('The --base_url argument is required.')
        sys.exit(-1)

    resource_type = None
    if 'resource_type' in args and args.resource_type:
        resource_type = args.resource_type
    else:
        print('The --resource_type argument is required.')
        sys.exit(-1)

    str_code_list = None
    if 'code_list' in args and args.code_list:
        str_code_list = args.code_list

    str_code_file = None
    if 'code_file' in args and args.code_file:
        str_code_file = args.code_file
        if not os.path.exists(str_code_file):
            print('File not found: "{0}"'.format(str_code_file))
            sys.exit(-1)

    str_output_file = 'out.csv'
    if 'output_file' in args and args.output_file:
        str_output_file = args.output_file

    start_date = None
    if 'start_date' in args and args.start_date:
        start_date = args.start_date.strip()
        if not _is_valid_date(start_date):
            sys.exit(-1)

    end_date = None
    if 'end_date' in args and args.end_date:
        end_date = args.end_date.strip()
        if not _is_valid_date(end_date):
            sys.exit(-1)
            
    # must have either a code_file or a list of codes
    if str_code_list is None and str_code_file is None:
        print('Either the --code_list or the --code_file argument must be provided.')
        sys.exit(-1)

    # cannot have both
    if str_code_list is not None and str_code_file is not None:
        print('The --code_list and --code_file arguments cannot both be present.')
        sys.exit(-1)

    query_url = build_query_url(base_url,
                                resource_type,
                                str_code_list,
                                str_code_file,
                                start_date,
                                end_date)
    if _TRACE:
        print('QUERY URL: {0}'.format(query_url))

    if _EMPTY_STRING != query_url:
        # submit the query to the FHIR server
        results = run(query_url)

        unique_patients = set()
        cols = ['patient_id', 'datetime_start', 'datetime_end']
        with open(str_output_file, 'wt') as outfile:
            dict_writer = csv.DictWriter(outfile, fieldnames=cols)
            dict_writer.writeheader()
            for r in results:
                dict_writer.writerow(
                    {cols[0]:r.patient_id,
                     cols[1]:r.datetime_start,
                     cols[2]:r.datetime_end}
                )
                unique_patients.add(r.patient_id)
            print('Wrote {0} results for {1} patients to "{2}".'.format(len(results),
                                                                        len(unique_patients),
                                                                        str_output_file))
            
    
