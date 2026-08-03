"use client";

// 流量分析页面（数据缺失骨架）
// 后端暂无对应 API，所有数据区域显示空状态占位

// ===== 指标卡 =====
function MetricCard({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="ds-card-hover p-5">
      <p className="ds-caption">{label}</p>
      <p className="mt-2 text-2xl font-bold tabular-nums text-gray-900">-</p>
      <div className="mt-2">
        {hint && <span className="ds-caption">{hint}</span>}
      </div>
    </div>
  );
}

// 区块标题
function SectionHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div>
      <h2 className="ds-title">{title}</h2>
      {subtitle && <p className="ds-subtitle mt-1">{subtitle}</p>}
    </div>
  );
}

// 空状态
function EmptyState({ emoji, source }: { emoji: string; source: string }) {
  return (
    <div className="ds-empty">
      <div className="mb-3 text-4xl opacity-30">{emoji}</div>
      <p className="ds-subtitle text-gray-400">暂无数据</p>
      <p className="ds-caption mt-1">需对接{source}接口</p>
    </div>
  );
}

export default function TrafficPage() {
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="ds-title">流量分析</h1>
        <p className="ds-subtitle mt-1">
          访客来源、流量质量与搜索热词，评估店铺引流效果
        </p>
      </div>

      {/* 1. 顶部4列指标卡 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="总访客数 UV" hint="独立访客去重" />
        <MetricCard label="页面浏览量 PV" hint="全店页面浏览总量" />
        <MetricCard label="人均浏览页数" hint="PV / UV" />
        <MetricCard label="平均停留时长" hint="单访客平均停留" />
      </div>

      {/* 2. 流量趋势与转化漏斗（全宽） */}
      <section className="ds-card p-5">
        <SectionHeader
          title="流量趋势与转化漏斗"
          subtitle="访客数变化趋势与访问-加购-下单转化漏斗"
        />
        <div className="mt-4">
          <EmptyState emoji="📈" source="流量趋势" />
        </div>
      </section>

      {/* 3. 流量来源渠道明细（左2/3） + 4. 流量质量评分（右1/3） */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="ds-card p-5 lg:col-span-2">
          <SectionHeader
            title="各渠道流量效果对比"
            subtitle="自然/搜索/广告/社交/直链等渠道的访客与转化"
          />
          <div className="mt-4 overflow-x-auto">
            <EmptyState emoji="🧭" source="渠道明细" />
          </div>
        </section>

        <section className="ds-card p-5">
          <SectionHeader
            title="流量质量评分"
            subtitle="基于跳出率、停留时长与转化的综合评分"
          />
          <div className="mt-4">
            <EmptyState emoji="🎯" source="流量质量" />
          </div>
        </section>
      </div>

      {/* 5. 进店搜索热词 TOP20（底部全宽） */}
      <section className="ds-card p-5">
        <SectionHeader
          title="进店搜索热词 TOP20"
          subtitle="站内搜索关键词热度排行与对应访客数"
        />
        <div className="mt-4">
          <EmptyState emoji="🔍" source="搜索热词" />
        </div>
      </section>
    </div>
  );
}
