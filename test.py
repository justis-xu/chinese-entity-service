"""
快速验证脚本：测试实体提取服务是否正常工作。

用法：
    python test.py --url http://localhost:8001   # 测试 LAC
    python test.py --url http://localhost:8002   # 测试 HanLP
    python test.py --url http://localhost:8003   # 测试 spaCy
    python test.py --url http://localhost:8001 --concurrent 10  # 并发测试
"""

import argparse
import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def post(url: str, body: dict, timeout: float = 30) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_healthy(base: str, max_wait: int = 120):
    print(f"等待服务就绪: {base}/health")
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            res = get(f"{base}/health")
            if res.get("status") == "ok":
                print(f"服务就绪: {res}")
                return
        except Exception:
            pass
        time.sleep(2)
    print("超时：服务未就绪")
    sys.exit(1)


def test_basic(base: str):
    print("\n--- 基础提取 ---")
    cases = [
        {
            "texts": ["李明在北京参加了阿里巴巴的发布会"],
            "expect": ["李明", "北京", "阿里巴巴"],
        },
        {
            "texts": ["2024年马云在杭州创立了新公司"],
            "expect": ["马云", "杭州"],
        },
        {
            "texts": ["今天天气不错"],
            "expect": [],
        },
    ]
    for c in cases:
        res = post(f"{base}/extract", {"texts": c["texts"]})
        entities = res["entities"][0]
        missing = [e for e in c["expect"] if not any(e in ent for ent in entities)]
        status = "✓" if not missing else f"✗ 缺失: {missing}"
        print(f"  输入: {c['texts'][0]}")
        print(f"  结果: {entities}  {status}")


def test_type_filter(base: str):
    print("\n--- 类型过滤 ---")
    text = "李明在北京参加了阿里巴巴的发布会"
    for types in [["PER"], ["LOC"], ["ORG"], ["PER", "ORG"]]:
        res = post(f"{base}/extract", {"texts": [text], "types": types})
        print(f"  types={types} → {res['entities'][0]}")


def test_batch(base: str):
    print("\n--- 批量输入 ---")
    texts = [
        "李明在北京工作",
        "张伟就职于腾讯",
        "王芳来自上海",
    ]
    res = post(f"{base}/extract", {"texts": texts})
    for t, e in zip(texts, res["entities"]):
        print(f"  {t} → {e}")


def test_edge_cases(base: str):
    print("\n--- 边界情况 ---")
    cases = [
        ("空字符串", ""),
        ("纯数字", "12345678"),
        ("超长文本", "李明" * 500),
        ("特殊符号", "!@#$%^&*()"),
    ]
    for name, text in cases:
        try:
            res = post(f"{base}/extract", {"texts": [text]})
            print(f"  {name}: {res['entities'][0]}")
        except Exception as e:
            print(f"  {name}: 异常 {e}")


def test_concurrent(base: str, n: int):
    print(f"\n--- 并发测试 ({n} 个同时请求) ---")
    payload = {"texts": ["李明在北京参加了阿里巴巴的发布会"]}

    results = {"ok": 0, "429": 0, "error": 0, "times": []}

    def call(_):
        t0 = time.time()
        try:
            post(f"{base}/extract", payload, timeout=15)
            results["ok"] += 1
        except urllib.error.HTTPError as e:
            if e.code == 429:
                results["429"] += 1
            else:
                results["error"] += 1
        except Exception:
            results["error"] += 1
        results["times"].append(time.time() - t0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        list(pool.map(call, range(n)))

    times = results["times"]
    print(f"  成功: {results['ok']}  限流(429): {results['429']}  异常: {results['error']}")
    print(f"  耗时: min={min(times):.2f}s  max={max(times):.2f}s  avg={sum(times)/len(times):.2f}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8001")
    parser.add_argument("--concurrent", type=int, default=5)
    parser.add_argument("--no-wait", action="store_true")
    args = parser.parse_args()

    base = args.url.rstrip("/")

    if not args.no_wait:
        wait_healthy(base)

    test_basic(base)
    test_type_filter(base)
    test_batch(base)
    test_edge_cases(base)
    test_concurrent(base, args.concurrent)

    print("\n完成")


if __name__ == "__main__":
    main()
