#!/usr/bin/env python3
"""
测试数据库连接的简单脚本
"""
import sys
import os
import configparser
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pymysql
from pymysql.cursors import DictCursor

def test_connection():
    """测试数据库连接"""
    # 读取配置文件
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    if os.path.exists(config_path):
        config.read(config_path, encoding='utf-8')
        db_config = dict(config['database'])
        # 清理引号和逗号
        for key, value in db_config.items():
            db_config[key] = value.strip('"\'').rstrip(',')
    else:
        print("❌ 配置文件config.ini不存在，使用默认配置")
        db_config = {
            'host': '3.76.79.249',
            'port': '3306',
            'user': 'getBYemsData',
            'password': 'getBYemsData',
            'db': 'getBYemsData'
        }
    
    connection = None
    try:
        print("正在测试数据库连接...")
        print(f"服务器: {db_config['host']}:{db_config['port']}")
        print(f"数据库: {db_config['db']}")
        print(f"用户: {db_config['user']}")
        
        connection = pymysql.connect(
            host=db_config['host'],
            port=int(db_config['port']),
            user=db_config['user'],
            password=db_config['password'],
            db=db_config['db'],
            charset='utf8mb4',
            cursorclass=DictCursor,
            connect_timeout=10
        )
        
        print("✅ 数据库连接成功！")
        
        # 测试查询
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            result = cursor.fetchone()
            print(f"MySQL版本: {result['VERSION()']}")
            
            cursor.execute("SELECT DATABASE()")
            result = cursor.fetchone()
            print(f"当前数据库: {result['DATABASE()']}")
            
            cursor.execute("SELECT USER()")
            result = cursor.fetchone()
            print(f"当前用户: {result['USER()']}")
            
            # 测试表是否存在
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"数据库中的表数量: {len(tables)}")
            if tables:
                print("表列表:")
                for table in tables:
                    table_name = list(table.values())[0]
                    print(f"  - {table_name}")
            else:
                print("数据库中没有表")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        return False
        
    finally:
        if connection:
            connection.close()
            print("连接已关闭")

if __name__ == "__main__":
    test_connection()