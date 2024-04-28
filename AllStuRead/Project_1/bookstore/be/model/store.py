import pymongo

class Store:
    client = None
    database = None

    def __init__(self):
        self.client = pymongo.MongoClient('mongodb://localhost:27017')
        self.database = self.client.bookstore1
        self.init_collections()

    def init_collections(self):
        self.database["user"].create_index([("user_id", pymongo.ASCENDING)])
        self.database["user_store"].create_index([("user_id", pymongo.ASCENDING), ("store_id", pymongo.ASCENDING)])
        self.database["store"].create_index([("book_id", pymongo.ASCENDING), ("store_id", pymongo.ASCENDING)])

    def get_db_conn(self):
        return self.database


def init_database():
    return Store()


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn() if database_instance else init_database().get_db_conn()

database_instance = init_database()
