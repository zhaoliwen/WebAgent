# -*- coding: utf-8 -*-
"""
元素分类器模块

将浏览器DOM元素按语义进行分类，并计算置信度分数。
用于帮助 LLM 更好地理解和选择页面元素。
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ElementCategory(Enum):
    """元素分类枚举"""
    DATE = "DATE"           # 日期相关元素
    INPUT = "INPUT"         # 输入框
    BUTTON = "BUTTON"       # 按钮
    LINK = "LINK"           # 链接
    SELECT = "SELECT"       # 下拉框
    CHECKBOX = "CHECKBOX"   # 复选框/单选框
    TAB = "TAB"             # 标签页/导航
    ICON = "ICON"           # 图标
    IMAGE = "IMAGE"         # 图片
    TEXT = "TEXT"           # 纯文本元素
    MODAL = "MODAL"         # 弹窗相关
    CALENDAR = "CALENDAR"   # 日历相关
    NAVIGATION = "NAVIGATION"  # 导航相关
    OTHER = "OTHER"         # 其他


@dataclass
class ClassifiedElement:
    """分类后的元素"""
    index: int                      # 原始索引
    tag_name: str                   # HTML标签名
    text: str                       # 元素文本
    category: ElementCategory       # 分类
    confidence: int                 # 置信度 0-100
    attributes: Dict[str, str] = field(default_factory=dict)  # 元素属性
    original_line: str = ""         # 原始行内容
    sub_category: str = ""          # 子分类（如日期的具体日期值）


class ElementClassifier:
    """元素分类器"""

    # 日期相关的关键词和模式
    DATE_PATTERNS = [
        r'\d{1,2}月\d{1,2}日',      # 1月30日
        r'\d{4}-\d{2}-\d{2}',        # 2026-01-30
        r'\d{4}/\d{2}/\d{2}',        # 2026/01/30
        r'\d{1,2}/\d{1,2}',          # 1/30
        r'^\d{1,2}$',                # 单独的日期数字 1-31
        r'周[一二三四五六日]',        # 周一
        r'星期[一二三四五六日]',      # 星期一
        r'今天|明天|后天|昨天',       # 相对日期
    ]

    DATE_KEYWORDS = [
        '日期', '出发', '返程', '入住', '离店', '预订',
        '选择日期', '出发日期', '返回日期', '出行日期',
        'date', 'departure', 'arrival', 'checkin', 'checkout',
    ]

    DATE_CLASSES = [
        'date', 'calendar', 'datepicker', 'day', 'month', 'year',
        'picker', 'cal-', '-cal', 'dt-', '-dt',
    ]

    # 按钮相关
    BUTTON_KEYWORDS = [
        '搜索', '查询', '提交', '确定', '取消', '登录', '注册', '购买',
        '预订', '下单', '支付', '确认', '同意', '开始', '继续',
        'search', 'submit', 'confirm', 'cancel', 'login', 'register',
        'buy', 'book', 'pay', 'ok', 'yes', 'no', 'start', 'continue',
    ]

    # 输入框相关
    INPUT_KEYWORDS = [
        '请输入', '输入', '填写', '搜索', '用户名', '密码', '手机号',
        '邮箱', '姓名', '地址', '出发地', '目的地', '到达',
        'enter', 'input', 'type', 'search', 'username', 'password',
        'email', 'phone', 'name', 'address', 'from', 'to',
    ]

    # 导航相关
    NAV_KEYWORDS = [
        '首页', '机票', '酒店', '火车票', '汽车票', '旅游', '攻略',
        '我的', '订单', '会员', '客服', '帮助', '设置',
        'home', 'flight', 'hotel', 'train', 'travel', 'order', 'member',
    ]

    # 标签页相关
    TAB_KEYWORDS = [
        '单程', '往返', '多程', '国内', '国际', '经济舱', '商务舱',
        '头等舱', '直飞', '中转',
    ]

    def __init__(self):
        # 编译正则表达式以提高性能
        self.date_patterns = [re.compile(p, re.IGNORECASE) for p in self.DATE_PATTERNS]

    def classify_element(
        self,
        index: int,
        tag_name: str,
        text: str,
        attributes: Optional[Dict[str, str]] = None,
        original_line: str = ""
    ) -> ClassifiedElement:
        """
        分类单个元素

        Args:
            index: 元素索引
            tag_name: HTML标签名
            text: 元素文本
            attributes: 元素属性
            original_line: 原始行内容

        Returns:
            ClassifiedElement: 分类后的元素
        """
        attributes = attributes or {}
        text_lower = text.lower()
        tag_lower = tag_name.lower()

        # 获取class和其他属性
        class_attr = attributes.get('class', '').lower()
        id_attr = attributes.get('id', '').lower()
        role_attr = attributes.get('role', '').lower()
        type_attr = attributes.get('type', '').lower()

        # 综合属性字符串用于匹配
        all_attrs = f"{class_attr} {id_attr} {role_attr} {type_attr}"

        # 初始化分类结果
        category = ElementCategory.OTHER
        confidence = 50
        sub_category = ""

        # 1. 首先根据标签名分类
        category, confidence = self._classify_by_tag(tag_lower, type_attr)

        # 2. 然后根据文本内容细化分类
        text_category, text_confidence, sub_cat = self._classify_by_text(text, text_lower)
        if text_confidence > confidence:
            category = text_category
            confidence = text_confidence
            sub_category = sub_cat

        # 3. 根据class/id属性进一步细化
        attr_category, attr_confidence = self._classify_by_attributes(all_attrs)
        if attr_confidence > confidence:
            category = attr_category
            confidence = attr_confidence

        # 4. 特殊情况处理：日历中的日期数字
        if self._is_calendar_date(text, tag_lower, all_attrs):
            category = ElementCategory.CALENDAR
            confidence = 95
            sub_category = f"日期:{text.strip()}"

        # 5. 确保置信度在0-100范围内
        confidence = max(0, min(100, confidence))

        return ClassifiedElement(
            index=index,
            tag_name=tag_name,
            text=text,
            category=category,
            confidence=confidence,
            attributes=attributes,
            original_line=original_line,
            sub_category=sub_category
        )

    def _classify_by_tag(self, tag_lower: str, type_attr: str) -> Tuple[ElementCategory, int]:
        """根据HTML标签分类"""
        # 输入框
        if tag_lower == 'input':
            if type_attr == 'checkbox':
                return ElementCategory.CHECKBOX, 90
            elif type_attr == 'radio':
                return ElementCategory.CHECKBOX, 90
            elif type_attr == 'submit':
                return ElementCategory.BUTTON, 85
            elif type_attr == 'button':
                return ElementCategory.BUTTON, 85
            elif type_attr == 'date':
                return ElementCategory.DATE, 95
            else:
                return ElementCategory.INPUT, 80

        # 按钮
        if tag_lower == 'button':
            return ElementCategory.BUTTON, 85

        # 链接
        if tag_lower == 'a':
            return ElementCategory.LINK, 75

        # 下拉框
        if tag_lower == 'select':
            return ElementCategory.SELECT, 90

        # 图片
        if tag_lower == 'img':
            return ElementCategory.IMAGE, 80

        # 文本区域
        if tag_lower == 'textarea':
            return ElementCategory.INPUT, 85

        # div/span 等通用标签，置信度较低
        if tag_lower in ['div', 'span', 'li', 'td', 'th']:
            return ElementCategory.OTHER, 40

        return ElementCategory.OTHER, 50

    def _classify_by_text(self, text: str, text_lower: str) -> Tuple[ElementCategory, int, str]:
        """根据文本内容分类"""
        # 检查日期模式
        for pattern in self.date_patterns:
            match = pattern.search(text)
            if match:
                return ElementCategory.DATE, 90, f"日期:{match.group()}"

        # 检查日期关键词
        for keyword in self.DATE_KEYWORDS:
            if keyword in text_lower:
                return ElementCategory.DATE, 75, ""

        # 检查按钮关键词
        for keyword in self.BUTTON_KEYWORDS:
            if keyword in text_lower:
                return ElementCategory.BUTTON, 80, ""

        # 检查输入框关键词
        for keyword in self.INPUT_KEYWORDS:
            if keyword in text_lower:
                return ElementCategory.INPUT, 70, ""

        # 检查导航关键词
        for keyword in self.NAV_KEYWORDS:
            if keyword in text_lower:
                return ElementCategory.NAVIGATION, 75, ""

        # 检查标签页关键词
        for keyword in self.TAB_KEYWORDS:
            if keyword in text_lower:
                return ElementCategory.TAB, 75, ""

        return ElementCategory.OTHER, 50, ""

    def _classify_by_attributes(self, all_attrs: str) -> Tuple[ElementCategory, int]:
        """根据属性分类"""
        # 检查日期相关class
        for date_class in self.DATE_CLASSES:
            if date_class in all_attrs:
                return ElementCategory.CALENDAR, 85

        # 检查弹窗相关
        if any(kw in all_attrs for kw in ['modal', 'popup', 'dialog', 'overlay', 'dropdown']):
            return ElementCategory.MODAL, 70

        # 检查导航相关
        if any(kw in all_attrs for kw in ['nav', 'menu', 'header', 'footer', 'sidebar']):
            return ElementCategory.NAVIGATION, 70

        # 检查按钮相关
        if any(kw in all_attrs for kw in ['btn', 'button', 'submit', 'action']):
            return ElementCategory.BUTTON, 75

        # 检查输入相关
        if any(kw in all_attrs for kw in ['input', 'field', 'form', 'search']):
            return ElementCategory.INPUT, 70

        return ElementCategory.OTHER, 50

    def _is_calendar_date(self, text: str, tag_lower: str, all_attrs: str) -> bool:
        """判断是否是日历中的日期格子"""
        text_stripped = text.strip()

        # 检查是否是1-31的数字
        if text_stripped.isdigit():
            num = int(text_stripped)
            if 1 <= num <= 31:
                # 额外检查是否有日历相关的class
                if any(kw in all_attrs for kw in ['day', 'date', 'cal', 'cell', 'td']):
                    return True
                # 如果在td/div/span中且是纯数字，很可能是日期
                if tag_lower in ['td', 'div', 'span', 'li', 'a', 'button']:
                    return True

        return False

    def parse_element_line(self, line: str) -> Optional[ClassifiedElement]:
        """
        解析单行元素字符串

        browser-use 库的格式: [index]<tag_name text/>
        或带属性格式: [index]<tag_name attr1;attr2>text/>
        例如: [33]<button>提交表单/>
              [33]<button class1;class2>提交表单/>
        """
        line = line.strip()
        if not line.startswith('['):
            return None

        # 尝试多种匹配模式
        # 模式1: [index]<tag_name attr>text/>
        match = re.match(r'\[(\d+)\]<(\w+)\s*([^>]*)>(.*)/?>', line)
        if match:
            index = int(match.group(1))
            tag_name = match.group(2)
            attrs_str = match.group(3).strip()
            text = match.group(4).strip()
            if text.endswith('/'):
                text = text[:-1].strip()
        else:
            # 模式2: [index]<tag_name>text/> (无属性)
            match = re.match(r'\[(\d+)\]<(\w+)>(.*)/?>', line)
            if match:
                index = int(match.group(1))
                tag_name = match.group(2)
                attrs_str = ""
                text = match.group(3).strip()
                if text.endswith('/'):
                    text = text[:-1].strip()
            else:
                # 模式3: [index]<tag_name text/> (text中没有>分隔)
                match = re.match(r'\[(\d+)\]<(\w+)\s+(.*)/?>', line)
                if match:
                    index = int(match.group(1))
                    tag_name = match.group(2)
                    attrs_str = ""
                    text = match.group(3).strip()
                    if text.endswith('/>'):
                        text = text[:-2].strip()
                    elif text.endswith('/'):
                        text = text[:-1].strip()
                else:
                    return None

        # 解析属性（简化处理，主要从class/id提取）
        attributes = {}
        if attrs_str:
            # browser-use 使用分号分隔属性
            # 尝试提取class属性
            class_match = re.search(r'class="([^"]*)"', attrs_str)
            if class_match:
                attributes['class'] = class_match.group(1)
            # 尝试提取id属性
            id_match = re.search(r'id="([^"]*)"', attrs_str)
            if id_match:
                attributes['id'] = id_match.group(1)
            # 将分号分隔的属性值也加入class
            if ';' in attrs_str:
                attributes['class'] = attrs_str

        return self.classify_element(
            index=index,
            tag_name=tag_name,
            text=text,
            attributes=attributes,
            original_line=line
        )

    def classify_elements_string(self, elements_str: str) -> Tuple[str, Dict[ElementCategory, List[ClassifiedElement]]]:
        """
        分类元素字符串并生成增强的输出

        Args:
            elements_str: browser-use 返回的元素字符串

        Returns:
            Tuple[str, Dict]: (格式化的分类元素字符串, 分类后的元素字典)
        """
        if not elements_str:
            return "", {}

        lines = elements_str.strip().split('\n')
        classified_elements: Dict[ElementCategory, List[ClassifiedElement]] = {
            cat: [] for cat in ElementCategory
        }

        # 解析和分类每个元素
        for line in lines:
            if not line.strip() or not line.strip().startswith('['):
                continue

            element = self.parse_element_line(line)
            if element:
                classified_elements[element.category].append(element)

        # 生成格式化输出
        output_lines = []

        # 按优先级排序的分类列表
        priority_order = [
            ElementCategory.DATE,
            ElementCategory.CALENDAR,
            ElementCategory.INPUT,
            ElementCategory.BUTTON,
            ElementCategory.SELECT,
            ElementCategory.TAB,
            ElementCategory.LINK,
            ElementCategory.NAVIGATION,
            ElementCategory.CHECKBOX,
            ElementCategory.MODAL,
            ElementCategory.IMAGE,
            ElementCategory.ICON,
            ElementCategory.TEXT,
            ElementCategory.OTHER,
        ]

        for category in priority_order:
            elements = classified_elements[category]
            if not elements:
                continue

            # 按置信度排序
            elements.sort(key=lambda x: x.confidence, reverse=True)

            # 输出分类标题
            category_name = self._get_category_display_name(category)
            output_lines.append(f"\n=== {category_name} ({len(elements)}个元素) ===")

            for elem in elements:
                # 格式: [index]<tag> text (置信度:XX) [子分类]
                line = f"[{elem.index}]<{elem.tag_name}>{elem.text}/> (置信度:{elem.confidence})"
                if elem.sub_category:
                    line += f" [{elem.sub_category}]"
                output_lines.append(line)

        return '\n'.join(output_lines), classified_elements

    def _get_category_display_name(self, category: ElementCategory) -> str:
        """获取分类的显示名称"""
        names = {
            ElementCategory.DATE: "日期相关",
            ElementCategory.CALENDAR: "日历日期",
            ElementCategory.INPUT: "输入框",
            ElementCategory.BUTTON: "按钮",
            ElementCategory.SELECT: "下拉框",
            ElementCategory.CHECKBOX: "复选/单选",
            ElementCategory.TAB: "标签页",
            ElementCategory.LINK: "链接",
            ElementCategory.NAVIGATION: "导航",
            ElementCategory.MODAL: "弹窗",
            ElementCategory.IMAGE: "图片",
            ElementCategory.ICON: "图标",
            ElementCategory.TEXT: "文本",
            ElementCategory.OTHER: "其他",
        }
        return names.get(category, category.value)

    def get_elements_by_category(
        self,
        elements_str: str,
        category: ElementCategory
    ) -> List[ClassifiedElement]:
        """
        获取指定分类的所有元素

        Args:
            elements_str: 元素字符串
            category: 目标分类

        Returns:
            List[ClassifiedElement]: 该分类的所有元素
        """
        _, classified = self.classify_elements_string(elements_str)
        return classified.get(category, [])

    def find_date_elements(self, elements_str: str, target_date: str = None) -> List[ClassifiedElement]:
        """
        查找所有日期相关的元素

        Args:
            elements_str: 元素字符串
            target_date: 目标日期字符串（可选，用于精确匹配）

        Returns:
            List[ClassifiedElement]: 日期相关的元素列表
        """
        _, classified = self.classify_elements_string(elements_str)

        # 合并 DATE 和 CALENDAR 分类
        date_elements = classified.get(ElementCategory.DATE, [])
        calendar_elements = classified.get(ElementCategory.CALENDAR, [])
        all_date_elements = date_elements + calendar_elements

        if target_date:
            # 精确匹配目标日期
            matched = []
            for elem in all_date_elements:
                if target_date in elem.text or target_date in elem.sub_category:
                    matched.append(elem)
            return matched

        return all_date_elements


# 便捷函数
def classify_browser_elements(elements_str: str) -> str:
    """
    分类浏览器元素并返回格式化的字符串

    这是一个便捷函数，可以直接在其他模块中使用。
    """
    classifier = ElementClassifier()
    formatted_str, _ = classifier.classify_elements_string(elements_str)
    return formatted_str


def find_calendar_dates(elements_str: str) -> List[ClassifiedElement]:
    """
    查找所有日历日期元素

    便捷函数，用于快速定位日历中的日期。
    """
    classifier = ElementClassifier()
    return classifier.get_elements_by_category(elements_str, ElementCategory.CALENDAR)

