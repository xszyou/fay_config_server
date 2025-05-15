#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
远程项目配置使用示例

此脚本演示如何在实际应用中使用修改后的config_util.py模块加载远程项目的配置文件。
"""

import os
import sys
import argparse

# 将父目录添加到导入路径，以便导入utils模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import config_util

def text_to_speech(text, project_path=None):
    """根据配置设置将文本转换为语音"""
    # 获取TTS模块配置
    tts_module = config_util.get_config_value('tts_module', project_path=project_path)
    
    print(f"使用 {tts_module} 进行文本转语音:")
    print(f"文本: {text}")
    
    if tts_module == 'azure':
        # 获取Azure TTS配置
        key = config_util.get_config_value('ms_tts_key', project_path=project_path)
        region = config_util.get_config_value('ms_tts_region', project_path=project_path)
        print(f"Azure TTS 配置: Key={key[:5]}..., Region={region}")
    elif tts_module == 'ali':
        # 获取阿里云TTS配置
        key_id = config_util.get_config_value('ali_tss_key_id', project_path=project_path)
        key_secret = config_util.get_config_value('ali_tss_key_secret', project_path=project_path)
        app_key = config_util.get_config_value('ali_tss_app_key', project_path=project_path)
        print(f"阿里云TTS配置: KeyID={key_id[:5]}..., Secret={key_secret[:5]}..., AppKey={app_key[:5]}...")
    else:
        print(f"使用其他TTS模块: {tts_module}")
    
    # 这里是模拟TTS流程，实际应用中会调用相应的API
    print(f"TTS转换成功！")

def chat_with_ai(input_text, project_path=None):
    """根据配置设置与AI聊天"""
    # 获取聊天模块配置
    chat_module = config_util.get_config_value('chat_module', project_path=project_path)
    
    print(f"使用 {chat_module} 进行AI对话:")
    print(f"用户输入: {input_text}")
    
    # 获取角色名称
    character_name = config_util.get_config_value('config.attribute.name', project_path=project_path)
    
    if chat_module == 'cognitive_stream':
        print(f"{character_name}: 我正在使用认知流模型处理您的请求。")
    elif chat_module == 'gpt_stream':
        # 获取GPT配置
        gpt_api_key = config_util.get_config_value('gpt_api_key', project_path=project_path)
        gpt_model = config_util.get_config_value('gpt_model_engine', project_path=project_path)
        print(f"GPT配置: API Key={gpt_api_key[:5]}..., Model={gpt_model}")
        print(f"{character_name}: 我正在使用GPT模型回答您的问题。")
    else:
        print(f"{character_name}: 我正在使用{chat_module}模型处理您的请求。")

def speech_recognition(audio_file_path, project_path=None):
    """根据配置设置进行语音识别"""
    # 获取ASR模式配置
    asr_mode = config_util.get_config_value('ASR_mode', project_path=project_path)
    
    print(f"使用 {asr_mode} 进行语音识别:")
    print(f"音频文件: {audio_file_path}")
    
    if asr_mode == 'ali':
        # 获取阿里云ASR配置
        key_id = config_util.get_config_value('ali_nls_key_id', project_path=project_path)
        key_secret = config_util.get_config_value('ali_nls_key_secret', project_path=project_path)
        app_key = config_util.get_config_value('ali_nls_app_key', project_path=project_path)
        print(f"阿里云ASR配置: KeyID={key_id[:5]}..., Secret={key_secret[:5]}..., AppKey={app_key[:5]}...")
    elif asr_mode == 'funasr':
        # 获取FunASR配置
        ip = config_util.get_config_value('local_asr_ip', project_path=project_path)
        port = config_util.get_config_value('local_asr_port', project_path=project_path)
        print(f"FunASR配置: IP={ip}, Port={port}")
    else:
        print(f"使用其他ASR模式: {asr_mode}")
    
    # 这里是模拟语音识别流程，实际应用中会调用相应的API
    print(f"识别结果: 你好，我想问一下天气怎么样？")
    return "你好，我想问一下天气怎么样？"

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='远程项目配置使用示例')
    parser.add_argument('--project', '-p', type=str, required=True, help='项目配置目录路径')
    parser.add_argument('--action', '-a', type=str, choices=['tts', 'chat', 'asr', 'all'], default='all', 
                        help='要执行的动作: tts=文本转语音, chat=AI对话, asr=语音识别, all=所有动作')
    args = parser.parse_args()
    
    project_path = args.project
    
    # 检查项目配置目录是否存在
    if not os.path.exists(project_path):
        print(f"错误: 项目目录 '{project_path}' 不存在")
        return
    
    # 检查配置文件是否存在
    if not os.path.exists(os.path.join(project_path, 'system.conf')) or not os.path.exists(os.path.join(project_path, 'config.json')):
        print(f"错误: 项目目录 '{project_path}' 中缺少配置文件")
        return
    
    print(f"使用项目配置: {project_path}")
    
    # 加载项目配置
    try:
        config_dict = config_util.load_project_config(project_path)
        print(f"成功加载项目配置")
        
        # 打印基本配置信息
        character_name = config_dict['config']['attribute']['name']
        character_gender = config_dict['config']['attribute']['gender']
        character_job = config_dict['config']['attribute']['job']
        
        print(f"角色信息: 名称={character_name}, 性别={character_gender}, 工作={character_job}")
        print(f"系统配置: ASR模式={config_dict['ASR_mode']}, TTS模块={config_dict['tts_module']}, 聊天模块={config_dict['chat_module']}")
        print("-" * 50)
        
        # 根据用户选择执行对应的动作
        if args.action == 'tts' or args.action == 'all':
            text_to_speech("今天天气真好，阳光明媚，适合出门散步。", project_path)
            print("-" * 50)
        
        if args.action == 'asr' or args.action == 'all':
            recognized_text = speech_recognition("sample_audio.wav", project_path)
            print("-" * 50)
            
            # 如果用户选择了all，则将ASR结果传递给chat
            if args.action == 'all':
                chat_with_ai(recognized_text, project_path)
                print("-" * 50)
        
        if args.action == 'chat' and args.action != 'all':
            chat_with_ai("你好，今天天气怎么样？", project_path)
            print("-" * 50)
        
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main() 