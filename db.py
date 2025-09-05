from pymongo import MongoClient
from config import MONGO_DB_URI

client = MongoClient(MONGO_DB_URI)
db = client["autofilter_db"]
files = db.files

def add_file(file_info):
    files.replace_one({"file_id": file_info["file_id"]}, file_info, upsert=True)

def search_files(query):
    return list(files.find(
        {"$or": [
            {"file_name": {"$regex": query, "$options": "i"}},
            {"caption": {"$regex": query, "$options": "i"}}
        ]}
    ))

def get_file_by_id(doc_id):
    from bson.objectid import ObjectId
    return files.find_one({"_id": ObjectId(doc_id)})

def file_count():
    return files.count_documents({})
