# 静态安全代码审查报告 — PyGoat（run r01, group B-with-extra-rules）

- **实验**: 01-pygoat-models-pi-agent / B组（附加完整安全规范）
- **审查方式**: 纯静态分析（未运行应用、未复现攻击、未运行任何验证/利用代码）
- **输入**: `D:/ai_share/langgraph/benchmark-data/pygoat-baseline/inputs/experiment-01/pygoat`（提交 2fb0c600245f50670e8b9233c784afe61e8b340b）
- **审查依据**: rules-v1 全部 9 份规范（Tencent Python 安全规范、Django 4.2 security/deployment-checklist、OWASP Django/Authorization/Deserialization/SQLi/SSRF/XSS Cheat Sheet）+ 既有安全知识
- **结论数量**: 确认发现 41 项（`findings.json`），未确认候选 5 项（`uncertain-findings.json`）

> 该项目为 OWASP PyGoat（刻意存在漏洞的教学应用），下述问题均为其源码中真实存在的模式；报告按发现本身描述，不因"教学用途"豁免。

---

## 一、注入类

### finding-001 / finding-002 — SQL 注入（CWE-89, critical）
- **位置**: `introduction/views.py:158`（`sql_lab`）、`introduction/views.py:864`（`injection_sql_lab`）
- **证据**: `sql_query = "SELECT * FROM introduction_login WHERE user='"+name+"' AND password='"+password+"'"` → `login.objects.raw(sql_query)`
- **触发条件**: 已登录用户提交 POST `name`/`pass`（源码已确认；登录要求为源码内确认条件）
- **根因**: 字符串拼接构造SQL并经 `objects.raw()` 执行，违反《Tencent Python 规范 1.2.1 使用参数化查询》《OWASP SQLi Cheat Sheet》
- **影响**: 绕过认证、读取/篡改 `introduction_login`、`introduction_sql_lab_table` 表数据
- **修复**: 使用参数绑定（`raw(sql, [params])`）或 ORM filter；输入校验仅作补充

### finding-005 — XXE（CWE-611, high）
- **位置**: `introduction/views.py:256-268`（`xxe_parse`，URL `/xxe_parse`）
- **证据**: `parser.setFeature(feature_external_ges, True)` + `parseString(request.body.decode('utf-8'), parser=parser)`
- **触发条件**: **该端点无认证、无CSRF**，匿名POST XML即可；`@csrf_exempt`（源码已确认）
- **根因**: 显式开启外部实体解析，违反《Tencent Python 规范 1.4.4》《OWASP SSRF/XXE 指引》
- **影响**: 读取本地文件（如 `introduction/xee_see.txt` 场景）、内网探测；解析结果写入 `comments` 表并经 `/xxe_see` 回显
- **修复**: `resolve_entities=False` / defusedxml；补认证

### finding-006 — 命令注入（CWE-78, critical）
- **位置**: `introduction/views.py:415-431`（`cmd_lab`）
- **证据**: `command="nslookup {}".format(domain)` → `subprocess.Popen(command, shell=True)`
- **触发条件**: 已登录用户POST `domain='; cat /etc/passwd'`（协议前缀正则剥离不阻止命令分隔符）
- **根因**: 拼接外部数据进shell命令，违反《Tencent Python 规范 1.3.2》
- **修复**: 固定命令+参数列表传参、关闭shell、白名单校验域名格式

### finding-009 — 命令注入（CWE-78, critical, 未认证）
- **位置**: `introduction/mitre.py:239-243`（`mitre_lab_17_api`），`command_out` 在 246-248 行以 `shell=True` 执行
- **证据**: `command = "nmap " + ip`
- **触发条件**: `/mitre/17/lab/api` 匿名POST（认证装饰器缺失）
- **影响**: 任意shell命令执行

## 二、代码执行类

### finding-007 / finding-008 — eval 任意代码执行（CWE-94, critical）
- **位置**: `introduction/views.py:460`（`cmd_lab2`，需登录）；`introduction/mitre.py:218`（`mitre_lab_25_api`，**无认证**，`@csrf_exempt`）
- **证据**: `output = eval(val)` / `result = eval(expression)`
- **触发条件**: 提交 `__import__('os').system('...')` 类表达式
- **修复**: 移除eval，使用受限表达式解析器并加白名单

### finding-011 — ImageMath.eval 表达式注入（CWE-94, high, 置信度 medium）
- **位置**: `introduction/views.py:574-588`（`a9_lab2`）
- **证据**: `function_str = request.POST.get("function")` → `ImageMath.eval(function_str, img=img, b=b, r=r, g=g)`
- **说明**: 用户字符串直接作为PIL表达式求值；具体逃逸能力依赖 Pillow==9.4.0 实现，静态分析无法完全确认，故入主结果但置信度 medium

### finding-012 / finding-013 — 用户代码写入可执行 .py 文件（CWE-94, high）
- **位置**: `introduction/apis.py:128-134`（`A6_disscussion_api_2` 写 `playground/A6/utility.py`）；`introduction/apis.py:60-75`（`log_function_checker` 写 `playground/A9/main.py`、`api.py`，**认证装饰器被注释，匿名可写**）
- **证据**: `f = open(filename,"w"); f.write(code)`
- **触发条件**: 写入端点本身无认证；被写入文件在 `apis.py`/`urls.py` 被 import，进程重新加载（开发服务器 StatReloader 或多worker重启）后执行（此为部署相关条件）
- **根因**: 违反《Tencent Python 规范 1.3.3》"不允许外部输入覆写会被导入执行的源文件"

## 三、反序列化类

### finding-003 / finding-004 — pickle 反序列化 RCE（CWE-502, critical）
- **位置**: `introduction/views.py:205-218`（`insec_des_lab`，Cookie `token`）；`dockerized_labs/insec_des_lab/main.py:36`（`/deserialize`，无认证）
- **证据**: `token = base64.b64decode(token); admin = pickle.loads(token)`；子应用 `User.__reduce__`
- **根因**: 对不可信数据调用 `pickle.loads`，违反《Tencent Python 规范 1.4.5》《OWASP Deserialization Cheat Sheet》
- **影响**: 任意代码执行；主应用伪造 `admin=1` 还泄露 `SECRETKEY:ADMIN123`

### finding-010 — 不安全 yaml.load（CWE-502, critical）
- **位置**: `introduction/views.py:551-560`（`a9_lab`）
- **证据**: `data = yaml.load(file, yaml.Loader)`，requirements.txt 锁定 `PyYAML==5.1`
- **触发条件**: 已登录用户上传 `!!python/object/apply:os.system [...]` YAML
- **修复**: `yaml.safe_load`

## 四、XSS / SSTI / SSRF / 路径穿越

### finding-014 / finding-015 / finding-016 / finding-017 — XSS（CWE-79）
- **finding-014** `introduction/templates/Lab/XSS/xss_lab.html:27`：`{{query|safe}}`，源为 GET `q`（views.py:93-100），反射型XSS（high）
- **finding-015** `introduction/templates/Lab/XSS/xss_lab_2.html:20`：`{{ username|safe }}`，后端仅删除小写 `<script>` 标签（views.py:112-115），`<img onerror>` 等向量直接绕过（high）
- **finding-016** `introduction/templates/Lab/XSS/xss_lab_3.html:22`：`{{code}}` 嵌入 `<script>` 块内，自动转义在JS上下文不构成防护（medium）
- **finding-017** `introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html:11`：`{{username | safe}}`，源为 GET `username`（views.py:1147 附近）（high）
- **根因**: 违反《Django security》"避免 safe/mark_safe 处理不可信输入"、《OWASP XSS Prevention》输出编码规则
- **附注**: `introduction/templates/Lab/ssrf/ssrf_lab2.html:23` `{{response | safe}}` 将SSRF响应内容作为HTML渲染（并入 finding-020 影响）

### finding-018 — 服务端模板注入 SSTI（CWE-1336, critical）
- **位置**: `introduction/views.py:975-1000`（`ssti_lab` + `ssti_view_blog`）
- **证据**: `blog = filter_blog(blog)`（`introduction/utility.py:21` 恒等返回，无过滤）→ 拼接 `{% block %}` 后写入 `templates/Lab_2021/A3_Injection/Blogs/{id}.html` → `render(request, f"Lab_2021/A3_Injection/Blogs/{blog_id}.html")`
- **根因**: 用户内容成为模板源码，违反《Tencent Python 规范 1.3.4 服务端模板与数据分离》
- **影响**: 模板语句执行，可读取 `settings.SECRET_KEY`、进而RCE

### finding-019 — 路径穿越/任意文件读取（CWE-22, high）
- **位置**: `introduction/views.py:918-927`（`ssrf_lab`）
- **证据**: `filename = os.path.join(dirname, file); file = open(filename,"r")`，`file` 为POST原文，无规范化和根目录校验
- **影响**: 读取 `db.sqlite3`、`pygoat/settings.py`（含SECRET_KEY）等任意可读文件
- **违反**: 《Tencent Python 规范 1.4.3 避免路径穿越》（仅删`..`或前缀检查不充分，此处连检查都没有）

### finding-020 — SSRF（CWE-918, high）
- **位置**: `introduction/views.py:956-965`（`ssrf_lab2`）
- **证据**: `url = request.POST["url"]; response = requests.get(url)`
- **根因**: 无协议/主机/私网/元数据地址校验，默认跟随重定向，违反《OWASP SSRF Prevention》
- **影响**: 探测内网、访问 127.0.0.1（绕过 `ssrf_target` 的来源检查）、云元数据；响应以 `|safe` 渲染还会造成XSS

## 五、访问控制与认证

### finding-021 — 失效的访问控制（CWE-862, high）
- **位置**: `introduction/views.py:837-841`（`a1_broken_access_lab3_secret`）
- **证据**: `# no checking applied here` → 任何已登录用户可读 `secret.html`
- **违反**: 《OWASP Authorization》"Validate the Permissions on Every Request"、最小权限

### finding-022 / finding-023 / finding-024 — 信任客户端输入做授权（CWE-807, high）
- **finding-022** `views.py:342-354`：`request.COOKIES.get('admin') == "1"` 决定管理员秘密（`a1_broken_access_lab_1` views.py:756 同模式）
- **finding-023** `views.py:783-797`：`HTTP_USER_AGENT == "pygoat_admin"` 决定管理员
- **finding-024** `views.py:535-540`：`X-Host == 'admin.localhost:8000'` 决定秘密 S3CR37K3Y，且该视图**无登录要求**
- **根因**: 《Tencent Python 规范 1.8.5》：客户端可提交的头部/Cookie不能作为授权依据

### finding-038 — 可预测顺序ID作为会话凭据（CWE-639, high）
- **位置**: `introduction/views.py:299-308`（`auth_lab_login` GET 分支）
- **证据**: `authLogin.objects.filter(userid=request.COOKIES['userid'])[0]` 即视为登录成功；`userid` 为 AutoField；Cookie 设置 `samesite=None, secure=False`
- **影响**: 枚举 userid 接管任意该lab账号

### finding-025 — OTP 认证缺陷（CWE-307, high）
- **位置**: `introduction/views.py:493-522`（`Otp`）+ `templates/Lab/BrokenAuth/otp.html`（`{{otp}}` 明文回显）
- **证据**: `otpN=randint(100,999)`；非admin邮箱直接在响应返回OTP；`otp.objects.filter(email=email,otp=otpR) or otp.objects.filter(id=2,otp=otpR)` 允许任何人用管理员OTP通过；无尝试次数限制
- **违反**: 《Tencent Python 规范 1.3.6》：验证码不得在响应中返回答案、需限速/尝试次数控制

### finding-026 — 未签名认证Cookie（CWE-345, high）
- **位置**: `introduction/views.py:1049-1080`（`crypto_failure_lab3`）
- **证据**: `cookie = f"{username}|{expire}"` 直接 `set_cookie`；GET 分支 `cookie.split('|')[0] == 'admin'` 判定管理员
- **影响**: 伪造 `admin|2099-01-01...` Cookie 即成管理员

### finding-028 — CSRF：GET 修改资金 + 硬编码JWT密钥（CWE-352, high）
- **位置**: `introduction/mitre.py:186-205`（`csrf_transfer_monei_api`）
- **证据**: GET 请求内 `User[0].balance = User[0].balance - int(amount); User[0].save()`；JWT 密钥硬编码 `'csrf_vulneribility'`（mitre.py:169/182/194）
- **触发条件**: 受害者持有效 `auth_cookiee` 访问攻击者页面，`<img src="/mitre/9/lab/api/x/999">` 即可转账
- **违反**: 《Tencent Python 规范 1.8.6》"GET等安全方法不应修改状态"

## 六、加密与凭据管理

### finding-027 — 硬编码JWT密钥（CWE-321, high）
- **位置**: `pygoat/settings.py:165` `SECRET_COOKIE_KEY = "PYGOAT"`；使用点 `introduction/views.py:1095/1107`（`sec_misconfig_lab3`）
- **影响**: 离线伪造 `{"user":"admin"}` 的 HS256 JWT

### finding-029 / finding-041 — 硬编码 SECRET_KEY（CWE-798, high/medium）
- `pygoat/settings.py:24`：主应用 SECRET_KEY 明文（high——影响会话/CSRF/重置令牌签名）
- `dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py:8-13`：占位密钥 + `DEBUG=True` + `ALLOWED_HOSTS=['*']`（medium）

### finding-030 — DEBUG=True（CWE-489, medium）
- `pygoat/settings.py:28`；错误页向客户端泄露源码/配置（违反《Tencent Python 规范 1.9.1》《Django deployment checklist》）

### finding-033 — 明文口令存储（CWE-256, medium）
- `introduction/views.py:285-287`：`authLogin.objects.create(..., password=passwd)`；`introduction/models.py` 中 `login`/`authLogin`/`CSRF_user_tbl` 口令均为普通 CharField
- **违反**: 《Tencent Python 规范 1.3.3 口令存储安全》

### finding-034 — 弱口令哈希（CWE-916, medium）
- `introduction/views.py:1026`：无盐 MD5；`crypto_failure_lab2` 用 `customHash`（`introduction/utility.py:24`，SHA-256 倒序，非专用口令哈希）；`introduction/mitre.py:150` 亦用无盐MD5
- **违反**: 《Tencent Python 规范 1.3.3》：单次MD5/SHA-256及倒序变换不能替代专用口令哈希

### finding-035 — 硬编码凭据（CWE-798, medium）
- `introduction/views.py:766/806`（jack/jacktheripper）、829-833 附近（John/reaper、admin/admin_pass）、1121 注释（管理员口令）、`introduction/playground/A9/api.py:22`（admin/admin）、`dockerized_labs/broken_auth_lab/app.py:10-19`（admin123/password123）

### finding-032 / finding-039 — 非密码学随机数（CWE-338, medium/low）
- `dockerized_labs/sensitive_data_exposure/dataexposure/views.py:42`：API key 用 `random.choices`
- `introduction/views.py:679-681`：工单码用 `random.choices`
- **违反**: 《Tencent Python 规范 1.3.6》：令牌需使用密码学安全随机源（`secrets`）

## 七、敏感数据暴露与日志

### finding-031 — 未授权访问全部用户敏感数据（CWE-862, critical）
- **位置**: `dockerized_labs/sensitive_data_exposure/dataexposure/views.py:113-131`（`all_users_data_view`，路由 `api/all-users/`）
- **证据**: 无 `login_required`、无 `is_authenticated` 检查；`UserData.objects.all()` 返回明文信用卡、SSN、API key
- **违反**: 《Tencent Python 规范 1.8.1/1.8.3 默认鉴权/避免越权》

### finding-036 — 日志注入（CWE-117, low）
- `introduction/views.py:645-672`（`a10_lab2`）：未校验的 `X-Forwarded-For` 与 `username` 直接 f-string 写日志；`logging.basicConfig(level=logging.DEBUG)`

### finding-037 — 日志文件对外（CWE-532, low, 置信度 medium）
- `introduction/views.py:636-639`（`/debug`）：向任意已登录用户返回服务器日志样本 `templates/Lab/A10/debug.log`

### finding-040 — Flask 子应用会话伪造（CWE-347, high）
- `dockerized_labs/broken_auth_lab/app.py:78` + `:105-106`：会话为无签名 base64(`username:timestamp`)，dashboard 解码即授权；同文件还有硬编码 secret_key(:8)、md5 重置令牌直接回显(:86)、`debug=True`(:123)

---

## 未覆盖范围与分析局限

- 仅静态分析，未运行任何应用、未发送请求、未验证漏洞可利用性；严重度按源码可达性推断。
- HTML 模板共约 120 个（mitre_top1~25、Lab 说明页、Lab_2021 说明页等），多数为教学说明页，仅抽查了与数据流相关的模板（xss_lab*.html、otp.html、auth_success.html、ssrf_lab2.html、xss_lab_3.html、debug.log），未逐字通读全部模板与 CSS/JS（a6.js、a7.js、a9.js、ssrf.js 仅按关键字检查 innerHTML/eval/document.write）。
- `gh-md-toc`（约 700 行 TOC 脚本）、`.all-contributorsrc`、LICENSE、部分 migrations、tests.py、docker-compose/Dockerfile 未深入审查；`installer.sh`/`uninstaller.py`/`uninstaller.sh` 仅快速浏览。
- 未做依赖 CVE 清单比对（无网络；requirements.txt 中 PyYAML==5.1、Pillow==9.4.0、cryptography==39.0.1 等版本较旧，仅在其被代码用法直接证实时引用，如 PyYAML）。
- `challenge/views.py` 中 `docker run` 使用数据库内 `docker_image`/`docker_port`（populate_challenge.py 从 challenge.json 导入），非直接用户输入，未计入确认发现，见 uncertain。
- 时间预算：分析至第 30 分钟上限即停止搜索，之后仅整理已有发现。
