import pymongo
import json

# MongoDB connection details
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
labels_db = mongo_client["JiraRepos"]
labels_collection = labels_db["Apache"]

# Fetch a sample of 300 documents
sample_size = 300
pipeline = [{"$sample": {"size": sample_size}}]
sample_documents = list(labels_collection.aggregate(pipeline))

# Save the sample to a JSON file
with open('sample_300.json', 'w') as json_file:
    json.dump(sample_documents, json_file, default=str, indent=4)

print(f"A sample of {sample_size} documents has been saved to 'sample_300.json'.")
