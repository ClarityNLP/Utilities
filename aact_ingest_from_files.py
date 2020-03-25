import csv
import json
import re
import sys
import time
import xmltodict

import requests
from requests.auth import HTTPBasicAuth


def get_exclusion_criteria_index(criteria):
	try:
		ex_index = criteria.lower().index("exclusion criteria")
	except ValueError:
		ex_index = -1
	return ex_index


def no_match(row):
	if not query_terms or len(query_terms) == 0:
		return False
	for qt in query_terms:
		for r1 in row:
			r_match = re.search(qt, r1, re.IGNORECASE)
			if r_match:
				return False

	return True


def no_id_match(the_id):
	return the_id not in valid_ids


def read_aact():
	# Sample AACT data read from here - https://www.ctti-clinicaltrials.org/aact-database
	file_in = "eligibilities.txt"
	with open('data/clinical_study.txt') as f:
		cols = None
		results = list()

		txt = ''
		for i, line in enumerate(f):

			if i == 0:
				cols = line.split('|')
			else:

				if line.startswith('NCT') and len(txt) > 0:
					res = txt.split('|')
					if no_id_match(res[1]):
						continue

					criteria = res[26]

					ex_index = get_exclusion_criteria_index(criteria)

					if ex_index >= 0:
						inclusion = criteria[0:ex_index]
						exclusion = criteria[ex_index:]
					else:
						inclusion = criteria
						exclusion = ''
					new_row = [res[0], inclusion, exclusion, res[27], res[28], res[29]]
					if criteria != 'Please contact site for information.':
						results.append(new_row)
					txt = line
				else:
					if len(line.strip()) > 0:
						txt = txt + line

		print(len(results))
		return results


def load_criteria_in_solr():
	file_in = base_dir + "eligibilities.txt"

	result_list = list()
	with open(file_in) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter='|')
		line = 0
		cols = []
		for row in csv_reader:
			if line == 0:
				cols = row
				print(cols)
			else:
				# print(row[1])
				if no_id_match(row[1]):
					continue
				criteria_str = str(row[8])
				criteria_split = criteria_str.split('~')
				criteria = ''
				n = 0
				for i in criteria_split:
					stripped = i.strip()
					if len(stripped) > 0:
						if n == 0:
							criteria = stripped
						elif not (stripped[0].islower() or stripped[0].isnumeric() or stripped[0] == ')' or stripped[
							0] == '(') and n > 0:
							criteria += '\n '
							criteria += stripped
						else:
							criteria += ' '
							criteria += stripped
					n += 1

				criteria = criteria.encode("ascii", errors="ignore").decode()
				ex_index = get_exclusion_criteria_index(criteria)

				if ex_index >= 0:
					inclusion = criteria[0:ex_index]
					exclusion = criteria[ex_index:]
				else:
					inclusion = criteria
					exclusion = ''

				d = {
					"subject": row[1],
					"description_attr": "AACT Clinical Trials",
					"source": source + '_inclusion_criteria',
					"report_date": report_date
				}
				for i in range(len(cols)):
					if i != 0 and i != 1 and i != 7 and i != 8:
						colname = cols[i] + "_attr"
						d[colname] = str(row[i])

				d2 = d.copy()

				d["report_type"] = "Clinical Trial Inclusion Criteria"
				d["id"] = "ct_inc_" + row[0]
				d["report_id"] = "ct_inc_" + row[0]
				d["report_text"] = inclusion
				result_list.append(d)

				if len(exclusion) > 0:
					d2["report_type"] = "Clinical Trial Exclusion Criteria"
					d2["id"] = "ct_exc_" + row[0]
					d2["report_id"] = "ct_exc_" + row[0]
					d2["report_text"] = exclusion
					result_list.append(d2)
				else:
					print('no exclusion')
			line += 1

			if line % 100 == 0:
				print("parsed {0} lines".format(str(line)))
				# Pushing data to Solr
				data = json.dumps(result_list)
				response2 = requests.post(url, headers=headers, data=data, auth=auth)

				if response2.status_code == 200:
					print("Uploaded AACT eligibilities batch")
				result_list = list()

	print("parsed {0} lines".format(str(line)))
	# Pushing data to Solr
	data = json.dumps(result_list)
	response2 = requests.post(url, headers=headers, data=data, auth=auth)

	if response2.status_code == 200:
		print("Uploaded AACT eligibilities all")


def get_criteria():
	file_in = base_dir + "eligibilities.txt"

	result_list = dict()
	excl_result_list = dict()
	with open(file_in) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter='|')
		line = 0
		cols = []
		for row in csv_reader:
			if line == 0:
				cols = row
				print(cols)
			else:
				# print(row[1])
				if no_id_match(row[1]):
					continue
				criteria_str = str(row[8])
				criteria_split = criteria_str.split('~')
				criteria = ''
				n = 0
				for i in criteria_split:
					stripped = i.strip()
					if len(stripped) > 0:
						if n == 0:
							criteria = stripped
						elif not (stripped[0].islower() or stripped[0].isnumeric() or stripped[0] == ')' or stripped[
							0] == '(') and n > 0:
							criteria += '\n '
							criteria += stripped
						else:
							criteria += ' '
							criteria += stripped
					n += 1

				criteria = criteria.encode("ascii", errors="ignore").decode()
				ex_index = get_exclusion_criteria_index(criteria)

				if ex_index >= 0:
					inclusion = criteria[0:ex_index]
					exclusion = criteria[ex_index:]
				else:
					inclusion = criteria
					exclusion = ''

				d = {
					"subject": row[1],
					"description_attr": "AACT Clinical Trials",
					"source": source + '_inclusion_criteria',
					"report_date": report_date
				}
				for i in range(len(cols)):
					if i != 0 and i != 1 and i != 7 and i != 8:
						colname = cols[i] + "_attr"
						d[colname] = str(row[i])

				d2 = d.copy()

				d["report_type"] = "Clinical Trial Inclusion Criteria"
				d["id"] = "ct_inc_" + row[0]
				d["report_id"] = "ct_inc_" + row[0]
				d["report_text"] = inclusion

				result_list[row[1]] = d

				if len(exclusion) > 0:
					d2["report_type"] = "Clinical Trial Exclusion Criteria"
					d2["id"] = "ct_exc_" + row[0]
					d2["report_id"] = "ct_exc_" + row[0]
					d2["report_text"] = exclusion

					if row[1] not in excl_result_list:
						excl_result_list[row[1]] = list()
					excl_result_list[row[1]] = d2
				else:
					excl_result_list[row[1]] = dict()
					print('no exclusion')
			line += 1

	return result_list, excl_result_list


def load_descriptions_in_solr():
	file_in = base_dir + "detailed_descriptions.txt"

	result_list = list()
	with open(file_in) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter='|')
		line = 0
		cols = []
		for row in csv_reader:
			if line == 0:
				cols = row
				print(cols)
			else:
				# print(row[1])
				if no_id_match(row[1]):
					continue
				txt_str = str(row[2])
				txt_split = txt_str.split('~')
				txt = ''
				n = 0
				for i in txt_split:
					stripped = i.strip()
					if len(stripped) > 0:
						if n == 0:
							txt = stripped
						elif not (stripped[0].islower() or stripped[0].isnumeric() or stripped[0] == ')' or stripped[
							0] == '(') and n > 0:
							txt += '\n '
							txt += stripped
						else:
							txt += ' '
							txt += stripped

					n += 1
				intervention = int
				d = {"subject": row[1],
				     "description_attr": "AACT Clinical Trials",
				     "source": source + '_trial_description',
				     "report_type": "Clinical Trial Description",
				     "report_text": txt,
				     "report_id": row[0],
				     "id": row[0],
				     "report_date": report_date
				     }
				result_list.append(d)
			line += 1

			if line % 100 == 0:
				print("parsed {0} lines".format(str(line)))
				# Pushing data to Solr
				data = json.dumps(result_list)
				response2 = requests.post(url, headers=headers, data=data, auth=auth)

				if response2.status_code == 200:
					print("Uploaded AACT description batch")
				result_list = list()

	print("parsed {0} lines".format(str(line)))
	# Pushing data to Solr
	data = json.dumps(result_list)
	response2 = requests.post(url, headers=headers, data=data, auth=auth)

	if response2.status_code == 200:
		print("Uploaded AACT description all")


def get_descriptions():
	file_in = base_dir + "detailed_descriptions.txt"

	result_list = dict()
	with open(file_in) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter='|')
		line = 0
		cols = []
		for row in csv_reader:
			if line == 0:
				cols = row
				print(cols)
			else:
				# print(row[1])
				if no_id_match(row[1]):
					continue
				txt_str = str(row[2])
				txt_split = txt_str.split('~')
				txt = ''
				n = 0
				for i in txt_split:
					stripped = i.strip()
					if len(stripped) > 0:
						if n == 0:
							txt = stripped
						elif not (stripped[0].islower() or stripped[0].isnumeric() or stripped[0] == ')' or stripped[
							0] == '(') and n > 0:
							txt += '\n '
							txt += stripped
						else:
							txt += ' '
							txt += stripped

					n += 1
				d = {"subject": row[1],
				     "description_attr": "AACT Clinical Trials",
				     "source": source + '_trial_description',
				     "report_type": "Clinical Trial Description",
				     "report_text": txt,
				     "report_id": row[0],
				     "id": row[0],
				     "report_date": report_date
				     }
				result_list[row[1]] = d
			line += 1
	return result_list


def load_interventions_in_solr():
	file_in = base_dir + "interventions.txt"

	result_list = list()
	with open(file_in) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter='|')
		line = 0
		cols = []
		for row in csv_reader:
			if line == 0:
				cols = row
				print(cols)
			else:
				# print(row[1])
				if no_id_match(row[1]):
					continue
				txt_str = str(row[4])
				txt_split = txt_str.split('~')
				txt = ''
				n = 0
				for i in txt_split:
					stripped = i.strip()
					if len(stripped) > 0:
						if n == 0:
							txt = stripped
						elif not (stripped[0].islower() or stripped[0].isnumeric() or stripped[0] == ')' or stripped[
							0] == '(') and n > 0:
							txt += '\n '
							txt += stripped
						else:
							txt += ' '
							txt += stripped
					n += 1
				# id|nct_id|intervention_type|name|description
				d = {"subject": row[1],
				     "description_attr": "AACT Clinical Trials",
				     "source": source + '_trial_intervention',
				     "report_type": "Clinical Trial Interventions",
				     "report_text": txt,
				     "report_id": row[0],
				     "id": row[0],
				     "type_attr": str(row[2]),
				     "name_attr": str(row[3]),
				     "intervention_desc_attr": str(row[4]),
				     "report_date": report_date
				     }
				result_list.append(d)
			line += 1

			if line % 100 == 0:
				print("parsed {0} lines".format(str(line)))
				# Pushing data to Solr
				data = json.dumps(result_list)
				response2 = requests.post(url, headers=headers, data=data, auth=auth)

				if response2.status_code == 200:
					print("Uploaded AACT intervention batch")
				result_list = list()

	print("parsed {0} lines".format(str(line)))
	# Pushing data to Solr
	data = json.dumps(result_list)
	response2 = requests.post(url, headers=headers, data=data, auth=auth)

	if response2.status_code == 200:
		print("Uploaded AACT intervention all")


def get_interventions():
	file_in = base_dir + "interventions.txt"

	result_list = dict()
	with open(file_in) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter='|')
		line = 0
		cols = []
		for row in csv_reader:
			if line == 0:
				cols = row
				print(cols)
			else:
				# print(row[1])
				if no_id_match(row[1]):
					continue
				txt_str = str(row[4])
				txt_split = txt_str.split('~')
				txt = ''
				n = 0
				for i in txt_split:
					stripped = i.strip()
					if len(stripped) > 0:
						if n == 0:
							txt = stripped
						elif not (stripped[0].islower() or stripped[0].isnumeric() or stripped[0] == ')' or stripped[
							0] == '(') and n > 0:
							txt += '\n '
							txt += stripped
						else:
							txt += ' '
							txt += stripped
					n += 1
				# id|nct_id|intervention_type|name|description
				d = {"subject": row[1],
				     "description_attr": "AACT Clinical Trials",
				     "source": source + '_trial_intervention',
				     "report_type": "Clinical Trial Interventions",
				     "report_text": txt,
				     "report_id": row[0],
				     "id": row[0],
				     "type_attr": str(row[2]),
				     "name_attr": str(row[3]),
				     "intervention_desc_attr": str(row[4]),
				     "report_date": report_date
				     }
				if row[1] not in result_list:
					result_list[row[1]] = list()
				result_list[row[1]].append(d)
			line += 1

	return result_list


def get_all_inclusion_ids():
	# Sample AACT data read from here - https://www.ctti-clinicaltrials.org/aact-database
	file_in = base_dir + "brief_summaries.txt"

	valid_ids = list()
	with open(file_in) as f:
		csv_reader = csv.reader(f, delimiter='|')
		line = 0
		for row in csv_reader:
			if line > 0:
				if no_match(row):
					continue
				else:
					print(row)

				id = row[1]
				valid_ids.append(id)

			line += 1
	return valid_ids


def generic_loader(name, field_names, nct_index=1):
	file_in = base_dir + "{}.txt".format(name)

	result_list = dict()
	with open(file_in) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter='|')
		line = 0
		cols = []
		for row in csv_reader:
			if line == 0:
				# cols = row
				# print(cols)
				pass
			else:
				# print(row[1])
				if no_id_match(row[1]):
					continue
				d = dict()
				n = 0
				for f in field_names:
					if n > 1:
						d[f] = row[n]
					n += 1
				subj = row[nct_index]
				result_list[subj] = d
			line += 1

	return result_list


def generic_list_loader(name, field_names, nct_index=1):
	file_in = base_dir + "{}.txt".format(name)

	result_list = dict()
	with open(file_in) as csv_file:
		csv_reader = csv.reader(csv_file, delimiter='|')
		line = 0
		cols = []
		for row in csv_reader:
			if line == 0:
				pass
			# cols = row
			# print(cols)
			else:
				# print(row[1])
				if no_id_match(row[1]):
					continue
				d = dict()
				n = 0
				for f in field_names:
					if n > 1:
						d[f] = row[n]
					n += 1
				subj = row[nct_index]
				if subj not in result_list:
					result_list[subj] = list()
				result_list[subj].append(d)
			line += 1

	return result_list


def get_others():
	brief_summary = generic_loader('brief_summaries', ['id', 'nct', 'report_text'])
	keywords = generic_list_loader('keywords', ['id', 'nct', 'name', 'downcase_name'])
	countries = generic_list_loader('countries', ['id', 'nct', 'name', 'removed'])

	df = ['id', 'nct_id']
	df.extend(design_fields)
	designs = generic_loader('designs', df)

	sf = ['nct']
	sf.extend(study_fields)
	studies = generic_loader('studies', sf)

	return brief_summary, keywords, countries, designs, studies


def load_into_solr(valid_ids, incl_list, excl_list, descriptions, interventions, brief_summary, keywords, countries,
                   designs, studies):
	print('load into solr..')
	max_intervention = 1
	for k in interventions.keys():
		v = interventions[k]
		if len(v) > max_intervention:
			max_intervention = len(v)
	with open(export_file, 'w+', newline='') as csvfile_writer:
		base_fieldnames = ['NCT_ID', 'Scrape_Date']

		description_fields = ['Brief_Summary', 'Detailed_Description']
		status_fieldnames = ['title', 'submitted_date', 'updated_date', 'status', 'phase', 'study_type',
		                     'number_of_arms', 'completion_date', 'completion_date_type', 'enrollment',
		                     'enrollment_type']
		intervention_fields = ['Intervention_Name_{}', 'Intervention_Type_{}', 'Intervention_Description_{}',
		                       'Intervention_Full_Text_{}']
		incl_fields = ['Inclusion_Criteria', 'Gender', 'Min_Age', 'Max_Age', 'Healthy_Volunteers',
		               'Inclusion_Sampling_Method']
		excl_fields = ['Exclusion_Criteria', 'Exclusion_Sampling_Method']
		keyword_fields = ['Keywords']
		country_fields = ['Countries']

		fields = list()
		fields.extend(base_fieldnames)
		fields.extend(status_fieldnames)
		fields.extend(description_fields)
		for i in range(max_intervention):
			for f in intervention_fields:
				fields.append(f.format(i))
		fields.extend(incl_fields)
		fields.extend(excl_fields)
		fields.extend(keyword_fields)
		fields.extend(country_fields)
		fields.extend(design_fields)
		fields.extend(study_fields)

		writer = csv.writer(csvfile_writer, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
		writer.writerow(fields)
		result_list = list()
		for i in valid_ids:
			try:
				resp = requests.get('https://clinicaltrials.gov/ct2/show/{}?displayxml=true'.format(i))
				if resp.status_code == 200:
					json_study_data = xmltodict.parse(resp.text).get('clinical_study', dict())
				else:
					json_study_data = dict()
			except Exception as ex:
				print(ex)

			inclusion = incl_list.get(i, dict())
			exclusion = excl_list.get(i, dict())
			description = descriptions.get(i, dict())
			iv = interventions.get(i, list())
			summary = brief_summary.get(i, dict())
			country_data = countries.get(i, list())
			keyword_data = keywords.get(i, list())
			design_data = designs.get(i, dict())
			study_data = studies.get(i, dict())

			d = list()

			d.append(i)
			d.append(inclusion.get('report_date'))

			solr_doc = {"subject": i,
			            "id": i,
			            "report_id": i,
			            "source": source,
			            "report_date": inclusion.get('report_date')
			            }

			title = json_study_data.get('official_title', '')
			submitted_date = json_study_data.get('study_first_submitted', '')
			updated_date = json_study_data.get('last_update_submitted', '')
			status = json_study_data.get('overall_status', '')
			phase = json_study_data.get('phase', '')
			study_type = json_study_data.get('study_type', '')
			number_of_arms = json_study_data.get('number_of_arms', '')

			year = int(updated_date[-2:])
			if year < 19:
				continue

			d.append(title)
			d.append(submitted_date)
			d.append(updated_date)
			d.append(status)
			d.append(phase)
			d.append(study_type)
			d.append(number_of_arms)
			solr_doc['title_attr'] = title
			solr_doc['submitted_attr'] = submitted_date
			solr_doc['update_attr'] = updated_date
			solr_doc['phase_attr'] = phase
			solr_doc['status_attr'] = status
			solr_doc['study_type_attr'] = study_type
			solr_doc['arms_attr'] = number_of_arms

			completion_date = json_study_data.get('completion_date', dict())
			if isinstance(completion_date, dict):
				completion_date_type = completion_date.get('@type', '')
				completion_date_text = completion_date.get('#text', '')
			else:
				completion_date_text = completion_date
				completion_date_type = ''
			d.append(completion_date_text)
			d.append(completion_date_type)
			solr_doc['completion_attr'] = completion_date_text
			solr_doc['completion_type_attr'] = completion_date_type

			enrollment = json_study_data.get('enrollment', dict())
			if isinstance(enrollment, dict):
				enrollment_type = enrollment.get('@type', '')
				enrollment_text = enrollment.get('#text', '')
			else:
				enrollment_type = ''
				enrollment_text = enrollment
			d.append(enrollment_text)
			d.append(enrollment_type)
			solr_doc['enrollment_attr'] = enrollment_text
			solr_doc['enrollment_type'] = enrollment_type

			summary_text = summary.get('report_text', '').replace('~', ' ').strip()
			detailed_text = description.get('report_text', '').strip()
			d.append(summary_text)
			d.append(detailed_text)

			solr_doc['report_text'] = summary_text
			solr_doc['detailed_summary_attr'] = detailed_text

			for n in range(max_intervention):
				if len(iv) > n:
					d.append(iv[n].get('name_attr'))
					d.append(iv[n].get('type_attr'))
					d.append(iv[n].get('intervention_desc_attr'))
					d.append(iv[n].get('report_text'))

					solr_doc['intervention_{}_name_attr'.format(n)] = iv[n].get('name_attr')
					solr_doc['intervention_{}_type_attr'.format(n)] = iv[n].get('type_attr')
					solr_doc['intervention_{}_desc_attr'.format(n)] = iv[n].get('intervention_desc_attr')
					solr_doc['intervention_{}_attr'.format(n)] = iv[n].get('report_text')
				else:
					d.append('')
					d.append('')
					d.append('')
					d.append('')

			d.append(inclusion.get('report_text', '').strip())
			d.append(inclusion.get('gender_attr'))
			d.append(inclusion.get('minimum_age_attr'))
			d.append(inclusion.get('maximum_age_attr'))
			d.append(inclusion.get('healthy_volunteers_attr'))
			d.append(inclusion.get('sampling_method_attr'))

			solr_doc['inclusion_attr'] = inclusion.get('report_text', '').strip()
			solr_doc['gender_attr'] = inclusion.get('gender_attr', '').strip()
			solr_doc['minimum_age_attr'] = inclusion.get('minimum_age_attr', '').strip()
			solr_doc['maximum_age_attr'] = inclusion.get('maximum_age_attr', '').strip()
			solr_doc['healthy_volunteers_attr'] = inclusion.get('healthy_volunteers_attr', '').strip()
			solr_doc['inclusion_sampling_method_attr'] = inclusion.get('report_text', '').strip()

			d.append(exclusion.get('report_text', '').strip())
			d.append(exclusion.get('sampling_method_attr'))

			solr_doc['exclusion_attr'] = exclusion.get('report_text', '').strip()
			solr_doc['exclusion_sampling_method_attr'] = exclusion.get('sampling_method_attr')

			keyword_txt = ''
			for k in keyword_data:
				if len(keyword_txt) > 0:
					keyword_txt += '|'
				name = k.get('name', '')
				if len(name) > 0:
					keyword_txt += name
			d.append(keyword_txt)
			solr_doc['keyword_attr'] = keyword_txt

			country_txt = ''
			for k in country_data:
				if len(country_txt) > 0:
					country_txt += '|'
				name = k.get('name', '')
				if len(name) > 0:
					country_txt += name
			d.append(country_txt)
			solr_doc['countries_attr'] = country_txt

			# design
			for df in design_fields:
				val = design_data.get(df, '')
				d.append(val)
				if len(val) > 0:
					solr_doc['{}_attr'.format(df)] = val

			# studies
			for sf in study_fields:
				val = study_data.get(sf, '')
				d.append(val)
				if len(val) > 0:
					solr_doc['{}_attr'.format(sf)] = val

			writer.writerow(d)
			csvfile_writer.flush()
			result_list.append(solr_doc)
		data = json.dumps(result_list)
		response2 = requests.post(url, headers=headers, data=data, auth=auth)

		if response2.status_code == 200:
			print("SUCCESSFUL AACT batch, {} records".format(len(result_list)))
		else:
			print("FAILED AACT batch, {} records".format(len(result_list)))

	print(d)


if __name__ == "__main__":

	year = '2020'
	month = '03'
	day = '24'
	solr_url = 'https://bare.claritynlp.cloud/solr/sample'
	base_dir = '/Users/charityhilton/Downloads/{}{}{}_pipe-delimited-export/'.format(year, month, day)
	export_file = '/Users/charityhilton/Downloads/{}{}{}_aact_covid19_export.csv'.format(year, month, day)
	default_source = 'covid19_trials'
	report_date = "{}-{}-{}T00:00:00Z".format(year, month, day)

	design_fields = 'allocation|intervention_model|observational_model|primary_purpose|time_perspective|masking|masking_description|intervention_model_description|subject_masked|caregiver_masked|investigator_masked|outcomes_assessor_masked'.split(
		'|')
	study_fields = 'nlm_download_date_description|study_first_submitted_date|results_first_submitted_date|disposition_first_submitted_date|last_update_submitted_date|study_first_submitted_qc_date|study_first_posted_date|study_first_posted_date_type|results_first_submitted_qc_date|results_first_posted_date|results_first_posted_date_type|disposition_first_submitted_qc_date|disposition_first_posted_date|disposition_first_posted_date_type|last_update_submitted_qc_date|last_update_posted_date|last_update_posted_date_type|start_month_year|start_date_type|start_date|verification_month_year|verification_date|completion_month_year|completion_date_type|completion_date|primary_completion_month_year|primary_completion_date_type|primary_completion_date|target_duration|study_type|acronym|baseline_population|brief_title|official_title|overall_status|last_known_status|phase|enrollment|enrollment_type|source|limitations_and_caveats|number_of_arms|number_of_groups|why_stopped|has_expanded_access|expanded_access_type_individual|expanded_access_type_intermediate|expanded_access_type_treatment|has_dmc|is_fda_regulated_drug|is_fda_regulated_device|is_unapproved_device|is_ppsd|is_us_export|biospec_retention|biospec_description|ipd_time_frame|ipd_access_criteria|ipd_url|plan_to_share_ipd|plan_to_share_ipd_description|created_at|updated_at'.split(
		'|')

	# default_query_terms = ['coronavirus', 'covid-19', 'covid19', 'SARS-CoV-2', 'Hydroxychloroquine', 'Lopinavir', 'Ritonavir',
	#                        'Remdisivir', 'Favipiravir', 'Camostat', '2019-nCoV']
	default_query_terms = ['coronavirus', 'covid-19', 'covid19', 'SARS-CoV-2', '2019-nCoV', 'SARS-nCoV']
	auth = None
	try:
		if len(sys.argv) < 1:
			print()
			print('Please run with the following command line args:')
			print(
				'\tpython3 aact_ingest_from_files.py <solr_url> <solr_user> <solr_password> <input_directory> <query_terms> <source>')
			print()
			print('e.g.:')
			print(
				'\tpython3 aact_ingest_from_files.py https://solr.internal.claritynlp.cloud/solr/sample admin test "/Users/Home/AACT_files/" drug 1,drug 2 my_custom_cohort')
			print()

			sys.exit(0)
		if len(sys.argv) > 6:
			source = sys.argv[5]
		else:
			source = default_source
		if len(sys.argv) > 5:
			query_terms = sys.argv[4].split(',')
		else:
			query_terms = default_query_terms
		if len(sys.argv) > 4:
			base_dir = int(sys.argv[4])
		if len(sys.argv) > 3:
			solr_user = sys.argv[2]
			solr_password = sys.argv[3]
			auth = HTTPBasicAuth(solr_user, solr_password)

		if len(sys.argv) > 2:
			solr_url = sys.argv[1]
	except Exception as ex1:
		print(ex1)

	url = solr_url + '/update?commit=true'
	headers = {
		'Content-type': 'application/json',
	}
	valid_ids = get_all_inclusion_ids()

	# load_criteria_in_solr()
	# load_descriptions_in_solr()
	# load_interventions_in_solr()

	brief_summary, keywords, countries, designs, studies = get_others()
	incl_list, excl_list = get_criteria()
	descriptions = get_descriptions()
	interventions = get_interventions()

	load_into_solr(valid_ids, incl_list, excl_list, descriptions, interventions, brief_summary,
	               keywords, countries, designs, studies)
	print('done')
