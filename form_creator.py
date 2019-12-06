import csv


def parse_set_net_form(csv_writer, csv_reader):

    last_form_field = None
    last_topic_field = None
    n = 1
    for row in csv_reader:
        # print(row.keys())
        topic_field = row.get('Topic').strip()
        variable_field = row.get('Variable').strip()
        response_field = row.get('Response options')

        if len(variable_field) == 0:
            continue

        if variable_field == "Pregnancy ID":
            answers = []
            notes = row.get('Response options')
            form_field = "All"
        else:
            answers = response_field.split('\n')
            notes = ''
            form_field = row.get('\ufeffForm').strip()

        question_type = "TEXT"
        if len(answers) > 1:
            question_type = "MC"
            if variable_field == "SET-NET pathogen/disease":
                question_type = "MS"
        else:
            notes = response_field
        if response_field == "MM/DD/YYYY" or response_field.lower() == 'date' or 'date of' in response_field:
            question_type = 'DATE'

        final_answers = []
        final_answers_str = ''
        if len(answers) > 1:
            for a in answers:
                low_a = a.lower()
                if low_a == 'etc.' or low_a == 'etc' or low_a == 'text' or low_a == 'text_field' or a.strip == '':
                    continue
                final_answers.append(a)
            if len(final_answers) > 1:
                final_answers_str = '"' + '","'.join(final_answers) + '"'
            else:
                notes = answers
        else:
            notes = answers

        if not form_field or len(form_field) == 0:
            form_field = last_form_field
        if not topic_field or len(topic_field) == 0:
            topic_field = last_topic_field
        # group = '{}: {}'.format(form_field, topic_field)
        group = form_field

        if n == 17:
            variable_field = 'Type 1 or type 2 diabetes (not gestational diabetes)'
        out_row = [str(n), variable_field, final_answers_str, group, question_type, '', '',
                             '', '', '', '', '',
                             '', '', '', '', '',
                             '', '', notes]
        csv_writer.writerow(out_row)
        print(out_row)
        last_form_field = form_field
        last_topic_field = topic_field

        n += 1


def convert_csv(input_file, output_file, form_type='set_net'):
    # print(form_type)
    with open(output_file, mode='w') as out_file:
        csv_writer = csv.writer(out_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(["#", "question_name", "answers", "group", "type", "evidence_bundle", "DoneBy",
                             "feature_name", "fhir_resource_type", "code_system", "codes", "valueset_oid",
                             "nlp_task_type", "text_terms", "value_min", "value_max", "value_enum_set",
                             "value_extractor_ast", "logic", "notes"])
        with open(input_file) as in_file:
            csv_reader = csv.DictReader(in_file, delimiter=',')

            if form_type == 'set_net':
                parse_set_net_form(csv_writer, csv_reader)


if __name__ == "__main__":
    convert_csv('/Users/charityhilton/Box/CDC_MotherBaby_TRANCHE2/set_net_variables.csv',
                '/Users/charityhilton/Box/CDC_MotherBaby_TRANCHE2/set_net_form.csv')
