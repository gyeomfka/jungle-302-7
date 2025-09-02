from config import get_config
from pymongo import MongoClient

cfg = get_config()

def get_db():
    mongo_uri = getattr(cfg, "MONGO_URI", cfg.MONGO_URI)

    print(cfg.MONGO_URI)
    client = MongoClient(
        mongo_uri,
        27017
    )
    return client['kaeal-study']
