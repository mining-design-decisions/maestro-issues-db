import os
from pymongo import MongoClient

# mongo_client = MongoClient('mongodb://localhost:27017')
mongo_client = MongoClient(os.environ['MONGO_URL'])
manual_labels_collection = mongo_client['IssueLabels']['ManualLabels']
jira_repos_db = mongo_client['JiraRepos']
