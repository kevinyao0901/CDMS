import sqlite3
import pymongo

# 连接到 SQLite 数据库
sqlite_conn = sqlite3.connect(r'D:\当代数据管理系统\project 1\bookstore\fe\data\book.db')
sqlite_cursor = sqlite_conn.cursor()

# 连接到 MongoDB
mongo_client = pymongo.MongoClient('mongodb://localhost:27017')
mongo_db = mongo_client['bookstore1']

# 查询 SQLite 数据
sqlite_cursor.execute('SELECT * FROM book')
rows = sqlite_cursor.fetchall()

# 将数据插入到 MongoDB
for row in rows:
    mongo_db.books.insert_one({
        'id': row[0],
        'title': row[1],
        'author': row[2],
        'publisher': row[3],
        'original_title': row[4],
        'translator': row[5],
        'pub_year': row[6],
        'pages': row[7],
        'price': row[8],
        'currency_unit': row[9],
        'binding': row[10],
        'isbn': row[11],
        'author_intro': row[12],
        'book_intro': row[13],
        'content': row[14],
        'tags': row[15],
        'picture': row[16],
    })

# 关闭连接
sqlite_conn.close()
mongo_client.close()
