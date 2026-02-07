# config/__init__.py
import pymysql

# Instala o PyMySQL como se fosse o MySQLdb
pymysql.install_as_MySQLdb()

# --- O TRUQUE ---
# Enganamos o Django definindo manualmente a versão do driver para uma aceita
import MySQLdb
MySQLdb.version_info = (2, 2, 7, 'final', 0)
MySQLdb.__version__ = '2.2.7'