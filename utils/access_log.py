#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
访问日志模块

负责记录项目访问日志，包括访问时间、IP地址、请求类型等信息
"""

import os
import json
import time
import datetime
import sqlite3

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'access_logs.db')

# 确保数据目录存在
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    """初始化数据库，创建访问日志表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建访问日志表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS access_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        access_time TIMESTAMP NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        request_method TEXT,
        endpoint TEXT,
        params TEXT,
        status_code INTEGER,
        response_time REAL,
        user_id TEXT
    )
    ''')
    
    # 创建项目统计表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS project_stats (
        project_id TEXT PRIMARY KEY,
        last_access TIMESTAMP,
        total_accesses INTEGER DEFAULT 0,
        api_accesses INTEGER DEFAULT 0,
        web_accesses INTEGER DEFAULT 0,
        unique_ips INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()

def log_access(project_id, ip_address, user_agent=None, request_method=None, 
               endpoint=None, params=None, status_code=200, response_time=0, user_id=None):
    """
    记录项目访问日志
    
    Args:
        project_id: 项目ID
        ip_address: 访问者IP地址
        user_agent: 用户代理信息
        request_method: 请求方法（GET/POST等）
        endpoint: 访问的端点
        params: 请求参数（字典形式）
        status_code: 响应状态码
        response_time: 响应时间（秒）
        user_id: 用户ID（如果已登录）
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 记录访问日志
        cursor.execute('''
        INSERT INTO access_logs (
            project_id, access_time, ip_address, user_agent, request_method, 
            endpoint, params, status_code, response_time, user_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id, 
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
            ip_address,
            user_agent,
            request_method,
            endpoint,
            json.dumps(params) if params else None,
            status_code,
            response_time,
            user_id
        ))
        
        # 更新项目统计
        is_api = endpoint and '/api/' in endpoint
        
        # 检查项目是否已存在统计记录
        cursor.execute('SELECT * FROM project_stats WHERE project_id = ?', (project_id,))
        project_stat = cursor.fetchone()
        
        if project_stat:
            # 更新现有记录
            cursor.execute('''
            UPDATE project_stats SET 
                last_access = ?, 
                total_accesses = total_accesses + 1,
                api_accesses = api_accesses + ? 
            WHERE project_id = ?
            ''', (
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                1 if is_api else 0,
                project_id
            ))
        else:
            # 创建新记录
            cursor.execute('''
            INSERT INTO project_stats (
                project_id, last_access, total_accesses, api_accesses, web_accesses
            ) VALUES (?, ?, 1, ?, ?)
            ''', (
                project_id,
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                1 if is_api else 0,
                0 if is_api else 1
            ))
        
        conn.commit()
        
        # 更新唯一IP数量（这是CPU密集型操作，可以考虑异步执行）
        cursor.execute('''
        SELECT COUNT(DISTINCT ip_address) FROM access_logs WHERE project_id = ?
        ''', (project_id,))
        unique_ips = cursor.fetchone()[0]
        
        cursor.execute('''
        UPDATE project_stats SET unique_ips = ? WHERE project_id = ?
        ''', (unique_ips, project_id))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"记录访问日志时出错: {str(e)}")
        return False

def get_project_access_logs(project_id, limit=100, offset=0):
    """
    获取项目的访问日志
    
    Args:
        project_id: 项目ID
        limit: 返回记录数量限制
        offset: 分页偏移量
        
    Returns:
        访问日志列表
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # 启用行工厂，使结果可以通过列名访问
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM access_logs 
        WHERE project_id = ? 
        ORDER BY access_time DESC
        LIMIT ? OFFSET ?
        ''', (project_id, limit, offset))
        
        logs = [dict(row) for row in cursor.fetchall()]
        
        # 获取记录总数
        cursor.execute('SELECT COUNT(*) FROM access_logs WHERE project_id = ?', (project_id,))
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'logs': logs,
            'total': total_count,
            'limit': limit,
            'offset': offset
        }
    except Exception as e:
        print(f"获取访问日志时出错: {str(e)}")
        return {
            'logs': [],
            'total': 0,
            'limit': limit,
            'offset': offset
        }

def get_project_stats(project_id=None):
    """
    获取项目访问统计
    
    Args:
        project_id: 项目ID，如果为None则返回所有项目的统计
        
    Returns:
        项目统计信息
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if project_id:
            cursor.execute('SELECT * FROM project_stats WHERE project_id = ?', (project_id,))
            result = cursor.fetchone()
            stats = dict(result) if result else None
        else:
            cursor.execute('SELECT * FROM project_stats ORDER BY last_access DESC')
            stats = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return stats
    except Exception as e:
        print(f"获取项目统计时出错: {str(e)}")
        return [] if project_id is None else None

def get_project_ip_stats(project_id, limit=10):
    """
    获取项目访问IP统计
    
    Args:
        project_id: 项目ID
        limit: 返回前N个最活跃的IP
        
    Returns:
        IP访问统计列表
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT ip_address, COUNT(*) as count 
        FROM access_logs 
        WHERE project_id = ? 
        GROUP BY ip_address 
        ORDER BY count DESC
        LIMIT ?
        ''', (project_id, limit))
        
        ip_stats = [{'ip': row[0], 'count': row[1]} for row in cursor.fetchall()]
        conn.close()
        
        return ip_stats
    except Exception as e:
        print(f"获取IP统计时出错: {str(e)}")
        return []

# 初始化数据库
init_db() 