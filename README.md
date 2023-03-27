# Setup
```
docker compose up --build -d

docker cp ./mongodump-JiraRepos_2023-03-07-16:00.archive mongo:/mongodump-JiraRepos.archive
docker exec -i mongo mongorestore --gzip --archive=mongodump-JiraRepos.archive --nsFrom "JiraRepos.*" --nsTo "JiraRepos.*"

docker cp ./mongodump-IssueLabels.archive mongo:/mongodump-IssueLabels.archive
docker exec -i mongo mongorestore --gzip --archive=mongodump-IssueLabels.archive --nsFrom "IssueLabels.*" --nsTo "IssueLabels.*"

python3.10 -m venv venv
source venv/bin/activate
pip install pymongo
python3.10 setup.py
```

# Download JiraRepos

```
pip install gdown
gdown file-id
```

# Dump data

## IssueLabels
```
docker exec -i mongo mongodump --db=IssueLabels --gzip --archive=mongodump-IssueLabels.archive
docker cp mongo:mongodump-IssueLabels.archive ./mongodump-IssueLabels.archive
```

## JiraRepos
```
docker exec -i mongo mongodump --db=JiraRepos --gzip --archive=mongodump-JiraRepos.archive
docker cp mongo:mongodump-JiraRepos.archive ./mongodump-JiraRepos.archive
```

# Restore data

## IssueLabels
```
docker cp ./mongodump-IssueLabels.archive mongo:/mongodump-IssueLabels.archive
docker exec -i mongo mongorestore --gzip --archive=mongodump-IssueLabels.archive --nsFrom "IssueLabels.*" --nsTo "IssueLabels.*"
```

## JiraRepos
```
docker cp ./mongodump-JiraRepos.archive mongo:/mongodump-JiraRepos.archive
docker exec -i mongo mongorestore --gzip --archive=mongodump-JiraRepos.archive --nsFrom "JiraRepos.*" --nsTo "JiraRepos.*"
```

# SSH Tunneling

```
ssh -L 8081:issues-db.nl:8081 arjan@issues-db.nl
```

# SSL

```
sudo cp /etc/letsencrypt/live/issues-db.nl/fullchain.pem issues-db-api/fullchain.pem
sudo cp /etc/letsencrypt/live/issues-db.nl/privkey.pem issues-db-api/privkey.pem
```
