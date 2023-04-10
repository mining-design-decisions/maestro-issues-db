import os
from pymongo import MongoClient
import gridfs

if os.environ.get('DOCKER', False):
    mongo_client = MongoClient(os.environ['MONGO_URL'])
else:
    mongo_client = MongoClient('mongodb://localhost:27017')

jira_repos_db = mongo_client['JiraRepos']
mining_add_db = mongo_client['MiningDesignDecisions']
fs = gridfs.GridFS(mongo_client['MiningDesignDecisions'])

manual_labels_collection = mongo_client['MiningDesignDecisions']['IssueLabels']
issue_links_collection = mongo_client['MiningDesignDecisions']['IssueLinks']
tags_collection = mongo_client['MiningDesignDecisions']['Tags']
projects_collection = mongo_client['MiningDesignDecisions']['Projects']
model_collection = mongo_client['MiningDesignDecisions']['DLModels']
embeddings_collection = mongo_client['MiningDesignDecisions']['DLEmbeddings']
users_collection = mongo_client['Users']['Users']
