#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
远程API客户端示例

此脚本演示如何通过HTTP API接口远程加载项目配置
"""

import os
import sys
import json
import argparse
import requests
from pprint import pprint

class RemoteConfigClient:
    """远程配置客户端类，用于通过API接口访问配置服务器"""
    
    def __init__(self, api_url, api_key):
        """
        初始化远程配置客户端
        
        Args:
            api_url: API服务器的基础URL，例如 http://localhost:5500
            api_key: 用于API认证的密钥
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
    
    def get_projects(self):
        """
        获取所有可用的项目列表
        
        Returns:
            项目列表，每个项目包含id、name等信息
        """
        url = f"{self.api_url}/api/projects"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return []
        
        data = response.json()
        if not data.get('success', False):
            print(f"API错误: {data.get('message', '未知错误')}")
            return []
        
        return data.get('projects', [])
    
    def get_project_config(self, project_id):
        """
        获取指定项目的完整配置
        
        Args:
            project_id: 项目ID
        
        Returns:
            包含项目信息和配置数据的字典
        """
        url = f"{self.api_url}/api/projects/{project_id}/config"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        if not data.get('success', False):
            print(f"API错误: {data.get('message', '未知错误')}")
            return None
        
        return data.get('project')
    
    def get_config_value(self, project_id, config_path):
        """
        获取指定项目的特定配置项的值
        
        Args:
            project_id: 项目ID
            config_path: 配置路径，例如 system.key.gpt_api_key 或 config.attribute.name
        
        Returns:
            配置项的值
        """
        url = f"{self.api_url}/api/projects/{project_id}/config/{config_path}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        if not data.get('success', False):
            print(f"API错误: {data.get('message', '未知错误')}")
            return None
        
        return data.get('config_value')
    
    def update_config_value(self, project_id, config_path, value):
        """
        更新指定项目的特定配置项的值
        
        Args:
            project_id: 项目ID
            config_path: 配置路径，例如 system.key.gpt_api_key 或 config.attribute.name
            value: 新的配置值
        
        Returns:
            是否更新成功
        """
        url = f"{self.api_url}/api/projects/{project_id}/config/{config_path}"
        payload = {
            'value': value
        }
        
        response = requests.put(url, headers=self.headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return False
        
        data = response.json()
        if not data.get('success', False):
            print(f"API错误: {data.get('message', '未知错误')}")
            return False
        
        return True
    
    def get_project_logs(self, project_id, limit=100, offset=0):
        """
        获取项目的访问日志
        
        Args:
            project_id: 项目ID
            limit: 返回记录数量限制
            offset: 分页偏移量
            
        Returns:
            访问日志数据
        """
        url = f"{self.api_url}/api/projects/{project_id}/logs"
        params = {
            'limit': limit,
            'offset': offset
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        if not data.get('success', False):
            print(f"API错误: {data.get('message', '未知错误')}")
            return None
        
        return data.get('logs')
    
    def get_project_stats(self, project_id):
        """
        获取项目的访问统计
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目访问统计数据
        """
        url = f"{self.api_url}/api/projects/{project_id}/stats"
        
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return None
        
        data = response.json()
        if not data.get('success', False):
            print(f"API错误: {data.get('message', '未知错误')}")
            return None
        
        return {
            'stats': data.get('stats'),
            'ip_stats': data.get('ip_stats')
        }

def list_projects(client):
    """显示所有项目列表"""
    print("\n===== 项目列表 =====")
    projects = client.get_projects()
    
    if not projects:
        print("没有找到任何项目")
        return
    
    for i, project in enumerate(projects, 1):
        print(f"{i}. ID: {project['id']}")
        print(f"   名称: {project['name']}")
        print(f"   描述: {project['description']}")
        print(f"   创建时间: {project['created_at']}")
        print("")

def show_project_config(client, project_id):
    """显示项目的完整配置"""
    print(f"\n===== 项目配置: {project_id} =====")
    project = client.get_project_config(project_id)
    
    if not project:
        print(f"找不到项目: {project_id}")
        return
    
    print(f"项目名称: {project['name']}")
    print(f"项目描述: {project['description']}")
    
    print("\n系统配置:")
    pprint(project['system_config'])
    
    print("\n用户配置:")
    pprint(project['config_json'])

def get_specific_config(client, project_id, config_path):
    """获取特定配置项的值"""
    print(f"\n===== 获取配置项: {config_path} =====")
    value = client.get_config_value(project_id, config_path)
    
    if value is None:
        print(f"找不到配置项: {config_path}")
        return
    
    print(f"配置路径: {config_path}")
    print(f"配置值: {value}")

def update_specific_config(client, project_id, config_path, value):
    """更新特定配置项的值"""
    print(f"\n===== 更新配置项: {config_path} =====")
    success = client.update_config_value(project_id, config_path, value)
    
    if success:
        print(f"成功更新配置: {config_path} = {value}")
    else:
        print(f"更新配置失败: {config_path}")

def text_to_speech_example(client, project_id, text):
    """使用远程配置的TTS演示"""
    print(f"\n===== TTS演示 =====")
    # 获取TTS模块配置
    tts_module = client.get_config_value(project_id, 'tts_module')
    
    if not tts_module:
        print("无法获取TTS模块配置")
        return
    
    print(f"使用 {tts_module} 进行文本转语音:")
    print(f"文本: {text}")
    
    if tts_module == 'azure':
        # 获取微软TTS配置
        ms_tts_key = client.get_config_value(project_id, 'system.key.ms_tts_key')
        ms_tts_region = client.get_config_value(project_id, 'system.key.ms_tts_region')
        print(f"Azure TTS配置: Key={ms_tts_key[:5]}..., Region={ms_tts_region}")
    elif tts_module == 'ali':
        # 获取阿里云TTS配置
        ali_tss_key_id = client.get_config_value(project_id, 'system.key.ali_tss_key_id')
        ali_tss_key_secret = client.get_config_value(project_id, 'system.key.ali_tss_key_secret')
        ali_tss_app_key = client.get_config_value(project_id, 'system.key.ali_tss_app_key')
        print(f"阿里云TTS配置: KeyID={ali_tss_key_id[:5]}..., Secret={ali_tss_key_secret[:5]}..., AppKey={ali_tss_app_key[:5]}...")
    
    # 获取角色名称
    name = client.get_config_value(project_id, 'config.attribute.name')
    print(f"角色名称: {name}")
    
    # 这里是模拟TTS流程，实际应用中会调用相应的API
    print(f"TTS转换成功!")

def show_project_logs(client, project_id, limit=20):
    """显示项目访问日志"""
    print(f"\n===== 项目访问日志: {project_id} =====")
    
    # 获取项目统计
    stats_data = client.get_project_stats(project_id)
    if not stats_data:
        print(f"找不到项目统计: {project_id}")
        return
    
    stats = stats_data['stats']
    ip_stats = stats_data['ip_stats']
    
    # 显示统计信息
    print("\n访问统计:")
    print(f"总访问次数: {stats['total_accesses']}")
    print(f"API访问次数: {stats['api_accesses']}")
    print(f"Web访问次数: {stats['web_accesses']}")
    print(f"唯一IP数: {stats['unique_ips']}")
    print(f"最后访问时间: {stats['last_access']}")
    
    # 显示IP统计
    print("\nIP统计 (Top 10):")
    for ip in ip_stats:
        percent = (ip['count'] / stats['total_accesses'] * 100) if stats['total_accesses'] > 0 else 0
        print(f"{ip['ip']}: {ip['count']}次 ({percent:.2f}%)")
    
    # 显示访问日志
    logs = client.get_project_logs(project_id, limit)
    if not logs:
        print("\n暂无访问日志")
        return
    
    print(f"\n最近 {min(limit, len(logs['logs']))} 条访问日志:")
    for log in logs['logs']:
        print(f"{log['access_time']} | {log['ip_address']} | {log['request_method']} | {log['endpoint']} | {log['status_code']} | {log['response_time']*1000:.2f}ms")
    
    print(f"\n共 {logs['total']} 条记录")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='远程配置API客户端示例')
    parser.add_argument('--url', '-u', type=str, default='http://localhost:5500',
                        help='API服务器URL，默认为http://localhost:5500')
    parser.add_argument('--key', '-k', type=str, default='your-api-key-here',
                        help='API认证密钥')
    parser.add_argument('--action', '-a', type=str, choices=['list', 'get', 'config', 'update', 'tts', 'logs'],
                        default='list', help='操作类型')
    parser.add_argument('--project', '-p', type=str, help='项目ID')
    parser.add_argument('--path', type=str, help='配置路径')
    parser.add_argument('--value', '-v', type=str, help='配置值')
    parser.add_argument('--text', '-t', type=str, default='今天天气真好，阳光明媚。',
                        help='TTS示例的文本')
    parser.add_argument('--limit', '-l', type=int, default=20,
                        help='日志条数限制')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 创建远程配置客户端
    client = RemoteConfigClient(args.url, args.key)
    
    # 根据操作类型执行相应的功能
    if args.action == 'list':
        list_projects(client)
    elif args.action == 'config':
        if not args.project:
            print("错误: 必须指定项目ID")
            return
        show_project_config(client, args.project)
    elif args.action == 'get':
        if not args.project or not args.path:
            print("错误: 必须指定项目ID和配置路径")
            return
        get_specific_config(client, args.project, args.path)
    elif args.action == 'update':
        if not args.project or not args.path or args.value is None:
            print("错误: 必须指定项目ID、配置路径和配置值")
            return
        update_specific_config(client, args.project, args.path, args.value)
    elif args.action == 'tts':
        if not args.project:
            print("错误: 必须指定项目ID")
            return
        text_to_speech_example(client, args.project, args.text)
    elif args.action == 'logs':
        if not args.project:
            print("错误: 必须指定项目ID")
            return
        show_project_logs(client, args.project, args.limit)

if __name__ == "__main__":
    main() 