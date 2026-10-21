import os

try:
    import pymysql
except ImportError:
    pymysql = None
else:
    pymysql.install_as_MySQLdb()

try:
    from dotenv import load_dotenv
except ImportError:
    pass
else:
    load_dotenv()