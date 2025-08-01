"""
属性反思器
使用增强的JSON处理工具
"""
from typing import Dict, Any, List
import json
import logging
from kag.utils.function_manager import EnhancedJSONUtils, process_with_format_guarantee
from kag.utils.general_text import attribute_reflection_repair_template

logger = logging.getLogger(__name__)



class AttributeReflector:
    """
    属性反思器
    确保最终返回的是correct_json_format处理后的结果
    """
    
    def __init__(self, prompt_loader=None, llm=None):
        self.prompt_loader = prompt_loader
        self.llm = llm
        
        # 定义验证规则
        self.required_fields = []
        self.field_validators = {}
        
        # 修复提示词模板
        self.repair_template = attribute_reflection_repair_template
    
    def call(self, params: str, **kwargs) -> str:
        """
        调用属性反思，保证返回correct_json_format处理后的结果
        
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
            entity_name = params_dict.get("entity_name", "")
            description = params_dict.get("description", "")
            entity_type = params_dict.get("entity_type", "")
            attribute_definitions = params_dict.get("attribute_definitions", "")
            abbreviations = params_dict.get("abbreviations", "")  # 和实体抽取逻辑保持一致
            feedbacks = params_dict.get("feedbacks", "")
            original_text = params_dict.get("original_text", "")
            previous_results = params_dict.get("previous_results", "")
            
        except Exception as e:
            logger.error(f"参数解析失败: {e}")
            # 即使是错误结果，也要经过correct_json_format处理
            error_result = {
                "error": f"参数解析失败: {str(e)}", 
                "feedbacks": [],
                "need_additional_context": False,
                "attributes_to_retry": [],
            }
            from kag.utils.format import correct_json_format
            return correct_json_format(json.dumps(error_result, ensure_ascii=False))
                
        try:
            # 构建提示词变量
            if original_text and previous_results and feedbacks:
                text = f"这些是之前的上下文：\n{original_text } \n这些是新增的文本，用于对已有的抽取结果进行补充和改进:\n{text}\n"
                
            prompt_text = self.prompt_loader.render_prompt(
                prompt_id='extract_attributes_prompt',
                variables={
                    "text": text,
                    "entity_name": entity_name,
                    "description": description,
                    "entity_type": entity_type,
                    "attribute_definitions": attribute_definitions
                }
            )
            
            # agent 指令（system prompt），同你之前写法
            agent_prompt_text = self.prompt_loader.render_prompt(
                prompt_id="agent_prompt",
                variables={"abbreviations": abbreviations}
            )
            messages = [{"role": "system", "content": agent_prompt_text}]
            
            if original_text and previous_results and feedbacks:
                background_info = f"上一次信息抽取的上下文：\n{original_text.strip()}\n\n" 
                
                background_info += f"上一次抽取的结果如下：\n{previous_results}\n反馈建议如下：\n{feedbacks}\n请仅针对缺失字段或内容不足的字段进行补充，保留已有字段。"
                
                messages.append({
                    "role": "user",
                    "content": background_info
                })
                
                prompt_text = prompt_text + "\n" + f"这是之前抽取的结果：\n {previous_results} \n 在此基础上根据建议进行补充和改进。"

            messages.append({"role": "user", "content": prompt_text})
            
            # 使用增强工具处理响应，保证返回correct_json_format处理后的结果
            corrected_json = process_with_format_guarantee(
                llm_client=self.llm,
                messages=messages,
                required_fields=self.required_fields,
                field_validators=self.field_validators,
                max_retries=3,
                repair_template=self.repair_template
            )
            
            logger.info("属性反思完成，返回格式化后的JSON")
            return corrected_json
            
        except Exception as e:
            logger.error(f"属性反思过程中出现异常: {e}")
            error_result = {
                "error": f"属性反思失败: {str(e)}",
                "feedbacks": [],
                "need_additional_context": False,
                "attributes_to_retry": [],
            }
            from kag.utils.format import correct_json_format
            return correct_json_format(json.dumps(error_result, ensure_ascii=False))

