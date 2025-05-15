#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import uuid
import hashlib
import base64
import datetime
import codecs
import shutil
import time
from configparser import ConfigParser
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from functools import wraps
import utils.config_util as config_util
from utils import access_log

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', str(uuid.uuid4()))

# Configuration for the application
APP_CONFIG = {
    'PROJECTS_DIR': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'projects'),
    'ADMIN_USERNAME': 'admin',
    'ADMIN_PASSWORD': generate_password_hash('admin'),  # Default password, change in production
    'ENCRYPTION_KEY': Fernet.generate_key(),
    'API_KEY': 'your-api-key-here'
}

# Ensure projects directory exists
if not os.path.exists(APP_CONFIG['PROJECTS_DIR']):
    os.makedirs(APP_CONFIG['PROJECTS_DIR'])

# Ensure templates directory exists
if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')):
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))

# Encryption handler
fernet = Fernet(APP_CONFIG['ENCRYPTION_KEY'])

def encrypt_data(data):
    """Encrypt sensitive data"""
    if isinstance(data, str):
        return fernet.encrypt(data.encode()).decode()
    return data

def decrypt_data(data):
    """Decrypt encrypted data"""
    if isinstance(data, str):
        try:
            return fernet.decrypt(data.encode()).decode()
        except:
            return data
    return data

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == APP_CONFIG['ADMIN_USERNAME'] and check_password_hash(APP_CONFIG['ADMIN_PASSWORD'], password):
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    projects = []
    if os.path.exists(APP_CONFIG['PROJECTS_DIR']):
        for project_dir in os.listdir(APP_CONFIG['PROJECTS_DIR']):
            project_path = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_dir)
            if os.path.isdir(project_path):
                # Load project details
                project_config_path = os.path.join(project_path, 'project.json')
                if os.path.exists(project_config_path):
                    with open(project_config_path, 'r', encoding='utf-8') as f:
                        project_config = json.load(f)
                        projects.append({
                            'id': project_dir,
                            'name': project_config.get('name', project_dir),
                            'path': project_config.get('path', project_path)
                        })
    
    return render_template('dashboard.html', projects=projects)

@app.route('/project/new', methods=['GET', 'POST'])
@login_required
def new_project():
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        project_path = request.form.get('project_path')
        create_backup = request.form.get('create_backup') == 'on'
        
        if not project_name:
            flash('Project name is required', 'danger')
            return redirect(url_for('new_project'))
        
        # Create unique project ID
        project_id = str(uuid.uuid4())
        project_dir = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_id)
        
        # Create project directory
        os.makedirs(project_dir, exist_ok=True)
        
        # 创建项目特定的配置目录
        project_specific_dir = os.path.join(project_dir, 'config')
        os.makedirs(project_specific_dir, exist_ok=True)
        
        # Use current directory if no path provided
        source_path = project_path
        if not source_path:
            source_path = os.path.dirname(os.path.abspath(__file__))
        
        # Validate path exists
        if not os.path.exists(source_path):
            flash(f'Path {source_path} does not exist', 'danger')
            return redirect(url_for('new_project'))
            
        # Check if config files exist in source path
        source_system_conf_path = os.path.join(source_path, 'system.conf')
        source_config_json_path = os.path.join(source_path, 'config.json')
        
        target_system_conf_path = os.path.join(project_specific_dir, 'system.conf')
        target_config_json_path = os.path.join(project_specific_dir, 'config.json')
        
        if not os.path.exists(source_system_conf_path) and not os.path.exists(source_config_json_path):
            flash('Neither system.conf nor config.json found in the specified path', 'warning')
        

        # 复制配置文件到项目特定目录
        if os.path.exists(source_system_conf_path):
            shutil.copy2(source_system_conf_path, target_system_conf_path)
        
        if os.path.exists(source_config_json_path):
            shutil.copy2(source_config_json_path, target_config_json_path)
        
        # Initialize project config
        project_config = {
            'name': project_name,
            'path': project_specific_dir,  # 使用项目特定的配置目录
            'created_at': str(datetime.datetime.now()),
            'encrypted_keys': []
        }
        
        # Save project config
        with open(os.path.join(project_dir, 'project.json'), 'w', encoding='utf-8') as f:
            json.dump(project_config, f, indent=4)
        
        flash(f'Project "{project_name}" created successfully', 'success')
        return redirect(url_for('project_config', project_id=project_id))
    
    return render_template('new_project.html')

@app.route('/project/<project_id>/config', methods=['GET', 'POST'])
@login_required
def project_config(project_id):
    # 检查project_id是否为空
    if not project_id or project_id.strip() == '':
        flash('项目ID不能为空', 'danger')
        return redirect(url_for('dashboard'))
        
    project_dir = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_id)
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        flash(f'找不到项目目录: {project_dir}', 'danger')
        return redirect(url_for('dashboard'))
    
    project_config_path = os.path.join(project_dir, 'project.json')
    
    # 检查project.json文件是否存在
    if not os.path.exists(project_config_path):
        flash(f'找不到项目配置文件: {project_config_path}', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # 加载项目配置
        with open(project_config_path, 'r', encoding='utf-8') as f:
            project_config = json.load(f)
        
        # 确保project_config包含id字段
        project_config['id'] = project_id
    except Exception as e:
        flash(f'读取项目配置时出错: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    
    # 检查是否有项目特定的配置文件，如果没有，则创建
    project_specific_dir = os.path.join(project_dir, 'config')
    if not os.path.exists(project_specific_dir):
        os.makedirs(project_specific_dir, exist_ok=True)
    
    system_conf_path = os.path.join(project_specific_dir, 'system.conf')
    config_json_path = os.path.join(project_specific_dir, 'config.json')
    
    # 如果项目特定的配置文件不存在，但project_config['path']中有配置文件，则复制一份
    if not os.path.exists(system_conf_path) and os.path.exists(os.path.join(project_config['path'], 'system.conf')):
        shutil.copy2(os.path.join(project_config['path'], 'system.conf'), system_conf_path)
    
    if not os.path.exists(config_json_path) and os.path.exists(os.path.join(project_config['path'], 'config.json')):
        shutil.copy2(os.path.join(project_config['path'], 'config.json'), config_json_path)
    
    # 更新项目配置中的路径
    project_config['path'] = project_specific_dir
    
    # 保存更新后的项目配置
    with open(project_config_path, 'w', encoding='utf-8') as f:
        json.dump(project_config, f, indent=4)
        
    system_config = ConfigParser()
    if os.path.exists(system_conf_path):
        system_config.read(system_conf_path, encoding='UTF-8')
    
    config_json = {}
    if os.path.exists(config_json_path):
        try:
            with open(config_json_path, 'r', encoding='utf-8') as f:
                config_json = json.load(f)
        except Exception as e:
            flash(f'读取JSON配置时出错: {str(e)}', 'warning')
    
    if request.method == 'POST':
        # 检查是否是AJAX请求，通过检查X-Requested-With头或Accept头
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                 'application/json' in request.headers.get('Accept', '')
                 
        # Handle field management operations
        if 'field_management' in request.form:
            try:
                action = request.form.get('action')
                field_type = request.form.get('type')
                
                if action == 'add_update':
                    # Add or update a field
                    if field_type == 'system':
                        section = request.form.get('section')
                        key = request.form.get('key')
                        value = request.form.get('value')
                        
                        if not section or not key:
                            return jsonify({'success': False, 'message': 'Section and key are required'})
                        
                        # Create backup before making changes
                        backup_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                        if os.path.exists(system_conf_path):
                            shutil.copy2(system_conf_path, f"{system_conf_path}.{backup_time}.bak")
                        
                        # Create section if it doesn't exist
                        if not system_config.has_section(section):
                            system_config.add_section(section)
                        
                        # Set the value
                        system_config[section][key] = value
                        
                        # Save system.conf
                        with open(system_conf_path, 'w', encoding='UTF-8') as f:
                            system_config.write(f)
                        
                        return jsonify({
                            'success': True, 
                            'message': f'Field {section}.{key} added/updated successfully'
                        })
                        
                    elif field_type == 'config':
                        path = request.form.get('path', '')
                        key = request.form.get('key')
                        value = request.form.get('value')
                        
                        if not key:
                            return jsonify({'success': False, 'message': 'Key is required'})
                        
                        # Create backup before making changes
                        backup_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                        if os.path.exists(config_json_path):
                            shutil.copy2(config_json_path, f"{config_json_path}.{backup_time}.bak")
                        
                        # Convert value to appropriate type
                        try:
                            # Try to convert to number or boolean if applicable
                            if value.lower() == 'true':
                                converted_value = True
                            elif value.lower() == 'false':
                                converted_value = False
                            elif value.isdigit():
                                converted_value = int(value)
                            elif value.replace('.', '', 1).isdigit() and value.count('.') < 2:
                                converted_value = float(value)
                            else:
                                converted_value = value
                        except:
                            converted_value = value
                            
                        # Set the value in the JSON structure
                        if not path:
                            # Set at root level
                            config_json[key] = converted_value
                        else:
                            # Navigate the path
                            parts = path.split('.')
                            current = config_json
                            
                            # Navigate to the correct level
                            for part in parts:
                                if part not in current:
                                    current[part] = {}
                                current = current[part]
                            
                            # Set the value
                            current[key] = converted_value
                        
                        # Save config.json
                        with open(config_json_path, 'w', encoding='utf-8') as f:
                            json.dump(config_json, f, indent=4, ensure_ascii=False)
                        
                        return jsonify({
                            'success': True, 
                            'message': f'Field {path + "." if path else ""}{key} added/updated successfully',
                            'updated_json': config_json
                        })
                
                elif action == 'delete':
                    # Delete a field
                    if field_type == 'system':
                        section = request.form.get('section')
                        key = request.form.get('key')
                        
                        if not section or not key:
                            return jsonify({'success': False, 'message': 'Section and key are required'})
                        
                        # Create backup before making changes
                        backup_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                        if os.path.exists(system_conf_path):
                            shutil.copy2(system_conf_path, f"{system_conf_path}.{backup_time}.bak")
                        
                        # Check if section and key exist
                        if not system_config.has_section(section) or not system_config.has_option(section, key):
                            return jsonify({'success': False, 'message': f'Field {section}.{key} does not exist'})
                        
                        # Remove the option
                        system_config.remove_option(section, key)
                        
                        # If section is now empty, ask if we want to remove it too
                        if not system_config.options(section):
                            # You can decide whether to remove empty sections automatically
                            # For now, we'll keep them
                            pass
                        
                        # Save system.conf
                        with open(system_conf_path, 'w', encoding='UTF-8') as f:
                            system_config.write(f)
                        
                        return jsonify({
                            'success': True, 
                            'message': f'Field {section}.{key} deleted successfully'
                        })
                        
                    elif field_type == 'config':
                        path = request.form.get('path', '')
                        key = request.form.get('key')
                        
                        if not key:
                            return jsonify({'success': False, 'message': 'Key is required'})
                        
                        # Create backup before making changes
                        backup_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                        if os.path.exists(config_json_path):
                            shutil.copy2(config_json_path, f"{config_json_path}.{backup_time}.bak")
                        
                        # Delete the value from the JSON structure
                        if not path:
                            # Delete at root level
                            if key in config_json:
                                del config_json[key]
                            else:
                                return jsonify({'success': False, 'message': f'Field {key} does not exist'})
                        else:
                            # Navigate the path
                            parts = path.split('.')
                            current = config_json
                            
                            try:
                                # Navigate to the correct level
                                for part in parts:
                                    current = current[part]
                                
                                # Delete the key
                                if key in current:
                                    del current[key]
                                else:
                                    return jsonify({'success': False, 'message': f'Field {path}.{key} does not exist'})
                            except (KeyError, TypeError):
                                return jsonify({'success': False, 'message': f'Path {path} does not exist'})
                        
                        # Save config.json
                        with open(config_json_path, 'w', encoding='utf-8') as f:
                            json.dump(config_json, f, indent=4, ensure_ascii=False)
                        
                        return jsonify({
                            'success': True, 
                            'message': f'Field {path + "." if path else ""}{key} deleted successfully',
                            'updated_json': config_json
                        })
                
                return jsonify({'success': False, 'message': f'Unknown action: {action}'})
                
            except Exception as e:
                import traceback
                print(f"Field management error: {traceback.format_exc()}")
                
                return jsonify({
                    'success': False, 
                    'message': f'Error in field management: {str(e)}'
                })
            
        # Handle form submission for configuration updates
        if 'update_system_conf' in request.form:
            try:
                # Create backup before making changes
                backup_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                if os.path.exists(system_conf_path):
                    shutil.copy2(system_conf_path, f"{system_conf_path}.{backup_time}.bak")
                
                for section in system_config.sections():
                    for key in system_config[section]:
                        form_key = f"{section}_{key}"
                        if form_key in request.form:
                            value = request.form[form_key]
                            
                            # Remove encryption functionality
                            system_config[section][key] = value
                
                # Save system.conf
                with open(system_conf_path, 'w', encoding='UTF-8') as f:
                    system_config.write(f)
                
                # Update project config
                with open(os.path.join(project_dir, 'project.json'), 'w', encoding='utf-8') as f:
                    json.dump(project_config, f, indent=4)
                
                # 根据请求类型返回不同的响应
                message = 'System configuration updated successfully'
                if is_ajax:
                    return jsonify({'success': True, 'message': message})
                else:
                    flash(message, 'success')
                    return redirect(url_for('project_config', project_id=project_id))
            except Exception as e:
                message = f'Error updating system configuration: {str(e)}'
                if is_ajax:
                    return jsonify({'success': False, 'message': message})
                else:
                    flash(message, 'danger')
                    return redirect(url_for('project_config', project_id=project_id))
        
        if 'update_config_json' in request.form:
            try:
                # Create backup before making changes
                backup_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                if os.path.exists(config_json_path):
                    shutil.copy2(config_json_path, f"{config_json_path}.{backup_time}.bak")
                
                # Parse the JSON data from the form
                json_data = request.form.get('config_json_data')
                if not json_data:
                    message = 'JSON data is empty or missing'
                    if is_ajax:
                        return jsonify({'success': False, 'message': message})
                    else:
                        flash(message, 'danger')
                        return redirect(url_for('project_config', project_id=project_id))
                
                try:
                    updated_config = json.loads(json_data)
                except json.JSONDecodeError as e:
                    # 记录详细错误信息
                    print(f"JSON parse error: {str(e)}")
                    print(f"JSON data excerpt: {json_data[:100]}...")
                    
                    message = f'JSON parsing error: {str(e)}'
                    if is_ajax:
                        return jsonify({'success': False, 'message': message})
                    else:
                        flash(message, 'danger')
                        return redirect(url_for('project_config', project_id=project_id))
                
                # Save config.json
                try:
                    # 记录要保存的JSON结构
                    print(f"Saving JSON to {config_json_path}, keys: {list(updated_config.keys() if isinstance(updated_config, dict) else [])}")
                    
                    with open(config_json_path, 'w', encoding='utf-8') as f:
                        # 确保ensure_ascii=False以正确处理中文和特殊字符
                        json.dump(updated_config, f, indent=4, ensure_ascii=False)
                    
                    # 直接告知用户更新成功，不尝试重新加载配置
                    message = 'JSON configuration updated successfully'
                    
                    # Update local variable for display
                    config_json = updated_config
                    
                    # 根据请求类型返回不同的响应
                    if is_ajax:
                        return jsonify({'success': True, 'message': message})
                    else:
                        flash(message, 'success')
                        return redirect(url_for('project_config', project_id=project_id))
                except IOError as e:
                    message = f'Error writing to file: {str(e)}'
                    if is_ajax:
                        return jsonify({'success': False, 'message': message})
                    else:
                        flash(message, 'danger')
                        return redirect(url_for('project_config', project_id=project_id))
            except Exception as e:
                # 打印详细错误信息到控制台，便于调试
                import traceback
                print(f"JSON update error: {traceback.format_exc()}")
                
                message = f'Error updating JSON configuration: {str(e)}'
                if is_ajax:
                    return jsonify({'success': False, 'message': message})
                else:
                    flash(message, 'danger')
                    return redirect(url_for('project_config', project_id=project_id))
    
    return render_template('project_config.html', 
                          project=project_config,
                          system_config=system_config,
                          config_json=config_json)

@app.route('/project/<project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    # 检查project_id是否为空
    if not project_id:
        flash('项目ID不能为空', 'danger')
        return redirect(url_for('dashboard'))
        
    project_dir = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_id)
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        flash(f'找不到项目目录: {project_dir}', 'danger')
        return redirect(url_for('dashboard'))
    
    project_config_path = os.path.join(project_dir, 'project.json')
    
    # 检查project.json文件是否存在
    if not os.path.exists(project_config_path):
        # 如果配置文件不存在但目录存在，仍然尝试删除目录
        try:
            shutil.rmtree(project_dir)
            flash(f'已删除项目目录，但找不到项目配置文件', 'warning')
        except Exception as e:
            flash(f'删除项目目录时出错: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # 获取项目名称以用于闪现消息
        with open(project_config_path, 'r', encoding='utf-8') as f:
            project_config = json.load(f)
        project_name = project_config.get('name', project_id)
        
        # 删除项目目录
        shutil.rmtree(project_dir)
        
        flash(f'项目 "{project_name}" 已成功删除', 'success')
    except json.JSONDecodeError:
        # 如果无法解析JSON但目录存在，仍然尝试删除目录
        try:
            shutil.rmtree(project_dir)
            flash(f'已删除项目目录，但项目配置文件格式无效', 'warning')
        except Exception as e:
            flash(f'删除项目目录时出错: {str(e)}', 'danger')
    except Exception as e:
        flash(f'删除项目时出错: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/project//config', methods=['GET', 'POST'])
@login_required
def project_empty_config():
    """专门处理双斜杠URL的路由，重定向到仪表盘"""
    flash('项目ID不能为空', 'danger')
    return redirect(url_for('dashboard'))

# 访问日志中间件
@app.before_request
def log_request_info():
    """记录请求开始时间，用于计算响应时间"""
    request.start_time = time.time()

@app.after_request
def log_request(response):
    """记录请求访问日志，只记录与配置相关的API访问"""
    try:
        # 判断是否是配置相关API
        is_config_api = False
        project_id = None
        
        # 检查是否是配置相关API路径
        if ('/api/projects/' in request.path and '/config' in request.path) or \
           ('/project/' in request.path and '/config' in request.path):
            is_config_api = True
            
            # 从URL中提取项目ID
            if hasattr(request, 'view_args') and request.view_args and 'project_id' in request.view_args:
                project_id = request.view_args.get('project_id')
                # 确保project_id不为空字符串
                if project_id == '':
                    project_id = None
            elif request.method == 'POST' and 'project_id' in request.form:
                project_id = request.form.get('project_id')
                # 确保project_id不为空字符串
                if project_id == '':
                    project_id = None
            
            # 如果是API请求，可能在URL中
            if '/api/projects/' in request.path:
                parts = request.path.split('/')
                try:
                    idx = parts.index('projects')
                    if idx + 1 < len(parts) and parts[idx + 1]:  # 确保项目ID不为空
                        project_id = parts[idx + 1]
                except ValueError:
                    pass
        
        # 只记录配置相关的API访问且项目ID不为空
        if is_config_api and project_id:
            # 计算响应时间
            response_time = time.time() - getattr(request, 'start_time', time.time())
            
            # 记录访问日志
            access_log.log_access(
                project_id=project_id,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string if hasattr(request, 'user_agent') else None,
                request_method=request.method,
                endpoint=request.path,
                params=request.args.to_dict() if request.method == 'GET' else None,
                status_code=response.status_code,
                response_time=response_time,
                user_id=session.get('username') if 'logged_in' in session else None
            )
    except Exception as e:
        # 确保日志记录错误不会影响响应返回
        print(f"访问日志记录错误: {str(e)}")
    
    return response

# 新增API接口：获取所有项目列表
@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    # 检查API认证
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != APP_CONFIG.get('API_KEY', 'your-api-key-here'):
        return jsonify({'success': False, 'message': '无效的API密钥'}), 401
    
    try:
        projects = []
        # 遍历项目目录
        for project_id in os.listdir(APP_CONFIG['PROJECTS_DIR']):
            project_dir = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_id)
            project_config_path = os.path.join(project_dir, 'project.json')
            
            # 检查是否为目录且包含project.json文件
            if os.path.isdir(project_dir) and os.path.exists(project_config_path):
                try:
                    with open(project_config_path, 'r', encoding='utf-8') as f:
                        project_config = json.load(f)
                        projects.append({
                            'id': project_id,
                            'name': project_config.get('name', project_id),
                            'description': project_config.get('description', ''),
                            'created_at': project_config.get('created_at', ''),
                            'updated_at': project_config.get('updated_at', '')
                        })
                except:
                    # 跳过无法读取的项目
                    continue
        
        return jsonify({
            'success': True, 
            'projects': projects
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取项目列表失败: {str(e)}'}), 500

# 新增API接口：获取项目访问日志
@app.route('/api/projects/<project_id>/logs', methods=['GET'])
def api_get_project_logs(project_id):
    # 检查API认证
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != APP_CONFIG.get('API_KEY', 'your-api-key-here'):
        return jsonify({'success': False, 'message': '无效的API密钥'}), 401
    
    # 验证项目ID
    if not project_id:
        return jsonify({'success': False, 'message': '项目ID不能为空'}), 400
    
    project_dir = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_id)
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        return jsonify({'success': False, 'message': f'找不到项目: {project_id}'}), 404
    
    # 获取查询参数
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # 获取访问日志
    logs = access_log.get_project_access_logs(project_id, limit, offset)
    
    return jsonify({
        'success': True,
        'logs': logs
    })

# 新增API接口：获取项目访问统计
@app.route('/api/projects/<project_id>/stats', methods=['GET'])
def api_get_project_stats(project_id):
    # 检查API认证
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != APP_CONFIG.get('API_KEY', 'your-api-key-here'):
        return jsonify({'success': False, 'message': '无效的API密钥'}), 401
    
    # 验证项目ID
    if not project_id:
        return jsonify({'success': False, 'message': '项目ID不能为空'}), 400
    
    project_dir = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_id)
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        return jsonify({'success': False, 'message': f'找不到项目: {project_id}'}), 404
    
    # 获取项目统计
    stats = access_log.get_project_stats(project_id)
    
    # 获取IP统计
    ip_stats = access_log.get_project_ip_stats(project_id)
    
    if stats:
        return jsonify({
            'success': True,
            'stats': stats,
            'ip_stats': ip_stats
        })
    else:
        return jsonify({
            'success': False,
            'message': '没有找到项目统计数据'
        }), 404

# 新增API接口：获取项目配置详情
@app.route('/api/projects/<project_id>/config', methods=['GET'])
def api_get_project_config(project_id):
    # 检查API认证
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != APP_CONFIG.get('API_KEY', 'your-api-key-here'):
        return jsonify({'success': False, 'message': '无效的API密钥'}), 401
    
    # 验证项目ID
    if not project_id:
        return jsonify({'success': False, 'message': '项目ID不能为空'}), 400
    
    project_dir = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_id)
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        return jsonify({'success': False, 'message': f'找不到项目: {project_id}'}), 404
    
    project_config_path = os.path.join(project_dir, 'project.json')
    
    # 检查project.json文件是否存在
    if not os.path.exists(project_config_path):
        return jsonify({'success': False, 'message': f'找不到项目配置文件'}), 404
    
    try:
        # 加载项目元数据
        with open(project_config_path, 'r', encoding='utf-8') as f:
            project_config = json.load(f)
        
        # 确保使用项目特定的配置目录
        project_specific_dir = os.path.join(project_dir, 'config')
        if not os.path.exists(project_specific_dir):
            os.makedirs(project_specific_dir, exist_ok=True)
        
        # 如果project_config['path']不是项目特定目录，则更新
        if project_config['path'] != project_specific_dir:
            # 如果项目特定目录中没有配置文件，但原路径中有，则复制一份
            system_conf_path = os.path.join(project_specific_dir, 'system.conf')
            config_json_path = os.path.join(project_specific_dir, 'config.json')
            
            if not os.path.exists(system_conf_path) and os.path.exists(os.path.join(project_config['path'], 'system.conf')):
                shutil.copy2(os.path.join(project_config['path'], 'system.conf'), system_conf_path)
            
            if not os.path.exists(config_json_path) and os.path.exists(os.path.join(project_config['path'], 'config.json')):
                shutil.copy2(os.path.join(project_config['path'], 'config.json'), config_json_path)
            
            # 更新项目配置中的路径
            project_config['path'] = project_specific_dir
            # 保存更新后的项目配置
            with open(project_config_path, 'w', encoding='utf-8') as f:
                json.dump(project_config, f, indent=4)
        
        # 加载系统配置和用户配置
        system_conf_path = os.path.join(project_config['path'], 'system.conf')
        config_json_path = os.path.join(project_config['path'], 'config.json')
        
        # 处理系统配置
        system_config = {}
        if os.path.exists(system_conf_path):
            config_parser = ConfigParser()
            config_parser.read(system_conf_path, encoding='UTF-8')
            
            # 将ConfigParser对象转换为字典
            for section in config_parser.sections():
                system_config[section] = {}
                for key, value in config_parser[section].items():
                    # 处理加密的配置项
                    form_key = f"{section}_{key}"
                    if form_key in project_config.get('encrypted_keys', []):
                        try:
                            value = decrypt_data(value)
                        except:
                            # 如果解密失败，使用加密的值
                            pass
                    system_config[section][key] = value
        
        # 处理用户配置
        config_json = {}
        if os.path.exists(config_json_path):
            try:
                with open(config_json_path, 'r', encoding='utf-8') as f:
                    config_json = json.load(f)
            except:
                pass
        
        return jsonify({
            'success': True, 
            'project': {
                'id': project_id,
                'name': project_config.get('name', project_id),
                'description': project_config.get('description', ''),
                'system_config': system_config,
                'config_json': config_json
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取项目配置失败: {str(e)}'}), 500

# 新增API接口：获取特定配置项
@app.route('/api/projects/<project_id>/config/<path:config_path>', methods=['GET'])
def api_get_config_value(project_id, config_path):
    # 检查API认证
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != APP_CONFIG.get('API_KEY', 'your-api-key-here'):
        return jsonify({'success': False, 'message': '无效的API密钥'}), 401
    
    # 验证项目ID和配置路径
    if not project_id:
        return jsonify({'success': False, 'message': '项目ID不能为空'}), 400
    if not config_path:
        return jsonify({'success': False, 'message': '配置路径不能为空'}), 400
    
    project_dir = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_id)
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        return jsonify({'success': False, 'message': f'找不到项目: {project_id}'}), 404
    
    project_config_path = os.path.join(project_dir, 'project.json')
    
    # 检查project.json文件是否存在
    if not os.path.exists(project_config_path):
        return jsonify({'success': False, 'message': f'找不到项目配置文件'}), 404
    
    try:
        # 加载项目元数据
        with open(project_config_path, 'r', encoding='utf-8') as f:
            project_config = json.load(f)
        
        # 调用配置工具获取配置值
        config_value = config_util.get_config_value(config_path, project_path=project_config['path'])
        
        # 如果配置值为None，可能是路径不存在
        if config_value is None:
            return jsonify({'success': False, 'message': f'找不到配置项: {config_path}'}), 404
        
        return jsonify({
            'success': True, 
            'config_path': config_path,
            'config_value': config_value
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取配置项失败: {str(e)}'}), 500

# 新增API接口：更新特定配置项
@app.route('/api/projects/<project_id>/config/<path:config_path>', methods=['PUT'])
def api_update_config_value(project_id, config_path):
    # 检查API认证
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != APP_CONFIG.get('API_KEY', 'your-api-key-here'):
        return jsonify({'success': False, 'message': '无效的API密钥'}), 401
    
    # 验证项目ID和配置路径
    if not project_id:
        return jsonify({'success': False, 'message': '项目ID不能为空'}), 400
    if not config_path:
        return jsonify({'success': False, 'message': '配置路径不能为空'}), 400
    
    # 获取请求数据
    data = request.get_json()
    if not data or 'value' not in data:
        return jsonify({'success': False, 'message': '请求数据无效，需要包含value字段'}), 400
    
    config_value = data['value']
    
    project_dir = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_id)
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        return jsonify({'success': False, 'message': f'找不到项目: {project_id}'}), 404
    
    project_config_path = os.path.join(project_dir, 'project.json')
    
    # 检查project.json文件是否存在
    if not os.path.exists(project_config_path):
        return jsonify({'success': False, 'message': f'找不到项目配置文件'}), 404
    
    try:
        # 加载项目元数据
        with open(project_config_path, 'r', encoding='utf-8') as f:
            project_config = json.load(f)
        
        # 确保使用项目特定的配置目录
        project_specific_dir = os.path.join(project_dir, 'config')
        if not os.path.exists(project_specific_dir):
            os.makedirs(project_specific_dir, exist_ok=True)
        
        # 如果project_config['path']不是项目特定目录，则更新
        if project_config['path'] != project_specific_dir:
            # 如果项目特定目录中没有配置文件，但原路径中有，则复制一份
            system_conf_path = os.path.join(project_specific_dir, 'system.conf')
            config_json_path = os.path.join(project_specific_dir, 'config.json')
            
            if not os.path.exists(system_conf_path) and os.path.exists(os.path.join(project_config['path'], 'system.conf')):
                shutil.copy2(os.path.join(project_config['path'], 'system.conf'), system_conf_path)
            
            if not os.path.exists(config_json_path) and os.path.exists(os.path.join(project_config['path'], 'config.json')):
                shutil.copy2(os.path.join(project_config['path'], 'config.json'), config_json_path)
            
            # 更新项目配置中的路径
            project_config['path'] = project_specific_dir
            # 保存更新后的项目配置
            with open(project_config_path, 'w', encoding='utf-8') as f:
                json.dump(project_config, f, indent=4)
        
        # 加载系统配置和用户配置
        system_conf_path = os.path.join(project_config['path'], 'system.conf')
        config_json_path = os.path.join(project_config['path'], 'config.json')
        
        # 解析配置路径
        parts = config_path.split('.')
        
        # 支持system.section.key格式更新system.conf
        if parts[0] == 'system' and len(parts) == 3:
            section, key = parts[1:]
            system_conf_path = os.path.join(project_config['path'], 'system.conf')
            
            # 检查system.conf文件是否存在
            if not os.path.exists(system_conf_path):
                return jsonify({'success': False, 'message': f'找不到系统配置文件'}), 404
            
            # 加载系统配置
            system_config = ConfigParser()
            system_config.read(system_conf_path, encoding='UTF-8')
            
            # 检查区段和键是否存在
            if section not in system_config.sections():
                return jsonify({'success': False, 'message': f'找不到配置区段: {section}'}), 404
            if key not in system_config[section]:
                return jsonify({'success': False, 'message': f'找不到配置键: {key}'}), 404
            
            # 创建备份
            backup_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            shutil.copy2(system_conf_path, f"{system_conf_path}.{backup_time}.bak")
            
            # 更新配置值
            system_config[section][key] = str(config_value)
            
            # 保存系统配置
            with open(system_conf_path, 'w', encoding='UTF-8') as f:
                system_config.write(f)
                
        # 支持config.path.to.key格式更新config.json
        elif parts[0] == 'config' and len(parts) > 1:
            config_json_path = os.path.join(project_config['path'], 'config.json')
            
            # 检查config.json文件是否存在
            if not os.path.exists(config_json_path):
                return jsonify({'success': False, 'message': f'找不到用户配置文件'}), 404
            
            # 加载用户配置
            with open(config_json_path, 'r', encoding='utf-8') as f:
                config_json = json.load(f)
            
            # 创建备份
            backup_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            shutil.copy2(config_json_path, f"{config_json_path}.{backup_time}.bak")
            
            # 递归更新嵌套配置
            current = config_json
            for i, part in enumerate(parts[1:]):
                if i == len(parts) - 2:  # 最后一个键
                    current[part] = config_value
                    break
                elif part not in current:
                    current[part] = {}
                current = current[part]
            
            # 保存用户配置
            with open(config_json_path, 'w', encoding='utf-8') as f:
                json.dump(config_json, f, indent=4, ensure_ascii=False)
        else:
            return jsonify({'success': False, 'message': f'不支持的配置路径格式: {config_path}'}), 400
        
        return jsonify({
            'success': True, 
            'message': '配置更新成功',
            'config_path': config_path,
            'config_value': config_value
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新配置项失败: {str(e)}'}), 500

# 项目访问日志页面
@app.route('/project/<project_id>/logs', methods=['GET'])
@login_required
def project_logs(project_id):
    # 检查project_id是否为空
    if not project_id:
        flash('项目ID不能为空', 'danger')
        return redirect(url_for('dashboard'))
        
    project_dir = os.path.join(APP_CONFIG['PROJECTS_DIR'], project_id)
    
    # 检查项目目录是否存在
    if not os.path.exists(project_dir):
        flash(f'找不到项目目录: {project_dir}', 'danger')
        return redirect(url_for('dashboard'))
    
    project_config_path = os.path.join(project_dir, 'project.json')
    
    # 检查project.json文件是否存在
    if not os.path.exists(project_config_path):
        flash(f'找不到项目配置文件: {project_config_path}', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # 加载项目配置
        with open(project_config_path, 'r', encoding='utf-8') as f:
            project_config = json.load(f)
            
        # 确保project_config包含id字段，用于生成正确的链接
        if 'id' not in project_config:
            project_config['id'] = project_id
            
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 获取项目访问日志
        logs = access_log.get_project_access_logs(
            project_id, 
            limit=per_page, 
            offset=(page-1)*per_page
        )
        
        # 获取项目统计
        stats = access_log.get_project_stats(project_id)
        
        # 获取IP统计
        ip_stats = access_log.get_project_ip_stats(project_id)
        
        # 计算总页数
        total_pages = (logs['total'] + per_page - 1) // per_page
        
        return render_template(
            'project_logs.html',
            project=project_config,
            logs=logs['logs'],
            stats=stats,
            ip_stats=ip_stats,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total_records=logs['total']
        )
    except Exception as e:
        flash(f'读取项目访问日志时出错: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5500) 