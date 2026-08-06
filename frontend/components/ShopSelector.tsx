"use client";

import { useShop } from "@/lib/shop/context";
import { useT } from "@/lib/i18n/context";

export function ShopSelector() {
  const { shops, currentShopId, setCurrentShopId, loading } = useShop();
  const t = useT();

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-1.5">
        <span className="text-xs text-gray-400">...</span>
      </div>
    );
  }

  // 只有一个店铺时，直接显示，不显示下拉（减少干扰）
  if (shops.length <= 1) {
    const shop = shops[0];
    return (
      <div className="hidden items-center gap-2 rounded-lg border border-gray-200 px-3 py-1.5 md:flex">
        <span className="text-xs text-gray-400">{t("nav.shop")}</span>
        <span className="max-w-[160px] truncate text-sm font-medium text-gray-700">
          {shop?.name ?? "TikTok Shop"}
        </span>
      </div>
    );
  }

  // 多个店铺时，显示下拉选择器
  return (
    <div className="flex items-center gap-2">
      <span className="hidden text-xs text-gray-400 md:inline">{t("nav.shop")}</span>
      <select
        value={currentShopId}
        onChange={(e) => setCurrentShopId(e.target.value)}
        className="max-w-[180px] truncate rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-sm font-medium text-gray-700 focus:border-primary-400 focus:outline-none focus:ring-1 focus:ring-primary-400"
      >
        <option value="">{t("common.allShops")}</option>
        {shops.map((shop) => (
          <option key={shop.shop_id} value={shop.shop_id}>
            {shop.name} ({shop.order_count})
          </option>
        ))}
      </select>
    </div>
  );
}
