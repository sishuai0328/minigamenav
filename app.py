from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_caching import Cache
import requests
import logging
from config import Config
import time
import os
import io
from urllib.parse import urlparse, parse_qs
import hashlib

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建静态目录
os.makedirs('static/images/cache', exist_ok=True)

# 验证配置
if not Config.validate_config():
    logger.error("配置验证失败，请检查环境变量")
    exit(1)

app = Flask(__name__)
app.config.from_object(Config)
cache = Cache(app)

# 飞书 API 相关函数
def get_access_token():
    """获取飞书访问令牌"""
    try:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": app.config['FEISHU_APP_ID'],
            "app_secret": app.config['FEISHU_APP_SECRET']
        }
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        
        logger.info("正在获取访问令牌...")
        logger.info(f"App ID: {app.config['FEISHU_APP_ID']}")
        logger.info(f"App Secret 长度: {len(app.config['FEISHU_APP_SECRET'])}")
        logger.info(f"请求 URL: {url}")
        logger.info(f"请求头: {headers}")
        
        response = requests.post(url, json=payload, headers=headers)
        logger.info(f"响应状态码: {response.status_code}")
        logger.info(f"响应头: {response.headers}")
        logger.info(f"响应内容: {response.text}")
        
        response.raise_for_status()
        
        data = response.json()
        if data.get('code') != 0:
            logger.error(f"获取访问令牌失败: {data.get('msg')}")
            logger.error(f"错误详情: {data.get('error')}")
            return None
            
        token = data.get('tenant_access_token')
        if token:
            logger.info(f"成功获取访问令牌，长度: {len(token)}")
            return token
        else:
            logger.error("访问令牌为空")
            return None
    except Exception as e:
        logger.error(f"获取访问令牌出错: {str(e)}")
        return None

@cache.memoize(timeout=300)  # 5分钟缓存
def get_file_download_url(file_token):
    """获取文件的下载链接"""
    try:
        if not file_token:
            logger.warning("文件 token 为空")
            return None
            
        token = get_access_token()
        if not token:
            logger.error("获取访问令牌失败")
            return None

        # 直接返回可访问的 URL
        return f"https://open.feishu.cn/open-apis/drive/v1/medias/{file_token}/download?access_token={token}"
    except Exception as e:
        logger.error(f"获取文件下载链接出错: {str(e)}")
        return None

def validate_image_field(image_data):
    """验证图片字段格式"""
    try:
        if not isinstance(image_data, dict):
            logger.warning(f"图片数据不是字典类型: {image_data}")
            return False
            
        # 检查必需字段
        required_fields = ['file_token', 'name', 'type']
        for field in required_fields:
            if field not in image_data:
                logger.warning(f"图片数据缺少必需字段 {field}: {image_data}")
                return False
                
        # 验证 file_token 格式
        file_token = image_data.get('file_token')
        if not file_token:
            logger.warning("file_token 为空")
            return False
            
        if not isinstance(file_token, str):
            logger.warning(f"file_token 不是字符串类型: {type(file_token)}")
            return False
            
        if len(file_token) < 10:  # 飞书 file_token 通常较长
            logger.warning(f"file_token 长度异常: {len(file_token)}")
            return False
            
        logger.info(f"file_token 验证通过: {file_token[:10]}...")
            
        # 验证文件类型
        file_type = image_data.get('type')
        if not file_type:
            logger.warning("文件类型为空")
            return False
            
        if not file_type.startswith('image/'):
            logger.warning(f"无效的文件类型: {file_type}")
            return False
            
        logger.info(f"图片字段验证通过: {image_data}")
        return True
    except Exception as e:
        logger.error(f"验证图片字段时出错: {str(e)}")
        return False

def process_file_info(file_info):
    """处理文件信息，返回可访问的 URL"""
    try:
        logger.info(f"处理文件信息: {file_info}")
        
        if not isinstance(file_info, dict):
            logger.warning(f"文件信息格式错误: {file_info}")
            return None
            
        # 验证图片字段格式
        if not validate_image_field(file_info):
            logger.warning(f"图片字段格式验证失败: {file_info}")
            return None
            
        # 如果已经是 URL，直接返回
        if 'url' in file_info and file_info['url'].startswith('http'):
            logger.info(f"使用现有 URL: {file_info['url']}")
            return file_info['url']
            
        # 获取 file_token
        file_token = file_info.get('file_token')
        if not file_token:
            logger.warning(f"未找到 file_token: {file_info}")
            return None
            
        logger.info(f"使用 file_token 获取下载链接: {file_token}")
        # 获取下载链接
        download_url = get_file_download_url(file_token)
        if download_url:
            return download_url
        return None
    except Exception as e:
        logger.error(f"处理文件信息出错: {str(e)}")
        return None

@cache.memoize(timeout=3600)  # 1小时缓存
def get_temp_download_urls(file_tokens):
    """批量获取临时下载链接
    
    Args:
        file_tokens: 文件token列表
        
    Returns:
        dict: {file_token: download_url}
    """
    if not file_tokens:
        logger.warning("没有需要获取的文件token")
        return {}
        
    token = get_access_token()
    if not token:
        logger.error("获取访问令牌失败")
        return {}
        
    # 使用飞书批量获取临时下载链接API
    url = "https://open.feishu.cn/open-apis/drive/v1/medias/batch_get_tmp_download_url"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 分批处理，每次最多处理100个
    result = {}
    for i in range(0, len(file_tokens), 100):
        batch_tokens = file_tokens[i:i+100]
        
        payload = {
            "file_tokens": batch_tokens
        }
        
        logger.info(f"请求临时下载链接: {url} 文件数量: {len(batch_tokens)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            logger.info(f"临时下载链接响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    tmp_download_urls = data.get('data', {}).get('tmp_download_urls', [])
                    
                    # 将结果转换为字典 {file_token: download_url}
                    for item in tmp_download_urls:
                        token = item.get('file_token')
                        download_url = item.get('tmp_download_url')
                        if token and download_url:
                            result[token] = download_url
                            logger.info(f"获取到临时下载链接: {token[:10]}... -> {download_url[:60]}...")
                else:
                    logger.error(f"获取临时下载链接失败: {data.get('msg')}")
            else:
                logger.error(f"临时下载链接请求失败: {response.text}")
        except Exception as e:
            logger.error(f"请求临时下载链接出错: {str(e)}")
    
    logger.info(f"共获取到 {len(result)} 个临时下载链接")
    return result

@cache.memoize(timeout=14400)  # 4小时缓存
def get_image_download_url(file_token):
    """获取图片的临时访问链接
    
    根据file_token获取临时访问链接，临时链接有效期为4小时
    """
    if not file_token:
        logger.warning("文件 token 为空")
        return None
        
    token = get_access_token()
    if not token:
        logger.error("获取访问令牌失败")
        return None
    
    try:
        # 直接请求下载接口，获取重定向URL
        url = f"https://open.feishu.cn/open-apis/drive/v1/medias/{file_token}/download"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        logger.info(f"获取图片临时访问链接: {url}")
        # 设置allow_redirects=False以获取重定向URL
        response = requests.get(url, headers=headers, allow_redirects=False)
        
        logger.info(f"图片临时访问链接响应状态码: {response.status_code}")
        logger.info(f"图片临时访问链接响应头: {response.headers}")
        
        if response.status_code == 302 or response.status_code == 307:
            # 从重定向头中获取真实的临时访问URL
            redirect_url = response.headers.get('Location')
            if redirect_url:
                logger.info(f"获取到图片临时访问链接: {redirect_url[:100]}...")
                return redirect_url
            else:
                logger.error(f"重定向响应中未找到Location头: {response.headers}")
                return None
        else:
            logger.error(f"获取图片临时访问链接失败: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        logger.error(f"获取图片临时访问链接出错: {str(e)}")
        logger.exception("详细错误堆栈:")
        return None

# 添加图片代理路由
@app.route('/image_proxy/<path:file_token>')
def image_proxy(file_token):
    """代理获取飞书图片"""
    try:
        logger.info(f"开始处理图片代理请求: {file_token}")
        
        # 获取图片临时URL
        image_url = get_image_download_url(file_token)
        if not image_url:
            logger.error(f"无法获取图片URL: {file_token}")
            return send_file('static/images/default-cover.png', mimetype='image/png')
            
        # 请求图片数据
        logger.info(f"通过代理获取图片: {image_url[:100]}...")
        try:
            response = requests.get(image_url, stream=True, timeout=10)  # 添加超时设置
            
            logger.info(f"图片响应状态码: {response.status_code}")
            logger.info(f"图片响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                # 检查内容类型
                content_type = response.headers.get('Content-Type', '')
                logger.info(f"图片内容类型: {content_type}")
                
                if not content_type.startswith('image/'):
                    logger.warning(f"非图片内容类型: {content_type}, 使用默认图片")
                    return send_file('static/images/default-cover.png', mimetype='image/png')
                
                # 将响应内容保存到内存中
                image_io = io.BytesIO(response.content)
                image_size = len(response.content)
                logger.info(f"图片大小: {image_size} 字节")
                
                # 检查图片大小是否合理
                if image_size < 100:  # 如果图片太小，可能是无效的
                    logger.warning(f"图片太小 ({image_size} 字节)，可能无效，使用默认图片")
                    return send_file('static/images/default-cover.png', mimetype='image/png')
                
                # 返回图片数据
                return send_file(
                    image_io,
                    mimetype=content_type,
                    etag=True,
                    max_age=14400  # 4小时缓存
                )
            else:
                logger.error(f"获取图片失败: {response.status_code}, {response.text[:200]}")
                return send_file('static/images/default-cover.png', mimetype='image/png')
        except requests.RequestException as e:
            logger.error(f"请求图片时出错: {str(e)}")
            return send_file('static/images/default-cover.png', mimetype='image/png')
    except Exception as e:
        logger.error(f"代理图片出错: {str(e)}")
        logger.exception("详细错误堆栈:")
        return send_file('static/images/default-cover.png', mimetype='image/png')

def get_table_data():
    """获取多维表格数据"""
    try:
        token = get_access_token()
        if not token:
            logger.error("无法获取访问令牌")
            return []

        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app.config['BASE_ID']}/tables/{app.config['TABLE_ID']}/records"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        params = {
            "page_size": 100  # 每页获取的记录数
        }
        
        logger.info(f"正在获取表格数据，BASE_ID: {app.config['BASE_ID']}, TABLE_ID: {app.config['TABLE_ID']}")
        
        all_records = []
        
        while True:
            response = requests.get(url, headers=headers, params=params)
            logger.info(f"表格数据响应状态码: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"获取表格数据失败: {data.get('msg')}")
                return []
                
            items = data.get('data', {}).get('items', [])
            logger.info(f"获取到 {len(items)} 条记录")
            
            # 处理每个记录中的图片
            for item in items:
                record_id = item.get('record_id')
                fields = item.get('fields', {})
                
                # 处理游戏封面
                if 'gamecover' in fields:
                    logger.info(f"处理游戏封面字段: {fields['gamecover']}")
                    cover_url = None
                    
                    # 将字段值转换为字符串并处理
                    cover_value = str(fields['gamecover']).strip()
                    
                    # 检查是否为非空
                    if cover_value:
                        # 如果包含多行，取第一行作为封面
                        if '\n' in cover_value:
                            lines = cover_value.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line and (line.startswith('http://') or line.startswith('https://')):
                                    cover_url = line
                                    logger.info(f"从多行文本中提取封面URL: {cover_url}")
                                    break
                        # 单行文本直接使用
                        elif cover_value.startswith('http://') or cover_value.startswith('https://'):
                            cover_url = cover_value
                            logger.info(f"使用直接提供的封面URL: {cover_url}")
                    
                    if cover_url:
                        fields['gamecover'] = cover_url
                    else:
                        fields['gamecover'] = '/static/images/default-cover.png'
                        logger.warning(f"未找到有效的封面链接，使用默认图片")
                else:
                    fields['gamecover'] = '/static/images/default-cover.png'
                
                # 处理游戏截图
                if 'gamescreenshots' in fields:
                    logger.info(f"处理游戏截图字段: {fields['gamescreenshots']}")
                    screenshots = []
                    
                    # 将字段值转换为字符串并处理
                    screenshots_value = str(fields['gamescreenshots']).strip()
                    
                    # 检查是否为非空
                    if screenshots_value:
                        # 按换行符分割多个URL
                        if '\n' in screenshots_value:
                            lines = screenshots_value.split('\n')
                            logger.info(f"从多行文本中提取截图链接，共 {len(lines)} 行")
                            
                            for line in lines:
                                line = line.strip()
                                if line and (line.startswith('http://') or line.startswith('https://')):
                                    screenshots.append(line)
                                    logger.info(f"提取到截图URL: {line}")
                        # 单行文本直接使用
                        elif screenshots_value.startswith('http://') or screenshots_value.startswith('https://'):
                            screenshots.append(screenshots_value)
                            logger.info(f"使用单个截图URL: {screenshots_value}")
                    
                    if screenshots:
                        fields['gamescreenshots'] = screenshots
                    else:
                        fields['gamescreenshots'] = ['/static/images/default-screenshot.png']
                        logger.warning(f"未找到有效的截图链接，使用默认图片")
                else:
                    fields['gamescreenshots'] = ['/static/images/default-screenshot.png']
                
                # 处理游戏标签
                if 'tags' in fields:
                    logger.info(f"处理游戏标签字段: {fields['tags']}")
                    game_tags = []
                    
                    # 将字段值转换为字符串并处理
                    tags_value = str(fields['tags']).strip()
                    
                    # 如果是多行文本，按行分割
                    if tags_value:
                        if '\n' in tags_value:
                            lines = tags_value.split('\n')
                            for line in lines:
                                # 清理标签，去除符号，只保留字母、数字、空格和中文字符
                                tag = ''.join(c for c in line.strip() if c.isalnum() or c.isspace() or '\u4e00' <= c <= '\u9fff')
                                tag = tag.strip()
                                if tag:
                                    game_tags.append(tag)
                                    logger.info(f"提取到标签: {tag}")
                        else:
                            # 单行可能包含多个标签，按逗号分割
                            tags = tags_value.split(',')
                            for tag in tags:
                                # 清理标签，去除符号，只保留字母、数字、空格和中文字符
                                tag = ''.join(c for c in tag.strip() if c.isalnum() or c.isspace() or '\u4e00' <= c <= '\u9fff')
                                tag = tag.strip()
                                if tag:
                                    game_tags.append(tag)
                                    logger.info(f"提取到标签: {tag}")
                    
                    fields['tags'] = game_tags
                else:
                    fields['tags'] = []
            
            all_records.extend(items)
            
            # 检查是否还有更多数据
            has_more = data.get('data', {}).get('has_more', False)
            if not has_more:
                break
                
            # 更新分页标记
            params['page_token'] = data.get('data', {}).get('page_token')
        
        logger.info(f"成功获取到 {len(all_records)} 条游戏记录")
        return all_records
    except Exception as e:
        logger.error(f"获取表格数据出错: {str(e)}")
        return []

# 路由
@app.route('/')
def index():
    """首页"""
    try:
        game_type = request.args.get('type', '全部')
        games = get_table_data()
        
        # 根据类型筛选游戏
        if game_type != '全部':
            games = [game for game in games if game.get('fields', {}).get('type') == game_type]
        
        # 获取所有游戏类型
        all_types = list(set(
            game.get('fields', {}).get('type') 
            for game in games 
            if game.get('fields', {}).get('type')
        ))
        all_types.sort()  # 对类型进行排序
        all_types.insert(0, '全部')
        
        logger.info(f"当前类型: {game_type}, 显示游戏数量: {len(games)}, 所有类型: {all_types}")
        return render_template('index.html', games=games, types=all_types, current_type=game_type)
    except Exception as e:
        logger.error(f"首页渲染出错: {str(e)}")
        return "服务器错误", 500

@app.route('/game/<game_id>')
def game_detail(game_id):
    """游戏详情页"""
    try:
        games = get_table_data()
        game = next((game for game in games if game.get('record_id') == game_id), None)
        
        if not game:
            logger.warning(f"未找到游戏: {game_id}")
            return "游戏不存在", 404
        
        fields = game.get('fields', {})
        logger.info(f"显示游戏详情: {fields.get('title')}")
        
        # 处理游戏 URL
        game_url = fields.get('game_url', '')
        logger.info(f"原始游戏链接数据: {game_url}")
        
        # 如果 game_url 是字典，尝试获取其中的 URL
        if isinstance(game_url, dict):
            game_url = game_url.get('text', '')
        elif isinstance(game_url, list) and len(game_url) > 0:
            # 如果是列表，取第一个元素
            game_url = game_url[0].get('text', '') if isinstance(game_url[0], dict) else str(game_url[0])
        
        # 确保 game_url 是字符串
        game_url = str(game_url).strip()
        
        if game_url:
            # 确保 URL 是以 http 或 https 开头
            if not game_url.startswith(('http://', 'https://')):
                game_url = 'https://' + game_url
            fields['game_url'] = game_url
        else:
            logger.warning(f"游戏 {fields.get('title')} 未设置游戏链接")
            fields['game_url'] = ''
        
        logger.info(f"处理后的游戏链接: {fields.get('game_url')}")
        logger.info(f"游戏封面: {fields.get('gamecover')[:60]}...")
        logger.info(f"游戏截图数量: {len(fields.get('gamescreenshots', []))}")
        
        return render_template('detail.html', game=game)
    except Exception as e:
        logger.error(f"游戏详情页渲染出错: {str(e)}")
        return "服务器错误", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006, debug=app.config['DEBUG']) 