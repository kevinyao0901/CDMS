from pymongo import MongoClient

# 连接 MongoDB 数据库
client = MongoClient('localhost', 27017)
db = client['book']

# 创建文档模板
user_template = {
    "user_id": "",
    "password": "",
    "balance": 0,
    "token": "",
    "terminal": ""
}

user_store_template = {
    "user_id": "",
    "store_id": ""
}

store_template = {
    "store_id": "",
    "book_id": "",
    "book_info": "",
    "stock_level": 0
}

new_order_template = {
    "order_id": "",
    "user_id": "",
    "store_id": ""
}

order_history_template = {
    "order_id": "",
    "user_id": "",
    "store_id": ""
}

new_order_detail_template = {
    "order_id": "",
    "user_id": "",
    "store_id": "",
    "book_id": "",
    "quantity": 0,
    "price": 0
}

order_history_detail_template = {
    "order_id": "",
    "book_id": "",
    "quantity": 0,
    "price": 0
}

books_template = {
    "id": "",
    "title": "",
    "author": "",
    "publisher": "",
    "original_title": "",
    "translator": "",
    "pub_year": "",
    "pages": 0,
    "price": 0,
    "currency_unit": "",
    "binding": "",
    "isbn": "",
    "author_intro": "",
    "book_intro": "",
    "content": "",
    "tags": [],
    "picture": ""
}

# 创建文档集合并插入空白文档作为模板
user_collection = db['user']
user_collection.insert_one(user_template)

user_store_collection = db['user_store']
user_store_collection.insert_one(user_store_template)

store_collection = db['store']
store_collection.insert_one(store_template)

new_order_collection = db['new_order']
new_order_collection.insert_one(new_order_template)

order_history_collection = db['order_history']
order_history_collection.insert_one(order_history_template)

new_order_detail_collection = db['new_order_detail']
new_order_detail_collection.insert_one(new_order_detail_template)

order_history_detail_collection = db['order_history_detail']
order_history_detail_collection.insert_one(order_history_detail_template)

books_collection = db['books']
books_collection.insert_one(books_template)

print("文档集合创建完成。")
