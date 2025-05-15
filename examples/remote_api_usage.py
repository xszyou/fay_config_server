#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
远程配置API使用示例

此脚本演示如何通过HTTP API获取远程项目配置。
"""

import os
import sys
import argparse
import requests
import json

def print_separator():
    """打印分隔线"""
    print('-' * 80)

def get_projects(api_url, api_key):
    """获取所有项目列表"""
    headers = {
        'X-API-Key': api_key
    }
    
    response = requests.get(f"{api_url}/api/projects", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            return data.get('projects', [])
        else:
            print(f"获取项目列表失败: {data.get('message', '未知错误')}")
    else:
        print(f"请求失败，状态码: {response.status_code}")
    
    return []

def get_project_config(api_url, api_key, project_id):
    """获取完整项目配置"""
    headers = {
        'X-API-Key': api_key
    }
    
    response = requests.get(f"{api_url}/api/projects/{project_id}/config", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            return data
        else:
            print(f"获取项目配置失败: {data.get('message', '未知错误')}")
    else:
        print(f"请求失败，状态码: {response.status_code}")
    
    return None

def get_config_value(api_url, api_key, project_id, config_key):
    """获取单个配置值"""
    headers = {
        'X-API-Key': api_key
    }
    
    response = requests.get(
        f"{api_url}/api/projects/{project_id}/config/value",
        headers=headers,
        params={'key': config_key}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            return data.get('value')
        else:
            print(f"获取配置值失败: {data.get('message', '未知错误')}")
    else:
        print(f"请求失败，状态码: {response.status_code}")
    
    return None

def get_multiple_config_values(api_url, api_key, project_id, config_keys):
    """批量获取多个配置值"""
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        f"{api_url}/api/projects/{project_id}/config/values",
        headers=headers,
        json={'keys': config_keys}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            return data.get('values', {})
        else:
            print(f"批量获取配置值失败: {data.get('message', '未知错误')}")
    else:
        print(f"请求失败，状态码: {response.status_code}")
    
    return {}

def text_to_speech_demo(api_url, api_key, project_id, text):
    """演示使用远程配置进行TTS处理"""
    # 获取TTS相关配置
    tts_config_keys = [
        'tts_module',
        'ali_tss_key_id',
        'ali_tss_key_secret',
        'ali_tss_app_key',
        'ms_tts_key',
        'ms_tts_region'
    ]
    
    tts_configs = get_multiple_config_values(api_url, api_key, project_id, tts_config_keys)
    
    tts_module = tts_configs.get('tts_module')
    if not tts_module:
        print("错误: 无法获取TTS模块配置")
        return
    
    print(f"使用 {tts_module} 进行文本转语音:")
    print(f"文本: {text}")
    
    if tts_module == 'azure':
        key = tts_configs.get('ms_tts_key')
        region = tts_configs.get('ms_tts_region')
        print(f"Azure TTS 配置: Key={key[:5] if key else 'N/A'}..., Region={region}")
    elif tts_module == 'ali':
        key_id = tts_configs.get('ali_tss_key_id')
        key_secret = tts_configs.get('ali_tss_key_secret')
        app_key = tts_configs.get('ali_tss_app_key')
        print(f"阿里云TTS配置: KeyID={key_id[:5] if key_id else 'N/A'}..., Secret={key_secret[:5] if key_secret else 'N/A'}..., AppKey={app_key[:5] if app_key else 'N/A'}...")
    else:
        print(f"使用其他TTS模块: {tts_module}")
    
    # 这里是模拟TTS流程，实际应用中会调用相应的API
    print(f"TTS转换成功！")

def chat_with_ai_demo(api_url, api_key, project_id, input_text):
    """演示使用远程配置进行AI对话"""
    # 获取聊天相关配置
    chat_config_keys = [
        'chat_module',
        'gpt_api_key',
        'gpt_model_engine',
        'config.attribute.name'
    ]
    
    chat_configs = get_multiple_config_values(api_url, api_key, project_id, chat_config_keys)
    
    chat_module = chat_configs.get('chat_module')
    if not chat_module:
        print("错误: 无法获取聊天模块配置")
        return
    
    print(f"使用 {chat_module} 进行AI对话:")
    print(f"用户输入: {input_text}")
    
    # 获取角色名称
    character_name = chat_configs.get('config.attribute.name')
    
    if chat_module == 'cognitive_stream':
        print(f"{character_name}: 我正在使用认知流模型处理您的请求。")
    elif chat_module == 'gpt_stream':
        gpt_api_key = chat_configs.get('gpt_api_key')
        gpt_model = chat_configs.get('gpt_model_engine')
        print(f"GPT配置: API Key={gpt_api_key[:5] if gpt_api_key else 'N/A'}..., Model={gpt_model}")
        print(f"{character_name}: 我正在使用GPT模型回答您的问题。")
    else:
        print(f"{character_name}: 我正在使用{chat_module}模型处理您的请求。")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='远程配置API使用示例')
    parser.add_argument('--url', type=str, default='http://localhost:5500',
                        help='配置服务器API URL')
    parser.add_argument('--key', type=str, required=True,
                        help='API密钥')
    parser.add_argument('--project', type=str, help='项目ID（如果不指定，将列出所有项目）')
    parser.add_argument('--action', type=str, choices=['list', 'config', 'tts', 'chat'], default='list',
                        help='要执行的操作: list=列出项目, config=获取配置, tts=文本转语音演示, chat=AI对话演示')
    
    args = parser.parse_args()
    
    if args.action == 'list':
        # 获取并列出所有项目
        projects = get_projects(args.url, args.key)
        if projects:
            print(f"可用项目列表 ({len(projects)}):")
            for i, project in enumerate(projects, 1):
                print(f"{i}. {project['name']} (ID: {project['id']})")
                print(f"   描述: {project['description']}")
                print(f"   创建时间: {project['created_at']}")
                print()
        else:
            print("没有找到可用的项目")
    
    elif args.action == 'config':
        # 获取项目完整配置
        if not args.project:
            print("错误: 必须指定项目ID")
            return
        
        config_data = get_project_config(args.url, args.key, args.project)
        if config_data:
            project_info = config_data['project']
            print(f"项目: {project_info['name']} (ID: {project_info['id']})")
            print(f"描述: {project_info['description']}")
            print(f"创建时间: {project_info['created_at']}")
            
            print_separator()
            print("系统配置:")
            for section, keys in config_data['system_config'].items():
                print(f"[{section}]")
                for key, value in keys.items():
                    # 敏感信息显示前几个字符
                    if key in ['key_id', 'key_secret', 'api_key', 'app_key']:
                        value_display = f"{value[:5]}..." if value and len(value) > 5 else value
                    else:
                        value_display = value
                    print(f"  {key} = {value_display}")
                print()
            
            print_separator()
            print("用户配置:")
            print(json.dumps(config_data['config_json'], indent=2, ensure_ascii=False))
    
    elif args.action == 'tts':
        # TTS演示
        if not args.project:
            print("错误: 必须指定项目ID")
            return
        
        text_to_speech_demo(args.url, args.key, args.project, "今天天气真好，阳光明媚，适合出门散步。")
    
    elif args.action == 'chat':
        # 聊天演示
        if not args.project:
            print("错误: 必须指定项目ID")
            return
        
        chat_with_ai_demo(args.url, args.key, args.project, "你好，今天天气怎么样？")

if __name__ == "__main__":
    main() 