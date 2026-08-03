"use client";

// 营销分析页面（数据缺失骨架）
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

export default function MarketingPage() {
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="ds-title">营销分析</h1>
        <p className="ds-subtitle mt-1">
          活动效果、广告投放、优惠券核销与达人带货
        </p>
      </div>

      {/* 1. 顶部4列指标卡 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="营销活动数" hint="周期内进行中的活动" />
        <MetricCard label="活动带来 GMV" hint="活动关联订单 GMV" />
        <MetricCard label="营销投入成本" hint="广告+优惠券+达人成本" />
        <MetricCard label="ROI" hint="GMV / 营销投入" />
      </div>

      {/* 2. 营销活动效果排行（全宽） */}
      <section className="ds-card p-5">
        <SectionHeader
          title="营销活动效果排行"
          subtitle="各活动 GMV、订单数、ROI 对比"
        />
        <div className="mt-4 overflow-x-auto">
          <EmptyState emoji="🏆" source="活动效果" />
        </div>
      </section>

      {/* 3. 广告投放分析（左1/2） + 4. 优惠券核销分析（右1/2） */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="ds-card p-5">
          <SectionHeader
            title="广告投放数据"
            subtitle="各广告计划消耗、点击、CPC 与 ROAS"
          />
          <div className="mt-4">
            <EmptyState emoji="📣" source="广告投放" />
          </div>
        </section>

        <section className="ds-card p-5">
          <SectionHeader
            title="优惠券核销分析"
            subtitle="发放量、领取量、核销率与核销 GMV"
          />
          <div className="mt-4">
            <EmptyState emoji="🎟️" source="优惠券核销" />
          </div>
        </section>
      </div>

      {/* 5. 达人带货效果排行（底部全宽） */}
      <section className="ds-card p-5">
        <SectionHeader
          title="达人带货效果排行"
          subtitle="合作达人 GMV、订单数与佣金 ROI 排行"
        />
        <div className="mt-4">
          <EmptyState emoji="⭐" source="达人带货" />
        </div>
      </section>
    </div>
  );
}
