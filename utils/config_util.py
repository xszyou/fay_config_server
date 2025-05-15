import os
import json
import codecs
import requests
from configparser import ConfigParser
import functools
from threading import Lock
import threading

# 线程本地存储，用于支持多个项目配置
_thread_local = threading.local()

# 全局锁，确保线程安全
lock = Lock()
def synchronized(func):
  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    with lock:
      return func(*args, **kwargs)
    return wrapper

# 默认配置，用于全局访问
config: json = None
system_config: ConfigParser = None
system_chrome_driver = None
key_ali_nls_key_id = None
key_ali_nls_key_secret = None
key_ali_nls_app_key = None
key_ms_tts_key = None
Key_ms_tts_region = None
baidu_emotion_app_id = None
baidu_emotion_api_key = None
baidu_emotion_secret_key = None
key_gpt_api_key = None
key_lingju_api_key = None
gpt_model_engine = None
proxy_config = None
ASR_mode = None
local_asr_ip = None 
local_asr_port = None 
ltp_mode = None
gpt_base_url = None
tts_module = None
key_ali_tss_key_id = None
key_ali_tss_key_secret = None
key_ali_tss_app_key = None
volcano_tts_appid = None
volcano_tts_access_token = None
volcano_tts_cluster = None
volcano_tts_voice_type = None
start_mode = None
fay_url = None

# API配置
API_CONFIG = {
    'BASE_URL': 'http://localhost:5500',  # 默认API服务器地址
    'API_KEY': 'your-api-key-here',       # 默认API密钥
    'PROJECT_ID': None                     # 项目ID，需要在使用前设置
}

# 项目配置缓存
_project_configs = {}

def set_api_config(base_url=None, api_key=None, project_id=None):
    """
    设置API配置信息
    
    Args:
        base_url: API服务器基础URL
        api_key: API密钥
        project_id: 项目ID
    """
    if base_url:
        API_CONFIG['BASE_URL'] = base_url
    if api_key:
        API_CONFIG['API_KEY'] = api_key
    if project_id:
        API_CONFIG['PROJECT_ID'] = project_id

def load_config_from_api(project_id=None):
    """
    从API加载配置
    
    Args:
        project_id: 项目ID，如果为None则使用全局设置的项目ID
    
    Returns:
        包含配置信息的字典，加载失败则返回None
    """
    # 使用参数提供的项目ID或全局设置的项目ID
    pid = project_id or API_CONFIG['PROJECT_ID']
    if not pid:
        print("错误: 未指定项目ID，无法从API加载配置")
        return None
    
    # 构建API请求URL
    url = f"{API_CONFIG['BASE_URL']}/api/projects/{pid}/config"
    
    # 设置请求头
    headers = {
        'X-API-Key': API_CONFIG['API_KEY'],
        'Content-Type': 'application/json'
    }
    
    try:
        # 发送API请求
        response = requests.get(url, headers=headers)
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                # 提取配置数据
                project_data = result.get('project', {})
                
                # 创建并填充ConfigParser对象
                sys_config = ConfigParser()
                sys_config.add_section('key')
                
                # 获取系统配置字典
                system_dict = project_data.get('system_config', {})
                for section, items in system_dict.items():
                    if not sys_config.has_section(section):
                        sys_config.add_section(section)
                    for key, value in items.items():
                        sys_config.set(section, key, str(value))
                
                # 获取用户配置
                user_config = project_data.get('config_json', {})
                
                # 创建配置字典
                config_dict = {
                    'system_config': sys_config,
                    'config': user_config,
                    'project_id': pid,
                    'name': project_data.get('name', ''),
                    'description': project_data.get('description', ''),
                    'source': 'api'  # 标记配置来源
                }
                
                # 提取所有配置项到配置字典
                for section in sys_config.sections():
                    for key, value in sys_config.items(section):
                        config_dict[f'{section}_{key}'] = value
                
                return config_dict
            else:
                print(f"API错误: {result.get('message', '未知错误')}")
        else:
            print(f"API请求失败: HTTP状态码 {response.status_code}")
    except Exception as e:
        print(f"从API加载配置时出错: {str(e)}")
    
    return None

@synchronized
def load_config(config_dir=None):
    """
    加载配置文件，如果本地文件不存在则直接使用API加载
    
    Args:
        config_dir: 配置文件所在目录路径，如果为None则使用当前目录
    
    Returns:
        包含配置信息的字典
    """
    global config
    global system_config
    global key_ali_nls_key_id
    global key_ali_nls_key_secret
    global key_ali_nls_app_key
    global key_ms_tts_key
    global key_ms_tts_region
    global baidu_emotion_app_id
    global baidu_emotion_secret_key
    global baidu_emotion_api_key
    global key_gpt_api_key
    global gpt_model_engine
    global proxy_config
    global ASR_mode
    global local_asr_ip 
    global local_asr_port
    global ltp_mode 
    global gpt_base_url
    global tts_module
    global key_ali_tss_key_id
    global key_ali_tss_key_secret
    global key_ali_tss_app_key
    global volcano_tts_appid
    global volcano_tts_access_token
    global volcano_tts_cluster
    global volcano_tts_voice_type
    global start_mode
    global fay_url
    
    # 如果指定了配置目录，使用指定的路径；否则使用当前目录
    base_dir = config_dir if config_dir else ""
    
    # 构建system.conf和config.json的完整路径
    system_conf_path = os.path.join(base_dir, 'system.conf')
    config_json_path = os.path.join(base_dir, 'config.json')
    
    # 检查本地文件是否存在
    sys_conf_exists = os.path.exists(system_conf_path)
    config_json_exists = os.path.exists(config_json_path)
    
    # 如果任一本地文件不存在，直接尝试从API加载
    if not sys_conf_exists or not config_json_exists:
        # 尝试从项目路径中提取项目ID（如果可能）
        project_id = None
        if config_dir:
            project_id = os.path.basename(config_dir)
        
        # 使用提取的项目ID或全局项目ID
        print(f"本地配置文件不完整（{'system.conf' if not sys_conf_exists else ''}{'和' if not sys_conf_exists and not config_json_exists else ''}{'config.json' if not config_json_exists else ''}不存在），尝试从API加载配置...")
        set_api_config(
            base_url=API_CONFIG['BASE_URL'],
            api_key=API_CONFIG['API_KEY'],
            project_id=API_CONFIG['PROJECT_ID']
        )
        api_config = load_config_from_api(project_id)
        
        if api_config:
            print("成功从API加载配置")
            system_config = api_config['system_config']
            config = api_config['config']
            
            # 设置所有配置项
            for section in system_config.sections():
                for key, value in system_config.items(section):
                    var_name = f"{section}_{key}"
                    if var_name in globals():
                        globals()[var_name] = value
            
            # 缓存API加载的配置
            if config_dir:
                _project_configs[config_dir] = api_config
            
            # 如果需要，保存API配置到本地文件
            # 这里可以选择是否将API加载的配置保存到本地
            # save_api_config_to_local(api_config, system_conf_path, config_json_path)
            
            return api_config
    
    # 如果本地文件存在，从本地文件加载
    try:
        # 加载system.conf
        system_config = ConfigParser()
        system_config.read(system_conf_path, encoding='UTF-8')
        
        # 从system.conf中读取所有配置项
        key_ali_nls_key_id = system_config.get('key', 'ali_nls_key_id')
        key_ali_nls_key_secret = system_config.get('key', 'ali_nls_key_secret')
        key_ali_nls_app_key = system_config.get('key', 'ali_nls_app_key')
        key_ali_tss_key_id = system_config.get('key', 'ali_tss_key_id')
        key_ali_tss_key_secret = system_config.get('key', 'ali_tss_key_secret')
        key_ali_tss_app_key = system_config.get('key', 'ali_tss_app_key')
        key_ms_tts_key = system_config.get('key', 'ms_tts_key')
        key_ms_tts_region  = system_config.get('key', 'ms_tts_region')
        baidu_emotion_app_id = system_config.get('key', 'baidu_emotion_app_id')
        baidu_emotion_api_key = system_config.get('key', 'baidu_emotion_api_key')
        baidu_emotion_secret_key = system_config.get('key', 'baidu_emotion_secret_key')
        key_gpt_api_key = system_config.get('key', 'gpt_api_key')
        gpt_model_engine = system_config.get('key', 'gpt_model_engine')
        ASR_mode = system_config.get('key', 'ASR_mode')
        local_asr_ip = system_config.get('key', 'local_asr_ip')
        local_asr_port = system_config.get('key', 'local_asr_port')
        proxy_config = system_config.get('key', 'proxy_config')
        ltp_mode = system_config.get('key', 'ltp_mode')
        gpt_base_url = system_config.get('key', 'gpt_base_url')
        tts_module = system_config.get('key', 'tts_module')
        volcano_tts_appid = system_config.get('key', 'volcano_tts_appid')
        volcano_tts_access_token = system_config.get('key', 'volcano_tts_access_token')
        volcano_tts_cluster = system_config.get('key', 'volcano_tts_cluster')
        volcano_tts_voice_type = system_config.get('key', 'volcano_tts_voice_type')
        start_mode = system_config.get('key', 'start_mode')
        fay_url = system_config.get('key', 'fay_url')
        
        # 读取用户配置
        with codecs.open(config_json_path, encoding='utf-8') as f:
            config = json.load(f)
        
        # 构建配置字典
        config_dict = {
            'system_config': system_config,
            'config': config,
            'ali_nls_key_id': key_ali_nls_key_id,
            'ali_nls_key_secret': key_ali_nls_key_secret,
            'ali_nls_app_key': key_ali_nls_app_key,
            'ms_tts_key': key_ms_tts_key,
            'ms_tts_region': key_ms_tts_region,
            'baidu_emotion_app_id': baidu_emotion_app_id,
            'baidu_emotion_api_key': baidu_emotion_api_key,
            'baidu_emotion_secret_key': baidu_emotion_secret_key,
            'gpt_api_key': key_gpt_api_key,
            'gpt_model_engine': gpt_model_engine,
            'ASR_mode': ASR_mode,
            'local_asr_ip': local_asr_ip,
            'local_asr_port': local_asr_port,
            'proxy_config': proxy_config,
            'ltp_mode': ltp_mode,
            'gpt_base_url': gpt_base_url,
            'tts_module': tts_module,
            'ali_tss_key_id': key_ali_tss_key_id,
            'ali_tss_key_secret': key_ali_tss_key_secret,
            'ali_tss_app_key': key_ali_tss_app_key,
            'volcano_tts_appid': volcano_tts_appid,
            'volcano_tts_access_token': volcano_tts_access_token,
            'volcano_tts_cluster': volcano_tts_cluster,
            'volcano_tts_voice_type': volcano_tts_voice_type,
            'start_mode': start_mode,
            'fay_url': fay_url,
            'source': 'local'  # 标记配置来源
        }
        
        # 如果指定了配置目录，则缓存配置
        if config_dir:
            _project_configs[config_dir] = config_dict
        
        return config_dict
        
    except Exception as e:
        # 如果本地文件加载失败，尝试从API加载
        print(f"加载本地配置文件失败: {str(e)}，尝试从API加载...")
        
        # 尝试从项目路径中提取项目ID（如果可能）
        project_id = None
        if config_dir:
            project_id = os.path.basename(config_dir)
        
        api_config = load_config_from_api(project_id)
        
        if api_config:
            print("成功从API加载配置")
            system_config = api_config['system_config']
            config = api_config['config']
            
            # 设置所有配置项
            for section in system_config.sections():
                for key, value in system_config.items(section):
                    var_name = f"{section}_{key}"
                    if var_name in globals():
                        globals()[var_name] = value
            
            # 缓存API加载的配置
            if config_dir:
                _project_configs[config_dir] = api_config
            
            return api_config
        
        # 如果API加载也失败，则重新抛出原始异常
        raise

def save_api_config_to_local(api_config, system_conf_path, config_json_path):
    """
    将从API加载的配置保存到本地文件
    
    Args:
        api_config: API加载的配置字典
        system_conf_path: system.conf文件路径
        config_json_path: config.json文件路径
    """
    try:
        # 保存system.conf
        with open(system_conf_path, 'w', encoding='UTF-8') as f:
            api_config['system_config'].write(f)
        
        # 保存config.json
        with codecs.open(config_json_path, mode='w', encoding='utf-8') as file:
            file.write(json.dumps(api_config['config'], sort_keys=True, indent=4, separators=(',', ': ')))
        
        print(f"已将API配置保存到本地文件")
    except Exception as e:
        print(f"保存API配置到本地文件时出错: {str(e)}")

def load_project_config(project_path):
    """
    加载特定项目的配置，优先尝试本地文件，如果不存在则直接使用API
    
    Args:
        project_path: 项目配置文件所在目录路径
    
    Returns:
        包含配置信息的字典
    """
    # 检查缓存中是否已有该项目的配置
    if project_path in _project_configs:
        return _project_configs[project_path]
    
    # 检查本地配置文件是否存在
    system_conf_path = os.path.join(project_path, 'system.conf')
    config_json_path = os.path.join(project_path, 'config.json')
    
    # 如果本地配置文件不完整，直接使用API加载
    if not os.path.exists(system_conf_path) or not os.path.exists(config_json_path):
        # 从项目路径中提取项目ID
        project_id = os.path.basename(project_path)
        if project_id:
            print(f"项目本地配置文件不完整，尝试使用API加载配置（项目ID: {project_id}）...")
            api_config = load_config_from_api(project_id)
            if api_config:
                print(f"成功从API加载项目配置（项目ID: {project_id}）")
                # 缓存API加载的配置
                _project_configs[project_path] = api_config
                
                # 可选：将API配置保存到本地文件
                # save_api_config_to_local(api_config, system_conf_path, config_json_path)
                
                return api_config
    
    # 如果本地配置文件存在或无法使用API加载，尝试正常加载
    try:
        return load_config(project_path)
    except Exception as e:
        print(f"加载项目配置时出错: {str(e)}")
        # 如果本地加载失败，尝试再次使用API加载（可能前面检查时文件存在但内容有问题）
        project_id = os.path.basename(project_path)
        if project_id:
            api_config = load_config_from_api(project_id)
            if api_config:
                # 缓存API加载的配置
                _project_configs[project_path] = api_config
                return api_config
        # 如果API加载也失败，则抛出原始异常
        raise

def get_current_project_config():
    """
    获取当前线程的项目配置
    
    Returns:
        当前线程的项目配置，如果未设置则返回None
    """
    return getattr(_thread_local, 'current_config', None)

def set_current_project(project_path):
    """
    设置当前线程使用的项目配置
    
    Args:
        project_path: 项目配置文件所在目录路径
    
    Returns:
        包含配置信息的字典
    """
    config_dict = load_project_config(project_path)
    _thread_local.current_config = config_dict
    return config_dict

@synchronized
def save_config(config_data, config_dir=None):
    """
    保存配置到config.json文件
    
    Args:
        config_data: 要保存的配置数据
        config_dir: 配置文件目录，如果为None则使用当前目录
    """
    global config
    
    # 如果指定了配置目录，使用指定的路径；否则使用当前目录
    if config_dir:
        config_json_path = os.path.join(config_dir, 'config.json')
    else:
        config_json_path = 'config.json'
    
    # 更新全局配置
    if config_dir is None:
        config = config_data
    elif config_dir in _project_configs:
        _project_configs[config_dir]['config'] = config_data
    
    # 保存到文件
    with codecs.open(config_json_path, mode='w', encoding='utf-8') as file:
        file.write(json.dumps(config_data, sort_keys=True, indent=4, separators=(',', ': ')))

def get_config_value(key, default=None, project_path=None, use_api=True):
    """
    获取配置值
    
    Args:
        key: 配置键，格式为'section.key'或'key'
        default: 默认值，如果配置项不存在则返回此值
        project_path: 项目路径，如果为None则使用当前线程的项目或全局配置
        use_api: 如果本地配置不存在或加载失败，是否尝试从API加载
    
    Returns:
        配置值
    """
    # 确定使用哪个配置
    config_dict = None
    
    if project_path:
        try:
            config_dict = load_project_config(project_path)
        except Exception as e:
            if use_api:
                # 尝试从API加载
                project_id = os.path.basename(project_path)
                if project_id:
                    api_config = load_config_from_api(project_id)
                    if api_config:
                        config_dict = api_config
    else:
        config_dict = get_current_project_config()
        if not config_dict:
            # 如果当前线程没有设置项目，使用全局配置
            if system_config is None:
                try:
                    load_config()
                except Exception as e:
                    if use_api and API_CONFIG['PROJECT_ID']:
                        # 尝试使用全局项目ID从API加载
                        api_config = load_config_from_api()
                        if api_config:
                            config_dict = api_config
                            return get_value_from_config(config_dict, key, default)
            
            if not config_dict:  # 如果API加载失败或不使用API
                # 构建全局配置字典
                config_dict = {
                    'system_config': system_config,
                    'config': config
                }
    
    return get_value_from_config(config_dict, key, default)

def get_value_from_config(config_dict, key, default=None):
    """
    从配置字典中获取值
    
    Args:
        config_dict: 配置字典
        key: 配置键，格式为'section.key'或'key'
        default: 默认值，如果配置项不存在则返回此值
    
    Returns:
        配置值
    """
    if not config_dict:
        return default
        
    # 解析键
    if '.' in key:
        section, key_name = key.split('.', 1)
        if section == 'config':
            # 从config.json获取配置
            try:
                current_level = config_dict['config']
                for part in key_name.split('.'):
                    current_level = current_level[part]
                return current_level
            except (KeyError, TypeError):
                return default
        elif section == 'system':
            # 从system.conf获取配置
            try:
                if key_name in config_dict:
                    return config_dict[key_name]
                else:
                    system_config = config_dict.get('system_config')
                    if system_config and system_config.has_option('key', key_name):
                        return system_config.get('key', key_name)
                    return default
            except KeyError:
                return default
    else:
        # 尝试直接从配置字典获取
        try:
            return config_dict[key]
        except KeyError:
            return default

