import os
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

# 获取日志记录器
logger = logging.getLogger(__name__)

class Config:
    # 飞书应用配置
    FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
    FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
    
    # 多维表格配置
    BASE_ID = os.getenv('BASE_ID')
    TABLE_ID = os.getenv('TABLE_ID')
    
    # Flask 配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # 缓存配置
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300  # 5分钟缓存

    @classmethod
    def validate_config(cls):
        """验证配置是否完整"""
        required_configs = {
            'FEISHU_APP_ID': cls.FEISHU_APP_ID,
            'FEISHU_APP_SECRET': cls.FEISHU_APP_SECRET,
            'BASE_ID': cls.BASE_ID,
            'TABLE_ID': cls.TABLE_ID
        }
        
        missing_configs = [key for key, value in required_configs.items() if not value]
        
        if missing_configs:
            logger.error(f"缺少必要的配置项: {', '.join(missing_configs)}")
            return False
            
        logger.info("配置验证通过")
        logger.info(f"当前配置: APP_ID={cls.FEISHU_APP_ID}, BASE_ID={cls.BASE_ID}, TABLE_ID={cls.TABLE_ID}")
        return True 