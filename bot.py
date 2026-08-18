import os

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

# 初始化 NoneBot
nonebot.init()

# 注册 OneBot V11 适配器（负责与 QQ 协议端通信）
driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)

# 加载 src/plugins 下的所有插件
_plugin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "plugins")
nonebot.load_plugins(_plugin_dir)

if __name__ == "__main__":
    nonebot.run()
