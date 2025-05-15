#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
多项目配置示例脚本

此脚本演示如何在多个项目中使用修改后的config_util.py模块加载不同的配置文件。
"""

import os
import sys
import threading
import time

# 将父目录添加到导入路径，以便导入utils模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import config_util

def print_config_info(project_path, project_name):
    """打印指定项目的配置信息"""
    print(f"\n{'='*20} {project_name} 配置信息 {'='*20}")
    
    try:
        # 加载项目配置
        config_dict = config_util.load_project_config(project_path)
        
        # 打印系统配置中的几个关键项
        print(f"ASR模式: {config_dict['ASR_mode']}")
        print(f"TTS模块: {config_dict['tts_module']}")
        print(f"聊天模块: {config_dict['chat_module']}")
        
        # 打印用户配置中的几个关键项
        user_config = config_dict['config']
        print(f"名称: {user_config['attribute']['name']}")
        print(f"性别: {user_config['attribute']['gender']}")
        print(f"工作: {user_config['attribute']['job']}")
        
        print(f"配置加载成功: {project_path}")
    except Exception as e:
        print(f"加载配置出错: {str(e)}")

def thread_worker(project_path, project_name):
    """线程工作函数，设置当前项目并使用配置"""
    # 设置当前线程使用的项目
    config_util.set_current_project(project_path)
    
    # 获取配置值示例
    print(f"\n线程 {threading.current_thread().name} 使用项目 {project_name}")
    print(f"ASR模式: {config_util.get_config_value('ASR_mode')}")
    print(f"名称: {config_util.get_config_value('config.attribute.name')}")
    
    # 使用系统配置中的ASR模式决定使用哪种服务
    asr_mode = config_util.get_config_value('ASR_mode')
    if asr_mode == 'ali':
        # 获取阿里云ASR配置
        key_id = config_util.get_config_value('ali_nls_key_id')
        key_secret = config_util.get_config_value('ali_nls_key_secret')
        app_key = config_util.get_config_value('ali_nls_app_key')
        print(f"使用阿里云ASR服务: KeyID={key_id[:5]}..., Secret={key_secret[:5]}..., AppKey={app_key[:5]}...")
    elif asr_mode == 'funasr':
        # 获取FunASR配置
        ip = config_util.get_config_value('local_asr_ip')
        port = config_util.get_config_value('local_asr_port')
        print(f"使用FunASR服务: IP={ip}, Port={port}")
    else:
        print(f"未知的ASR模式: {asr_mode}")

def main():
    """主函数"""
    # 项目路径列表 - 在实际使用中，这些路径会指向不同的远程项目目录
    projects = [
        {"path": ".", "name": "当前项目"},
        {"path": "./projects/project1", "name": "项目1"},
        {"path": "./projects/project2", "name": "项目2"},
    ]
    
    # 创建示例项目目录结构
    setup_example_projects()
    
    # 顺序加载和打印每个项目的配置
    for project in projects:
        print_config_info(project["path"], project["name"])
    
    # 演示在多线程环境中使用不同项目配置
    threads = []
    for project in projects:
        thread = threading.Thread(
            target=thread_worker,
            args=(project["path"], project["name"]),
            name=f"Thread-{project['name']}"
        )
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    print("\n所有项目配置加载完成！")

def setup_example_projects():
    """设置示例项目目录结构"""
    # 创建项目目录
    os.makedirs('./projects/project1', exist_ok=True)
    os.makedirs('./projects/project2', exist_ok=True)
    
    # 复制系统配置文件到项目目录
    copy_with_modifications('system.conf', './projects/project1/system.conf', {
        'ASR_mode = ali': 'ASR_mode = funasr',
        'tts_module=azure': 'tts_module=ali',
        'ollama_model = deepseek-r1:1.5b': 'ollama_model = llama2:latest'
    })
    
    copy_with_modifications('system.conf', './projects/project2/system.conf', {
        'ASR_mode = ali': 'ASR_mode = sensevoice',
        'tts_module=azure': 'tts_module=gptsovits',
        'chat_module = cognitive_stream': 'chat_module = gpt_stream'
    })
    
    # 复制JSON配置文件到项目目录
    copy_with_modifications('config.json', './projects/project1/config.json', {
        '"name": "\\u83f2\\u83f2"': '"name": "小艾"',
        '"gender": "\\u5973"': '"gender": "女"',
        '"job": "\\u52a9\\u7406"': '"job": "秘书"'
    })
    
    copy_with_modifications('config.json', './projects/project2/config.json', {
        '"name": "\\u83f2\\u83f2"': '"name": "小明"',
        '"gender": "\\u5973"': '"gender": "男"',
        '"job": "\\u52a9\\u7406"': '"job": "助手"'
    })

def copy_with_modifications(src_file, dest_file, replacements):
    """复制文件并进行内容替换"""
    try:
        # 读取源文件内容
        with open(src_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 进行内容替换
        for old_text, new_text in replacements.items():
            content = content.replace(old_text, new_text)
        
        # 写入目标文件
        with open(dest_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"已创建示例文件: {dest_file}")
    except Exception as e:
        print(f"创建示例文件失败 {dest_file}: {str(e)}")

if __name__ == "__main__":
    main() 