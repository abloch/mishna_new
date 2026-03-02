import json

from google.cloud import storage


def get_blob(config):
    bucket_name = config.get('GOOGLE_STORAGE_BUCKET')
    blob_name = config.get('SERIALZIZATION_FILENAME')
    print(f"Getting blob {blob_name} from bucket {bucket_name}")
    if not bucket_name or not blob_name:
        raise ValueError("Missing required configuration values")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.get_blob(blob_name)
    return blob

def get_blob_as_dict(config):
    blob = get_blob(config)
    content = blob.download_as_text()
    return json.loads(content)

def save_dict_as_blob(config, data):
    blob = get_blob(config)
    blob.upload_from_string(json.dumps(data))
