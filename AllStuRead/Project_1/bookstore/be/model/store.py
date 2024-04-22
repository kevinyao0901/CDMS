# import logging
# import os
# import sqlite3 as sqlite
import pymongo


class Store:
    client = None
    database = None

    def __init__(self):
        self.client = pymongo.MongoClient('mongodb://localhost:27017')
        self.database = self.client.bookstore1
        self.init_collections()

    def init_collections(self):
        # user_collection = self.database["user"]
        # user_store_collection = self.database["user_store"]
        # store_collection = self.database["store"]
        # order_collection = self.database["new_order"]
        # order_detail_collection = self.database["new_order_detail"]
        self.database["user"].create_index([("user_id", pymongo.ASCENDING)])
        self.database["user_store"].create_index([("user_id", pymongo.ASCENDING), ("store_id", pymongo.ASCENDING)])
        self.database["store"].create_index([("book_id", pymongo.ASCENDING), ("store_id", pymongo.ASCENDING)])

    def get_db_conn(self):
        return self.database


database_instance: Store = None


def init_database():
    global database_instance
    database_instance = Store()


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()
