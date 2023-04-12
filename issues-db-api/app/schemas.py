dl_models_collection_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["name", "config", "versions", "performances"],
        "properties": {
            "_id": {
                "bsonType": "objectId",
                "description": "'_id' must be a objectId"
            },
            "name": {
                "bsonType": "string",
                "description": "'name' must be a string"
            },
            "config": {
                "bsonType": "object",
                "description": "'config' must be an object"
            },
            "versions": {
                "bsonType": "array",
                "description": "'versions' must be an array",
                "items": {
                    "bsonType": ["object", "null"],
                    "description": "'version' must be an object",
                    "additionalProperties": False,
                    "required": ["id", "time"],
                    "properties": {
                        "id": {
                            "bsonType": "objectId",
                            "description": "'version_id' must be an objectId"
                        },
                        "time": {
                            "bsonType": "string",
                            "description": "'version_time' must be a string"
                        }
                    }
                }
            },
            "performances": {
                "bsonType": "object",
                "description": "'performances' must be an object"
            }
        }
    }
}

embeddings_collection_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "properties": {
            "_id": {
                "bsonType": "objectId",
                "description": "'_id' must be a objectId"
            },
            "name": {
                "bsonType": "string",
                "description": "'name' must be a string"
            },
            "config": {
                "bsonType": "object",
                "description": "'config' must be an object"
            },
            "file_id": {
                "bsonType": ["objectId", "null"],
                "description": "'type' must be an objectId"
            }
        }
    }
}

issue_labels_collection_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "properties": {
            "_id": {
                "bsonType": "string",
                "description": "'_id' must be a string"
            },
            "existence": {
                "bsonType": "bool",
                "description": "'existence' must be a boolean"
            },
            "property": {
                "bsonType": "bool",
                "description": "'property' must be a boolean"
            },
            "executive": {
                "bsonType": "bool",
                "description": "'executive' must be a boolean"
            },
            "tags": {
                "bsonType": "array",
                "description": "'tags' must be an array of strings",
                "uniqueItems": True,
                "items": {
                    "bsonType": "string",
                    "description": "a 'tag' must be a string"
                }
            },
            "comments": {
                "bsonType": "object",
                "additionalProperties": {
                    "bsonType": "object",
                    "additionalProperties": False,
                    "required": ["author", "comment"],
                    "properties": {
                        "author": {
                            "bsonType": "string",
                            "description": "'author' must be a string"
                        },
                        "comment": {
                            "bsonType": "string",
                            "description": "'comment' must be a string"
                        }
                    }
                }
            },
            "predictions": {
                "bsonType": "object",
                "additionalProperties": {
                    "bsonType": "object",
                    "additionalProperties": {
                        "bsonType": "object",
                        "required": ["prediction", "confidence"],
                        "properties": {
                            "prediction": {
                                "bsonType": "bool",
                                "description": "'prediction' must be a bool"
                            },
                            "confidence": {
                                "bsonType": "double",
                                "description": "'confidence' must be a double"
                            }
                        }
                    }
                }
            }
        }
    }
}

issue_links_collection_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "properties": {
            "_id": {
                "bsonType": "string",
                "description": "'_id' must be a string"
            },
            "link": {
                "bsonType": "string",
                "description": "'link' must be a string"
            }
        }
    }
}


projects_collection_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "required": ["repo", "project"],
        "properties": {
            "_id": {
                "bsonType": "string",
                "description": "'_id' must be a string"
            },
            "repo": {
                "bsonType": "string",
                "description": "'_id' must be a string"
            },
            "project": {
                "bsonType": "string",
                "description": "'_id' must be a string"
            }
        }
    }
}


tags_collection_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "properties": {
            "_id": {
                "bsonType": "string",
                "description": "'_id' must be a string"
            },
            "description": {
                "bsonType": "string",
                "description": "'description' must be a string"
            },
            "type": {
                "bsonType": "string",
                "description": "'type' must be a string"
            }
        }
    }
}

users_collection_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "additionalProperties": False,
        "properties": {
            "_id": {
                "bsonType": "string",
                "description": "'_id' must be a string"
            },
            "hashed_password": {
                "bsonType": "string",
                "description": "'hashed_password' must be a string"
            }
        }
    }
}
