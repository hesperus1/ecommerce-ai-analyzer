"""
意图路由模块 - 负责将用户输入分类到不同的处理分支

分类：
1. IRRELEVANT - 无关闲聊（天气、写诗等）
2. KNOWLEDGE_QA - 业务概念与知识问答（如"点击率代表什么"）
3. DATA_QUERY - 数据查询与诊断（如"昨天引力魔方的ROI是多少"）
"""

import requests
import json
import re

# 无关问题关键词
IRRELEVANT_KEYWORDS = [
    # 问候语
    '你好', '您好', '嗨', '哈喽', 'hello', 'hi', '早上好', '下午好', '晚上好', '再见',
    # 闲聊
    '吃饭了吗', '天气', '天气怎么样', '今天天气', '明天天气', '历史', '故事',
    '新闻', '娱乐', '电影', '音乐', '游戏', '旅游', '美食',
    # 创作类
    '写诗', '写文章', '写故事', '编段子', '作对联', '写代码', '编程',
    # 其他无关话题
    '笑话', '谜语', '脑筋急转弯', '星座', '运势', '股票', '基金',
    '足球', '篮球', '体育', '运动', '健康', '医疗', '教育', '学习'
]

# 知识问答关键词（不需要查库的概念性问题）
KNOWLEDGE_QA_KEYWORDS = [
    # 指标定义
    '什么是', '代表什么', '是什么', '含义', '定义', '意思',
    '如何计算', '怎么算', '计算公式',
    # 运营策略
    '怎么开', '怎么设置', '如何优化', '优化方法', '策略',
    '技巧', '方法', '教程', '指南',
    # 概念解释
    '区别', '差异', '对比', '比较',
    '为什么', '原理', '机制', '逻辑'
]

# 数据查询关键词（需要查库的问题）
DATA_QUERY_KEYWORDS = [
    # 查询类
    '是多少', '多少', '查询', '查一下', '查看', '统计', '汇总',
    # 分析类
    '分析', '归因', '诊断', '异常', '问题', '为什么',
    # 趋势类
    '趋势', '变化', '对比', '环比', '同比',
    # 排名类
    '排名', '最高', '最低', 'top', '最好', '最差',
    # 具体数据
    '花费', '点击', '展现', '转化', '订单', 'gmv', 'roi',
    'ctr', 'cvr', '漏斗', '流失'
]

def route_intent(user_question: str, api_key: str) -> str:
    """
    意图路由 - 将用户问题分类到不同的处理分支
    
    Args:
        user_question: 用户的自然语言问题
        api_key: 硅基流动 API Key
    
    Returns:
        'IRRELEVANT' - 无关闲聊
        'KNOWLEDGE_QA' - 业务概念与知识问答
        'DATA_QUERY' - 数据查询与诊断
    """
    if not user_question or not user_question.strip():
        return 'IRRELEVANT'
    
    question = user_question.lower().strip()
    
    # 第一级：快速规则匹配 - 无关问题
    for keyword in IRRELEVANT_KEYWORDS:
        if keyword.lower() in question:
            print(f"[意图路由] 快速匹配：无关问题 - {keyword}")
            return 'IRRELEVANT'
    
    # 第二级：快速规则匹配 - 知识问答
    for keyword in KNOWLEDGE_QA_KEYWORDS:
        if keyword.lower() in question:
            # 需要进一步判断是否真的是知识问答
            # 如果同时包含数据查询关键词，则判定为数据查询
            has_data_query = any(dq_keyword.lower() in question for dq_keyword in DATA_QUERY_KEYWORDS)
            if not has_data_query:
                print(f"[意图路由] 快速匹配：知识问答 - {keyword}")
                return 'KNOWLEDGE_QA'
    
    # 第三级：调用大模型进行精确意图分类
    return _classify_with_model(user_question, api_key)

def _classify_with_model(user_question: str, api_key: str) -> str:
    """
    使用大模型进行精确意图分类
    
    Args:
        user_question: 用户问题
        api_key: API Key
    
    Returns:
        分类结果
    """
    system_prompt = """
你是一个电商数据分析专家，负责将用户的问题分类到以下三类：

【分类标准】
1. IRRELEVANT（无关闲聊）：与电商广告投放完全无关的问题，如天气、写诗、问候语等。
2. KNOWLEDGE_QA（业务概念与知识问答）：询问电商指标定义、运营策略理论等不需要查询具体数据库中数值的问题。
   例如："点击率代表什么？"、"直通车怎么开？"、"ROI如何计算？"
3. DATA_QUERY（数据查询与诊断）：明确询问具体计划、渠道的表现，或要求排查数据异常，必须依赖底层数据的问题。
   例如："昨天引力魔方的ROI是多少？"、"帮我查一下点击率异常的计划"、"分析最近3天的漏斗流失"

【输出格式】
只输出分类结果：IRRELEVANT、KNOWLEDGE_QA 或 DATA_QUERY

【示例】
用户问：你好
输出：IRRELEVANT

用户问：点击率代表什么？
输出：KNOWLEDGE_QA

用户问：昨天直通车的ROI是多少？
输出：DATA_QUERY
"""
    
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "Qwen/Qwen3.5-9B",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ],
        "temperature": 0.01,
        "max_tokens": 20
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        classification = result["choices"][0]["message"]["content"].strip()
        
        # 验证分类结果
        if classification in ['IRRELEVANT', 'KNOWLEDGE_QA', 'DATA_QUERY']:
            print(f"[意图路由] 模型分类结果：{classification}")
            return classification
        else:
            print(f"[意图路由] 模型返回无效结果，默认归类为 DATA_QUERY")
            return 'DATA_QUERY'
            
    except Exception as e:
        print(f"[意图路由] 模型调用失败，使用默认分类：{str(e)}")
        # 默认归类为数据查询
        return 'DATA_QUERY'

# 测试代码
if __name__ == "__main__":
    # 需要设置环境变量或传入 API Key
    import os
    api_key = os.environ.get("SILICONFLOW_API_KEY", "")
    
    test_cases = [
        "你好",
        "今天天气怎么样",
        "帮我写一首诗",
        "点击率代表什么？",
        "ROI如何计算？",
        "直通车怎么开？",
        "昨天引力魔方的ROI是多少？",
        "分析最近3天的漏斗流失情况",
        "检查有没有异常数据"
    ]
    
    for test in test_cases:
        result = route_intent(test, api_key)
        print(f"问题: {test} -> 分类: {result}")
