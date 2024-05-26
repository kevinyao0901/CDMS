import uuid
import json
import logging
import psycopg2
from threading import Timer
from be.model import db_conn
from be.model import error


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(self, user_id: str, store_id: str, id_and_count: [(str, int)]) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            order = {"order_id": uid, "user_id": user_id, "store_id": store_id}

            order_details = []
            for book_id, count in id_and_count:
                cursor = self.cur.execute(
                    "SELECT book_id, stock_level, book_info FROM store "
                    "WHERE store_id = %s AND book_id = %s;",
                    (store_id, book_id),
                )
                row = self.cur.fetchone()
                if row is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = row[1]
                book_info = row[2]
                book_info_json = json.loads(book_info)
                price = book_info_json.get("price")

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                self.cur.execute(
                    "UPDATE store SET stock_level = stock_level - %s "
                    "WHERE store_id = %s AND book_id = %s AND stock_level >= %s",
                    (count, store_id, book_id, count),
                )
                if self.cur.rowcount == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)

                self.cur.execute(
                    "INSERT INTO new_order_detail(order_id, book_id, count, price) "
                    "VALUES(%s, %s, %s, %s);",
                    (uid, book_id, count, price),
                )

            self.cur.execute(
                "INSERT INTO new_order(order_id, store_id, user_id) "
                "VALUES(%s, %s, %s);",
                (uid, store_id, user_id),
            )
            self.conn.commit()
            order_id = uid

            # 延迟队列
            timer = Timer(60.0, self.cancel_order, args=[user_id, order_id])
            timer.start()

            # 存入历史订单
            order["status"] = "pending"
            self.cur.execute(
                "INSERT INTO order_history(order_id, user_id, store_id, status) "
                "VALUES(%s, %s, %s, %s);",
                (uid, user_id, store_id, order["status"]),
            )
            self.conn.commit()

            for detail in order_details:
                self.cur.execute(
                    "INSERT INTO order_history_detail(order_id, book_id, count, price) "
                    "VALUES(%s, %s, %s, %s);",
                    (uid, detail["book_id"], detail["count"], detail["price"]),
                )
                self.conn.commit()

        except psycopg2.Error as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""
        finally:
            self.cur.close()
            self.conn.close()

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            # 获取订单信息
            self.cur.execute(
                "SELECT user_id, store_id FROM new_order WHERE order_id = %s;",
                (order_id,)
            )
            row = self.cur.fetchone()
            if row is None:
                return error.error_invalid_order_id(order_id)

            buyer_id, store_id = row

            if buyer_id != user_id:
                return error.error_authorization_fail()

            # 获取买家信息
            self.cur.execute(
                'SELECT balance, password FROM "user" WHERE user_id = %s;',
                (buyer_id,)
            )
            row = self.cur.fetchone()
            if row is None:
                return error.error_non_exist_user_id(buyer_id)
            balance, buyer_password = row

            if password != buyer_password:
                return error.error_authorization_fail()

            # 获取卖家信息
            self.cur.execute(
                "SELECT user_id FROM user_store WHERE store_id = %s;",
                (store_id,)
            )
            row = self.cur.fetchone()
            if row is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = row[0]

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            # 获取订单详情
            self.cur.execute(
                "SELECT book_id, count, price FROM new_order_detail WHERE order_id = %s;",
                (order_id,)
            )
            total_price = 0
            for row in self.cur.fetchall():
                count, price = row[1], row[2]
                total_price += price * count

            # 检查余额是否足够支付
            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            # 执行交易：扣除买家余额，增加卖家余额
            self.cur.execute(
                'UPDATE "user" SET balance = balance - %s '
                'WHERE user_id = %s AND balance >= %s',
                (total_price, buyer_id, total_price),
            )
            if self.cur.rowcount == 0:
                return error.error_not_sufficient_funds(order_id)

            self.cur.execute(
                'UPDATE "user" SET balance = balance + %s '
                'WHERE user_id = %s',
                (total_price, seller_id),
            )
            if self.cur.rowcount == 0:
                return error.error_non_exist_user_id(buyer_id)

            # 删除订单和订单详情
            self.cur.execute(
                "DELETE FROM new_order WHERE order_id = %s",
                (order_id,)
            )
            if self.cur.rowcount == 0:
                return error.error_invalid_order_id(order_id)

            self.cur.execute(
                "DELETE FROM new_order_detail WHERE order_id = %s",
                (order_id,)
            )
            if self.cur.rowcount == 0:
                return error.error_invalid_order_id(order_id)

            # 更新订单历史状态为 "paid"
            self.cur.execute(
                "UPDATE order_history SET status = 'paid' WHERE order_id = %s;",
                (order_id,)
            )
            if self.cur.rowcount == 0:
                return error.error_invalid_order_id(order_id)

            self.conn.commit()

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            cursor = self.cur.execute(
                'SELECT password FROM "user" WHERE user_id = %s', (user_id,)
            )
            row = self.cur.fetchone()
            if row is None:
                return error.error_authorization_fail()

            if row[0] != password:
                return error.error_authorization_fail()

            self.cur.execute(
                'UPDATE "user" SET balance = balance + %s WHERE user_id = %s',
                (add_value, user_id),
            )
            if self.cur.rowcount == 0:
                return error.error_non_exist_user_id(user_id)

            self.conn.commit()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()

        return 200, "ok"

    def get_order_history(self, user_id: str) -> (int, str, [dict]):
        try:
            # 获取用户的历史订单
            self.cur.execute(
                "SELECT order_id FROM order_history WHERE user_id = %s;",
                (user_id,)
            )
            rows = self.cur.fetchall()

            if not rows:
                return error.error_non_exist_user_id(user_id) + ([],)

            order_list = []
            for row in rows:
                order_id = row[0]

                # 获取订单详情
                self.cur.execute(
                    "SELECT book_id, count, price FROM order_history_detail WHERE order_id = %s;",
                    (order_id,)
                )
                order_detail_list = []
                for detail_row in self.cur.fetchall():
                    book_id, count, price = detail_row
                    order_detail = {
                        "book_id": book_id,
                        "count": count,
                        "price": price
                    }
                    order_detail_list.append(order_detail)

                order_info = {
                    "order_id": order_id,
                    "order_detail": order_detail_list
                }
                order_list.append(order_info)

        except psycopg2.Error as e:
            return 528, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        finally:
            self.cur.close()
            self.conn.close()

        return 200, "ok", order_list

    def cancel_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            # 检查订单是否存在
            self.cur.execute(
                "SELECT user_id FROM new_order WHERE order_id = %s;",
                (order_id,)
            )
            row = self.cur.fetchone()
            if not row:
                return error.error_invalid_order_id(order_id)

            buyer_id = row[0]

            # 检查用户权限
            if buyer_id != user_id:
                return error.error_authorization_fail()

            # 删除订单和订单详情
            self.cur.execute(
                "DELETE FROM new_order WHERE order_id = %s;",
                (order_id,)
            )
            if self.cur.rowcount == 0:
                return error.error_invalid_order_id(order_id)

            self.cur.execute(
                "DELETE FROM new_order_detail WHERE order_id = %s;",
                (order_id,)
            )
            if self.cur.rowcount == 0:
                return error.error_invalid_order_id(order_id)

            # 更新订单历史状态为取消
            self.cur.execute(
                "UPDATE order_history SET status = 'cancelled' WHERE order_id = %s;",
                (order_id,)
            )
            if self.cur.rowcount == 0:
                return error.error_invalid_order_id(order_id)

            self.conn.commit()

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()

        return 200, "ok"

    def receive_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            # 检查订单是否存在
            self.cur.execute(
                "SELECT user_id, status FROM order_history WHERE order_id = %s;",
                (order_id,)
            )
            row = self.cur.fetchone()
            if not row:
                return error.error_invalid_order_id(order_id)

            buyer_id, status = row

            # 检查用户权限
            if buyer_id != user_id:
                return error.error_authorization_fail()

            # 检查订单状态是否为已发货
            if status != "shipped":
                return error.error_not_shipped(order_id)

            # 更新订单历史状态为已收货
            self.cur.execute(
                "UPDATE order_history SET status = 'received' WHERE order_id = %s;",
                (order_id,)
            )
            if self.cur.rowcount == 0:
                return error.error_invalid_order_id(order_id)

            self.conn.commit()

        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()

        return 200, "ok"
