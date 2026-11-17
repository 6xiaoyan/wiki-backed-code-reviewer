# 静态安全代码审查报告 — 实验 01 / A 组（无额外规范）/ run r01

- MODEL_LABEL：`qwen-3.8-flash-next`　RUN_ID：`r01`
- 输入目录（唯一代码输入，只读）：`D:/ai_share/langgraph/benchmark-data/pygoat-baseline/inputs/experiment-01/pygoat`
- 源码提交：`2fb0c600245f50670e8b9233c784afe61e8b340b`
- 审查方式：**仅静态分析**。逐段阅读 Python/HTML 模板/JavaScript/配置与子应用源码，未安装依赖、未启动应用、未执行任何测试或利用代码、未调用扫描器、未联网检索。
- 因此本报告中的“可导致代码执行/可绕过”等结论均基于数据流与缺失校验的源码推理，**未经运行验证**。

## 概览

- 确认发现：**47** 项（critical 15、high 22、medium 10、low 0）
- 未确认候选：**9** 项（不计入评分，见 `uncertain-findings.json`）
- 涉及文件：13 个
- 按严重度排序的索引：

| 编号 | CWE | 严重度 | 位置 |
| --- | --- | --- | --- |
| finding-040 | CWE-502 | critical | `dockerized_labs/insec_des_lab/main.py:30-36` |
| finding-041 | CWE-306 | critical | `dockerized_labs/sensitive_data_exposure/dataexposure/views.py:112-132` |
| finding-034 | CWE-94 | critical | `introduction/apis.py:59-73` |
| finding-035 | CWE-94 | critical | `introduction/apis.py:126-135` |
| finding-032 | CWE-95 | critical | `introduction/mitre.py:213-219` |
| finding-033 | CWE-78 | critical | `introduction/mitre.py:237-242` |
| finding-001 | CWE-89 | critical | `introduction/views.py:158-158` |
| finding-003 | CWE-502 | critical | `introduction/views.py:213-214` |
| finding-004 | CWE-611 | critical | `introduction/views.py:256-266` |
| finding-005 | CWE-78 | critical | `introduction/views.py:419-434` |
| finding-006 | CWE-95 | critical | `introduction/views.py:456-460` |
| finding-007 | CWE-502 | critical | `introduction/views.py:557-560` |
| finding-008 | CWE-95 | critical | `introduction/views.py:583-588` |
| finding-002 | CWE-89 | critical | `introduction/views.py:864-864` |
| finding-013 | CWE-1336 | critical | `introduction/views.py:982-996` |
| finding-045 | CWE-798 | high | `dockerized_labs/broken_auth_lab/app.py:5-8` |
| finding-044 | CWE-640 | high | `dockerized_labs/broken_auth_lab/app.py:78-100` |
| finding-043 | CWE-565 | high | `dockerized_labs/broken_auth_lab/app.py:103-116` |
| finding-046 | CWE-798 | high | `dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py:8-13` |
| finding-036 | CWE-94 | high | `introduction/apis.py:23-33` |
| finding-029 | CWE-798 | high | `introduction/mitre.py:169-169` |
| finding-030 | CWE-352 | high | `introduction/mitre.py:191-207` |
| finding-009 | CWE-79 | high | `introduction/templates/Lab/XSS/xss_lab.html:27-27` |
| finding-010 | CWE-79 | high | `introduction/templates/Lab/XSS/xss_lab_2.html:20-20` |
| finding-011 | CWE-79 | high | `introduction/templates/Lab/XSS/xss_lab_3.html:20-22` |
| finding-012 | CWE-79 | high | `introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html:11-11` |
| finding-024 | CWE-256 | high | `introduction/views.py:283-287` |
| finding-023 | CWE-330 | high | `introduction/views.py:300-306` |
| finding-019 | CWE-863 | high | `introduction/views.py:344-356` |
| finding-038 | CWE-287 | high | `introduction/views.py:493-516` |
| finding-020 | CWE-290 | high | `introduction/views.py:790-800` |
| finding-015 | CWE-22 | high | `introduction/views.py:923-929` |
| finding-016 | CWE-918 | high | `introduction/views.py:959-963` |
| finding-014 | CWE-22 | high | `introduction/views.py:1003-1006` |
| finding-022 | CWE-565 | high | `introduction/views.py:1053-1076` |
| finding-028 | CWE-347 | high | `introduction/views.py:1086-1099` |
| finding-039 | CWE-798 | high | `pygoat/settings.py:25-32` |
| finding-042 | CWE-330 | medium | `dockerized_labs/sensitive_data_exposure/dataexposure/views.py:38-42` |
| finding-031 | CWE-327 | medium | `introduction/mitre.py:155-161` |
| finding-026 | CWE-327 | medium | `introduction/utility.py:58-59` |
| finding-018 | CWE-290 | medium | `introduction/views.py:535-540` |
| finding-037 | CWE-538 | medium | `introduction/views.py:636-639` |
| finding-027 | CWE-330 | medium | `introduction/views.py:679-680` |
| finding-021 | CWE-862 | medium | `introduction/views.py:837-841` |
| finding-017 | CWE-290 | medium | `introduction/views.py:942-953` |
| finding-025 | CWE-327 | medium | `introduction/views.py:1026-1026` |
| finding-047 | CWE-798 | medium | `introduction/views.py:1119-1121` |

---

## finding-040 — CWE-502 @ `dockerized_labs/insec_des_lab/main.py:30`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 30–36（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

insec_des_lab 的 /deserialize 路由把表单字段 serialized_data 做 base64 解码后直接 pickle.loads()。该 Flask 应用无任何认证，Dockerfile CMD 为 flask run --debug --port=8080 且监听 0.0.0.0，docker-compose 暴露端口。恶意 pickle 的 __reduce__ 会在反序列化时执行任意可调用对象，未认证攻击者可因此获得容器内命令执行（--debug 暴露的 Werkzeug 交互控制台是另一条 RCE 途径）。根因：对不可信输入执行 pickle 反序列化。

**代码证据（逐字摘录）**

```text
        serialized_data = request.form.get('serialized_data', '')
        decoded_data = base64.b64decode(serialized_data)
        # Intentionally vulnerable deserialization, matching PyGoat
        user = pickle.loads(decoded_data)
```

**触发条件（前提）**

源码已确认：路由仅声明 methods=['POST']（main.py:30），无身份校验；Dockerfile/docker-compose.yml 提供网络暴露。需部署环境确认容器端口对不可信网络可达。

**数据流 / 可达路径**

POST serialized_data -> base64.b64decode -> pickle.loads -> __reduce__ 指定的可调用对象执行 -> user.is_admin 判定并渲染 admin 内容。

**修复方向**

不要对不可信数据使用 pickle/yaml.Loader 等可执行反序列化。改用 JSON 等纯数据格式 + 服务端会话，或使用 `yaml.safe_load`；如必须传递状态，使用带签名（其 `itsdangerous`/JWT 长随机密钥）的令牌。

---

## finding-041 — CWE-306 @ `dockerized_labs/sensitive_data_exposure/dataexposure/views.py:112`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 112–132（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

all_users_data_view 挂载在 /api/all-users/（dataexposure/urls.py:13），既没有 @login_required 也没有任何权限判定，遍历 UserData.objects.all() 后返回全部用户的完整信用卡号、完整 SSN 与 API Key。未认证访客一次请求即可获得全量 PII。根因：敏感数据端点缺失认证与授权，且缺少字段级脱敏。

**代码证据（逐字摘录）**

```text
def all_users_data_view(request):
    # MAJOR SECURITY FLAW: This endpoint allows ANY user (even unauthenticated ones!)
    # to see ALL users' sensitive data!
...
    for user_data in UserData.objects.all():
        all_users_data.append({
            'username': user_data.user.username,
            'credit_card': user_data.credit_card,  # Completely exposed! No masking!
```

**触发条件（前提）**

源码已确认：该子应用独立部署（dockerized_labs/sensitive_data_exposure/docker-compose.yml、Dockerfile），settings DEBUG=True 且 ALLOWED_HOSTS=['*']；UserData 内容由 entrypoint.sh 预置。

**数据流 / 可达路径**

GET /api/all-users/ -> UserData.objects.all() -> 组装 username/credit_card/ssn/api_key -> JsonResponse 全量返回。

**修复方向**

先认证再授权：给端点加 `@login_required` 与角色/对象级权限校验，默认拒绝匿名访问；PII 只返回当前授权主体可见的字段，并做掩码（卡号仅显示后 4 位）、加密存储与访问审计。

---

## finding-034 — CWE-94 @ `introduction/apis.py:59`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 59–73（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

log_function_checker 的 @authentication_decorator 被注释（60 行附近），只有 @csrf_exempt，把 POST 的 log_code / api_code 原样写入 introduction/playground/A9/main.py 与 introduction/playground/A9/api.py。这两个文件被项目导入并注册为视图（introduction/urls.py:3 导入 log_function_target，urls.py:84 挂载 /2021/discussion/A9/target），因此未认证攻击者一次 POST 即可让 Django 进程在下次导入/自动重载（runserver autoreload、worker 重启）时执行任意 Python 代码。该视图还会把内容写入 test.log 并向 http://127.0.0.1:8000 发起内部请求（对自身端点的请求伪造）。根因：用户上传代码被写入可执行源码路径。

**代码证据（逐字摘录）**

```text
@csrf_exempt
# @authentication_decorator
def log_function_checker(request):
    if request.method == 'POST':
        csrf_token = request.POST.get("csrfmiddlewaretoken")
        log_code = request.POST.get('log_code')
        api_code = request.POST.get('api_code')
```

**触发条件（前提）**

源码已确认：路由 /2021/discussion/A9/api（urls.py:83），无身份校验。需在部署环境确认应用进程对源码目录可写（Dockerfile 以 root 运行且 COPY . /app，docker-compose 将 . 挂载为 /app，成立）。

**数据流 / 可达路径**

POST log_code/api_code -> open(log_filename,'w').write(log_code) -> playground/A9/*.py -> Django 导入该模块（urls.py 导入 / 自动重载）-> 攻击者代码在服务器进程内执行。

**修复方向**

禁止把用户提交的代码写入应用可导入/可执行路径。练习环境应在一次性容器、只读挂载、非 root 用户与独立命名空间中运行；判分应在服务进程外用沙箱解释器完成，并给端点加上认证与速率限制。

---

## finding-035 — CWE-94 @ `introduction/apis.py:126`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 126–135（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

A6_disscussion_api_2 未认证（@csrf_exempt，无 is_authenticated 检查）地把 POST code 写入 introduction/playground/A6/utility.py，而该文件的 check_vuln 由同项目 apis.py:8 导入、A6_disscussion_api（urls.py:86）调用。攻击者先写入恶意 utility.py，再请求 /2021/discussion/A6/api 触发模块重新导入或函数调用，即可以服务器权限执行任意 Python 代码。根因：用户上传代码写入可导入模块（与 finding-034 同类但不同端点/不同目标文件，独立位置）。

**代码证据（逐字摘录）**

```text
        code = request.POST.get('code')
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, "playground/A6/utility.py")
        f = open(filename,"w")
        f.write(code)
```

**触发条件（前提）**

源码已确认：路由 /2021/discussion/A6/api2（urls.py:88）；写入内容无语法/危险调用校验；需要进程发生模块重新导入（开发模式自动重载或重启）才会执行，该运行时条件需部署环境确认。

**数据流 / 可达路径**

POST code -> 写 playground/A6/utility.py -> A6_disscussion_api 调用 check_vuln() -> 模块重载后执行攻击者代码。

**修复方向**

禁止把用户提交的代码写入应用可导入/可执行路径。练习环境应在一次性容器、只读挂载、非 root 用户与独立命名空间中运行；判分应在服务进程外用沙箱解释器完成，并给端点加上认证与速率限制。

---

## finding-032 — CWE-95 @ `introduction/mitre.py:213`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 213–219（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

mitre_lab_25_api 的 @authentication_decorator 已被注释掉（213 行），只剩 @csrf_exempt，未授权访客 POST expression 即被 Python eval() 求值，结果以 JSON 原样回显。eval 可调用 __import__('os').system / open 等，构成未认证远程代码执行与任意文件读取。根因：不可信输入动态求值 + 端点缺失认证。

**代码证据（逐字摘录）**

```text
# @authentication_decorator
@csrf_exempt
def mitre_lab_25_api(request):
    if request.method == "POST":
        expression = request.POST.get('expression')
        result = eval(expression)
```

**触发条件（前提）**

源码已确认：路由 /mitre/25/lab/api（urls.py:125）无任何认证；仅需能访问服务端口。

**数据流 / 可达路径**

POST expression -> request.POST.get('expression') -> eval() -> JsonResponse({'result': result}) 回显。

**修复方向**

移除 eval()/ImageMath.eval 对不可信输入的求值路径。若需计算表达式，使用受限解析器（自定义 AST 遍历、`asteval` 白名单）并只允许数字与运算符；图像运算改为服务端固定选项映射，不接受用户表达式。

---

## finding-033 — CWE-78 @ `introduction/mitre.py:237`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 237–242（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

mitre_lab_17_api 同样只有 @csrf_exempt（无认证），把 POST ip 直接拼进 "nmap " + ip，再由 command_out() 以 subprocess.Popen(command, shell=True) 执行；该端点构成未认证远程命令执行，命令原始输出通过 raw_res/raw_err 字段完整回显。根因：不可信输入拼接进 shell 命令 + 端点缺失认证。

**代码证据（逐字摘录）**

```text
        ip = request.POST.get('ip')
        command = "nmap " + ip 
        res, err = command_out(command)
```

**触发条件（前提）**

源码已确认：路由 /mitre/17/lab/api（urls.py:127）；shell=True 见 mitre.py:232-234。即使目标机未安装 nmap，shell=True 仍会执行注入的命令（仅回显部分依赖 nmap 输出）。

**数据流 / 可达路径**

POST ip -> 字符串拼接 -> Popen(shell=True) -> res/err 解码 -> JsonResponse 回显（可含命令输出）。

**修复方向**

不要经 shell 执行外部命令：改用参数列表 + `shell=False`（如 `subprocess.run(['dig','--',domain])`），并在调用前用严格白名单校验主机名（RFC 1123 LDH、无空格/元字符）；限制可执行命令集合。

---

## finding-001 — CWE-89 @ `introduction/views.py:158`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 158–158（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

sql_lab 将 POST 参数 name 与 pass 直接字符串拼接成原生 SQL 后交给 login.objects.raw() 执行，未做任何参数化或转义。攻击者（任意已登录用户）可用引号闭合改写 WHERE 条件绕过口令校验，并通过回显/报错分支读取 introduction_login 表中的其他用户凭据；异常分支还把整条拼好的 SQL 语句（sql_error 上下文）返回给客户端，直接暴露注入点。根因：SQL 查询由不可信输入拼接而成。

**代码证据（逐字摘录）**

```text
sql_query = "SELECT * FROM introduction_login WHERE user='"+name+"' AND password='"+password+"'"
```

**触发条件（前提）**

源码已确认：/sql_lab 路由存在（introduction/urls.py:19），视图仅要求已登录，name 需命中 login 表已有用户。部署环境需确认使用默认 SQLite 数据库。

**数据流 / 可达路径**

POST name/pass -> request.POST.get() -> 字符串拼接 sql_query -> login.objects.raw(sql_query) -> val[0].user 渲染回 Lab/SQL/sql_lab.html；异常时 sql_query 原样回显。

**修复方向**

改用参数化查询（`Model.objects.raw(sql, params=[...])` 占位符）或直接用 ORM 的 filter/exclude 表达查询；不要向客户端回显拼好的 SQL 或后端报错；对账号口令改为哈希存储并走认证框架。

---

## finding-003 — CWE-502 @ `introduction/views.py:213`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 213–214（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

insec_des_lab 读取 Cookie token，base64 解码后直接 pickle.loads()。pickle 在反序列化过程中会自动调用 __reduce__ 指定的任意可调用对象，因此提交一个 __reduce__=(os.system,('...')) 形式的构造 pickle 即可获得服务器端命令执行；即使不利用执行，把 admin 字段改为 1 也能拿到页面中的 ADMIN123 机密。根因：对完全由客户端控制的字节流执行不受信反序列化。

**代码证据（逐字摘录）**

```text
            token = base64.b64decode(token)
            admin = pickle.loads(token)
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 Cookie 值不做任何签名校验；/insec_des_lab 路由见 urls.py:16。

**数据流 / 可达路径**

Cookie: token=<base64(pickle)> -> request.COOKIES.get('token') -> base64.b64decode -> pickle.loads -> __reduce__ 在 loads 期间执行 -> admin 属性决定返回内容。

**修复方向**

不要对不可信数据使用 pickle/yaml.Loader 等可执行反序列化。改用 JSON 等纯数据格式 + 服务端会话，或使用 `yaml.safe_load`；如必须传递状态，使用带签名（其 `itsdangerous`/JWT 长随机密钥）的令牌。

---

## finding-004 — CWE-611 @ `introduction/views.py:256`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 256–266（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

xxe_parse 显式开启 xml.sax 外部通用实体（parser.setFeature(feature_external_ges, True)）后解析 request.body，并把解析出的 <text> 内容 update 进 comments 表（再由 /xxe_see 渲染）。攻击者可声明 SYSTEM 实体读取服务器本地文件（/etc/passwd、源码、配置）或用 http/file 实体探测内网（SSRF）。该视图既没有认证装饰器也没有 is_authenticated 判断，且标注 @csrf_exempt，属未授权可达的 XML 解析入口。根因：XML 解析器未禁用 DTD/外部实体。

**代码证据（逐字摘录）**

```text
    parser = make_parser()
    parser.setFeature(feature_external_ges, True)
    doc = parseString(request.body.decode('utf-8'), parser=parser)
```

**触发条件（前提）**

源码已确认：路由 /xxe_parse（urls.py:22）无认证检查；解析结果写入 comments(id=1) 并由 /xxe_see 输出。需部署环境确认解析器实现（Python 3.11 + xml.sax）允许文件协议实体。

**数据流 / 可达路径**

POST body(XML + 外部实体) -> request.body.decode('utf-8') -> parseString(parser) -> expandNode/toxml -> comments.objects.filter(id=1).update(comment=text) -> /xxe_see 页面回显文件内容。

**修复方向**

使用禁用了 DTD/外部实体的解析器（`defusedxml`，或 lxml 的 `resolve_entities=False`、sax 关闭 external-ges/加载外部 DTD），并对 XML 端点补充认证、大小与深度限制。

---

## finding-005 — CWE-78 @ `introduction/views.py:419`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 419–434（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

cmd_lab 用 POST domain 拼接出 'dig {domain}' / 'nslookup {domain}'，再以 shell=True 交给 subprocess.Popen。唯一的处理是 re.sub(r'^(?:(https?|ftp)://)?(?:www\.)?', ...) —— 该正则只锚定协议/www 前缀，不过滤 ; | & ` $() 换行等 shell 元字符，因此提交 `x; id`、`$(curl attacker)`、`` `cat /etc/passwd` `` 即以应用权限执行任意系统命令，命令 stdout+stderr 还直接渲染回页面。根因：不可信输入拼入 shell 命令。

**代码证据（逐字摘录）**

```text
                command="nslookup {}".format(domain)
            else:
                command = "dig {}".format(domain)
...
                process = subprocess.Popen(
                    command,
                    shell=True,
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 /cmd_lab（urls.py:38）标注 @csrf_exempt，可用跨站表单提交。需部署主机存在 dig/nslookup（Dockerfile 已 apt 安装 dnsutils，容器内成立）。

**数据流 / 可达路径**

POST domain -> re.sub 去协议前缀 -> "dig {}".format(domain) -> subprocess.Popen(shell=True) -> stdout+stderr -> cmd_lab.html 的 <pre>{{output}}</pre> 回显（有回显 RCE）。

**修复方向**

不要经 shell 执行外部命令：改用参数列表 + `shell=False`（如 `subprocess.run(['dig','--',domain])`），并在调用前用严格白名单校验主机名（RFC 1123 LDH、无空格/元字符）；限制可执行命令集合。

---

## finding-006 — CWE-95 @ `introduction/views.py:456`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 456–460（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

cmd_lab2 把 POST val 原样传入 Python eval()。任何已登录用户提交 __import__('os').popen('id').read() 等表达式即可在服务器上执行任意代码，求值结果渲染回页面便于读取输出。根因：对用户输入执行动态求值。

**代码证据（逐字摘录）**

```text
                output = eval(val)
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 /cmd_lab2（urls.py:39）为 @csrf_exempt。

**数据流 / 可达路径**

POST val -> request.POST.get('val') -> eval(val) -> output 上下文 -> Lab/CMD/cmd_lab2.html 渲染。

**修复方向**

移除 eval()/ImageMath.eval 对不可信输入的求值路径。若需计算表达式，使用受限解析器（自定义 AST 遍历、`asteval` 白名单）并只允许数字与运算符；图像运算改为服务端固定选项映射，不接受用户表达式。

---

## finding-007 — CWE-502 @ `introduction/views.py:557`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 557–560（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

a9_lab 用 yaml.load(file, yaml.Loader) 解析用户上传的 YAML 文件。requirements.txt:27 固定 PyYAML==5.1，该版本配合 FullLoader/完整加载器可被 !!python/object/apply:os.system 一类标签触发任意对象构造与调用，导致服务器端代码执行（PyYAML 5.1 存在 CVE-2020-1747 等已知绕过）。根因：以不安全加载器反序列化不可信数据。

**代码证据（逐字摘录）**

```text
                    data = yaml.load(file,yaml.Loader)
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 上传入口 /a9_lab（urls.py:53）@csrf_exempt，multipart 字段名 file；PyYAML 版本由 requirements.txt 固定。

**数据流 / 可达路径**

multipart file -> request.FILES['file'] -> yaml.load(..., yaml.Loader) -> 构造 python 对象并执行 -> data 渲染回 a9_lab.html。

**修复方向**

不要对不可信数据使用 pickle/yaml.Loader 等可执行反序列化。改用 JSON 等纯数据格式 + 服务端会话，或使用 `yaml.safe_load`；如必须传递状态，使用带签名（其 `itsdangerous`/JWT 长随机密钥）的令牌。

---

## finding-008 — CWE-95 @ `introduction/views.py:583`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 583–588（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

a9_lab2 将 POST function 字符串直接交给 PIL.ImageMath.eval() 求值。ImageMath.eval 内部使用表达式求值，可借助传入图像的 Python 对象链（如 r.__class__ 上的 __init__.__globals__）访问 os/subprocess 执行系统命令，属于典型的不安全表达式求值导致的 RCE。根因：用户可控表达式被动态求值。

**代码证据（逐字摘录）**

```text
            output = ImageMath.eval(function_str,img = img, b=b, r=r, g=g)
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 需同时上传一张可被 Pillow 打开的图片（img.convert('RGB') 成功）；路由 /a9_lab2（urls.py:54）@csrf_exempt。

**数据流 / 可达路径**

POST function -> request.POST.get('function') -> ImageMath.eval(function_str, img=..., r=r, g=g, b=b) -> 表达式在 Django 进程内求值，结果转 JPEG 后 base64 渲染。

**修复方向**

移除 eval()/ImageMath.eval 对不可信输入的求值路径。若需计算表达式，使用受限解析器（自定义 AST 遍历、`asteval` 白名单）并只允许数字与运算符；图像运算改为服务端固定选项映射，不接受用户表达式。

---

## finding-002 — CWE-89 @ `introduction/views.py:864`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 864–864（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

injection_sql_lab 再次把 POST name/pass 拼接进 SELECT 语句并用 sql_lab_table.objects.raw() 执行，失败分支同样回显完整 SQL。由于 id 是字符串主键，注入 ' OR '1'='1 或 UNION/子查询即可绕过口令校验、枚举任意 id，并可读取库中其他表的敏感字段（同函数还硬编码写入了 admin 等账号口令）。根因：与 finding-001 相同类别，但位于不同视图、不同数据表，属独立代码位置。

**代码证据（逐字摘录）**

```text
sql_query = "SELECT * FROM introduction_sql_lab_table WHERE id='"+name+"'AND password='"+password+"'"
```

**触发条件（前提）**

源码已确认：路由 /injection_sql_lab（urls.py:74），仅要求已登录；866-873 行向表中写入含口令的固定记录。

**数据流 / 可达路径**

POST name/pass -> 拼接 sql_query -> sql_lab_table.objects.raw() -> user[0].id 渲染；异常回显 SQL。

**修复方向**

改用参数化查询（`Model.objects.raw(sql, params=[...])` 占位符）或直接用 ORM 的 filter/exclude 表达查询；不要向客户端回显拼好的 SQL 或后端报错；对账号口令改为哈希存储并走认证框架。

---

## finding-013 — CWE-1336 @ `introduction/views.py:982`

- **严重度 / 置信度**：critical / high
- **代码范围**：行 982–996（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

ssti_lab 把用户 POST 的 blog 内容（filter_blog 实为恒等函数，见 utility.py:55-57，未做任何过滤）与固定前缀拼接后写入 introduction/templates/Lab_2021/A3_Injection/Blogs/<id>.html，再重定向到 ssti_view_blog 用 render() 把该文件当作 Django 模板编译执行。攻击者可提交 {% %} 标签与模板表达式，在服务器端执行模板逻辑：仓库中已存在的两个由该入口写出的博客即为实例——a2538af1b5e4.html 读取 {{settings.SECRET_KEY}}，9d73d120683d.html 使用 {% load log %}{% get_admin_log 5 as log %} 输出其他用户的 {{e.user.password}}。根因：服务端模板注入（用户内容成为模板）。

**代码证据（逐字摘录）**

```text
            blog = filter_blog(blog)
            prepend_code = "{% extends 'introduction/base.html' %}\
...
            blog = prepend_code + blog + "{% endblock %}"
```

**触发条件（前提）**

源码已确认：需已登录（普通用户即可）；写入路径固定在应用模板目录，需部署环境确认进程对该目录可写（Dockerfile COPY . /app 以 root 运行，docker-compose 将 . 挂载到 /app，成立）。

**数据流 / 可达路径**

POST blog -> 拼接为 Django 模板文本 -> open(filename,'w+') 写入模板目录 -> redirect /ssti/blog/<id> -> render(request, f"Lab_2021/A3_Injection/Blogs/{blog_id}.html") -> 模板引擎求值用户标签。

**修复方向**

永远不要把用户输入拼接成模板再渲染。把用户内容作为数据传入固定模板（自动转义），如需富文本则先做标签白名单清洗；删除 `filter_blog` 这类恒等“过滤器”的假象实现。

---

## finding-045 — CWE-798 @ `dockerized_labs/broken_auth_lab/app.py:5`

- **严重度 / 置信度**：high / high
- **代码范围**：行 5–8（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

broken_auth_lab 在源码中硬编码 app.secret_key = 'your-secret-key-here'，同时 users 字典内置 admin/admin123、user/password123 明文口令，/login 以明文等值比较，/register 同样明文写入，登录失败无次数限制。凭据随源码分发即导致管理员账户直接泄露，签名密钥公开还使 flash/会话可被伪造。根因：硬编码凭据与明文口令存储（app.py:122 的 debug=True + 0.0.0.0 监听为同一配置问题集中的附加风险，Werkzeug 调试控制台可执行代码）。

**代码证据（逐字摘录）**

```text
app.secret_key = 'your-secret-key-here'  # Vulnerable: Hardcoded secret key

# Vulnerable: Storing user data in memory
users = {
    'admin': {
        'password': 'admin123',
```

**触发条件（前提）**

源码已确认：users 为源码内置字典（进程内存）；Dockerfile 设 FLASK_ENV=development，CMD python app.py。

**数据流 / 可达路径**

静态泄露：源码 -> admin/admin123 -> POST /login 明文比较通过 -> 获得可伪造 session Cookie -> 管理员视图。

**修复方向**

所有密钥、口令、固定凭据从源码中移除，改为环境变量或密钥管理服务注入并定期轮换；示例/教学用的口令不应写入生产可复用路径，注释中也不得包含真实凭据。

---

## finding-044 — CWE-640 @ `dockerized_labs/broken_auth_lab/app.py:78`

- **严重度 / 置信度**：high / high
- **代码范围**：行 78–100（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

/reset-password 用 md5(f"{email}:{datetime.now()}") 生成口令重置令牌（无密钥、时间戳精度到微秒但完全可从邮箱+大致时间枚举），并把包含令牌的重置链接直接通过 flash 返回给发起请求的人，/reset/<token> 又不做任何身份校验。结果：任何知道/猜到目标邮箱的人都能自助获得重置入口并接管账户，同时该差异（Email not found vs 返回链接）可用于用户枚举。根因：可预测的重置令牌 + 令牌通过响应泄露给请求方。

**代码证据（逐字摘录）**

```text
            token = hashlib.md5(f"{email}:{datetime.now()}".encode()).hexdigest()
            password_reset_tokens[token] = username
...
            flash(f'Password reset link: /reset/{token}')
```

**触发条件（前提）**

源码已确认：/reset/<token>（app.py:97-101）直接渲染 reset.html；口令重置流程无速率限制。

**数据流 / 可达路径**

POST email -> md5(email:now) -> 令牌写入内存字典并把链接回显给请求方 -> 访问 /reset/<token> 进入他人账户重置页。

**修复方向**

重置令牌必须由密码学安全随机源生成（`secrets.token_urlsafe(32)`）、服务端存储、单次使用且短有效期，只能发送到已验证的所有者邮箱，不得出现在给请求方的响应中；同时统一成功/失败响应以避免用户枚举。

---

## finding-043 — CWE-565 @ `dockerized_labs/broken_auth_lab/app.py:103`

- **严重度 / 置信度**：high / high
- **代码范围**：行 103–116（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

broken_auth_lab 的 /dashboard 只把 session Cookie 做 base64 解码、取冒号前第一段作为用户名去查 users 表；登录时签发形式为 base64(f"{username}:{datetime.now()}")，无签名、无服务端会话记录、无过期校验。任何人构造 session=base64('admin:whatever') 即可以 admin 角色读取仪表盘（含他人邮箱、role 等）。根因：以可伪造的客户端 Cookie 作为身份/会话凭据。

**代码证据（逐字摘录）**

```text
        session_token = request.cookies.get('session')
...
        username = base64.b64decode(session_token).decode().split(':')[0]
        if username in users:
```

**触发条件（前提）**

源码已确认：该应用以 python app.py 启动（Dockerfile CMD，host='0.0.0.0', port=5000, debug=True），docker-compose 暴露 5000；/login、/register、/reset-password 均无认证。

**数据流 / 可达路径**

Cookie: session=base64('admin:...') -> request.cookies.get('session') -> b64decode().split(':')[0] -> users[username] -> render dashboard.html(username, role='admin', email)。

**修复方向**

认证/授权状态不得由未签名的客户端 Cookie 内容决定。使用 Django 会话框架或带签名、过期与吊销机制的令牌（服务端存储），并设置 HttpOnly/Secure/SameSite。

---

## finding-046 — CWE-798 @ `dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py:8`

- **严重度 / 置信度**：high / high
- **代码范围**：行 8–13（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

sensitive_data_exposure 子应用设置同样硬编码 SECRET_KEY，并设置 DEBUG = True、ALLOWED_HOSTS = ['*']。该服务通过 docker-compose 暴露端口，硬编码密钥允许攻击者伪造 django_session 绕过 /profile、/api/user-data/ 上的 @login_required；DEBUG 异常页会输出 settings（含 SECRET_KEY）与执行的 SQL。根因：生产配置中硬编码密钥并开启调试模式（与主应用 finding-039 为不同部署单元、不同文件）。

**代码证据（逐字摘录）**

```text
SECRET_KEY = 'django-insecure-key-for-demonstration-only'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
```

**触发条件（前提）**

源码已确认：dockerized_labs/sensitive_data_exposure/docker-compose.yml 暴露端口；entrypoint.sh 固定创建口令为 demopass 的 demo 用户（弱凭据为附加证据，未单列为发现）。

**数据流 / 可达路径**

公开源码 -> SECRET_KEY -> 伪造 django_session 访问 login_required 视图；DEBUG -> 异常页泄露配置与 SQL。

**修复方向**

所有密钥、口令、固定凭据从源码中移除，改为环境变量或密钥管理服务注入并定期轮换；示例/教学用的口令不应写入生产可复用路径，注释中也不得包含真实凭据。

---

## finding-036 — CWE-94 @ `introduction/apis.py:23`

- **严重度 / 置信度**：high / medium
- **代码范围**：行 23–33（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

ssrf_code_checker 虽要求已登录，但把用户提交的 python_code 经 ssrf_code_converter 转换后写入 introduction/playground/ssrf/main.py（utility.py:31-37），随后立即调用 main.ssrf_lab(...) 执行该文件中的函数。转换逻辑只是按行截取、删除空行，不做任何危险调用检查，普通注册用户即可向应用源码目录写入任意 Python 代码，在进程重启/自动重载后获得代码执行，也可借此破坏其它用户正在使用的练习环境。根因：用户代码持久化到可导入模块（不同端点、不同目标文件）。

**代码证据（逐字摘录）**

```text
            python_code = request.POST['python_code']
            html_code = request.POST['html_code']
            if not (ssrf_code_converter(python_code)):
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 路由 /api/ssrf（urls.py:85）为 @csrf_exempt；代码真正执行需要 playground/ssrf/main.py 被（重新）导入，该运行时时序需部署环境确认，故置信度为 medium。

**数据流 / 可达路径**

POST python_code -> ssrf_code_converter -> open(playground/ssrf/main.py,'w').write(output_Code) -> main.ssrf_lab() 调用（当前进程为旧模块，重载后为攻击者代码）。

**修复方向**

禁止把用户提交的代码写入应用可导入/可执行路径。练习环境应在一次性容器、只读挂载、非 root 用户与独立命名空间中运行；判分应在服务进程外用沙箱解释器完成，并给端点加上认证与速率限制。

---

## finding-029 — CWE-798 @ `introduction/mitre.py:169`

- **严重度 / 置信度**：high / high
- **代码范围**：行 169–169（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

mitre.csrf_lab_login 用硬编码字符串 'csrf_vulneribility' 作为 HS256 签名密钥签发 auth_cookiee，csrf_transfer_monei / csrf_transfer_monei_api 仅凭该 JWT 中的 username 认定当前用户。任何人（含未登录 Django 用户）都能为任意用户名离线签发合法令牌，从而以他人身份访问与转账。根因：硬编码签名密钥导致认证令牌可伪造。

**代码证据（逐字摘录）**

```text
            cookie = jwt.encode(payload, 'csrf_vulneribility', algorithm='HS256')
```

**触发条件（前提）**

源码已确认：密钥字面量同时出现在 mitre.py:169/182/194；转账 API（urls.py:122）视图本身无认证装饰器。

**数据流 / 可达路径**

离线 jwt.encode({'username':'<victim>'}, 'csrf_vulneribility') -> Cookie auth_cookiee -> jwt.decode 通过 -> 以受害者身份读写其余额。

**修复方向**

所有密钥、口令、固定凭据从源码中移除，改为环境变量或密钥管理服务注入并定期轮换；示例/教学用的口令不应写入生产可复用路径，注释中也不得包含真实凭据。

---

## finding-030 — CWE-352 @ `introduction/mitre.py:191`

- **严重度 / 置信度**：high / high
- **代码范围**：行 191–207（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

csrf_transfer_monei_api 通过 GET /mitre/9/lab/api/<recipent>/<int:amount> 直接完成真实余额变更：GET 属于浏览器“安全方法”，Django 的 CsrfViewMiddleware 不会拦截跨站 GET，视图自身也没有任何来源/token 校验，auth_cookiee Cookie 也未设置 SameSite。第三方页面只需一个 <img src="/mitre/9/lab/api/attacker/100"> 即可让已登录受害者向攻击者账户转账。根因：状态变更操作缺失 CSRF 防护。

**代码证据（逐字摘录）**

```text
def csrf_transfer_monei_api(request,recipent,amount):
    if request.method == "GET":
        cookie = request.COOKIES['auth_cookiee']
```

**触发条件（前提）**

源码已确认：路由 urls.py:122；视图未加 @authentication_decorator 与 @csrf_protect；受害者需在受害者浏览器中携带有效 auth_cookiee（即曾登录过该 lab）。

**数据流 / 可达路径**

第三方页面 GET 请求 -> 浏览器自动携带 auth_cookiee -> 解析 username -> CSRF_user_tbl 双方 balance 更新。

**修复方向**

资金等状态变更只接受带 CSRF 保护的 POST/PUT 请求（`@require_POST` + `{% csrf_token %}` 或显式 `CSRF_COOKIE_*` 策略），校验 Origin/Referer，Cookie 设置 `SameSite=Lax/Strict` 与 `Secure`，并对敏感操作增加二次确认。

---

## finding-009 — CWE-79 @ `introduction/templates/Lab/XSS/xss_lab.html:27`

- **严重度 / 置信度**：high / high
- **代码范围**：行 27–27（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

xss_lab.html 使用 {{query|safe}} 输出检索词，显式关闭 Django 自动转义；对应视图把 GET q 参数原样放入上下文（views.py:96-101）。构造 /xssL1?q=<script>alert(document.cookie)</script> 即形成反射型 XSS，可在已登录用户浏览器中执行任意脚本（窃取会话、以用户身份发起请求）。根因：不可信数据在 HTML 上下文中未转义输出。

**代码证据（逐字摘录）**

```text
    <h3> The company '{{query|safe}}' You searched for is not Part of FAANG</h3>
```

**触发条件（前提）**

源码已确认：视图 xss_lab 仅在 q 未命中 FAANG 公司时进入该 |safe 分支；需受害者点击带 q 参数的链接。

**数据流 / 可达路径**

GET /xssL1?q= -> request.GET.get('q') -> context {'query': q} -> 模板 {{query|safe}} -> 浏览器按脚本解析。

**修复方向**

去掉模板中的 `|safe`，依赖 Django 自动转义；对确需富文本的场景使用 bleach 等白名单清洗库，并按输出上下文（HTML 属性 / JavaScript / URL）分别编码；JavaScript 上下文用 `json_script` 传递数据；同时配置 CSP、`SESSION_COOKIE_HTTPONLY`/`SameSite`。

---

## finding-010 — CWE-79 @ `introduction/templates/Lab/XSS/xss_lab_2.html:20`

- **严重度 / 置信度**：high / high
- **代码范围**：行 20–20（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

xss_lab_2.html 用 {{ username|safe}} 回显用户输入；视图侧“过滤”仅 strip() 并删除小写 <script>/</script> 字符串（views.py:112-116），<img src=x onerror=...>、<svg onload=...>、<ScRiPt> 等变体全部可绕过，构成反射型 XSS。同页脚本从 document.cookie 读取 flag，XSS 成功后可直接取到该 Cookie。根因：黑名单式过滤 + |safe 输出。

**代码证据（逐字摘录）**

```text
<p>Hello, {{ username|safe }}</p>
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 POST /xssL2 参数 username 非空即进入 |safe 分支（urls.py:11）。

**数据流 / 可达路径**

POST username -> strip().replace('<script>','').replace('</script>','') -> context['username'] -> 模板 |safe 原样输出。

**修复方向**

去掉模板中的 `|safe`，依赖 Django 自动转义；对确需富文本的场景使用 bleach 等白名单清洗库，并按输出上下文（HTML 属性 / JavaScript / URL）分别编码；JavaScript 上下文用 `json_script` 传递数据；同时配置 CSP、`SESSION_COOKIE_HTTPONLY`/`SameSite`。

---

## finding-011 — CWE-79 @ `introduction/templates/Lab/XSS/xss_lab_3.html:20`

- **严重度 / 置信度**：high / high
- **代码范围**：行 20–22（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

xss_lab_3.html 把过滤后的 {{code}} 直接放进页面内联 <script> 标签中。视图只删除字母与数字（pattern = r'[a-zA-Z0-9]'，views.py:131-135），刻意保留 []()!+ 等特殊字符，因此可用 JSFuck 风格（纯特殊字符构成的合法 JavaScript）在该脚本上下文中执行任意代码。根因：未按输出上下文转义，把用户数据写入 JavaScript 代码区。

**代码证据（逐字摘录）**

```text
<p>{{code}}</p>
<script>
    // LAB 3 JS CODE
    {{code}}
</script>
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 POST /xssL3 参数 username（urls.py:12）；过滤器只删除字符，不限制长度。

**数据流 / 可达路径**

POST username -> re.sub('[a-zA-Z0-9]','',username) -> context['code'] -> 模板内联 <script>{{code}}</script> 执行。

**修复方向**

去掉模板中的 `|safe`，依赖 Django 自动转义；对确需富文本的场景使用 bleach 等白名单清洗库，并按输出上下文（HTML 属性 / JavaScript / URL）分别编码；JavaScript 上下文用 `json_script` 传递数据；同时配置 CSP、`SESSION_COOKIE_HTTPONLY`/`SameSite`。

---

## finding-012 — CWE-79 @ `introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html:11`

- **严重度 / 置信度**：high / high
- **代码范围**：行 11–11（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

software_and_data_integrity_failure_lab2 把 GET username 直接交给模板 lab2.html 的 {{username | safe}}，视图（views.py:1222-1224）除 try/except 外无任何校验或转义，构成反射型 XSS。根因：|safe 关闭自动转义，用户输入进入 HTML 上下文。

**代码证据（逐字摘录）**

```text
<h1>Hey {{username | safe}},</h1>
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 路由 /2021/A8/lab2（urls.py:92），视图带 @authentication_decorator。

**数据流 / 可达路径**

GET ?username= -> request.GET['username'] -> context {'username': ...} -> 模板 |safe 输出。

**修复方向**

去掉模板中的 `|safe`，依赖 Django 自动转义；对确需富文本的场景使用 bleach 等白名单清洗库，并按输出上下文（HTML 属性 / JavaScript / URL）分别编码；JavaScript 上下文用 `json_script` 传递数据；同时配置 CSP、`SESSION_COOKIE_HTTPONLY`/`SameSite`。

---

## finding-024 — CWE-256 @ `introduction/views.py:283`

- **严重度 / 置信度**：high / high
- **代码范围**：行 283–287（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

auth_lab_signup 把用户口令以明文写入 authLogin.password（models.py:35 该字段为普通 CharField，无哈希器），auth_lab_login 再以 authLogin.objects.filter(username=user_name,password=passwd) 做明文等值比较。数据库文件（db.sqlite3 或备份）一旦泄露，全部账号口令立即可读，并可用于其他站点撞库。根因：口令明文存储/明文比较。

**代码证据（逐字摘录）**

```text
                obj = authLogin.objects.create(name=name,username=user_name,password=passwd)
```

**触发条件（前提）**

源码已确认：/auth_lab/signup（urls.py:25）无密码哈希；同文件其它 lab 至少使用了 md5/sha256，可对比确认此处缺失。

**数据流 / 可达路径**

POST pass -> request.POST['pass'] -> authLogin.objects.create(password=...) -> 明文写入 SQLite；登录时（views.py:315）以明文做等值查询。

**修复方向**

口令一律使用自适应哈希存储（Django `set_password`，argon2/bcrypt/PBKDF2 + 每用户盐与成本因子），禁止明文入库与明文等值查询；对既有明文数据做迁移与强制改密。

---

## finding-023 — CWE-330 @ `introduction/views.py:300`

- **严重度 / 置信度**：high / high
- **代码范围**：行 300–306（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

auth_lab_login 在 GET 分支仅凭 Cookie userid 完成登录（authLogin.objects.filter(userid=request.COOKIES['userid'])[0]），而 userid 是 models.py 中 authLogin 的 AutoField 主键，从 1 开始自增、可枚举；signup/login 还以 samesite=None, secure=False 长期（max_age=31449600）写出该 Cookie。攻击者遍历 userid=1..N 即可冒充任意注册用户，跨站请求也会自动携带该 Cookie。根因：使用可预测且未签名的客户端标识作为会话凭据。

**代码证据（逐字摘录）**

```text
            obj = authLogin.objects.filter(userid=request.COOKIES['userid'])[0]
```

**触发条件（前提）**

源码已确认：/auth_lab/login（urls.py:26）不依赖 Django 会话；authLogin.userid = models.AutoField(primary_key=True)（introduction/models.py:35-39）。

**数据流 / 可达路径**

Cookie: userid=1 -> authLogin.objects.filter(userid=...) -> 取该用户对象 -> 渲染 auth_success.html 并再次 set_cookie。

**修复方向**

安全相关的标识、票据、密钥改用密码学安全随机源（`secrets.token_urlsafe`/`uuid4`/`random.SystemRandom`），并保证足够的熵与一次性；服务端不应把凭据的正确性建立在可预测值上。

---

## finding-019 — CWE-863 @ `introduction/views.py:344`

- **严重度 / 置信度**：high / high
- **代码范围**：行 344–356（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

ba_lab 把“是否管理员”的授权判定建立在客户端 Cookie admin 上：只要 admin=1 就直接返回 0NLY_F0R_4DM1N5 机密，而该 Cookie 由本视图自行 set_cookie 写出、未签名、未设置 httponly/samesite。攻击者手工设置 admin=1 即绕过授权。根因：客户端可控状态参与服务端授权判定。

**代码证据（逐字摘录）**

```text
            if request.COOKIES.get('admin') == "1":
                return render(
                    request, 
                    'Lab/BrokenAccess/ba_lab.html', 
                    {
                        "data":"0NLY_F0R_4DM1N5",
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 /ba_lab（urls.py:31）标注 @csrf_exempt；admin Cookie 无签名。

**数据流 / 可达路径**

Cookie: admin=1 -> request.COOKIES.get('admin') -> 授权分支 -> 返回仅管理员可见数据。

**修复方向**

授权判定必须在服务端完成：使用 Django 的 `user.has_perm`/`is_staff`/组或专用角色模型，不要读取客户端 Cookie 决定角色；确需保存状态时使用签名的服务端会话。

---

## finding-038 — CWE-287 @ `introduction/views.py:493`

- **严重度 / 置信度**：high / high
- **代码范围**：行 493–516（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

Otp 视图在“非管理员”分支把刚生成的三位 OTP 直接渲染进 HTTP 响应（render(..., {"otp":otpN})），校验分支写成 otp.objects.filter(email=email,otp=otpR) or otp.objects.filter(id=2,otp=otpR)：只要提交的 OTP 等于管理员（id=2）当前 OTP 也算通过，而用于标识会话的 email 来自客户端 Cookie；OTP 空间仅 100-999 且无尝试次数限制。结果二次认证可被直接读取、跨账户接受或在线爆破绕过。根因：认证凭据下发给客户端 + 错误的凭据归属校验。

**代码证据（逐字摘录）**

```text
                otp.objects.filter(id=1).update(email=email, otp=otpN)
                html=render (request,"Lab/BrokenAuth/otp.html",{"otp":otpN})
...
        if otp.objects.filter(email=email,otp=otpR) or otp.objects.filter(id=2,otp=otpR):
```

**触发条件（前提）**

源码已确认：/otp（urls.py:42）标注 @csrf_exempt 且无认证要求；otp 模型的 MaxValueValidator(300) 对 update() 不生效；email 参数来自 GET 查询串，攻击者可任意指定。

**数据流 / 可达路径**

GET /otp?email=x -> randint(100,999) -> 写入 otp 表并把明文 OTP 回显给请求方 -> POST otp + Cookie email -> 校验通过即视为该邮箱登录成功。

**修复方向**

第二因素凭据绝不能随响应下发；应服务端保存、短有效期、限制尝试次数并在失败时失效，校验时必须同时比对“该凭据属于哪个会话/账户”，改用 HMAC 签名的一次性令牌与足够位长的随机值。

---

## finding-020 — CWE-290 @ `introduction/views.py:790`

- **严重度 / 置信度**：high / high
- **代码范围**：行 790–800（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

a1_broken_access_lab_2 以 User-Agent 是否等于 'pygoat_admin' 判定管理员并返回 0NLY_F0R_4DM1N5，该头完全由客户端控制（curl -A pygoat_admin 即绕过）。此外 request.META['HTTP_USER_AGENT'] 直接下标取值，客户端省略该头会抛 KeyError 导致 500（次要可用性问题）。根因：把可伪造的客户端标识当作权限凭据。

**代码证据（逐字摘录）**

```text
    user_agent = request.META['HTTP_USER_AGENT']
...
    if name :  
        if (user_agent == "pygoat_admin"):
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 路由 /broken_access_lab_2（urls.py:61）。

**数据流 / 可达路径**

请求头 User-Agent -> request.META['HTTP_USER_AGENT'] -> 与 'pygoat_admin' 比较 -> 管理员数据分支。

**修复方向**

不要用客户端可控的头（X-Forwarded-For、User-Agent、自定义 X-Host）做身份或权限判定。改为服务端会话/角色校验；如确需代理转发的真实 IP，只信任可信代理链并由中间件（如`NUM_PROXY`/`SECURE_PROXY_SSL_HEADER`）解析。

---

## finding-015 — CWE-22 @ `introduction/views.py:923`

- **严重度 / 置信度**：high / high
- **代码范围**：行 923–929（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

ssrf_lab 把 POST blog 的值直接与 views.py 所在目录 os.path.join 后 open().read()。blog 未做规范化或前缀校验，os.path.join 在第二参数为绝对路径时会丢弃 dirname，且 ../ 可逐级跳出 introduction 目录，因此 blog=../../../pygoat/settings.py 或 /etc/passwd 即可读取任意文本文件，内容通过 {"blog":data} 渲染回页面；读取异常统一返回 No blog found，可用于路径存在性探测。根因：路径遍历导致任意文件读取。

**代码证据（逐字摘录）**

```text
            file=request.POST["blog"]
            try :
                dirname = os.path.dirname(__file__)
                filename = os.path.join(dirname, file)
                file = open(filename,"r")
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 路由 /ssrf_lab（urls.py:66）。

**数据流 / 可达路径**

POST blog -> os.path.join(dirname, file) -> open().read() -> context {'blog': data} -> ssrf_lab.html 回显。

**修复方向**

对文件/模板路径使用白名单（如只允许 `[0-9a-f]{12}` 的 blog_id 或固定枚举的 blog 文件名），用 `os.path.realpath` + `commonpath` 校验结果仍在允许目录内；对象访问还需校验数据库中的 author 归属。

---

## finding-016 — CWE-918 @ `introduction/views.py:959`

- **严重度 / 置信度**：high / high
- **代码范围**：行 959–963（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

ssrf_lab2 对用户提交的 url 直接 requests.get(url)，无协议白名单、无内网/回环地址拦截、无重定向限制。已登录用户可用它扫描内网服务、读取云元数据（http://169.254.169.254/），或访问仅监听本机的功能（例如 http://127.0.0.1:8000/ssrf_target，配合该视图对 XFF 的信任拿到受限内容）。响应体被完整回显。根因：服务端按用户可控 URL 发起请求且不做目标校验。

**代码证据（逐字摘录）**

```text
    elif request.method == "POST":
        url = request.POST["url"]
        try:
            response = requests.get(url)
```

**触发条件（前提）**

源码已确认：视图带 @authentication_decorator，路由 /ssrf_lab2（urls.py:68）。目标应用可达内网或云环境属部署前提。

**数据流 / 可达路径**

POST url -> request.POST['url'] -> requests.get(url) -> response.content.decode() -> 模板 ssrf_lab2.html 回显。

**修复方向**

不要按用户提供的 URL 直接请求。改为白名单主机/路径枚举；若必须支持，禁止重定向、只允许 http/https、拒绝回环/私网/链路本地（含 169.254.169.254）地址、按解析后的 IP 建连并设超时。

---

## finding-014 — CWE-22 @ `introduction/views.py:1003`

- **严重度 / 置信度**：high / medium
- **代码范围**：行 1003–1006（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

ssti_view_blog 把 URL 捕获参数 blog_id 直接拼进模板名传给 render()，没有白名单校验，也没有确认该 id 属于请求者（Blogs 表中的 author 从未参与判断）。攻击者可请求他人博客（遍历 8 位十六进制 id 即可，空间很小），并利用 <str:blog_id> 允许的点号构造 ../ 使模板加载器解析 Blogs 目录之外的模板文件。根因：不可信输入参与模板路径构造 + 缺失对象级授权校验。

**代码证据（逐字摘录）**

```text
def ssti_view_blog(request,blog_id):
    if request.user.is_authenticated:
        if request.method=="GET":
            return render(request,f"Lab_2021/A3_Injection/Blogs/{blog_id}.html")
```

**触发条件（前提）**

源码已确认：路由 path("ssti/blog/<str:blog_id>", ...)（urls.py:87）；<str> 转换器不匹配 '/'，因此目录遍历能否跳出 Blogs 目录取决于模板加载器对 '../' 的处理，需在部署环境进一步确认；跨用户读取他人博客（水平越权）则仅依赖 id 可猜测性，源码已可确认缺失授权判断。

**数据流 / 可达路径**

URL /ssti/blog/<blog_id> -> 视图参数 -> f-string 拼接模板名 -> Django TemplateLoader 解析并渲染（无 author 校验）。

**修复方向**

对文件/模板路径使用白名单（如只允许 `[0-9a-f]{12}` 的 blog_id 或固定枚举的 blog 文件名），用 `os.path.realpath` + `commonpath` 校验结果仍在允许目录内；对象访问还需校验数据库中的 author 归属。

---

## finding-022 — CWE-565 @ `introduction/views.py:1053`

- **严重度 / 置信度**：high / high
- **代码范围**：行 1053–1076（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

crypto_failure_lab3 的“会话令牌”就是未签名的 f"{username}|{expire}" 字符串写入 Cookie，GET 分支再用 cookie.split('|')[0] == 'admin' 判定管理员，仅比较一个可预测的过期时间。攻击者设置 Cookie: cookie=admin|2999-01-01 00:00:00 即可获得 admin 视图。根因：以可伪造的客户端 Cookie 作为认证/授权凭据。

**代码证据（逐字摘录）**

```text
                elif cookie.split('|')[0] == 'admin':
...
                    cookie = f"{username}|{expire}"
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 路由 /cryptographic_failure/lab3（urls.py:95）；Cookie 无签名、无服务端存储。

**数据流 / 可达路径**

Cookie: cookie -> request.COOKIES['cookie'] -> split('|') -> 用户名/过期时间比较 -> admin 分支渲染。

**修复方向**

认证/授权状态不得由未签名的客户端 Cookie 内容决定。使用 Django 会话框架或带签名、过期与吊销机制的令牌（服务端存储），并设置 HttpOnly/Secure/SameSite。

---

## finding-028 — CWE-347 @ `introduction/views.py:1086`

- **严重度 / 置信度**：high / high
- **代码范围**：行 1086–1099（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

sec_misconfig_lab3 使用硬编码在 pygoat/settings.py:171 的常量 SECRET_COOKIE_KEY = "PYGOAT" 校验 HS256 JWT，只要 payload['user'] == 'admin' 即渲染管理员视图。该密钥随源码公开且强度极低，攻击者可离线 jwt.encode({'user':'admin',...}, 'PYGOAT') 自行签发令牌放入 auth_cookie 完成权限提升。根因：安全令牌使用硬编码/公开密钥签名，服务端无法验证来源真实性。

**代码证据（逐字摘录）**

```text
    payload = jwt.decode(cookie, SECRET_COOKIE_KEY, algorithms=['HS256'])
        if payload['user'] == 'admin':
```

**触发条件（前提）**

源码已确认：/sec_mis_lab3（urls.py:48）要求已登录，但 admin 判定完全取决于 Cookie 中 JWT 内容；密钥常量见 settings.py:171（views.py:1088 处 from pygoat.settings import SECRET_COOKIE_KEY）。

**数据流 / 可达路径**

Cookie auth_cookie -> jwt.decode(cookie, SECRET_COOKIE_KEY) -> payload['user'] 判定 admin -> 管理员页面渲染。

**修复方向**

令牌验证必须使用仅服务端持有的强密钥（从环境变量注入），并校验 exp/iat/aud/iss 与算法白名单；对已泄露的密钥做轮换，同时使权限判定回到服务端会话（不能仅依赖 JWT 中的 user 字段）。

---

## finding-039 — CWE-798 @ `pygoat/settings.py:25`

- **严重度 / 置信度**：high / high
- **代码范围**：行 25–32（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

主项目设置把 SECRET_KEY 直接硬编码进仓库（未从环境变量读取），并同时保持 DEBUG = True。SECRET_KEY 用于签名 django_session、Signed Cookie 与 CSRF token：拿到它即可伪造任意用户（含超级用户）的会话、伪造 CSRF 令牌，配合 /admin 后台即完全接管应用；DEBUG=True 部署到 gunicorn 时任何异常都会返回含堆栈、settings 内容与 SQL 语句的调试页面，形成敏感信息泄露。ALLOWED_HOSTS 还包含 '0.0.0.0.' 这类宽松条目。根因：生产配置内含硬编码密钥并保留调试模式。

**代码证据（逐字摘录）**

```text
SECRET_KEY = 'lr66%-a!$km5ed@n5ug!tya5bv!0(yqwa1tn!q%0%3m2nh%oml'

SENSITIVE_DATA = 'FLAGTHATNEEDSTOBEFOUND'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
```

**触发条件（前提）**

源码已确认：settings.py 未使用 os.environ 读取 SECRET_KEY/DEBUG；Dockerfile CMD 为 gunicorn --bind 0.0.0.0:8000 pygoat.wsgi，docker-compose.yml 未注入 DEBUG/SECRET_KEY 环境变量。django_heroku.settings(locals()) 是否会改写 DEBUG 需在部署环境确认（因此影响中的 Host/CSRF 具体行为需实测）。

**数据流 / 可达路径**

公开源码 -> SECRET_KEY 泄露 -> 伪造/篡改 django_session 或 signed cookie -> 会话与权限绕过；DEBUG=True -> 异常页堆栈/配置泄露。

**修复方向**

所有密钥、口令、固定凭据从源码中移除，改为环境变量或密钥管理服务注入并定期轮换；示例/教学用的口令不应写入生产可复用路径，注释中也不得包含真实凭据。

---

## finding-042 — CWE-330 @ `dockerized_labs/sensitive_data_exposure/dataexposure/views.py:38`

- **严重度 / 置信度**：medium / high
- **代码范围**：行 38–42（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

generate_api_key 使用非密码学安全的 random.choices（Mersenne Twister）从 36 字符集中取 16 位生成 API Key，随后写入 UserData.api_key 并通过 /api/user-data/、profile.html（含 localStorage.setItem('user_api_key', ...)）下发。作为访问账户资源的凭据，其随机源可预测：观测到部分输出即可推断 PRNG 内部状态，进而预测其他用户注册时生成的 Key。根因：安全令牌使用不安全随机源。

**代码证据（逐字摘录）**

```text
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=16))  # 16 chars should be enough right?
```

**触发条件（前提）**

源码已确认：调用点 views.py:58/82/98；entrypoint.sh 另外固定写入 api_key='demokey123456789'（弱凭据，附加证据）。

**数据流 / 可达路径**

注册/profile/api 请求 -> generate_api_key() -> 存 UserData.api_key -> JSON 与页面暴露给前端。

**修复方向**

安全相关的标识、票据、密钥改用密码学安全随机源（`secrets.token_urlsafe`/`uuid4`/`random.SystemRandom`），并保证足够的熵与一次性；服务端不应把凭据的正确性建立在可预测值上。

---

## finding-031 — CWE-327 @ `introduction/mitre.py:155`

- **严重度 / 置信度**：medium / high
- **代码范围**：行 155–161（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

csrf_lab_login 用无盐 MD5 摘要与 CSRF_user_tbl.password 比对，成功即签发长期身份令牌；该 lab 的账户余额可直接被资金操作消耗，弱口令保护等级与业务风险不匹配，可离线爆破后接管任意账户。根因：不安全口令摘要（与 finding-029 的硬编码密钥、finding-030 的缺失 CSRF 为不同根因，独立位置）。

**代码证据（逐字摘录）**

```text
        password = md5(password.encode()).hexdigest()
        User = CSRF_user_tbl.objects.filter(username=username, password=password)
```

**触发条件（前提）**

源码已确认：视图带 @authentication_decorator（需先登录 Django 账号）；CSRF_user_tbl.password 存放 MD5 摘要（introduction/models.py:91-96）。

**数据流 / 可达路径**

POST password -> md5().hexdigest() -> filter(username,password) -> 签发 auth_cookiee JWT 作为后续交易身份。

**修复方向**

口令存储改用 Django 认证框架的哈希器（argon2/bcrypt/scrypt/PBKDF2），不要自研摘要函数或使用无盐 MD5/SHA；如需摘要，仅用于非安全用途并由框架统一管理。

---

## finding-026 — CWE-327 @ `introduction/utility.py:58`

- **严重度 / 置信度**：medium / high
- **代码范围**：行 58–59（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

utility.customHash 作为“口令哈希”函数只做了 sha256 后把十六进制摘要整体反转（[::-1]），无盐、无迭代、无密钥，字符串反转不提供任何额外强度；crypto_failure_lab2（views.py:1046-1047）用它比对 CF_user.password2。攻击者拿到数据库即可离线高速爆破全部口令。根因：自制且不充分的口令派生函数。（与 finding-025 为不同函数、不同调用点，独立修复。）

**代码证据（逐字摘录）**

```text
def customHash(password):
    return hashlib.sha256(password.encode()).hexdigest()[::-1]
```

**触发条件（前提）**

源码已确认：调用点 views.py:1046（crypto_failure_lab2），数据库字段 CF_user.password2（max_length=64）。

**数据流 / 可达路径**

POST password -> customHash() -> CF_user.objects.filter(username=..., password2=...) 比对；摘要可离线暴力破解。

**修复方向**

口令存储改用 Django 认证框架的哈希器（argon2/bcrypt/scrypt/PBKDF2），不要自研摘要函数或使用无盐 MD5/SHA；如需摘要，仅用于非安全用途并由框架统一管理。

---

## finding-018 — CWE-290 @ `introduction/views.py:535`

- **严重度 / 置信度**：medium / high
- **代码范围**：行 535–540（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

secret 视图以自定义请求头 X-Host 是否等于 'admin.localhost:8000' 判定管理员，命中即在页面输出 S3CR37K3Y；未命中分支还把用户提交的 XHost 拼接进提示文本回显。请求头完全由客户端控制，一次 curl -H 'X-Host: admin.localhost:8000' /secret 即绕过。根因：以可伪造的客户端标识做身份/权限判定。

**代码证据（逐字摘录）**

```text
    XHost = request.headers.get('X-Host', 'None')
    if(XHost == 'admin.localhost:8000'):
        return render(request,"Lab/sec_mis/sec_mis_lab.html", {"secret": "S3CR37K3Y"})
```

**触发条件（前提）**

源码已确认：/secret（urls.py:49）无任何认证检查，未登录即可访问。

**数据流 / 可达路径**

请求头 X-Host -> 字符串相等比较 -> 模板 secret 分支（机密信息泄露）。

**修复方向**

不要用客户端可控的头（X-Forwarded-For、User-Agent、自定义 X-Host）做身份或权限判定。改为服务端会话/角色校验；如确需代理转发的真实 IP，只信任可信代理链并由中间件（如`NUM_PROXY`/`SECURE_PROXY_SSL_HEADER`）解析。

---

## finding-037 — CWE-538 @ `introduction/views.py:636`

- **严重度 / 置信度**：medium / high
- **代码范围**：行 636–639（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

debug 视图在任何身份校验缺失的情况下把 introduction/templates/Lab/A10/debug.log 以 text/plain 返回。该日志包含请求路径、/admin 访问、登录页访问等记录，未认证攻击者可用于收集内部路径、验证管理面板存在、辅助进一步攻击；同类调试输出文件（app.log、test.log）也在应用根目录生成。根因：调试/日志资源作为公开端点提供（信息泄露）。

**代码证据（逐字摘录）**

```text
def debug(request):
    response = render(request,'Lab/A10/debug.log')
    response['Content-Type'] =  'text/plain'
    return response
```

**触发条件（前提）**

源码已确认：路由 /debug（urls.py:56）无 is_authenticated 检查；日志文件随仓库分发（含 /admin、/login 记录）。

**数据流 / 可达路径**

GET /debug -> render 模板目录中的 debug.log -> 完整日志文本返回给未认证请求。

**修复方向**

不要把日志文件作为 Web 端点公开。移除 `/debug`、`/robots.txt` 之类的调试资源路由，或至少加上管理员权限校验；日志写入应用目录之外（stdout/集中式日志），并对路径做敏感信息脱敏。

---

## finding-027 — CWE-330 @ `introduction/views.py:679`

- **严重度 / 置信度**：medium / medium
- **代码范围**：行 679–680（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

gentckt 使用 Python 内置 random（Mersenne Twister，非密码学安全）生成长度 10 的大小写门票码，而 insec_desgine_lab 中该门票码是唯一兑换凭据（tickits.tickit 为 unique 字段）。用于安全用途的凭据来自可预测 PRNG：观测到若干输出即可推断内部状态并预测未发放的票据，且 52^10 空间在无速率限制下可被在线枚举。根因：不安全随机数生成安全令牌（CWE-330）。

**代码证据（逐字摘录）**

```text
def gentckt():
    return (''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=10)))
```

**触发条件（前提）**

源码已确认：/insecure-design_lab（urls.py:59）需已登录；兑换成功分支要求全库 sold_tickets>=60 且票据属于当前用户，该业务前置条件已在源码中确认，但需部署环境确认票据发放量。

**数据流 / 可达路径**

POST count -> gentckt() -> random.choices(...) -> 写入 tickits 表并把票据码渲染给攻击者。

**修复方向**

安全相关的标识、票据、密钥改用密码学安全随机源（`secrets.token_urlsafe`/`uuid4`/`random.SystemRandom`），并保证足够的熵与一次性；服务端不应把凭据的正确性建立在可预测值上。

---

## finding-021 — CWE-862 @ `introduction/views.py:837`

- **严重度 / 置信度**：medium / high
- **代码范围**：行 837–841（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

a1_broken_access_lab3_secret 只做 is_authenticated 判断，注释直接写明 “no checking applied here”，任何登录用户（包括刚注册的普通账号）都能访问 Lab_2021/A1_BrokenAccessControl/secret.html 读取其中的机密内容（模板正文即 SOME_SECRET_KEYS）。根因：敏感端点缺失授权（角色）校验。

**代码证据（逐字摘录）**

```text
def a1_broken_access_lab3_secret(request):
    if not request.user.is_authenticated:
        return redirect('login')
    # no checking applied here
    return render(request, 'Lab_2021/A1_BrokenAccessControl/secret.html')
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 路由 /broken_access_controle/secret（urls.py:64）。

**数据流 / 可达路径**

GET /broken_access_controle/secret -> 仅登录判断（无角色判断）-> 渲染含机密的模板。

**修复方向**

为敏感端点显式声明权限检查（`@login_required` + `@permission_required`/自定义角色判断），并用默认拒绝的策略覆盖全部视图；增加测试确保未授权访问返回 403。

---

## finding-017 — CWE-290 @ `introduction/views.py:942`

- **严重度 / 置信度**：medium / high
- **代码范围**：行 942–953（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

ssrf_target 仅依据 HTTP_X_FORWARDED_FOR 的第一个片段判断请求是否来自 127.0.0.1。该头完全由客户端控制，加上 'X-Forwarded-For: 127.0.0.1' 即可获取本应仅限本机访问的 target 页面内容（该页面即 SSRF 靶标内容）。根因：以可伪造的转发头做访问控制判定。

**代码证据（逐字摘录）**

```text
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    if ip == '127.0.0.1':
```

**触发条件（前提）**

源码已确认：/ssrf_target（urls.py:69）没有认证装饰器，任意未认证访客可请求。

**数据流 / 可达路径**

请求头 X-Forwarded-For -> request.META['HTTP_X_FORWARDED_FOR'].split(',')[0] -> 与 '127.0.0.1' 比较 -> 决定是否返回受限制内容。

**修复方向**

不要用客户端可控的头（X-Forwarded-For、User-Agent、自定义 X-Host）做身份或权限判定。改为服务端会话/角色校验；如确需代理转发的真实 IP，只信任可信代理链并由中间件（如`NUM_PROXY`/`SECURE_PROXY_SSL_HEADER`）解析。

---

## finding-025 — CWE-327 @ `introduction/views.py:1026`

- **严重度 / 置信度**：medium / high
- **代码范围**：行 1026–1026（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

crypto_failure_lab 以无盐 MD5(password).hexdigest() 作为口令摘要与 CF_user.password 比对。MD5 计算极快且已不适用于口令保护，配合库中/字典中的弱口令可离线批量爆破或直接用彩虹表还原，导致账户接管。根因：使用不安全摘要算法保护认证凭据。

**代码证据（逐字摘录）**

```text
                password = md5(password.encode()).hexdigest()
                user = CF_user.objects.filter(username=username,password=password).first()
```

**触发条件（前提）**

源码已确认：视图内存在 request.user.is_authenticated 检查（任意已注册普通用户即可满足）。尚需部署环境确认：应用按仓库提供方式运行（manage.py runserver 或 gunicorn pygoat.wsgi），对应 urls.py 路由已注册。 路由 /cryptographic_failure/lab（urls.py:94）；CF_user.password 字段长度 200（models.py:66-68）。

**数据流 / 可达路径**

POST password -> md5().hexdigest() -> CF_user.objects.filter(username,password) 等值比对 -> 页面回显用户对象。

**修复方向**

口令存储改用 Django 认证框架的哈希器（argon2/bcrypt/scrypt/PBKDF2），不要自研摘要函数或使用无盐 MD5/SHA；如需摘要，仅用于非安全用途并由框架统一管理。

---

## finding-047 — CWE-798 @ `introduction/views.py:1119`

- **严重度 / 置信度**：medium / medium
- **代码范围**：行 1119–1121（起始列 1）
- **验证状态**：static_analysis_only（未执行漏洞验证）

**根因与影响**

源码注释直接公布 A7 lab2 管理员账号口令：'# used admin password --> 2022_in_pygoat@pygoat.com'，紧随其后的 auth_failure_lab2 用 AF_admin 表 + argon2 校验该账号。任何能读到源码/镜像/仓库的人都可直接登录该受保护的管理功能页（该 URL /auth_failure/lab2/admin12983gfugef81e8yeryepanel 也被硬编码在 urls.py:96，属于“仅靠隐藏路径保护”的次要问题）。根因：凭据硬编码在源码中。

**代码证据（逐字摘录）**

```text
## used admin password --> 2022_in_pygoat@pygoat.com
```

**触发条件（前提）**

源码已确认：注释位于 views.py:1119；AF_admin 记录由练习/迁移流程写入，需部署环境确认数据库中的实际口令与该注释一致（因此置信度 medium）。

**数据流 / 可达路径**

静态泄露：源码注释 -> 用户名/口令 -> POST /auth_failure/lab2/... -> ph.verify 通过 -> 登录管理员功能。

**修复方向**

所有密钥、口令、固定凭据从源码中移除，改为环境变量或密钥管理服务注入并定期轮换；示例/教学用的口令不应写入生产可复用路径，注释中也不得包含真实凭据。

---

## 未覆盖范围与分析局限

**明确未覆盖 / 仅粗读的部分**

- `introduction/templates/mitre/mitre_top1.html` ~ `mitre_top25.html`（25 个纯讲解模板）未逐行阅读，仅确认其视图 `mitre_top1..25` 只是 `render` 静态模板（mitre.py:22-151）。
- `introduction/migrations/*.py`（21 个）、`challenge/migrations/*.py`（3 个）、`dockerized_labs/sensitive_data_exposure/dataexposure/migrations/*.py` 只做抽样（0019_af_admin.py 全文阅读），其余按 Django 自动生成迁移处理，未逐行核查字段默认值中是否含额外敏感数据。
- `introduction/static/css/*.css`、`introduction/static/Lab/*.css`、各 lab 的 `static/style.css` 未阅读（样式文件通常无安全影响，但其中可能残留的内部路径未做确认）。
- 大部分 HTML 讲解模板（`introduction/templates/Lab/**`、`Lab_2021/**`、`introduction/templates/introduction/**`、`registration/**`、各 dockerized_labs 模板）只做了针对性搜索（`|safe`、`autoescape`、`innerHTML`、`document.write`、`eval(`、表单/敏感字段名），命中处才展开阅读；未逐行核对每一处模板输出。
- `introduction/templates/Lab/A10/debug.log`、`introduction/xee_see.txt`、`installer.sh`、`uninstaller.sh`、`LICENSE.md`、`README` 类文本只读取了开头部分（详见 coverage.json 的 partial 说明）。
- 二进制资源（图片、SVG 等）未分析，已单列 `excluded_binary_files`。
- 未在目录中检索到的文件（如 `db.sqlite3`、`README.md`、文档目录、独立解答与 Notebook）本次不存在，因此无法据其判断数据层实际内容（例如各 lab 表中真实口令哈希、AF_admin 记录）。

**方法学局限**

- 未运行应用、未执行测试或利用代码，所有可利用性判断依赖静态数据流推理；运行时路由、中间件、反向代理对头/路径的处理差异都可能改变结论。
- 未访问任何外部规范、漏洞库或该项目公开资料（按实验要求），因此 CWE 归类与严重度依赖审查者既有知识。
- 有意为之的教学漏洞与“真实缺陷”在源码中混杂：本报告只按证据陈述缺陷本身，不推断出题意图。
- 不声称“已覆盖全部漏洞”或“其余代码安全”；本次时间预算内未展开的文件已在 coverage.json 中标注为 partial / not_reviewed。
- 未计算精确率/召回率/F1 等指标，也未与任何标准答案比对。
