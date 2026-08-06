"use client";

// 流量分析页面（数据缺失骨架）
// 后端暂无对应 API，所有数据区域显示空状态占位

import { useT } from "@/lib/i18n/context";

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
  const t = useT();
  return (
    <div className="ds-empty">
      <div className="mb-3 text-4xl opacity-30">{emoji}</div>
      <p className="ds-subtitle text-gray-400">{t("common.noData")}</p>
      <p className="ds-caption mt-1">{t("skeleton.needApi", { source })}</p>
    </div>
  );
}

export default function TrafficPage() {
  const t = useT();
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="ds-title">{t("skeleton.trafficTitle")}</h1>
        <p className="ds-subtitle mt-1">{t("skeleton.trafficSub")}</p>
      </div>

      {/* 1. 顶部4列指标卡 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label={t("skeleton.trafficK1")}
          hint={t("skeleton.trafficK1Hint")}
        />
        <MetricCard
          label={t("skeleton.trafficK2")}
          hint={t("skeleton.trafficK2Hint")}
        />
        <MetricCard
          label={t("skeleton.trafficK3")}
          hint={t("skeleton.trafficK3Hint")}
        />
        <MetricCard
          label={t("skeleton.trafficK4")}
          hint={t("skeleton.trafficK4Hint")}
        />
      </div>

      {/* 2. 流量趋势与转化漏斗（全宽） */}
      <section className="ds-card p-5">
        <SectionHeader
          title={t("skeleton.trafficS1")}
          subtitle={t("skeleton.trafficS1Sub")}
        />
        <div className="mt-4">
          <EmptyState emoji="📈" source={t("skeleton.trafficSrc1")} />
        </div>
      </section>

      {/* 3. 流量来源渠道明细（左2/3） + 4. 流量质量评分（右1/3） */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <section className="ds-card p-5 lg:col-span-2">
          <SectionHeader
            title={t("skeleton.trafficS2")}
            subtitle={t("skeleton.trafficS2Sub")}
          />
          <div className="mt-4 overflow-x-auto">
            <EmptyState emoji="🧭" source={t("skeleton.trafficSrc2")} />
          </div>
        </section>

        <section className="ds-card p-5">
          <SectionHeader
            title={t("skeleton.trafficS3")}
            subtitle={t("skeleton.trafficS3Sub")}
          />
          <div className="mt-4">
            <EmptyState emoji="🎯" source={t("skeleton.trafficSrc3")} />
          </div>
        </section>
      </div>

      {/* 5. 进店搜索热词 TOP20（底部全宽） */}
      <section className="ds-card p-5">
        <SectionHeader
          title={t("skeleton.trafficS4")}
          subtitle={t("skeleton.trafficS4Sub")}
        />
        <div className="mt-4">
          <EmptyState emoji="🔍" source={t("skeleton.trafficSrc4")} />
        </div>
      </section>
    </div>
  );
}
