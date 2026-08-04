"""生成 AI Shop Analyzer 产品设计文档 PDF（上线用）。"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    ListFlowable, ListItem, KeepTogether, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# 注册中文字体
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AI店铺分析器-产品设计文档.pdf")

# ==================== 样式定义 ====================
PRIMARY = colors.HexColor("#2563EB")
DARK = colors.HexColor("#1E293B")
GRAY = colors.HexColor("#64748B")
LIGHT_GRAY = colors.HexColor("#F1F5F9")
ACCENT = colors.HexColor("#10B981")
WARN = colors.HexColor("#F59E0B")

styles = getSampleStyleSheet()

style_title = ParagraphStyle(
    "Title", parent=styles["Title"], fontName="STSong-Light",
    fontSize=26, leading=34, textColor=PRIMARY, alignment=TA_CENTER,
    spaceAfter=10,
)
style_subtitle = ParagraphStyle(
    "Subtitle", parent=styles["Normal"], fontName="STSong-Light",
    fontSize=14, leading=20, textColor=GRAY, alignment=TA_CENTER,
    spaceAfter=6,
)
style_h1 = ParagraphStyle(
    "H1", parent=styles["Heading1"], fontName="STSong-Light",
    fontSize=18, leading=26, textColor=PRIMARY,
    spaceBefore=18, spaceAfter=10,
)
style_h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"], fontName="STSong-Light",
    fontSize=14, leading=20, textColor=DARK,
    spaceBefore=14, spaceAfter=8,
)
style_h3 = ParagraphStyle(
    "H3", parent=styles["Heading3"], fontName="STSong-Light",
    fontSize=12, leading=17, textColor=DARK,
    spaceBefore=10, spaceAfter=6,
)
style_body = ParagraphStyle(
    "Body", parent=styles["Normal"], fontName="STSong-Light",
    fontSize=10.5, leading=16, textColor=DARK, alignment=TA_JUSTIFY,
    spaceAfter=6,
)
style_bullet = ParagraphStyle(
    "Bullet", parent=style_body, leftIndent=18, spaceAfter=3,
)
style_table_header = ParagraphStyle(
    "TableHeader", fontName="STSong-Light", fontSize=10, leading=14,
    textColor=colors.white, alignment=TA_CENTER,
)
style_table_cell = ParagraphStyle(
    "TableCell", fontName="STSong-Light", fontSize=9.5, leading=13,
    textColor=DARK, alignment=TA_LEFT,
)
style_caption = ParagraphStyle(
    "Caption", parent=styles["Normal"], fontName="STSong-Light",
    fontSize=9, leading=12, textColor=GRAY, alignment=TA_CENTER,
    spaceAfter=10,
)
style_footer = ParagraphStyle(
    "Footer", fontName="STSong-Light", fontSize=8, leading=11,
    textColor=GRAY, alignment=TA_CENTER,
)


def make_table(data, col_widths=None, header_bg=PRIMARY):
    """构造统一样式的表格。"""
    # 把字符串单元格转成 Paragraph 以支持换行
    rows = []
    for i, row in enumerate(data):
        new_row = []
        for cell in row:
            if isinstance(cell, str):
                style = style_table_header if i == 0 else style_table_cell
                new_row.append(Paragraph(cell, style))
            else:
                new_row.append(cell)
        rows.append(new_row)
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def bullets(items, style=style_bullet):
    return ListFlowable(
        [ListItem(Paragraph(t, style), leftIndent=12, value="•") for t in items],
        bulletType="bullet", start="•", leftIndent=18,
    )


# ==================== 页眉页脚 ====================
def add_page_decoration(canvas, doc):
    canvas.saveState()
    page_num = canvas.getPageNumber()
    width, height = A4
    # 页脚分割线
    canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.5 * cm, width - 2 * cm, 1.5 * cm)
    # 页脚文字
    canvas.setFont("STSong-Light", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(2 * cm, 1.1 * cm, "AI 店铺分析器 · 产品设计文档")
    canvas.drawRightString(width - 2 * cm, 1.1 * cm, f"第 {page_num} 页")
    # 页眉（非首页）
    if page_num > 1:
        canvas.setFillColor(PRIMARY)
        canvas.rect(0, height - 0.8 * cm, width, 0.8 * cm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("STSong-Light", 8)
        canvas.drawString(2 * cm, height - 0.55 * cm, "AI Shop Analyzer")
        canvas.drawRightString(width - 2 * cm, height - 0.55 * cm, "产品设计文档")
    canvas.restoreState()


# ==================== 文档内容 ====================
story = []

# ---------- 封面 ----------
story.append(Spacer(1, 4 * cm))
story.append(Paragraph("AI 店铺分析器", style_title))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph("AI Shop Analyzer", ParagraphStyle(
    "EnTitle", fontName="Helvetica-Bold", fontSize=16, leading=22,
    textColor=GRAY, alignment=TA_CENTER,
)))
story.append(Spacer(1, 1 * cm))
story.append(HRFlowable(width="40%", thickness=2, color=PRIMARY, hAlign="CENTER"))
story.append(Spacer(1, 1 * cm))
story.append(Paragraph("产品设计文档", ParagraphStyle(
    "DocType", fontName="STSong-Light", fontSize=20, leading=28,
    textColor=DARK, alignment=TA_CENTER,
)))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph("面向 TikTok Shop 商家的智能数据分析与 AI 报告平台", style_subtitle))
story.append(Spacer(1, 6 * cm))

# 封面信息表
cover_info = [
    ["文档版本", "V1.0"],
    ["文档类型", "产品设计文档（上线版）"],
    ["发布日期", datetime.now().strftime("%Y-%m-%d")],
    ["文档状态", "正式发布"],
]
cover_table = Table(cover_info, colWidths=[4 * cm, 8 * cm], hAlign="CENTER")
cover_table.setStyle(TableStyle([
    ("FONT", (0, 0), (-1, -1), "STSong-Light", 11),
    ("TEXTCOLOR", (0, 0), (0, -1), GRAY),
    ("TEXTCOLOR", (1, 0), (1, -1), DARK),
    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
    ("ALIGN", (1, 0), (1, -1), "LEFT"),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
]))
story.append(cover_table)
story.append(PageBreak())

# ---------- 目录 ----------
story.append(Paragraph("目  录", style_h1))
story.append(Spacer(1, 0.3 * cm))
toc_items = [
    "一、产品概述",
    "二、产品定位与目标用户",
    "三、系统架构与技术栈",
    "四、核心功能模块",
    "    4.1 数据概览看板",
    "    4.2 销售数据分析",
    "    4.3 商品分析",
    "    4.4 达人分析",
    "    4.5 流量与营销分析",
    "    4.6 AI 智能分析报告",
    "    4.7 TikTok Shop 数据同步",
    "    4.8 飞书企业集成",
    "    4.9 店铺与用户管理",
    "    4.10 实时分析与监控",
    "五、数据模型与存储",
    "六、API 接口设计",
    "七、安全与权限",
    "八、部署与运维",
    "九、版本规划",
]
story.append(bullets(toc_items, style=ParagraphStyle(
    "TOC", fontName="STSong-Light", fontSize=11, leading=18,
    textColor=DARK, leftIndent=10, spaceAfter=2,
)))
story.append(PageBreak())

# ---------- 一、产品概述 ----------
story.append(Paragraph("一、产品概述", style_h1))
story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("1.1 产品简介", style_h2))
story.append(Paragraph(
    "AI 店铺分析器（AI Shop Analyzer）是一款面向 TikTok Shop 商家的智能数据分析与 AI 报告生成平台。"
    "系统通过对接 TikTok Shop Partner API 自动同步店铺订单与商品数据，结合通义千问大语言模型（qwen-max）"
    "生成深度经营分析报告，帮助商家从销售、商品、达人、流量、营销等多维度洞察经营状况，辅助决策优化。",
    style_body
))

story.append(Paragraph("1.2 核心价值", style_h2))
value_data = [
    ["价值维度", "说明"],
    ["数据自动化", "对接 TikTok Shop 官方 API，一键同步订单/商品数据，无需手动导出 Excel"],
    ["多维分析", "销售、商品、达人、流量、营销五大维度看板，覆盖经营全链路"],
    ["AI 深度洞察", "基于通义千问大模型生成自然语言分析报告，自动识别异常与机会"],
    ["企业协作", "集成飞书多维表格与 Webhook，分析结果自动回写、团队实时协同"],
    ["可视化呈现", "Recharts 动态图表，KPI 卡片 + 趋势折线 + 排行柱状 + 达人散点"],
]
story.append(make_table(value_data, col_widths=[3.5 * cm, 12 * cm]))
story.append(Spacer(1, 0.4 * cm))

story.append(Paragraph("1.3 适用场景", style_h2))
story.append(bullets([
    "TikTok Shop 本地店/跨境店商家日常经营复盘",
    "达人带货效果评估与 ROI 分析",
    "爆品识别与商品结构优化",
    "流量来源诊断与营销策略调整",
    "团队周报/月报自动化生成",
]))

story.append(PageBreak())

# ---------- 二、产品定位与目标用户 ----------
story.append(Paragraph("二、产品定位与目标用户", style_h1))
story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("2.1 产品定位", style_h2))
story.append(Paragraph(
    "面向 TikTok Shop 中小商家的轻量级 SaaS 分析工具，以「数据自动同步 + AI 智能解读 + 飞书协同」为核心差异点，"
    "降低商家的数据分析门槛，让非技术背景的运营人员也能快速获得专业级经营洞察。",
    style_body
))

story.append(Paragraph("2.2 目标用户", style_h2))
user_data = [
    ["用户角色", "典型诉求", "使用频率"],
    ["店铺运营", "每日复盘 GMV/订单/退款，快速发现异常", "每日"],
    ["达人商务", "评估达人带货效果，筛选优质合作对象", "每周"],
    ["商品负责人", "识别爆品/滞销品，优化商品结构", "每周"],
    ["营销投放", "诊断流量来源，调整广告与活动策略", "每日/每周"],
    ["店铺老板", "查看 AI 总结报告，掌握整体经营健康度", "每周/每月"],
    ["数据分析师", "导出明细数据做深度建模与预测", "按需"],
]
story.append(make_table(user_data, col_widths=[3 * cm, 9.5 * cm, 3 * cm]))

story.append(PageBreak())

# ---------- 三、系统架构与技术栈 ----------
story.append(Paragraph("三、系统架构与技术栈", style_h1))
story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("3.1 系统架构", style_h2))
story.append(Paragraph(
    "系统采用前后端分离架构，后端基于 FastAPI 提供 RESTful API，前端基于 Next.js 渲染看板与报告页面。"
    "数据层使用 PostgreSQL（生产）/ SQLite（开发），异步任务通过 Celery + Redis 调度。"
    "外部集成包括 TikTok Shop Partner API（数据源）、通义千问 Dashscope（AI 分析）、飞书开放平台（企业协同）。",
    style_body
))

# 架构分层表
arch_data = [
    ["层次", "组件", "说明"],
    ["前端展示层", "Next.js + Recharts + Tailwind", "看板可视化、报告 H5 页、设置中心"],
    ["API 网关层", "FastAPI + CORS", "统一路由、参数校验、依赖注入"],
    ["业务服务层", "AI 引擎 / 数据预处理 / 报告生成", "调用大模型、聚合计算、Prompt 编排"],
    ["数据适配层", "TikTok / 抖店 / 飞书多维表格适配器", "多平台数据源归一化为 Standard 模型"],
    ["异步任务层", "Celery + Redis", "日报定时任务、长耗时分析"],
    ["数据持久层", "PostgreSQL / SQLite + SQLAlchemy", "StandardOrder/Product/Influencer/Report"],
    ["外部服务", "TikTok Partner API / 通义千问 / 飞书", "数据采集、AI 分析、消息推送"],
]
story.append(make_table(arch_data, col_widths=[3 * cm, 5 * cm, 7.5 * cm]))
story.append(Spacer(1, 0.4 * cm))

story.append(Paragraph("3.2 技术栈明细", style_h2))
tech_data = [
    ["分类", "技术", "用途"],
    ["后端框架", "FastAPI 0.115+", "异步 Web 框架，自动生成 OpenAPI 文档"],
    ["ORM", "SQLAlchemy 2.0", "数据模型定义与查询"],
    ["数据库", "PostgreSQL / SQLite", "生产用 PG，开发用 SQLite 零依赖"],
    ["任务队列", "Celery 5.4 + Redis", "异步任务（日报生成、批量分析）"],
    ["AI 模型", "通义千问 qwen-max（Dashscope）", "自然语言分析报告生成"],
    ["前端框架", "Next.js 14 + React 18", "SSR/CSR 混合渲染"],
    ["图表库", "Recharts", "折线/柱状/散点/饼图"],
    ["样式", "Tailwind CSS", "原子化 CSS，设计系统一致"],
    ["数据源", "TikTok Shop Partner API 202309", "订单/商品/授权管理"],
    ["企业协同", "飞书开放平台（多维表格/Webhook）", "数据回写、消息通知"],
    ["部署", "Render / Docker", "云端部署，支持自动扩缩容"],
]
story.append(make_table(tech_data, col_widths=[2.8 * cm, 4.5 * cm, 8.2 * cm]))

story.append(PageBreak())

# ---------- 四、核心功能模块 ----------
story.append(Paragraph("四、核心功能模块", style_h1))
story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph(
    "系统共包含 10 个核心功能模块，覆盖数据采集、可视化分析、AI 报告、企业协同全流程。",
    style_body
))

# 功能模块总览
module_overview = [
    ["模块", "核心能力", "页面入口"],
    ["数据概览看板", "KPI 卡片 + GMV 趋势 + 商品 TOP10 + 达人散点", "/dashboard"],
    ["销售数据分析", "按时间/店铺筛选，GMV/订单/客单价/退款率环比", "/sales"],
    ["商品分析", "商品销量排行、品类分布、滞销识别", "/products"],
    ["达人分析", "达人带货 GMV、互动率、转化率、异常标记", "/influencers"],
    ["流量与营销", "流量来源占比、营销活动效果、投放 ROI", "/traffic /marketing"],
    ["AI 智能报告", "大模型生成经营分析报告，支持 H5 分享", "/reports"],
    ["TikTok 数据同步", "一键同步订单/商品，Token 自动刷新", "/settings"],
    ["飞书企业集成", "多维表格回写、Webhook 通知、秒搭接入", "后台服务"],
    ["店铺与用户管理", "多店铺切换、权限管理", "/shops /users"],
    ["实时分析监控", "实时订单流、异常告警", "/realtime"],
]
story.append(make_table(module_overview, col_widths=[3 * cm, 7.5 * cm, 5 * cm]))
story.append(Spacer(1, 0.5 * cm))

# 4.1 数据概览看板
story.append(Paragraph("4.1 数据概览看板", style_h2))
story.append(Paragraph(
    "数据概览看板是用户进入系统后的首屏，一屏呈现店铺经营核心指标与趋势，支持近 7/30/90/180 天时间窗口切换与多店铺筛选。",
    style_body
))
story.append(Paragraph("核心指标卡片（KPI）：", style_h3))
story.append(bullets([
    "GMV（成交总额）：当前窗口成交金额，含环比变化百分比",
    "订单数：当前窗口订单总量，含环比",
    "客单价（AOV）：GMV / 订单数，反映客单质量",
    "退款率：退款订单数 / 总订单数，衡量售后健康度",
]))
story.append(Paragraph("可视化图表：", style_h3))
chart_data = [
    ["图表", "类型", "说明"],
    ["GMV 趋势图", "面积图（Area）", "按日聚合 GMV，渐变填充，支持悬停查看明细"],
    ["商品销量 TOP10", "横向柱状图", "按 GMV 降序，底部为第一名"],
    ["达人散点图", "散点图（气泡）", "X=互动率，Y=转化率，气泡大小=GMV，红色标记异常达人"],
    ["流量来源占比", "列表+图例", "For You / Search / Affiliate / Ads / Profile / 其他"],
]
story.append(make_table(chart_data, col_widths=[3.5 * cm, 3.5 * cm, 8.5 * cm]))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph(
    "当所选时间窗口无数据时，系统会提示已同步数据的实际范围，引导用户扩大时间范围查看。",
    style_body
))

story.append(PageBreak())

# 4.2 销售数据分析
story.append(Paragraph("4.2 销售数据分析", style_h2))
story.append(Paragraph(
    "销售数据分析模块提供更细粒度的销售趋势洞察，支持按店铺、时间、状态多维筛选，"
    "帮助运营人员定位销售波动原因。",
    style_body
))
story.append(Paragraph("功能要点：", style_h3))
story.append(bullets([
    "时间维度：近 7/30/90/180 天快速切换，支持自定义起止日期",
    "店铺筛选：多店铺勾选，含「默认店铺」选项（shop_id 为空）",
    "核心指标：GMV、订单数、客单价、退款率，均含环比百分比",
    "趋势对比：当前窗口 vs 上一等长窗口，自动计算 delta_pct",
    "数据同步：一键触发 TikTok 数据同步（前台/后台两种模式）",
    "同步反馈：实时显示新增/更新/跳过的订单与商品数量",
]))

# 4.3 商品分析
story.append(Paragraph("4.3 商品分析", style_h2))
story.append(Paragraph(
    "商品分析模块帮助商品负责人识别爆品与滞销品，优化商品结构。",
    style_body
))
story.append(Paragraph("功能要点：", style_h3))
story.append(bullets([
    "商品销量排行：按 GMV / 销量排序，TOP N 可配置",
    "品类分布：按类目聚合 GMV 占比",
    "滞销识别：低销量/零销量商品清单",
    "价格区间分析：不同价位带的销售贡献",
    "商品详情：单商品的订单数、GMV、退款率、趋势",
]))

# 4.4 达人分析
story.append(Paragraph("4.4 达人分析", style_h2))
story.append(Paragraph(
    "达人分析模块评估达人带货效果，辅助达人商务筛选优质合作对象，标记异常达人（刷单嫌疑）。",
    style_body
))
story.append(Paragraph("功能要点：", style_h3))
story.append(bullets([
    "达人散点图：互动率（X轴）× 转化率（Y轴），气泡大小=GMV",
    "异常标记：is_suspicious 字段标记疑似刷单达人（互动率/转化率异常）",
    "达人详情：粉丝数、品类、ROI、历史带货记录",
    "达人对比：多达人横向对比 GMV/ROI/互动指标",
    "达人来源：对接飞书秒搭达人管理表（多维表格）",
]))

story.append(PageBreak())

# 4.5 流量与营销
story.append(Paragraph("4.5 流量与营销分析", style_h2))
story.append(Paragraph(
    "流量与营销分析模块诊断流量来源结构，评估营销活动与广告投放效果。",
    style_body
))
story.append(bullets([
    "流量来源占比：For You 推荐 / 搜索 / 达人带货 / 广告投放 / 店铺首页 / 其他",
    "营销活动效果：活动期间 vs 非活动期 GMV 对比",
    "广告投放 ROI：花费 / 产出 / ROAS",
    "流量趋势：各来源流量随时间变化",
]))

# 4.6 AI 智能分析报告
story.append(Paragraph("4.6 AI 智能分析报告", style_h2))
story.append(Paragraph(
    "AI 智能分析报告是系统的核心差异化能力。基于通义千问 qwen-max 大模型，"
    "将店铺数据自动转化为自然语言经营分析报告，支持 H5 分享链接，便于团队传播与复盘。",
    style_body
))
story.append(Paragraph("报告类型：", style_h3))
report_types = [
    ["报告类型", "内容", "生成时机"],
    ["店铺经营分析", "GMV/订单/退款/商品/达人综合分析", "手动触发 / 定时日报"],
    ["达人带货分析", "单个达人带货效果深度评估", "飞书秒搭 Webhook 触发"],
    ["周报/月报", "周期性经营总结与趋势", "Celery 定时任务"],
]
story.append(make_table(report_types, col_widths=[3.5 * cm, 7 * cm, 5 * cm]))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph("报告生成流程：", style_h3))
story.append(bullets([
    "数据聚合：从 StandardOrder/Product/Influencer 表聚合指标",
    "Prompt 编排：将指标注入预设 Prompt 模板（shop_analysis.md / creator_analysis.md）",
    "大模型调用：通义千问 qwen-max 生成结构化 Markdown 报告",
    "持久化：报告存入 report 表，关联 dataset（可空）",
    "H5 渲染：/report/[id] 页面渲染报告内容，支持分享链接",
    "飞书推送：通过 Webhook 推送报告摘要到飞书群",
]))

story.append(PageBreak())

# 4.7 TikTok 数据同步
story.append(Paragraph("4.7 TikTok Shop 数据同步", style_h2))
story.append(Paragraph(
    "数据同步模块对接 TikTok Shop Partner API（202309 版本），自动拉取店铺订单与商品数据，"
    "归一化为 StandardOrder / StandardProduct 标准模型落库。Token 支持自动刷新与多渠道持久化。",
    style_body
))
story.append(Paragraph("同步流程：", style_h3))
sync_flow = [
    ["步骤", "操作", "说明"],
    ["1", "获取 access_token", "优先数据库，其次环境变量；过期自动刷新"],
    ["2", "获取 shop_cipher", "调用 /authorization/202309/shops 获取店铺密钥"],
    ["3", "拉取订单", "POST /order/202309/orders/search，按 next_page_token 分页"],
    ["4", "拉取商品", "POST /product/202309/products/search"],
    ["5", "字段映射", "map_tiktok_order / map_tiktok_product 归一化"],
    ["6", "Upsert 落库", "按 (order_id, platform) 唯一键插入或更新"],
    ["7", "Token 持久化", "刷新后写入 内存/数据库/环境变量/.env 四级存储"],
]
story.append(make_table(sync_flow, col_widths=[1.2 * cm, 5 * cm, 9.3 * cm]))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph("Token 管理策略：", style_h3))
story.append(bullets([
    "读取优先级：数据库 > 环境变量（首次引导）",
    "写入目标：内存缓存 + 数据库 + 环境变量 + .env 文件（生产环境跳过文件写入）",
    "自动刷新：过期前 60 分钟自动刷新（OAuth2 rotation 机制）",
    "持久化：Token 存入 platform_tokens 表，服务重启后自动恢复",
]))

# 4.8 飞书企业集成
story.append(Paragraph("4.8 飞书企业集成", style_h2))
story.append(Paragraph(
    "系统深度集成飞书开放平台，实现数据回写、消息通知、秒搭接入三大企业协同能力。",
    style_body
))
story.append(bullets([
    "多维表格回写：分析结果写入飞书多维表格（Bitable），支持达人管理表",
    "Webhook 通知：日报/告警通过飞书自定义机器人 Webhook 推送到群",
    "事件订阅：监听飞书事件（如达人表变更），触发 AI 分析",
    "秒搭接入：飞书秒搭 Webhook 触发达人分析，H5 报告回嵌秒搭 iframe",
    "应用身份：飞书应用身份（app_id/app_secret）用于 OpenAPI 调用",
]))

story.append(PageBreak())

# 4.9 店铺与用户管理
story.append(Paragraph("4.9 店铺与用户管理", style_h2))
story.append(Paragraph(
    "支持多店铺管理与用户权限控制，满足多店铺运营团队需求。",
    style_body
))
story.append(bullets([
    "店铺列表：去重展示所有已同步店铺及订单数/GMV",
    "多店铺筛选：看板支持多店铺勾选，含「默认店铺」",
    "用户管理：用户列表与角色（预留）",
    "设置中心：TikTok 配置、Token 状态、飞书配置、授权码交换",
]))

# 4.10 实时分析
story.append(Paragraph("4.10 实时分析与监控", style_h2))
story.append(Paragraph(
    "实时分析模块提供订单流的实时监控与异常告警能力（预留扩展）。",
    style_body
))
story.append(bullets([
    "实时订单流：最新订单滚动展示",
    "异常告警：GMV 骤降/退款率飙升等异常自动告警",
    "健康检查：/health 与 /api/health 端点监控服务状态",
]))

story.append(PageBreak())

# ---------- 五、数据模型 ----------
story.append(Paragraph("五、数据模型与存储", style_h1))
story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph(
    "系统采用「标准模型」设计，将多平台（TikTok/抖店等）数据归一化为统一的 Standard 系列 ORM 模型，"
    "便于跨平台聚合分析。所有模型使用 SQLAlchemy 2.0 定义，支持 PostgreSQL 与 SQLite 双数据库。",
    style_body
))

story.append(Paragraph("5.1 核心数据表", style_h2))
table_data = [
    ["数据表", "用途", "关键字段"],
    ["standard_orders", "标准化订单", "order_id, platform, shop_id, product_name, gmv, quantity, status, paid_at"],
    ["standard_products", "标准化商品", "product_id, platform, name, category, price, total_gmv, total_sold"],
    ["standard_influencers", "标准化达人", "creator_id, name, category, engagement_rate, conversion_rate, gmv, roi, is_suspicious"],
    ["platform_tokens", "平台 Token 持久化", "platform, access_token, refresh_token, expires_at"],
    ["reports", "AI 分析报告", "id, type, content, dataset_id, ai_report_url, created_at"],
    ["datasets", "分析数据集", "id, source, file_path, meta"],
    ["miaoda_analyses", "秒搭分析记录", "record_id, status, report_id, creator_id"],
]
story.append(make_table(table_data, col_widths=[3.5 * cm, 3.5 * cm, 8.5 * cm]))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("5.2 数据模型设计原则", style_h2))
story.append(bullets([
    "平台字段：platform 使用 VARCHAR + 小写值（如 'tiktok'），非原生 enum，便于扩展",
    "唯一键：StandardOrder 使用 (order_id, platform) 复合唯一键做 Upsert",
    "时间字段：paid_at / create_time 统一存 datetime，支持时区",
    "可空约束：AI 报告的 dataset_id 可空，无外键约束，避免数据耦合",
    "状态枚举：OrderStatus 归一化各平台订单状态（PAID/SHIPPED/COMPLETED/REFUNDED）",
]))

story.append(PageBreak())

# ---------- 六、API 接口 ----------
story.append(Paragraph("六、API 接口设计", style_h1))
story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph(
    "后端基于 FastAPI 提供 RESTful API，所有接口统一 /api 前缀，支持 CORS 跨域。"
    "接口分为数据看板、数据同步、AI 报告、文件上传、飞书集成五大类。",
    style_body
))

story.append(Paragraph("6.1 接口总览", style_h2))
api_data = [
    ["接口", "方法", "说明"],
    ["/api/dashboard/overview", "GET", "KPI 卡片数据 + 环比 + 数据范围"],
    ["/api/dashboard/gmv-trend", "GET", "每日 GMV 趋势序列"],
    ["/api/dashboard/top-products", "GET", "商品销量 TOP N"],
    ["/api/dashboard/influencers", "GET", "达人散点数据 + 异常标记"],
    ["/api/dashboard/shops", "GET", "店铺列表（供多选）"],
    ["/api/tiktok/status", "GET", "TikTok 配置与 Token 状态"],
    ["/api/tiktok/sync", "POST", "触发订单+商品同步（前台/后台）"],
    ["/api/ai-report/generate", "POST", "生成 AI 分析报告"],
    ["/api/ai-report/list", "GET", "报告列表"],
    ["/api/ai-report/{id}", "GET", "报告详情"],
    ["/api/upload", "POST", "上传 CSV/Excel 数据文件"],
    ["/api/analyze", "POST", "分析上传的数据"],
    ["/api/reports", "GET", "历史分析报告"],
    ["/api/feishu/push", "POST", "飞书 Webhook 消息推送"],
    ["/api/miaoda/webhook", "POST", "飞书秒搭 Webhook 入口"],
    ["/health, /api/health", "GET", "健康检查"],
]
story.append(make_table(api_data, col_widths=[5 * cm, 1.5 * cm, 9 * cm]))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("6.2 接口设计规范", style_h2))
story.append(bullets([
    "统一前缀：所有业务接口 /api 开头，便于网关路由",
    "查询参数：列表接口支持 days / shop_ids / limit 等分页与筛选",
    "响应格式：JSON，含 code / message / data 三段式（部分接口直接返回数据）",
    "错误处理：HTTP 状态码 + message 字段描述错误原因",
    "异步任务：长耗时操作用 BackgroundTasks 或 Celery，接口立即返回任务状态",
]))

story.append(PageBreak())

# ---------- 七、安全与权限 ----------
story.append(Paragraph("七、安全与权限", style_h1))
story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("7.1 认证与授权", style_h2))
story.append(bullets([
    "TikTok OAuth2 授权：auth_code 换取 access_token / refresh_token",
    "Token 安全存储：数据库持久化 + 内存缓存，不明文记录日志",
    "Token 自动刷新：过期前 60 分钟自动刷新，OAuth2 rotation 机制",
    "飞书应用身份：app_id / app_secret 调用飞书 OpenAPI",
    "Webhook 签名校验：飞书 Webhook 支持签名密钥校验（安全模式）",
]))

story.append(Paragraph("7.2 数据安全", style_h2))
story.append(bullets([
    "CORS 限制：仅允许指定前端域名（localhost / 生产域名）",
    "文件上传：限制 50MB，支持 CSV / Excel 格式校验",
    "数据库连接：PostgreSQL 强制 SSL（sslmode=require）",
    "敏感配置：app_secret / refresh_token 等通过环境变量注入，不硬编码",
    "连接池：PostgreSQL 启用 pool_recycle=1800s，防止空闲连接被回收",
]))

story.append(Paragraph("7.3 接口安全", style_h2))
story.append(bullets([
    "秒搭 Webhook：X-Miaoda-Secret 头部校验",
    "飞书事件订阅：verification_token 校验",
    "输入校验：Pydantic 模型自动校验请求体",
    "SQL 注入防护：SQLAlchemy ORM 参数化查询",
]))

story.append(PageBreak())

# ---------- 八、部署与运维 ----------
story.append(Paragraph("八、部署与运维", style_h1))
story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("8.1 部署架构", style_h2))
deploy_data = [
    ["组件", "部署方式", "说明"],
    ["前端", "Render 静态站点 / Vercel", "Next.js 构建产物"],
    ["后端 API", "Render Web Service / Docker", "FastAPI + Uvicorn"],
    ["数据库", "Render PostgreSQL", "生产数据库，SSL 连接"],
    ["Redis", "Render Redis / 自建", "Celery broker + 结果后端"],
    ["Celery Worker", "Render Background Worker", "异步任务执行"],
    ["文件存储", "本地 uploads / 对象存储", "上传文件暂存"],
]
story.append(make_table(deploy_data, col_widths=[3 * cm, 5 * cm, 7.5 * cm]))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("8.2 环境变量配置", style_h2))
env_data = [
    ["变量名", "用途", "必填"],
    ["DATABASE_URL", "数据库连接串", "是"],
    ["REDIS_URL", "Redis 连接串", "是（异步任务）"],
    ["DASHSCOPE_API_KEY", "通义千问 API Key", "是（AI 报告）"],
    ["QWEN_MODEL", "模型名（默认 qwen-max）", "否"],
    ["TK_PARTNER_APP_KEY", "TikTok 应用 Key", "是（数据同步）"],
    ["TK_PARTNER_APP_SECRET", "TikTok 应用密钥", "是"],
    ["TK_AUTH_SHOP_ID", "授权店铺 ID", "是"],
    ["TK_AUTH_ACCESS_TOKEN", "访问令牌（首次引导）", "首次"],
    ["TK_AUTH_REFRESH_TOKEN", "刷新令牌（首次引导）", "首次"],
    ["FEISHU_APP_ID / APP_SECRET", "飞书应用凭证", "否（飞书集成）"],
    ["MIAODA_WEBHOOK_SECRET", "秒搭 Webhook 校验密钥", "否"],
]
story.append(make_table(env_data, col_widths=[5 * cm, 6 * cm, 4.5 * cm]))
story.append(Spacer(1, 0.3 * cm))

story.append(Paragraph("8.3 运维监控", style_h2))
story.append(bullets([
    "健康检查：/health 与 /api/health 端点，供 Render 探活",
    "日志：Python logging，记录 API 调用、同步进度、错误堆栈",
    "自动建表：开发期 Base.metadata.create_all 自动建表",
    "数据库迁移：生产建议用 Alembic（当前自动建表）",
    "定时任务：Celery beat 调度日报生成（/api/tasks/daily-report/trigger 手动触发）",
]))

story.append(PageBreak())

# ---------- 九、版本规划 ----------
story.append(Paragraph("九、版本规划", style_h1))
story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
story.append(Spacer(1, 0.3 * cm))

roadmap_data = [
    ["版本", "阶段", "核心功能"],
    ["V1.0（当前）", "上线版", "数据看板 + TikTok 同步 + AI 报告 + 飞书集成"],
    ["V1.1", "优化版", "TikTok API 分页修复、流量来源对接、实时告警"],
    ["V1.2", "扩展版", "抖店/Shopee 多平台接入、用户权限体系"],
    ["V2.0", "企业版", "预测分析（销量预测）、智能选品、自动化营销建议"],
]
story.append(make_table(roadmap_data, col_widths=[3 * cm, 2.5 * cm, 10 * cm]))
story.append(Spacer(1, 0.5 * cm))

story.append(Paragraph("9.1 已知限制", style_h2))
story.append(bullets([
    "TikTok API 分页：202309 orders/search 接口分页失效，当前仅同步最近 100 单（需 App 上线模式）",
    "流量来源：当前为占位数据，需对接 TikTok Analytics API",
    "用户权限：当前无登录认证，多租户权限体系待 V1.2",
    "数据库迁移：开发期自动建表，生产建议迁移到 Alembic",
]))

story.append(Spacer(1, 1 * cm))
story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph(
    "— 文档结束 —",
    ParagraphStyle("End", fontName="STSong-Light", fontSize=10, leading=14,
                   textColor=GRAY, alignment=TA_CENTER)
))
story.append(Paragraph(
    f"AI Shop Analyzer · V1.0 · {datetime.now().strftime('%Y-%m-%d')}",
    style_caption
))


# ==================== 生成 PDF ====================
doc = SimpleDocTemplate(
    OUTPUT_PATH,
    pagesize=A4,
    leftMargin=2 * cm,
    rightMargin=2 * cm,
    topMargin=2 * cm,
    bottomMargin=2 * cm,
    title="AI 店铺分析器 - 产品设计文档",
    author="AI Shop Analyzer Team",
    subject="产品设计文档",
)

doc.build(story, onFirstPage=add_page_decoration, onLaterPages=add_page_decoration)
print(f"PDF 已生成: {OUTPUT_PATH}")
print(f"文件大小: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")
