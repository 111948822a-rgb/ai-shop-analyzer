"""冒烟测试：不依赖真实 LLM Key，验证 上传 → Pandas 预处理 → 入库 全链路。

运行: python smoke_test.py
"""

import io
import json
import os
import sys
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.gettempdir(), "smoke_test.db").replace("\\", "/")
os.environ["UPLOAD_DIR"] = os.path.join(tempfile.gettempdir(), "smoke_uploads")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SHOP_CSV = """日期,商品名称,销售额,订单数,访客数
2026-07-14,磁吸手机壳,¥1,234.50,32,1200
2026-07-14,车载支架,890.00,15,800
2026-07-15,磁吸手机壳,"2,100.00",55,1500
2026-07-15,数据线三合一,560.00,21,600
2026-07-16,磁吸手机壳,1800.00,44,1400
2026-07-16,车载支架,1020.00,18,850
""".replace("¥1,234.50", '"¥1,234.50"')

CREATOR_CSV = """达人昵称,粉丝数,视频数,销售额,投产比
@techgirl_us,15.2万,3,4200,5.6
@gadgetdad,8.7万,2,1800,3.1
@lifehacks101,22万,5,300,0.8
@coolstuff_review,4.5万,1,0,0
@phoneaccessory,12万,4,2600,4.2
"""


def main() -> int:
    ok = True
    with TestClient(app) as client:
        # 1. 健康检查
        r = client.get("/api/health")
        assert r.status_code == 200, r.text
        print("[PASS] /api/health")

        # 2. 店铺数据上传 + 预处理
        r = client.post(
            "/api/upload",
            files={"file": ("shop_sales.csv", io.BytesIO(SHOP_CSV.encode("utf-8-sig")), "text/csv")},
            data={"data_type": "shop"},
        )
        assert r.status_code == 200, r.text
        shop = r.json()["dataset"]
        s = shop["summary"]
        print(f"[PASS] 店铺上传: {shop['row_count']} 行, 总GMV={s.get('total_gmv')}, "
              f"订单={s.get('total_orders')}, 转化率={s.get('overall_conversion_rate')}%, "
              f"Top商品={s['top10_products'][0]['product'] if s.get('top10_products') else '无'}")
        assert s.get("total_gmv") and s.get("top10_products") and s.get("daily_gmv_trend")

        # 3. 达人数据上传 + 预处理
        r = client.post(
            "/api/upload",
            files={"file": ("creators.csv", io.BytesIO(CREATOR_CSV.encode("gbk")), "text/csv")},
            data={"data_type": "creator"},
        )
        assert r.status_code == 200, r.text
        creator = r.json()["dataset"]
        c = creator["summary"]
        print(f"[PASS] 达人上传(GBK编码): 达人数={c.get('creator_count')}, "
              f"平均ROI={c.get('avg_roi')}, 出单率={c.get('producing_rate')}%, "
              f"ROI分布={json.dumps(c.get('roi_distribution'), ensure_ascii=False)}")
        assert c.get("creator_count") == 5 and c.get("avg_roi")

        # 4. 非法文件拦截
        r = client.post(
            "/api/upload",
            files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
            data={"data_type": "shop"},
        )
        assert r.status_code == 400
        print("[PASS] 非法格式拦截 (.exe -> 400)")

        # 5. 数据集列表
        r = client.get("/api/datasets")
        assert r.status_code == 200 and len(r.json()) >= 2
        print(f"[PASS] 数据集列表: {len(r.json())} 条")

        # 6. 创建分析任务（无 API Key 时应落为 failed 状态而非崩溃）
        r = client.post(f"/api/analyze/{shop['id']}", json={"report_type": "weekly"})
        assert r.status_code == 200, r.text
        report_id = r.json()["id"]
        r = client.get(f"/api/reports/{report_id}")
        status = r.json()["status"]
        print(f"[PASS] 分析任务创建: report_id={report_id}, status={status}"
              + ("（未配置 LLM Key，符合预期）" if status == "failed" else ""))

    print("\n全部通过 ✓" if ok else "存在失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
