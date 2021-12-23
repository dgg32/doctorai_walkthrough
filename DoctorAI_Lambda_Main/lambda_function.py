import json
import random
import decimal 
import logging
import re
import os
from lambda_helper import random_num, get_slots, get_slot, get_session_attributes, elicit_intent, close
from neo4j_connection import Neo4jConnection

import base64
import boto3
import json
import random
import os
from botocore.exceptions import ClientError

def get_password_from_secret():
    password = "None"
    secret_name = os.environ['SECRET_NAME']
    my_session = boto3.session.Session()
    region_name = my_session.region_name
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        print(get_secret_value_response)
    except ClientError as e:
        print(e)
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            j = json.loads(secret)
            password = j['password']
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            print("password binary:" + decoded_binary_secret)
            password = decoded_binary_secret.password

    return password

password = get_password_from_secret()
Neo4jIp = os.environ['Neo4jIp']
conn = Neo4jConnection(uri=f"neo4j://{Neo4jIp}:7687", user='neo4j', pwd=password)
db = "neo4j"

def dispatch(intent_request):
    global password, Neo4jIp, conn, db
    intent_name = intent_request['sessionState']['intent']['name']
    response = None

    #print (f"Password: {password}; Neo4jIp: {Neo4jIp}; db: {db}")
    
    
    
    # Dispatch to your bot's intent handlers
    if intent_name == "test":
        return test(intent_request)
    elif intent_name == 'CountICUVisit':
        return count_icu_visit(intent_request, conn, db)
    elif intent_name == 'CheckFirstICUVisit':
        return check_first_icu_visit(intent_request, conn, db)
    elif intent_name == 'CheckLastDiagnosis':
        return check_last_diagnosis(intent_request, conn, db)
    elif intent_name == 'AskForLabReadings':
        return ask_for_readings(intent_request, conn, db)
    elif intent_name == 'Hello':
        return hello(intent_request, conn, db)
    elif intent_name == 'AskPatientRecord':
        return ask_patient_record(intent_request, conn, db)
    elif intent_name == 'AskForEthnicity':
        return ask_patient_ethnicity(intent_request, conn, db)
    elif intent_name == 'AskForInfectionOrganism':
        return ask_infection_organism(intent_request, conn, db)
    elif intent_name == 'RecommendTreatment':
        return recommend_patient_treatment(intent_request, conn, db)
    else:
        raise Exception('Intent with name ' + intent_name + ' not supported')

def lambda_handler(event, context):
    response = dispatch(event)
    return response

def count_icu_visit(intent_request, conn, db):
    session_attributes = get_session_attributes(intent_request)
    
    slots = get_slots(intent_request)
    patient_id = get_slot(intent_request, 'name').title()
    
    #print (f"MATCH(p:Patient{{patient_id: '{patient_id}'}})-[r:HAS_STAY]-(n) RETURN COUNT(r) as count_icu_visit")
    
    result = conn.query(f"MATCH(p:Patient{{patient_id: '{patient_id}'}})-[r:HAS_STAY]-(n) RETURN COUNT(r) as count_icu_visit",db=db)
    count_icu_visit = str(result[0]["count_icu_visit"])
    
    text = text = f"Patient {patient_id} visited the ICU {count_icu_visit} times."
    if count_icu_visit == "0":
        text = f"Patient {patient_id} has never visited the ICU before."
    elif count_icu_visit == "1":
        text = f"Patient {patient_id} has visited the ICU once."
    else:
        text = f"Patient {patient_id} has visited the ICU {count_icu_visit} times."
    
    message =  {
            'contentType': 'PlainText',
            'content': text
        }
    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)

def check_first_icu_visit(intent_request, conn, db):
    session_attributes = get_session_attributes(intent_request)
    
    slots = get_slots(intent_request)
    patient_id = get_slot(intent_request, 'name').title()
    
    result = conn.query(f"MATCH(p:Patient{{patient_id: '{patient_id}'}})-[r:HAS_STAY]-(n) RETURN COUNT(DISTINCT n) as last_visit",db=db)
    last_visit = str(result[0]["last_visit"])
    
    text = f"Patient {patient_id} first visited the ICU last {last_visit}."
    message =  {
            'contentType': 'PlainText',
            'content': text
        }
    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)

def check_last_diagnosis(intent_request, conn, db):
    session_attributes = get_session_attributes(intent_request)
    
    slots = get_slots(intent_request)
    patient_id = get_slot(intent_request, 'name').title()
    
    if get_slot(intent_request, 'count'):
        count = get_slot(intent_request, 'count')
        query = f"""MATCH(p:Patient{{patient_id:'{patient_id}'}})-[:HAS_STAY]->(n:PatientUnitStay)
        OPTIONAL MATCH (n)-[:HAS_DIAG]->(d:Diagnosis)
        WITH COUNT(DISTINCT n) AS visit_number
        MATCH(p:Patient{{patient_id:'{patient_id}'}})-[:HAS_STAY]->(n:PatientUnitStay)
        OPTIONAL MATCH (n)-[:HAS_DIAG]->(d:Diagnosis)
        WITH n.hospitaladmitoffset AS visit_order, collect(d.diagnosisstring) AS diagnosis, visit_number
        ORDER BY visit_order DESC
        LIMIT {count}
        RETURN visit_order, diagnosis, visit_number
        ORDER BY visit_order
        """
        
        result = conn.query(query,db=db)
        diagnosis_exist = False
        if result:
            text = f"[CONFIDENTIAL] Patient {patient_id}'s previous diagnosis: "
            for idx, val in enumerate(result):
                visit_number = result[idx]["visit_number"]
                text = text + f"\n[VISIT {str(visit_number-int(count)+idx+1)} of {str(visit_number)}]:"
                diagnosis = result[idx]["diagnosis"]
                if diagnosis:
                    diagnosis_exist = True
                    for num, diag in enumerate(result[idx]["diagnosis"]):
                        text = text + f"\n- Diagnosis {num+1}."
                        for lvl, diag_level in enumerate(diag.split("|")):
                            text = text + f"\n-- Level {lvl+1}: {diag_level.title()}"
                else:
                    text = text + " NONE"
            
            if diagnosis_exist == False:
                text = "Patient does not have any previous diagnosis"
    else:
        query = f"""MATCH(p:Patient{{patient_id:'{patient_id}'}})-[:HAS_STAY]->(n:PatientUnitStay)
        OPTIONAL MATCH (n)-[:HAS_DIAG]->(d:Diagnosis)
        WITH COUNT(DISTINCT n) AS visit_number
        MATCH(p:Patient{{patient_id:'{patient_id}'}})-[:HAS_STAY]->(n:PatientUnitStay)
        OPTIONAL MATCH (n)-[:HAS_DIAG]->(d:Diagnosis)
        WITH n.hospitaladmitoffset AS visit_order, collect(d.diagnosisstring) AS diagnosis, visit_number
        RETURN visit_order, diagnosis, visit_number
        ORDER BY visit_order"""
        
        result = conn.query(query,db=db)
        
        diagnosis_exist = False
        if result:
            
            text = f"[CONFIDENTIAL] Patient {patient_id}'s previous diagnosis: "
            for idx, val in enumerate(result):
                visit_number = result[idx]["visit_number"]
                text = text + f"\n[VISIT {str(idx+1)} of {str(visit_number)}]:"
                diagnosis = result[idx]["diagnosis"]
                if diagnosis:
                    diagnosis_exist = True
                    for num, diag in enumerate(result[idx]["diagnosis"]):
                        text = text + f"\n- Diagnosis {num+1}."
                        for lvl, diag_level in enumerate(diag.split("|")):
                            text = text + f"\n-- Level {lvl+1}: {diag_level.title()}"
                    
                else:
                    text = text + " NONE"
        else:
            text = f"[CONFIDENTIAL] Patient {patient_id} does not have previous diagnosis"
        
        if diagnosis_exist == False:
            text = f"[CONFIDENTIAL] Patient does not have any previous diagnosis"
        
    message =  {
            'contentType': 'PlainText',
            'content': text
        }
    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)

def ask_for_readings(intent_request, conn, db):
    session_attributes = get_session_attributes(intent_request)
    
    slots = get_slots(intent_request)
    patient_id = get_slot(intent_request, 'name').title()
    lab = get_slot(intent_request, 'lab').lower()
    lab_title = lab.title()

    query = f"""MATCH(p:Patient{{patient_id:'{patient_id}'}})-[:HAS_STAY]->(n:PatientUnitStay)-[:HAS_LAB]->(l:Lab)
    WHERE l.{lab} <>0
    WITH n.hospitaladmitoffset AS visit_order, l.{lab} AS {lab}
    ORDER BY visit_order, {lab}
    RETURN visit_order, collect({lab}) AS {lab_title}
    ORDER BY visit_order, {lab_title}"""
    
    result = conn.query(query,db=db)
    
    if result:
        text = f"[CONFIDENTIAL] Patient {patient_id}'s {lab_title} reading(s): "
        for idx, val in enumerate(result):
            text = text + f"\n[VISIT {idx+1}]:"
            for num, reading in enumerate(result[idx][lab_title]):
                text = text + f"\n- Reading {num+1}: {reading}"
    else:
        text = f"[CONFIDENTIAL] Patient {patient_id} has not yet tested for {lab_title} reading"
    
    message =  {
            'contentType': 'PlainText',
            'content': text
        }
    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)

def test(intent_request,):
    session_attributes = get_session_attributes(intent_request)
    
    slots = get_slots(intent_request)
    
    message =  {
            'contentType': 'PlainText',
            'content': "Yes, I am online."
        }
    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)

def hello(intent_request, conn, db):
    session_attributes = get_session_attributes(intent_request)
    
    slots = get_slots(intent_request)
    # input_doctor_name = get_slot(intent_request, 'doctor_name').title()
    # input_doctor_name = re.sub(r"[^a-zA-Z0-9]","",input_doctor_name)
    
    # query = f"MATCH (d:Doctor{{nickname:'{input_doctor_name}'}}) RETURN d.name AS doctor_name, d.nickname AS nickname"
    # result = conn.query(query,db=db)
    # result_doctor_name = None
    # if result:
    #     result_doctor_name = result[0]["doctor_name"]
    
    # if result_doctor_name:
    #     text = f"Welcome back, {result_doctor_name}! How can I help?"
    # else:
    #     raise Exception(f'{result_doctor_name} does not exist!')
    message =  {
            'contentType': 'PlainText',
            'content': "Hello. How can I help?"
        }
    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)

def ask_patient_record(intent_request, conn, db):
    session_attributes = get_session_attributes(intent_request)
    
    slots = get_slots(intent_request)
    name = get_slot(intent_request, 'name').title()
    patient_name = get_slot(intent_request, 'patient_name').title()
    
    if name != patient_name:
        raise Exception(f'{patient_name} does not exist!')
    
    query = f"""MATCH(p:Patient{{patient_id:'{patient_name}'}})-[]-(n)-[:HAS_MICROLAB]->(m:MicroLab{{organism:'Staphylococcus aureus'}})
    RETURN DISTINCT m.organism as organism"""
    
    result = conn.query(query,db=db)
    organism = result[0]["organism"]
    
    if organism:
        text = f"Patient {patient_name} have {organism}."
    else:
        raise Exception(f'No record exists!')
    message =  {
            'contentType': 'PlainText',
            'content': text
        }
    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)

def ask_patient_ethnicity(intent_request, conn, db):
    session_attributes = get_session_attributes(intent_request)
    
    slots = get_slots(intent_request)
    name = get_slot(intent_request, 'name').title()
    
    query = f"""MATCH(p:Patient{{patient_id:'{name}'}})
    RETURN p.ethnicity as ethnicity"""
    
    result = conn.query(query,db=db)
    ethnicity = result[0]["ethnicity"]
    
    if ethnicity:
        text = f"Patient {name} has {ethnicity} ethnicity."
    else:
        raise Exception(f'Not authorized!')
    message =  {
            'contentType': 'PlainText',
            'content': text
        }
    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)
    
def ask_infection_organism(intent_request, conn, db):
    session_attributes = get_session_attributes(intent_request)
    
    slots = get_slots(intent_request)
    patient_id = get_slot(intent_request, 'name').title()
    
    if get_slot(intent_request, 'count'):
        count = get_slot(intent_request, 'count')
        query = f"""MATCH(p:Patient{{patient_id:'{patient_id}'}})-[:HAS_STAY]->(n:PatientUnitStay)
        OPTIONAL MATCH (n)-[:HAS_MICROLAB]->(d:MicroLab)
        WITH COUNT(DISTINCT n) AS visit_number
        MATCH(p:Patient{{patient_id:'{patient_id}'}})-[:HAS_STAY]->(n:PatientUnitStay)
        OPTIONAL MATCH (n)-[:HAS_MICROLAB]->(d:MicroLab)
        WITH n.hospitaladmitoffset AS visit_order, collect(DISTINCT d.organism) AS organism, visit_number
        ORDER BY visit_order DESC
        LIMIT {count}
        RETURN visit_order, organism, visit_number
        ORDER BY visit_order
        """
        
        result = conn.query(query,db=db)
        diagnosis_exist = False
        if result:
            text = f"[CONFIDENTIAL] Patient {patient_id}'s previous organism: "
            for idx, val in enumerate(result):
                visit_number = result[idx]["visit_number"]
                text = text + f"\n[VISIT {str(visit_number-int(count)+idx+1)} of {str(visit_number)}]:"
                organism = result[idx]["organism"]
                if organism:
                    diagnosis_exist = True
                    for num, org in enumerate(result[idx]["organism"]):
                        text = text + f"\n- Organism {num+1}: {org.title()}"
                else:
                    text = text + " NONE"
            
            if diagnosis_exist == False:
                text = "Patient does not have any previous organisms detected."
    else:
        query = f"""MATCH(p:Patient{{patient_id:'{patient_id}'}})-[:HAS_STAY]->(n:PatientUnitStay)
        OPTIONAL MATCH (n)-[:HAS_MICROLAB]->(d:MicroLab)
        WITH COUNT(DISTINCT n) AS visit_number
        MATCH(p:Patient{{patient_id:'{patient_id}'}})-[:HAS_STAY]->(n:PatientUnitStay)
        OPTIONAL MATCH (n)-[:HAS_MICROLAB]->(d:MicroLab)
        WITH n.hospitaladmitoffset AS visit_order, collect(DISTINCT d.organism) AS organism, visit_number
        RETURN visit_order, organism, visit_number
        ORDER BY visit_order"""
        
        result = conn.query(query,db=db)
        
        diagnosis_exist = False
        if result:
            
            text = f"[CONFIDENTIAL] Patient {patient_id}'s previous organism: "
            for idx, val in enumerate(result):
                visit_number = result[idx]["visit_number"]
                text = text + f"\n[VISIT {str(idx+1)} of {str(visit_number)}]:"
                organism = result[idx]["organism"]
                if organism:
                    diagnosis_exist = True
                    for num, org in enumerate(result[idx]["organism"]):
                        text = text + f"\n- Organism {num+1}: {org.title()}"
                    
                else:
                    text = text + " NONE"
        else:
            text = f"[CONFIDENTIAL] Patient {patient_id} does not have previous organism detected"
        
        if diagnosis_exist == False:
            text = f"[CONFIDENTIAL] Patient does not have any previous organism detected"
        
    message =  {
            'contentType': 'PlainText',
            'content': text
        }
    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)

def recommend_patient_treatment(intent_request, conn, db):
    session_attributes = get_session_attributes(intent_request)
    
    slots = get_slots(intent_request)
    patient_id = get_slot(intent_request, 'name').title()
    
    query = f"""MATCH (p:Patient {{patient_id: '{patient_id}'}})-[:HAS_STAY]->(ps:PatientUnitStay)-[r:HAS_LAB]->(l:Lab)
    match (:Patient {{patient_id: '{patient_id}'}})-[:HAS_STAY]->(ps:PatientUnitStay)-[:HAS_TREATMENT]->(tr:Treatment)
    MATCH (p2:Patient) where abs(p2.age - p.age) < 10 and p2.gender = p.gender
    MATCH (p2)-[:HAS_STAY]->(ps2:PatientUnitStay)-[:HAS_LAB]->(l2:Lab)
    with p.patient_id as pid,tr.treatmentstring as trea_string, p2.patient_id as p2id,
    gds.alpha.similarity.cosine([
     l.albumin,
     l.bilirubin,
     l.BUN,
     l.calcium,
     l.creatinine,
     l.glucose,
     l.bicarbonate,
     l.TotalCO2,
     l.hematocrit,
     l.hemoglobin,
     l.INR,
     l.lactate,
     l.platelets,
     l.potassium,
     l.ptt,
     l.sodium,
     l.wbc,
     l.bands,
     l.alt,
     l.ast,
     l.alp
    ],
    [
     l2.albumin,
     l2.bilirubin,
     l2.BUN,
     l2.calcium,
     l2.creatinine,
     l2.glucose,
     l2.bicarbonate,
     l2.TotalCO2,
     l2.hematocrit,
     l2.hemoglobin,
     l2.INR,
     l2.lactate,
     l2.platelets,
     l2.potassium,
     l2.ptt,
     l2.sodium,
     l2.wbc,
     l2.bands,
     l2.alt,
     l2.ast,
     l2.alp
    ]) as similarity
    where similarity > 0.9
    match (p2:Patient {{patient_id: p2id}})-[:HAS_STAY]->(ps:PatientUnitStay)-[:HAS_TREATMENT]->(tr2:Treatment)
    where exists(tr2.treatmentid) and trea_string <> tr2.treatmentstring
    and split(tr2.treatmentstring,'|')[0]=split(trea_string,'|')[0]
    and split(tr2.treatmentstring,'|')[1]=split(trea_string,'|')[1]
    return DISTINCT tr2.treatmentstring as treatment limit 3"""
    
    result = conn.query(query,db=db)
    
    if result:
        text = f"[CONFIDENTIAL] Patient {patient_id}'s potential treatment options: "
        for idx, val in enumerate(result):
            treatments = result[idx]["treatment"]
            text = text + f"\n[POSSIBLE TREATMENT {str(idx+1)}]: {treatments.split('|')[-1].title()}"
    else:
        raise Exception(f'Not recommend treatment!')
    message =  {
            'contentType': 'PlainText',
            'content': text
        }
    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)
