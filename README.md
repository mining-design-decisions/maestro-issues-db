# Setup
```
docker compose up --build -d

docker cp ./mongodump-JiraRepos_2023-03-07-16:00.archive mongo:/mongodump-JiraRepos.archive
docker exec -i mongo mongorestore --gzip --archive=mongodump-JiraRepos.archive --nsFrom "JiraRepos.*" --nsTo "JiraRepos.*"

docker cp ./mongodump-MiningDesignDecisions.archive mongo:/mongodump-MiningDesignDecisions.archive
docker exec -i mongo mongorestore --gzip --archive=mongodump-MiningDesignDecisions.archive --nsFrom "MiningDesignDecisions.*" --nsTo "MiningDesignDecisions.*"

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

## MiningDesignDecisions
```
docker exec -i mongo mongodump --db=MiningDesignDecisions --gzip --archive=mongodump-MiningDesignDecisions.archive
docker cp mongo:mongodump-MiningDesignDecisions.archive ./mongodump-MiningDesignDecisions.archive
```

## JiraRepos
```
docker exec -i mongo mongodump --db=JiraRepos --gzip --archive=mongodump-JiraRepos.archive
docker cp mongo:mongodump-JiraRepos.archive ./mongodump-JiraRepos.archive
```

# Restore data

## MiningDesignDecisions
```
docker cp ./mongodump-MiningDesignDecisions.archive mongo:/mongodump-MiningDesignDecisions.archive
docker exec -i mongo mongorestore --gzip --archive=mongodump-MiningDesignDecisions.archive --nsFrom "MiningDesignDecisions.*" --nsTo "MiningDesignDecisions.*"
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
