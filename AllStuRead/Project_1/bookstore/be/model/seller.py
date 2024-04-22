#import sqlite3 as sqlite
from be.model import error
from be.model import db_conn
import pymongo

class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(
        self,
        user_id: str,
        store_id: str,
        book_id: str,
        book_json_str: str,
        stock_level: int,
    ):
        try:
            if not self.user_id_exist(user_id) or not self.store_id_exist(store_id) or self.book_id_exist(store_id, book_id):
                return 400, "Invalid request parameters"  

            book_doc = {
                'store_id': store_id,
                'book_id': book_id,
                'book_info': book_json_str,
                'stock_level': stock_level,
            }
            self.conn['store'].insert_one(book_doc)
        except pymongo.errors.PyMongoError as e:
            return 500, str(e)  
        return 200, "ok"  


    def add_stock_level(
        self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            if not all([
                self.user_id_exist(user_id),
                self.store_id_exist(store_id),
                self.book_id_exist(store_id, book_id)
            ]):
                return 400, "Invalid request parameters"  

            self.conn['store'].update_one(
                {'store_id': store_id, 'book_id': book_id},
                {'$inc': {'stock_level': add_stock_level}},
            )
        except pymongo.errors.PyMongoError as e:
            return 500, str(e)  
        return 200, "ok"  


    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return 400, "User does not exist"

            if self.store_id_exist(store_id):
                return 400, "Store ID already exists"

            user_store_doc = {
                'store_id': store_id,
                'user_id': user_id,
            }
            self.conn['user_store'].insert_one(user_store_doc)
        except pymongo.errors.PyMongoError as e:
            return 500, str(e)  
        return 200, "Store created successfully" 


    def ship_order(self, user_id: str, store_id: str, order_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return 400, "User does not exist"
            if not self.store_id_exist(store_id):
                return 400, "Store does not exist"

            order = self.conn['order_history'].find_one({'order_id': order_id})
            if not order:
                return 400, "Invalid order ID"
            if order['status'] != 'paid':
                return 400, "Order is not paid"

            self.conn['order_history'].update_one(
                {'order_id': order_id},
                {'$set': {'status': 'shipped'}},
            )
        except pymongo.errors.PyMongoError as e:
            return 500, str(e)  
        return 200, "Order shipped successfully"  
