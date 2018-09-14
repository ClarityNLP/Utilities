# Utilities

This repository contains a collection of scripts which are used for automating routine tasks associated with ClarityNLP. 


#### mimic_ingest.py

This script is for uploading the MIMIC dataset into ClarityNLPs Solr instance. 

To use the script, open the script and feed in the required parameters under the comment "User fed parameters". Then run `python mimic_ingest.py`.


#### gleason_pathology.py

This script is for uploading the Gleason pathology reports dataset into ClarityNLPs Solr instance. 

To use the script, open the script and feed in the required parameters under the comment "User fed parameters". Then run `python gleason_pathology.py`.


#### aact_ingest.py

This script is for loading information from the AACT clinical trials database into ClarityNLPs Solr instance. Information from the `detailed_descriptions`, `eligibilities`, and `interventions` tables are loaded into ClarityNLP. 

To use the script, open the script and feed in the required parameters under the comment "User fed parameters". Then run `python aact_ingest.py`.
