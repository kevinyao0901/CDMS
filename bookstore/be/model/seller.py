import psycopg2
from be.model import error
from be.model import db_conn


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
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            self.cur.execute(
                "INSERT INTO store(store_id, book_id, book_info, stock_level) "
                "VALUES (%s, %s, %s, %s)",
                (store_id, book_id, book_json_str, stock_level),
            )
            self.conn.commit()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok"

    def add_stock_level(
        self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            self.cur.execute(
                "UPDATE store SET stock_level = stock_level + %s "
                "WHERE store_id = %s AND book_id = %s",
                (add_stock_level, store_id, book_id),
            )
            self.conn.commit()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
            self.cur.execute(
                "INSERT INTO user_store(store_id, user_id) VALUES (%s, %s)",
                (store_id, user_id),
            )
            self.conn.commit()
        except psycopg2.Error as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        finally:
            self.cur.close()
            self.conn.close()
        return 200, "ok"

    def ship_order(self, user_id: str, store_id: str, order_id: str) -> (int, str):
        try:
            # 检查用户和商店是否存在
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)

            # 查询订单状态
            self.cur.execute(
                "SELECT status FROM order_history WHERE order_id = %s;",
                (order_id,)
            )
            row = self.cur.fetchone()
            if not row:
                return error.error_invalid_order_id(order_id)

            status = row[0]

            # 检查订单状态是否为已支付
            if status != 'paid':
                return error.error_not_paid(order_id)

            # 更新订单历史状态为已发货
            self.cur.execute(
                "UPDATE order_history SET status = 'shipped' WHERE order_id = %s;",
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
