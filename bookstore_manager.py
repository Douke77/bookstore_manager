import sqlite3
from typing import Tuple
import sys

def connect_db() -> sqlite3.Connection:
    """
    建立並返回 SQLite 資料庫連線
    設置 row_factory = sqlite3.Row
    """
    conn = sqlite3.connect("bookstore.db")
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db(conn: sqlite3.Connection) -> None:
    """
    檢查並建立資料表，匯入初始資料。
    """
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS member (
            mid TEXT PRIMARY KEY,
            mname TEXT NOT NULL,
            mphone TEXT NOT NULL,
            memail TEXT
        );

        CREATE TABLE IF NOT EXISTS book (
            bid TEXT PRIMARY KEY,
            btitle TEXT NOT NULL,
            bprice INTEGER NOT NULL,
            bstock INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sale (
            sid INTEGER PRIMARY KEY AUTOINCREMENT,
            sdate TEXT NOT NULL,
            mid TEXT NOT NULL,
            bid TEXT NOT NULL,
            sqty INTEGER NOT NULL,
            sdiscount INTEGER NOT NULL,
            stotal INTEGER NOT NULL
        );

        INSERT OR IGNORE INTO member VALUES ('M001', 'Alice', '0912-345678', 'alice@example.com');
        INSERT OR IGNORE INTO member VALUES ('M002', 'Bob', '0923-456789', 'bob@example.com');
        INSERT OR IGNORE INTO member VALUES ('M003', 'Cathy', '0934-567890', 'cathy@example.com');

        INSERT OR IGNORE INTO book VALUES ('B001', 'Python Programming', 600, 50);
        INSERT OR IGNORE INTO book VALUES ('B002', 'Data Science Basics', 800, 30);
        INSERT OR IGNORE INTO book VALUES ('B003', 'Machine Learning Guide', 1200, 20);

        INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal) VALUES (1, '2024-01-15', 'M001', 'B001', 2, 100, 1100);
        INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal) VALUES (2, '2024-01-16', 'M002', 'B002', 1, 50, 750);
        INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal) VALUES (3, '2024-01-17', 'M001', 'B003', 3, 200, 3400);
        INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal) VALUES (4, '2024-01-18', 'M003', 'B001', 1, 0, 600);
    """)
    conn.commit()

def is_valid_date(date_str: str) -> bool:
    return len(date_str) == 10 and date_str.count("-") == 2

def add_sale(conn: sqlite3.Connection, sdate: str, mid: str, bid: str, sqty: int, sdiscount: int) -> Tuple[bool, str]:
    """
    新增銷售記錄，驗證會員、書籍編號和庫存，計算總額並更新庫存。
    """
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM member WHERE mid = ?", (mid,))
        member = cursor.fetchone()
        cursor.execute("SELECT * FROM book WHERE bid = ?", (bid,))
        book = cursor.fetchone()

        if not member or not book:
            return False, "錯誤：會員編號或書籍編號無效"

        if book['bstock'] < sqty:
            return False, f"錯誤：書籍庫存不足 (現有庫存: {book['bstock']})"

        stotal = book['bprice'] * sqty - sdiscount

        conn.execute("BEGIN")
        cursor.execute("INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES (?, ?, ?, ?, ?, ?)",
                       (sdate, mid, bid, sqty, sdiscount, stotal))
        cursor.execute("UPDATE book SET bstock = bstock - ? WHERE bid = ?", (sqty, bid))
        conn.commit()
        return True, f"銷售記錄已新增！(銷售總額: {stotal:,})"
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"資料庫錯誤：{e}"

def print_sale_report(conn: sqlite3.Connection) -> None:
    """
    查詢並顯示所有銷售報表，按銷售編號排序。
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.sid, s.sdate, m.mname, b.btitle, b.bprice, s.sqty, s.sdiscount, s.stotal
        FROM sale s
        JOIN member m ON s.mid = m.mid
        JOIN book b ON s.bid = b.bid
        ORDER BY s.sid
    """)
    sales = cursor.fetchall()

    for idx, row in enumerate(sales, start=1):
        if idx == 1:
            print(f"\n==================== 銷售報表 ====================")
        print(f"銷售 #{idx}")
        print(f"銷售編號: {row['sid']}")
        print(f"銷售日期: {row['sdate']}")
        print(f"會員姓名: {row['mname']}")
        print(f"書籍標題: {row['btitle']}")
        print("--------------------------------------------------")
        print("單價\t數量\t折扣\t小計")
        print("--------------------------------------------------")
        print(f"{row['bprice']:,}\t{row['sqty']}\t{row['sdiscount']:,}\t{row['stotal']:,}")
        print("--------------------------------------------------")
        print(f"銷售總額: {row['stotal']:,}")
        print("==================================================")
        print()
def update_sale(conn: sqlite3.Connection) -> None:
    """
    顯示銷售記錄列表，提示使用者輸入要更新的銷售編號和新的折扣金額，重新計算總額。
    """
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT sale.sid, member.mname, sale.sdate
            FROM sale
            JOIN member ON sale.mid = member.mid
            ORDER BY sale.sid
        """)
        sales = cursor.fetchall()

        if not sales:
            print("目前沒有銷售記錄可更新。")
            return

        print("\n======== 銷售記錄列表 ========")
        for idx, row in enumerate(sales, start=1):
            print(f"{idx}. 銷售編號: {row['sid']} - 會員: {row['mname']} - 日期: {row['sdate']}")
        print("================================")

        choice = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ").strip()
        if not choice:
            return

        try:
            choice = int(choice)
            if choice < 1 or choice > len(sales):
                print("錯誤：請輸入有效的數字")
                return
        except ValueError:
            print("錯誤：請輸入有效的數字")
            return

        sid = sales[choice - 1]["sid"]

        # 取得該筆銷售的詳細資料
        cursor.execute("""
            SELECT sale.sid, sale.sqty, book.bprice
            FROM sale
            JOIN book ON sale.bid = book.bid
            WHERE sale.sid = ?
        """, (sid,))
        record = cursor.fetchone()
        if not record:
            print("錯誤：找不到該筆銷售記錄")
            return

        sqty = record["sqty"]
        bprice = record["bprice"]

        # 輸入新的折扣金額
        while True:
            try:
                new_discount = int(input("請輸入新的折扣金額："))
                if new_discount < 0:
                    print("錯誤：折扣金額不能為負數，請重新輸入")
                    continue
                break
            except ValueError:
                print("錯誤：折扣金額必須為整數，請重新輸入")

        new_total = bprice * sqty - new_discount

        # 更新記錄
        cursor.execute("""
            UPDATE sale
            SET sdiscount = ?, stotal = ?
            WHERE sid = ?
        """, (new_discount, new_total, sid))
        conn.commit()

        print(f"=> 銷售編號 {sid} 已更新！(銷售總額: {new_total:,})")

    except sqlite3.DatabaseError as e:
        print("資料庫錯誤：", e)

def delete_sale(conn: sqlite3.Connection) -> None:
    """
    顯示銷售記錄列表，提示使用者輸入要刪除的銷售編號，執行刪除操作並提交
    """
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT sale.sid, member.mname, sale.sdate
            FROM sale
            JOIN member ON sale.mid = member.mid
            ORDER BY sale.sid
        """)
        sales = cursor.fetchall()

        if not sales:
            print("目前沒有銷售記錄可刪除。")
            return

        print("\n======== 銷售記錄列表 ========")
        for idx, row in enumerate(sales, start=1):
            print(f"{idx}. 銷售編號: {row['sid']} - 會員: {row['mname']} - 日期: {row['sdate']}")
        print("================================")

        while 1:
            choice = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 離開)：").strip()
            if not choice:
                return


            try:
                choice = int(choice)
                if choice < 1 or choice > len(sales):
                    print("錯誤：請輸入有效的數字")
                    continue
            except ValueError:
                print("錯誤：請輸入有效的數字")
                continue
            break

        sid = sales[choice - 1]["sid"]

        cursor.execute("DELETE FROM sale WHERE sid = ?", (sid,))
        conn.commit()

        print(f"=> 銷售編號 {sid} 已成功刪除！")

    except sqlite3.DatabaseError as e:
        print("資料庫錯誤：", e)

def main() -> None:
    """
    程式主流程，包含選單迴圈和各功能的呼叫
    """
    conn = connect_db()
    initialize_db(conn)

    while True:
        print("""
***************選單***************
1. 新增銷售記錄
2. 顯示銷售報表
3. 更新銷售記錄
4. 刪除銷售記錄
5. 離開
**********************************
""")
        choice = input("請選擇操作項目(Enter 離開)：").strip()
        if choice == "":
            break
        elif choice == "1":
            sdate = input("請輸入銷售日期 (YYYY-MM-DD)：").strip()
            if not is_valid_date(sdate):
                print("=> 錯誤：日期格式不正確")
                continue
            mid = input("請輸入會員編號：").strip()
            bid = input("請輸入書籍編號：").strip()
            while 1:
                try:
                    sqty = int(input("請輸入購買數量："))
                    if sqty <= 0:
                        print("=> 錯誤：數量必須為正整數，請重新輸入")
                        continue
                except ValueError:
                    print("=> 錯誤：數量或折扣必須為整數，請重新輸入")
                    continue
                break
            while 1:
                try:
                    sdiscount = int(input("請輸入折扣金額："))
                    if sdiscount < 0:
                        print("=> 錯誤：折扣金額不能為負數，請重新輸入")
                        continue
                except ValueError:
                    print("=> 錯誤：數量或折扣必須為整數，請重新輸入")
                    continue
                break

            success, msg = add_sale(conn, sdate, mid, bid, sqty, sdiscount)
            print(f"=> {msg}")

        elif choice == "2":
            print_sale_report(conn)

        elif choice == "3":
            update_sale(conn)

        elif choice == "4":
            delete_sale(conn)

        elif choice == "5":
            print("結束")
            break
        else:
            print("=> 請輸入有效的選項（1-5）")

if __name__ == '__main__':
    main()
