# 实验 01 / A 组静态安全代码审查报告（无额外规范）

- 运行标识：model_label=`glm-5.3-flash`，run_id=`r01`，harness=`pi-agent`
- 审查方式：**纯静态分析**（未运行应用、未执行测试或利用代码、未做动态验证）
- 确认发现：**48** 项（与 findings.json 一致）；未确认候选见 uncertain-findings.json
- 分析开始：2026-11-17T13:38:36+08:00；分析结束：2026-11-17T13:45:00+08:00 左右（详见 run.json）

## 发现明细

### finding-001 — CWE-89（严重度 critical，置信度 high）
- 位置：`introduction/views.py` 第 158 行（范围 158:17 – 162:1）
- 代码证据：`sql_query = "SELECT * FROM introduction_login WHERE user='"+name+"' AND password='"+password+"'"`
- 根因与安全影响：SQL 注入：sql_lab 视图将 POST 参数 name、password 直接拼接进 SQL 字符串并用 login.objects.raw() 执行（第158-162行）。攻击者可通过 ' OR '1'='1 之类的载荷绕过口令校验或读取/破坏 introduction_login 表数据（sqlite3 后端）。异常分支还会把完整 SQL（含注入载荷）回显到页面，便于盲注探测。
- 触发条件：源码已确认：无需特殊配置。视图要求 request.user.is_authenticated，因此需先注册/登录任意 Django 账号；POST /sql_lab 或 /sql_lab1。部署环境条件：应用按仓库默认配置可达。
- 数据流：HTTP POST name/password → request.POST.get → 字符串拼接 sql_query → login.objects.raw(sql_query) 直接执行 → 结果回显 user1 或 sql_error。
- 修复方向：使用 ORM 参数化查询（filter/get）或 cursor.execute 的参数绑定；禁止字符串拼接进 raw()。

### finding-002 — CWE-89（严重度 critical，置信度 high）
- 位置：`introduction/views.py` 第 864 行（范围 864:13 – 878:1）
- 代码证据：`sql_query = "SELECT * FROM introduction_sql_lab_table WHERE id='"+name+"'AND password='"+password+"'"`
- 根因与安全影响：SQL 注入：injection_sql_lab 视图（POST /injection_sql_lab）将 name、password 拼接进 SQL 后经 sql_lab_table.objects.raw() 执行（第864、878行），与 finding-001 位于不同视图，为独立注入点。可绕过认证并读取/篡改 introduction_sql_lab_table 表。
- 触发条件：源码已确认：需登录（request.user.is_authenticated）。视图每次请求都会向 sql_lab_table 插入固定行，第二次访问起因主键冲突走异常分支，但注入查询仍先于插入前构造并在 try 中执行。
- 数据流：HTTP POST name/pass → 字符串拼接 → sql_lab_table.objects.raw(sql_query) → user[0].id 回显。
- 修复方向：同 finding-001：改用 ORM 参数化查询；同时移除每请求插入种子数据的逻辑。

### finding-003 — CWE-502（严重度 critical，置信度 high）
- 位置：`introduction/views.py` 第 214 行（范围 214:13 – 216:1）
- 代码证据：`admin = pickle.loads(token)`
- 根因与安全影响：不安全的反序列化：insec_des_lab 从 Cookie token 取 base64 解码后的数据直接 pickle.loads（第213-214行）。pickle 可携带任意 __reduce__ 载荷，攻击者设置恶意 Cookie 即可在服务端以应用进程身份执行任意 Python 代码。dockerized_labs/insec_des_lab/main.py 的 /deserialize 端点存在同类问题（单独报告）。
- 触发条件：源码已确认：需登录后访问 /insec_des_lab；Cookie 完全由客户端控制。若服务端未曾种 Cookie，token=None 时会先以 encoded_user 覆盖为安全值，攻击者手动携带恶意 Cookie 即可触发。
- 数据流：Cookie token → base64.b64decode → pickle.loads → 恶意对象在加载时执行任意代码（如 os.system）。
- 修复方向：禁止对客户端可控数据做 pickle 反序列化；改用签名 token（如 itsdangerous）或 Django 签名 Cookie 承载结构化数据。

### finding-004 — CWE-611（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 259 行（范围 259:5 – 261:1）
- 代码证据：`parser.setFeature(feature_external_ges, True)`
- 根因与安全影响：XXE（XML 外部实体注入）：xxe_parse 视图启用 feature_external_ges 并用 xml.dom.pulldom.parseString 解析原始请求体（第259-260行），允许解析外部实体，可借 file:// 等实体读取服务器本地文件、内网探测（SSRF），且解析结果写入 comments 表回显。该视图同时带 @csrf_exempt 且缺少任何登录校验，可被未认证者直接调用（GET/POST 均可，POST 才携带 XML）。
- 触发条件：源码已确认：端点 /xxe_parse 无认证、无 CSRF 保护（源码可见）。部署条件：外部实体解析依赖 Python xml.sax 默认行为（标准库会解析外部 DTD/实体）。
- 数据流：HTTP 请求体（XML，含外部实体 DOCTYPE）→ parseString + expandNode → 提取 <text> 内容写入 comments(id=1) → 由 /xxe_see 页面回显，实现文件读取外带。
- 修复方向：改用 defusedxml 等禁用外部实体的解析器；删除 feature_external_ges=True；补认证与 CSRF 校验。

### finding-005 — CWE-78（严重度 critical，置信度 high）
- 位置：`introduction/views.py` 第 426 行（范围 426:17 – 434:1）
- 代码证据：`command = "dig {}".format(domain)`
- 根因与安全影响：命令注入：cmd_lab 将 POST 参数 domain 仅去除协议前缀后直接拼入 nslookup/dig 命令，并以 subprocess.Popen(command, shell=True) 执行（第426-434行）。domain 形如 '127.0.0.1; cat /etc/passwd' 即可执行任意系统命令；os 参数（win/其他）仅选择命令名，不构成过滤。
- 触发条件：源码已确认：需登录，POST /cmd_lab（@csrf_exempt）。部署条件：容器/主机需存在 dig 或 nslookup（Dockerfile 安装了 dnsutils），shell=True 在 Linux 下为 /bin/sh。
- 数据流：POST domain → 正则仅去协议头 → command 字符串拼接 → Popen(shell=True) → 命令输出回显到页面。
- 修复方向：不拼接命令字符串；使用固定参数列表 Popen(['dig', domain], shell=False) 并对域名做白名单正则校验。

### finding-006 — CWE-94（严重度 critical，置信度 high）
- 位置：`introduction/views.py` 第 460 行（范围 460:17 – 460:35）
- 代码证据：`output = eval(val)`
- 根因与安全影响：任意代码执行：cmd_lab2 将 POST 参数 val 直接传入内建 eval()（第460行），攻击者可提交任意 Python 表达式（如 __import__('os').system(...)）在服务器执行代码，结果部分回显。异常捕获会吞掉部分报错但不影响执行副作用。
- 触发条件：源码已确认：需登录，POST /cmd_lab2（@csrf_exempt）。
- 数据流：POST val → eval(val) → 任意 Python 表达式求值/执行 → output 回显。
- 修复方向：移除 eval；如需计算器功能，用受限表达式解析器（ast 白名单）。

### finding-007 — CWE-79（严重度 medium，置信度 high）
- 位置：`introduction/templates/Lab/XSS/xss_lab.html` 第 27 行（范围 27:23 – 27:37）
- 代码证据：`{{query|safe}}`
- 根因与安全影响：反射型 XSS：xss_lab 视图把 GET 参数 q 原样传入模板（views.py 第93-98行），模板 xss_lab.html 第27行用 {{query|safe}} 关闭 Django 自动转义后直接输出到 HTML。URL 未命中 FAANG 记录时注入 <script>alert(1)</script> 等载荷将在受害者浏览器执行，可窃取会话 Cookie。
- 触发条件：源码已确认：需登录后访问 /xssL?q=<载荷>，且查询未命中数据库记录才走含 safe 的分支；view 无其他过滤。
- 数据流：GET q → views.xss_lab → 模板上下文 query → |safe 原样输出。
- 修复方向：移除 |safe，保持 Django 自动转义；如必须富文本，服务端清洗后再渲染。

### finding-008 — CWE-79（严重度 medium，置信度 high）
- 位置：`introduction/templates/Lab/XSS/xss_lab_2.html` 第 20 行（范围 20:11 – 20:30）
- 代码证据：`{{ username|safe }}`
- 根因与安全影响：过滤可绕过的 XSS：xss_lab2 仅做 username.replace('<script>','').replace('</script>','') 的黑名单清理（views.py 第107-120行），模板以 {{ username|safe }} 原样输出。载荷 <scr<script>ipt>alert(1)</scr</script>ipt> 或 <img src=x onerror=alert(1)> 均可绕过，在 /xssL2 反射执行。
- 触发条件：源码已确认：需登录，POST /xssL2（Django CSRF 中间件仍生效，需携带表单 token 或诱导受害者提交）。
- 数据流：POST username → 黑名单替换 → 模板 |safe 输出。
- 修复方向：移除 |safe；用成熟 HTML 净化库替代黑名单 replace 过滤。

### finding-009 — CWE-79（严重度 medium，置信度 high）
- 位置：`introduction/templates/Lab/XSS/xss_lab_3.html` 第 22 行（范围 22:5 – 22:13）
- 代码证据：`{{code}}`
- 根因与安全影响：脚本上下文 XSS：xss_lab3 用 re.sub(r'[a-zA-Z0-9]','',username) 仅删除字母数字（views.py 第124-136行），模板 xss_lab_3.html 第22行把结果 {{code}} 直接放入 <script> 标签内（第21-23行）。JSFuck 风格的纯符号载荷（[]()!+ 等）在此上下文中无需标签即可执行任意 JS。
- 触发条件：源码已确认：需登录，POST /xssL3；载荷无需绕过 HTML 转义，因为输出位于既有 <script> 块内。
- 数据流：POST username → 删除字母数字 → 模板 <script> 块内输出 {{code}} → JSFuck 载荷执行。
- 修复方向：不要把用户输入放进 <script> 块；如必须，做 JS 上下文安全编码并移除该输出。

### finding-010 — CWE-79（严重度 medium，置信度 high）
- 位置：`introduction/templates/Lab/ssrf/ssrf_lab2.html` 第 23 行（范围 23:70 – 23:89）
- 代码证据：`{{response | safe}}`
- 根因与安全影响：SSRF 响应导致的存储/反射 XSS：ssrf_lab2 将 requests.get(url) 的响应体直接作为 response 传入模板，ssrf_lab2.html 第23行用 {{response | safe}} 原样渲染。攻击者让服务端请求其控制的外部/内网 URL，返回的 HTML/JS 将在受害者浏览器上下文执行；同时该内容也来自内网端点，形成把内网响应泄露给客户端的通道。
- 触发条件：源码已确认：需登录，POST /ssrf_lab2。攻击者需能控制 url 指向的响应（自己的服务器或内网可控端点）。
- 数据流：POST url → requests.get(url) → response.content.decode() → 模板 |safe 输出。
- 修复方向：对 SSRF 响应不使用 |safe；作为纯文本展示并限制长度。

### finding-011 — CWE-79（严重度 medium，置信度 high）
- 位置：`introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html` 第 11 行（范围 11:9 – 11:28）
- 代码证据：`{{username | safe}}`
- 根因与安全影响：反射型 XSS：software_and_data_integrity_failure_lab2 将 GET 参数 username 直接传入模板（views.py 第1220-1227行），lab2.html 第11行以 {{username | safe}} 原样输出。GET 链接可被投递给受害者（视图要求登录，但受害者会话内即可触发）。
- 触发条件：源码已确认：需登录，GET /2021/A8/lab2?username=<载荷>。
- 数据流：GET username → 视图上下文 → 模板 |safe 输出。
- 修复方向：移除 |safe，保持自动转义。

### finding-012 — CWE-284（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 347 行（范围 347:13 – 352:1）
- 代码证据：`if request.COOKIES.get('admin') == "1":`
- 根因与安全影响：基于客户端 Cookie 的授权判定：ba_lab 直接以 request.COOKIES.get('admin') == "1" 决定是否返回管理员机密 0NLY_F0R_4DM1N5（第347-352行），该 Cookie 值由服务端普通流程以明文 set_cookie('admin','1') 下发且无签名。攻击者手动设置 admin=1 Cookie 即可绕过登录口令校验获取管理员数据。
- 触发条件：源码已确认：需登录（任意普通用户），POST /ba_lab 或 GET（GET 时 name=None 走 no_creds 分支，Cookie 判定在 POST 分支内）。
- 数据流：POST name → if Cookies['admin']=='1' → 直接返回管理员机密，跳过口令验证。
- 修复方向：授权判定以服务端会话/角色为准，不信任客户端 Cookie；Cookie 加签名。

### finding-013 — CWE-284（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 758 行（范围 758:9 – 763:1）
- 代码证据：`if request.COOKIES.get('admin') == "1":`
- 根因与安全影响：与 finding-012 相同的客户端 Cookie 授权缺陷出现在另一独立视图 a1_broken_access_lab_1（2021 版 Broken Access Control lab_1，第758-763行）：Cookie admin=1 即返回管理员数据，无需服务端会话校验。该视图还硬编码 jack/jacktheripper 口令（第766行）。
- 触发条件：源码已确认：需登录，POST /broken_access_lab_1。
- 数据流：POST name → Cookies['admin']=='1' → 返回管理员机密。
- 修复方向：同 finding-012；并移除硬编码口令。

### finding-014 — CWE-284（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 791 行（范围 791:5 – 796:1）
- 代码证据：`user_agent = request.META['HTTP_USER_AGENT']`
- 根因与安全影响：以客户端可控的 User-Agent 头做授权：a1_broken_access_lab_2 中只要请求头 User-Agent 等于 pygoat_admin 即直接返回管理员机密（第791-796行），完全绕过凭据校验。UA 头可由攻击者任意设置。
- 触发条件：源码已确认：需登录，POST /broken_access_lab_2，携带 User-Agent: pygoat_admin。
- 数据流：HTTP User-Agent 头 → request.META['HTTP_USER_AGENT'] → 相等即返回管理员数据。
- 修复方向：不以 User-Agent 等客户端头做授权；改用服务端角色校验。

### finding-015 — CWE-862（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 840 行（范围 840:5 – 841:1）
- 代码证据：`# no checking applied here`
- 根因与安全影响：缺失授权检查：a1_broken_access_lab3_secret 渲染包含机密内容的 secret.html 时未做任何角色/权限检查（源码注释明示 '# no checking applied here'，第840行）。a1_broken_access_lab_3 中普通用户 John 与管理员 admin 使用同一登录入口，任何已登录（甚至仅知道该 URL）的用户都能访问 /broken_access_controle/secret 获取管理员页面。
- 触发条件：源码已确认：视图仅要求 request.user.is_authenticated（任意账号），无 admin 角色判定。
- 数据流：GET /broken_access_controle/secret → 直接 render(secret.html)，无权限判定。
- 修复方向：补充角色/权限校验（如 request.user.is_staff）后再渲染机密页面。

### finding-016 — CWE-284（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 537 行（范围 537:5 – 538:1）
- 代码证据：`if(XHost == 'admin.localhost:8000'):`
- 根因与安全影响：以可伪造的请求头做访问控制并泄露机密：secret() 视图（路由 /secret，无任何登录要求）在 X-Host 请求头等于 admin.localhost:8000 时返回 S3CR37K3Y（第536-538行）。X-Host 为客户端可控头，攻击者直接携带该头即可未认证获取机密；不匹配时还会把攻击者头值回显进页面。
- 触发条件：源码已确认：/secret 路由无认证装饰器（urls.py）。部署条件：反向代理是否会剥离自定义头视部署而定，直连 Django 时必然可伪造。
- 数据流：HTTP X-Host 头 → 字符串比较 → 命中即渲染 secret=S3CR37K3Y。
- 修复方向：访问控制改为服务端身份+角色判定；不得以可伪造头(X-Host/Host)作为唯一依据；机密不放入响应。

### finding-017 — CWE-307（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 496 行（范围 496:9 – 511:1）
- 代码证据：`otpN=randint(100,999)`
- 根因与安全影响：OTP 认证缺陷（多项叠加）：GET /otp 时生成仅 3 位数（100-999，共 900 种）的 OTP，且对非管理员邮箱直接把 OTP 明文渲染进响应页（第506行 {"otp":otpN}）；POST /otp 校验时无任何尝试次数限制、无过期时间（第511行 filter(email,otp) 或 filter(id=2,otp)）。攻击者可对管理员（id=2 行）在 900 次内爆破 OTP 完成未授权登录，或直接读取响应中的 OTP。@csrf_exempt 且无登录要求。
- 触发条件：源码已确认：/otp 端点无需认证；爆破无需前置条件。部署条件：无速率限制中间件（源码未见）。
- 数据流：GET email → randint(100,999) 存库并回显 → POST otp 无次数限制校验 → 登录成功页。
- 修复方向：OTP 用 secrets 生成足够长度随机值、限时限次、不回显；引入失败锁定与速率限制。

### finding-018 — CWE-502（严重度 critical，置信度 high）
- 位置：`introduction/views.py` 第 560 行（范围 560:21 – 561:1）
- 代码证据：`data = yaml.load(file,yaml.Loader)`
- 根因与安全影响：不安全的 YAML 反序列化：a9_lab 用 yaml.load(file, yaml.Loader) 解析用户上传文件（第560行）。PyYAML 5.1 的 yaml.Loader 等价于不安全的 full loader，支持 !!python/object 等 tag，可实例化任意 Python 对象（如 os.system）实现上传即 RCE。requirements.txt 锁定 PyYAML==5.1（另见 finding-048）。
- 触发条件：源码已确认：需登录，POST /a9_lab 上传恶意 YAML。部署条件：环境中 PyYAML 版本为 requirements.txt 所锁 5.1。
- 数据流：multipart file → yaml.load(Loader) → python/object 构造器执行任意代码。
- 修复方向：使用 yaml.safe_load；升级 PyYAML 至受支持版本。

### finding-019 — CWE-94（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 588 行（范围 588:13 – 589:1）
- 代码证据：`output = ImageMath.eval(function_str,img = img, b=b, r=r, g=g)`
- 根因与安全影响：表达式求值代码注入：a9_lab2 将 POST 参数 function_str 直接传入 PIL.ImageMath.eval（第588行）。ImageMath.eval 会把字符串编译为 Python 表达式并执行，历史上被证明可借其内置环境实现任意代码执行/文件读取（表达式本身即为可执行代码）。
- 触发条件：源码已确认：需登录，POST /a9_lab2，需同时上传可被 PIL 打开的图片文件。部署条件：Pillow 版本按 requirements.txt 为 9.4.0。
- 数据流：POST function_str + file → Image.open → ImageMath.eval(function_str,...) → 表达式执行。
- 修复方向：不将用户输入传给 ImageMath.eval；如需表达式功能用受限 AST 求值并沙箱化。

### finding-020 — CWE-22（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 926 行（范围 926:17 – 928:1）
- 代码证据：`filename = os.path.join(dirname, file)`
- 根因与安全影响：路径穿越/任意文件读取：ssrf_lab 将 POST 参数 blog 与视图目录 os.path.join 后直接 open().read() 并回显（第924-929行）。blog 值为 '../../../etc/passwd' 之类相对路径时 os.path.join 不会限制在 templates 目录内，可读取应用进程可访问的任意文件（源码、settings、数据库文件等）。
- 触发条件：源码已确认：需登录，POST /ssrf_lab。无任何路径规范化/白名单。
- 数据流：POST blog → os.path.join(dirname, blog) → open().read() → 内容回显 blog。
- 修复方向：对文件名做 basename + 目录白名单校验（os.path.realpath 前缀检查），禁止 '..'。

### finding-021 — CWE-918（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 963 行（范围 963:13 – 963:41）
- 代码证据：`response = requests.get(url)`
- 根因与安全影响：SSRF：ssrf_lab2 将 POST 参数 url 直接交给 requests.get（第963行），无 scheme/host 白名单或内网地址过滤。攻击者可让服务器访问内网地址（http://127.0.0.1:8000/ssrf_target、云元数据端点等），响应体经 |safe 渲染回显（同时构成 finding-010 的 XSS 源）。ssrf_target 端点本身以 X-Forwarded-For=127.0.0.1 做访问控制，可被本 SSRF 绕过。
- 触发条件：源码已确认：需登录，POST /ssrf_lab2。
- 数据流：POST url → requests.get(url) → response.content → 模板回显。
- 修复方向：对 URL 做 scheme/host 白名单，禁止内网/环回/元数据地址；出口请求经代理隔离。

### finding-022 — CWE-1336（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 996 行（范围 996:13 – 1006:1）
- 代码证据：`file.write(blog)`
- 根因与安全影响：服务端模板注入（SSTI）：ssti_lab 把用户提交的博客内容（仅经恒等函数 filter_blog 处理，utility.py）包上 Django 模板标签后写入 templates/Lab_2021/A3_Injection/Blogs/<id>.html（第995-998行），ssti_view_blog 随后用 render() 将该用户内容作为 Django 模板编译执行（第1006行）。攻击者可在博客中嵌入 {% include %}/{% extends %} 等模板语法，实现任意模板文件包含、信息泄露；用户内容进入模板引擎而非数据位，是典型的模板注入根因。
- 触发条件：源码已确认：需登录，POST /ssti/lab 提交内容后访问 /ssti/blog/<id>。filter_blog 未做任何过滤（introduction/utility.py 末行）。
- 数据流：POST blog → filter_blog(不过滤) → 写入模板文件 → render(该文件) → 模板语法被服务端执行。
- 修复方向：用户内容作为数据渲染（模板上下文变量），绝不写入模板文件；若必须，转义模板语法。

### finding-023 — CWE-328（严重度 medium，置信度 high）
- 位置：`introduction/views.py` 第 1026 行（范围 1026:17 – 1026:62）
- 代码证据：`password = md5(password.encode()).hexdigest()`
- 根因与安全影响：以 MD5 存储校验口令：crypto_failure_lab 对登录口令做 md5 后与 CF_user 表比对（第1026行）。MD5 无加盐、抗碰撞/抗暴力破解能力极弱，数据库泄露后口令可被快速还原；等效弱哈希实现还出现在 introduction/mitre.py 第161行（独立位置，见 finding-037）。
- 触发条件：源码已确认：需登录后访问 /cryptographic_failure/lab；CF_user 表由迁移/使用过程写入。
- 数据流：POST username/password → md5 → ORM filter(password=md5值) → 命中即视为登录成功。
- 修复方向：改用 Argon2/bcrypt/PBKDF2 等慢哈希加盐存储口令。

### finding-024 — CWE-347（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 1060 行（范围 1060:17 – 1060:54）
- 代码证据：`elif cookie.split('|')[0] == 'admin':`
- 根因与安全影响：可伪造的未签名会话 Cookie：crypto_failure_lab3 的身份 Cookie 格式为 'username|过期时间' 明文（第1074-1076行 set_cookie），GET 分支仅按 cookie.split('|')[0]=='admin' 判定管理员（第1060行），无签名/HMAC。攻击者直接设置 Cookie cookie='admin|2099-01-01 00:00:00' 即可未认证获取管理员视图。
- 触发条件：源码已确认：/cryptographic_failure/lab3 GET 分支在登录前也会执行（is_authenticated 检查在函数开头，伪造 Cookie 需先登录任意账号或直接访问；视图要求 is_authenticated）。
- 数据流：Cookie cookie → split('|') → 取第一段比较 'admin' → 授予 admin 视图，无任何密码学校验。
- 修复方向：会话 Cookie 必须签名（HMAC/JWT 带签名+过期+服务端校验），不可由客户端自拼字段。

### finding-025 — CWE-256（严重度 medium，置信度 high）
- 位置：`introduction/views.py` 第 287 行（范围 287:13 – 287:89）
- 代码证据：`obj = authLogin.objects.create(name=name,username=user_name,password=passwd)`
- 根因与安全影响：明文存储口令：auth_lab_signup 将注册口令原样写入 authLogin.password（第289行，模型为普通 CharField，introduction/models.py），auth_lab_login 也以明文比对。数据库或备份泄露即导致所有该 lab 用户口令直接泄露。
- 触发条件：源码已确认：POST /auth_lab/signup。
- 数据流：POST pass → authLogin.objects.create(password=明文) → 数据库存储。
- 修复方向：口令经强哈希（加盐慢哈希）后存储；比对用恒定时间函数。

### finding-026 — CWE-614（严重度 low，置信度 high）
- 位置：`introduction/views.py` 第 291 行（范围 291:17 – 291:105）
- 代码证据：`response.set_cookie('userid', obj.userid, max_age=31449600, samesite=None, secure=False)`
- 根因与安全影响：会话 Cookie 缺少安全属性：auth_lab 系列 set_cookie('userid', ..., samesite=None, secure=False)（第291、305、319行），未设 HttpOnly（Django 默认 httponly=False）、未设 Secure，且 samesite=None 显式允许跨站携带，一年有效期（max_age=31449600）。userid 为可预测的自增值，配合明文存储/弱会话设计扩大冒用风险。
- 触发条件：源码已确认：/auth_lab/signup、/auth_lab/login。部署条件：HTTPS 部署下 Secure=False 仍可能经明文信道泄露。
- 数据流：登录成功 → set_cookie(userid, samesite=None, secure=False, 无 HttpOnly) → Cookie 暴露给 JS/跨站请求。
- 修复方向：set_cookie 加 httponly=True、secure=True、samesite='Lax'，缩短有效期。

### finding-027 — CWE-532（严重度 medium，置信度 high）
- 位置：`introduction/views.py` 第 637 行（范围 637:5 – 642:1）
- 代码证据：`response = render(request,'Lab/A10/debug.log')`
- 根因与安全影响：敏感信息进入日志且日志公开可读：debug 视图（/debug，无认证检查）把服务器请求日志文件 Lab/A10/debug.log 原样作为响应返回（第636-640行），文件中包含带凭据的请求记录（如 GET /a10_lab?username=Hacker&password=Hacker）；另 logging.basicConfig(level=DEBUG, filename='app.log')（第642行）与 auth_lab_login 中 print(user_name,passwd)（第314行）把口令写入日志/标准输出。
- 触发条件：源码已确认：/debug 路由无 is_authenticated 检查（views.py 第636-640行）。debug.log 文件需随部署存在（仓库中已含该文件）。
- 数据流：请求 URL（含凭据）→ 服务器访问日志 → debug 视图直接回传日志文件 → 未认证用户读取。
- 修复方向：日志不记录明文口令；debug 路由删除或加管理员权限；日志文件不放入可路由目录。

### finding-028 — CWE-798（严重度 high，置信度 high）
- 位置：`introduction/views.py` 第 831 行（范围 831:9 – 833:1）
- 代码证据：`if username == 'John' and password == 'reaper':`
- 根因与安全影响：硬编码凭据：源码中多处明文硬编码口令——a1_broken_access_lab_3 中 John/reaper 与 admin/admin_pass（第831-833行）、a1_broken_access_lab_1 中 jack/jacktheripper（第766行）、crypto_failure_lab3 中 User/P@$$w0rd（第1072行）、注释中直接写出管理员口令 2022_in_pygoat@pygoat.com（第1119行）、USER_A7_LAB3 字典硬编码 SHA256 口令表（第1130-1135行）。任何拿到源码者均可直接登录相应 lab 获取机密数据。
- 触发条件：源码已确认：无需部署信息，凭据随源码分发。
- 数据流：源码内硬编码凭据 → 对应 lab 登录端点比对通过 → 返回机密。
- 修复方向：移除源码中全部硬编码口令与口令注释；使用环境变量/密管系统。

### finding-029 — CWE-352（严重度 medium，置信度 high）
- 位置：`introduction/views.py` 第 414 行（范围 414:1 – 415:1）
- 代码证据：`@csrf_exempt`
- 根因与安全影响：对状态变更/敏感视图系统性禁用 CSRF 防护：@csrf_exempt 覆盖 cmd_lab（第414行）、cmd_lab2（452）、Otp（492）、a9_lab（550）、a9_lab2（573）、ba（738）、ba_lab（746）、a1_broken_access（746 附近）、injection/injection_sql_lab（846/854 附近）、xxe_see/xxe_parse（239/255）、auth_failure_lab3（1178）等。已登录受害者的浏览器被诱导跨站提交时，攻击者可借其会话执行命令注入类 lab 的请求、修改 OTP、注入评论等。Django 全局 CSRF 中间件存在但被逐视图豁免。
- 触发条件：源码已确认：以上视图均无额外 CSRF token 校验；受害者需处于登录态并访问攻击者页面。
- 数据流：第三方页面构造跨站 POST → 浏览器携带受害者 Cookie 提交 → 被 @csrf_exempt 视图接受执行。
- 修复方向：移除敏感视图上的 @csrf_exempt；确需豁免的接口改用其他防 CSRF 机制（如 Origin 校验+token）。

### finding-030 — CWE-94（严重度 critical，置信度 high）
- 位置：`introduction/apis.py` 第 61 行（范围 61:1 – 73:1）
- 代码证据：`def log_function_checker(request):`
- 根因与安全影响：未认证任意代码写入并执行：log_function_checker（/2021/discussion/A9/api）的 @authentication_decorator 被注释掉、仅剩 @csrf_exempt（第59-61行），将 POST 参数 log_code、api_code 原样写入 introduction/playground/A9/main.py 与 api.py（第70、73行）。这两个模块被 urls.py 与本模块导入并实例化/调用（log_function_target 使用 Log 类，A6_disscussion_api 间接导入链触发），写入任意 Python 代码即获得服务端代码执行。
- 触发条件：源码已确认：无需登录（装饰器已注释）；POST /2021/discussion/A9/api。执行触发：导入发生在新进程/重载时（Django runserver 重载或后续请求导入），写入本身就是持久后门。
- 数据流：POST log_code/api_code → open(main.py/api.py,'w').write → 模块后续被 import → 任意代码执行。
- 修复方向：绝不将用户输入写入可导入的 .py；补认证与授权；代码写入需求改为数据驱动配置。

### finding-031 — CWE-94（严重度 critical，置信度 high）
- 位置：`introduction/apis.py` 第 26 行（范围 26:13 – 46:1）
- 代码证据：`python_code = request.POST['python_code']`
- 根因与安全影响：任意代码执行（认证后）：ssrf_code_checker（/api/ssrf，@csrf_exempt）将 POST python_code 经 ssrf_code_converter 写入 introduction/playground/ssrf/main.py（introduction/utility.py 第26-38行，无任何净化），随后在同一请求内调用 main.ssrf_lab(inputs) 执行刚写入的用户代码（第38、46行），构成直接 RCE。
- 触发条件：源码已确认：需登录（request.user.is_authenticated），POST /api/ssrf。
- 数据流：POST python_code → 写 playground/ssrf/main.py → import main → main.ssrf_lab() 执行用户代码。
- 修复方向：同 finding-030：用户代码只存数据库展示，不落盘到 import 路径、不执行。

### finding-032 — CWE-94（严重度 high，置信度 high）
- 位置：`introduction/apis.py` 第 126 行（范围 126:1 – 136:1）
- 代码证据：`def A6_disscussion_api_2(request):`
- 根因与安全影响：任意 Python 文件写入（认证后可致 RCE）：A6_disscussion_api_2（/2021/discussion/A6/api2，@csrf_exempt，无登录校验）将 POST code 原样写入 introduction/playground/A6/utility.py（第134行）；该文件被 urls.py 导入链与本模块 A6_disscussion_api 使用的 check_vuln 引用，写入的代码将在后续导入/调用时执行。
- 触发条件：源码已确认：端点本身未校验用户身份（仅检查请求方法）。
- 数据流：POST code → 写 playground/A6/utility.py → 后续 import → 任意代码执行。
- 修复方向：同 finding-030；对该端点补认证。

### finding-033 — CWE-94（严重度 critical，置信度 high）
- 位置：`introduction/mitre.py` 第 218 行（范围 218:9 – 218:34）
- 代码证据：`result = eval(expression)`
- 根因与安全影响：未认证任意代码执行：mitre_lab_25_api（/mitre/25/lab/api）把 POST expression 直接 eval（第218行）；其 @authentication_decorator 被注释、带 @csrf_exempt（第212-214行），无任何登录要求，任何可达该端点者即可执行任意 Python 代码。
- 触发条件：源码已确认：无需登录，POST /mitre/25/lab/api。
- 数据流：POST expression → eval(expression) → 任意代码执行 → 结果 JSON 回显。
- 修复方向：移除 eval；该接口如必须保留需认证+白名单表达式。

### finding-034 — CWE-78（严重度 critical，置信度 high）
- 位置：`introduction/mitre.py` 第 241 行（范围 241:9 – 242:1）
- 代码证据：`command = "nmap " + ip`
- 根因与安全影响：命令注入：mitre_lab_17_api 将 POST ip 拼接到 'nmap ' 后交 command_out() 以 shell=True 执行（第241-242行、第232-233行），无任何输入校验，ip='127.0.0.1; whoami' 即可执行任意命令。
- 触发条件：源码已确认：@csrf_exempt（第237行）且无登录校验；部署条件：主机需安装 nmap 才有正常输出，但命令注入本身在 shell 层面即可触发。
- 数据流：POST ip → 字符串拼接 → Popen(shell=True) → 输出回显。
- 修复方向：参数列表化执行（['nmap', ip], shell=False）并校验 IP 格式。

### finding-035 — CWE-321（严重度 high，置信度 high）
- 位置：`introduction/mitre.py` 第 169 行（范围 169:13 – 169:82）
- 代码证据：`cookie = jwt.encode(payload, 'csrf_vulneribility', algorithm='HS256')`
- 根因与安全影响：硬编码 JWT 签名密钥：csrf_lab_login/csrf_transfer_monei/csrf_transfer_monei_api 使用硬编码密钥 'csrf_vulneribility' 签发与校验 auth_cookiee（第169、182、194行）。密钥随源码泄露，攻击者可自签 {'username':'任意用户'} 的 JWT 直接冒充任意用户访问转账面板。
- 触发条件：源码已确认：密钥在源码中；需知道端点格式。
- 数据流：自签 JWT（username=受害者/任意）→ set 为 auth_cookiee → jwt.decode 用同一硬编码密钥验证通过 → 以该用户身份操作余额。
- 修复方向：JWT 密钥移入环境变量/密管，禁止硬编码；考虑非对称签名。

### finding-036 — CWE-352（严重度 high，置信度 high）
- 位置：`introduction/mitre.py` 第 191 行（范围 191:1 – 213:1）
- 代码证据：`def csrf_transfer_monei_api(request,recipent,amount):`
- 根因与安全影响：GET 方式执行转账状态变更且无 CSRF 防护：csrf_transfer_monei_api 通过 GET /mitre/9/lab/api/<recipent>/<amount> 直接修改账户余额（第191-213行），无 CSRF token 校验，也无需 POST；攻击者在 csrf_dashboard 页面诱导已登录受害者点击/加载 <img src='/mitre/9/lab/api/attacker/100'> 即完成转账。JWT Cookie samesite 未限制进一步放宽了利用条件。
- 触发条件：源码已确认：路由为 GET 形式（urls.py），视图内无 csrf 校验。
- 数据流：GET 链接 → 解析 auth_cookiee → 修改 CSRF_user_tbl 余额并保存。
- 修复方向：状态变更改 POST+CSRF token；GET 仅用于读取。

### finding-037 — CWE-328（严重度 medium，置信度 high）
- 位置：`introduction/mitre.py` 第 161 行（范围 161:9 – 161:54）
- 代码证据：`password = md5(password.encode()).hexdigest()`
- 根因与安全影响：以 MD5 校验口令（独立于 finding-023 的位置）：mitre/csrf_lab_login 对 CSRF_user_tbl 的口令做无盐 MD5 比对（第161行），数据库泄露后口令可被快速破解。
- 触发条件：源码已确认：POST /mitre/9/lab/login。
- 数据流：POST password → md5 → ORM filter → 登录。
- 修复方向：同 finding-023：改用强口令哈希。

### finding-038 — CWE-798（严重度 high，置信度 high）
- 位置：`pygoat/settings.py` 第 25 行（范围 25:1 – 27:1）
- 代码证据：`SECRET_KEY = 'lr66%-a!$km5ed@n5ug!tya5bv!0(yqwa1tn!q%0%3m2nh%oml'`
- 根因与安全影响：硬编码密钥：Django SECRET_KEY 硬编码在源码中（第25行），SECRET_COOKIE_KEY="PYGOAT"（第171行）被 sec_misconfig_lab3 用于 JWT 签名（views.py 第1101-1103行）。密钥随源码泄露后，攻击者可伪造 Django 会话 Cookie、伪造 sec_misconfig_lab3 的 admin JWT，直接获取管理员视图。
- 触发条件：源码已确认：settings 随源码分发；docker-compose 直接 COPY . /app。
- 数据流：源码内密钥 → 伪造 sessionid（Django 签名）或 auth_cookie（JWT HS256 'PYGOAT'）→ 通过认证/授权。
- 修复方向：SECRET_KEY/SECRET_COOKIE_KEY 经环境变量注入并轮换；禁止随源码分发。

### finding-039 — CWE-489（严重度 medium，置信度 high）
- 位置：`pygoat/settings.py` 第 30 行（范围 30:1 – 30:13）
- 代码证据：`DEBUG = True`
- 根因与安全影响：生产配置开启 DEBUG：pygoat/settings.py 第30行 DEBUG=True，而 docker-compose/Dockerfile 以 gunicorn 生产方式运行。出错页面将暴露设置、环境变量（含上述密钥）与完整栈回溯，放大所有注入类漏洞的利用效果。
- 触发条件：源码已确认：DEBUG=True 为仓库默认；生产部署方式见 docker-compose.yml。
- 数据流：触发任意未处理异常（如 /500error 视图返回 None）→ Django 调试页输出敏感配置。
- 修复方向：生产环境 DEBUG=False；DEBUG 信息经日志系统受控输出。

### finding-040 — CWE-862（严重度 critical，置信度 high）
- 位置：`dockerized_labs/sensitive_data_exposure/dataexposure/views.py` 第 112 行（范围 112:1 – 132:1）
- 代码证据：`def all_users_data_view(request):`
- 根因与安全影响：未认证批量泄露全量敏感数据：all_users_data_view（/api/all-users，dataexposure/urls.py 已路由）不做任何认证/授权检查，遍历 UserData.objects.all() 返回所有用户的完整信用卡号、SSN 与 API key（第112-132行）。任何能访问该子应用的人即可一次性获取全部用户敏感数据。
- 触发条件：源码已确认：视图无任何检查；部署条件：sensitive_data_exposure 子应用按 docker-compose 暴露 8000 端口。
- 数据流：GET /api/all-users → UserData.objects.all() → JsonResponse 全量敏感字段。
- 修复方向：增加认证+管理员授权；敏感字段脱敏；如为演示接口，默认禁用。

### finding-041 — CWE-330（严重度 medium，置信度 high）
- 位置：`dockerized_labs/sensitive_data_exposure/dataexposure/views.py` 第 38 行（范围 38:1 – 42:1）
- 代码证据：`def generate_api_key():`
- 根因与安全影响：API key 使用非加密安全随机数生成：generate_api_key 用 random.choices（Mersenne Twister，非 secrets）生成 16 位 API key（第38-42行），可预测性高于密码学随机；同时 UserData 中信用卡、SSN 以明文存储（models.py 第6-8行）。
- 触发条件：源码已确认：注册流程调用；攻击者需掌握部分输出或状态以推断后续值（利用难度较高，故降级为 medium）。
- 数据流：注册 → random.choices 生成 api_key → 存库并经 /api/user-data 暴露。
- 修复方向：改用 secrets 模块生成 API key；敏感数据（卡号/SSN）加密存储。

### finding-042 — CWE-330（严重度 high，置信度 high）
- 位置：`dockerized_labs/broken_auth_lab/app.py` 第 86 行（范围 86:13 – 91:1）
- 代码证据：`token = hashlib.md5(f"{email}:{datetime.now()}".encode()).hexdigest()`
- 根因与安全影响：可预测的口令重置令牌：reset_password 以 md5(email:当前时间) 生成重置 token（第86行），token 随 flash 消息回显且无需认证即可对任意已知邮箱触发（第91行）；时间可被枚举，令牌可预测。配合 /reset/<token> 即可接管任意账户。
- 触发条件：源码已确认：POST /reset-password 无认证；需要知道受害者注册邮箱并缩小时间窗口。
- 数据流：POST email → md5(email:now) → token 存内存字典并回显 → /reset/<token> 重置。
- 修复方向：重置令牌用 secrets.token_urlsafe 生成、限时限次、不经响应回显（走邮件）。

### finding-043 — CWE-287（严重度 high，置信度 high）
- 位置：`dockerized_labs/broken_auth_lab/app.py` 第 45 行（范围 45:9 – 52:1）
- 代码证据：`session_token = base64.b64encode(f"{username}:{datetime.now()}".encode()).decode()`
- 根因与安全影响：可伪造的未签名会话令牌：login 以 base64('username:时间') 作为 session Cookie（第45-52行），dashboard 仅 base64 解码后取用户名判定（第111行），无签名、无过期、无服务端会话。攻击者设置 Cookie session=base64('admin:x') 即可冒充 admin（角色信息 users['admin']['role'] 随之泄露 dashboard 内容）。
- 触发条件：源码已确认：/dashboard 无其他校验。
- 数据流：伪造 session Cookie → b64decode → username='admin' in users → 渲染 dashboard。
- 修复方向：会话令牌需服务端签发+签名+过期+失效机制（如 itsdangerous/Flask session）。

### finding-044 — CWE-256（严重度 medium，置信度 high）
- 位置：`dockerized_labs/broken_auth_lab/app.py` 第 13 行（范围 13:9 – 18:1）
- 代码证据：`'password': 'admin123',  # Vulnerable: Weak password`
- 根因与安全影响：明文/弱口令凭据存储：users 字典硬编码 admin/admin123 与 user/password123 明文口令（第13、18行），register 同样明文存储新口令（第68行），登录为明文比较（第41行）。应用源码即泄露全部凭据。
- 触发条件：源码已确认。
- 数据流：源码内凭据 → POST /login 明文比对 → 登录。
- 修复方向：凭据不硬编码；口令强哈希存储；默认弱口令首次登录强制修改。

### finding-045 — CWE-502（严重度 critical，置信度 high）
- 位置：`dockerized_labs/insec_des_lab/main.py` 第 36 行（范围 36:9 – 42:1）
- 代码证据：`user = pickle.loads(decoded_data)`
- 根因与安全影响：不安全的反序列化：/deserialize 将用户提交的 serialized_data base64 解码后直接 pickle.loads（第37行），User 类还定义了 __reduce__（第12-14行）演示构造载荷；攻击者提交恶意 pickle 即可在服务端执行任意代码。与 introduction/views.py 的 finding-003 属不同应用的独立位置。
- 触发条件：源码已确认：POST /deserialize 无认证；部署条件：insec_des_lab 子应用暴露 8080 端口。
- 数据流：POST serialized_data → b64decode → pickle.loads → __reduce__ 任意代码执行。
- 修复方向：禁止对客户端输入 pickle 反序列化；改 JSON+签名。

### finding-046 — CWE-489（严重度 medium，置信度 high）
- 位置：`dockerized_labs/broken_auth_lab/app.py` 第 123 行（范围 123:5 – 123:51）
- 代码证据：`app.run(host='0.0.0.0', port=5000, debug=True)`
- 根因与安全影响：Flask 调试模式对外监听：app.run(host='0.0.0.0', port=5000, debug=True)（文件末行）开启 Werkzeug 交互式调试器并绑定所有网卡；按 docker-compose 暴露端口后，未处理异常页可进入调试控制台（受 PIN 保护，但 PIN 可由容器内公开信息推导），存在导致 RCE 的风险。
- 触发条件：源码已确认；部署条件：docker-compose 映射 5000 端口对外。
- 数据流：触发异常 → Werkzeug debugger 页面 → 控制台执行代码。
- 修复方向：生产关闭 debug；Flask 用 WSGI 服务器运行且 debug=False。

### finding-047 — CWE-798（严重度 medium，置信度 high）
- 位置：`dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py` 第 8 行（范围 8:1 – 14:1）
- 代码证据：`SECRET_KEY = 'django-insecure-key-for-demonstration-only'`
- 根因与安全影响：子应用 Django 配置弱默认：硬编码可预测 SECRET_KEY（第8行）、DEBUG=True（第11行）、ALLOWED_HOSTS=['*']（第13行）。会话/CSRF 签名可被伪造，调试页泄露信息，且允许任意 Host 头注入（缓存投毒、密码重置链接投毒等场景）。
- 触发条件：源码已确认：该子应用独立 settings，随源码分发。
- 数据流：源码内密钥/配置 → 伪造会话 cookie 或触发调试页。
- 修复方向：SECRET_KEY 环境变量化；DEBUG=False；ALLOWED_HOSTS 收敛。

### finding-048 — CWE-1104（严重度 medium，置信度 medium）
- 位置：`requirements.txt` 第 27 行（范围 27:1 – 27:12）
- 代码证据：`PyYAML==5.1`
- 根因与安全影响：锁定已知不安全/过时依赖：requirements.txt 锁定 PyYAML==5.1（第27行，配合 yaml.Loader 直接构成 finding-018 的 RCE 链），以及 PyJWT==2.4.0、urllib3==1.26.9、Werkzeug==2.1.2、requests==2.28.2、Pillow==9.4.0 等早已被更高安全版本替代的旧版（各存在已公开的 CVE 记录，本次静态分析未逐一验证可达性）。基础镜像 python:3.11.0b1-buster（Dockerfile 第3行）为 beta 版且基于已停止维护的 Debian buster。
- 触发条件：源码已确认：版本锁定与镜像版本随源码分发；具体 CVE 在运行环境的实际可达性需部署确认。
- 数据流：pip install -r requirements.txt → 安装带已知漏洞的版本 → 应用经 yaml.load/其他入口触达。
- 修复方向：升级至受支持版本（PyYAML≥6、Pillow/PyJWT/urllib3/Werkzeug/requests 最新安全版）；更换受维护基础镜像并定期重建。

## 未覆盖范围与分析局限

- 结论性质：全部发现基于静态分析，未运行应用、未复现攻击、未执行测试；标注“部署环境条件”的前提需实际部署确认。
- 模板与前端资源未逐行审查：introduction/templates 下大量 HTML、CSS、JS（a6.js/a7.js/a9.js/xss.js/ssrf.js 等）仅做了模式搜索与关键模板定点阅读；其余模板可能存在未发现的 XSS 或敏感信息硬编码。
- 未完整阅读的代码包括：数据库迁移文件、challenge/management/commands/populate_challenge.py、mitre 各模板、dockerized_labs 全部 HTML 模板与剩余配置、gh-md-toc、LICENSE 等（详见 coverage.json）。
- challenge/views.py 用数据库值构造 docker 命令（第49、80行），利用前提是攻击者能写入 Challenge 表，证据不足以列为确认发现，已放入 uncertain-findings.json。
- 部分业务逻辑设计缺陷（a11 工单机制、OTP 与 email Cookie 的绑定关系）仅覆盖主要面。
- 本报告不声称“整个仓库安全”或“完整覆盖所有漏洞”；48 项确认发现为静态证据支持的下限，而非全集。
