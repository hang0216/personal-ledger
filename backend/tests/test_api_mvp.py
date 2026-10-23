"""个人记账本 — MVP API 黑盒测试脚本。

依据：spec.md v1.3、docs/api-design.md v1.1。
目标：对运行中的后端（默认 http://127.0.0.1:8000）执行端到端黑盒测试，覆盖
      账单 CRUD、分类管理、月度统计、金额边界、非法月份、无效分类、空数据、CORS 联调。

月份隔离设计（关键）：
      2001-02 统计专用月 —— 只放 5 条已知种子数据，用于校验汇总数值；
      2001-06 噪音月 —— 放 CRUD / 金额边界 / 备注边界等用例产生的记录，避免污染统计月；
      2001-03 空数据月；2001-05 负结余月；2000-12 与 2001-01 用于跨年边界。
      全部测试数据带 TMP 前缀并保留月份，脚本结束（含异常）自动清理。

用法：python backend/tests/test_api_mvp.py
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"
MONTH = "2001-02"          # 统计专用月：仅放 5 条已知种子数据
NOISE_MONTH = "2001-06"    # CRUD / 边界噪音数据月（与统计月隔离，避免污染汇总）
EMPTY_MONTH = "2001-03"    # 空数据月
NEG_MONTH = "2001-05"      # 负结余月
NOISE_DATE = "2001-06-05"  # 噪音数据默认业务日期
NOISE_DATE2 = "2001-06-06"  # 编辑用例目标日期
NOISE_SAME_DAY = "2001-06-07"  # 排序用例同日日期
STAMP = str(int(time.time()))

CAT_IN = f"TMP收入_{STAMP}"
CAT_EX_A = f"TMP支出A_{STAMP}"
CAT_EX_B = f"TMP支出B_{STAMP}"
CAT_SAME = f"TMP同名_{STAMP}"

results = []
created_tx = []
created_cats = []


def call(method, path, body=None, headers=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, data) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8")), dict(resp.headers)
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = raw
        return err.code, payload, dict(err.headers)


def record(cid, goal, inp, expected, actual, passed):
    results.append(
        {"id": cid, "goal": goal, "input": inp, "expected": expected, "actual": actual, "passed": bool(passed)}
    )
    print(("[PASS] " if passed else "[FAIL] ") + cid + " | " + actual)
    return bool(passed)


def expect(cid, goal, inp, expected, status, payload, exp_http, exp_code, exp_msg=None):
    code = payload.get("code") if isinstance(payload, dict) else None
    msg = payload.get("message") if isinstance(payload, dict) else None
    ok = status == exp_http and code == exp_code and (exp_msg is None or msg == exp_msg)
    actual = f"HTTP {status}, code={code}, message={msg}"
    return record(cid, goal, inp, expected, actual, ok)


def code_of(payload):
    return payload.get("code") if isinstance(payload, dict) else None


def data_of(payload):
    return payload.get("data") if isinstance(payload, dict) else None


# ---------------------------------------------------------------- 前置检查
RESERVED = ["2000-12", "2001-01", MONTH, EMPTY_MONTH, "2001-04", NEG_MONTH, NOISE_MONTH]
busy = []
for m in RESERVED:
    st_, pl_, _ = call("GET", f"/transactions?month={m}")
    if not (st_ == 200 and data_of(pl_) == []):
        busy.append(m)
record(
    "P-00",
    "全部保留月份未被业务数据占用（保证测试可复现、可清理）",
    "GET /api/transactions?month=" + ",".join(RESERVED),
    "全部 200 且 data=[]",
    f"被占用的月份={busy or '无'}",
    not busy,
)
if busy:
    print(f"保留月份非空 {busy}，终止测试以避免污染。")
    sys.exit(1)

try:
    # ============================================================ 分类管理
    st, pl, _ = call("GET", "/categories")
    cats = data_of(pl) or []
    types = [c["type"] for c in cats]
    sorted_ok = types == sorted(types, key=lambda t: (t != "expense",)) and len(cats) >= 13
    record(
        "C-01",
        "分类列表全量查询 + 排序（type 升序、expense 组在前）",
        "GET /api/categories",
        "200/0，数组，含 13 条预置分类，expense 组在前",
        f"HTTP {st}, code={code_of(pl)}, 条数={len(cats)}, 首条 type={types[0] if types else None}, 末条 type={types[-1] if types else None}",
        st == 200 and code_of(pl) == 0 and sorted_ok,
    )

    st, pl, _ = call("GET", "/categories?type=income")
    income_cats = data_of(pl) or []
    record(
        "C-02",
        "按 type 过滤分类（income）",
        "GET /api/categories?type=income",
        "200/0，5 条（预置收入分类）",
        f"HTTP {st}, code={code_of(pl)}, 条数={len(income_cats)}, 全为 income={all(c['type'] == 'income' for c in income_cats)}",
        st == 200 and len(income_cats) == 5 and all(c["type"] == "income" for c in income_cats),
    )

    st, pl, _ = call("GET", "/categories?type=expense")
    expense_cats = data_of(pl) or []
    record(
        "C-03",
        "按 type 过滤分类（expense）",
        "GET /api/categories?type=expense",
        "200/0，8 条（预置支出分类）",
        f"HTTP {st}, code={code_of(pl)}, 条数={len(expense_cats)}",
        st == 200 and len(expense_cats) == 8,
    )

    st, pl, _ = call("GET", "/categories?type=bad")
    expect(
        "C-04",
        "分类查询 type 非法",
        "GET /api/categories?type=bad",
        "1001 / HTTP 400 参数不合法",
        st,
        pl,
        400,
        1001,
        "参数不合法",
    )

    st, pl, _ = call("POST", "/categories", {"name": f"  {CAT_EX_A}  ", "type": "expense"})
    cat_a = data_of(pl) or {}
    if st == 200:
        created_cats.append(cat_a.get("id"))
    record(
        "C-05",
        "新增支出分类（名称首尾空格应被去除）",
        f"POST /api/categories  body={{name:'  {CAT_EX_A}  ', type:'expense'}}",
        "200/0，name 去空格后写入",
        f"HTTP {st}, code={code_of(pl)}, id={cat_a.get('id')}, name={cat_a.get('name')!r}",
        st == 200 and cat_a.get("name") == CAT_EX_A,
    )

    st, pl, _ = call("POST", "/categories", {"name": CAT_IN, "type": "income"})
    cat_i = data_of(pl) or {}
    if st == 200:
        created_cats.append(cat_i.get("id"))
    record(
        "C-06",
        "新增收入分类",
        f"POST /api/categories  body={{name:'{CAT_IN}', type:'income'}}",
        "200/0，返回 id/name/type",
        f"HTTP {st}, code={code_of(pl)}, id={cat_i.get('id')}, type={cat_i.get('type')}",
        st == 200 and cat_i.get("type") == "income",
    )

    st, pl, _ = call("POST", "/categories", {"name": CAT_IN, "type": "income"})
    expect(
        "C-07",
        "同类型下分类重名（E-09）",
        f"POST /api/categories  body={{name:'{CAT_IN}', type:'income'}}（重复）",
        "1009 / HTTP 409 该分类已存在",
        st,
        pl,
        409,
        1009,
        "该分类已存在",
    )

    st, pl, _ = call("POST", "/categories", {"name": "   ", "type": "expense"})
    expect(
        "C-08",
        "分类名称为空（E-10）",
        "POST /api/categories  body={name:'   ', type:'expense'}",
        "1001 / HTTP 400 分类名称不合法",
        st,
        pl,
        400,
        1001,
        "分类名称不合法",
    )

    st, pl, _ = call("POST", "/categories", {"name": "超" * 21, "type": "expense"})
    expect(
        "C-09",
        "分类名称超长 21 码点（E-10）",
        "POST /api/categories  body={name:'超'*21, type:'expense'}",
        "1001 / HTTP 400 分类名称不合法",
        st,
        pl,
        400,
        1001,
        "分类名称不合法",
    )

    st1, pl1, _ = call("POST", "/categories", {"name": CAT_SAME, "type": "expense"})
    st2, pl2, _ = call("POST", "/categories", {"name": CAT_SAME, "type": "income"})
    for s, p in ((st1, pl1), (st2, pl2)):
        if s == 200:
            created_cats.append((data_of(p) or {}).get("id"))
    record(
        "C-10",
        "不同类型下同名分类允许（唯一约束范围为 (name,type)）",
        f"POST /api/categories  同名 '{CAT_SAME}' 分别 type=expense / income",
        "两次均 200/0",
        f"expense: HTTP {st1}/code {code_of(pl1)}；income: HTTP {st2}/code {code_of(pl2)}",
        st1 == 200 and st2 == 200 and code_of(pl1) == 0 and code_of(pl2) == 0,
    )

    st, pl, _ = call("POST", "/categories", {"name": "非法类型", "type": "other"})
    record(
        "C-11",
        "新增分类 type 非法",
        "POST /api/categories  body={name:'非法类型', type:'other'}",
        "1001 / HTTP 400",
        f"HTTP {st}, code={code_of(pl)}, message={pl.get('message') if isinstance(pl, dict) else None}",
        st == 400 and code_of(pl) == 1001,
    )

    st, pl, _ = call("DELETE", "/categories/999999")
    expect(
        "C-12",
        "删除不存在的分类（E-17）",
        "DELETE /api/categories/999999",
        "1007 / HTTP 404 分类不存在",
        st,
        pl,
        404,
        1007,
        "分类不存在",
    )

    # 建立一条引用 cat_a 的账单，用于验证「被引用分类不可删除」
    st, pl, _ = call(
        "POST",
        "/transactions",
        {"amount": 30.00, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE, "note": "引用测试"},
    )
    ref_tx = data_of(pl) or {}
    if st == 200:
        created_tx.append(ref_tx.get("id"))

    st, pl, _ = call("DELETE", f"/categories/{cat_a.get('id')}")
    expect(
        "C-13",
        "删除存在账单引用的分类（E-11，应用层 + RESTRICT 双保险）",
        f"DELETE /api/categories/{cat_a.get('id')}（该分类已被 1 条账单引用）",
        "1010 / HTTP 409 该分类下存在记录，无法删除",
        st,
        pl,
        409,
        1010,
        "该分类下存在记录，无法删除",
    )

    st, pl, _ = call("POST", "/categories", {"name": f"TMP可删_{STAMP}", "type": "expense"})
    del_cat = data_of(pl) or {}
    st2, pl2, _ = call("DELETE", f"/categories/{del_cat.get('id')}")
    record(
        "C-14",
        "删除无引用的分类",
        f"POST 新建 '{del_cat.get('name')}' 后 DELETE /api/categories/{del_cat.get('id')}",
        "新建 200/0；删除 200/0，data=null",
        f"新建 HTTP {st}/code {code_of(pl)}；删除 HTTP {st2}/code {code_of(pl2)}, data={data_of(pl2)}",
        st == 200 and st2 == 200 and code_of(pl2) == 0,
    )

    # ============================================================ 账单 CRUD（噪音月）
    st, pl, _ = call(
        "POST",
        "/transactions",
        {"amount": 33.33, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE, "note": "午餐"},
    )
    tx = data_of(pl) or {}
    if st == 200:
        created_tx.append(tx.get("id"))
    record(
        "T-01",
        "新增账单（正常支出）",
        f"POST /api/transactions  body={{amount:33.33, type:expense, category_id:{cat_a.get('id')}, date:'{NOISE_DATE}', note:'午餐'}}",
        f"200/0，amount=33.33，date={NOISE_DATE}，字段回显正确（元）",
        f"HTTP {st}, code={code_of(pl)}, data={json.dumps(tx, ensure_ascii=False)}",
        st == 200 and tx.get("amount") == 33.33 and tx.get("type") == "expense" and tx.get("date") == NOISE_DATE,
    )

    st, pl, _ = call("GET", f"/transactions?month={NOISE_MONTH}")
    lst = data_of(pl) or []
    record(
        "T-02",
        "按月查询账单列表",
        f"GET /api/transactions?month={NOISE_MONTH}",
        "200/0，data 为数组且包含刚新增记录",
        f"HTTP {st}, code={code_of(pl)}, 条数={len(lst)}, 含 id={tx.get('id')}: {any(r.get('id') == tx.get('id') for r in lst)}",
        st == 200 and isinstance(lst, list) and any(r.get("id") == tx.get("id") for r in lst),
    )

    record(
        "T-07",
        "列表项不含 category_name（字段严格对齐 spec §6.2）",
        f"GET /api/transactions?month={NOISE_MONTH}",
        "数组元素仅含 id/amount/type/category_id/date/note",
        f"实际字段={sorted(lst[0].keys()) if lst else 'N/A'}",
        bool(lst) and "category_name" not in lst[0] and set(lst[0].keys()) == {"id", "amount", "type", "category_id", "date", "note"},
    )

    st, pl, _ = call(
        "PUT",
        f"/transactions/{tx.get('id')}",
        {"amount": 45.00, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE2, "note": "午餐（改）"},
    )
    upd = data_of(pl) or {}
    record(
        "T-03",
        "编辑账单（PUT 全量覆盖）",
        f"PUT /api/transactions/{tx.get('id')}  body={{amount:45.00, date:'{NOISE_DATE2}', note:'午餐（改）'}}",
        f"200/0，amount=45.00、date={NOISE_DATE2}、note 已更新",
        f"HTTP {st}, code={code_of(pl)}, data={json.dumps(upd, ensure_ascii=False)}",
        st == 200 and upd.get("amount") == 45.00 and upd.get("date") == NOISE_DATE2 and upd.get("note") == "午餐（改）",
    )

    st, pl, _ = call(
        "PUT",
        "/transactions/999999",
        {"amount": 1.00, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE, "note": None},
    )
    expect(
        "T-04",
        "编辑不存在的记录（E-12）",
        "PUT /api/transactions/999999",
        "1008 / HTTP 404 记录不存在",
        st,
        pl,
        404,
        1008,
        "记录不存在",
    )

    st, pl, _ = call("DELETE", "/transactions/999999")
    expect(
        "T-06",
        "删除不存在的记录（E-12）",
        "DELETE /api/transactions/999999",
        "1008 / HTTP 404 记录不存在",
        st,
        pl,
        404,
        1008,
        "记录不存在",
    )

    # 排序：两条同日记录，id 大者应在前
    st1, pl1, _ = call("POST", "/transactions", {"amount": 11.00, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_SAME_DAY, "note": "排序A"})
    st2, pl2, _ = call("POST", "/transactions", {"amount": 22.00, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_SAME_DAY, "note": "排序B"})
    id1, id2 = (data_of(pl1) or {}).get("id"), (data_of(pl2) or {}).get("id")
    created_tx += [id1, id2]
    st, pl, _ = call("GET", f"/transactions?month={NOISE_MONTH}")
    lst = data_of(pl) or []
    order_ok = True
    prev = None
    for r in lst:
        key = (r["date"], r["id"])
        if prev is not None and key > prev:
            order_ok = False
        prev = key
    same_day = [r["id"] for r in lst if r["date"] == NOISE_SAME_DAY]
    record(
        "T-08",
        "列表排序 date DESC, id DESC（R-12）",
        f"GET /api/transactions?month={NOISE_MONTH}（含 2 条同日记录 id={id1}/{id2}）",
        "整体按 date 降序；同日按 id 降序",
        f"整体降序={order_ok}, 同日 id 顺序={same_day}",
        order_ok and same_day == [id2, id1],
    )

    st, pl, _ = call("POST", "/transactions", {"type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE})
    record(
        "T-09",
        "新增账单缺少必填字段 amount（E-03）",
        "POST /api/transactions  body={type, category_id, date}（无 amount）",
        "1001 / HTTP 400 参数不合法",
        f"HTTP {st}, code={code_of(pl)}, message={pl.get('message') if isinstance(pl, dict) else None}",
        st == 400 and code_of(pl) == 1001,
    )

    st, pl, _ = call("POST", "/transactions", {"amount": 1.00, "type": "other", "category_id": cat_a.get("id"), "date": NOISE_DATE})
    record(
        "T-10",
        "新增账单 type 非法",
        "POST /api/transactions  body={amount:1.00, type:'other', ...}",
        "1001 / HTTP 400 参数不合法",
        f"HTTP {st}, code={code_of(pl)}, message={pl.get('message') if isinstance(pl, dict) else None}",
        st == 400 and code_of(pl) == 1001,
    )

    st, pl, _ = call("POST", "/transactions", {"amount": 1.00, "type": "expense", "category_id": 999999, "date": NOISE_DATE})
    expect(
        "T-11",
        "新增账单引用不存在的分类（E-05）",
        "POST /api/transactions  body={category_id:999999, ...}",
        "1007 / HTTP 404 分类不存在",
        st,
        pl,
        404,
        1007,
        "分类不存在",
    )

    st, pl, _ = call("POST", "/transactions", {"amount": 1.00, "type": "income", "category_id": cat_a.get("id"), "date": NOISE_DATE})
    expect(
        "T-12",
        "新增账单类型与分类类型不一致（E-04）",
        f"POST /api/transactions  body={{type:'income', category_id:{cat_a.get('id')}(expense)}}",
        "1006 / HTTP 400 分类类型与收支类型不一致",
        st,
        pl,
        400,
        1006,
        "分类类型与收支类型不一致",
    )

    body_bad = {"amount": 0, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE, "note": None}
    stp, plp, _ = call("POST", "/transactions", body_bad)
    stu, plu, _ = call("PUT", f"/transactions/{tx.get('id')}", body_bad)
    record(
        "T-13",
        "POST 与 PUT 复用同一校验（AC-24：同输入同错误码）",
        "POST 与 PUT 均提交 amount=0",
        "两者返回相同 code（1002）",
        f"POST → HTTP {stp}/code {code_of(plp)}；PUT → HTTP {stu}/code {code_of(plu)}",
        code_of(plp) == code_of(plu) == 1002,
    )

    st, pl, _ = call("DELETE", f"/transactions/{tx.get('id')}")
    record(
        "T-05",
        "删除账单",
        f"DELETE /api/transactions/{tx.get('id')}",
        "200/0，data=null",
        f"HTTP {st}, code={code_of(pl)}, data={data_of(pl)}",
        st == 200 and code_of(pl) == 0 and data_of(pl) is None,
    )
    if tx.get("id") in created_tx:
        created_tx.remove(tx.get("id"))

    # ============================================================ 金额边界（噪音月）
    cases_amt = [
        ("A-01", 0, 1002, "金额为 0（E-01）", "400/1002 金额不合法"),
        ("A-02", -5, 1002, "金额为负（E-01）", "400/1002 金额不合法"),
        ("A-03", 0.001, 1002, "金额 3 位小数（E-01）", "400/1002 金额不合法"),
        ("A-04", "abc", 1002, "金额非数字（E-01）", "400/1002 金额不合法"),
        ("A-07", 100000000, 1003, "金额超上限 100,000,000（E-02）", "400/1003 金额超出允许范围"),
        ("A-08a", "__MISSING__", 1001, "amount 字段缺失（E-03 必填缺失）", "400/1001 参数不合法"),
        ("A-08b", None, 1002, "amount 显式传 null（E-01 金额为空）", "400/1002 金额不合法"),
    ]
    for cid, amt, exp_code, goal, exp_desc in cases_amt:
        body = {"type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE, "note": None}
        shown = amt
        if amt == "__MISSING__":
            shown = "<字段缺失>"
        else:
            body["amount"] = amt
        st, pl, _ = call("POST", "/transactions", body)
        record(
            cid,
            goal,
            f"POST /api/transactions  body={{amount:{shown}, ...}}",
            exp_desc,
            f"HTTP {st}, code={code_of(pl)}, message={pl.get('message') if isinstance(pl, dict) else None}",
            st == 400 and code_of(pl) == exp_code,
        )

    st, pl, _ = call("POST", "/transactions", {"amount": 99999999.99, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE, "note": "上限"})
    up = data_of(pl) or {}
    if st == 200:
        created_tx.append(up.get("id"))
    record(
        "A-06",
        "金额取上限 99,999,999.99 应成功",
        "POST /api/transactions  body={amount:99999999.99, ...}",
        "200/0，amount 回显 99999999.99",
        f"HTTP {st}, code={code_of(pl)}, amount={up.get('amount')}",
        st == 200 and up.get("amount") == 99999999.99,
    )

    st, pl, _ = call("POST", "/transactions", {"amount": 33.33, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE, "note": "精度"})
    prec = data_of(pl) or {}
    if st == 200:
        created_tx.append(prec.get("id"))
    record(
        "A-05",
        "金额元/分转换精度（AC-20：33.33 → 3333 分 → 33.33）",
        "POST /api/transactions  body={amount:33.33, ...}",
        "200/0，amount 精确回显 33.33（无浮点误差）",
        f"HTTP {st}, amount={prec.get('amount')!r}",
        st == 200 and prec.get("amount") == 33.33,
    )

    # ============================================================ 日期与备注
    for cid, d, goal in (("D-01", "2001-2-5", "日期非补零格式（R-19）"), ("D-02", "1999-12-31", "日期早于 2000-01-01（R-24）"), ("D-03", "2099-01-01", "日期晚于今天")):
        st, pl, _ = call("POST", "/transactions", {"amount": 1.00, "type": "expense", "category_id": cat_a.get("id"), "date": d, "note": None})
        expect(
            cid,
            goal,
            f"POST /api/transactions  body={{date:'{d}', ...}}",
            "1004 / HTTP 400 日期不合法",
            st,
            pl,
            400,
            1004,
            "日期不合法",
        )

    st, pl, _ = call("POST", "/transactions", {"amount": 1.00, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE, "note": "备" * 101})
    expect(
        "N-01",
        "备注超长 101 码点（E-08）",
        "POST /api/transactions  body={note:'备'*101, ...}",
        "1001 / HTTP 400 备注长度超限",
        st,
        pl,
        400,
        1001,
        "备注长度超限",
    )

    st, pl, _ = call("POST", "/transactions", {"amount": 1.00, "type": "expense", "category_id": cat_a.get("id"), "date": NOISE_DATE, "note": "备" * 100})
    note100 = data_of(pl) or {}
    if st == 200:
        created_tx.append(note100.get("id"))
    record(
        "N-02",
        "备注恰好 100 码点应成功",
        "POST /api/transactions  body={note:'备'*100, ...}",
        "200/0",
        f"HTTP {st}, code={code_of(pl)}, note 长度={len(note100.get('note') or '')}",
        st == 200 and len(note100.get("note") or "") == 100,
    )

    # ============================================================ 非法月份
    for cid, path, goal in (
        ("M-01", "/transactions?month=2026-13", "账单列表月份 13 非法（R-09）"),
        ("M-02", "/transactions?month=2026-1", "账单列表月份非补零非法（R-09）"),
        ("M-03", "/reports/monthly?month=2026-13", "报表月份 13 非法（E-07）"),
        ("M-04", "/reports/monthly?month=abc", "报表月份格式非法（E-07）"),
    ):
        st, pl, _ = call("GET", path)
        expect(cid, goal, f"GET /api{path}", "1005 / HTTP 400 月份不合法", st, pl, 400, 1005, "月份不合法")

    # ============================================================ 月度统计（统计月：仅 5 条种子）
    st, pl, _ = call("POST", "/categories", {"name": CAT_EX_B, "type": "expense"})
    cat_b = data_of(pl) or {}
    if st == 200:
        created_cats.append(cat_b.get("id"))

    seeds = [
        (100.00, "income", cat_i.get("id"), "2001-02-01", "工资"),
        (200.00, "income", cat_i.get("id"), "2001-02-02", "兼职"),
        (30.00, "expense", cat_a.get("id"), "2001-02-03", "餐饮"),
        (70.00, "expense", cat_a.get("id"), "2001-02-04", "餐饮"),
        (100.00, "expense", cat_b.get("id"), "2001-02-05", "购物"),
    ]
    for amt, ptype, cid_, d, note in seeds:
        s, p, _ = call("POST", "/transactions", {"amount": amt, "type": ptype, "category_id": cid_, "date": d, "note": note})
        if s == 200:
            created_tx.append((data_of(p) or {}).get("id"))

    st, pl, _ = call("GET", f"/reports/monthly?month={MONTH}")
    rep = data_of(pl) or {}
    record(
        "R-01",
        "月度收入总额（spec §7.6）",
        f"GET /api/reports/monthly?month={MONTH}",
        "total_income = 300.00",
        f"HTTP {st}, total_income={rep.get('total_income')}",
        st == 200 and rep.get("total_income") == 300.00,
    )
    record(
        "R-02",
        "月度支出总额（spec §7.6）",
        f"GET /api/reports/monthly?month={MONTH}",
        "total_expense = 200.00",
        f"total_expense={rep.get('total_expense')}",
        rep.get("total_expense") == 200.00,
    )
    record(
        "R-03",
        "月度结余 = 收入 − 支出（spec §7.6）",
        f"GET /api/reports/monthly?month={MONTH}",
        "balance = 100.00",
        f"balance={rep.get('balance')}（= {rep.get('total_income')} - {rep.get('total_expense')}）",
        rep.get("balance") == 100.00,
    )
    detail = rep.get("expense_by_category") or []
    detail_ok = (
        len(detail) == 2
        and {d.get("category_name") for d in detail} == {CAT_EX_A, CAT_EX_B}
        and all(d.get("amount") == 100.00 for d in detail)
        and all(d.get("percentage") == 50.00 for d in detail)
        and [d.get("amount") for d in detail] == sorted([d.get("amount") for d in detail], reverse=True)
    )
    record(
        "R-04",
        "支出分类统计与占比（后端唯一计算，按 amount 降序，R-21）",
        f"GET /api/reports/monthly?month={MONTH}",
        "2 项，各 100.00 / 50.00%，按金额降序，percentage 之和 = 100.00",
        f"明细={json.dumps(detail, ensure_ascii=False)}, 占比之和={sum(d.get('percentage', 0) for d in detail)}",
        detail_ok,
    )
    record(
        "R-05",
        "占比不出现 NaN 且合计落在 99.99–100.01（R-10）",
        f"GET /api/reports/monthly?month={MONTH}",
        "合计 ∈ [99.99, 100.01]",
        f"合计={sum(d.get('percentage', 0) for d in detail)}",
        99.99 <= sum(d.get("percentage", 0) for d in detail) <= 100.01,
    )

    # 负结余月
    s, p, _ = call("POST", "/transactions", {"amount": 50.00, "type": "expense", "category_id": cat_a.get("id"), "date": "2001-05-10", "note": "负结余"})
    if s == 200:
        created_tx.append((data_of(p) or {}).get("id"))
    st, pl, _ = call("GET", f"/reports/monthly?month={NEG_MONTH}")
    neg = data_of(pl) or {}
    record(
        "R-06",
        "负结余正确返回（AC-22、R-22）",
        f"GET /api/reports/monthly?month={NEG_MONTH}（仅 50.00 支出）",
        "total_income=0.00, total_expense=50.00, balance=-50.00",
        f"income={neg.get('total_income')}, expense={neg.get('total_expense')}, balance={neg.get('balance')}",
        neg.get("balance") == -50.00 and neg.get("total_expense") == 50.00 and neg.get("total_income") == 0.00,
    )

    # 跨年边界：2000-12-31 与 2001-01-01 分属两月（AC-17）
    for amt, d in ((10.00, "2000-12-31"), (20.00, "2001-01-01")):
        s, p, _ = call("POST", "/transactions", {"amount": amt, "type": "income", "category_id": cat_i.get("id"), "date": d, "note": "跨年"})
        if s == 200:
            created_tx.append((data_of(p) or {}).get("id"))
    st1, pl1, _ = call("GET", "/reports/monthly?month=2000-12")
    st2, pl2, _ = call("GET", "/reports/monthly?month=2001-01")
    d1, d2 = data_of(pl1) or {}, data_of(pl2) or {}
    record(
        "R-07",
        "跨年月份区间不混入相邻年份（AC-17、R-05）",
        "2000-12-31 记 10.00；2001-01-01 记 20.00，分别查询 2000-12 / 2001-01",
        "2000-12: income=10.00；2001-01: income=20.00",
        f"2000-12 income={d1.get('total_income')}；2001-01 income={d2.get('total_income')}",
        d1.get("total_income") == 10.00 and d2.get("total_income") == 20.00,
    )

    # 空数据
    st, pl, _ = call("GET", f"/reports/monthly?month={EMPTY_MONTH}")
    emp = data_of(pl) or {}
    record(
        "E-01",
        "空月份报表（E-13：正常返回 0 值）",
        f"GET /api/reports/monthly?month={EMPTY_MONTH}",
        "200/0，三项为 0.00，expense_by_category=[]",
        f"HTTP {st}, code={code_of(pl)}, data={json.dumps(emp, ensure_ascii=False)}",
        st == 200 and code_of(pl) == 0 and emp.get("total_income") == 0.00 and emp.get("total_expense") == 0.00 and emp.get("balance") == 0.00 and emp.get("expense_by_category") == [],
    )
    st, pl, _ = call("GET", f"/transactions?month={EMPTY_MONTH}")
    record(
        "E-02",
        "空月份账单列表（E-13、AC-26：data 恒为数组）",
        f"GET /api/transactions?month={EMPTY_MONTH}",
        "200/0，data=[]",
        f"HTTP {st}, code={code_of(pl)}, data={json.dumps(data_of(pl), ensure_ascii=False)}",
        st == 200 and code_of(pl) == 0 and data_of(pl) == [],
    )

    # 互斥筛选
    st, pl, _ = call("GET", f"/transactions?month={NOISE_MONTH}&type=income&category_id={cat_a.get('id')}")
    record(
        "F-01",
        "互斥筛选：type 与 category_id 矛盾（AC-27 / R-03）",
        f"GET /api/transactions?month={NOISE_MONTH}&type=income&category_id={cat_a.get('id')}(expense)",
        "200/0，data=[]（不返回 1006/1007）",
        f"HTTP {st}, code={code_of(pl)}, data={json.dumps(data_of(pl), ensure_ascii=False)}",
        st == 200 and code_of(pl) == 0 and data_of(pl) == [],
    )
    st, pl, _ = call("GET", f"/transactions?month={NOISE_MONTH}&category_id=999999")
    record(
        "F-02",
        "category_id 指向不存在分类（不校验存在性，返回空数组）",
        f"GET /api/transactions?month={NOISE_MONTH}&category_id=999999",
        "200/0，data=[]",
        f"HTTP {st}, code={code_of(pl)}, data={json.dumps(data_of(pl), ensure_ascii=False)}",
        st == 200 and data_of(pl) == [],
    )

    # ============================================================ 前后端联调（CORS）
    st, pl, hdrs = call("GET", "/health", headers={"Origin": "http://localhost:5173"})
    acao = hdrs.get("access-control-allow-origin")
    record(
        "I-01",
        "开发环境 CORS：允许前端源 http://localhost:5173（spec §8）",
        "GET /api/health  Header: Origin: http://localhost:5173",
        "响应头含 access-control-allow-origin = http://localhost:5173",
        f"HTTP {st}, access-control-allow-origin={acao!r}",
        st == 200 and acao == "http://localhost:5173",
    )
    st, pl, hdrs = call("GET", "/health", headers={"Origin": "http://evil.example.com"})
    record(
        "I-02",
        "非白名单源不返回 CORS 许可",
        "GET /api/health  Header: Origin: http://evil.example.com",
        "响应头不含 access-control-allow-origin",
        f"HTTP {st}, access-control-allow-origin={hdrs.get('access-control-allow-origin')!r}",
        hdrs.get("access-control-allow-origin") is None,
    )

finally:
    # ============================================================ 清理
    for tid in created_tx:
        call("DELETE", f"/transactions/{tid}")
    for cid_ in created_cats:
        call("DELETE", f"/categories/{cid_}")

passed = sum(1 for r in results if r["passed"])
failed = [r for r in results if not r["passed"]]

print("\n===== 汇总 =====")
print(f"总用例：{len(results)}，通过：{passed}，失败：{len(failed)}")
for r in failed:
    print(f"  FAIL {r['id']} | 预期：{r['expected']} | 实际：{r['actual']}")

dump = {"total": len(results), "passed": passed, "failed": len(failed), "results": results}
with open("test_results.json", "w", encoding="utf-8") as fh:
    json.dump(dump, fh, ensure_ascii=False, indent=2)
print("结果已写入 test_results.json")

sys.exit(0 if not failed else 2)