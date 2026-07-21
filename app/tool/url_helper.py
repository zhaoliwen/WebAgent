# -*- coding: utf-8 -*-
"""
URL 帮助工具模块

用于帮助处理复杂网站的 URL 参数，特别是日期选择等交互式组件。
通过 URL 参数直接跳转可以绕过日历选择器等复杂 JavaScript 交互。
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs


@dataclass
class FlightSearchParams:
    """机票搜索参数"""
    departure_city: str        # 出发城市代码
    arrival_city: str          # 到达城市代码
    departure_date: str        # 出发日期 YYYY-MM-DD
    return_date: Optional[str] = None  # 返程日期（往返时使用）
    cabin: str = "y"           # 舱位: y=经济舱, c=商务舱, f=头等舱
    adult: int = 1             # 成人数量
    child: int = 0             # 儿童数量
    infant: int = 0            # 婴儿数量


class URLHelper:
    """URL 帮助工具类"""

    # 城市代码映射
    CITY_CODES = {
        # 国内主要城市
        "上海": "sha",
        "北京": "pek",
        "广州": "can",
        "深圳": "szx",
        "成都": "ctu",
        "杭州": "hgh",
        "南京": "nkg",
        "武汉": "wuh",
        "西安": "sia",
        "重庆": "ckg",
        "青岛": "tao",
        "大连": "dlc",
        "厦门": "xmn",
        "昆明": "kmg",
        "长沙": "csx",
        "郑州": "cgo",
        "天津": "tsn",
        "沈阳": "she",
        "哈尔滨": "hrb",
        "三亚": "syx",
        "海口": "hak",
        "福州": "foc",
        "济南": "tna",
        "太原": "tyn",
        "贵阳": "kwe",
        "南宁": "nng",
        "合肥": "hfe",
        "无锡": "wux",
        "宁波": "ngb",
        "温州": "wnz",

        # 国际主要城市
        "香港": "hkg",
        "澳门": "mfm",
        "台北": "tpe",
        "东京": "tyo",
        "大阪": "osa",
        "首尔": "sel",
        "新加坡": "sin",
        "曼谷": "bkk",
        "吉隆坡": "kul",
        "伦敦": "lon",
        "巴黎": "par",
        "纽约": "nyc",
        "洛杉矶": "lax",
        "悉尼": "syd",
        "墨尔本": "mel",
    }

    # 日期关键词解析
    DATE_KEYWORDS = {
        "今天": 0,
        "明天": 1,
        "后天": 2,
        "大后天": 3,
    }

    def __init__(self):
        pass

    def parse_date(self, date_str: str) -> Optional[str]:
        """
        解析日期字符串，返回 YYYY-MM-DD 格式

        支持格式:
        - 1月30日 / 1月30号
        - 2026-01-30
        - 2026/01/30
        - 01-30 / 01/30
        - 今天/明天/后天
        """
        date_str = date_str.strip()
        today = datetime.now()

        # 检查相对日期关键词
        for keyword, days in self.DATE_KEYWORDS.items():
            if keyword in date_str:
                target_date = today + timedelta(days=days)
                return target_date.strftime("%Y-%m-%d")

        # 检查 X月X日 格式
        match = re.search(r'(\d{1,2})月(\d{1,2})[日号]?', date_str)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            # 如果没有年份，假设是今年或明年
            year = today.year
            target_date = datetime(year, month, day)
            # 如果日期已过，使用明年
            if target_date < today:
                year += 1
                target_date = datetime(year, month, day)
            return target_date.strftime("%Y-%m-%d")

        # 检查 YYYY-MM-DD 或 YYYY/MM/DD 格式
        match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
        if match:
            return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"

        # 检查 MM-DD 或 MM/DD 格式
        match = re.search(r'(\d{1,2})[-/](\d{1,2})', date_str)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            year = today.year
            target_date = datetime(year, month, day)
            if target_date < today:
                year += 1
            return f"{year}-{month:02d}-{day:02d}"

        return None

    def get_city_code(self, city_name: str) -> Optional[str]:
        """获取城市的机场代码"""
        # 先尝试直接匹配
        if city_name in self.CITY_CODES:
            return self.CITY_CODES[city_name]

        # 尝试部分匹配
        for name, code in self.CITY_CODES.items():
            if name in city_name or city_name in name:
                return code

        # 检查是否已经是代码格式（3个字母）
        if len(city_name) == 3 and city_name.isalpha():
            return city_name.lower()

        return None

    def build_ctrip_flight_url(self, params: FlightSearchParams) -> str:
        """
        构建携程机票搜索 URL

        示例:
        单程: https://flights.ctrip.com/online/list/oneway-sha-pek?depdate=2026-01-30&cabin=y&adult=1&child=0&infant=0
        往返: https://flights.ctrip.com/online/list/round-sha-pek?depdate=2026-01-30&rdate=2026-02-10&cabin=y&adult=1&child=0&infant=0
        """
        base_url = "https://flights.ctrip.com/online/list"

        dep_code = self.get_city_code(params.departure_city) or params.departure_city.lower()
        arr_code = self.get_city_code(params.arrival_city) or params.arrival_city.lower()

        if params.return_date:
            # 往返
            route = f"round-{dep_code}-{arr_code}"
            query_params = {
                "depdate": params.departure_date,
                "rdate": params.return_date,
                "cabin": params.cabin,
                "adult": params.adult,
                "child": params.child,
                "infant": params.infant,
            }
        else:
            # 单程
            route = f"oneway-{dep_code}-{arr_code}"
            query_params = {
                "depdate": params.departure_date,
                "cabin": params.cabin,
                "adult": params.adult,
                "child": params.child,
                "infant": params.infant,
            }

        url = f"{base_url}/{route}?{urlencode(query_params)}"
        return url

    def parse_flight_query(self, query: str) -> Optional[FlightSearchParams]:
        """
        从自然语言查询中解析机票搜索参数

        示例查询:
        - 1月30日从上海到北京的机票
        - 用携程查询 1月30日 从上海到北京的机票
        - 明天从北京到上海的机票
        """
        # 提取日期
        date = self.parse_date(query)
        if not date:
            return None

        # 提取出发城市和目的城市
        # 模式: 从X到Y
        match = re.search(r'从([^\s到]+)到([^\s的]+)', query)
        if not match:
            # 模式: X到Y
            match = re.search(r'([^\s从到]+)到([^\s的]+)', query)

        if not match:
            return None

        dep_city = match.group(1).strip()
        arr_city = match.group(2).strip()

        # 获取城市代码
        dep_code = self.get_city_code(dep_city)
        arr_code = self.get_city_code(arr_city)

        if not dep_code or not arr_code:
            return None

        return FlightSearchParams(
            departure_city=dep_city,
            arrival_city=arr_city,
            departure_date=date,
        )


def build_ctrip_flight_url_from_query(query: str) -> Optional[str]:
    """
    便捷函数：从自然语言查询构建携程机票 URL

    Args:
        query: 自然语言查询，如 "1月30日从上海到北京的机票"

    Returns:
        携程机票搜索 URL 或 None
    """
    helper = URLHelper()
    params = helper.parse_flight_query(query)
    if params:
        return helper.build_ctrip_flight_url(params)
    return None


# 测试代码
if __name__ == "__main__":
    helper = URLHelper()

    # 测试日期解析
    test_dates = [
        "1月30日",
        "2月14号",
        "2026-01-30",
        "01/30",
        "明天",
        "后天",
    ]
    print("=== 日期解析测试 ===")
    for date_str in test_dates:
        result = helper.parse_date(date_str)
        print(f"  {date_str} -> {result}")

    # 测试查询解析
    test_queries = [
        "用携程查询 1月30日 从上海到北京的机票",
        "明天从北京到广州的机票",
        "1月30日从上海到北京的机票",
    ]
    print("\n=== 查询解析测试 ===")
    for query in test_queries:
        params = helper.parse_flight_query(query)
        if params:
            url = helper.build_ctrip_flight_url(params)
            print(f"  查询: {query}")
            print(f"  URL: {url}")
            print()

