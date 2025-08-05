"""
图谱反思器
使用增强的JSON处理工具
"""
from typing import Dict, Any, List
import json
import logging
from kag.utils.function_manager import EnhancedJSONUtils, process_with_format_guarantee

logger = logging.getLogger(__name__)


repair_template = """
请修复以下图谱反思结果中的问题：

原始响应：{original_response}
错误信息：{error_message}

请确保返回的JSON包含：
1. "reflection_result"字段，包含反思结果
2. "graph_quality_score"字段，包含图谱质量评分
3. "issues"字段，包含发现的问题列表
4. "suggestions"字段，包含改进建议列表
5. JSON格式正确

请直接返回修复后的JSON，不要包含解释。
"""


class GraphReflector:
    """
    图谱反思器
    确保最终返回的是correct_json_format处理后的结果
    """
    
    def __init__(self, prompt_loader=None, llm=None):
        self.prompt_loader = prompt_loader
        self.llm = llm
        
        # 定义验证规则
        self.required_fields = ["reflection_result"]
        self.field_validators = {
            "reflection_result": lambda x: isinstance(x, dict),
            "graph_quality_score": lambda x: isinstance(x, (int, float)) if x is not None else True,
            "issues": lambda x: isinstance(x, list) if x is not None else True,
            "suggestions": lambda x: isinstance(x, list) if x is not None else True
        }
        
        # 修复提示词模板
        self.repair_template = repair_template
    
    def call(self, params: str, **kwargs) -> str:
        """
        调用图谱反思，保证返回correct_json_format处理后的结果
        
        Args:
            params: 参数字符串
            **kwargs: 其他参数
            
        Returns:
            str: 经过correct_json_format处理的JSON字符串
        """
        try:
            # 解析参数
            params_dict = json.loads(params)
            original_text = params_dict.get("original_text", "")
            graph_data = params_dict.get("graph_data", "")
            entity_types = params_dict.get("entity_types", "")
            relation_types = params_dict.get("relation_types", "")
            quality_criteria = params_dict.get("quality_criteria", "")
            
        except Exception as e:
            logger.error(f"参数解析失败: {e}")
            # 即使是错误结果，也要经过correct_json_format处理
            error_result = {
                "error": f"参数解析失败: {str(e)}", 
                "reflection_result": {},
                "graph_quality_score": 0,
                "issues": [],
                "suggestions": []
            }
            from kag.utils.format import correct_json_format
            return correct_json_format(json.dumps(error_result, ensure_ascii=False))
        
        if not original_text or not graph_data:
            error_result = {
                "error": "缺少必要参数", 
                "reflection_result": {},
                "graph_quality_score": 0,
                "issues": [],
                "suggestions": []
            }
            from kag.utils.format import correct_json_format
            return correct_json_format(json.dumps(error_result, ensure_ascii=False))
        
        try:
            # 构建提示词变量
            variables = {
                'original_text': original_text,
                'graph_data': graph_data,
                'entity_types': entity_types,
                'relation_types': relation_types,
                'quality_criteria': quality_criteria
            }
            
            # 渲染提示词
            prompt_text = self.prompt_loader.render_prompt('graph_reflection_prompt', variables)
            
            # 构建消息
            messages = [{"role": "user", "content": prompt_text}]
            
            # 使用增强工具处理响应，保证返回correct_json_format处理后的结果
            corrected_json = process_with_format_guarantee(
                llm_client=self.llm,
                messages=messages,
                required_fields=self.required_fields,
                field_validators=self.field_validators,
                max_retries=3,
                repair_template=self.repair_template
            )
            
            logger.info("图谱反思完成，返回格式化后的JSON")
            return corrected_json
            
        except Exception as e:
            logger.error(f"图谱反思过程中出现异常: {e}")
            error_result = {
                "error": f"图谱反思失败: {str(e)}",
                "reflection_result": {},
                "graph_quality_score": 0,
                "issues": [],
                "suggestions": []
            }
            from kag.utils.format import correct_json_format
            return correct_json_format(json.dumps(error_result, ensure_ascii=False))

