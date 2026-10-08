# -*- coding: utf-8 -*-
"""ERP Professional v3.0 - Single File Edition"""
import os, sys, sqlite3, hashlib, tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date

# ============ Paths ============
def app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(app_dir(), "erp_data.db")

# ============ Database ============
def get_conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, full_name TEXT, role TEXT DEFAULT 'user', active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS accounts (account_id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT, type TEXT, parent_id INTEGER, is_leaf INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS parties (party_id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, type TEXT, name TEXT, phone TEXT, email TEXT, address TEXT, balance REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS warehouses (wh_id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT, location TEXT);
CREATE TABLE IF NOT EXISTS items (item_id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT, unit TEXT, category TEXT, cost REAL DEFAULT 0, price REAL DEFAULT 0, reorder_level REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS stock (stock_id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, wh_id INTEGER, quantity REAL DEFAULT 0, UNIQUE(item_id,wh_id));
CREATE TABLE IF NOT EXISTS journal_entries (entry_id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, ref TEXT, description TEXT, source TEXT, source_id INTEGER, posted INTEGER DEFAULT 1, created_by INTEGER);
CREATE TABLE IF NOT EXISTS journal_lines (line_id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER, account_id INTEGER, debit REAL DEFAULT 0, credit REAL DEFAULT 0, description TEXT);
CREATE TABLE IF NOT EXISTS sales_invoices (inv_id INTEGER PRIMARY KEY AUTOINCREMENT, inv_no TEXT UNIQUE, date TEXT, customer_id INTEGER, subtotal REAL, tax REAL, discount REAL, total REAL, paid REAL, payment_method TEXT, notes TEXT, wh_id INTEGER);
CREATE TABLE IF NOT EXISTS sales_lines (line_id INTEGER PRIMARY KEY AUTOINCREMENT, inv_id INTEGER, item_id INTEGER, quantity REAL, price REAL, discount REAL DEFAULT 0, total REAL);
CREATE TABLE IF NOT EXISTS purchase_invoices (inv_id INTEGER PRIMARY KEY AUTOINCREMENT, inv_no TEXT UNIQUE, date TEXT, supplier_id INTEGER, subtotal REAL, tax REAL, discount REAL, total REAL, paid REAL, payment_method TEXT, notes TEXT, wh_id INTEGER);
CREATE TABLE IF NOT EXISTS purchase_lines (line_id INTEGER PRIMARY KEY AUTOINCREMENT, inv_id INTEGER, item_id INTEGER, quantity REAL, price REAL, discount REAL DEFAULT 0, total REAL);
CREATE TABLE IF NOT EXISTS inventory_trans (trans_id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, item_id INTEGER, wh_id INTEGER, type TEXT, quantity REAL, unit_cost REAL, ref TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS employees (emp_id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT, position TEXT, department TEXT, basic_salary REAL, allowances REAL, hire_date TEXT, phone TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS payroll (payroll_id INTEGER PRIMARY KEY AUTOINCREMENT, emp_id INTEGER, period TEXT, basic REAL, allowances REAL, deductions REAL, net REAL, paid INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS fixed_assets (asset_id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT, category TEXT, purchase_date TEXT, cost REAL, salvage REAL, life_years INTEGER, method TEXT DEFAULT 'straight', accumulated REAL DEFAULT 0, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""

DEFAULT_ACCOUNTS = [
    ("1000","الأصول","أصول",None,0),("1100","النقدية","أصول","1000",1),
    ("1110","الصندوق","أصول","1000",1),("1120","البنك","أصول","1000",1),
    ("1200","العملاء المدينون","أصول","1000",1),("1300","المخزون","أصول","1000",1),
    ("1500","الأصول الثابتة","أصول","1000",1),("1510","مجمع الإهلاك","أصول","1000",1),
    ("2000","الخصوم","خصوم",None,0),("2100","الموردون الدائنون","خصوم","2000",1),
    ("2200","ضريبة القيمة المضافة","خصوم","2000",1),("2300","الرواتب المستحقة","خصوم","2000",1),
    ("3000","حقوق الملكية","حقوق ملكية",None,0),("3100","رأس المال","حقوق ملكية","3000",1),
    ("3200","الأرباح المحتجزة","حقوق ملكية","3000",1),
    ("4000","الإيرادات","إيرادات",None,0),("4100","المبيعات","إيرادات","4000",1),
    ("4200","إيرادات أخرى","إيرادات","4000",1),
    ("5000","المصروفات","مصروفات",None,0),("5100","تكلفة البضاعة","مصروفات","5000",1),
    ("5200","مصروف الرواتب","مصروفات","5000",1),("5300","مصروف الإهلاك","مصروفات","5000",1),
    ("5400","مصروفات عمومية","مصروفات","5000",1),
]

def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 0:
        conn.execute("INSERT INTO users(username,password,full_name,role) VALUES (?,?,?,?)",
                     ("admin", hashlib.sha256("admin".encode()).hexdigest(), "المدير", "admin"))
    if conn.execute("SELECT COUNT(*) c FROM accounts").fetchone()["c"] == 0:
        for code,name,typ,parent,lf in DEFAULT_ACCOUNTS:
            pid = None
            if parent:
                p = conn.execute("SELECT account_id FROM accounts WHERE code=?", (parent,)).fetchone()
                if p: pid = p["account_id"]
            conn.execute("INSERT INTO accounts(code,name,type,parent_id,is_leaf) VALUES (?,?,?,?,?)",
                         (code,name,typ,pid,lf))
    if conn.execute("SELECT COUNT(*) c FROM warehouses").fetchone()["c"] == 0:
        conn.execute("INSERT INTO warehouses(code,name,location) VALUES ('WH01','المخزن الرئيسي','المركز')")
    defaults = {"account_cash":"1110","account_ar":"1200","account_ap":"2100","account_sales":"4100",
                "account_tax":"2200","account_inventory":"1300","account_cogs":"5100",
                "account_salary_expense":"5200","account_depreciation_expense":"5300",
                "account_accumulated_dep":"1510","account_fixed_assets":"1500"}
    for k,code in defaults.items():
        if not conn.execute("SELECT 1 FROM settings WHERE key=?", (k,)).fetchone():
            a = conn.execute("SELECT account_id FROM accounts WHERE code=?", (code,)).fetchone()
            if a: conn.execute("INSERT INTO settings(key,value) VALUES (?,?)", (k, str(a["account_id"])))
    conn.commit(); conn.close()

def get_setting(key):
    c = get_conn()
    r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    c.close()
    return int(r["value"]) if r and r["value"] else None

# ============ Accounting ============
def get_accounts(leaf_only=False):
    c = get_conn()
    q = "SELECT * FROM accounts" + (" WHERE is_leaf=1" if leaf_only else "") + " ORDER BY code"
    rows = c.execute(q).fetchall(); c.close()
    return [dict(r) for r in rows]

def post_journal(d, ref, desc, lines, source=None, sid=None, uid=None):
    td = sum(l.get("debit",0) for l in lines)
    tc = sum(l.get("credit",0) for l in lines)
    if abs(td-tc) > 0.01: return False, "قيد غير متوازن"
    c = get_conn()
    try:
        cur = c.execute("INSERT INTO journal_entries(date,ref,description,source,source_id,posted,created_by) VALUES (?,?,?,?,?,1,?)",
                        (d, ref, desc, source, sid, uid))
        eid = cur.lastrowid
        for l in lines:
            c.execute("INSERT INTO journal_lines(entry_id,account_id,debit,credit,description) VALUES (?,?,?,?,?)",
                      (eid, l["account_id"], l.get("debit",0), l.get("credit",0), l.get("description","")))
        c.commit(); return True, eid
    except Exception as e:
        c.rollback(); return False, str(e)
    finally: c.close()

def get_journal_entries(limit=300):
    c = get_conn()
    rows = c.execute("SELECT e.*, (SELECT SUM(debit) FROM journal_lines WHERE entry_id=e.entry_id) total FROM journal_entries e ORDER BY entry_id DESC LIMIT ?", (limit,)).fetchall()
    c.close(); return [dict(r) for r in rows]

def get_journal_lines(eid):
    c = get_conn()
    rows = c.execute("SELECT l.*,a.code,a.name acc_name FROM journal_lines l JOIN accounts a ON a.account_id=l.account_id WHERE l.entry_id=?", (eid,)).fetchall()
    c.close(); return [dict(r) for r in rows]

def trial_balance(f, t):
    c = get_conn()
    rows = c.execute("""SELECT a.account_id,a.code,a.name,a.type,
        COALESCE(SUM(CASE WHEN e.date BETWEEN ? AND ? THEN l.debit ELSE 0 END),0) debit,
        COALESCE(SUM(CASE WHEN e.date BETWEEN ? AND ? THEN l.credit ELSE 0 END),0) credit
        FROM accounts a LEFT JOIN journal_lines l ON l.account_id=a.account_id
        LEFT JOIN journal_entries e ON e.entry_id=l.entry_id
        WHERE a.is_leaf=1 GROUP BY a.account_id ORDER BY a.code""", (f,t,f,t)).fetchall()
    c.close(); return [dict(r) for r in rows]

# ============ Inventory ============
def get_items():
    c = get_conn(); r = c.execute("SELECT * FROM items ORDER BY code").fetchall(); c.close()
    return [dict(x) for x in r]

def stock_in(item_id, wh_id, qty, cost, ref, src=""):
    c = get_conn()
    try:
        c.execute("INSERT INTO inventory_trans(date,item_id,wh_id,type,quantity,unit_cost,ref,source) VALUES (?,?,?,?,?,?,?,?)",
                  (date.today().isoformat(), item_id, wh_id, "IN", qty, cost, ref, src))
        cur = c.execute("SELECT * FROM stock WHERE item_id=? AND wh_id=?", (item_id, wh_id)).fetchone()
        if cur:
            old_q = cur["quantity"]
            new_avg = ((old_q*c.execute("SELECT cost FROM items WHERE item_id=?", (item_id,)).fetchone()["cost"]) + qty*cost) / (old_q+qty) if (old_q+qty) else cost
            c.execute("UPDATE stock SET quantity=quantity+? WHERE stock_id=?", (qty, cur["stock_id"]))
            c.execute("UPDATE items SET cost=? WHERE item_id=?", (new_avg, item_id))
        else:
            c.execute("INSERT INTO stock(item_id,wh_id,quantity) VALUES (?,?,?)", (item_id, wh_id, qty))
        c.commit(); return True, ""
    except Exception as e:
        c.rollback(); return False, str(e)
    finally: c.close()

def stock_out(item_id, wh_id, qty, ref, src=""):
    c = get_conn()
    try:
        cur = c.execute("SELECT * FROM stock WHERE item_id=? AND wh_id=?", (item_id, wh_id)).fetchone()
        if not cur or cur["quantity"] < qty: return False, "كمية غير كافية"
        cost = c.execute("SELECT cost FROM items WHERE item_id=?", (item_id,)).fetchone()["cost"]
        c.execute("INSERT INTO inventory_trans(date,item_id,wh_id,type,quantity,unit_cost,ref,source) VALUES (?,?,?,?,?,?,?,?)",
                  (date.today().isoformat(), item_id, wh_id, "OUT", qty, cost, ref, src))
        c.execute("UPDATE stock SET quantity=quantity-? WHERE stock_id=?", (qty, cur["stock_id"]))
        c.commit(); return True, ""
    except Exception as e:
        c.rollback(); return False, str(e)
    finally: c.close()

def get_stock():
    c = get_conn()
    rows = c.execute("""SELECT s.*,i.code,i.name iname,i.unit,i.reorder_level,w.name wname FROM stock s
        JOIN items i ON i.item_id=s.item_id JOIN warehouses w ON w.wh_id=s.wh_id ORDER BY i.code""").fetchall()
    c.close(); return [dict(r) for r in rows]

# ============ Parties ============
def get_parties(t=None):
    c = get_conn()
    q = "SELECT * FROM parties" + (f" WHERE type='{t}'" if t else "") + " ORDER BY code"
    rows = c.execute(q).fetchall(); c.close()
    return [dict(r) for r in rows]

def update_party_balance(pid, delta):
    c = get_conn(); c.execute("UPDATE parties SET balance=balance+? WHERE party_id=?", (delta, pid)); c.commit(); c.close()

# ============ Sales / Purchase ============
def next_inv_no(prefix, table):
    c = get_conn()
    r = c.execute(f"SELECT inv_no FROM {table} WHERE inv_no LIKE '{prefix}%' ORDER BY inv_id DESC LIMIT 1").fetchone()
    c.close()
    n = 1
    if r:
        try: n = int(r["inv_no"][1:])+1
        except: n = 1
    return f"{prefix}{n:04d}"

def create_sale(customer_id, lines, wh_id, pmt, paid, tax_rate, disc, uid):
    sub = sum(l["quantity"]*l["price"]-l.get("discount",0) for l in lines)
    tax = sub*tax_rate/100; total = sub+tax-disc
    no = next_inv_no("S","sales_invoices")
    c = get_conn()
    try:
        cur = c.execute("""INSERT INTO sales_invoices(inv_no,date,customer_id,subtotal,tax,discount,total,paid,payment_method,wh_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (no, date.today().isoformat(), customer_id, sub, tax, disc, total, paid, pmt, wh_id))
        iid = cur.lastrowid
        for l in lines:
            lt = l["quantity"]*l["price"]-l.get("discount",0)
            c.execute("INSERT INTO sales_lines(inv_id,item_id,quantity,price,discount,total) VALUES (?,?,?,?,?,?)",
                      (iid, l["item_id"], l["quantity"], l["price"], l.get("discount",0), lt))
        c.commit()
    except Exception as e:
        c.rollback(); c.close(); return False, str(e)
    c.close()
    for l in lines:
        ok, m = stock_out(l["item_id"], wh_id, l["quantity"], no, "SALE")
        if not ok: return False, m
    je = []
    ar = get_setting("account_ar"); sl = get_setting("account_sales")
    tx = get_setting("account_tax"); ca = get_setting("account_cash")
    if total-paid>0 and ar: je.append({"account_id":ar,"debit":total-paid})
    if paid and ca: je.append({"account_id":ca,"debit":paid})
    if sl: je.append({"account_id":sl,"credit":sub-disc})
    if tax and tx: je.append({"account_id":tx,"credit":tax})
    if je: post_journal(date.today().isoformat(), no, f"فاتورة {no}", je, "SALE", iid, uid)
    if customer_id and total-paid>0: update_party_balance(customer_id, total-paid)
    return True, no

def create_purchase(supplier_id, lines, wh_id, pmt, paid, tax_rate, disc, uid):
    sub = sum(l["quantity"]*l["price"]-l.get("discount",0) for l in lines)
    tax = sub*tax_rate/100; total = sub+tax-disc
    no = next_inv_no("P","purchase_invoices")
    c = get_conn()
    try:
        cur = c.execute("""INSERT INTO purchase_invoices(inv_no,date,supplier_id,subtotal,tax,discount,total,paid,payment_method,wh_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", (no, date.today().isoformat(), supplier_id, sub, tax, disc, total, paid, pmt, wh_id))
        iid = cur.lastrowid
        for l in lines:
            lt = l["quantity"]*l["price"]-l.get("discount",0)
            c.execute("INSERT INTO purchase_lines(inv_id,item_id,quantity,price,discount,total) VALUES (?,?,?,?,?,?)",
                      (iid, l["item_id"], l["quantity"], l["price"], l.get("discount",0), lt))
        c.commit()
    except Exception as e:
        c.rollback(); c.close(); return False, str(e)
    c.close()
    for l in lines: stock_in(l["item_id"], wh_id, l["quantity"], l["price"], no, "PURCHASE")
    je = []
    inv = get_setting("account_inventory"); ap = get_setting("account_ap")
    tx = get_setting("account_tax"); ca = get_setting("account_cash")
    if inv: je.append({"account_id":inv,"debit":sub-disc})
    if tax and tx: je.append({"account_id":tx,"debit":tax})
    if paid and ca: je.append({"account_id":ca,"credit":paid})
    if total-paid>0 and ap: je.append({"account_id":ap,"credit":total-paid})
    if je: post_journal(date.today().isoformat(), no, f"مشتريات {no}", je, "PURCHASE", iid, uid)
    if supplier_id and total-paid>0: update_party_balance(supplier_id, -(total-paid))
    return True, no

def get_sales(limit=200):
    c = get_conn()
    r = c.execute("SELECT s.*,p.name cname FROM sales_invoices s LEFT JOIN parties p ON p.party_id=s.customer_id ORDER BY inv_id DESC LIMIT ?", (limit,)).fetchall()
    c.close(); return [dict(x) for x in r]

def get_purchases(limit=200):
    c = get_conn()
    r = c.execute("SELECT s.*,p.name sname FROM purchase_invoices s LEFT JOIN parties p ON p.party_id=s.supplier_id ORDER BY inv_id DESC LIMIT ?", (limit,)).fetchall()
    c.close(); return [dict(x) for x in r]

# ============ HR ============
def get_employees():
    c = get_conn(); r = c.execute("SELECT * FROM employees ORDER BY code").fetchall(); c.close()
    return [dict(x) for x in r]

def get_payroll(period=None):
    c = get_conn()
    q = """SELECT p.*,e.code,e.name ename FROM payroll p JOIN employees e ON e.emp_id=p.emp_id"""
    params = []
    if period: q += " WHERE p.period=?"; params.append(period)
    q += " ORDER BY p.period DESC, e.code"
    r = c.execute(q, params).fetchall(); c.close()
    return [dict(x) for x in r]

def run_payroll(period, rate=5.0):
    c = get_conn()
    emps = c.execute("SELECT * FROM employees WHERE active=1").fetchall()
    cnt = 0; total = 0
    for e in emps:
        if c.execute("SELECT 1 FROM payroll WHERE emp_id=? AND period=?", (e["emp_id"], period)).fetchone(): continue
        b = e["basic_salary"] or 0; a = e["allowances"] or 0; d = b*rate/100; n = b+a-d
        c.execute("INSERT INTO payroll(emp_id,period,basic,allowances,deductions,net,paid) VALUES (?,?,?,?,?,?,0)",
                  (e["emp_id"], period, b, a, d, n))
        cnt += 1; total += n
    c.commit(); c.close()
    return cnt, total

def pay_payroll(pid, uid):
    c = get_conn()
    p = c.execute("SELECT * FROM payroll WHERE payroll_id=?", (pid,)).fetchone()
    if not p or p["paid"]: c.close(); return False, "مدفوع مسبقاً"
    c.execute("UPDATE payroll SET paid=1 WHERE payroll_id=?", (pid,))
    c.commit(); c.close()
    sa = get_setting("account_salary_expense"); ca = get_setting("account_cash")
    if sa and ca:
        post_journal(date.today().isoformat(), f"PAY-{pid}", f"راتب {p['period']}",
                     [{"account_id":sa,"debit":p["net"]},{"account_id":ca,"credit":p["net"]}], "PAYROLL", pid, uid)
    return True, "تم"

# ============ Assets ============
def get_assets():
    c = get_conn(); r = c.execute("SELECT * FROM fixed_assets WHERE active=1 ORDER BY code").fetchall(); c.close()
    return [dict(x) for x in r]

def monthly_dep(a):
    lm = (a["life_years"] or 5)*12
    return (a["cost"]-a["salvage"])/lm if lm else 0

def post_dep(asset_id, months, uid):
    c = get_conn()
    a = c.execute("SELECT * FROM fixed_assets WHERE asset_id=?", (asset_id,)).fetchone()
    if not a: c.close(); return False, "غير موجود"
    m = monthly_dep(a)*months
    max_d = a["cost"]-a["salvage"]
    if a["accumulated"]+m > max_d: m = max_d-a["accumulated"]
    if m <= 0: c.close(); return False, "مهلك بالكامل"
    c.execute("UPDATE fixed_assets SET accumulated=accumulated+? WHERE asset_id=?", (m, asset_id))
    c.commit(); c.close()
    da = get_setting("account_depreciation_expense"); ad = get_setting("account_accumulated_dep")
    if da and ad:
        post_journal(date.today().isoformat(), f"DEP-{asset_id}", f"إهلاك {a['name']}",
                     [{"account_id":da,"debit":m},{"account_id":ad,"credit":m}], "DEP", asset_id, uid)
    return True, f"إهلاك {m:.2f}"

# ============ Reports ============
def income_stmt(f, t):
    c = get_conn()
    rows = c.execute("""SELECT a.type,a.code,a.name,
        COALESCE(SUM(CASE WHEN e.date BETWEEN ? AND ? THEN l.debit ELSE 0 END),0) d,
        COALESCE(SUM(CASE WHEN e.date BETWEEN ? AND ? THEN l.credit ELSE 0 END),0) c
        FROM accounts a LEFT JOIN journal_lines l ON l.account_id=a.account_id
        LEFT JOIN journal_entries e ON e.entry_id=l.entry_id
        WHERE a.type IN ('إيرادات','مصروفات') AND a.is_leaf=1
        GROUP BY a.account_id ORDER BY a.type,a.code""", (f,t,f,t)).fetchall()
    c.close()
    rev = [{"name":r["name"],"amount":r["c"]-r["d"]} for r in rows if r["type"]=="إيرادات"]
    exp = [{"name":r["name"],"amount":r["d"]-r["c"]} for r in rows if r["type"]=="مصروفات"]
    return rev, exp

def balance_sheet(to_date):
    c = get_conn()
    rows = c.execute("""SELECT a.type,a.code,a.name,
        COALESCE(SUM(CASE WHEN e.date <= ? THEN l.debit ELSE 0 END),0) d,
        COALESCE(SUM(CASE WHEN e.date <= ? THEN l.credit ELSE 0 END),0) c
        FROM accounts a LEFT JOIN journal_lines l ON l.account_id=a.account_id
        LEFT JOIN journal_entries e ON e.entry_id=l.entry_id
        WHERE a.type IN ('أصول','خصوم','حقوق ملكية') AND a.is_leaf=1
        GROUP BY a.account_id ORDER BY a.type,a.code""", (to_date,to_date)).fetchall()
    c.close()
    A,L,E = [],[],[]
    for r in rows:
        b = r["d"]-r["c"] if r["type"]=="أصول" else r["c"]-r["d"]
        item = {"name":r["name"],"amount":b}
        (A if r["type"]=="أصول" else L if r["type"]=="خصوم" else E).append(item)
    return A,L,E

def low_stock():
    c = get_conn()
    r = c.execute("""SELECT i.code,i.name,i.reorder_level,COALESCE(SUM(s.quantity),0) qty
        FROM items i LEFT JOIN stock s ON s.item_id=i.item_id GROUP BY i.item_id
        HAVING qty <= i.reorder_level""").fetchall()
    c.close(); return [dict(x) for x in r]

def dashboard():
    c = get_conn(); s = {}
    for k,q in [("items","SELECT COUNT(*) FROM items"),("customers","SELECT COUNT(*) FROM parties WHERE type='CUSTOMER'"),
                ("suppliers","SELECT COUNT(*) FROM parties WHERE type='SUPPLIER'"),
                ("employees","SELECT COUNT(*) FROM employees WHERE active=1"),
                ("sales","SELECT COALESCE(SUM(total),0) FROM sales_invoices"),
                ("purch","SELECT COALESCE(SUM(total),0) FROM purchase_invoices"),
                ("recv","SELECT COALESCE(SUM(balance),0) FROM parties WHERE type='CUSTOMER'"),
                ("pay","SELECT COALESCE(SUM(-balance),0) FROM parties WHERE type='SUPPLIER'")]:
        s[k] = c.execute(q).fetchone()[0]
    s["inv_value"] = c.execute("SELECT COALESCE(SUM(s.quantity*i.cost),0) FROM stock s JOIN items i ON i.item_id=s.item_id").fetchone()[0]
    c.close(); return s

# ============ Auth ============
def login(u, p):
    c = get_conn()
    r = c.execute("SELECT * FROM users WHERE username=? AND active=1", (u,)).fetchone()
    c.close()
    if r and r["password"] == hashlib.sha256(p.encode()).hexdigest(): return dict(r)
    return None

# ============ UI Helpers ============
def style_tree(tv):
    tv.tag_configure("odd", background="#f8fafc")
    tv.tag_configure("even", background="#ffffff")

class BaseFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#f0f4f8"); self.app = app; self.build()
    def build(self): pass
    def refresh(self): pass
    def title_bar(self, text, buttons=None):
        f = tk.Frame(self, bg="#f0f4f8"); f.pack(fill="x", padx=15, pady=10)
        tk.Label(f, text=text, bg="#f0f4f8", fg="#1e293b", font=("Tahoma", 16, "bold")).pack(side="right")
        if buttons:
            for t,c,col in buttons:
                tk.Button(f, text=t, bg=col, fg="white", font=("Tahoma",10,"bold"), bd=0, padx=15, pady=6, cursor="hand2", command=c).pack(side="left", padx=3)
        return f
    def make_tree(self, cols, widths=None):
        cont = tk.Frame(self, bg="#f0f4f8"); cont.pack(fill="both", expand=True, padx=15, pady=(0,15))
        tv = ttk.Treeview(cont, columns=cols, show="headings", height=18)
        for i,c in enumerate(cols):
            tv.heading(c, text=c); tv.column(c, width=widths[i] if widths else 120, anchor="center")
        sb = ttk.Scrollbar(cont, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="right", fill="both", expand=True); sb.pack(side="right", fill="y")
        style_tree(tv); return tv, cont
    def sel(self, tv, data):
        s = tv.selection()
        if not s: return None
        i = tv.index(s[0])
        return data[i] if i < len(data) else None

# ============ Frames ============
class DashboardFrame(BaseFrame):
    def build(self):
        self.title_bar("لوحة التحكم")
        self.f = tk.Frame(self, bg="#f0f4f8"); self.f.pack(fill="x", padx=15, pady=10)
    def refresh(self):
        for w in self.f.winfo_children(): w.destroy()
        s = dashboard()
        cards = [("المبيعات",f"{s['sales']:,.0f}","#10b981"),("المشتريات",f"{s['purch']:,.0f}","#3b82f6"),
                 ("المدينون",f"{s['recv']:,.0f}","#f59e0b"),("الدائنون",f"{s['pay']:,.0f}","#ef4444"),
                 ("قيمة المخزون",f"{s['inv_value']:,.0f}","#8b5cf6"),("الأصناف",str(s["items"]),"#06b6d4"),
                 ("العملاء",str(s["customers"]),"#0ea5e9"),("الموردون",str(s["suppliers"]),"#f97316"),
                 ("الموظفون",str(s["employees"]),"#84cc16")]
        for i,(l,v,c) in enumerate(cards):
            r,cc = divmod(i,3)
            card = tk.Frame(self.f, bg=c, height=100); card.grid(row=r,column=cc,padx=8,pady=8,sticky="nsew")
            card.grid_propagate(False)
            tk.Label(card,text=l,bg=c,fg="white",font=("Tahoma",11)).pack(pady=(15,3))
            tk.Label(card,text=v,bg=c,fg="white",font=("Tahoma",18,"bold")).pack()
        for c in range(3): self.f.columnconfigure(c, weight=1)
        low = low_stock()
        if low:
            tk.Label(self, text=f"⚠️ {len(low)} صنف وصل للحد الأدنى", bg="#fef3c7", fg="#92400e",
                     font=("Tahoma",12,"bold"), pady=10).pack(fill="x", padx=15, pady=10)

class AccountsFrame(BaseFrame):
    def build(self):
        self.title_bar("دليل الحسابات", [("➕ إضافة",self.add,"#10b981"),("🗑️ حذف",self.del_,"#ef4444")])
        cols = ("#","الكود","الاسم","النوع","ورقة")
        self.tv,_ = self.make_tree(cols,[50,100,300,120,80]); self.data = []
    def refresh(self):
        self.data = get_accounts()
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,a in enumerate(self.data):
            self.tv.insert("","end",values=(i+1,a["code"],a["name"],a["type"],"نعم" if a["is_leaf"] else "لا"),
                          tags=("even" if i%2 else "odd",))
    def add(self):
        dlg = tk.Toplevel(self); dlg.title("حساب جديد"); dlg.geometry("400x300+500+200"); dlg.configure(bg="#f0f4f8"); dlg.grab_set()
        f = tk.Frame(dlg,bg="#f0f4f8"); f.pack(fill="both",expand=True,padx=20,pady=15)
        tk.Label(f,text="الكود",bg="#f0f4f8").pack(anchor="e")
        code = ttk.Entry(f,justify="right"); code.pack(fill="x",pady=3)
        tk.Label(f,text="الاسم",bg="#f0f4f8").pack(anchor="e")
        name = ttk.Entry(f,justify="right"); name.pack(fill="x",pady=3)
        tk.Label(f,text="النوع",bg="#f0f4f8").pack(anchor="e")
        typ = ttk.Combobox(f,values=["أصول","خصوم","حقوق ملكية","إيرادات","مصروفات"],state="readonly")
        typ.pack(fill="x",pady=3)
        def save():
            if not code.get() or not name.get() or not typ.get(): return
            c = get_conn()
            try:
                c.execute("INSERT INTO accounts(code,name,type,is_leaf) VALUES (?,?,?,1)", (code.get(),name.get(),typ.get()))
                c.commit(); dlg.destroy(); self.refresh()
            except Exception as e: messagebox.showerror("خطأ",str(e))
            finally: c.close()
        tk.Button(f,text="حفظ",bg="#10b981",fg="white",bd=0,pady=8,command=save).pack(fill="x",pady=10)
    def del_(self):
        a = self.sel(self.tv, self.data)
        if not a: return
        if messagebox.askyesno("تأكيد",f"حذف {a['name']}؟"):
            c = get_conn()
            if c.execute("SELECT COUNT(*) c FROM journal_lines WHERE account_id=?", (a["account_id"],)).fetchone()["c"]:
                messagebox.showerror("خطأ","الحساب مستخدم"); c.close(); return
            c.execute("DELETE FROM accounts WHERE account_id=?", (a["account_id"],))
            c.commit(); c.close(); self.refresh()

class JournalFrame(BaseFrame):
    def build(self):
        self.title_bar("القيود اليومية",[("➕ قيد يدوي",self.add,"#10b981"),("👁️ عرض",self.view,"#3b82f6")])
        cols = ("#","التاريخ","المرجع","الوصف","المبلغ","المصدر")
        self.tv,_ = self.make_tree(cols,[50,100,100,300,120,100]); self.data = []
    def refresh(self):
        self.data = get_journal_entries()
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,e in enumerate(self.data):
            self.tv.insert("","end",values=(i+1,e["date"],e["ref"] or "",e["description"] or "",
                          f"{e['total'] or 0:,.2f}",e["source"] or "يدوي"),tags=("even" if i%2 else "odd",))
    def add(self):
        dlg = tk.Toplevel(self); dlg.title("قيد جديد"); dlg.geometry("800x520+350+150"); dlg.configure(bg="#f0f4f8"); dlg.grab_set()
        lines = []
        accounts = get_accounts(leaf_only=True)
        top = tk.Frame(dlg,bg="#f0f4f8"); top.pack(fill="x",padx=15,pady=10)
        tk.Label(top,text="التاريخ",bg="#f0f4f8").pack(side="right",padx=3)
        dt = ttk.Entry(top,width=15,justify="center"); dt.insert(0,date.today().isoformat()); dt.pack(side="right",padx=3)
        tk.Label(top,text="المرجع",bg="#f0f4f8").pack(side="right",padx=3)
        rf = ttk.Entry(top,width=20,justify="right"); rf.pack(side="right",padx=3)
        form = tk.Frame(dlg,bg="#e2e8f0",pady=8); form.pack(fill="x",padx=15)
        tk.Label(form,text="الحساب",bg="#e2e8f0").grid(row=0,column=0,padx=3)
        av = tk.StringVar()
        ac = ttk.Combobox(form,textvariable=av,width=35,justify="right")
        ac["values"] = [f"{a['code']} - {a['name']}" for a in accounts]; ac.grid(row=0,column=1,padx=3)
        tk.Label(form,text="مدين",bg="#e2e8f0").grid(row=0,column=2,padx=3)
        de = ttk.Entry(form,width=10,justify="right"); de.grid(row=0,column=3,padx=3)
        tk.Label(form,text="دائن",bg="#e2e8f0").grid(row=0,column=4,padx=3)
        cr = ttk.Entry(form,width=10,justify="right"); cr.grid(row=0,column=5,padx=3)
        tv = ttk.Treeview(dlg,columns=("الحساب","مدين","دائن"),show="headings",height=10)
        for c,w in zip(("الحساب","مدين","دائن"),[400,120,120]):
            tv.heading(c,text=c); tv.column(c,width=w,anchor="center")
        tv.pack(fill="both",expand=True,padx=15,pady=10)
        tot_lbl = tk.Label(dlg,text="مدين 0.00 | دائن 0.00",bg="#f0f4f8",font=("Tahoma",12,"bold"))
        tot_lbl.pack()
        def upd():
            td = sum(l["debit"] for l in lines); tc = sum(l["credit"] for l in lines)
            tot_lbl.config(text=f"مدين {td:,.2f} | دائن {tc:,.2f}",fg="#10b981" if abs(td-tc)<0.01 else "#ef4444")
        def add_line():
            try:
                s = av.get()
                if not s: return
                code = s.split(" - ")[0]
                a = next((x for x in accounts if x["code"]==code),None)
                if not a: return
                d = float(de.get() or 0); c2 = float(cr.get() or 0)
                if d==0 and c2==0: return
                lines.append({"account_id":a["account_id"],"debit":d,"credit":c2})
                tv.insert("","end",values=(f"{a['code']} - {a['name']}",f"{d:,.2f}" if d else "",f"{c2:,.2f}" if c2 else ""))
                de.delete(0,"end"); cr.delete(0,"end"); upd()
            except: pass
        def save():
            if not lines: messagebox.showwarning("تنبيه","أضف سطوراً"); return
            ok,msg = post_journal(dt.get(), rf.get(), "قيد يدوي", lines, "MANUAL")
            if ok: messagebox.showinfo("نجاح","تم الحفظ"); dlg.destroy(); self.refresh()
            else: messagebox.showerror("خطأ",str(msg))
        tk.Button(form,text="➕",bg="#3b82f6",fg="white",bd=0,padx=10,pady=4,command=add_line).grid(row=0,column=6,padx=5)
        tk.Button(dlg,text="💾 حفظ القيد",bg="#10b981",fg="white",font=("Tahoma",11,"bold"),bd=0,pady=8,command=save).pack(fill="x",padx=15,pady=10)
    def view(self):
        e = self.sel(self.tv, self.data)
        if not e: return
        dlg = tk.Toplevel(self); dlg.title(f"القيد {e['ref']}"); dlg.geometry("700x400"); dlg.configure(bg="#f0f4f8")
        tv = ttk.Treeview(dlg,columns=("الحساب","مدين","دائن"),show="headings",height=12)
        for c,w in zip(("الحساب","مدين","دائن"),[350,120,120]):
            tv.heading(c,text=c); tv.column(c,width=w,anchor="center")
        tv.pack(fill="both",expand=True,padx=15,pady=15)
        for l in get_journal_lines(e["entry_id"]):
            tv.insert("","end",values=(f"{l['code']} - {l['acc_name']}",f"{l['debit']:,.2f}" if l["debit"] else "",f"{l['credit']:,.2f}" if l["credit"] else ""))

class ItemsFrame(BaseFrame):
    def build(self):
        self.title_bar("الأصناف",[("➕ إضافة",self.add,"#10b981"),("🗑️ حذف",self.del_,"#ef4444")])
        cols = ("#","الكود","الاسم","الوحدة","الفئة","التكلفة","السعر","حد الطلب")
        self.tv,_ = self.make_tree(cols,[40,90,250,70,100,90,90,90]); self.data = []
    def refresh(self):
        self.data = get_items()
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,it in enumerate(self.data):
            self.tv.insert("","end",values=(i+1,it["code"],it["name"],it["unit"],it["category"] or "",
                          f"{it['cost']:,.2f}",f"{it['price']:,.2f}",f"{it['reorder_level']:,.0f}"),tags=("even" if i%2 else "odd",))
    def add(self):
        dlg = tk.Toplevel(self); dlg.title("صنف جديد"); dlg.geometry("420x420+500+150"); dlg.configure(bg="#f0f4f8"); dlg.grab_set()
        f = tk.Frame(dlg,bg="#f0f4f8"); f.pack(fill="both",expand=True,padx=20,pady=15)
        entries = {}
        for i,(l,k) in enumerate([("الكود","code"),("الاسم","name"),("الوحدة","unit"),("الفئة","cat"),
                                    ("التكلفة","cost"),("السعر","price"),("حد الطلب","reorder")]):
            tk.Label(f,text=l,bg="#f0f4f8").grid(row=i,column=1,sticky="e",pady=4)
            e = ttk.Entry(f,justify="right"); e.grid(row=i,column=0,pady=4,sticky="ew"); entries[k] = e
        f.columnconfigure(0,weight=1)
        def save():
            try:
                c = get_conn()
                c.execute("INSERT INTO items(code,name,unit,category,cost,price,reorder_level) VALUES (?,?,?,?,?,?,?)",
                          (entries["code"].get(),entries["name"].get(),entries["unit"].get(),entries["cat"].get(),
                           float(entries["cost"].get() or 0),float(entries["price"].get() or 0),float(entries["reorder"].get() or 0)))
                c.commit(); c.close(); dlg.destroy(); self.refresh()
            except Exception as e: messagebox.showerror("خطأ",str(e))
        tk.Button(f,text="حفظ",bg="#10b981",fg="white",bd=0,pady=8,command=save).grid(row=7,column=0,columnspan=2,pady=15,sticky="ew")
    def del_(self):
        it = self.sel(self.tv, self.data)
        if not it: return
        if messagebox.askyesno("تأكيد",f"حذف {it['name']}؟"):
            c = get_conn()
            if c.execute("SELECT COUNT(*) c FROM inventory_trans WHERE item_id=?", (it["item_id"],)).fetchone()["c"]:
                messagebox.showerror("خطأ","الصنف مستخدم"); c.close(); return
            c.execute("DELETE FROM stock WHERE item_id=?", (it["item_id"],))
            c.execute("DELETE FROM items WHERE item_id=?", (it["item_id"],))
            c.commit(); c.close(); self.refresh()

class WarehousesFrame(BaseFrame):
    def build(self):
        self.title_bar("المخازن",[("➕ إضافة",self.add,"#10b981")])
        cols = ("#","الكود","الاسم","الموقع")
        self.tv,_ = self.make_tree(cols,[50,120,300,300]); self.data = []
    def refresh(self):
        c = get_conn(); self.data = [dict(r) for r in c.execute("SELECT * FROM warehouses").fetchall()]; c.close()
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,w in enumerate(self.data):
            self.tv.insert("","end",values=(i+1,w["code"],w["name"],w["location"] or ""),tags=("even" if i%2 else "odd",))
    def add(self):
        dlg = tk.Toplevel(self); dlg.title("مخزن جديد"); dlg.geometry("350x250+550+250"); dlg.configure(bg="#f0f4f8"); dlg.grab_set()
        f = tk.Frame(dlg,bg="#f0f4f8"); f.pack(fill="both",expand=True,padx=20,pady=15)
        for l in ["الكود","الاسم","الموقع"]:
            tk.Label(f,text=l,bg="#f0f4f8").pack(anchor="e")
            e = ttk.Entry(f,justify="right"); e.pack(fill="x",pady=3)
            if l=="الكود": code = e
            elif l=="الاسم": name = e
            else: loc = e
        def save():
            c = get_conn()
            try:
                c.execute("INSERT INTO warehouses(code,name,location) VALUES (?,?,?)", (code.get(),name.get(),loc.get()))
                c.commit(); c.close(); dlg.destroy(); self.refresh()
            except Exception as e: messagebox.showerror("خطأ",str(e))
        tk.Button(f,text="حفظ",bg="#10b981",fg="white",bd=0,pady=8,command=save).pack(fill="x",pady=10)

class PartiesFrame(BaseFrame):
    def build(self):
        self.title_bar("العملاء والموردون",[("➕ عميل",lambda:self.add("CUSTOMER"),"#10b981"),
                                             ("➕ مورد",lambda:self.add("SUPPLIER"),"#3b82f6"),
                                             ("🗑️ حذف",self.del_,"#ef4444")])
        cols = ("#","الكود","النوع","الاسم","الهاتف","الرصيد")
        self.tv,_ = self.make_tree(cols,[50,100,100,250,130,120]); self.data = []
    def refresh(self):
        self.data = get_parties()
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,p in enumerate(self.data):
            t = "عميل" if p["type"]=="CUSTOMER" else "مورد"
            self.tv.insert("","end",values=(i+1,p["code"],t,p["name"],p["phone"] or "",f"{p['balance']:,.2f}"),tags=("even" if i%2 else "odd",))
    def add(self, t):
        dlg = tk.Toplevel(self); dlg.title("جهة جديدة"); dlg.geometry("420x380+500+200"); dlg.configure(bg="#f0f4f8"); dlg.grab_set()
        f = tk.Frame(dlg,bg="#f0f4f8"); f.pack(fill="both",expand=True,padx=20,pady=15)
        entries = {}
        for i,(l,k) in enumerate([("الكود","code"),("الاسم","name"),("الهاتف","phone"),("البريد","email"),("العنوان","addr")]):
            tk.Label(f,text=l,bg="#f0f4f8").grid(row=i,column=1,sticky="e",pady=4)
            e = ttk.Entry(f,justify="right"); e.grid(row=i,column=0,pady=4,sticky="ew"); entries[k] = e
        f.columnconfigure(0,weight=1)
        def save():
            c = get_conn()
            try:
                c.execute("INSERT INTO parties(code,type,name,phone,email,address) VALUES (?,?,?,?,?,?)",
                          (entries["code"].get(),t,entries["name"].get(),entries["phone"].get(),
                           entries["email"].get(),entries["addr"].get()))
                c.commit(); c.close(); dlg.destroy(); self.refresh()
            except Exception as e: messagebox.showerror("خطأ",str(e))
        tk.Button(f,text="حفظ",bg="#10b981",fg="white",bd=0,pady=8,command=save).grid(row=5,column=0,columnspan=2,pady=15,sticky="ew")
    def del_(self):
        p = self.sel(self.tv, self.data)
        if not p: return
        if messagebox.askyesno("تأكيد",f"حذف {p['name']}؟"):
            c = get_conn()
            c.execute("DELETE FROM parties WHERE party_id=?", (p["party_id"],)); c.commit(); c.close(); self.refresh()

class InventoryFrame(BaseFrame):
    def build(self):
        self.title_bar("المخزون الحالي")
        cols = ("#","كود الصنف","الصنف","المخزن","الكمية","الوحدة","حد الطلب","الحالة")
        self.tv,_ = self.make_tree(cols,[40,90,250,130,100,70,90,100]); self.data = []
    def refresh(self):
        self.data = get_stock()
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,s in enumerate(self.data):
            status = "✅" if s["quantity"] > s["reorder_level"] else "⚠️ منخفض"
            self.tv.insert("","end",values=(i+1,s["code"],s["iname"],s["wname"],f"{s['quantity']:,.2f}",
                          s["unit"],f"{s['reorder_level']:,.0f}",status),tags=("even" if i%2 else "odd",))

class InvoiceDialog(tk.Toplevel):
    def __init__(self, parent, kind):
        super().__init__(parent); self.kind = kind
        self.title("فاتورة مبيعات" if kind=="SALE" else "فاتورة مشتريات")
        self.geometry("900x600+250+120"); self.configure(bg="#f0f4f8"); self.grab_set()
        self.lines = []
        self.parties = get_parties("CUSTOMER" if kind=="SALE" else "SUPPLIER")
        self.items = get_items()
        c = get_conn(); self.warehouses = [dict(r) for r in c.execute("SELECT * FROM warehouses").fetchall()]; c.close()
        self._build()
    def _build(self):
        top = tk.Frame(self,bg="#f0f4f8"); top.pack(fill="x",padx=15,pady=10)
        lbl = "العميل" if self.kind=="SALE" else "المورد"
        tk.Label(top,text=lbl,bg="#f0f4f8").grid(row=0,column=0,padx=5)
        self.pv = tk.StringVar()
        self.pc = ttk.Combobox(top,textvariable=self.pv,state="readonly",width=30,justify="right")
        self.pc["values"] = [f"{p['code']} - {p['name']}" for p in self.parties]
        self.pc.grid(row=0,column=1,padx=5)
        tk.Label(top,text="المخزن",bg="#f0f4f8").grid(row=0,column=2,padx=5)
        self.wv = tk.StringVar()
        self.wc = ttk.Combobox(top,textvariable=self.wv,state="readonly",width=20,justify="right")
        self.wc["values"] = [f"{w['code']} - {w['name']}" for w in self.warehouses]
        if self.warehouses: self.wc.current(0)
        self.wc.grid(row=0,column=3,padx=5)
        tk.Label(top,text="الدفع",bg="#f0f4f8").grid(row=0,column=4,padx=5)
        self.pm = tk.StringVar(value="نقداً")
        ttk.Combobox(top,textvariable=self.pm,values=["نقداً","آجل","شيك","تحويل"],state="readonly",width=12,justify="right").grid(row=0,column=5,padx=5)
        form = tk.Frame(self,bg="#e2e8f0",pady=8); form.pack(fill="x",padx=15,pady=5)
        tk.Label(form,text="الصنف",bg="#e2e8f0").grid(row=0,column=0,padx=3)
        self.iv = tk.StringVar()
        self.ic = ttk.Combobox(form,textvariable=self.iv,width=30,justify="right")
        self.ic["values"] = [f"{i['code']} - {i['name']}" for i in self.items]
        self.ic.grid(row=0,column=1,padx=3)
        tk.Label(form,text="الكمية",bg="#e2e8f0").grid(row=0,column=2,padx=3)
        self.qe = ttk.Entry(form,width=10,justify="right"); self.qe.grid(row=0,column=3,padx=3)
        tk.Label(form,text="السعر",bg="#e2e8f0").grid(row=0,column=4,padx=3)
        self.pe = ttk.Entry(form,width=10,justify="right"); self.pe.grid(row=0,column=5,padx=3)
        tk.Button(form,text="➕",bg="#3b82f6",fg="white",bd=0,padx=10,pady=4,command=self.add_line).grid(row=0,column=6,padx=5)
        self.tv = ttk.Treeview(self,columns=("الصنف","الكمية","السعر","الإجمالي"),show="headings",height=10)
        for c,w in zip(("الصنف","الكمية","السعر","الإجمالي"),[350,80,100,120]):
            self.tv.heading(c,text=c); self.tv.column(c,width=w,anchor="center")
        self.tv.pack(fill="both",expand=True,padx=15,pady=10)
        bot = tk.Frame(self,bg="#f0f4f8"); bot.pack(fill="x",padx=15,pady=5)
        tk.Label(bot,text="الضريبة %",bg="#f0f4f8").pack(side="right",padx=3)
        self.tax = ttk.Entry(bot,width=6,justify="right"); self.tax.insert(0,"0"); self.tax.pack(side="right",padx=3)
        tk.Label(bot,text="خصم",bg="#f0f4f8").pack(side="right",padx=3)
        self.disc = ttk.Entry(bot,width=10,justify="right"); self.disc.insert(0,"0"); self.disc.pack(side="right",padx=3)
        tk.Label(bot,text="مدفوع",bg="#f0f4f8").pack(side="right",padx=3)
        self.paid = ttk.Entry(bot,width=12,justify="right"); self.paid.insert(0,"0"); self.paid.pack(side="right",padx=3)
        self.tot = tk.Label(self,text="الإجمالي: 0.00",bg="#f0f4f8",font=("Tahoma",14,"bold"),fg="#1e293b")
        self.tot.pack(pady=5)
        tk.Button(self,text="💾 حفظ",bg="#10b981",fg="white",font=("Tahoma",12,"bold"),bd=0,pady=10,
                  command=self.save).pack(fill="x",padx=15,pady=10)
        self.ic.bind("<<ComboboxSelected>>",self.on_item)
    def on_item(self, e=None):
        s = self.iv.get()
        if not s: return
        code = s.split(" - ")[0]
        it = next((i for i in self.items if i["code"]==code),None)
        if it:
            self.pe.delete(0,"end"); self.pe.insert(0, str(it["price"] if self.kind=="SALE" else it["cost"]))
    def add_line(self):
        try:
            s = self.iv.get()
            if not s: return
            code = s.split(" - ")[0]
            it = next((i for i in self.items if i["code"]==code),None)
            if not it: return
            q = float(self.qe.get() or 0); p = float(self.pe.get() or 0)
            if q<=0: return
            self.lines.append({"item_id":it["item_id"],"quantity":q,"price":p,"discount":0})
            self.tv.insert("","end",values=(f"{it['code']} - {it['name']}",f"{q:,.2f}",f"{p:,.2f}",f"{q*p:,.2f}"))
            self.qe.delete(0,"end"); self.iv.set(""); self._upd()
        except: pass
    def _upd(self):
        sub = sum(l["quantity"]*l["price"] for l in self.lines)
        t = float(self.tax.get() or 0); d = float(self.disc.get() or 0)
        self.tot.config(text=f"الإجمالي: {sub + sub*t/100 - d:,.2f}")
    def save(self):
        if not self.lines: messagebox.showwarning("تنبيه","أضف أصنافاً"); return
        try:
            pv = self.pv.get(); pid = None
            if pv:
                code = pv.split(" - ")[0]
                p = next((x for x in self.parties if x["code"]==code),None)
                if p: pid = p["party_id"]
            wv = self.wv.get(); wid = None
            if wv:
                code = wv.split(" - ")[0]
                w = next((x for x in self.warehouses if x["code"]==code),None)
                if w: wid = w["wh_id"]
            args = (pid, self.lines, wid, self.pm.get(), float(self.paid.get() or 0),
                    float(self.tax.get() or 0), float(self.disc.get() or 0), self.master.app.user["user_id"])
            ok,msg = create_sale(*args) if self.kind=="SALE" else create_purchase(*args)
            if ok: messagebox.showinfo("نجاح",f"تم: {msg}"); self.destroy(); self.master.refresh()
            else: messagebox.showerror("خطأ",str(msg))
        except Exception as e: messagebox.showerror("خطأ",str(e))

class SalesFrame(BaseFrame):
    def build(self):
        self.title_bar("المبيعات",[("➕ فاتورة جديدة",lambda:InvoiceDialog(self,"SALE"),"#10b981")])
        cols = ("#","رقم","التاريخ","العميل","الإجمالي","المدفوع","المتبقي")
        self.tv,_ = self.make_tree(cols,[40,100,100,250,100,100,100]); self.data = []
    def refresh(self):
        self.data = get_sales()
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,inv in enumerate(self.data):
            self.tv.insert("","end",values=(i+1,inv["inv_no"],inv["date"],inv["cname"] or "",
                          f"{inv['total']:,.2f}",f"{inv['paid']:,.2f}",f"{inv['total']-inv['paid']:,.2f}"),tags=("even" if i%2 else "odd",))

class PurchasesFrame(BaseFrame):
    def build(self):
        self.title_bar("المشتريات",[("➕ فاتورة جديدة",lambda:InvoiceDialog(self,"PURCHASE"),"#10b981")])
        cols = ("#","رقم","التاريخ","المورد","الإجمالي","المدفوع","المتبقي")
        self.tv,_ = self.make_tree(cols,[40,100,100,250,100,100,100]); self.data = []
    def refresh(self):
        self.data = get_purchases()
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,inv in enumerate(self.data):
            self.tv.insert("","end",values=(i+1,inv["inv_no"],inv["date"],inv["sname"] or "",
                          f"{inv['total']:,.2f}",f"{inv['paid']:,.2f}",f"{inv['total']-inv['paid']:,.2f}"),tags=("even" if i%2 else "odd",))

class EmployeesFrame(BaseFrame):
    def build(self):
        self.title_bar("الموظفون",[("➕ إضافة",self.add,"#10b981"),("🗑️ حذف",self.del_,"#ef4444")])
        cols = ("#","الكود","الاسم","الوظيفة","القسم","الأساسي","البدلات")
        self.tv,_ = self.make_tree(cols,[40,80,200,130,130,90,90]); self.data = []
    def refresh(self):
        self.data = get_employees()
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,e in enumerate(self.data):
            self.tv.insert("","end",values=(i+1,e["code"],e["name"],e["position"] or "",e["department"] or "",
                          f"{e['basic_salary']:,.2f}",f"{e['allowances']:,.2f}"),tags=("even" if i%2 else "odd",))
    def add(self):
        dlg = tk.Toplevel(self); dlg.title("موظف جديد"); dlg.geometry("420x480+500+150"); dlg.configure(bg="#f0f4f8"); dlg.grab_set()
        f = tk.Frame(dlg,bg="#f0f4f8"); f.pack(fill="both",expand=True,padx=20,pady=15)
        entries = {}
        for i,(l,k) in enumerate([("الكود","code"),("الاسم","name"),("الوظيفة","pos"),("القسم","dept"),
                                    ("الأساسي","basic"),("البدلات","allow"),("تاريخ التعيين","hire"),("الهاتف","phone")]):
            tk.Label(f,text=l,bg="#f0f4f8").grid(row=i,column=1,sticky="e",pady=4)
            e = ttk.Entry(f,justify="right"); e.grid(row=i,column=0,pady=4,sticky="ew"); entries[k] = e
        entries["hire"].insert(0,date.today().isoformat())
        f.columnconfigure(0,weight=1)
        def save():
            try:
                c = get_conn()
                c.execute("INSERT INTO employees(code,name,position,department,basic_salary,allowances,hire_date,phone) VALUES (?,?,?,?,?,?,?,?)",
                          (entries["code"].get(),entries["name"].get(),entries["pos"].get(),entries["dept"].get(),
                           float(entries["basic"].get() or 0),float(entries["allow"].get() or 0),
                           entries["hire"].get(),entries["phone"].get()))
                c.commit(); c.close(); dlg.destroy(); self.refresh()
            except Exception as e: messagebox.showerror("خطأ",str(e))
        tk.Button(f,text="حفظ",bg="#10b981",fg="white",bd=0,pady=8,command=save).grid(row=8,column=0,columnspan=2,pady=15,sticky="ew")
    def del_(self):
        e = self.sel(self.tv, self.data)
        if not e: return
        if messagebox.askyesno("تأكيد",f"حذف {e['name']}؟"):
            c = get_conn(); c.execute("DELETE FROM employees WHERE emp_id=?", (e["emp_id"],)); c.commit(); c.close(); self.refresh()

class PayrollFrame(BaseFrame):
    def build(self):
        self.title_bar("الرواتب",[("➕ تشغيل مسير",self.run,"#10b981"),("💵 دفع قسيمة",self.pay,"#3b82f6")])
        top = tk.Frame(self,bg="#f0f4f8"); top.pack(fill="x",padx=15)
        tk.Label(top,text="الفترة YYYY-MM",bg="#f0f4f8").pack(side="right",padx=5)
        self.period = ttk.Entry(top,width=15,justify="center"); self.period.insert(0,date.today().strftime("%Y-%m"))
        self.period.pack(side="right",padx=5)
        tk.Button(top,text="بحث",bg="#64748b",fg="white",bd=0,padx=10,pady=3,command=self.refresh).pack(side="right",padx=5)
        cols = ("#","الكود","الموظف","الفترة","الأساسي","البدلات","الخصومات","الصافي","مدفوع")
        self.tv,_ = self.make_tree(cols,[40,80,180,100,90,90,90,100,80]); self.data = []
    def refresh(self):
        p = self.period.get().strip() or None
        self.data = get_payroll(p)
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,x in enumerate(self.data):
            self.tv.insert("","end",values=(i+1,x["code"],x["ename"],x["period"],f"{x['basic']:,.2f}",
                          f"{x['allowances']:,.2f}",f"{x['deductions']:,.2f}",f"{x['net']:,.2f}",
                          "✅" if x["paid"] else "❌"),tags=("even" if i%2 else "odd",))
    def run(self):
        p = simpledialog.askstring("مسير رواتب","الفترة (YYYY-MM):",parent=self)
        if not p: return
        n,t = run_payroll(p); messagebox.showinfo("نتيجة",f"تم إنشاء {n} قسيمة، الإجمالي {t:,.2f}")
        self.period.delete(0,"end"); self.period.insert(0,p); self.refresh()
    def pay(self):
        x = self.sel(self.tv, self.data)
        if not x: return
        ok,msg = pay_payroll(x["payroll_id"], self.app.user["user_id"])
        if not ok: messagebox.showerror("خطأ",msg)
        self.refresh()

class AssetsFrame(BaseFrame):
    def build(self):
        self.title_bar("الأصول الثابتة",[("➕ إضافة",self.add,"#10b981"),("📉 إهلاك",self.dep,"#3b82f6"),("🗑️ حذف",self.del_,"#ef4444")])
        cols = ("#","الكود","الاسم","الفئة","التاريخ","التكلفة","شهري","المجمع","الدفترية")
        self.tv,_ = self.make_tree(cols,[40,80,200,100,100,100,80,100,120]); self.data = []
    def refresh(self):
        self.data = get_assets()
        for r in self.tv.get_children(): self.tv.delete(r)
        for i,a in enumerate(self.data):
            self.tv.insert("","end",values=(i+1,a["code"],a["name"],a["category"] or "",a["purchase_date"] or "",
                          f"{a['cost']:,.2f}",f"{monthly_dep(a):,.2f}",f"{a['accumulated']:,.2f}",
                          f"{a['cost']-a['accumulated']:,.2f}"),tags=("even" if i%2 else "odd",))
    def add(self):
        dlg = tk.Toplevel(self); dlg.title("أصل جديد"); dlg.geometry("420x420+500+180"); dlg.configure(bg="#f0f4f8"); dlg.grab_set()
        f = tk.Frame(dlg,bg="#f0f4f8"); f.pack(fill="both",expand=True,padx=20,pady=15)
        entries = {}
        for i,(l,k) in enumerate([("الكود","code"),("الاسم","name"),("الفئة","cat"),("تاريخ الشراء","pdate"),
                                    ("التكلفة","cost"),("الإنقاذ","salv"),("العمر سنوات","life")]):
            tk.Label(f,text=l,bg="#f0f4f8").grid(row=i,column=1,sticky="e",pady=4)
            e = ttk.Entry(f,justify="right"); e.grid(row=i,column=0,pady=4,sticky="ew"); entries[k] = e
        entries["pdate"].insert(0,date.today().isoformat()); entries["life"].insert(0,"5")
        f.columnconfigure(0,weight=1)
        def save():
            try:
                c = get_conn()
                c.execute("INSERT INTO fixed_assets(code,name,category,purchase_date,cost,salvage,life_years,method) VALUES (?,?,?,?,?,?,?, 'straight')",
                          (entries["code"].get(),entries["name"].get(),entries["cat"].get(),entries["pdate"].get(),
                           float(entries["cost"].get() or 0),float(entries["salv"].get() or 0),int(entries["life"].get() or 5)))
                c.commit(); c.close(); dlg.destroy(); self.refresh()
            except Exception as e: messagebox.showerror("خطأ",str(e))
        tk.Button(f,text="حفظ",bg="#10b981",fg="white",bd=0,pady=8,command=save).grid(row=7,column=0,columnspan=2,pady=15,sticky="ew")
    def dep(self):
        a = self.sel(self.tv, self.data)
        if not a: return
        m = simpledialog.askinteger("إهلاك","عدد الأشهر:",initialvalue=1,parent=self)
        if not m: return
        ok,msg = post_dep(a["asset_id"], m, self.app.user["user_id"])
        if ok: messagebox.showinfo("نجاح",msg)
        else: messagebox.showerror("خطأ",msg)
        self.refresh()
    def del_(self):
        a = self.sel(self.tv, self.data)
        if not a: return
        if messagebox.askyesno("تأكيد",f"حذف {a['name']}؟"):
            c = get_conn(); c.execute("DELETE FROM fixed_assets WHERE asset_id=?", (a["asset_id"],)); c.commit(); c.close(); self.refresh()

class ReportsFrame(BaseFrame):
    def build(self):
        self.title_bar("التقارير",[("ميزان المراجعة",self.tb,"#3b82f6"),("قائمة الدخل",self.inc,"#10b981"),
                                    ("الميزانية",self.bs,"#8b5cf6"),("نواقص المخزون",self.low,"#dc2626")])
        tk.Label(self,text="📊 اختر تقريراً من الأعلى",bg="#f0f4f8",fg="#64748b",font=("Tahoma",14)).pack(pady=50)
    def show(self, title, cols, rows, widths=None):
        w = tk.Toplevel(self); w.title(title); w.geometry("1000x600+200+120"); w.configure(bg="#f0f4f8")
        tv = ttk.Treeview(w,columns=cols,show="headings",height=20)
        for i,c in enumerate(cols):
            tv.heading(c,text=c); tv.column(c,width=widths[i] if widths else 130,anchor="center")
        sb = ttk.Scrollbar(w,orient="vertical",command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side="right",fill="both",expand=True,padx=15,pady=15); sb.pack(side="right",fill="y",pady=15)
        for i,r in enumerate(rows): tv.insert("","end",values=r,tags=("even" if i%2 else "odd",))
    def tb(self):
        f = simpledialog.askstring("من","YYYY-MM-DD:",initialvalue=date.today().replace(day=1).isoformat(),parent=self)
        if not f: return
        t = simpledialog.askstring("إلى","YYYY-MM-DD:",initialvalue=date.today().isoformat(),parent=self)
        if not t: return
        rows = trial_balance(f,t)
        data = [(r["code"],r["name"],r["type"],f"{r['debit']:,.2f}",f"{r['credit']:,.2f}",
                 f"{r['debit']-r['credit']:,.2f}") for r in rows]
        self.show(f"ميزان المراجعة {f} → {t}",("الكود","الاسم","النوع","مدين","دائن","الرصيد"),data)
    def inc(self):
        f = simpledialog.askstring("من","YYYY-MM-DD:",initialvalue=date.today().replace(month=1,day=1).isoformat(),parent=self)
        if not f: return
        t = simpledialog.askstring("إلى","YYYY-MM-DD:",initialvalue=date.today().isoformat(),parent=self)
        if not t: return
        rev,exp = income_stmt(f,t)
        rows = [("——— الإيرادات ———","")]
        for r in rev: rows.append((r["name"],f"{r['amount']:,.2f}"))
        tr = sum(r["amount"] for r in rev); rows.append(("إجمالي الإيرادات",f"{tr:,.2f}"))
        rows.append(("——— المصروفات ———",""))
        for e in exp: rows.append((e["name"],f"{e['amount']:,.2f}"))
        te = sum(e["amount"] for e in exp); rows.append(("إجمالي المصروفات",f"{te:,.2f}"))
        rows.append(("صافي الربح",f"{tr-te:,.2f}"))
        self.show(f"قائمة الدخل {f} → {t}",("البند","المبلغ"),rows)
    def bs(self):
        t = simpledialog.askstring("حتى","YYYY-MM-DD:",initialvalue=date.today().isoformat(),parent=self)
        if not t: return
        A,L,E = balance_sheet(t); rows = [("——— الأصول ———","")]
        for x in A: rows.append((x["name"],f"{x['amount']:,.2f}"))
        rows.append(("إجمالي الأصول",f"{sum(x['amount'] for x in A):,.2f}"))
        rows.append(("——— الخصوم ———",""))
        for x in L: rows.append((x["name"],f"{x['amount']:,.2f}"))
        rows.append(("إجمالي الخصوم",f"{sum(x['amount'] for x in L):,.2f}"))
        rows.append(("——— حقوق الملكية ———",""))
        for x in E: rows.append((x["name"],f"{x['amount']:,.2f}"))
        self.show(f"الميزانية {t}",("البند","المبلغ"),rows)
    def low(self):
        rows = low_stock()
        data = [(r["code"],r["name"],f"{r['qty']:,.2f}",f"{r['reorder_level']:,.2f}") for r in rows]
        self.show("نواقص المخزون",("الكود","الصنف","الكمية","حد الطلب"),data)

class SettingsFrame(BaseFrame):
    def build(self):
        self.title_bar("الإعدادات المحاسبية")
        self.f = tk.Frame(self,bg="#f0f4f8"); self.f.pack(fill="both",expand=True,padx=20,pady=15)
        self.accounts = get_accounts(leaf_only=True)
        self.entries = {}
        fields = [("حساب الصندوق","account_cash"),("حساب العملاء","account_ar"),("حساب الموردين","account_ap"),
                  ("حساب المبيعات","account_sales"),("حساب الضريبة","account_tax"),("حساب المخزون","account_inventory"),
                  ("تكلفة المبيعات","account_cogs"),("مصروف الرواتب","account_salary_expense"),
                  ("مصروف الإهلاك","account_depreciation_expense"),("مجمع الإهلاك","account_accumulated_dep"),
                  ("الأصول الثابتة","account_fixed_assets")]
        for i,(l,k) in enumerate(fields):
            tk.Label(self.f,text=l,bg="#f0f4f8").grid(row=i,column=1,sticky="e",pady=4,padx=10)
            cb = ttk.Combobox(self.f,width=50,justify="right")
            cb["values"] = [f"{a['code']} - {a['name']}" for a in self.accounts]
            cb.grid(row=i,column=0,sticky="ew",pady=4); self.entries[k] = cb
        self.f.columnconfigure(0,weight=1)
        tk.Button(self.f,text="💾 حفظ",bg="#10b981",fg="white",font=("Tahoma",12,"bold"),bd=0,pady=8,
                  command=self.save).grid(row=len(fields),column=0,columnspan=2,pady=20,sticky="ew")
    def refresh(self):
        for k,cb in self.entries.items():
            c = get_conn(); r = c.execute("SELECT value FROM settings WHERE key=?", (k,)).fetchone(); c.close()
            if r and r["value"]:
                a = next((x for x in self.accounts if x["account_id"]==int(r["value"])),None)
                if a: cb.set(f"{a['code']} - {a['name']}")
    def save(self):
        c = get_conn()
        for k,cb in self.entries.items():
            s = cb.get()
            if s:
                code = s.split(" - ")[0]
                a = next((x for x in self.accounts if x["code"]==code),None)
                if a: c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)", (k, str(a["account_id"])))
        c.commit(); c.close(); messagebox.showinfo("نجاح","تم الحفظ")

# ============ Login & App ============
class LoginWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master); self.user = None
        self.title("تسجيل الدخول"); self.configure(bg="#0f172a"); self.resizable(False,False); self.grab_set()
        tk.Label(self,text="ERP PRO",bg="#0f172a",fg="#38bdf8",font=("Tahoma",26,"bold")).pack(pady=(30,5))
        tk.Label(self,text="نظام تخطيط موارد المؤسسات",bg="#0f172a",fg="#94a3b8",font=("Tahoma",11)).pack()
        f = tk.Frame(self,bg="#0f172a"); f.pack(pady=20,padx=40,fill="x")
        tk.Label(f,text="اسم المستخدم",bg="#0f172a",fg="white").pack(anchor="e")
        self.u = ttk.Entry(f,font=("Tahoma",12),justify="right"); self.u.pack(fill="x",pady=5)
        tk.Label(f,text="كلمة المرور",bg="#0f172a",fg="white").pack(anchor="e")
        self.p = ttk.Entry(f,show="*",font=("Tahoma",12),justify="right"); self.p.pack(fill="x",pady=5)
        tk.Button(f,text="دخول",bg="#0ea5e9",fg="white",font=("Tahoma",12,"bold"),bd=0,pady=10,
                  command=self.do).pack(fill="x",pady=15)
        self.u.insert(0,"admin"); self.p.insert(0,"admin"); self.p.bind("<Return>",lambda e:self.do())
        self.update_idletasks()
        x = (self.winfo_screenwidth()-420)//2; y = (self.winfo_screenheight()-340)//2
        self.geometry(f"420x340+{x}+{y}")
    def do(self):
        u = login(self.u.get().strip(), self.p.get().strip())
        if u: self.user = u; self.destroy()
        else: messagebox.showerror("خطأ","بيانات غير صحيحة",parent=self)

class ERPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ERP Professional v3.0")
        self.geometry("1300x780"); self.configure(bg="#f0f4f8")
        try: self.state('zoomed')
        except: pass
        self.withdraw(); self.user = None
        lg = LoginWindow(self); self.wait_window(lg)
        if lg.user:
            self.user = lg.user; self.deiconify(); self._ui()
        else: self.destroy()
    def _ui(self):
        side = tk.Frame(self,bg="#1e293b",width=230); side.pack(side="right",fill="y"); side.pack_propagate(False)
        h = tk.Frame(side,bg="#1e293b"); h.pack(fill="x",pady=(15,10))
        tk.Label(h,text="ERP PRO",bg="#1e293b",fg="#38bdf8",font=("Tahoma",18,"bold")).pack()
        tk.Label(h,text=self.user["full_name"] or self.user["username"],bg="#1e293b",fg="#94a3b8").pack()
        self.main = tk.Frame(self,bg="#f0f4f8"); self.main.pack(side="left",fill="both",expand=True)
        self.frames = {}; self.cur = None
        menu = [("🏠 لوحة التحكم","dash",DashboardFrame),("📒 دليل الحسابات","acc",AccountsFrame),
                ("📝 القيود اليومية","jr",JournalFrame),("📦 الأصناف","it",ItemsFrame),
                ("🏬 المخازن","wh",WarehousesFrame),("👥 العملاء والموردون","pt",PartiesFrame),
                ("📊 المخزون","inv",InventoryFrame),("💰 المبيعات","sl",SalesFrame),
                ("🛒 المشتريات","pu",PurchasesFrame),("🧑‍💼 الموظفون","emp",EmployeesFrame),
                ("💵 الرواتب","pay",PayrollFrame),("🏢 الأصول الثابتة","as",AssetsFrame),
                ("📈 التقارير","rp",ReportsFrame),("⚙️ الإعدادات","st",SettingsFrame)]
        canvas = tk.Canvas(side,bg="#1e293b",highlightthickness=0)
        sb = tk.Scrollbar(side,orient="vertical",command=canvas.yview)
        inner = tk.Frame(canvas,bg="#1e293b")
        inner.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0),window=inner,anchor="nw",width=210)
        canvas.configure(yscrollcommand=sb.set); canvas.pack(side="top",fill="both",expand=True,padx=5)
        for lbl,k,cls in menu:
            tk.Button(inner,text=lbl,bg="#334155",fg="white",font=("Tahoma",11),bd=0,height=2,
                      anchor="e",padx=15,activebackground="#0ea5e9",cursor="hand2",
                      command=lambda k=k,c=cls:self.show(k,c)).pack(fill="x",padx=2,pady=2)
        tk.Button(side,text="🚪 خروج",bg="#dc2626",fg="white",font=("Tahoma",11,"bold"),bd=0,height=2,
                  command=self.destroy).pack(fill="x",padx=5,pady=10,side="bottom")
        self.show("dash",DashboardFrame)
    def show(self, k, cls):
        if self.cur and self.cur in self.frames: self.frames[self.cur].pack_forget()
        if k not in self.frames: self.frames[k] = cls(self.main, self)
        self.frames[k].pack(fill="both",expand=True); self.cur = k
        try: self.frames[k].refresh()
        except: pass
    def refresh(self):
        if self.cur in self.frames:
            try: self.frames[self.cur].refresh()
            except: pass

# ============ Main ============
if __name__ == "__main__":
    init_db()
    app = ERPApp()
    app.mainloop()
