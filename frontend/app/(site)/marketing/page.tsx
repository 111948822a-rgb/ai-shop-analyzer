"use client";

// 营销分析页面（数据缺失骨架）
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

export default function MarketingPage() {
  const t = useT();
  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="ds-title">{t("skeleton.marketingTitle")}</h1>
        <p className="ds-subtitle mt-1">{t("skeleton.marketingSub")}</p>
      </div>

      {/* 1. 顶部4列指标卡 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label={t("skeleton.marketingK1")}
          hint={t("skeleton.marketingK1Hint")}
        />
        <MetricCard
          label={t("skeleton.marketingK2")}
          hint={t("skeleton.marketingK2Hint")}
        />
        <MetricCard
          label={t("skeleton.marketingK3")}
          hint={t("skeleton.marketingK3Hint")}
        />
        <MetricCard
          label={t("skeleton.marketingK4")}
          hint={t("skeleton.marketingK4Hint")}
        />
      </div>

      {/* 2. 营销活动效果排行（全宽） */}
      <section className="ds-card p-5">
        <SectionHeader
          title={t("skeleton.marketingS1")}
          subtitle={t("skeleton.marketingS1Sub")}
        />
        <div className="mt-4 overflow-x-auto">
          <EmptyState emoji="🏆" source={t("skeleton.marketingSrc1")} />
        </div>
      </section>

      {/* 3. 广告投放分析（左1/2） + 4. 优惠券核销分析（右1/2） */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="ds-card p-5">
          <SectionHeader
            title={t("skeleton.marketingS2")}
            subtitle={t("skeleton.marketingS2Sub")}
          />
          <div className="mt-4">
            <EmptyState emoji="📣" source={t("skeleton.marketingSrc2")} />
          </div>
        </section>

        <section className="ds-card p-5">
          <SectionHeader
            title={t("skeleton.marketingS3")}
            subtitle={t("skeleton.marketingS3Sub")}
          />
          <div className="mt-4">
            <EmptyState emoji="🎟️" source={t("skeleton.marketingSrc3")} />
          </div>
        </section>
      </div>

      {/* 5. 达人带货效果排行（底部全宽） */}
      <section className="ds-card p-5">
        <SectionHeader
          title={t("skeleton.marketingS4")}
          subtitle={t("skeleton.marketingS4Sub")}
        />
        <div className="mt-4">
          <EmptyState emoji="⭐" source={t("skeleton.marketingSrc4")} />
        </div>
      </section>
    </div>
  );
}
