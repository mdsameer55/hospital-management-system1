import mysql.connector
from mysql.connector import pooling
from config import Config
_pool=None
def init_pool():
 global _pool
 if _pool is None:
  _pool=pooling.MySQLConnectionPool(pool_name='hms_pool',pool_size=5,host=Config.DB_HOST,port=Config.DB_PORT,user=Config.DB_USER,password=Config.DB_PASSWORD,database=Config.DB_NAME)
def get_connection():
 if _pool is None: init_pool()
 return _pool.get_connection()
def fetch(sql,args=(),one=False):
 c=get_connection(); cur=c.cursor(dictionary=True)
 try:
  cur.execute(sql,args); return cur.fetchone() if one else cur.fetchall()
 finally: cur.close(); c.close()
def execute(sql,args=()):
 c=get_connection(); cur=c.cursor()
 try:
  cur.execute(sql,args); c.commit(); return cur.lastrowid
 except: c.rollback(); raise
 finally: cur.close(); c.close()
