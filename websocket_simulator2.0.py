import asyncio
import json
import uuid
import random
import platform
import websockets
import sys
import os
import ssl
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from playwright.async_api import async_playwright


class SemiAutoLoginManager:
    """半自动登录管理器"""
    
    async def semi_auto_login(self, headless: bool = False) -> Optional[Tuple[str, str]]:
        """
        半自动登录 - 浏览器打开，用户手动登录，脚本自动提取
        
        Args:
            headless: 是否无头模式（通常应为 False 以便用户操作）
        
        Returns:
            (invoker_id, session_id) 或 None
        """
        print("\n🌐 正在启动浏览器...")
        print("📱 请在浏览器中完成登录（包括短信验证码）")
        print("⚠️  登录成功后请不要关闭浏览器，脚本会自动提取凭证")
        print("💡 登录后随便点击页面或刷新，触发网络请求\n")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=headless,
                    args=['--start-maximized']
                )
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                
                # 存储提取的凭证
                credentials = {'invoker_id': None, 'session_id': None}
                
                # 监听所有网络请求
                def capture_credentials(request):
                    headers = request.headers
                    
                    # 尝试多种可能的 header 名称
                    for key, value in headers.items():
                        key_lower = key.lower()
                        if key_lower in ['userid', 'user-id', 'invokerid', 'invoker-id']:
                            if value and value != 'undefined':
                                credentials['invoker_id'] = value
                        if key_lower in ['sessionid', 'session-id']:
                            if value and value != 'undefined':
                                credentials['session_id'] = value
                    
                    # 如果两个都拿到了，输出提示
                    if credentials['invoker_id'] and credentials['session_id']:
                        if not hasattr(capture_credentials, 'notified'):
                            print(f"\n✅ 凭证已自动捕获！")
                            print(f"   Invoker ID: {credentials['invoker_id']}")
                            print(f"   Session ID: {credentials['session_id'][:30]}...")
                            print(f"   可以关闭浏览器了")
                            capture_credentials.notified = True
                
                page.on('request', capture_credentials)
                
                # 打开登录页
                print("🔗 正在打开登录页面...")
                await page.goto('https://www.srdcloud.cn/login', wait_until='networkidle')
                
                print("⏳ 等待登录完成...")
                print("   提示: 登录后如果凭证未自动提取，请刷新页面或点击任意链接\n")
                
                # 等待登录完成
                max_wait = 300  # 5分钟超时
                waited = 0
                check_interval = 1
                
                while waited < max_wait:
                    if credentials['invoker_id'] and credentials['session_id']:
                        print("\n🎉 登录成功！正在关闭浏览器...")
                        await asyncio.sleep(2)
                        break
                    
                    await asyncio.sleep(check_interval)
                    waited += check_interval
                    
                    # 每30秒提示一次
                    if waited % 30 == 0 and waited > 0:
                        print(f"⏱️  已等待 {waited} 秒... (登录后请刷新页面以触发请求)")
                
                await browser.close()
                
                if credentials['invoker_id'] and credentials['session_id']:
                    return credentials['invoker_id'], credentials['session_id']
                else:
                    print("❌ 未能提取凭证")
                    print("💡 可能原因:")
                    print("   - 登录未完成")
                    print("   - 登录后未刷新页面或发起网络请求")
                    print("   - 请尝试手动模式")
                    return None
                    
        except Exception as e:
            print(f"❌ 浏览器启动失败: {e}")
            print("💡 请确保已安装 playwright:")
            print("   pip install playwright")
            print("   playwright install chromium")
            return None


class CodeFreeSimulator:
    def __init__(self, invoker_id: str, session_id: str, client_platform: str = "", 
                 filename: str = "", max_completions: int = 2000, disable_ssl_verification: bool = True):
        """
        初始化模拟器
        
        Args:
            invoker_id: 用户ID (必填)
            session_id: 会话ID (必填)
            client_platform: 操作系统 (如 "macos-arm64", "windows-x64", "linux-x64")
            filename: 文件路径
            max_completions: 最大补全次数
            disable_ssl_verification: 是否禁用SSL证书验证 (默认True，解决证书问题)
        """
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.channel_id: Optional[str] = None
        self.completion_count = 0
        self.max_completions = max_completions
        self.session_id = session_id
        self.invoker_id = invoker_id
        self.api_key: Optional[str] = None
        self.client_platform = client_platform or self._detect_platform()
        self.filename = filename or "simulator.js"
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.running = True
        self.start_time = None
        self.disable_ssl_verification = disable_ssl_verification

        # 模拟代码内容变化
        self.code_variations = [
            {"prefix": "const name = '", "suffix": "';\nconsole.log(name);"},
            {"prefix": "function hello() {\n  return '", "suffix": "';\n}"},
            {"prefix": "let count = ", "suffix": ";\ncount++;"},
            {"prefix": "if (true) {\n  console.log('", "suffix": "');\n}"},
            {"prefix": "const arr = [1, 2, ", "suffix": "];\narr.push(4);"},
            {"prefix": "class MyClass {\n  constructor() {\n    this.value = '", "suffix": "';\n  }\n}"},
            {"prefix": "async function getData() {\n  const response = '", "suffix": "';\n  return response;\n}"},
            {"prefix": "const obj = {\n  key: '", "suffix": "',\n  method() {}\n};"}
        ]

        self.random_texts = [
            "hello", "world", "test", "code", "data", "value", "result", "item",
            "name", "id", "user", "admin", "config", "setting", "option", "param"
        ]

    def _detect_platform(self) -> str:
        """自动检测平台信息"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "darwin":
            return "macos-arm64" if "arm" in machine or "aarch64" in machine else "macos-x64"
        elif system == "windows":
            return "windows-x64"
        elif system == "linux":
            return "linux-x64"
        return f"{system}-{machine}"

    def generate_req_id(self) -> str:
        """生成请求ID"""
        return str(uuid.uuid4())

    def get_random_text(self) -> str:
        """获取随机文本"""
        return random.choice(self.random_texts)

    def get_random_code_variation(self) -> Dict[str, str]:
        """获取随机代码变化"""
        variation = random.choice(self.code_variations)
        random_text = self.get_random_text()
        return {
            "prefix": variation["prefix"] + random_text,
            "suffix": variation["suffix"]
        }

    async def send_message(self, message_name: str, context: Optional[Dict] = None, 
                          payload: Optional[Dict] = None):
        """发送WebSocket消息"""
        if not self.ws:
            print(f"[{self.invoker_id}] WebSocket未连接")
            return

        message = {
            "messageName": message_name,
            "context": context,
            "payload": payload
        }

        wrapped_message = f"<WBChannel>{json.dumps(message, ensure_ascii=False)}</WBChannel>"

        print(f"[{self.invoker_id}] 发送: {message_name}")
        try:
            await self.ws.send(wrapped_message)
        except Exception as e:
            print(f"[{self.invoker_id}] 发送消息失败: {e}")

    async def connect(self):
        """连接到WebSocket服务器"""
        print(f"[{self.invoker_id}] 正在连接WebSocket...")
        
        url = "wss://www.srdcloud.cn/websocket/peerAppgw"
        
        try:
            # 配置SSL上下文
            ssl_context = None
            if self.disable_ssl_verification:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                print(f"[{self.invoker_id}] SSL证书验证已禁用")
            
            self.ws = await websockets.connect(url, ssl=ssl_context)
            self.start_time = datetime.now()
            print(f"[{self.invoker_id}] WebSocket连接已建立")
            await self.register_channel()
            
            await self.handle_messages()
            
        except Exception as e:
            print(f"[{self.invoker_id}] 连接错误: {e}")
            raise

    async def register_channel(self):
        """注册通道"""
        context = {
            "messageName": "RegisterChannel",
            "appGId": "aicode",
            "invokerId": self.invoker_id,
            "sessionId": self.session_id,
            "version": "2.0.0"
        }
        await self.send_message("RegisterChannel", context)

    async def get_user_api_key(self):
        """获取用户API密钥"""
        req_id = self.generate_req_id()
        context = {
            "messageName": "GetUserApiKey",
            "reqId": req_id,
            "invokerId": self.invoker_id,
            "sessionId": self.session_id,
            "version": "2.0.0"
        }

        payload = {
            "clientType": "vscode",
            "clientVersion": "1.106.0-insider",
            "clientPlatform": self.client_platform,
            "gitUrls": [],
            "pluginVersion": "2.0.0"
        }

        await self.send_message("GetUserApiKey", context, payload)

    async def subscribe_channel_group(self):
        """订阅频道组"""
        req_id = self.generate_req_id()
        context = {
            "messageName": "SubscribeChannelGroup",
            "invokerId": self.invoker_id,
            "groupId": "aicode/comment/undefined",
            "reqId": req_id,
            "version": "2.0.0"
        }
        await self.send_message("SubscribeChannelGroup", context)

    async def start_heartbeat(self):
        """启动心跳"""
        async def heartbeat_loop():
            while self.running:
                try:
                    await self.send_message("ClientHeartbeat")
                    await asyncio.sleep(10)
                except Exception as e:
                    print(f"[{self.invoker_id}] 心跳错误: {e}")
                    break

        self.heartbeat_task = asyncio.create_task(heartbeat_loop())

    async def request_code_generation(self):
        """请求代码生成"""
        if not self.api_key:
            print(f"[{self.invoker_id}] 错误: API密钥尚未获取")
            return
            
        req_id = self.generate_req_id()
        code_variation = self.get_random_code_variation()

        context = {
            "messageName": "CodeGenRequest",
            "reqId": req_id,
            "invokerId": self.invoker_id,
            "sessionId": self.session_id,
            "version": "2.0.0",
            "apiKey": self.api_key
        }

        payload = {
            "clientType": "vscode",
            "clientVersion": "1.106.0-insider",
            "gitUrls": [],
            "clientPlatform": self.client_platform,
            "pluginVersion": "2.0.0",
            "messages": {
                "language": "javascript",
                "filename": self.filename,
                "prefix": code_variation["prefix"],
                "suffix": code_variation["suffix"],
                "max_new_tokens": 256,
                "stop_words": ["\n"]
            }
        }

        print(f"[{self.invoker_id}] 请求代码补全 #{self.completion_count + 1}/{self.max_completions}")
        await self.send_message("CodeGenRequest", context, payload)

    async def send_user_activity(self, activity_type: str = "code_display"):
        """发送用户活动通知"""
        if not self.api_key:
            return
            
        req_id = self.generate_req_id()
        context = {
            "messageName": "UserActivityNotify",
            "reqId": req_id,
            "invokerId": self.invoker_id,
            "version": "2.0.0",
            "apiKey": self.api_key
        }

        payload = {
            "client": {
                "platform": self.client_platform,
                "type": "vscode",
                "version": "1.106.0-insider",
                "pluginVersion": "2.0.0",
                "gitUrl": "",
                "gitUrls": [],
                "projectName": "code-free"
            },
            "activityType": activity_type,
            "service": "codegen",
            "lines": random.random() * 2,
            "count": 1
        }

        await self.send_message("UserActivityNotify", context, payload)

    async def handle_message(self, data: str):
        """处理接收到的消息"""
        try:
            if data.startswith("<WBChannel>") and data.endswith("</WBChannel>"):
                json_str = data[11:-12]
                message = json.loads(json_str)
            else:
                message = json.loads(data)

            message_name = message.get("messageName", "")
            print(f"[{self.invoker_id}] 收到: {message_name}")

            if message_name == "RegisterChannel_resp":
                self.channel_id = message.get("context", {}).get("channelId")
                print(f"[{self.invoker_id}] 通道注册成功: {self.channel_id}")
                await self.get_user_api_key()

            elif message_name == "GetUserApiKey_resp":
                self.api_key = message.get("payload", {}).get("apiKey")
                if self.api_key:
                    print(f"[{self.invoker_id}] API密钥获取成功")
                    await self.subscribe_channel_group()
                    await self.start_heartbeat()
                    await self.start_coding_simulation()
                else:
                    print(f"[{self.invoker_id}] ❌ API密钥获取失败，可能凭证已过期")
                    await self.disconnect()

            elif message_name == "SubscribeChannelGroup_resp":
                print(f"[{self.invoker_id}] 频道组订阅成功")

            elif message_name == "CodeGenRequest_resp":
                self.completion_count += 1
                answer = message.get("payload", {}).get("answer", "")
                print(f"[{self.invoker_id}] 代码补全 #{self.completion_count}: \"{answer[:50]}...\"")

                await self.send_user_activity("code_display")

                if self.completion_count >= self.max_completions:
                    print(f"[{self.invoker_id}] 已完成 {self.max_completions} 次，准备断开...")
                    await self.disconnect()
                    return

                delay = random.uniform(0.5, 2.5)
                await asyncio.sleep(delay)
                await self.request_code_generation()

            elif message_name == "ServerHeartbeat":
                await self.send_message("ServerHeartbeatResponse")

            elif message_name == "ClientHeartbeatResponse":
                pass

        except Exception as e:
            print(f"[{self.invoker_id}] 解析消息失败: {e}")

    async def handle_messages(self):
        """处理所有接收到的消息"""
        try:
            async for message in self.ws:
                if not self.running:
                    break
                await self.handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print(f"[{self.invoker_id}] WebSocket连接已关闭")
        except Exception as e:
            print(f"[{self.invoker_id}] 消息处理错误: {e}")
        finally:
            if self.running:
                await self.disconnect()

    async def start_coding_simulation(self):
        """开始模拟编码过程"""
        print(f"[{self.invoker_id}] 开始模拟编码...")
        await asyncio.sleep(1)
        await self.request_code_generation()

    async def disconnect(self):
        """断开连接"""
        print(f"[{self.invoker_id}] 正在断开连接...")
        self.running = False
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                print(f"[{self.invoker_id}] 关闭连接时出错: {e}")
        
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        print(f"[{self.invoker_id}] 完成！补全次数: {self.completion_count}, 耗时: {elapsed:.1f}秒")


class SimulatorManager:
    """模拟器管理器"""
    
    def __init__(self):
        self.simulators: List[CodeFreeSimulator] = []
        
    def load_from_file(self, filepath: str) -> List[Dict[str, str]]:
        """从文件加载账号信息"""
        accounts = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split(',')
                    if len(parts) >= 2:
                        accounts.append({
                            'invoker_id': parts[0].strip(),
                            'session_id': parts[1].strip()
                        })
                    else:
                        print(f"警告: 第{line_num}行格式错误，已跳过")
            
            print(f"✅ 成功加载 {len(accounts)} 个账号")
            return accounts
        except FileNotFoundError:
            print(f"❌ 文件不存在: {filepath}")
            return []
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return []
    
    async def run_simulator(self, invoker_id: str, session_id: str, max_completions: int = 2000, 
                          disable_ssl_verification: bool = True):
        """运行单个模拟器"""
        simulator = CodeFreeSimulator(
            invoker_id=invoker_id,
            session_id=session_id,
            max_completions=max_completions,
            disable_ssl_verification=disable_ssl_verification
        )
        self.simulators.append(simulator)
        
        try:
            await simulator.connect()
        except Exception as e:
            print(f"[{invoker_id}] 运行失败: {e}")
    
    async def run_batch(self, accounts: List[Dict[str, str]], max_completions: int = 2000, 
                      disable_ssl_verification: bool = True):
        """批量运行多个模拟器"""
        tasks = [
            self.run_simulator(acc['invoker_id'], acc['session_id'], max_completions, disable_ssl_verification)
            for acc in accounts
        ]
        await asyncio.gather(*tasks, return_exceptions=True)


def print_banner():
    """打印工具横幅"""
    banner = """
╔═══════════════════════════════════════════════════╗
║     CodeFree WebSocket Simulator Tool v2.0       ║
║              Enhanced with Semi-Auto Login        ║
╚═══════════════════════════════════════════════════╝
    """
    print(banner)


def print_menu():
    """打印菜单"""
    menu = """
请选择运行模式:
  1. 🤖 半自动模式 (浏览器自动打开，手动登录，自动提取凭证) ⭐ 推荐
  2. ✋ 手动模式 (直接输入凭证)
  3. 📦 批量模式 (从文件导入多账号)
  4. 📝 生成配置文件模板
  5. 🚪 退出

请输入选项 (1-5): """
    return input(menu).strip()


async def semi_auto_mode():
    """半自动模式"""
    print("\n" + "="*50)
    print("🤖 半自动登录模式")
    print("="*50)
    
    manager = SemiAutoLoginManager()
    result = await manager.semi_auto_login()
    
    if not result:
        print("\n❌ 未能获取凭证")
        print("💡 您可以尝试:")
        print("   - 重新运行并在登录后刷新页面")
        print("   - 使用手动模式 (选项 2)")
        return
    
    invoker_id, session_id = result
    
    print(f"\n✅ 凭证获取成功!")
    print(f"   Invoker ID: {invoker_id}")
    print(f"   Session ID: {session_id[:30]}...")
    
    # 询问运行参数
    print("\n" + "-"*50)
    max_completions_input = input("请输入最大补全次数 (默认 2000，直接回车使用默认值): ").strip()
    max_completions = int(max_completions_input) if max_completions_input.isdigit() else 2000
    
    print(f"\n📊 配置信息:")
    print(f"  Invoker ID: {invoker_id}")
    print(f"  Session ID: {session_id[:30]}...")
    print(f"  最大补全次数: {max_completions}")
    print(f"\n🚀 开始运行模拟器...\n")
    
    sim_manager = SimulatorManager()
    try:
        await sim_manager.run_simulator(invoker_id, session_id, max_completions, disable_ssl_verification=True)
    except KeyboardInterrupt:
        print("\n\n⚠️  收到中断信号，正在停止...")


async def manual_mode():
    """手动模式"""
    print("\n" + "="*50)
    print("✋ 手动模式")
    print("="*50)
    
    print("\n💡 获取凭证的方法:")
    print("   1. 打开 https://www.srdcloud.cn/login 并登录")
    print("   2. 按 F12 打开开发者工具 -> Network 标签")
    print("   3. 刷新页面或点击任意链接")
    print("   4. 找到任意请求，查看 Request Headers")
    print("   5. 找到 userid 和 sessionid 字段\n")
    
    invoker_id = input("请输入 Invoker ID (User ID): ").strip()
    session_id = input("请输入 Session ID: ").strip()
    
    if not invoker_id or not session_id:
        print("❌ Invoker ID 和 Session ID 不能为空")
        return
    
    # 询问运行参数
    print("\n" + "-"*50)
    max_completions_input = input("请输入最大补全次数 (默认 2000，直接回车使用默认值): ").strip()
    max_completions = int(max_completions_input) if max_completions_input.isdigit() else 2000
    
    print(f"\n📊 配置信息:")
    print(f"  Invoker ID: {invoker_id}")
    print(f"  Session ID: {session_id[:30]}...")
    print(f"  最大补全次数: {max_completions}")
    print(f"\n🚀 开始运行模拟器...\n")
    
    manager = SimulatorManager()
    try:
        await manager.run_simulator(invoker_id, session_id, max_completions, disable_ssl_verification=True)
    except KeyboardInterrupt:
        print("\n\n⚠️  收到中断信号，正在停止...")


async def batch_mode():
    """批量模式"""
    print("\n" + "="*50)
    print("📦 批量模式")
    print("="*50)
    
    filepath = input("\n请输入配置文件路径 (默认: accounts.txt): ").strip()
    
    if not filepath:
        filepath = "accounts.txt"
    
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        print("💡 您可以使用选项 4 生成配置文件模板")
        return
    
    manager = SimulatorManager()
    accounts = manager.load_from_file(filepath)
    
    if not accounts:
        print("❌ 没有加载到有效账号")
        return
    
    print(f"\n📊 将运行 {len(accounts)} 个模拟器")
    for idx, acc in enumerate(accounts, 1):
        print(f"   {idx}. Invoker ID: {acc['invoker_id']}")
    
    # 询问运行参数
    max_completions_input = input("\n请输入每个账号的最大补全次数 (默认 2000，直接回车使用默认值): ").strip()
    max_completions = int(max_completions_input) if max_completions_input.isdigit() else 2000
    
    confirm = input(f"\n确认开始批量运行? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("已取消")
        return
    
    print(f"\n🚀 开始批量运行 {len(accounts)} 个模拟器...\n")
    
    try:
        await manager.run_batch(accounts, max_completions, disable_ssl_verification=True)
    except KeyboardInterrupt:
        print("\n\n⚠️  收到中断信号，正在停止所有模拟器...")


def generate_template():
    """生成配置文件模板"""
    print("\n" + "="*50)
    print("📝 生成配置文件模板")
    print("="*50)
    
    template = """# CodeFree 账号配置文件
# 格式: invoker_id,session_id
# 每行一个账号，使用逗号分隔
# 以 # 开头的行为注释

# 示例 1
186812,488eb840-c068-4c75-9df3-a3XXXXX

# 示例 2
# 123456,abcdef12-3456-7890-abcd-efghijklmnop

# 添加更多账号...
"""
    
    filename = input("请输入文件名 (默认: accounts.txt): ").strip()
    if not filename:
        filename = "accounts.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(template)
        print(f"✅ 配置文件模板已生成: {filename}")
        print(f"📝 请编辑 {filename} 文件，填入你的账号信息")
        print(f"💡 可以使用半自动模式 (选项 1) 获取凭证后手动添加到文件中")
    except Exception as e:
        print(f"❌ 生成文件失败: {e}")


async def main():
    """主函数"""
    print_banner()
    
    while True:
        try:
            choice = print_menu()
            
            if choice == '1':
                await semi_auto_mode()
                break
            elif choice == '2':
                await manual_mode()
                break
            elif choice == '3':
                await batch_mode()
                break
            elif choice == '4':
                generate_template()
                print()
            elif choice == '5':
                print("\n👋 再见!")
                sys.exit(0)
            else:
                print("❌ 无效选项，请重新选择\n")
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()
            break


if __name__ == "__main__":
    try:
        # 检查依赖
        try:
            import playwright
        except ImportError:
            print("❌ 缺少依赖: playwright")
            print("请运行以下命令安装:")
            print("  pip install playwright")
            print("  playwright install chromium")
            sys.exit(1)
        
        # 运行主程序
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()