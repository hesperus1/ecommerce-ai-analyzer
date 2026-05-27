import requests
import json
import re
import sqlite3

# ==================== 业务边界定义 ====================
# 业务相关关键词列表 - 只有包含这些关键词的问题才会被处理
BUSINESS_KEYWORDS = [
    # 业务场景
    "漏斗", "流失", "转化", "曝光", "点击", "订单",
    # 分析类型
    "分析", "查询", "检查", "统计", "对比", "趋势", "排名",
    # 指标关键词
    "花费", "预算", "成本", "支出", "gmv", "成交额", "销售额", 
    "roi", "投入产出", "投资回报", "点击率", "ctr", "转化率", "cvr",
    # 渠道名称
    "直通车", "引力魔方", "万相台", "渠道", "计划",
    # 异常检测
    "异常", "问题", "不对劲", "告警", "异常数据",
    # 时间范围
    "最近", "今天", "昨天", "本周", "上周", "本月", "上月", "天", "周", "月"
]

# 友好提示信息
BUSINESS_PROMPT = """
👋 您好！我是电商数据分析助手，专注于广告投放数据的分析和归因。

**我可以帮您分析：**
- 📈 漏斗流失分析（曝光→点击→订单）
- 💰 ROI 投入产出分析
- 🔍 异常数据检测
- 📉 广告花费趋势
- 🎯 点击率/转化率分析
- 🏷️ GMV 销售额分析
- 📦 订单数据分析

**示例问题：**
- 分析引力魔方最近 3 天的漏斗流失情况
- 查询各渠道的 ROI 排名
- 检查最近 3 天有没有异常数据

**请提问与电商广告数据分析相关的问题，感谢您的使用！**
"""

def is_business_related(question: str) -> bool:
    """
    检查问题是否与业务相关
    
    Args:
        question: 用户问题
        
    Returns:
        True 如果问题包含业务关键词，False 否则
    """
    if not question or not isinstance(question, str):
        return False
    
    question_lower = question.lower()
    for keyword in BUSINESS_KEYWORDS:
        if keyword.lower() in question_lower:
            return True
    return False

# ==================== 业务意图定义 ====================
INTENT_DEFINITIONS = {
    "funnel_analysis": {
        "name": "漏斗流失分析",
        "patterns": ["漏斗", "流失", "转化路径", "曝光点击转化"],
        "description": "分析用户从曝光到点击到订单的转化漏斗，识别流失环节"
    },
    "roi_analysis": {
        "name": "ROI分析",
        "patterns": ["roi", "投入产出", "投资回报率", "投入产出比"],
        "description": "分析各渠道或计划的投入产出比"
    },
    "spend_analysis": {
        "name": "花费分析",
        "patterns": ["花费", "烧钱", "预算", "成本", "支出"],
        "description": "分析广告花费情况"
    },
    "abnormal_detection": {
        "name": "异常检测",
        "patterns": ["异常", "问题", "不对劲", "检查", "告警"],
        "description": "检测数据异常情况"
    },
    "ctr_analysis": {
        "name": "点击率分析",
        "patterns": ["点击率", "ctr", "点击", "点击量"],
        "description": "分析广告点击率"
    },
    "cvr_analysis": {
        "name": "转化率分析",
        "patterns": ["转化率", "cvr", "转化", "订单转化"],
        "description": "分析点击到订单的转化率"
    },
    "gmv_analysis": {
        "name": "GMV分析",
        "patterns": ["gmv", "成交额", "销售额", "收入", "业绩"],
        "description": "分析成交金额"
    },
    "order_analysis": {
        "name": "订单分析",
        "patterns": ["订单", "成交", "下单", "订单量"],
        "description": "分析订单数量"
    },
    "channel_analysis": {
        "name": "渠道分析",
        "patterns": ["渠道", "直通车", "引力魔方", "万相台"],
        "description": "分析特定渠道的表现"
    },
    "daily_report": {
        "name": "日报分析",
        "patterns": ["日报", "周报", "月报", "汇总", "整体"],
        "description": "生成定期数据报告"
    }
}

# 默认时间范围映射
TIME_MAPPING = {
    '最近3天': "date >= DATE('now', '-3 days')",
    '最近7天': "date >= DATE('now', '-7 days')",
    '最近一周': "date >= DATE('now', '-7 days')",
    '昨天': "date = DATE('now', '-1 days')",
    '今天': "date = DATE('now')",
    '本周': "strftime('%W', date) = strftime('%W', 'now')",
    '上周': "strftime('%W', date) = strftime('%W', 'now', '-7 days')",
}

# 根据意图生成SQL的模板
INTENT_SQL_TEMPLATES = {
    "funnel_analysis": """SELECT campaign_name, SUM(impressions) AS impressions, 
                          SUM(clicks) AS clicks, SUM(orders) AS orders, 
                          SUM(clicks)*100.0/MAX(SUM(impressions),1) AS ctr, 
                          SUM(orders)*100.0/MAX(SUM(clicks),1) AS cvr 
                          FROM ad_campaign_daily_reports 
                          WHERE {channel_condition} AND {time_condition} 
                          GROUP BY campaign_name""",
    
    "roi_analysis": """SELECT campaign_type, campaign_name, 
                       SUM(gmv)/MAX(SUM(spend),1) AS roi, 
                       SUM(spend) AS total_spend, SUM(gmv) AS total_gmv 
                       FROM ad_campaign_daily_reports 
                       WHERE {channel_condition} AND {time_condition} 
                       GROUP BY campaign_type, campaign_name 
                       ORDER BY roi ASC""",
    
    "spend_analysis": """SELECT campaign_type, campaign_name, 
                         SUM(spend) AS total_spend, SUM(orders) AS total_orders,
                         SUM(gmv)/MAX(SUM(spend),1) AS roi 
                         FROM ad_campaign_daily_reports 
                         WHERE {channel_condition} AND {time_condition} 
                         GROUP BY campaign_type, campaign_name 
                         ORDER BY total_spend DESC""",
    
    "abnormal_detection": """SELECT campaign_type, campaign_name, date,
                            spend, impressions, clicks, orders, gmv
                            FROM ad_campaign_daily_reports 
                            WHERE {channel_condition} AND {time_condition} 
                            ORDER BY date DESC""",
    
    "ctr_analysis": """SELECT campaign_type, campaign_name, 
                       SUM(impressions) AS impressions, SUM(clicks) AS clicks,
                       SUM(clicks)*100.0/MAX(SUM(impressions),1) AS ctr 
                       FROM ad_campaign_daily_reports 
                       WHERE {channel_condition} AND {time_condition} 
                       GROUP BY campaign_type, campaign_name 
                       ORDER BY ctr ASC""",
    
    "cvr_analysis": """SELECT campaign_type, campaign_name, 
                       SUM(clicks) AS clicks, SUM(orders) AS orders,
                       SUM(orders)*100.0/MAX(SUM(clicks),1) AS cvr 
                       FROM ad_campaign_daily_reports 
                       WHERE {channel_condition} AND {time_condition} 
                       GROUP BY campaign_type, campaign_name 
                       ORDER BY cvr ASC""",
    
    "gmv_analysis": """SELECT campaign_type, campaign_name, 
                       SUM(gmv) AS total_gmv, SUM(orders) AS total_orders,
                       SUM(spend) AS total_spend 
                       FROM ad_campaign_daily_reports 
                       WHERE {channel_condition} AND {time_condition} 
                       GROUP BY campaign_type, campaign_name 
                       ORDER BY total_gmv DESC""",
    
    "order_analysis": """SELECT campaign_type, campaign_name, 
                         SUM(orders) AS total_orders, SUM(gmv) AS total_gmv,
                         SUM(spend) AS total_spend, SUM(gmv)/MAX(SUM(spend),1) AS roi
                         FROM ad_campaign_daily_reports 
                         WHERE {channel_condition} AND {time_condition} 
                         GROUP BY campaign_type, campaign_name 
                         ORDER BY total_orders DESC""",
    
    "channel_analysis": """SELECT campaign_name, SUM(spend) AS spend, 
                           SUM(impressions) AS impressions, SUM(clicks) AS clicks, 
                           SUM(orders) AS orders, SUM(gmv) AS gmv,
                           SUM(gmv)/MAX(SUM(spend),1) AS roi, 
                           SUM(clicks)*100.0/MAX(SUM(impressions),1) AS ctr
                           FROM ad_campaign_daily_reports 
                           WHERE {channel_condition} AND {time_condition} 
                           GROUP BY campaign_name""",
    
    "daily_report": """SELECT campaign_type, SUM(spend) AS total_spend, 
                       SUM(impressions) AS total_impressions, SUM(clicks) AS total_clicks,
                       SUM(orders) AS total_orders, SUM(gmv) AS total_gmv,
                       SUM(gmv)/MAX(SUM(spend),1) AS avg_roi,
                       SUM(clicks)*100.0/MAX(SUM(impressions),1) AS avg_ctr
                       FROM ad_campaign_daily_reports 
                       WHERE {time_condition} 
                       GROUP BY campaign_type"""
}

def _detect_intent(user_question: str, api_key: str) -> str:
    """
    第一阶段：意图识别 - 让模型分析用户问题，识别业务意图
    
    Args:
        user_question: 用户问题
        api_key: API Key
    
    Returns:
        识别出的意图ID（如 "funnel_analysis"），如果无法识别则返回 ""
    """
    # 首先尝试基于规则的意图识别
    rule_intent = _rule_based_intent_detection(user_question)
    if rule_intent:
        print(f"[意图识别] 规则匹配成功: {INTENT_DEFINITIONS[rule_intent]['name']}")
        return rule_intent
    
    # 如果规则无法匹配，调用模型进行意图识别
    print(f"[意图识别] 规则匹配失败，调用模型分析意图")
    
    system_prompt = f"""
你是一个电商数据分析专家，你的任务是分析用户的业务问题，识别其意图。

【意图定义】
{json.dumps(INTENT_DEFINITIONS, ensure_ascii=False, indent=2)}

【输出格式】
只输出意图ID，不要输出任何其他内容。

【示例】
用户问：分析引力魔方最近3天的漏斗流失情况
输出：funnel_analysis

用户问：查询各渠道的ROI
输出：roi_analysis

用户问：检查异常数据
输出：abnormal_detection
"""
    
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ],
        "temperature": 0.01,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        intent_id = result["choices"][0]["message"]["content"].strip()
        
        # 验证意图ID是否有效
        if intent_id in INTENT_DEFINITIONS:
            print(f"[意图识别] 模型识别成功: {INTENT_DEFINITIONS[intent_id]['name']}")
            return intent_id
        else:
            print(f"[意图识别] 模型返回无效意图: {intent_id}")
            return ""
            
    except Exception as e:
        print(f"[意图识别] 模型调用失败: {str(e)}")
        return ""

def _rule_based_intent_detection(user_question: str) -> str:
    """
    基于规则的意图识别（快速路径）
    
    Args:
        user_question: 用户问题
    
    Returns:
        意图ID或空字符串
    """
    if not user_question:
        return ""
    
    question = user_question.lower()
    
    # 按优先级匹配意图
    intent_order = ['funnel_analysis', 'abnormal_detection', 'roi_analysis', 
                   'ctr_analysis', 'cvr_analysis', 'gmv_analysis', 
                   'order_analysis', 'spend_analysis', 'channel_analysis']
    
    for intent_id in intent_order:
        intent = INTENT_DEFINITIONS[intent_id]
        if any(pattern.lower() in question for pattern in intent['patterns']):
            return intent_id
    
    return ""

def _extract_parameters(user_question: str) -> dict:
    """
    从用户问题中提取参数（渠道、时间范围）
    
    Args:
        user_question: 用户问题
    
    Returns:
        参数字典
    """
    params = {
        'channel': None,
        'time_range': '最近7天'
    }
    
    # 提取渠道
    channels = ['引力魔方', '直通车', '万相台']
    for channel in channels:
        if channel in user_question:
            params['channel'] = channel
            break
    
    # 提取时间范围
    for time_key in TIME_MAPPING:
        if time_key in user_question:
            params['time_range'] = time_key
            break
    
    return params

def _generate_sql_from_intent(intent_id: str, params: dict) -> str:
    """
    根据意图和参数生成SQL查询
    
    Args:
        intent_id: 意图ID
        params: 参数字典
    
    Returns:
        SQL查询语句
    """
    # 获取模板
    template = INTENT_SQL_TEMPLATES.get(intent_id)
    if not template:
        return _get_default_sql()
    
    # 构建条件
    channel_condition = '1=1'
    if params['channel']:
        channel_condition = f"campaign_type = '{params['channel']}'"
    
    time_condition = TIME_MAPPING.get(params['time_range'], TIME_MAPPING['最近7天'])
    
    # 生成SQL
    sql = template.format(
        channel_condition=channel_condition,
        time_condition=time_condition
    )
    
    return sql

def text_to_sql(user_question: str, api_key: str) -> str:
    """
    将用户的自然语言问题转化为 SQLite 查询语句
    
    两阶段处理：
    1. 意图识别：分析用户问题，确定业务意图
    2. SQL 生成：根据意图和参数生成 SQL
    
    Args:
        user_question: 用户的自然语言问题
        api_key: 硅基流动 API Key（由调用方传入）
    
    Returns:
        生成的 SQL 查询语句
    """
    # 检查 API Key 是否有效
    if not api_key:
        print("[错误] API Key 未提供")
        return ""
    
    print(f"\n=== 开始处理用户问题 ===")
    print(f"用户问：{user_question}")
    
    # 业务边界检查
    if not is_business_related(user_question):
        print("[警告] 用户问题与业务无关")
        return "BUSINESS_BOUNDARY"  # 返回特殊标记表示业务边界
    
    # 第一阶段：意图识别
    intent_id = _detect_intent(user_question, api_key)
    
    # 如果意图识别失败，使用默认查询
    if not intent_id:
        print("[警告] 意图识别失败，使用默认查询")
        return _get_default_sql()
    
    # 第二阶段：提取参数
    params = _extract_parameters(user_question)
    print(f"[参数提取] 渠道: {params['channel']}, 时间范围: {params['time_range']}")
    
    # 第三阶段：生成SQL
    sql = _generate_sql_from_intent(intent_id, params)
    print(f"[SQL生成] {sql[:100]}...")
    
    return sql

def _get_default_sql() -> str:
    """返回默认的安全查询"""
    return """SELECT campaign_type, campaign_name, SUM(spend) AS spend, SUM(impressions) AS impressions, 
              SUM(clicks) AS clicks, SUM(orders) AS orders, SUM(gmv) AS gmv, 
              SUM(gmv)/MAX(SUM(spend),1) AS roi, SUM(clicks)*100.0/MAX(SUM(impressions),1) AS ctr 
              FROM ad_campaign_daily_reports 
              WHERE date >= DATE('now', '-7 days') 
              GROUP BY campaign_type, campaign_name"""

def execute_sql(sql: str) -> list:
    """
    执行 SQL 查询并返回结果
    
    Args:
        sql: SQL 查询语句
    
    Returns:
        查询结果列表，每行为一个字典
    """
    try:
        conn = sqlite3.connect('ecommerce_ads.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        conn.close()
        return result
    except Exception as e:
        print(f"SQL 执行失败: {str(e)}")
        return []

if __name__ == "__main__":
    """测试用例"""
    API_KEY = "your_api_key_here"
    
    test_questions = [
        "分析引力魔方最近3天的漏斗流失情况",
        "查询各渠道的ROI",
        "查看直通车最近7天的花费",
        "检查异常数据",
        "分析最近一周的GMV"
    ]
    
    for question in test_questions:
        print(f"\n=== 测试: {question} ===")
        sql = text_to_sql(question, API_KEY)
        print(f"生成的SQL:\n{sql}")
        results = execute_sql(sql)
        print(f"查询结果数: {len(results)}")
