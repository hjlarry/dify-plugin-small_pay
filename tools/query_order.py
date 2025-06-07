from collections.abc import Generator
from typing import Any
import logging
import time

from dify_plugin.config.logger_format import plugin_logger_handler
import httpx
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)

ORDER_STATUS_MAP = {
    0: "未支付",
    1: "支付成功",
    2: "支付失败",
    3: "已过期",
    4: "订单取消",
    5: "订单退款"
}

class QueryOrderTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        order_no = tool_parameters.get("order_no")
        if not order_no and self.session.storage.exist(self.session.conversation_id):
            order_no = self.session.storage.get(self.session.conversation_id).decode("utf-8")
        if not order_no:
            yield self.create_text_message("订单号不存在")
            return
        
        url = "https://pay.freecicoda.com/smallPayment/api/v1/order/queryOrder"
        payload = {
            "apiKey": self.runtime.credentials.get("api_key"),
            "orderNo": order_no
        }
        logger.info(f"发送订单参数: {payload}")
        response = httpx.get(url, params=payload).json()
        logger.info(f"查询订单响应: {response}")
        if response.get("code") != 200:
            raise ValueError(response.get("message"))
        
        status = response.get("data").get("status")
        if status == 1:
            if self.session.storage.exist(f"{self.session.conversation_id}_valid_times"):
                valid_times = int.from_bytes(self.session.storage.get(f"{self.session.conversation_id}_valid_times"), byteorder='big', signed=False)
                valid_times = valid_times - 1
                if valid_times <= 0:
                    self.session.storage.delete(f"{self.session.conversation_id}_valid_times")
                else:
                    self.session.storage.set(f"{self.session.conversation_id}_valid_times", valid_times.to_bytes(4, byteorder='big', signed=False))
                response["validTimes"] = valid_times
            else:
                yield self.create_text_message("该订单次数用完")
                return

        order_status = ORDER_STATUS_MAP.get(status, "未知状态")
        yield self.create_text_message(order_status)
        yield self.create_json_message(response)
        
        
        

        
