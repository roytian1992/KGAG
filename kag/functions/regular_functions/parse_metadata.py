from typing import Dict, Any, List
import json
import logging
from kag.utils.function_manager import EnhancedJSONUtils, process_with_format_guarantee
from kag.utils.general_text import general_repair_template

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    集成format.py的实体提取器
    确保最终返回的是correct_json_format处理后的结果
    """
    
    def __init__(self, prompt_loader=None, llm=None):
        self.prompt_loader = prompt_loader
        self.llm = llm
        
        # 定义验证规则
        self.required_fields = []
        self.field_validators = {}
        
        # 修复提示词模板
        self.repair_template = general_repair_template
    
    def call(self, params: str, **kwargs) -> str:
        """
        调用实体提取，保证返回correct_json_format处理后的结果
        
        Args:
            params: 参数字符串
            **kwargs: 其他参数
            
        Returns:
            str: 经过correct_json_format处理的JSON字符串
        """
        try:
            # 解析参数
            params_dict = json.loads(params)
            text = params_dict.get("text", "")
            title = params_dict.get("title", "")
            subtitle = params_dict.get("subtitle", "")
            file_type = params_dict.get("file_type", "novel")
            
        except Exception as e:
            logger.error(f"参数解析失败: {e}")
            # 即使是错误结果，也要经过correct_json_format处理
            error_result = {"error": f"参数解析失败: {str(e)}", "metadata": {}}
            from kag.utils.format import correct_json_format
            return correct_json_format(json.dumps(error_result, ensure_ascii=False))
                
        try:
            if subtitle:
                title = f"{title}\n子标题：{subtitle}"
                
            if file_type == "screenplay":
                prompt_id = "parse_screenplay_prompt"
                variables = {
                    "title": title
                }
            else:
                prompt_id = "parse_novel_prompt"
                varialbles = {
                    "title": title,
                    "text": text
                }
                
            prompt_text = self.prompt_loader.render_prompt(
                prompt_id=prompt_id,
                variables=variables
            )
           
            # 构造初始消息
            messages = []
            messages.append({"role": "user", "content": prompt_text})
            
            # 使用增强工具处理响应，保证返回correct_json_format处理后的结果
            corrected_json = process_with_format_guarantee(
                llm_client=self.llm,
                messages=messages,
                required_fields=self.required_fields,
                field_validators=self.field_validators,
                max_retries=2,
                repair_template=self.repair_template
            )
            
            logger.info("元数据提取完成，返回格式化后的JSON")
            return corrected_json
            
        except Exception as e:
            logger.error(f"元数据提取过程中出现异常: {e}")
            error_result = {
                "error": f"元数据提取失败: {str(e)}",
                "metadata": {}
            }
            from kag.utils.format import correct_json_format
            return correct_json_format(json.dumps(error_result, ensure_ascii=False))

