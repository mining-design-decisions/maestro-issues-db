import pymongo
import json
from bson import ObjectId

# MongoDB connection details
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")

# Issue collection details
issue_db = mongo_client["JiraRepos"]
issue_collection = issue_db["Apache"]

# IssueLabels collection details
labels_db = mongo_client["MiningDesignDecisions"]
labels_collection = labels_db["IssueLabels"]

# Aggregation pipeline
pipeline = [
    {"$sample": {"size": 300}},
    {
        "$lookup": {
            "from": "IssueLabels",
            "localField": "key",
            "foreignField": "_id",
            "as": "issueDetails"
        }
    },
    {"$unwind": {"path": "$issueDetails", "preserveNullAndEmptyArrays": True}}
]

# Run aggregation
result = list(issue_collection.aggregate(pipeline))

# Convert ObjectId to string for JSON serialization
def convert_objectid(data):
    if isinstance(data, list):
        return [convert_objectid(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_objectid(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data

result = convert_objectid(result)

# Export to JSON
with open("joined_data.json", "w") as json_file:
    json.dump(result, json_file, indent=4)

print("Data has been exported to joined_data.json")
