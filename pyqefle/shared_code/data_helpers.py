from pymongo import MongoClient
from dotenv import load_dotenv
import shared_code.qe_helpers as helpers
import os

if os.environ["AzureWebJobsStorage"] == "UseDevelopmentStorage=true":
    load_dotenv()

def read_data() -> str:
    uri =  os.environ['MONGODB_URI']
    encrypt_client = MongoClient(uri)
    db = encrypt_client.medicalRecords
    collection = db['patients']
    o = collection.find_one()
    return f"{o['patientName']}"

def encrypt_data_field(name: str) -> str:
    
    kms_provider_name = "azure"

    uri = os.environ['MONGODB_URI']  # Your connection URI

    key_vault_database_name = "encryption"
    key_vault_collection_name = "__keyVault"
    key_vault_namespace = f"{key_vault_database_name}.{key_vault_collection_name}"
    encrypted_database_name = "medicalRecords"
    encrypted_collection_name = "patients"

    kms_provider_credentials = helpers.get_kms_provider_credentials(
        kms_provider_name)
    customer_master_key_credentials = helpers.get_customer_master_key_credentials(
        kms_provider_name)

    auto_encryption_options = helpers.get_auto_encryption_options(
        kms_provider_name,
        key_vault_namespace,
        kms_provider_credentials,
    )

    # start-create-client
    encrypted_client = MongoClient(
        uri, auto_encryption_opts=auto_encryption_options)
    # end-create-client

    encrypted_client[key_vault_database_name][key_vault_collection_name].drop()
    encrypted_client[encrypted_database_name][encrypted_collection_name].drop()

    # start-encrypted-fields-map
    encrypted_fields_map = {
        "fields": [
            {
                "path": "patientRecord.ssn",
                "bsonType": "string",
                "queries": [{"queryType": "equality"}]
            },
            {
                "path": "patientRecord.billing",
                "bsonType": "object",
            }
        ]
    }
    # end-encrypted-fields-map

    client_encryption = helpers.get_client_encryption(
        encrypted_client,
        kms_provider_name,
        kms_provider_credentials,
        key_vault_namespace
    )

    try:
        # start-create-encrypted-collection
        client_encryption.create_encrypted_collection(
            encrypted_client[encrypted_database_name],
            encrypted_collection_name,
            encrypted_fields_map,
            kms_provider_name,
            customer_master_key_credentials,
        )
        # end-create-encrypted-collection
    except Exception as e:
        raise Exception("Unable to create encrypted collection due to the following error: ", e)

    # start-insert-document
    patient_document = {
        "patientName": name,
        "patientId": 12345678,
        "patientRecord": {
            "ssn": "987-65-4320",
            "billing": {
                "type": "Visa",
                "number": "4111111111111111",
            },
        },
    }

    encrypted_collection = encrypted_client[encrypted_database_name][encrypted_collection_name]

    result = encrypted_collection.insert_one(patient_document)
    # end-insert-document
    if result.acknowledged:
        print("Successfully inserted the patient document.")