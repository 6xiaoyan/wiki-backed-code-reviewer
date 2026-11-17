# 静态安全代码审查报告（实验 01 / B 组 / qwen-3.8-flash-next / r01）

- 审查对象：`D:/ai_share/langgraph/benchmark-data/pygoat-baseline/inputs/experiment-01/pygoat`（source commit `2fb0c600245f50670e8b9233c784afe61e8b340b`）
- 附加依据：`inputs/experiment-01/rules-v1` 全部 9 份规范（Django 官方 security/deployment checklist、OWASP Django/Authorization/Deserialization/SQLi/SSRF/XSS、腾讯 Python 安全编码规范）
- 方法：仅静态分析（文件阅读 + 全文检索 + 逐处数据流核对）。**未安装依赖、未运行目标应用、未执行任何测试或利用代码、未调用漏洞扫描器。**
- 结论口径：以下每条发现均有具体文件行号与逐字代码证据；未经运行验证，因此不构成“已复现”的表述。
- 确认发现总数：**59**；按严重度：critical 13 / high 27 / medium 18 / low 1。另有 10 条未确认候选见 `uncertain-findings.json`。

## 发现索引

| 编号 | 严重度 | CWE | 位置 | 摘要 |
|---|---|---|---|---|
| finding-001 | critical | CWE-89 | `introduction/views.py:158-162` | raw SQL 字符串拼接导致 SQL 注入 |
| finding-002 | critical | CWE-89 | `introduction/views.py:864-878` | raw SQL 字符串拼接导致 SQL 注入（另一视图） |
| finding-003 | critical | CWE-502 | `introduction/views.py:214-216` | Cookie 中 pickle.loads 导致 RCE |
| finding-004 | high | CWE-611 | `introduction/views.py:259-268` | XXE：显式启用外部通用实体 |
| finding-005 | critical | CWE-78 | `introduction/views.py:426-436` | shell=True 命令注入 |
| finding-006 | critical | CWE-95 | `introduction/views.py:460-464` | eval() 任意代码执行 |
| finding-007 | high | CWE-918 | `introduction/views.py:963-966` | SSRF：requests.get 目标完全可控 |
| finding-008 | high | CWE-22 | `introduction/views.py:926-928` | 路径穿越导致任意文件读取 |
| finding-009 | critical | CWE-502 | `introduction/views.py:560-563` | yaml.load 非安全 Loader 导致 RCE |
| finding-010 | high | CWE-95 | `introduction/views.py:588-592` | PIL.ImageMath.eval 表达式注入 |
| finding-011 | critical | CWE-1336 | `introduction/views.py:984-1008` | Django 模板 SSTI（用户内容写成模板并渲染） |
| finding-012 | high | CWE-79 | `introduction/templates/Lab/XSS/xss_lab.html:27-27` | 反射型 XSS（{{query|safe}}） |
| finding-013 | high | CWE-79 | `introduction/templates/Lab/XSS/xss_lab_2.html:20-20` | 反射型 XSS（黑名单过滤 + |safe） |
| finding-014 | high | CWE-79 | `introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html:11-11` | 反射型 XSS（GET 参数 + |safe） |
| finding-015 | medium | CWE-79 | `introduction/templates/Lab/ssrf/ssrf_lab2.html:23-23` | XSS（SSRF 响应以 |safe 输出） |
| finding-016 | medium | CWE-79 | `introduction/static/js/a9.js:40-42` | DOM XSS（innerHTML 写入服务端日志） |
| finding-017 | critical | CWE-94 | `introduction/apis.py:67-88` | 未认证接口写入被 import 的源码文件（代码注入） |
| finding-018 | critical | CWE-94 | `introduction/apis.py:132-137` | 未认证接口写入被 import 的源码文件（代码注入） |
| finding-019 | high | CWE-94 | `introduction/utility.py:34-37` | 登录用户可覆盖应用源码文件（代码注入） |
| finding-020 | critical | CWE-95 | `introduction/mitre.py:215-218` | 未认证 eval() RCE |
| finding-021 | critical | CWE-78 | `introduction/mitre.py:241-243` | 未认证 nmap 命令注入 |
| finding-022 | high | CWE-352 | `introduction/mitre.py:191-209` | 转账接口用 GET 且无 CSRF/鉴权 |
| finding-023 | high | CWE-798 | `introduction/mitre.py:169-170` | JWT 签名密钥硬编码 |
| finding-024 | medium | CWE-327 | `introduction/mitre.py:161-162` | 口令使用 MD5 摘要 |
| finding-025 | high | CWE-798 | `pygoat/settings.py:171-171` | JWT SECRET_COOKIE_KEY="PYGOAT" 硬编码 |
| finding-026 | high | CWE-798 | `pygoat/settings.py:25-28` | Django SECRET_KEY/SENSITIVE_DATA 硬编码 |
| finding-027 | medium | CWE-489 | `pygoat/settings.py:30-33` | DEBUG=True 与宽松 ALLOWED_HOSTS |
| finding-028 | medium | CWE-614 | `pygoat/settings.py:55-66` | 缺少全部 HTTPS/安全 Cookie/点击劫持相关设置 |
| finding-029 | high | CWE-565 | `introduction/views.py:1060-1063` | 未签名可拼装的 admin 会话 Cookie |
| finding-030 | medium | CWE-327 | `introduction/views.py:1026-1027` | 口令使用 MD5（CF_user） |
| finding-031 | medium | CWE-916 | `introduction/views.py:1042-1044` | 自制哈希（无盐 sha256 反转） |
| finding-032 | medium | CWE-798 | `introduction/views.py:1163-1168` | 认证依赖源码中的硬编码账号表 |
| finding-033 | medium | CWE-916 | `introduction/views.py:1194-1204` | 无盐单轮 SHA-256 口令哈希且无限速 |
| finding-034 | high | CWE-256 | `introduction/views.py:287-292` | 口令明文入库并明文比对 |
| finding-035 | high | CWE-287 | `introduction/views.py:302-307` | 仅凭可猜测 userid Cookie 登录（认证绕过/IDOR） |
| finding-036 | high | CWE-285 | `introduction/views.py:347-364` | admin Cookie 决定权限（越权） |
| finding-037 | high | CWE-285 | `introduction/views.py:797-800` | User-Agent 决定管理员权限（越权） |
| finding-038 | high | CWE-862 | `introduction/views.py:840-842` | 机密页面缺少授权检查 |
| finding-039 | high | CWE-200 | `introduction/views.py:506-508` | OTP 直接回显给请求方 |
| finding-040 | high | CWE-287 | `introduction/views.py:514-516` | 3 位弱 OTP + 不校验身份的 id=2 分支 |
| finding-041 | medium | CWE-290 | `introduction/views.py:536-541` | 以 X-Host 请求头做访问控制 |
| finding-042 | medium | CWE-290 | `introduction/views.py:950-951` | 以可伪造的 XFF 判定内网来源 |
| finding-043 | medium | CWE-117 | `introduction/views.py:669-671` | 日志注入（XFF/用户名未规范化写日志） |
| finding-044 | medium | CWE-538 | `introduction/views.py:636-640` | 未认证提供真实 debug.log |
| finding-045 | low | CWE-200 | `introduction/views.py:571-572` | 对外暴露组件版本 |
| finding-046 | high | CWE-1035 | `requirements.txt:27-33` | 锁定多个已知不安全依赖版本 |
| finding-047 | medium | CWE-1104 | `Dockerfile:1-24` | 过期基础镜像 + COPY . 把机密打进镜像 |
| finding-048 | high | CWE-384 | `dockerized_labs/broken_auth_lab/app.py:45-52` | 可伪造的 base64 会话 Cookie |
| finding-049 | high | CWE-640 | `dockerized_labs/broken_auth_lab/app.py:86-92` | 可预测且直接回显的口令重置令牌 |
| finding-050 | high | CWE-798 | `dockerized_labs/broken_auth_lab/app.py:13-22` | 源码内明文弱口令账号 |
| finding-051 | high | CWE-489 | `dockerized_labs/broken_auth_lab/app.py:8-9` | Flask 硬编码 secret_key + debug=True 对外监听 |
| finding-052 | critical | CWE-502 | `dockerized_labs/insec_des_lab/main.py:33-36` | 未认证 pickle.loads RCE |
| finding-053 | critical | CWE-306 | `dockerized_labs/sensitive_data_exposure/dataexposure/views.py:112-132` | 未认证端点导出全部用户卡号/SSN/API key |
| finding-054 | high | CWE-312 | `dockerized_labs/sensitive_data_exposure/dataexposure/models.py:6-8` | 卡号/SSN/API key 明文存储且无脱敏 |
| finding-055 | medium | CWE-798 | `dockerized_labs/sensitive_data_exposure/entrypoint.sh:11-12` | 初始化脚本硬编码默认口令与机密数据 |
| finding-056 | medium | CWE-489 | `dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py:8-14` | 子实验 DEBUG=True + ALLOWED_HOSTS=['*'] |
| finding-057 | medium | CWE-259 | `introduction/playground/A9/api.py:17-19` | 路由上的接口使用硬编码 admin/admin 且把凭据写日志 |
| finding-058 | high | CWE-922 | `dockerized_labs/sensitive_data_exposure/templates/profile.html:217-223` | API 密钥写入页面 JS 与 localStorage |
| finding-059 | medium | CWE-829 | `dockerized_labs/sensitive_data_exposure/templates/base.html:60-62` | 多个模板从 CDN 加载无 SRI/CSP 的第三方脚本 |

## finding-001 — raw SQL 字符串拼接导致 SQL 注入

- **位置**：`introduction/views.py` 第 158 行第 17 列 至 第 162 行第 53 列
- **CWE**：CWE-89　**严重度**：critical　**置信度**：high

**问题说明与根因**

sql_lab() 直接把 POST 参数 name / pass 字符串拼进 SQL 语句，再交给 Django 的 raw() 执行。攻击者可在 name 或 pass 中注入 SQL 元字符（如 ' or '1'='1' -- ）改变查询语义，绕过口令判断、读取或探测 introduction_login 表的全部数据；查询失败时原始语句还会被回显到页面。

**代码证据**（逐字摘自上述行号）

```
                sql_query = "SELECT * FROM introduction_login WHERE user='"+name+"' AND password='"+password+"'"
                print(sql_query)
                try:
                    print("\nin try\n")
                    val=login.objects.raw(sql_query)
```

**触发条件 / 前提**

源码已确认：视图仅要求 request.user.is_authenticated（任何已登录用户），无输入参数化或转义；部署环境需确认（本次仅静态分析）：应用已初始化 introduction_login 表且存在用户数据。

**数据流（输入 → 危险操作）**

HTTP POST /sql_lab 的 name、pass -> views.sql_lab() 拼接 sql_query -> login.objects.raw(sql_query) 直接送到数据库执行。

**修复方向**

改用 ORM 条件或参数化查询：login.objects.filter(user=name, password=password)；确需 raw 时使用 login.objects.raw(sql, params=[name, password]) 占位符，并对错误信息做通用化，不回显 SQL 语句。

**验证状态**：`static_analysis_only`

---

## finding-002 — raw SQL 字符串拼接导致 SQL 注入（另一视图）

- **位置**：`introduction/views.py` 第 864 行第 13 列 至 第 878 行第 60 列
- **CWE**：CWE-89　**严重度**：critical　**置信度**：high

**问题说明与根因**

injection_sql_lab() 与 finding-001 是不同代码位置的同类缺陷：POST 的 name / pass 被拼接进 SELECT 语句并用 sql_lab_table.objects.raw() 执行，且每次请求都会先把一批含明文口令的账号写库。注入可绕过口令校验并读出 introduction_sql_lab_table 中所有 id/password。

**代码证据**（逐字摘自上述行号）

```
            sql_query = "SELECT * FROM introduction_sql_lab_table WHERE id='"+name+"'AND password='"+password+"'"

            sql_instance = sql_lab_table(id="admin", password="65079b006e85a7e798abecb99e47c154")
            sql_instance.save()
            sql_instance = sql_lab_table(id="jack", password="jack")
            sql_instance.save()
            sql_instance = sql_lab_table(id="slinky", password="b4f945433ea4c369c12741f62a23ccc0")
            sql_instance.save()
            sql_instance = sql_lab_table(id="bloke", password="f8d1ce191319ea8f4d1d26e65e130dd5")
            sql_instance.save()

            print(sql_query)

            try:
                user = sql_lab_table.objects.raw(sql_query)
```

**触发条件 / 前提**

源码已确认：同样只做 is_authenticated 判断，未做参数化查询。

**数据流（输入 → 危险操作）**

HTTP POST /injection_sql_lab 的 name、pass -> 拼接 sql_query -> sql_lab_table.objects.raw(sql_query) -> 数据库执行。

**修复方向**

同 finding-001：使用 sql_lab_table.objects.filter(id=name, password=password) 或 raw(..., params=[...])；同时删除视图内每次请求都写库的种子数据逻辑，改为迁移/管理命令初始化。

**验证状态**：`static_analysis_only`

---

## finding-003 — Cookie 中 pickle.loads 导致 RCE

- **位置**：`introduction/views.py` 第 214 行第 21 列 至 第 216 行第 127 列
- **CWE**：CWE-502　**严重度**：critical　**置信度**：high

**问题说明与根因**

insec_des_lab() 读取用户完全可控的 token Cookie，base64 解码后直接 pickle.loads()，并用反序列化对象的 admin 属性做授权判断。pickle 在构造对象时会执行任意 __reduce__ 指令，因此攻击者构造恶意 pickle 即可在该 Web 进程内获得任意代码执行（RCE），而不仅仅是绕过管理员判断。

**代码证据**（逐字摘自上述行号）

```
            admin = pickle.loads(token)
            if admin.admin == 1:
                response = render(request,'Lab/insec_des/insec_des_lab.html', {"message":"Welcome Admin, SECRETKEY:ADMIN123"})
```

**触发条件 / 前提**

源码已确认：Cookie 内容未做任何签名/完整性校验，pickle.loads 直接作用于解码结果；视图要求已登录。部署环境需确认（本次仅静态分析）：服务运行在可被登录用户访问的环境。

**数据流（输入 → 危险操作）**

Cookie: token -> request.COOKIES.get('token') -> base64.b64decode -> pickle.loads(token)（危险操作）-> admin.admin == 1 授权判断。

**修复方向**

不要在 Cookie 中放 pickle。改为服务端 session 或签名+加密的不可执行数据结构（django.core.signing / itsdangerous / JWT），若必须传递对象则使用 JSON 白名单字段。

**验证状态**：`static_analysis_only`

---

## finding-004 — XXE：显式启用外部通用实体

- **位置**：`introduction/views.py` 第 259 行第 23 列 至 第 268 行第 57 列
- **CWE**：CWE-611　**严重度**：high　**置信度**：high

**问题说明与根因**

xxe_parse() 显式开启 xml.sax 的外部通用实体解析（feature_external_ges=True），随后解析未受信任的 request.body。攻击者可用 <!ENTITY xxe SYSTEM "file:///etc/passwd"> 之类载荷读取服务器本地文件或内网 URL（SSRF 式外联），并把读到的内容写进 comments 表，再通过 /xxe_see 回显。该视图同时带 @csrf_exempt，可被跨站伪造请求触发。requirements.txt 已引入 defusedxml 但未在此使用。

**代码证据**（逐字摘自上述行号）

```
    parser.setFeature(feature_external_ges, True)
    doc = parseString(request.body.decode('utf-8'), parser=parser)
    for event, node in doc:
        if event == START_ELEMENT and node.tagName == 'text':
            doc.expandNode(node)
            text = node.toxml()
    startInd = text.find('>')
    endInd = text.find('<', startInd)
    text = text[startInd + 1:endInd:]
    p=comments.objects.filter(id=1).update(comment=text)
```

**触发条件 / 前提**

源码已确认：parser.setFeature(feature_external_ges, True) 显式打开外部实体；端点无认证、无 CSRF 保护。

**数据流（输入 → 危险操作）**

任意 HTTP POST /xxe_parse 的请求体 -> request.body.decode('utf-8') -> parseString(..., parser) 展开外部实体 -> node.toxml() 文本 -> comments.objects.filter(id=1).update(comment=text) -> /xxe_see 页面回显。

**修复方向**

禁用外部实体：改用 defusedxml.defuse_std_parser / xml.etree 且关闭 DTD，或 xml.sax 中设 feature_external_ges=False、feature_load_external_dtd/parameter_entity=False；同时移除 @csrf_exempt 并补充身份校验。

**验证状态**：`static_analysis_only`

---

## finding-005 — shell=True 命令注入

- **位置**：`introduction/views.py` 第 426 行第 17 列 至 第 436 行第 46 列
- **CWE**：CWE-78　**严重度**：critical　**置信度**：high

**问题说明与根因**

cmd_lab() 把 POST 的 domain 直接 format 进 shell 命令字符串并用 subprocess.Popen(..., shell=True) 执行。仅在开头做一次协议/www 前缀的正则剥离，未做 shell 元字符过滤或参数列表化；提交 `x; cat /etc/passwd #`、`$(id)`、反引号等即可在服务器上执行任意系统命令。

**代码证据**（逐字摘自上述行号）

```
                command = "dig {}".format(domain)
            
            try:
                # output=subprocess.check_output(command,shell=True,encoding="UTF-8")
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                data = stdout.decode('utf-8')
```

**触发条件 / 前提**

源码已确认：domain 来自 request.POST，命令用字符串拼接后经 shell=True 执行，输出 stdout+stderr 回显到页面。

**数据流（输入 → 危险操作）**

POST /cmd_lab 的 domain -> re.sub 去协议前缀 -> "dig {}".format(domain) -> subprocess.Popen(command, shell=True) -> 命令输出写入 output -> render 回显。

**修复方向**

不要拼接 shell 命令：使用参数列表 subprocess.run(["dig", domain], shell=False)，并用域名白名单正则（^[A-Za-z0-9.-]+$）校验 domain；os 参数应做枚举白名单（win/other）。

**验证状态**：`static_analysis_only`

---

## finding-006 — eval() 任意代码执行

- **位置**：`introduction/views.py` 第 460 行第 26 列 至 第 464 行第 39 列
- **CWE**：CWE-95　**严重度**：critical　**置信度**：high

**问题说明与根因**

cmd_lab2() 将 POST 参数 val 原样传给 Python 内置 eval()，并把结果回显。eval 会执行任意 Python 表达式，攻击者可用 __import__('os').popen('...').read()、open('/etc/passwd').read() 之类载荷实现任意代码/命令执行与文件读取。

**代码证据**（逐字摘自上述行号）

```
                output = eval(val)
            except:
                output = "Something went wrong"
                return render(request,'Lab/CMD/cmd_lab2.html',{"output":output})
            print("Output = ", output)
```

**触发条件 / 前提**

源码已确认：val 无任何白名单/字符校验，直接 eval()。视图要求已登录。

**数据流（输入 → 危险操作）**

POST /cmd_lab2 的 val -> eval(val)（危险操作）-> 结果写入 output -> 模板回显。

**修复方向**

删除 eval()。若只需算术求值，用 AST 白名单解析（ast.literal_eval 或自写 ast.NodeVisitor 只允许 Add/Sub/Mul/Div）；任何情况下都不把请求参数交给解释器。

**验证状态**：`static_analysis_only`

---

## finding-007 — SSRF：requests.get 目标完全可控

- **位置**：`introduction/views.py` 第 963 行第 24 列 至 第 966 行第 88 列
- **CWE**：CWE-918　**严重度**：high　**置信度**：high

**问题说明与根因**

ssrf_lab2() 用用户完全控制的 url 调用 requests.get()，未做协议、目标主机/IP 段白名单，也未禁止重定向。攻击者可让服务端访问内网服务与云元数据地址（如 http://169.254.169.254/）、http://127.0.0.1:8000/ssrf_target（该端点仅凭来源 IP==127.0.0.1 判定内网可信），并把响应内容原样回显。

**代码证据**（逐字摘自上述行号）

```
            response = requests.get(url)
            return render(request, "Lab/ssrf/ssrf_lab2.html", {"response": response.content.decode()})
        except:
            return render(request, "Lab/ssrf/ssrf_lab2.html", {"error": "Invalid URL"})
```

**触发条件 / 前提**

源码已确认：requests.get(url) 的 url 直接来自 request.POST['url']；response.content 被 decode 后传入模板。部署环境需确认（本次仅静态分析）：部署主机可访问内网/元数据服务时影响更大。

**数据流（输入 → 危险操作）**

POST /ssrf_lab2 的 url -> requests.get(url) -> response.content.decode() -> ssrf_lab2.html 中 {{response|safe}} 输出。

**修复方向**

按 OWASP SSRF 建议做“默认拒绝”：只允许固定 scheme(http/https)、解析域名到公网 IP 后拒绝回环/私有/链路本地地址、禁止或逐跳校验重定向、设置超时，并且优先使用白名单主机名映射而不是任意 URL。

**验证状态**：`static_analysis_only`

---

## finding-008 — 路径穿越导致任意文件读取

- **位置**：`introduction/views.py` 第 926 行第 28 列 至 第 928 行第 35 列
- **CWE**：CWE-22　**严重度**：high　**置信度**：high

**问题说明与根因**

ssrf_lab() 把 POST 参数 blog 直接 os.path.join 到模块目录后 open() 读取。blog 中的 ../ 序列不会被 os.path.join 剥离，因此可穿越到应用目录之外，读取任意进程可读文件（如 /etc/passwd、pygoat/settings.py 中的 SECRET_KEY、db.sqlite3），读到的内容作为 blog 回显。

**代码证据**（逐字摘自上述行号）

```
                filename = os.path.join(dirname, file)
                file = open(filename,"r")
                data = file.read()
```

**触发条件 / 前提**

源码已确认：文件路径由用户输入拼接，未使用 os.path.realpath + 前缀校验，也没有限定扩展名/目录。

**数据流（输入 → 危险操作）**

POST /ssrf_lab 的 blog -> os.path.join(dirname, file) -> open(filename,'r').read() -> 模板 {{blog}} 输出。

**修复方向**

不要接受用户提供的相对路径。用固定 id→文件名映射（如 blog1..blog4 白名单），或对 realpath 结果做 os.path.realpath(...).startswith(allowed_dir + os.sep) 校验，并限制扩展名。

**验证状态**：`static_analysis_only`

---

## finding-009 — yaml.load 非安全 Loader 导致 RCE

- **位置**：`introduction/views.py` 第 560 行第 28 列 至 第 563 行第 24 列
- **CWE**：CWE-502　**严重度**：critical　**置信度**：high

**问题说明与根因**

a9_lab() 用 yaml.load(file, yaml.Loader) 解析用户上传的 YAML 文件。PyYAML 的 Loader（requirements.txt 固定 PyYAML==5.1）支持 !!python/object/apply 等Python 专属标签，会在构造对象时调用任意可调用对象，等同于反序列化 RCE；应使用 yaml.safe_load。

**代码证据**（逐字摘自上述行号）

```
                    data = yaml.load(file,yaml.Loader)
                    
                    return render(request,"Lab/A9/a9_lab.html",{"data":data})
                except:
```

**触发条件 / 前提**

源码已确认：yaml.load(..., yaml.Loader) 明确使用非安全 Loader；PyYAML==5.1（requirements.txt:27）。部署环境需确认（本次仅静态分析）：运行环境按 requirements.txt 安装依赖。

**数据流（输入 → 危险操作）**

POST /a9_lab 上传 file -> request.FILES['file'] -> yaml.load(file, yaml.Loader) -> 解析结果作为 data 渲染回页面。

**修复方向**

改用 yaml.safe_load（或 yaml.load(file, Loader=yaml.SafeLoader)），并校验上传文件的类型/大小；若需要复杂结构，改用 JSON 并做 schema 校验。

**验证状态**：`static_analysis_only`

---

## finding-010 — PIL.ImageMath.eval 表达式注入

- **位置**：`introduction/views.py` 第 588 行第 22 列 至 第 592 行第 49 列
- **CWE**：CWE-95　**严重度**：high　**置信度**：medium

**问题说明与根因**

a9_lab2() 把 POST 参数 function 直接传给 PIL.ImageMath.eval()。ImageMath.eval 内部会对表达式做 Python 编译/求值（Pillow 9.4.0 的 ImageMath 仍接受任意 lambda/expression），登录用户可用形如 <lambda> 的表达式或借助 r/g/b 变量构造 Python 求值，从而在服务器上执行代码；上传文件本身也没有类型/大小限制。

**代码证据**（逐字摘自上述行号）

```
            output = ImageMath.eval(function_str,img = img, b=b, r=r, g=g)

            # saving the image 
            buffered = BytesIO()
            output.save(buffered, format="JPEG")
```

**触发条件 / 前提**

源码已确认：function_str = request.POST.get("function") 未校验即进入 ImageMath.eval。部署环境需确认（本次仅静态分析）：实际可利用性取决于 Pillow 9.4.0 中 ImageMath 的表达式求值能力，需运行时确认（本次仅静态分析）。

**数据流（输入 → 危险操作）**

POST /a9_lab2 的 function + file -> Image.open/convert -> ImageMath.eval(function_str, img=..., r=..., g=..., b=...) -> 结果保存为图片并以 base64 回显。

**修复方向**

不要用任意表达式驱动 ImageMath：把可用的图像运算改为固定枚举（例如 choices = {'gray', 'invert', ...}）由服务端映射到预定义表达式；同时限制上传文件的 MIME/尺寸。

**验证状态**：`static_analysis_only`

---

## finding-011 — Django 模板 SSTI（用户内容写成模板并渲染）

- **位置**：`introduction/views.py` 第 984 行第 20 列 至 第 1008 行第 44 列
- **CWE**：CWE-1336　**严重度**：critical　**置信度**：high

**问题说明与根因**

ssti_lab() 把用户提交的 blog 正文写入 introduction/templates/.../Blogs/<id>.html，再由 ssti_view_blog() 用 render(request, f"Lab_2021/A3_Injection/Blogs/{blog_id}.html") 当作 Django 模板渲染。唯一 supposed-to-sanitize 的 filter_blog() 在 introduction/utility.py:55-56 只是 `return code`，因此 Django 模板标签与过滤器会原样执行，构成服务端模板注入（SSTI）；攻击者可借 {{ ... }} / {% include %} / with+format 等组合访问模板上下文中的 request、settings 与 Python 对象，在依赖配置下升级为远程代码执行。

**代码证据**（逐字摘自上述行号）

```
            blog = filter_blog(blog)
            prepend_code = "{% extends 'introduction/base.html' %}\
                {% block content %}{% block title %}\
                <title>SSTI-Blogs</title>\
                {% endblock %}"
            
            blog = prepend_code + blog + "{% endblock %}"
            new_blog = Blogs.objects.create(author = request.user, blog_id = id)
            new_blog.save() 
            dirname = os.path.dirname(__file__)
            filename = os.path.join(dirname, f"templates/Lab_2021/A3_Injection/Blogs/{id}.html")
            file = open(filename, "w+") 
            file.write(blog)
            file.close()
            return redirect(f'blog/{id}')
    else:
        return redirect('login')


def ssti_view_blog(request,blog_id):
    if request.user.is_authenticated:
        if request.method=="GET":
            return render(request,f"Lab_2021/A3_Injection/Blogs/{blog_id}.html")
        elif request.method=="POST":
            return HttpResponseBadRequest()
```

**触发条件 / 前提**

源码已确认：写入的目录在 APP_DIRS 模板搜索路径内；filter_blog 为空实现；blog_id 由 uuid 末段生成并落库。

**数据流（输入 → 危险操作）**

POST /ssti/lab 的 blog -> filter_blog()（无过滤）-> open(filename,'w+').write(blog) -> 重定向 /ssti/blog/<id> -> render(f"...Blogs/{blog_id}.html") 模板求值。

**修复方向**

禁止把用户内容作为模板渲染。改为把博客正文作为数据存入数据库，在固定模板中以变量（自动转义）输出；若确需富文本，使用 bleach/ nh3 做 HTML 白名单清洗，并确保 filter_blog 不再是空实现。

**验证状态**：`static_analysis_only`

---

## finding-012 — 反射型 XSS（{{query|safe}}）

- **位置**：`introduction/templates/Lab/XSS/xss_lab.html` 第 27 行第 25 列 至 第 27 行第 81 列
- **CWE**：CWE-79　**严重度**：high　**置信度**：high

**问题说明与根因**

xss_lab() 在查询的公司不存在时把 GET 参数 q 作为 query 传入模板，模板用 {{query|safe}} 输出，关闭了 Django 的自动 HTML 转义。攻击者可构造 /xssL?q=<script>alert(document.cookie)</script> 之类的反射型 XSS，在已登录用户浏览器中执行脚本、窃取会话或代为发起操作。

**代码证据**（逐字摘自上述行号）

```
    <h3> The company '{{query|safe}}' You searched for is not Part of FAANG</h3>
```

**触发条件 / 前提**

源码已确认：视图 views.py:96 取 request.GET.get('q','')，views.py:101 直接进上下文；模板使用 |safe。

**数据流（输入 → 危险操作）**

GET /xssL?q= -> views.xss_lab -> render('Lab/XSS/xss_lab.html', {'query': q}) -> {{query|safe}} 原样写入 HTML。

**修复方向**

移除 |safe，使用默认自动转义；若必须输出到特定上下文，按 OWASP XSS 规则做对应上下文编码（HTML 实体/属性/URL/JS），并对 q 做公司名白名单校验。

**验证状态**：`static_analysis_only`

---

## finding-013 — 反射型 XSS（黑名单过滤 + |safe）

- **位置**：`introduction/templates/Lab/XSS/xss_lab_2.html` 第 20 行第 14 列 至 第 20 行第 34 列
- **CWE**：CWE-79　**严重度**：high　**置信度**：high

**问题说明与根因**

xss_lab2() 只做 `strip()` 与 <script>/</script> 字符串替换（views.py:108-113），属于黑名单式过滤；模板又以 {{ username|safe }} 输出。攻击者可用 <img src=x onerror=...>、<svg onload=...> 或 <ScRiPt> 大小写/嵌套标签绕过过滤，实现反射型 XSS。

**代码证据**（逐字摘自上述行号）

```
<p>Hello, {{ username|safe }}</p>
```

**触发条件 / 前提**

源码已确认：views.py 的 replace 仅移除精确的 "<script>"、"</script>" 字面量；模板对 username 使用 |safe。

**数据流（输入 → 危险操作）**

POST /xssL2 的 username -> strip/replace 黑名单 -> context['username'] -> {{ username|safe }}。

**修复方向**

删除“去掉 <script>”这类黑名单过滤，改为不关闭转义（{{ username }}）；如需展示富文本，使用成熟 sanitizer 的标签/属性白名单。

**验证状态**：`static_analysis_only`

---

## finding-014 — 反射型 XSS（GET 参数 + |safe）

- **位置**：`introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html` 第 11 行第 11 列 至 第 11 行第 34 列
- **CWE**：CWE-79　**严重度**：high　**置信度**：high

**问题说明与根因**

software_and_data_integrity_failure_lab2() 把 GET 参数 username 直接放入上下文（views.py:1220-1226），模板以 {{username | safe}} 输出，形成反射型 XSS；表单本身使用 method="get"，因此可通过恶意链接投递给任意已登录用户。

**代码证据**（逐字摘自上述行号）

```
<h1>Hey {{username | safe}},</h1>
```

**触发条件 / 前提**

源码已确认：views.py:1222 request.GET["username"] 无过滤；模板使用 |safe。

**数据流（输入 → 危险操作）**

GET /2021/A8/lab2?username=<svg onload=...> -> render(..., {"username":username}) -> {{username | safe}}。

**修复方向**

去掉 |safe 并让 username 走默认转义；GET 参数不应直接作为 HTML 片段输出。

**验证状态**：`static_analysis_only`

---

## finding-015 — XSS（SSRF 响应以 |safe 输出）

- **位置**：`introduction/templates/Lab/ssrf/ssrf_lab2.html` 第 23 行第 72 列 至 第 23 行第 94 列
- **CWE**：CWE-79　**严重度**：medium　**置信度**：high

**问题说明与根因**

ssrf_lab2 把服务端抓取回来的远端响应体以 {{response | safe}} 直接嵌入页面。攻击者让 url 指向自己控制的主机并返回 HTML/JS，即可在本应用同源上下文中执行脚本（存储于一次请求内的 XSS），配合 finding-007 的 SSRF 可读取并回显内网响应。

**代码证据**（逐字摘自上述行号）

```
        <div style="width:70%;overflow:scroll;background-color:#000">{{response | safe}}<div>
```

**触发条件 / 前提**

源码已确认：response.content.decode() 未转义进入模板；模板使用 |safe。

**数据流（输入 → 危险操作）**

POST /ssrf_lab2 的 url -> requests.get(url) -> response.content -> {{response | safe}} -> 浏览器解析为 HTML。

**修复方向**

不要用 |safe 输出远端响应。将响应作为纯文本渲染（默认转义 + <pre>），或只提取受控字段；同时对 finding-007 的 SSRF 做出口限制。

**验证状态**：`static_analysis_only`

---

## finding-016 — DOM XSS（innerHTML 写入服务端日志）

- **位置**：`introduction/static/js/a9.js` 第 40 行第 13 列 至 第 42 行第 10 列
- **CWE**：CWE-79　**严重度**：medium　**置信度**：medium

**问题说明与根因**

前端把 /2021/discussion/A9/api 返回的 logs 数组逐条写入 li.innerHTML。这些日志行来源于用户可影响的写入内容（见 finding-017：log_code/api_code 由请求体提供），因此含 HTML/JS 的日志行会在页面中作为标记执行，构成 DOM 型 XSS。

**代码证据**（逐字摘自上述行号）

```
            li.innerHTML = data.logs[i];
            document.getElementById("a9_d3").appendChild(li);
        }
```

**触发条件 / 前提**

源码已确认：使用 innerHTML 而非 textContent/innerText；数据来自接口返回的 logs 字段。

**数据流（输入 → 危险操作）**

POST 响应 JSON 的 logs[i] -> li.innerHTML -> DOM 解析执行。

**修复方向**

把 li.innerHTML = data.logs[i] 改为 li.textContent = data.logs[i]；若确需标记，使用文档片段与显式创建的元素，不解析服务端返回字符串。

**验证状态**：`static_analysis_only`

---

## finding-017 — 未认证接口写入被 import 的源码文件（代码注入）

- **位置**：`introduction/apis.py` 第 67 行第 9 列 至 第 88 行第 79 列
- **CWE**：CWE-94　**严重度**：critical　**置信度**：high

**问题说明与根因**

log_function_checker() 的 @authentication_decorator 被注释掉（apis.py:60），任何未认证访问者都能通过 POST 的 log_code / api_code 字段把任意内容写入 introduction/playground/A9/main.py 与 introduction/playground/A9/api.py。这两个模块会被应用 import（introduction/urls.py:3 直接 `from introduction.playground.A9.api import log_function_target`），因此写入的 Python 源码会在下次进程加载/reload 时被执行，等同未授权远程代码执行；同时该接口还会把写入的日志内容回读返回（配合 finding-016）。

**代码证据**（逐字摘自上述行号）

```
        log_filename = os.path.join(dirname, "playground/A9/main.py")
        api_filename = os.path.join(dirname, "playground/A9/api.py")
        f = open(log_filename,"w")
        f.write(log_code)
        f.close()
        f = open(api_filename,"w")
        f.write(api_code)
        f.close()
        # Clearing the log file before starting the test
        f = open('test.log', 'w')
        f.write("")
        f.close()
        url = "http://127.0.0.1:8000/2021/discussion/A9/target"
        payload={'csrfmiddlewaretoken': csrf_token }
        requests.request("GET", url)
        requests.request("POST", url)
        requests.request("PATCH", url, data=payload)
        requests.request("DELETE", url)
        f = open('test.log', 'r')
        lines = f.readlines()
        f.close()
        return JsonResponse({"message":"success", "logs": lines},status = 200)
```

**触发条件 / 前提**

源码已确认：路由 introduction/urls.py:83 暴露该视图；@csrf_exempt 且鉴权装饰器被注释；写入路径为应用源码目录。部署环境需确认（本次仅静态分析）：运行方式需支持代码重新加载（Dockerfile 中源码随镜像分发，docker-compose 以 .:/app 挂载卷，写入可持久生效）。

**数据流（输入 → 危险操作）**

未认证 POST /2021/discussion/A9/api 的 log_code/api_code -> open(log_filename,'w').write(...) -> 被 import 的模块 -> 解释器执行攻击者代码。

**修复方向**

恢复并强制鉴权（去掉被注释的装饰器即可 fail-open），并且不要写入应用源码文件：把待检查代码放到内存/临时目录、以独立低权限子进程运行，或改用只读的字符串静态检查。同时移除 @csrf_exempt。

**验证状态**：`static_analysis_only`

---

## finding-018 — 未认证接口写入被 import 的源码文件（代码注入）

- **位置**：`introduction/apis.py` 第 132 行第 9 列 至 第 137 行第 69 列
- **CWE**：CWE-94　**严重度**：critical　**置信度**：high

**问题说明与根因**

A6_disscussion_api_2() 没有任何身份认证检查（只判断 method != POST），并把 POST 的 code 字段原样写入 introduction/playground/A6/utility.py。该模块被 introduction/apis.py:9 `from introduction.playground.A6.utility import check_vuln` 导入，因此未认证攻击者可写入任意 Python 源码并在模块重新加载时执行，导致远程代码执行。

**代码证据**（逐字摘自上述行号）

```
        filename = os.path.join(dirname, "playground/A6/utility.py")
        f = open(filename,"w")
        f.write(code)
        f.close()
    except:
        return JsonResponse({"message":"missing code"},status = 400)
```

**触发条件 / 前提**

源码已确认：路由 introduction/urls.py:89；视图内无 is_authenticated 判断；写入目标位于应用包内并被 import。

**数据流（输入 → 危险操作）**

未认证 POST /2021/discussion/A6/api2 的 code -> os.path.join(dirname,'playground/A6/utility.py') -> open(filename,'w').write(code) -> import 时执行。

**修复方向**

为视图加身份与角色校验，并停止把用户内容写入被 import 的模块；改为将代码作为字符串分析，或在隔离沙箱中以固定文件名运行。

**验证状态**：`static_analysis_only`

---

## finding-019 — 登录用户可覆盖应用源码文件（代码注入）

- **位置**：`introduction/utility.py` 第 34 行第 39 列 至 第 37 行第 14 列
- **CWE**：CWE-94　**严重度**：high　**置信度**：high

**问题说明与根因**

ssrf_code_converter() 从用户提交的 Python 代码文本中按行截取内容，拼接后写入 introduction/playground/ssrf/main.py（该模块被 apis.py:10 import 并调用 main.ssrf_lab）。调用方 apis.ssrf_code_checker 只要求已登录，因此任何普通登录用户都能覆盖应用源码文件，注入额外 Python 语句以获得代码执行，且写入在容器/卷挂载下可持久化。

**代码证据**（逐字摘自上述行号）

```
    filename = os.path.join(dirname, "playground/ssrf/main.py")
    f = open(filename,"w")
    f.write(output_Code)
    f.close()
```

**触发条件 / 前提**

源码已确认：写入文件名硬编码在应用包内；内容来自 request.POST['python_code'] 的行切片，未做任何语法白名单。

**数据流（输入 → 危险操作）**

POST /api/ssrf 的 python_code -> ssrf_code_converter() -> open(filename,'w').write(output_Code) -> 后续 import/调用 playground.ssrf.main。

**修复方向**

同 finding-017/018：不生成可被导入的源码文件。把学生代码保存到应用目录之外的一次性临时目录，并以独立进程 + 最小权限执行，路径由服务端生成。

**验证状态**：`static_analysis_only`

---

## finding-020 — 未认证 eval() RCE

- **位置**：`introduction/mitre.py` 第 215 行第 1 列 至 第 218 行第 34 列
- **CWE**：CWE-95　**严重度**：critical　**置信度**：high

**问题说明与根因**

mitre_lab_25_api() 只有 @csrf_exempt，既没有 @authentication_decorator（同文件其他 mitre 视图都有），也不做任何输入校验，直接把 POST 的 expression 交给 eval() 并以 JSON 返回结果。未认证攻击者可执行任意 Python 表达式，实现远程代码执行与数据读取。

**代码证据**（逐字摘自上述行号）

```
def mitre_lab_25_api(request):
    if request.method == "POST":
        expression = request.POST.get('expression')
        result = eval(expression)
```

**触发条件 / 前提**

源码已确认：路由 introduction/urls.py:119；视图上无鉴权装饰器；返回值直接进 JsonResponse。

**数据流（输入 → 危险操作）**

未认证 POST /mitre/25/lab/api 的 expression -> eval(expression) -> JsonResponse({'result': result})。

**修复方向**

删除 eval，改为按表达式类型受理解析（白名单运算符）；同时补上 @authentication_decorator 与 CSRF 保护，并对失败请求做限速。

**验证状态**：`static_analysis_only`

---

## finding-021 — 未认证 nmap 命令注入

- **位置**：`introduction/mitre.py` 第 241 行第 9 列 至 第 243 行第 27 列
- **CWE**：CWE-78　**严重度**：critical　**置信度**：high

**问题说明与根因**

mitre_lab_17_api() 未认证（无 authentication_decorator，仅 @csrf_exempt），把 POST 的 ip 直接字符串拼进 "nmap " + ip 并交给 subprocess.Popen(shell=True) 执行，同时把命令的 stdout 与 stderr 原样返回给调用者。提交 `; cat /etc/passwd` 或 `$(id)` 即可获得未授权远程命令执行。

**代码证据**（逐字摘自上述行号）

```
        command = "nmap " + ip 
        res, err = command_out(command)
        res = res.decode()
```

**触发条件 / 前提**

源码已确认：路由 introduction/urls.py:122；command_out() 使用 shell=True；raw_res/raw_err 直接返回。

**数据流（输入 → 危险操作）**

未认证 POST /mitre/17/lab/api 的 ip -> "nmap " + ip -> command_out(command) -> subprocess.Popen(command, shell=True) -> JsonResponse 回显。

**修复方向**

使用参数列表 subprocess.run(["nmap", "-Pn", ip], shell=False)，并对 ip 做 IP/主机名格式白名单校验；补上身份认证与 CSRF 防护、请求限速。

**验证状态**：`static_analysis_only`

---

## finding-022 — 转账接口用 GET 且无 CSRF/鉴权

- **位置**：`introduction/mitre.py` 第 191 行第 1 列 至 第 209 行第 10 列
- **CWE**：CWE-352　**严重度**：high　**置信度**：high

**问题说明与根因**

csrf_transfer_monei_api() 是执行资金转移的写操作端点，却只接受 GET 请求、没有 @authentication_decorator 也没有 @csrf_exempt 之外的任何 CSRF 防护，收款人与金额直接来自 URL 路径参数。攻击者只需诱导已登录受害者访问 /mitre/9/lab/api/<attacker>/<amount> 即可完成转账（CSRF），同时 GET 语义使该操作可被预取、代理日志与 Referer 泄露。

**代码证据**（逐字摘自上述行号）

```
def csrf_transfer_monei_api(request,recipent,amount):
    if request.method == "GET":
        cookie = request.COOKIES['auth_cookiee']
        payload = jwt.decode(cookie, 'csrf_vulneribility', algorithms=['HS256'])
        username = payload['username']
        User = CSRF_user_tbl.objects.filter(username=username)
        if not User:
            return redirect('/mitre/9/lab/login')
        if int(amount) > 0:
            if int(amount) <= User[0].balance:
                recipent = CSRF_user_tbl.objects.filter(username=recipent)
                if recipent:
                    recipent = recipent[0]
                    recipent.balance = recipent.balance + int(amount)
                    recipent.save()
                    User[0].balance = User[0].balance - int(amount)
                    User[0].save()
        return redirect('/mitre/9/lab/transaction') 
    else:
```

**触发条件 / 前提**

源码已确认：路由 introduction/urls.py:118 使用 <str:recipent>/<int:amount>；函数内仅校验 JWT Cookie 与余额。

**数据流（输入 → 危险操作）**

GET /mitre/9/lab/api/<recipent>/<amount>（受害者浏览器自动携带 auth_cookiee）-> jwt.decode 取当前用户 -> 修改双方 balance 并 save()。

**修复方向**

资金转移必须是 POST + CSRF 令牌 + 显式身份校验（@authentication_decorator 或 django.contrib.auth 装饰器），并加入二次确认（如交易签名/幂等 token）。

**验证状态**：`static_analysis_only`

---

## finding-023 — JWT 签名密钥硬编码

- **位置**：`introduction/mitre.py` 第 169 行第 22 列 至 第 170 行第 60 列
- **CWE**：CWE-798　**严重度**：high　**置信度**：high

**问题说明与根因**

该 CSRF 实验模块把 JWT 签名密钥以字面量 'csrf_vulneribility' 硬编码在源码中（mitre.py:169/182/194），用于签发和校验 auth_cookiee。任何能读到源码的人都可以自行伪造任意 username 的令牌，冒充任意用户访问 /mitre/9/lab/transaction 与转账接口；密钥也无法随环境轮换。

**代码证据**（逐字摘自上述行号）

```
            cookie = jwt.encode(payload, 'csrf_vulneribility', algorithm='HS256')
            response = redirect("/mitre/9/lab/transaction")
```

**触发条件 / 前提**

源码已确认：签名与校验均使用同一硬编码字符串；algorithms=['HS256'] 固定。

**数据流（输入 → 危险操作）**

攻击者离线伪造 jwt.encode({'username': '<victim>'}, 'csrf_vulneribility') -> 设置 auth_cookiee -> csrf_transfer_monei / csrf_transfer_monei_api 通过校验。

**修复方向**

把签名密钥移出源码，改由环境变量/密钥管理注入，按环境区分并支持轮换；或直接用 Django session 替代自制 JWT。

**验证状态**：`static_analysis_only`

---

## finding-024 — 口令使用 MD5 摘要

- **位置**：`introduction/mitre.py` 第 161 行第 20 列 至 第 162 行第 82 列
- **CWE**：CWE-327　**严重度**：medium　**置信度**：high

**问题说明与根因**

csrf_lab_login() 用 MD5 对口令做单次无盐摘要后再与数据库中的 password 比对。MD5 已被证明不适合口令存储（碰撞与GPU高速破解），且此处无慢哈希、无盐，一旦 CSRF_user_tbl 泄露可被离线还原；同时该端点自身也没有登录尝试次数限制。

**代码证据**（逐字摘自上述行号）

```
        password = md5(password.encode()).hexdigest()
        User = CSRF_user_tbl.objects.filter(username=username, password=password)
```

**触发条件 / 前提**

源码已确认：from hashlib import md5（mitre.py:5）；仅做 md5(...).hexdigest()。

**数据流（输入 → 危险操作）**

POST /mitre/9/lab/login 的 password -> md5 摘要 -> CSRF_user_tbl.objects.filter(username=..., password=<md5>) 比对。

**修复方向**

使用 Django 自带的口令哈希（django.contrib.auth.hashers.make_password/check_password，argon2/pbkdf2），不要用 MD5；并补充登录失败锁定。

**验证状态**：`static_analysis_only`

---

## finding-025 — JWT SECRET_COOKIE_KEY="PYGOAT" 硬编码

- **位置**：`pygoat/settings.py` 第 171 行第 1 列 至 第 171 行第 29 列
- **CWE**：CWE-798　**严重度**：high　**置信度**：high

**问题说明与根因**

JWT 会话签名密钥 SECRET_COOKIE_KEY 被硬编码为极弱常量 "PYGOAT"。introduction/views.py:1090-1109 的 sec_misconfig_lab3 用它签发/校验 auth_cookie，并仅依据 payload['user'] == 'admin' 判定管理员；攻击者可用该常量离线伪造 user=admin 的 HS256 令牌，直接获得管理视图，属于硬编码凭据 + 弱密钥的组合。

**代码证据**（逐字摘自上述行号）

```
SECRET_COOKIE_KEY = "PYGOAT"
```

**触发条件 / 前提**

源码已确认：settings.py:171 明文常量；views.py:1088 `from pygoat.settings import SECRET_COOKIE_KEY`。部署环境需确认（本次仅静态分析）：该密钥随源码分发，任何公开部署都一样。

**数据流（输入 → 危险操作）**

离线 jwt.encode({'user':'admin',...}, "PYGOAT", 'HS256') -> 请求 Cookie: auth_cookie -> jwt.decode 校验通过 -> 渲染 admin=True 页面。

**修复方向**

SECRET_COOKIE_KEY 改为从环境变量读取的高熵密钥并支持轮换；对管理员判定应使用服务端角色，而不是 Cookie/JWT 中可自填的 user 字段。

**验证状态**：`static_analysis_only`

---

## finding-026 — Django SECRET_KEY/SENSITIVE_DATA 硬编码

- **位置**：`pygoat/settings.py` 第 25 行第 1 列 至 第 28 行第 1 列
- **CWE**：CWE-798　**严重度**：high　**置信度**：high

**问题说明与根因**

Django 的 SECRET_KEY 与 SENSITIVE_DATA（'FLAGTHATNEEDSTOBEFOUND'）以明文硬编码在版本库中。SECRET_KEY 用于签名 session、Cookie、password reset 等；泄露后攻击者可伪造任意用户的 session，绕过认证。密钥随源码分发即等同于公开，且无法区分环境。

**代码证据**（逐字摘自上述行号）

```
SECRET_KEY = 'lr66%-a!$km5ed@n5ug!tya5bv!0(yqwa1tn!q%0%3m2nh%oml'

SENSITIVE_DATA = 'FLAGTHATNEEDSTOBEFOUND'

```

**触发条件 / 前提**

源码已确认：settings.py:25 SECRET_KEY 明文，settings.py:27 SENSITIVE_DATA 明文；注释自述应保持秘密。

**数据流（输入 → 危险操作）**

读取源码中的 SECRET_KEY -> 用 django.core.signing / session 序列化伪造 signed_cookies session -> 冒充任意用户（若使用签名 Cookie session 后端）。

**修复方向**

SECRET_KEY 与任何业务机密都不应写进源码：改用环境变量或密钥管理服务注入，泄露后必须轮换；SENSITIVE_DATA 之类的答案不应放在 settings 中随源码分发。

**验证状态**：`static_analysis_only`

---

## finding-027 — DEBUG=True 与宽松 ALLOWED_HOSTS

- **位置**：`pygoat/settings.py` 第 30 行第 1 列 至 第 33 行第 1 列
- **CWE**：CWE-489　**严重度**：medium　**置信度**：high

**问题说明与根因**

配置以 DEBUG = True 交付，且 ALLOWED_HOSTS 写成 ['pygoat.herokuapp.com', '0.0.0.0.'] 这类宽泛/畸形条目。DEBUG 开启时未处理异常会向客户端输出完整 traceback（含本地绝对路径、settings 与请求数据），并启用 Django 可调试页面与详细 500 输出，属于敏感信息泄露； ALLOWED_HOSTS 过于宽松会削弱 Host 头校验。

**代码证据**（逐字摘自上述行号）

```
DEBUG = True

ALLOWED_HOSTS = ['pygoat.herokuapp.com', '0.0.0.0.']

```

**触发条件 / 前提**

源码已确认：settings.py:30 DEBUG=True；无环境区分。部署环境需确认（本次仅静态分析）：是否以该配置直接对外提供服务需部署确认。

**数据流（输入 → 危险操作）**

不适用（配置型缺陷）：DEBUG/ALLOWED_HOSTS 直接影响所有视图的错误响应内容与 Host 校验，无需特定数据流。

**修复方向**

DEBUG 必须由环境变量控制且生产为 False；ALLOWED_HOSTS 收紧为确切域名列表（不要写 '0.0.0.0.'），并配合 SECURE_SSL_REDIRECT。

**验证状态**：`static_analysis_only`

---

## finding-028 — 缺少全部 HTTPS/安全 Cookie/点击劫持相关设置

- **位置**：`pygoat/settings.py` 第 55 行第 1 列 至 第 66 行第 29 列
- **CWE**：CWE-614　**严重度**：medium　**置信度**：high

**问题说明与根因**

MIDDLEWARE 与 settings 中完全没有 HTTPS/安全 Cookie 相关配置：未设置 SESSION_COOKIE_SECURE、CSRF_COOKIE_SECURE、SECURE_SSL_REDIRECT、SECURE_HSTS_SECONDS、SECURE_CONTENT_TYPE_NOSNIFF、SECURE_REFERRER_POLICY、X_FRAME_OPTIONS 等，也没有任何 Content-Security-Policy 输出（全仓库 grep 无 SECURE_/CSP 配置）。登录站点在明文 HTTP 下会同时泄露 sessionid/csrf 令牌，并缺少点击劫持与 MIME 嗅探防护，放大了本仓库中多处 XSS 发现的影响。

**代码证据**（逐字摘自上述行号）

```
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pygoat.urls'
```

**触发条件 / 前提**

源码已确认：settings.py:55-66 的 MIDDLEWARE 仅含 Django 默认项；文件末尾无 SECURE_*/COOKIE_SECURE 设置。部署环境需确认（本次仅静态分析）：生产是否置于 HTTPS 反代之后需确认。

**数据流（输入 → 危险操作）**

不适用（配置缺失型）：缺少的是安全检查，影响体现在所有认证流量与 Cookie 上。

**修复方向**

补齐 Django 安全设置：SESSION_COOKIE_SECURE=True、CSRF_COOKIE_SECURE=True、SECURE_SSL_REDIRECT=True、SECURE_HSTS_SECONDS、SECURE_CONTENT_TYPE_NOSNIFF、SECURE_REFERRER_POLICY、X_FRAME_OPTIONS='DENY'，并评估加入 CSP。

**验证状态**：`static_analysis_only`

---

## finding-029 — 未签名可拼装的 admin 会话 Cookie

- **位置**：`introduction/views.py` 第 1060 行第 22 列 至 第 1063 行第 143 列
- **CWE**：CWE-565　**严重度**：high　**置信度**：high

**问题说明与根因**

crypto_failure_lab3() 以 `角色|过期时间` 这种可预测、无签名、无服务端状态的字符串作为会话凭据，并直接以 cookie.split('|')[0] == 'admin' 授予管理员视图。任何普通登录用户只需把 Cookie 改成 `admin|<未来时间>` 即可越权成为 admin，且该令牌不包含任何可校验的身份绑定。

**代码证据**（逐字摘自上述行号）

```
                elif cookie.split('|')[0] == 'admin':
                    return render(request,"Lab_2021/A2_Crypto_failur/crypto_failure_lab3.html",{"success":True,"failure":False,"admin":True})
                else:
                    return render(request,"Lab_2021/A2_Crypto_failur/crypto_failure_lab3.html",{"success":True,"failure":False,"admin":False})
```

**触发条件 / 前提**

源码已确认：views.py:1073-1076 仅设置明文 cookie=f"{username}|{expire}"，set_cookie 未加 secure/httponly 之外的完整性保护。

**数据流（输入 → 危险操作）**

Cookie: cookie=admin|2999-01-01T00:00:00 -> fromisoformat 解析通过 -> now > expire 为假 -> 分支判定 admin=True -> 返回管理员页面。

**修复方向**

不要用可自行拼装的字符串作会话凭据：改为 Django session 或带签名/加密且含过期与用户绑定的令牌，角色信息由服务端权威数据决定。

**验证状态**：`static_analysis_only`

---

## finding-030 — 口令使用 MD5（CF_user）

- **位置**：`introduction/views.py` 第 1026 行第 28 列 至 第 1027 行第 91 列
- **CWE**：CWE-327　**严重度**：medium　**置信度**：high

**问题说明与根因**

crypto_failure_lab() 使用 MD5（无盐、单次）对口令做摘要后与 CF_user.password 比对，作为“身份验证”实现。这属于使用已被认为不安全的哈希算法保护凭据：数据库一旦外泄可被字典/GPU 快速还原，且此处也没有登录失败限速。

**代码证据**（逐字摘自上述行号）

```
                password = md5(password.encode()).hexdigest()
                user = CF_user.objects.filter(username=username,password=password).first()
```

**触发条件 / 前提**

源码已确认：from hashlib import md5（views.py:15）；password = md5(...).hexdigest() 后直接进 filter。

**数据流（输入 → 危险操作）**

POST /cryptographic_failure/lab 的 username/password -> md5 摘要 -> CF_user.objects.filter(username=..., password=<md5>)。

**修复方向**

改用 django.contrib.auth.hashers 或 argon2/bcrypt 的加盐慢哈希；CF_user.password 字段应存储可校验的哈希串而非固定摘要。

**验证状态**：`static_analysis_only`

---

## finding-031 — 自制哈希（无盐 sha256 反转）

- **位置**：`introduction/views.py` 第 1042 行第 28 列 至 第 1044 行第 138 列
- **CWE**：CWE-916　**严重度**：medium　**置信度**：high

**问题说明与根因**

crypto_failure_lab2() 使用自定义哈希 customHash()，其实现是 hashlib.sha256(password).hexdigest() 后做字符串反转（introduction/utility.py:58-59）。反转不增加任何强度：依旧是单轮、无盐、高速摘要，等价于 unsalted SHA-256，不符合口令存储要求（应使用 argon2/bcrypt/PBKDF2 等带盐慢哈希）。

**代码证据**（逐字摘自上述行号）

```
                password = customHash(password)
                user = CF_user.objects.filter(username=username,password2=password).first()
                return render(request,"Lab_2021/A2_Crypto_failur/crypto_failure_lab2.html",{"user":user, "success":True,"failure":False})
```

**触发条件 / 前提**

源码已确认：utility.py:58-59 定义；views.py:1042 调用并与 CF_user.password2 比对。

**数据流（输入 → 危险操作）**

POST /cryptographic_failure/lab2 的 password -> customHash -> CF_user.objects.filter(username=..., password2=<reversed sha256>)。

**修复方向**

删除 customHash 这类自制哈希，统一使用 Django 口令哈希器（带盐、可调工作因子）。

**验证状态**：`static_analysis_only`

---

## finding-032 — 认证依赖源码中的硬编码账号表

- **位置**：`introduction/views.py` 第 1163 行第 1 列 至 第 1168 行第 2 列
- **CWE**：CWE-798　**严重度**：medium　**置信度**：high

**问题说明与根因**

auth_failure_lab3() 的认证完全依赖硬编码在源码里的 USER_A7_LAB3 字典（含 4 个账号的口令摘要），同文件 a1_broken_access_lab_1/2/3 也硬编码了 jack/jacktheripper、John/reaper、admin/admin_pass （views.py:766、806、830-833）。硬编码凭据一旦随源码公开即等同于泄露，无法轮换、无法撤销，任何知道常量的人都可以直接通过认证。

**代码证据**（逐字摘自上述行号）

```
USER_A7_LAB3 = {
    "User1":{"userid":"1", "username":"User1", "password": "491a2800b80719ea9e3c89ca5472a8bda1bdd1533d4574ea5bd85b70a8e93be0"},
    "User2":{"userid":"2", "username":"User2", "password": "c577e95bf729b94c30a878d01155693a9cdddafbb2fe0d52143027474ecb91bc"},
    "User3":{"userid":"3", "username":"User3", "password": "5a91a66f0c86b5435fe748706b99c17e6e54a17e03c2a3ef8d0dfa918db41cf6"},
    "User4":{"userid":"4", "username":"User4", "password": "6046bc3337728a60967a151ee584e4fd7c53740a49485ebdc38cac42a255f266"}
}
```

**触发条件 / 前提**

源码已确认：凭据以 Python 常量形式写在视图模块中，直接参与密码比对分支。

**数据流（输入 → 危险操作）**

POST /auth_failure/lab3 的 username/password -> sha256(password) -> 与 USER_A7_LAB3[username]['password'] 常量比较 -> 相等即创建会话并下发 session_id Cookie。

**修复方向**

把演示账号移到数据库/管理命令初始化，并用加盐哈希存储；生产功能绝不使用源码中的常量凭据作为认证依据。

**验证状态**：`static_analysis_only`

---

## finding-033 — 无盐单轮 SHA-256 口令哈希且无限速

- **位置**：`introduction/views.py` 第 1194 行第 24 列 至 第 1204 行第 53 列
- **CWE**：CWE-916　**严重度**：medium　**置信度**：high

**问题说明与根因**

auth_failure_lab3() 用无盐单轮 SHA-256 保存并比对口令，同时整个流程没有任何失败计数或锁定，可对硬编码账号做离线/在线爆破。作为对比，同文件的 auth_failure_lab2 已正确使用 argon2 PasswordHasher，说明 lab3 是独立的实现缺陷。

**代码证据**（逐字摘自上述行号）

```
            password = hashlib.sha256(password.encode()).hexdigest()
        except:
            response = render(request, "Lab_2021/A7_auth_failure/lab3.html")
            response.set_cookie("session_id", None)
            return response

        if USER_A7_LAB3[username]['password'] == password:
            session_data = AF_session_id.objects.create(session_id=token, user=USER_A7_LAB3[username]['username'])
            session_data.save()
            response = render(request, "Lab_2021/A7_auth_failure/lab3.html", {"success":True, "failure":False, "username":username})
            response.set_cookie("session_id", token)
```

**触发条件 / 前提**

源码已确认：password = hashlib.sha256(...).hexdigest() 后与常量表比对；无限速、无盐。

**数据流（输入 → 危险操作）**

POST /auth_failure/lab3 -> sha256(明文口令) -> USER_A7_LAB3[username]['password'] == password -> AF_session_id.objects.create(session_id=uuid4) -> set_cookie。

**修复方向**

口令改为带盐慢哈希（argon2/bcrypt/Django hasher），并补充失败计数、锁定与限速；避免 KeyError 直接 500。

**验证状态**：`static_analysis_only`

---

## finding-034 — 口令明文入库并明文比对

- **位置**：`introduction/views.py` 第 287 行第 19 列 至 第 292 行第 51 列
- **CWE**：CWE-256　**严重度**：high　**置信度**：high

**问题说明与根因**

auth_lab_signup() 把用户提交的 passwd 原文存入 authLogin.password，auth_lab_login() 再以 filter(username=..., password=...) 直接比对明文（views.py:315）。对应模型 introduction/models.py:30-34 的 password 也只是 CharField，无任何哈希。数据库或备份一旦泄露即直接得到全部用户口令，且明文口令还会进入查询日志/调试输出。

**代码证据**（逐字摘自上述行号）

```
            obj = authLogin.objects.create(name=name,username=user_name,password=passwd)
            try:
                rendered = render_to_string('Lab/AUTH/auth_success.html', {'username': obj.username,'userid':obj.userid,'name':obj.name,'err_msg':'Cookie Set'})
                response = HttpResponse(rendered)
                response.set_cookie('userid', obj.userid, max_age=31449600, samesite=None, secure=False)
                print('Setting cookie successful')
```

**触发条件 / 前提**

源码已确认：create(...password=passwd) 无哈希；登录路径同样明文比较。

**数据流（输入 → 危险操作）**

POST /auth_lab/signup 的 pass -> authLogin.objects.create(password=passwd) -> 数据库明文存储 -> /auth_lab/login 明文 filter 比对。

**修复方向**

authLogin.password 必须存储哈希（推荐直接用 django.contrib.auth 的 User 模型 + authenticate()），登录使用 check_password 而不是明文 filter 比对。

**验证状态**：`static_analysis_only`

---

## finding-035 — 仅凭可猜测 userid Cookie 登录（认证绕过/IDOR）

- **位置**：`introduction/views.py` 第 302 行第 51 列 至 第 307 行第 28 列
- **CWE**：CWE-287　**严重度**：high　**置信度**：high

**问题说明与根因**

auth_lab_login() 的 GET 分支把 userid Cookie 当作唯一的身份凭据：只要 filter(userid=request.COOKIES['userid']) 有结果就直接渲染登录成功页面并续签 Cookie，完全不校验口令或会话。而 userid 是 authLogin 的 AutoField 主键（introduction/models.py:35），是连续可猜的整数，攻击者枚举 1、2、3… 即可冒充任意注册用户（IDOR + 认证绕过）。

**代码证据**（逐字摘自上述行号）

```
            obj = authLogin.objects.filter(userid=request.COOKIES['userid'])[0]
            rendered = render_to_string('Lab/AUTH/auth_success.html', {'username': obj.username,'userid':obj.userid,'name':obj.name, 'err_msg':'Login Successful'})
            response = HttpResponse(rendered)
            response.set_cookie('userid', obj.userid, max_age=31449600, samesite=None, secure=False)
            print('Login successful')
            return response
```

**触发条件 / 前提**

源码已确认：GET /auth_lab/login 无 CSRF/口令校验；userid 为自增主键；Cookie 设置 max_age=31449600（约一年）、secure=False、samesite=None。

**数据流（输入 → 危险操作）**

GET /auth_lab/login + Cookie: userid=<任意整数> -> authLogin.objects.filter(userid=...) -> 命中即返回 auth_success.html（以该用户身份）。

**修复方向**

不要用可猜测的主键 Cookie 作为身份凭据。改为 Django session/签名令牌（含用户绑定与过期），登录必须校验口令，Cookie 加 httponly/secure/samesite。

**验证状态**：`static_analysis_only`

---

## finding-036 — admin Cookie 决定权限（越权）

- **位置**：`introduction/views.py` 第 347 行第 16 列 至 第 364 行第 28 列
- **CWE**：CWE-285　**严重度**：high　**置信度**：high

**问题说明与根因**

ba_lab() 用客户端 Cookie `admin` 的值作为唯一的权限判定：只要 Cookie 里 admin=="1" 就直接返回 "0NLY_F0R_4DM1N5" 机密。该 Cookie 由应用自己在登录时下发（admin=0/1），任何普通登录用户把它改成 1 即可越权读取管理员数据，属于典型的客户端可信授权决策 + 可预测授权标识。

**代码证据**（逐字摘自上述行号）

```
            if request.COOKIES.get('admin') == "1":
                return render(
                    request, 
                    'Lab/BrokenAccess/ba_lab.html', 
                    {
                        "data":"0NLY_F0R_4DM1N5",
                        "username": "admin"
                    })
            elif login.objects.filter(user='admin',password=password):
                html = render(
                    request, 
                    'Lab/BrokenAccess/ba_lab.html', 
                    {
                        "data":"0NLY_F0R_4DM1N5",
                        "username": "admin"
                    })
                html.set_cookie("admin", "1",max_age=200)
                return html
```

**触发条件 / 前提**

源码已确认：views.py:347 直接信任 request.COOKIES；views.py:363 set_cookie("admin","1") 无签名。部署环境需确认（本次仅静态分析）：同样问题在 a1_broken_access_lab_1（views.py:758）以另一处代码重复出现。

**数据流（输入 → 危险操作）**

POST /ba_lab + Cookie: admin=1 -> 跳过 login.objects 口令校验分支 -> 渲染含 data="0NLY_F0R_4DM1N5" 的模板。

**修复方向**

权限判定必须在服务端进行（如 request.user.is_staff 或角色字段），不得读取客户端 admin Cookie；同时移除该视图的 @csrf_exempt。

**验证状态**：`static_analysis_only`

---

## finding-037 — User-Agent 决定管理员权限（越权）

- **位置**：`introduction/views.py` 第 797 行第 13 列 至 第 800 行第 77 列
- **CWE**：CWE-285　**严重度**：high　**置信度**：high

**问题说明与根因**

a1_broken_access_lab_2() 以 User-Agent 字符串是否等于 "pygoat_admin" 判定管理员并返回机密，且 user_agent = request.META['HTTP_USER_AGENT'] 直接取值、未做默认处理。请求头完全由客户端控制，任何登录用户设置该 UA 即可越权；缺失 UA 时还会抛 KeyError 造成 500。

**代码证据**（逐字摘自上述行号）

```
        if (user_agent == "pygoat_admin"):
            return render(
                request, 
                'Lab_2021/A1_BrokenAccessControl/broken_access_lab_2.html', 
```

**触发条件 / 前提**

源码已确认：views.py:791 读取 UA，views.py:796 直接比较常量字符串。

**数据流（输入 → 危险操作）**

POST /broken_access_lab_2 + Header: User-Agent: pygoat_admin -> 命中管理员分支 -> 返回 data="0NLY_F0R_4DM1N5"。

**修复方向**

删除基于 User-Agent 的权限判定；使用服务端角色/权限校验，并对 request.META['HTTP_USER_AGENT'] 改用 .get() 默认值避免异常。

**验证状态**：`static_analysis_only`

---

## finding-038 — 机密页面缺少授权检查

- **位置**：`introduction/views.py` 第 840 行第 7 列 至 第 842 行第 1 列
- **CWE**：CWE-862　**严重度**：high　**置信度**：high

**问题说明与根因**

a1_broken_access_lab3_secret() 只判断 request.user.is_authenticated，随后注释明确写着 “no checking applied here”，直接渲染 secret.html，页面上包含 SOME_SECRET_KEYS = THIS_FILE_CONTAINS_SECRET_INFORMATION。同一实验中的 a1_broken_access_lab_3 已实现 John/admin 两种角色的登录判定，但该机密页面对任何最低权限登录用户开放，属于缺少授权检查（非默认拒绝）。

**代码证据**（逐字摘自上述行号）

```
    # no checking applied here
    return render(request, 'Lab_2021/A1_BrokenAccessControl/secret.html')

```

**触发条件 / 前提**

源码已确认：视图内除 is_authenticated 外无任何角色/权限判断；模板内容为机密（introduction/templates/Lab_2021/A1_BrokenAccessControl/secret.html:7）。

**数据流（输入 → 危险操作）**

任意已登录用户 GET /broken_access_controle/secret -> render('.../secret.html') -> 机密正文返回。

**修复方向**

为机密页面加权限校验（如 @user_passes_test(lambda u: u.is_staff) 或角色判断），实现默认拒绝，而不是只判断是否登录。

**验证状态**：`static_analysis_only`

---

## finding-039 — OTP 直接回显给请求方

- **位置**：`introduction/views.py` 第 506 行第 64 列 至 第 508 行第 28 列
- **CWE**：CWE-200　**严重度**：high　**置信度**：high

**问题说明与根因**

Otp() 在用户不是 admin@pygoat.com 时，把刚刚 randint(100,999) 生成的 OTP 作为模板变量 otp 直接渲染进返回给同一请求发起者的 HTML 页面，等价于把一次性口令写在登录响应里；同时 email 由 GET 参数自由指定，可让服务端把 email 绑定到攻击者选择的值。第二步 POST 只需带上响应中看到的数字即可通过校验，OTP 这一层认证形同不存在。

**代码证据**（逐字摘自上述行号）

```
                html=render (request,"Lab/BrokenAuth/otp.html",{"otp":otpN})
                html.set_cookie("email",email)
                return html
```

**触发条件 / 前提**

源码已确认：otpN 通过 render(..., {"otp":otpN}) 返回；otp 表按 email 更新，email 来自 request.GET 并写入 Cookie。

**数据流（输入 → 危险操作）**

GET /otp?email=victim -> randint -> 响应 HTML 内含明文 otp -> POST /otp（Cookie email + otpR=看到的数字）-> 登录成功分支。

**修复方向**

OTP 只能通过带外通道（邮件/短信）送达，绝不能渲染回发起请求的页面；同时按 email 绑定校验并设置短有效期与尝试上限。

**验证状态**：`static_analysis_only`

---

## finding-040 — 3 位弱 OTP + 不校验身份的 id=2 分支

- **位置**：`introduction/views.py` 第 514 行第 56 列 至 第 516 行第 78 列
- **CWE**：CWE-287　**严重度**：high　**置信度**：high

**问题说明与根因**

OTP 认证存在两个叠加缺陷：口令空间只有 randint(100,999) 共 900 种取值（且 introduction/models.py:37-40 的 otp 字段还带 MaxValueValidator(300)，与实际写入值范围矛盾），并且校验条件为 `filter(email=email,otp=otpR) or filter(id=2,otp=otpR)` —— 第二个分支完全不比较 email，只要猜中管理员（id=2）当前的 3 位数字，任意 Cookie email 的攻击者都能登录为 admin。该视图 @csrf_exempt 且无失败次数限制、无有效期，可被暴力枚举。

**代码证据**（逐字摘自上述行号）

```
        if otp.objects.filter(email=email,otp=otpR) or otp.objects.filter(id=2,otp=otpR):
            # return HttpResponse("<h3>Login Success for email:::"+email+"</h3>")
            return render (request,"Lab/BrokenAuth/otp.html",{"email":email})
```

**触发条件 / 前提**

源码已确认：randint(100,999)；or 条件写死 id=2；无尝试次数或过期约束；@csrf_exempt（views.py:492）。

**数据流（输入 → 危险操作）**

POST /otp 的 otpR -> otp.objects.filter(id=2,otp=otpR) 命中 -> render("Lab/BrokenAuth/otp.html", {"email":email}) 登录成功。

**修复方向**

OTP 使用 secrets.randbelow 生成至少 6 位、服务端存储哈希、绑定 email、设置 60-300 秒有效期与最多 3-5 次尝试；删除 `or filter(id=2, otp=otpR)` 这类不校验身份的分支，并修正 MaxValueValidator(300) 与生成范围不一致的问题。

**验证状态**：`static_analysis_only`

---

## finding-041 — 以 X-Host 请求头做访问控制

- **位置**：`introduction/views.py` 第 536 行第 34 列 至 第 541 行第 1 列
- **CWE**：CWE-290　**严重度**：medium　**置信度**：high

**问题说明与根因**

secret() 以请求头 X-Host 是否等于 'admin.localhost:8000' 作为唯一的访问控制，并且该视图没有任何认证要求。自定义请求头可由任意 HTTP 客户端设置，攻击者直接 `curl -H 'X-Host: admin.localhost:8000' /secret` 即可拿到机密 S3CR37K3Y；另一分支还会把用户提交的头值原样拼进模板上下文回显。

**代码证据**（逐字摘自上述行号）

```
    XHost = request.headers.get('X-Host', 'None')
    if(XHost == 'admin.localhost:8000'):
        return render(request,"Lab/sec_mis/sec_mis_lab.html", {"secret": "S3CR37K3Y"})
    else:
        return render(request,"Lab/sec_mis/sec_mis_lab.html", {"no_secret": "Only admin.localhost:8000 can access, Your X-Host is " + XHost})

```

**触发条件 / 前提**

源码已确认：request.headers.get('X-Host', 'None') 直接用于授权判定；视图无 is_authenticated 检查。

**数据流（输入 → 危险操作）**

GET /secret + Header X-Host: admin.localhost:8000 -> 渲染 {"secret": "S3CR37K3Y"}。

**修复方向**

不要用自定义请求头做访问控制。改为服务端角色/权限校验；机密不应写在源码常量里；若必须使用 Host 类信息，应使用 Django 的 get_host() 并受 ALLOWED_HOSTS 约束。

**验证状态**：`static_analysis_only`

---

## finding-042 — 以可伪造的 XFF 判定内网来源

- **位置**：`introduction/views.py` 第 950 行第 8 列 至 第 951 行第 59 列
- **CWE**：CWE-290　**严重度**：medium　**置信度**：high

**问题说明与根因**

ssrf_target() 用 X-Forwarded-For 的第一段作为“来源 IP”来决定是否放行内部目标页面：if x_forwarded_for: ip = x_forwarded_for.split(',')[0]。该头由客户端控制，任何外部请求加 `X-Forwarded-For: 127.0.0.1` 即可绕过 localhost 限制，看到 access_denied 之外的内容；结合 finding-007 的 SSRF，服务端自访时本来也是 127.0.0.1，该防护实际不提供任何边界。

**代码证据**（逐字摘自上述行号）

```
    if ip == '127.0.0.1':
        return render(request,"Lab/ssrf/ssrf_target.html")
```

**触发条件 / 前提**

源码已确认：ip 取自可伪造的请求头而非 request.META['REMOTE_ADDR']（仅在缺失 XFF 时回退）；无网段/代理可信性判断。

**数据流（输入 → 危险操作）**

GET /ssrf_target + Header: X-Forwarded-For: 127.0.0.1 -> ip == '127.0.0.1' 成立 -> render('Lab/ssrf/ssrf_target.html') 不带 access_denied。

**修复方向**

只信任可信代理追加的值：使用 DJANGO_TRUSTED_PROXIES / 中间件校验 REMOTE_ADDR 是否为已知代理，否则以 request.META['REMOTE_ADDR'] 为准；内网边界不应依赖请求头。

**验证状态**：`static_analysis_only`

---

## finding-043 — 日志注入（XFF/用户名未规范化写日志）

- **位置**：`introduction/views.py` 第 669 行第 13 列 至 第 671 行第 14 列
- **CWE**：CWE-117　**严重度**：medium　**置信度**：high

**问题说明与根因**

a10_lab2() 把 X-Forwarded-For 首段与 POST 的 name 未经处理直接写入日志（logging.info/warning/error）。两者都完全由请求方控制，可注入换行符伪造额外日志条目（如伪造一条成功登录记录），也可写入超长或含敏感外观的字符串污染日志；日志中还会留下用户名这类身份数据。对照规范 tencent-python-security 1.2.2「禁止将未经验证的用户输入直接记录日志」与 1.2.3。

**代码证据**（逐字摘自上述行号）

```
            logging.info(f"{now}:{ip}:{user}")
            return render(request,"Lab/A10/a10_lab2.html",{"name":user})
        else:
```

**触发条件 / 前提**

源码已确认：logging.basicConfig(level=logging.DEBUG, filename='app.log')（views.py:641）；ip/user 未做换行剥离或长度限制。

**数据流（输入 → 危险操作）**

任意 POST /a10_lab_2 的 name + Header X-Forwarded-For -> logging.{info,warning,error}(f"{now}:{ip}:{user}") -> app.log 中出现攻击者控制的行。

**修复方向**

写日志前规范化输入：剥离 CR/LF 与制表符、限制长度、对用户名字段做格式校验，并避免把身份数据原样写入 INFO 级日志。

**验证状态**：`static_analysis_only`

---

## finding-044 — 未认证提供真实 debug.log

- **位置**：`introduction/views.py` 第 636 行第 1 列 至 第 640 行第 1 列
- **CWE**：CWE-538　**严重度**：medium　**置信度**：high

**问题说明与根因**

debug() 无任何认证即把模板文件 Lab/A10/debug.log 以 text/plain 返回。该文件是真实 Django 运行日志，包含开发者本机绝对路径（A:\wsl\Pygoat\...）、venv/site-packages 路径、完整异常堆栈、内部 URL 结构以及形如 "GET /a10_lab?username=Hacker&password=Hacker" 的明文口令查询串，为后续针对性攻击提供了大量环境信息。

**代码证据**（逐字摘自上述行号）

```
def debug(request):
    response = render(request,'Lab/A10/debug.log')
    response['Content-Type'] =  'text/plain'
    return response

```

**触发条件 / 前提**

源码已确认：路由 introduction/urls.py:53 path("debug", views.debug)；视图内无 is_authenticated 判断；文件内容见 introduction/templates/Lab/A10/debug.log。

**数据流（输入 → 危险操作）**

未认证 GET /debug -> render('Lab/A10/debug.log') -> response['Content-Type']='text/plain' -> 日志正文完整返回。

**修复方向**

不要在可访问路径提供日志文件。删除该路由，或将日志文件移出模板目录并加权限校验；日志本身应脱敏（不含口令查询串与绝对路径）。

**验证状态**：`static_analysis_only`

---

## finding-045 — 对外暴露组件版本

- **位置**：`introduction/views.py` 第 571 行第 62 列 至 第 572 行第 1 列
- **CWE**：CWE-200　**严重度**：low　**置信度**：high

**问题说明与根因**

get_version() 无需认证即向任意访客返回 {"version":"pyyaml v5.1"}，配合同目录 requirements.txt 可让攻击者直接确认服务端使用了存在已知不安全默认 Loader 的旧版 PyYAML，从而定向构造 finding-009 的 !!python/object/apply 载荷。属于不必要的组件版本/技术栈信息暴露。

**代码证据**（逐字摘自上述行号）

```
      return render(request,"Lab/A9/a9_lab.html",{"version":"pyyaml v5.1"})

```

**触发条件 / 前提**

源码已确认：路由 introduction/urls.py:49；视图无认证判断。

**数据流（输入 → 危险操作）**

未认证 GET /get_version -> render(..., {"version":"pyyaml v5.1"}) -> 响应正文泄露依赖组件与版本。

**修复方向**

移除对外暴露组件版本的端点；版本信息只应通过受控的运维接口获取。

**验证状态**：`static_analysis_only`

---

## finding-046 — 锁定多个已知不安全依赖版本

- **位置**：`requirements.txt` 第 27 行第 1 列 至 第 33 行第 18 列
- **CWE**：CWE-1035　**严重度**：high　**置信度**：medium

**问题说明与根因**

依赖清单固定了多个已知存在安全问题的组件版本，最典型的是 PyYAML==5.1（requirements.txt:27，对应 finding-009 的不安全 Loader RCE 面）、Pillow==9.4.0、PyJWT==2.4.0、urllib3==1.26.9、cryptography==39.0.1、Django==4.2 与 Werkzeug==2.1.2 等；同时 dockerized_labs/sensitive_data_exposure/requirements.txt:1 使用 django==3.2.18。应用没有任何 lockfile/哈希校验或来源固定，构建结果不可复核。

**代码证据**（逐字摘自上述行号）

```
PyYAML==5.1
requests==2.28.2
requests-oauthlib==1.3.1
sqlparse==0.3.1
urllib3==1.26.9
Werkzeug==2.1.2
whitenoise==6.2.0
```

**触发条件 / 前提**

源码已确认：requirements.txt 明确锁定上述版本；代码中确实调用了这些库的危险接口（yaml.load、jwt.decode、PIL.ImageMath.eval）。部署环境需确认（本次仅静态分析）：具体可利用的 CVE 需要比对官方公告，本次未联网核实，因此 confidence 为 medium。

**数据流（输入 → 危险操作）**

不适用（依赖组件风险）：影响面通过 finding-009/010/025 等具体调用点体现。

**修复方向**

升级到当前受支持的稳定版本，使用带哈希的 lockfile（pip-tools/uv/poetry lock）固定来源与摘要，并在 CI 中接入依赖漏洞扫描与自动更新。

**验证状态**：`static_analysis_only`

---

## finding-047 — 过期基础镜像 + COPY . 把机密打进镜像

- **位置**：`Dockerfile` 第 1 行第 1 列 至 第 24 行第 13 列
- **CWE**：CWE-1104　**严重度**：medium　**置信度**：medium

**问题说明与根因**

镜像基础层使用 Python 3.11.0b1（预发布版）与已停止维护的 Debian buster 组合，apt 包还被固定到具体的旧版本字符串；随后 `COPY . /app/` 会把整个源码目录（含 pygoat/settings.py 里的 SECRET_KEY、SECRET_COOKIE_KEY、SENSITIVE_DATA，以及 debug.log）一并打进镜像。运行镜像因此带有过期系统组件和随镜像分发的硬编码机密。

**代码证据**（逐字摘自上述行号）

```
FROM python:3.11.0b1-buster


# set work directory
WORKDIR /app


# dependencies for psycopg2
RUN apt-get update && apt-get install --no-install-recommends -y dnsutils=1:9.11.5.P4+dfsg-5.1+deb10u11 libpq-dev=11.16-0+deb10u1 python3-dev=3.7.3-1 && apt-get clean && rm -rf /var/lib/apt/lists/*


# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# Install dependencies
RUN python -m pip install --no-cache-dir pip==22.0.4
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


# copy project
COPY . /app/
```

**触发条件 / 前提**

源码已确认：Dockerfile:1 基础镜像标签、Dockerfile:9 固定 apt 版本、Dockerfile:24 COPY . /app/。部署环境需确认（本次仅静态分析）：buster 是否仍在维护、镜像是否公开分发需环境确认。

**数据流（输入 → 危险操作）**

不适用（构建配置）：机密通过 finding-026/025 的文件读取或镜像提取路径被利用。

**修复方向**

改用受支持的稳定 Python 基础镜像与仍在维护的 OS 发行版（如 python:3.12-slim-bookworm），按 .dockerignore 精确控制 COPY 范围，避免把 settings.py、日志与数据库打进镜像。

**验证状态**：`static_analysis_only`

---

## finding-048 — 可伪造的 base64 会话 Cookie

- **位置**：`dockerized_labs/broken_auth_lab/app.py` 第 45 行第 9 列 至 第 52 行第 13 列
- **CWE**：CWE-384　**严重度**：high　**置信度**：high

**问题说明与根因**

登录成功后 session 凭据仅为 base64("username:datetime")，dashboard() 再 base64 解码并按 ':' 取第一段作为用户名去 users 字典查权限（app.py:111）。该令牌没有签名、没有服务端会话表、没有过期校验，攻击者直接构造 base64('admin:...') 即可冒充管理员并获得 role='admin' 的页面，属于可伪造会话凭据。

**代码证据**（逐字摘自上述行号）

```
        session_token = base64.b64encode(f"{username}:{datetime.now()}".encode()).decode()
        
        if remember_me:
            # Vulnerable: Insecure "Remember Me" implementation
            response.set_cookie('session', session_token, max_age=30*24*60*60)
        else:
            response.set_cookie('session', session_token)
            
```

**触发条件 / 前提**

源码已确认：app.py:45 生成逻辑、app.py:110-116 校验逻辑，注释亦自述 insecure。

**数据流（输入 → 危险操作）**

GET /dashboard + Cookie: session=<base64('admin:x')> -> b64decode().split(':')[0] -> username in users 成立 -> 以 admin 角色渲染 dashboard。

**修复方向**

使用签名+加密的会话（Flask 内置 session 依赖 secret_key，且应改为随机不透明 token + 服务端会话表），登录成功后轮换会话标识，并设置 HttpOnly/Secure/SameSite。

**验证状态**：`static_analysis_only`

---

## finding-049 — 可预测且直接回显的口令重置令牌

- **位置**：`dockerized_labs/broken_auth_lab/app.py` 第 86 行第 13 列 至 第 92 行第 44 列
- **CWE**：CWE-640　**严重度**：high　**置信度**：high

**问题说明与根因**

reset_password() 用 md5(email:当前时间) 生成口令重置令牌，熵仅来自可猜测的时间戳；更严重的是生成后立刻通过 flash() 把完整重置链接 /reset/<token> 返回给请求者，而 /reset/<token>（app.py:97-101）只要 token 命中字典就展示改密表单，不校验请求者身份。任何人用他人邮箱触发一次重置即可拿到可直接使用的高权限链接，实现账户接管。

**代码证据**（逐字摘自上述行号）

```
            token = hashlib.md5(f"{email}:{datetime.now()}".encode()).hexdigest()
            password_reset_tokens[token] = username
            
            # In a real application, this would send an email
            # Vulnerable: Token exposed in response
            flash(f'Password reset link: /reset/{token}')
            return redirect(url_for('lab'))
```

**触发条件 / 前提**

源码已确认：token 由 email + datetime.now() 经 md5 得到；token 明文回显在响应 flash 中；重置表单页无额外校验。

**数据流（输入 → 危险操作）**

POST /reset-password(email=victim) -> token 计算 -> flash('Password reset link: /reset/'+token) -> 攻击者访问 GET /reset/<token> 获得改密页面。

**修复方向**

重置令牌必须由 secrets.token_urlsafe(32) 生成、服务端存储哈希与过期时间、一次性使用，并且只能通过邮件送达；响应中绝不能返回令牌或链接。

**验证状态**：`static_analysis_only`

---

## finding-050 — 源码内明文弱口令账号

- **位置**：`dockerized_labs/broken_auth_lab/app.py` 第 13 行第 9 列 至 第 22 行第 2 列
- **CWE**：CWE-798　**严重度**：high　**置信度**：high

**问题说明与根因**

实验应用把 admin/user 两个账号的口令以明文常量写在源码中（admin123、password123），登录时又用 users[username]['password'] == password 直接比较明文（app.py:41），注册路径同样把 password 原文存入内存字典（app.py:67-71）。这同时构成硬编码凭据、明文口令存储与弱口令三个问题。

**代码证据**（逐字摘自上述行号）

```
        'password': 'admin123',  # Vulnerable: Weak password
        'email': 'admin@example.com',
        'role': 'admin'
    },
    'user': {
        'password': 'password123',  # Vulnerable: Weak password
        'email': 'user@example.com',
        'role': 'user'
    }
}
```

**触发条件 / 前提**

源码已确认：app.py:11-22 常量表；app.py:41 明文比较；app.py:68 明文写入。部署环境需确认（本次仅静态分析）：users 字典在内存中，重启会重置。

**数据流（输入 → 危险操作）**

POST /login 的 username/password -> `users[username]['password'] == password` 常量比较 -> 下发可伪造 session Cookie。

**修复方向**

不要在源码中存放账号与口令；口令统一使用 werkzeug.security.generate_password_hash 或 Django hasher，并通过初始化脚本从环境变量注入。

**验证状态**：`static_analysis_only`

---

## finding-051 — Flask 硬编码 secret_key + debug=True 对外监听

- **位置**：`dockerized_labs/broken_auth_lab/app.py` 第 8 行第 1 列 至 第 9 行第 1 列
- **CWE**：CWE-489　**严重度**：high　**置信度**：high

**问题说明与根因**

Flask 的 app.secret_key 被硬编码为 'your-secret-key-here'，文件末尾以 app.run(host='0.0.0.0', port=5000, debug=True) 启动。固定密钥使任何获得源码的人都能伪造签名 session/flash Cookie；debug=True 会在异常页面暴露 Werkzeug 交互式调试器与完整 traceback，配合 host=0.0.0.0 相当于把可执行调试控制台暴露到网络上。

**代码证据**（逐字摘自上述行号）

```
app.secret_key = 'your-secret-key-here'  # Vulnerable: Hardcoded secret key

```

**触发条件 / 前提**

源码已确认：app.py:8 硬编码 secret_key（自带 Vulnerable 注释）、app.py:123 debug=True。部署环境需确认（本次仅静态分析）：端口是否对外可路由需部署确认。

**数据流（输入 → 危险操作）**

不适用（配置型）：伪造 session 通过 secret_key 已知这一事实达成；调试器通过任意未捕获异常触发。

**修复方向**

secret_key 由环境变量注入且高熵；生产环境使用 gunicorn/uwsgi 而非 flask run，并关闭 debug（或至少限制 werkzeug 调试器仅监听回环）。

**验证状态**：`static_analysis_only`

---

## finding-052 — 未认证 pickle.loads RCE

- **位置**：`dockerized_labs/insec_des_lab/main.py` 第 33 行第 9 列 至 第 36 行第 42 列
- **CWE**：CWE-502　**严重度**：critical　**置信度**：high

**问题说明与根因**

deserialize_data() 把表单字段 serialized_data 直接 base64 解码后交给 pickle.loads()，没有任何签名校验或类型白名单；该端点甚至不做身份认证，返回页面还会打印异常文本。构造恶意 pickle（__reduce__ 指向 os.system / subprocess）即可实现未授权远程代码执行，同时 is_admin 字段可被伪造以获得 ADMIN_KEY_123。

**代码证据**（逐字摘自上述行号）

```
        serialized_data = request.form.get('serialized_data', '')
        decoded_data = base64.b64decode(serialized_data)
        # Intentionally vulnerable deserialization, matching PyGoat
        user = pickle.loads(decoded_data)
```

**触发条件 / 前提**

源码已确认：app.py 路由 /deserialize（main.py:30）无任何认证装饰器；pickle.loads 直接作用于用户输入。部署环境需确认（本次仅静态分析）：Dockerfile 以 flask run --debug 启动（Dockerfile CMD）。

**数据流（输入 → 危险操作）**

POST /deserialize 的 serialized_data -> base64.b64decode -> pickle.loads(decoded_data)（危险操作，构造期执行任意 callable）。

**修复方向**

不要 pickle.loads 用户数据。改为 JSON + 固定字段校验，或使用带签名与过期的一次性令牌。

**验证状态**：`static_analysis_only`

---

## finding-053 — 未认证端点导出全部用户卡号/SSN/API key

- **位置**：`dockerized_labs/sensitive_data_exposure/dataexposure/views.py` 第 112 行第 5 列 至 第 132 行第 51 列
- **CWE**：CWE-306　**严重度**：critical　**置信度**：high

**问题说明与根因**

all_users_data_view() 是全仓库暴露面最大的一个端点：函数上没有任何 @login_required （对比 api_data_view 有 @login_required），却遍历 UserData.objects.all() 并把每个用户的 username、完整 credit_card、完整 ssn、api_key 组装成 JSON 返回。urls.py:13 把它挂在 /api/all-users/，因此未认证攻击者可一次性导出全部用户的支付卡号、社保号与 API 密钥。

**代码证据**（逐字摘自上述行号）

```
def all_users_data_view(request):
    # MAJOR SECURITY FLAW: This endpoint allows ANY user (even unauthenticated ones!)
    # to see ALL users' sensitive data!
    # This demonstrates why proper authentication/authorization is essential.
    
    # Note for students: Notice how there are no checks for who's requesting the data!

    all_users_data = []
    for user_data in UserData.objects.all():
        all_users_data.append({
            'username': user_data.user.username,
            'credit_card': user_data.credit_card,  # Completely exposed! No masking!
            'ssn': user_data.ssn,  # Sending full SSN - terrible practice!
            'api_key': user_data.api_key  # API keys should never be exposed like this
        })
    
    # In a secure application, we would add:
    # if not request.user.is_authenticated or not request.user.is_staff:
    #     return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    return JsonResponse({'users': all_users_data})
```

**触发条件 / 前提**

源码已确认：视图定义处无认证/授权装饰器（views.py:111-112）；UserData 字段为明文 CharField（models.py:6-8）；路由见 urls.py:13。

**数据流（输入 → 危险操作）**

未认证 GET /api/all-users/ -> UserData.objects.all() -> JsonResponse({'users': [...]}) 含完整卡号/SSN/API key。

**修复方向**

为该端点补上认证与授权（@login_required + 仅管理员），默认拒绝；即便用于教学，也应把导出内容与真实用户表隔离。

**验证状态**：`static_analysis_only`

---

## finding-054 — 卡号/SSN/API key 明文存储且无脱敏

- **位置**：`dockerized_labs/sensitive_data_exposure/dataexposure/models.py` 第 6 行第 5 列 至 第 8 行第 75 列
- **CWE**：CWE-312　**严重度**：high　**置信度**：high

**问题说明与根因**

UserData 以普通 CharField 明文存储 credit_card、ssn、api_key，profile.html/api_data_view 会把这些字段直接输出，且 profile_view 在缺失数据时还会现场补齐明文样例数据。对高敏感个人信息既无加密存储也无后台脱敏展示（views.py:68-84），对照规范 tencent-python-security 1.7.1/1.7.2/1.7.4「敏感数据加密存储」「必须由后台脱敏」。

**代码证据**（逐字摘自上述行号）

```
    credit_card = models.CharField(max_length=16)  # probly should encrypt this lol
    ssn = models.CharField(max_length=9)  # this 2, security risk!
    api_key = models.CharField(max_length=32)  # generated on registration
```

**触发条件 / 前提**

源码已确认：models.py:6-8 字段定义（注释自述未加密）；views.py:101-109 未脱敏输出。

**数据流（输入 → 危险操作）**

注册/访问 /profile 或 /api/user-data/ -> UserData.objects.get(user=request.user) -> 明文卡号/SSN/api_key 进入响应。

**修复方向**

卡号/SSN 等应加密存储（字段级加密 + 独立密钥）或直接不保存；展示层必须后台脱敏（如仅保留后 4 位），API key 应存哈希。

**验证状态**：`static_analysis_only`

---

## finding-055 — 初始化脚本硬编码默认口令与机密数据

- **位置**：`dockerized_labs/sensitive_data_exposure/entrypoint.sh` 第 11 行第 168 列 至 第 12 行第 1 列
- **CWE**：CWE-798　**严重度**：medium　**置信度**：high

**问题说明与根因**

容器入口脚本通过 manage.py shell 自动创建 demo 账号，口令 'demopass' 连同固定信用卡号、SSN 与 API key 'demokey123456789' 一起硬编码在镜像构建产物中；紧随其后注释掉的一行还给出了 admin/adminpass 超管账号的创建命令。所有部署实例共享同一套凭据，可被直接用于登录或后台访问。

**代码证据**（逐字摘自上述行号）

```
echo "from django.contrib.auth.models import User; from dataexposure.models import UserData; demo_user = User.objects.filter(username='demo').exists() or User.objects.create_user('demo', 'demo@example.com', 'demopass'); user = User.objects.get(username='demo'); UserData.objects.filter(user=user).exists() or UserData.objects.create(user=user, credit_card='4111111111111111', ssn='123456789', api_key='demokey123456789')" | python manage.py shell

```

**触发条件 / 前提**

源码已确认：entrypoint.sh 明文常量；dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py:8 亦硬编码 SECRET_KEY、:11 DEBUG=True、:13 ALLOWED_HOSTS=['*']。

**数据流（输入 → 危险操作）**

不适用（初始化脚本）：凭据在容器启动时写入数据库，任何人可用其登录 /login/。

**修复方向**

初始化脚本不写入固定口令/机密：口令从环境变量读取或随机生成并一次性输出；SECRET_KEY 同样应注入而非硬编码，DEBUG 与 ALLOWED_HOSTS 按环境区分。

**验证状态**：`static_analysis_only`

---

## finding-056 — 子实验 DEBUG=True + ALLOWED_HOSTS=['*']

- **位置**：`dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py` 第 8 行第 1 列 至 第 14 行第 1 列
- **CWE**：CWE-489　**严重度**：medium　**置信度**：high

**问题说明与根因**

子实验项目的配置同样以不安全默认值交付：SECRET_KEY 明文硬编码、DEBUG = True、ALLOWED_HOSTS = ['*']。DEBUG 开启会让 Django 在异常页输出 settings 与堆栈，ALLOWED_HOSTS 通配则完全关闭 Host 头校验（对照规范 django-4.2-deployment-checklist「Critical settings」与 django-4.2-security「Host header validation」）。

**代码证据**（逐字摘自上述行号）

```
SECRET_KEY = 'django-insecure-key-for-demonstration-only'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

```

**触发条件 / 前提**

源码已确认：settings.py:8 SECRET_KEY、:11 DEBUG、:13 ALLOWED_HOSTS=['*']。部署环境需确认（本次仅静态分析）：是否对外暴露该容器需确认。

**数据流（输入 → 危险操作）**

不适用（配置型）：影响该子应用的所有端点（包括 finding-053 的未认证数据导出）。

**修复方向**

ALLOWED_HOSTS 收紧为实际主机名，DEBUG 由环境变量控制，SECRET_KEY 从环境注入；参照 django-4.2-deployment-checklist 逐项确认 Critical settings 与 HTTPS 段。

**验证状态**：`static_analysis_only`

---

## finding-057 — 路由上的接口使用硬编码 admin/admin 且把凭据写日志

- **位置**：`introduction/playground/A9/api.py` 第 17 行第 12 列 至 第 19 行第 93 列
- **CWE**：CWE-259　**严重度**：medium　**置信度**：high

**问题说明与根因**

被 introduction/urls.py:3 直接注册为路由 /2021/discussion/A9/target 的 log_function_target() 同时带有 @csrf_exempt、无任何认证，并以硬编码的 admin/admin 作口令校验；POST 分支还会把 username、password 原文写入 L.info(...) 日志。这是与主实验应用相互独立的另一处硬编码凭据与凭据入日志问题。

**代码证据**（逐字摘自上述行号）

```
        if username == "admin" and password == "admin":
            return JsonResponse({"message":"Loged in successfully", "method":"post"},status = 200)
        return JsonResponse({"message":"Invalid credentials", "method":"post"},status = 401)
```

**触发条件 / 前提**

源码已确认：api.py:7 @csrf_exempt、api.py:16 记录明文凭据、api.py:17 明文常量比较；路由见 introduction/urls.py:84。部署环境需确认（本次仅静态分析）：该模块文件可被 finding-017 覆盖，实际内容取决于运行目录状态。

**数据流（输入 → 危险操作）**

未认证 POST /2021/discussion/A9/target 的 username/password -> 常量比较 -> 成功即返回登录成功 JSON；同时明文凭据写入 test.log。

**修复方向**

删除源码中的固定口令，改用 Django 认证（authenticate/login）与哈希存储；不要记录用户名口令等凭据到日志；教学用靶场接口同样应校验 CSRF。

**验证状态**：`static_analysis_only`

---

## finding-058 — API 密钥写入页面 JS 与 localStorage

- **位置**：`dockerized_labs/sensitive_data_exposure/templates/profile.html` 第 217 行第 9 列 至 第 223 行第 9 列
- **CWE**：CWE-922　**严重度**：high　**置信度**：high

**问题说明与根因**

该教学子应用的 profile 页面把用户的 API 密钥写进浏览器可读的 JS 对象，并额外用 localStorage.setItem('user_api_key', ...) 持久化到本机。凭据一旦进入 localStorage 就不再随会话结束失效，且可被同源下的任意 XSS、浏览器扩展或共享电脑的本地访问者直接取走；结合本仓库多处未转义输出（见 finding-012 ~ finding-016）会直接导致凭据泄露。

**代码证据**（逐字摘自上述行号）

```
        var userData = {
            username: "{{ user.username }}",
            apiKey: "{{ user_data.api_key }}" // Yeah it is necessary for this lab.
        };
        
        localStorage.setItem('user_api_key', "{{ user_data.api_key }}");
        
```

**触发条件 / 前提**

源码已确认：模板中确实存在上述代码；api_key 字段为明文 CharField（见 finding-054）。部署环境需确认（本次仅静态分析）：该子应用是否对外开放需确认。

**数据流（输入 → 危险操作）**

登录用户 GET /profile -> views.profile_view 上下文 user_data -> 模板把 user_data.api_key 写入内联 <script> 与 localStorage → 浏览器本地持久化凭据。

**修复方向**

凭据不应下发到浏览器：页面只展示必要的脱敏信息（例如仅显示前缀 + 后 4 位），需要 API key 的操作改为服务端代理签名；绝不写入 localStorage/sessionStorage，并移除内联 <script> 中的凭据字段。

**验证状态**：`static_analysis_only`

---

## finding-059 — 多个模板从 CDN 加载无 SRI/CSP 的第三方脚本

- **位置**：`dockerized_labs/sensitive_data_exposure/templates/base.html` 第 60 行第 26 列 至 第 62 行第 99 列
- **CWE**：CWE-829　**严重度**：medium　**置信度**：high

**问题说明与根因**

该子应用的公共基底模板（以及 about/index/lesson/login/profile 等多个页面）从多个第三方 CDN 直接加载可执行脚本，且全部没有 integrity/SRI 属性，也没有任何 Content-Security-Policy 。一旦这些 CDN 资源被替换、域名/包被劫持或链接被篡改，攻击者的 JS 将在包含用户敏感数据的页面上以应用源执行（供应链式脚本注入）。

**代码证据**（逐字摘自上述行号）

```
    <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.1/dist/umd/popper.min.js"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
```

**触发条件 / 前提**

源码已确认：多个模板中的 <script src="http..."> 均无 integrity 属性（grep 确认）；仓库内无任何 CSP 配置。部署环境需确认（本次仅静态分析）：实际是否能抢占 CDN 响应需网络位置确认。

**数据流（输入 → 危险操作）**

不适用（前端供应链缺陷）：危险操作发生在浏览器加载外部脚本时，无服务端数据流。

**修复方向**

把第三方脚本改为本地自托管（Django 已有 staticfiles/whitenoise），或至少为每个 <script>/<link> 补 integrity + crossorigin；同时下发 Content-Security-Policy（script-src 明确白名单）作为纵深防御。

**验证状态**：`static_analysis_only`

---

## 规范条文的对应关系（B 组附加依据）

> 说明：`tencent-python-security.md` 内部存在两套并列的 1.x 编号（第一套为通用要求：1.1 加密算法 / 1.2 程序日志 / 1.3 系统口令；第二套为 Web 专章：1.1 输入验证 / 1.2 SQL 操作 / 1.3 执行命令 / 1.4 文件操作 …）。下列条目按条文标题引用，避开编号歧义；完整文件名见 `rules-v1/core`、`rules-v1/supplemental`。
- `tencent-python-security.md` 1.2.1（使用参数化查询）→ finding-001、finding-002
- 同 1.3.1/1.3.2（避免直接执行系统命令、安全传递外部程序参数）→ finding-005、finding-021、finding-057
- 同 1.3.3（禁止不安全的代码执行）→ finding-006、finding-010、finding-020
- 同 1.3.4（服务端模板与数据分离）→ finding-011
- 同 1.4.3（避免路径穿越）、1.4.6（避免路径拼接）→ finding-008
- 同 1.4.4（禁用 XML 外部实体）→ finding-004
- 同 1.4.5（禁用不安全的反序列化函数）→ finding-003、finding-009、finding-052
- 同 1.5.1（限定可访问网络资源地址范围）→ finding-007
- 同 1.6.3（对外输出含第三方数据须编码）→ finding-012 ~ finding-016
- 同 1.7.1/1.7.2/1.7.4（敏感数据加密存储与后台脱敏）→ finding-034、finding-054
- 同 1.8.1/1.8.3/1.8.5/1.8.6（默认鉴权、避免越权、可信会话与授权决策、浏览器请求防伪造）→ finding-017、finding-018、finding-029、finding-035 ~ finding-038、finding-041、finding-042、finding-053
- 同 2.3.1/2.3.2（密钥存储安全、禁止硬编码敏感配置）→ finding-023、finding-025、finding-026、finding-032、finding-050、finding-051、finding-055、finding-056
- 同 1.1.1（按类型进行数据校验）→ finding-005、finding-008、finding-021、finding-022
- 同 1.3.1/1.3.2/1.3.3（禁止弱口令、口令强度、口令存储安全）与 1.3.6（安全生成和验证认证令牌）→ finding-024、finding-030、finding-031、finding-033、finding-040、finding-049
- 同 1.7.3（高敏感信息禁止存储、展示）→ finding-053、finding-054
- 同 1.9.1/1.9.2（不对外输出错误提示、禁止异常抛出敏感信息）→ finding-027、finding-044、finding-052
- 同 1.2.2/1.2.3（不记录未验证输入、日志避免敏感信息）→ finding-043、finding-044
- 同 1.11.1/1.10.1（生产环境关闭调试模式）→ finding-027、finding-051、finding-056
- `django-4.2-security.rst`（CSRF/模板转义/raw 查询/Host 头/会话安全）→ finding-001、finding-012 ~ finding-015、finding-022、finding-027
- `django-4.2-deployment-checklist.rst`（Secret key、DEBUG、HTTPS、Cookie Secure）→ finding-026、finding-027、finding-028
- `owasp-ssrf-prevention.md`、`owasp-deserialization.md`、`owasp-xss-prevention.md`、`owasp-authorization.md`、`owasp-sql-injection-prevention.md` → 分别对应 finding-007、finding-003/009/052、finding-012 ~ 016、finding-036 ~ 038/053、finding-001/002

规范只提供判定口径；以上每条都仍配有本仓库内的具体代码位置与逐字证据。未找到对应条文的问题（如 finding-045 组件版本暴露、finding-046/047 依赖与镜像）依据既有知识报告。

## 未覆盖范围与分析局限

1. **未逐行阅读的文件**：本次 30 分钟窗口内，`coverage.json` 标记为 `not_reviewed` 的 176 个文本文件未打开，主要包括 `introduction/templates/mitre/mitre_top1.html ~ mitre_top25.html`（MITRE 讲解页，除 base.html 外未逐个检查其内联脚本）、`introduction/static/css/*.css` 与 `introduction/static/Lab/*.css`、`introduction/migrations/0001~0021`、`challenge/migrations/*`、`introduction/tests.py`、`challenge/tests.py`、`introduction/apps.py`、`challenge/apps.py`、`pygoat/asgi.py`、`pygoat/wsgi.py`、各 `__init__.py`、`dockerized_labs/*/manage.py`、`dockerized_labs/broken_auth_lab/templates/*.html`、`dockerized_labs/*/docker-compose.yml`、`.gitignore`、`.dockerignore`、`.all-contributorsrc`、`gh-md-toc`、`uninstaller.sh`、`introduction/playground/A6/index.html` 等 playground 讲解页。这些文件里仍可能存在未被报告的问题。
2. **只做了部分阅读的文件**：见 `coverage.json` 中 `status=partial` 的 24 个条目及其实际阅读行段。例如 `uninstaller.py` 只读了前 70 行，`introduction/templates/introduction/base.html` 只读了前 30 行（共 743 行），多数含 `|safe` 的模板只看了搜索命中行。
3. **二进制文件未解析**：`coverage.json` 的 `excluded_binary_files` 列出的 5 个二进制资源未做内容分析（均为图片，未验证其中是否隐藏额外数据）。
4. **纯静态结论**：没有安装依赖、没有启动 Django/Flask 进程、没有构造任何请求或载荷，因此所有可利用性判断都基于代码与配置的静态语义。像 finding-010（ImageMath.eval 表达式能力）、finding-046（具体 CVE 编号）这类依赖第三方库运行期行为的结论，置信度已标为 medium。
5. **部署相关前提未验证**：是否真的以 `pygoat/settings.py` 的 DEBUG=True 对外服务、容器是否以 root 运行、`django_heroku` 是否覆盖 ALLOWED_HOSTS/数据库、内网是否可达云元数据地址，均需部署环境确认；各发现的 `preconditions` 已区分“源码已确认”和“尚需部署确认”。
6. **不声称找全**：本报告不主张覆盖该仓库的全部漏洞，`completed` 仅表示本次审查按时间预算正常结束。不使用“整个仓库安全”“完整覆盖所有漏洞”这类结论。
7. **判分口径**：`uncertain-findings.json` 中的 10 条候选因缺少上下文（例如模板输出上下文、是否存在用户可写的 DB 字段、Django 版本行为需实测）而未计入 `findings.json`。
