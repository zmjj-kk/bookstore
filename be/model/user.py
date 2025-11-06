import jwt
import time
import logging
import secrets
from be.model import error
from be.model import db_conn
from pymongo.errors import PyMongoError
from datetime import datetime, timedelta


class User(db_conn.DBConn):
    # 配置项：可根据需求调整
    TOKEN_LIFETIME = 3600  # token有效期（秒）
    JWT_ALGORITHM = "HS256"  # 加密算法
    SECRET_KEY_LENGTH = 32  # 密钥长度

    def __init__(self):
        super().__init__()
        # 初始化时确保密钥集合存在（用于存储用户JWT密钥）
        self._init_secret_collection()

    def _init_secret_collection(self):
        """初始化用户密钥集合，用于JWT签名"""
        try:
            # 创建唯一索引
            self.db.user_secret.create_index("user_id", unique=True)
        except PyMongoError as e:
            logging.warning(f"初始化密钥集合失败: {e}")

    def _get_user_secret(self, user_id: str) -> str:
        """获取用户的JWT签名密钥，不存在则自动生成"""
        secret_doc = self.db.user_secret.find_one({"user_id": user_id})
        if secret_doc:
            return secret_doc["secret"]
        
        # 生成新的随机密钥
        secret = secrets.token_hex(self.SECRET_KEY_LENGTH)
        self.db.user_secret.insert_one({
            "user_id": user_id,
            "secret": secret,
            "create_time": datetime.now()
        })
        return secret

    def jwt_encode(self, user_id: str, terminal: str) -> str:
        """生成JWT令牌（使用用户专属密钥）"""
        secret = self._get_user_secret(user_id)
        payload = {
            "user_id": user_id,
            "terminal": terminal,
            "exp": datetime.utcnow() + timedelta(seconds=self.TOKEN_LIFETIME)
        }
        return jwt.encode(payload, secret, algorithm=self.JWT_ALGORITHM)

    def jwt_decode(self, encoded_token: str, user_id: str) -> dict:
        """验证并解析JWT令牌"""
        secret = self._get_user_secret(user_id)
        try:
            return jwt.decode(
                encoded_token,
                secret,
                algorithms=[self.JWT_ALGORITHM],
                options={"verify_exp": True}  # 验证过期时间
            )
        except jwt.ExpiredSignatureError:
            raise error.error_token_expired()
        except jwt.InvalidTokenError as e:
            logging.error(f"无效的token: {e}")
            raise error.error_invalid_token()

    def __check_token(self, user_id: str, db_token: str, token: str) -> bool:
        """验证token有效性"""
        if not db_token or db_token != token:
            return False
        
        try:
            # 解码时会自动验证过期时间
            self.jwt_decode(token, user_id)
            return True
        except Exception:
            return False

    def register(self, user_id: str, password: str) -> (int, str):
        """用户注册"""
        try:
            if self.db.user.find_one({"user_id": user_id}):
                return error.error_exist_user_id(user_id)
            
            # 生成初始终端标识和token
            terminal = f"terminal_{time.time()}"
            token = self.jwt_encode(user_id, terminal)
            
            # 插入用户记录
            self.db.user.insert_one({
                "user_id": user_id,
                "password": password,  # 注意：实际生产环境需加密存储密码
                "balance": 0,
                "token": token,
                "terminal": terminal,
                "register_time": datetime.now()
            })
            return 200, "ok"
            
        except PyMongoError as e:
            logging.error(f"MongoDB错误: {str(e)}")
            return error.error_database_error(str(e))
        except Exception as e:
            logging.error(f"注册异常: {str(e)}")
            return 530, str(e)

    def check_token(self, user_id: str, token: str) -> (int, str):
        """验证token"""
        try:
            user_doc = self.db.user.find_one({"user_id": user_id})
            if not user_doc:
                return error.error_non_exist_user_id(user_id)
            
            if not self.__check_token(user_id, user_doc.get("token"), token):
                return error.error_authorization_fail()
            
            return 200, "ok"
        except Exception as e:
            logging.error(f"token验证异常: {str(e)}")
            return 530, str(e)

    def check_password(self, user_id: str, password: str) -> (int, str):
        """验证密码"""
        user_doc = self.db.user.find_one({"user_id": user_id})
        if not user_doc:
            return error.error_non_exist_user_id(user_id)
        
        if password != user_doc.get("password"):  # 注意：实际需解密验证
            return error.error_authorization_fail()
        
        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        """用户登录"""
        try:
            code, msg = self.check_password(user_id, password)
            if code != 200:
                return code, msg, ""
            
            # 生成新token
            token = self.jwt_encode(user_id, terminal)
            result = self.db.user.update_one(
                {"user_id": user_id},
                {"$set": {
                    "token": token,
                    "terminal": terminal,
                    "last_login_time": datetime.now()
                }}
            )
            
            if result.modified_count == 0:
                return error.error_authorization_fail() + ("",)
            
            return 200, "ok", token
        except PyMongoError as e:
            return error.error_database_error(str(e)) + ("",)
        except Exception as e:
            return 530, str(e), ""

    def logout(self, user_id: str, token: str) -> (int, str):
        """用户登出"""
        try:
            code, msg = self.check_token(user_id, token)
            if code != 200:
                return code, msg
            
            # 生成无效token
            terminal = f"terminal_logout_{time.time()}"
            dummy_token = self.jwt_encode(user_id, terminal)
            
            result = self.db.user.update_one(
                {"user_id": user_id},
                {"$set": {
                    "token": dummy_token,
                    "terminal": terminal,
                    "last_logout_time": datetime.now()
                }}
            )
            
            if result.modified_count == 0:
                return error.error_authorization_fail()
            
            return 200, "ok"
        except PyMongoError as e:
            return error.error_database_error(str(e))
        except Exception as e:
            return 530, str(e)

    def unregister(self, user_id: str, password: str) -> (int, str):
        """用户注销"""
        try:
            code, msg = self.check_password(user_id, password)
            if code != 200:
                return code, msg
            
            # 事务：删除用户记录和密钥
            with self.db.client.start_session() as session:
                with session.start_transaction():
                    # 删除用户信息
                    user_result = self.db.user.delete_one(
                        {"user_id": user_id},
                        session=session
                    )
                    # 删除用户密钥
                    secret_result = self.db.user_secret.delete_one(
                        {"user_id": user_id},
                        session=session
                    )
                    
                    if user_result.deleted_count == 1:
                        return 200, "ok"
                    return error.error_authorization_fail()
                    
        except PyMongoError as e:
            return error.error_database_error(str(e))
        except Exception as e:
            return 530, str(e)

    def change_password(self, user_id: str, old_password: str, new_password: str) -> (int, str):
        """修改密码"""
        try:
            code, msg = self.check_password(user_id, old_password)
            if code != 200:
                return code, msg
            
            # 生成新token（密码变更后旧token失效）
            terminal = f"terminal_pwdchange_{time.time()}"
            token = self.jwt_encode(user_id, terminal)
            
            result = self.db.user.update_one(
                {"user_id": user_id},
                {"$set": {
                    "password": new_password,  # 注意：实际需加密存储
                    "token": token,
                    "terminal": terminal,
                    "last_pwd_change_time": datetime.now()
                }}
            )
            
            if result.modified_count == 0:
                return error.error_authorization_fail()
            
            return 200, "ok"
        except PyMongoError as e:
            return error.error_database_error(str(e))
        except Exception as e:
            return 530, str(e)