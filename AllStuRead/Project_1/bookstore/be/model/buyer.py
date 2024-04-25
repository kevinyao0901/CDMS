#import sqlite3 as sqlite
import uuid
import json
import logging
import pymongo
import threading
from be.model import db_conn
from be.model import error


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(
            self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            order_details = []
            
            for book_id, count in id_and_count:
                book = self.conn["store"].find_one({"store_id": store_id, "book_id": book_id})
                if not book:
                    return error.error_non_exist_book_id(book_id) + (order_id,)
                stock_level = book["stock_level"]
                if stock_level - count < 0:
                    return error.error_stock_level_low(book_id) + (order_id,)

                # 更新库存
                query = {"book_id": book_id, "store_id": store_id, "stock_level": {"$gte": count}}
                update = {"$inc": {"stock_level": -count}}
                result = self.conn["store"].update_one(query, update)
                
                if result.modified_count == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)

                # 计算价格
                book_info = json.loads(book["book_info"])
                price = book_info.get("price")
                new_order_detail = {
                    "order_id": uid,
                    "book_id": book_id,
                    "count": count,
                    "price": price
                }
                order_details.append(new_order_detail)

            # 插入订单详情
            if len(order_details) > 0:
                self.conn["new_order_detail"].insert_many(order_details)

            # 插入订单
            order = {"order_id": uid, "user_id": user_id, "store_id": store_id}
            self.conn["new_order"].insert_one(order)
            order_id = uid
            
            # 新功能：取消订单
            # 延迟队列
            timer = threading.Timer(60.0, self.cancel_order, args=[user_id, order_id])
            timer.start()
            
            #新功能：历史订单
            # 存入历史订单
            order["status"] = "pending"
            self.conn["order_history"].insert_one(order)
            self.conn["order_history_detail"].insert_many(order_details)

        except pymongo.errors.PyMongoError as e:
            logging.error("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            conn = self.conn

            # 查找订单
            order = conn["new_order"].find_one({"order_id": order_id})
            if not order:
                return error.error_invalid_order_id(order_id)

            # 检查订单是否属于当前用户
            if order["user_id"] != user_id:
                return error.error_authorization_fail()

            # 查找买家信息
            buyer = conn["user"].find_one({"user_id": user_id})
            if not buyer:
                return error.error_non_exist_user_id(user_id)

            # 检查密码是否正确
            if password != buyer["password"]:
                return error.error_authorization_fail()

            # 检查余额是否足够支付订单
            total_price = sum(detail["price"] * detail["count"] for detail in conn["new_order_detail"].find({"order_id": order_id}))
            if buyer["balance"] < total_price:
                return error.error_not_sufficient_funds(order_id)

            # 更新买家余额
            result = conn["user"].update_one({"user_id": user_id, "balance": {"$gte": total_price}}, {"$inc": {"balance": -total_price}})
            if result.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            # 更新卖家余额
            seller_id = conn["user_store"].find_one({"store_id": order["store_id"]})["user_id"]
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)
            result = conn["user"].update_one({"user_id": seller_id}, {"$inc": {"balance": total_price}})
            if result.modified_count == 0:
                return error.error_non_exist_user_id(seller_id)

            # 删除订单及订单详情
            conn["new_order"].delete_one({"order_id": order_id})
            conn["new_order_detail"].delete_many({"order_id": order_id})

            # 更新订单状态
            conn["order_history"].update_one({"order_id": order_id}, {"$set": {"status": "paid"}})

        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except BaseException as e:
            return 530, str(e)

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            conn = self.conn

            # 查找用户并验证密码
            user = conn["user"].find_one({"user_id": user_id})
            if not user or user["password"] != password:
                return error.error_authorization_fail()

            # 更新余额
            result = conn["user"].update_one({"user_id": user_id}, {"$inc": {"balance": add_value}})
            if result.modified_count == 0:
                return error.error_non_exist_user_id(user_id)

        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except BaseException as e:
            return 530, str(e)

        return 200, "ok"
    
    def get_order_history(self, user_id: str) -> (int, str, [dict]):
        try:
            conn = self.conn

            # 查询用户的订单
            orders = conn["order_history"].aggregate([
                {"$match": {"user_id": user_id}},
                {"$lookup": {
                    "from": "order_history_detail",
                    "localField": "order_id",
                    "foreignField": "order_id",
                    "as": "order_details"
                }}
            ])

            # 如果用户没有订单，返回错误信息和空订单列表
            if not orders:
                return error.error_non_exist_user_id(user_id) + ([],)

            # 构建订单列表
            order_list = []
            for order in orders:
                order_id = order["order_id"]
                order_detail_list = []

                # 构建订单详情列表
                for detail in order["order_details"]:
                    book_id = detail["book_id"]
                    count = detail["count"]
                    price = detail["price"]
                    order_detail = {
                        "book_id": book_id,
                        "count": count,
                        "price": price
                    }
                    order_detail_list.append(order_detail)

                # 构建订单信息
                order_info = {
                    "order_id": order_id,
                    "order_detail": order_detail_list
                }
                order_list.append(order_info)

        except pymongo.errors.PyMongoError as e:
            return 528, str(e), []
        except BaseException as e:
            return 530, str(e), []

        return 200, "ok", order_list


    def cancel_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            order = self.conn["new_order"].find_one({"order_id": order_id})
            if not order:
                return error.error_invalid_order_id(order_id)

            buyer_id = order["user_id"]
            if buyer_id != user_id:
                return error.error_authorization_fail()

            result = self.conn["new_order"].delete_one({"order_id": order_id})
            if result.deleted_count == 0:
                return error.error_invalid_order_id(order_id)

            result = self.conn["new_order_detail"].delete_one({"order_id": order_id})
                                                   #delete_many -> delete_one
            if result.deleted_count == 0:
                return error.error_invalid_order_id(order_id)

            query = {"order_id": order_id}
            update = {"$set": {"status": "cancelled"}}
            result = self.conn["order_history"].update_one(query, update)
            if result.modified_count == 0:
                return error.error_invalid_order_id(order_id)
        except pymongo.errors.PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def receive_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            conn = self.conn

            # 查询订单
            order = conn["order_history"].find_one({"order_id": order_id})
            if not order:
                return error.error_invalid_order_id(order_id)

            # 检查订单是否属于当前用户
            if order["user_id"] != user_id:
                return error.error_authorization_fail()

            # 检查订单状态是否为已发货
            if order["status"] != "shipped":
                return error.error_not_shipped(order_id)

            # 更新订单状态为已收货
            result = conn["order_history"].update_one({"order_id": order_id}, {"$set": {"status": "received"}})
            if result.modified_count == 0:
                return error.error_invalid_order_id(order_id)

        except pymongo.errors.PyMongoError as e:
            return 528, str(e)
        except BaseException as e:
            return 530, str(e)

        return 200, "ok"