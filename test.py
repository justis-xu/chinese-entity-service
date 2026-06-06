"""
验证与压测脚本。

用法：
    python test.py --url http://localhost:8001        # 测试 spaCy sm
    python test.py --url http://localhost:8002        # 测试 spaCy lg
    python test.py --all                              # 对比所有服务，生成报告
    python test.py --all --bench                      # 只跑压测
    python test.py --all --duration 300 --concurrent 20
    python test.py --url http://localhost:8002 -v     # 显示每条用例详情
"""

import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from threading import Lock

SERVICES = {
    "spacy-sm": "http://localhost:8001",
    "spacy-lg": "http://localhost:8002",
}

# ── 验证用例 (文本, 期望包含的实体, 分类标签) ──────────────────────
BASIC_CASES = [
    # 政治人名
    ("习近平在人民大会堂会见了来访代表团", ["习近平", "人民大会堂"], "政治人名"),
    ("李强主持召开国务院常务会议研究部署稳增长工作", ["李强"], "政治人名"),
    ("王毅外长与布林肯国务卿在日内瓦举行会谈", ["王毅", "布林肯", "日内瓦"], "政治人名"),
    ("普京与拜登在赫尔辛基举行峰会", ["普京", "拜登", "赫尔辛基"], "政治人名"),
    ("岸田文雄访问北京与中国领导人举行会谈", ["岸田文雄", "北京"], "政治人名"),
    ("安东尼奥·古特雷斯在联合国发表演讲", ["古特雷斯", "联合国"], "政治人名"),
    ("朔尔茨总理访问北京寻求加强中德经济合作", ["朔尔茨", "北京"], "政治人名"),
    ("马克龙在爱丽舍宫会见中国驻法大使", ["马克龙", "爱丽舍宫"], "政治人名"),
    ("苏纳克宣布提前举行英国大选", ["苏纳克", "英国"], "政治人名"),
    ("韩国总统尹锡悦宣布戒严随后撤回", ["尹锡悦", "韩国"], "政治人名"),
    # 商业人名
    ("马云创立了淘宝网", ["马云", "淘宝"], "商业人名"),
    ("任正非创立华为已超过三十年", ["任正非", "华为"], "商业人名"),
    ("张一鸣离开字节跳动后梁汝波接任CEO", ["张一鸣", "字节跳动", "梁汝波"], "商业人名"),
    ("雷军宣布小米汽车正式上市", ["雷军", "小米"], "商业人名"),
    ("王兴旗下的美团在香港上市", ["王兴", "美团", "香港"], "商业人名"),
    ("刘强东卸任京东CEO由徐雷接棒", ["刘强东", "京东", "徐雷"], "商业人名"),
    ("黄峥创立的拼多多市值超过阿里巴巴", ["黄峥", "拼多多", "阿里巴巴"], "商业人名"),
    ("程维和柳青共同领导滴滴出行", ["程维", "柳青", "滴滴出行"], "商业人名"),
    ("王慧文从美团离职后创办了光年之外", ["王慧文", "美团", "光年之外"], "商业人名"),
    ("张勇从阿里巴巴CEO职位卸任", ["张勇", "阿里巴巴"], "商业人名"),
    # 科技人名
    ("蒂姆·库克访问北京与工信部官员会面", ["蒂姆·库克", "北京", "工信部"], "科技人名"),
    ("埃隆·马斯克旗下星舰完成第六次试飞", ["埃隆·马斯克"], "科技人名"),
    ("比尔·盖茨基金会宣布向非洲捐款十亿美元", ["比尔·盖茨"], "科技人名"),
    ("萨姆·奥特曼重返人工智能公司担任CEO", ["萨姆·奥特曼"], "科技人名"),
    ("黄仁勋在台北宣布新一代AI芯片量产计划", ["黄仁勋", "台北"], "科技人名"),
    ("扎克伯格宣布将在元宇宙领域继续加大投资", ["扎克伯格"], "科技人名"),
    ("苏姿丰领导超威半导体成功追赶英特尔和英伟达", ["苏姿丰", "英特尔", "英伟达"], "科技人名"),
    ("杰夫·贝佐斯卸任亚马逊CEO由安迪·贾西接任", ["杰夫·贝佐斯", "亚马逊", "安迪·贾西"], "科技人名"),
    # 国内地名
    ("深圳湾科技生态园位于南山区", ["深圳湾科技生态园", "南山区"], "国内地名"),
    ("黄河流经青海四川甘肃宁夏内蒙古等九省", ["黄河", "青海", "四川", "甘肃", "宁夏", "内蒙古"], "国内地名"),
    ("成渝经济圈涵盖重庆和四川两地", ["重庆", "四川"], "国内地名"),
    ("雄安新区是河北省的国家级新区", ["雄安新区", "河北"], "国内地名"),
    ("粤港澳大湾区包括广州深圳香港澳门等城市", ["广州", "深圳", "香港", "澳门"], "国内地名"),
    ("长三角一体化涵盖上海江苏浙江安徽", ["上海", "江苏", "浙江", "安徽"], "国内地名"),
    ("三峡大坝位于湖北省宜昌市", ["三峡大坝", "湖北", "宜昌"], "国内地名"),
    ("青藏高原平均海拔超过四千米", ["青藏高原"], "国内地名"),
    ("海南自由贸易港吸引大量企业注册落户", ["海南"], "国内地名"),
    ("北京中关村科技园是中国最重要的创新中心", ["北京", "中关村"], "国内地名"),
    ("上海浦东新区是改革开放的重要试验田", ["上海", "浦东新区"], "国内地名"),
    ("深圳前海合作区与香港深度联通", ["深圳", "前海合作区", "香港"], "国内地名"),
    ("西藏拉萨布达拉宫是著名的历史文化遗址", ["西藏", "拉萨", "布达拉宫"], "国内地名"),
    # 国际地名
    ("中美贸易谈判在华盛顿举行", ["华盛顿"], "国际地名"),
    ("欧盟总部设在比利时布鲁塞尔", ["比利时", "布鲁塞尔"], "国际地名"),
    ("联合国安理会在纽约召开紧急会议", ["纽约"], "国际地名"),
    ("G20峰会在印度新德里举行", ["印度", "新德里"], "国际地名"),
    ("乌克兰基辅遭到导弹袭击", ["乌克兰", "基辅"], "国际地名"),
    ("以色列与哈马斯在加沙地带爆发冲突", ["以色列", "加沙"], "国际地名"),
    ("台积电在美国亚利桑那州建设芯片工厂", ["台积电", "美国", "亚利桑那州"], "国际地名"),
    ("三星电子在韩国平泽建设新晶圆厂", ["三星电子", "韩国", "平泽"], "国际地名"),
    ("东京奥运会在疫情期间如期举行", ["东京"], "国际地名"),
    ("巴黎协定是全球应对气候变化的重要框架", ["巴黎"], "国际地名"),
    ("中巴经济走廊连接新疆与巴基斯坦瓜达尔港", ["新疆", "巴基斯坦"], "国际地名"),
    # 科技机构
    ("腾讯阿里巴巴字节跳动是中国互联网三巨头", ["腾讯", "阿里巴巴", "字节跳动"], "科技机构"),
    ("华为发布了最新旗舰手机Mate系列", ["华为"], "科技机构"),
    ("百度Apollo自动驾驶在北京开放商业运营", ["百度", "北京"], "科技机构"),
    ("小米与比亚迪达成战略合作协议", ["小米", "比亚迪"], "科技机构"),
    ("美团收购了摩拜单车", ["美团"], "科技机构"),
    ("滴滴出行在纽约证券交易所退市", ["纽约证券交易所"], "科技机构"),
    ("快手在短视频领域展开竞争", ["快手"], "科技机构"),
    ("京东物流在全国建设了大量智能仓储中心", ["京东"], "科技机构"),
    ("拼多多在北美市场快速扩张", ["北美"], "科技机构"),
    ("蚂蚁集团上市计划被监管部门叫停", ["蚂蚁集团"], "科技机构"),
    ("大疆在无人机领域占据全球市场主导地位", ["大疆"], "科技机构"),
    ("商汤科技旷视科技是人工智能视觉领域主要企业", ["商汤科技", "旷视科技"], "科技机构"),
    ("科大讯飞在语音识别领域处于国内领先地位", ["科大"], "科技机构"),
    # 金融机构
    ("中国人民银行宣布下调存款准备金率", ["中国人民银行"], "金融机构"),
    ("中国平安保险集团发布三季报净利润同比增长", ["中国平安保险集团"], "金融机构"),
    ("招商银行和工商银行联合发布绿色金融报告", ["招商银行", "工商银行"], "金融机构"),
    ("上海证券交易所公告显示比亚迪股价创历史新高", ["上海证券交易所", "比亚迪"], "金融机构"),
    ("高盛摩根士丹利下调中国市场评级", ["高盛", "摩根士丹利"], "金融机构"),
    ("欧洲央行宣布加息二十五个基点", ["欧洲央行"], "金融机构"),
    ("美联储主席鲍威尔发表讲话暗示暂停加息", ["鲍威尔"], "金融机构"),
    ("国家开发银行向雄安新区提供融资支持", ["国家开发银行", "雄安新区"], "金融机构"),
    ("中国建设银行与农业银行合并传闻被辟谣", ["中国建设银行", "农业银行"], "金融机构"),
    ("中信证券海通证券在资本市场业务上展开竞争", ["中信证券", "海通证券"], "金融机构"),
    ("高瓴资本红杉资本是国内最活跃的私募投资机构", ["高瓴资本", "红杉资本"], "金融机构"),
    # 教育机构
    ("清华大学和北京大学是中国顶尖高校", ["清华大学", "北京大学"], "教育机构"),
    ("复旦大学浙江大学联合举办人工智能峰会", ["复旦大学", "浙江大学"], "教育机构"),
    ("麻省理工学院与清华大学开展联合研究", ["麻省理工学院", "清华大学"], "教育机构"),
    ("中国科学院在量子计算领域取得重大突破", ["中国科学院"], "教育机构"),
    ("哈佛大学耶鲁大学普林斯顿大学合称常春藤名校", ["哈佛大学", "耶鲁大学", "普林斯顿大学"], "教育机构"),
    ("斯坦福大学孵化了谷歌惠普思科等科技巨头", ["斯坦福大学", "谷歌", "惠普", "思科"], "教育机构"),
    ("中国人民大学在人文社科领域享有盛誉", ["中国人民大学"], "教育机构"),
    ("南京大学武汉大学中山大学是华中华南名校", ["南京大学", "武汉大学", "中山大学"], "教育机构"),
    # 政府机构
    ("工业和信息化部发布新能源汽车产业规划", ["工业和信息化部"], "政府机构"),
    ("国家市场监督管理总局对互联网平台展开调查", ["国家市场监督管理总局"], "政府机构"),
    ("商务部宣布对美国芯片企业实施出口管制", ["商务部"], "政府机构"),
    ("国家发展改革委批复了多个基础设施项目", ["国家发展改革委"], "政府机构"),
    ("科学技术部发布新一轮国家重点研发计划", ["科学技术部"], "政府机构"),
    ("国家能源局批准多个海上风电项目建设方案", ["国家能源局"], "政府机构"),
    ("中国证券监督管理委员会对违规上市公司展开调查", ["中国证券监督管理委员会"], "政府机构"),
    # 能源制造
    ("宁德时代全球动力电池市场份额稳居第一", ["宁德时代"], "能源制造"),
    ("比亚迪新能源汽车销量连续多月超过特斯拉", ["比亚迪", "特斯拉"], "能源制造"),
    ("中国石油天然气集团在中亚签署新开采合同", ["中国石油天然气集团", "中亚"], "能源制造"),
    ("国家电网在西藏建设超高压输电线路", ["国家电网", "西藏"], "能源制造"),
    ("隆基绿能通威股份在光伏行业展开价格竞争", ["隆基绿能", "通威股份"], "能源制造"),
    ("中国商飞研制的客机完成首次商业飞行", ["中国商飞"], "能源制造"),
    # 媒体体育
    ("新华社人民日报是中国最主要的官方媒体", ["新华社", "人民日报"], "媒体体育"),
    ("字节跳动旗下今日头条月活超六亿用户", ["字节跳动", "今日头条"], "媒体体育"),
    ("腾讯视频爱奇艺优酷是国内三大视频平台", ["腾讯视频", "爱奇艺", "优酷"], "媒体体育"),
    ("苏炳添在东京奥运会百米半决赛跑出九秒八三", ["苏炳添", "东京"], "媒体体育"),
    ("谷爱凌代表中国队在北京冬奥会上夺得两金", ["谷爱凌", "北京"], "媒体体育"),
    ("梅西加盟迈阿密国际后美职联热度大增", ["梅西", "迈阿密国际"], "媒体体育"),
    ("李娜是第一位赢得大满贯的亚洲网球运动员", ["李娜"], "媒体体育"),
    ("姚明担任中国篮球协会主席推动篮球改革", ["姚明", "中国篮球协会"], "媒体体育"),
    ("郎平卸任中国女排主教练后由蔡斌接任", ["郎平", "蔡斌"], "媒体体育"),
    # 多实体密集
    ("王健林旗下万达集团在成都武汉杭州新开万达广场", ["王健林", "万达集团", "成都", "武汉", "杭州"], "多实体"),
    ("宁德时代与大众汽车宝马集团签署三方战略合作协议", ["宁德时代", "大众汽车", "宝马集团"], "多实体"),
    ("苹果公司将部分产能从中国转移至印度和越南", ["苹果公司", "中国", "印度", "越南"], "多实体"),
    ("张伟从北京大学毕业后加入华为后创立北京智源科技", ["张伟", "北京大学", "华为", "北京"], "多实体"),
    ("李华担任腾讯副总裁期间主导了与京东的战略合作", ["李华", "腾讯", "京东"], "多实体"),
    ("清华大学北京大学复旦大学浙江大学联合申报国家重点实验室", ["清华大学", "北京大学", "复旦大学", "浙江大学"], "多实体"),
    ("马云和马化腾同时出现在北京的全国两会会场", ["马云", "马化腾", "北京"], "多实体"),
    ("高盛摩根大通花旗银行联合为字节跳动提供上市咨询服务", ["高盛", "摩根大通", "花旗银行", "字节跳动"], "多实体"),
    ("中国平安中国人寿太平洋保险三家保险巨头发布年报", ["中国平安", "中国人寿", "太平洋保险"], "多实体"),
    # 简短句
    ("马云退休了", ["马云"], "简短句"),
    ("华为被制裁", ["华为"], "简短句"),
    ("北京下雪了", ["北京"], "简短句"),
    ("腾讯裁员", ["腾讯"], "简短句"),
    ("特斯拉降价", ["特斯拉"], "简短句"),
    ("阿里巴巴上市", ["阿里巴巴"], "简短句"),
    ("李明去上海出差", ["李明", "上海"], "简短句"),
    ("张三在清华大学读书", ["张三", "清华大学"], "简短句"),
    ("小李加入了百度", ["百度"], "简短句"),
    # 无实体
    ("今天天气不错适合出行", [], "无实体"),
    ("这个产品的性价比非常高", [], "无实体"),
    ("会议于下午三点准时开始", [], "无实体"),
    ("请问您需要什么帮助", [], "无实体"),
    ("系统已完成更新请重新登录", [], "无实体"),
    ("目前进展顺利没有问题", [], "无实体"),
    ("价格还在谈判中尚未确定", [], "无实体"),
    ("用户反馈整体比较正面", [], "无实体"),
    ("这项技术目前还不成熟", [], "无实体"),
    ("我们下周开会讨论这个问题", [], "无实体"),
]

BENCH_POOL = [
    "马云在杭州创立了阿里巴巴",
    "李明在北京参加了腾讯的发布会",
    "苹果公司CEO蒂姆·库克访问北京",
    "中国人民银行宣布下调存款准备金率",
    "宁德时代与大众汽车签署战略合作协议",
    "清华大学和北京大学联合举办人工智能峰会",
    "张一鸣离开字节跳动后梁汝波接任CEO职位",
    "特斯拉上海超级工厂第一百万辆整车正式下线",
    "黄河流经青海四川甘肃宁夏内蒙古陕西等九省",
    "王健林旗下万达集团在成都武汉杭州三地新开万达广场",
    "国务院总理李强主持召开常务会议研究部署稳增长相关工作",
    "英伟达CEO黄仁勋在台北宣布新一代AI芯片将于明年量产",
    "中芯国际华虹半导体在上海扩大先进制程芯片产能投资",
    "微软与OpenAI在西雅图举行联合发布会推出新版GPT模型",
    "欧洲央行行长拉加德在法兰克福发表讲话暗示年内停止加息",
    "苏炳添代表中国队参加在巴黎举办的世界田径锦标赛",
    "上海证券交易所与深圳证券交易所联合发布市场互联互通方案",
    "招商银行工商银行建设银行三家银行联合发布绿色金融白皮书",
    "国家发展改革委批复北京至雄安新区高速铁路项目可行性研究报告",
    "中国平安中国人寿太平洋保险三家保险巨头同日发布年报",
    "谷爱凌代表中国队在北京冬奥会自由式滑雪项目中夺得两枚金牌",
    "比亚迪新能源汽车销量连续多月超过特斯拉位居全球第一",
    "字节跳动旗下抖音在欧洲市场面临来自欧盟监管机构的审查",
    "中国商飞研制的C919客机完成首次商业飞行正式投入运营",
    "今天天气不错",
    "系统更新完成请重启",
    "会议准时开始",
    "价格待确认",
    "进展顺利",
]


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def post(url: str, body: dict, timeout: float = 30) -> tuple[dict, float]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        result = json.loads(r.read())
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return result, elapsed_ms


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


def run_basic(base: str, verbose: bool) -> dict:
    """运行所有验证用例，返回结构化结果。"""
    categories: dict[str, dict] = {}
    failures = []
    latencies = []

    for text, expect, cat in BASIC_CASES:
        res, ms = post(f"{base}/extract", {"texts": [text]})
        entities = res["entities"][0]
        missing = [e for e in expect if not any(e in ent for ent in entities)]
        ok = not missing
        latencies.append(ms)

        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0}
        categories[cat]["total"] += 1
        if ok:
            categories[cat]["passed"] += 1
        else:
            failures.append({"text": text, "expect": expect, "got": entities, "missing": missing, "ms": ms})

        if verbose:
            flag = "✓" if ok else f"✗ 缺失:{missing}"
            slow = " ⚠️>200ms" if ms > 200 else ""
            print(f"  [{ms:6.1f}ms{slow}] [{cat}] {text[:40]:<40} {flag}")

    total = len(BASIC_CASES)
    passed = sum(v["passed"] for v in categories.values())
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]

    # 打印分类摘要
    print(f"\n  {'分类':<10} {'通过':>6} {'总数':>6} {'通过率':>8}")
    print(f"  {'-'*36}")
    for cat, s in categories.items():
        rate = s["passed"] / s["total"] * 100
        bar = "█" * int(rate / 10) + "░" * (10 - int(rate / 10))
        print(f"  {cat:<10} {s['passed']:>6} {s['total']:>6}   {bar} {rate:.0f}%")
    print(f"  {'-'*36}")
    print(f"  {'总计':<10} {passed:>6} {total:>6}   {passed/total*100:.1f}%")
    print(f"\n  延迟 p95={p95:.0f}ms  >200ms={sum(1 for l in latencies if l > 200)}/{total}")

    if failures:
        print(f"\n  ── 失败用例 ({len(failures)}) ──")
        for f in failures:
            print(f"  [{f['ms']:.0f}ms] {f['text'][:50]}")
            print(f"         期望包含: {f['missing']}  实际: {f['got']}")

    return {
        "total": total, "passed": passed,
        "categories": categories, "failures": failures,
        "latency_p95": p95,
        "latency_avg": sum(latencies) / len(latencies),
    }


def run_bench(base: str, workers: int, duration: int) -> dict:
    print(f"\n  压测: {workers} 并发，持续 {duration}s")

    ok = 0
    rate_limited = 0
    errors = 0
    times: list[float] = []
    lock = Lock()
    stop_at = time.perf_counter() + duration

    def worker():
        nonlocal ok, rate_limited, errors
        idx = 0
        while time.perf_counter() < stop_at:
            text = BENCH_POOL[idx % len(BENCH_POOL)]
            idx += 1
            try:
                _, ms = post(f"{base}/extract", {"texts": [text]}, timeout=10)
                with lock:
                    ok += 1
                    times.append(ms)
            except urllib.error.HTTPError as e:
                with lock:
                    if e.code == 429:
                        rate_limited += 1
                    else:
                        errors += 1
            except Exception:
                with lock:
                    errors += 1

    import concurrent.futures as cf
    t_start = time.perf_counter()
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(worker) for _ in range(workers)]
        while any(not f.done() for f in futures):
            elapsed = time.perf_counter() - t_start
            if elapsed < duration:
                with lock:
                    cur_ok = ok
                print(f"  [{elapsed:.0f}s/{duration}s] 已完成 {cur_ok} 请求...", end="\r")
            time.sleep(5)
    total_s = time.perf_counter() - t_start

    total = ok + rate_limited + errors
    qps = ok / total_s
    times.sort()
    p50 = times[int(len(times) * 0.50)] if times else 0
    p95 = times[int(len(times) * 0.95)] if times else 0
    p99 = times[min(int(len(times) * 0.99), len(times) - 1)] if times else 0
    over = sum(1 for t in times if t > 200)

    print(f"\n  总请求:{total}  成功:{ok}  限流:{rate_limited}  异常:{errors}")
    print(f"  QPS: {qps:.1f} req/s  耗时: {total_s:.1f}s")
    print(f"  延迟(ms): min={times[0]:.0f}  p50={p50:.0f}  p95={p95:.0f}  p99={p99:.0f}  max={times[-1]:.0f}")
    print(f"  >200ms: {over}/{len(times)} ({over/len(times)*100:.1f}%)")

    return {
        "total": total, "ok": ok, "rate_limited": rate_limited, "errors": errors,
        "qps": qps, "duration": total_s,
        "p50": p50, "p95": p95, "p99": p99,
        "over_200ms_pct": over / len(times) * 100 if times else 0,
    }


def save_report(results: dict, path: str):
    """将所有服务的测试结果写入 JSON 报告。"""
    report = {
        "generated_at": datetime.now().isoformat(),
        "services": results,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {path}")


def run_service(base: str, workers: int, duration: int, verbose: bool, bench_only: bool) -> dict:
    result = {}
    if not bench_only:
        print(f"\n--- 基础验证 ({len(BASIC_CASES)} 条) ---")
        result["basic"] = run_basic(base, verbose)

        print("\n--- 类型过滤 ---")
        text = "李强在北京主持了中国人民银行的新闻发布会"
        for types in [["PER"], ["LOC"], ["ORG"], ["PER", "LOC"], ["PER", "ORG"]]:
            res, ms = post(f"{base}/extract", {"texts": [text], "types": types})
            print(f"  [{ms:6.1f}ms] types={types} → {res['entities'][0]}")

        print("\n--- 边界情况 ---")
        for name, text in [
            ("空字符串", ""), ("纯数字", "12345678"),
            ("纯英文", "Apple CEO Tim Cook visited Beijing"),
            ("中英混合", "苹果Apple在上海Shanghai开设了新门店"),
            ("单字", "京"), ("重复实体", "马云说马云已经退休"),
            ("超长文本", "李明在北京工作。" * 200),
        ]:
            try:
                res, ms = post(f"{base}/extract", {"texts": [text]})
                print(f"  [{ms:6.1f}ms] {name}: {res['entities'][0]}")
            except Exception as e:
                print(f"  {name}: 异常 {e}")

    print("\n--- 压测 ---")
    result["bench"] = run_bench(base, workers, duration)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8002")
    parser.add_argument("--concurrent", type=int, default=10)
    parser.add_argument("--duration", type=int, default=180, help="压测持续秒数，默认 180s")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--all", action="store_true", help="依次测试所有服务")
    parser.add_argument("--bench", action="store_true", help="只跑压测")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示每条用例详情")
    parser.add_argument("--report", default="report.json", help="报告输出路径，默认 report.json")
    args = parser.parse_args()

    all_results = {}

    if args.all:
        for name, url in SERVICES.items():
            print(f"\n{'='*52}")
            print(f"  服务: {name}  ({url})")
            print(f"{'='*52}")
            if not args.no_wait:
                wait_healthy(url)
            all_results[name] = run_service(url, args.concurrent, args.duration, args.verbose, args.bench)
    else:
        base = args.url.rstrip("/")
        if not args.no_wait:
            wait_healthy(base)
        all_results["target"] = run_service(base, args.concurrent, args.duration, args.verbose, args.bench)

    save_report(all_results, args.report)

    # 多服务对比摘要
    if args.all and not args.bench and len(all_results) > 1:
        print(f"\n{'='*52}")
        print("  对比摘要")
        print(f"{'='*52}")
        print(f"  {'服务':<12} {'通过率':>8} {'p95(ms)':>10} {'QPS':>10} {'>200ms':>8}")
        print(f"  {'-'*52}")
        for name, r in all_results.items():
            b = r.get("basic", {})
            bench = r.get("bench", {})
            pass_rate = b.get("passed", 0) / b.get("total", 1) * 100 if b else 0
            print(f"  {name:<12} {pass_rate:>7.1f}% {b.get('latency_p95',0):>9.0f}ms "
                  f"{bench.get('qps',0):>9.1f} {bench.get('over_200ms_pct',0):>7.1f}%")

    print("\n完成")


if __name__ == "__main__":
    main()
