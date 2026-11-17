# PyGoat 静态安全审查报告（实验 01 / A 组 / minimax-m3.1-flash / r01）

本报告为**纯静态分析**结果：本次运行没有启动应用、没有执行测试或利用代码、没有运行任何漏洞扫描器，也没有安装依赖。所有结论均来自对输入目录源码的阅读与人工推理。

- 确认发现数量：**47**
- 未确认候选：见 `uncertain-findings.json`
- 审查范围：`D:/ai_share/langgraph/benchmark-data/pygoat-baseline/inputs/experiment-01/pygoat`（源码提交 `2fb0c600245f50670e8b9233c784afe61e8b340b`）

> 说明：PyGoat 是**故意设计为存在漏洞**的教学应用（OWASP PyGoat），因此多数发现位于“实验/lab”视图中，其目的是教学而非生产使用；但从代码证据看，这些位置确实存在缺失的安全校验，具有真实的安全影响。

## 发现汇总

| 编号 | 文件 | 行 | CWE | 严重度 | 置信度 | 问题 |
| --- | --- | --- | --- | --- | --- | --- |
| finding-003 | `introduction/views.py` | 424 | CWE-78 | critical | high | OS command injection |
| finding-004 | `introduction/views.py` | 460 | CWE-95 | critical | high | Code injection via eval() |
| finding-005 | `introduction/mitre.py` | 218 | CWE-95 | critical | high | Unauthenticated remote code execution |
| finding-006 | `introduction/mitre.py` | 241 | CWE-78 | critical | high | OS command injection (unauthenticated) |
| finding-007 | `introduction/views.py` | 214 | CWE-502 | critical | high | Insecure deserialization |
| finding-009 | `dockerized_labs/insec_des_lab/main.py` | 36 | CWE-502 | critical | high | Insecure deserialization in the dockerized insecure-design lab |
| finding-012 | `introduction/views.py` | 588 | CWE-95 | critical | medium | Code injection through Pillow's ImageMath.eval |
| finding-025 | `pygoat/settings.py` | 171 | CWE-321 | critical | high | Hard-coded cryptographic key used to sign and verify authentication tokens |
| finding-001 | `introduction/views.py` | 158 | CWE-89 | high | high | SQL injection |
| finding-002 | `introduction/views.py` | 864 | CWE-89 | high | high | SQL injection in the 2021 A3 injection lab |
| finding-008 | `introduction/views.py` | 560 | CWE-502 | high | high | Unsafe YAML deserialization |
| finding-010 | `introduction/views.py` | 926 | CWE-22 | high | high | Path traversal / arbitrary file read |
| finding-011 | `introduction/views.py` | 963 | CWE-918 | high | high | Server-Side Request Forgery |
| finding-013 | `introduction/views.py` | 984 | CWE-1336 | high | high | Server-Side Template Injection |
| finding-014 | `introduction/apis.py` | 70 | CWE-94 | high | medium | Unauthenticated arbitrary Python source injection |
| finding-015 | `introduction/apis.py` | 134 | CWE-94 | high | medium | Unauthenticated arbitrary Python source injection |
| finding-016 | `introduction/utility.py` | 36 | CWE-94 | high | medium | Arbitrary Python source injection through the SSRF playground |
| finding-017 | `introduction/views.py` | 259 | CWE-611 | high | high | XML External Entity (XXE) injection |
| finding-018 | `introduction/views.py` | 347 | CWE-602 | high | high | Broken access control |
| finding-019 | `introduction/views.py` | 758 | CWE-602 | high | high | Broken access control (2021 A1 lab) |
| finding-020 | `introduction/views.py` | 791 | CWE-807 | high | high | Broken access control based on a spoofable client header |
| finding-021 | `introduction/templates/Lab/XSS/xss_lab.html` | 27 | CWE-79 | high | high | Reflected cross-site scripting |
| finding-022 | `introduction/templates/Lab/XSS/xss_lab_2.html` | 20 | CWE-79 | high | high | Reflected cross-site scripting |
| finding-026 | `introduction/mitre.py` | 169 | CWE-321 | high | high | Hard-coded JWT signing secret |
| finding-027 | `introduction/views.py` | 1053 | CWE-345 | high | high | Unsigned client-side session cookie drives an authorization decision |
| finding-031 | `introduction/views.py` | 287 | CWE-256 | high | high | Plain-text storage of user passwords |
| finding-034 | `pygoat/settings.py` | 25 | CWE-798 | high | high | Hard-coded Django SECRET_KEY committed to the repository |
| finding-035 | `introduction/views.py` | 514 | CWE-287 | high | high | Authentication bypass in the OTP login |
| finding-037 | `introduction/mitre.py` | 191 | CWE-352 | high | high | State changing operation without CSRF protection |
| finding-039 | `dockerized_labs/sensitive_data_exposure/dataexposure/views.py` | 112 | CWE-306 | high | high | Missing authentication on a sensitive data endpoint |
| finding-041 | `dockerized_labs/broken_auth_lab/app.py` | 111 | CWE-565 | high | high | Forgable session token |
| finding-042 | `dockerized_labs/broken_auth_lab/app.py` | 86 | CWE-330 | high | high | Weak password reset mechanism |
| finding-043 | `dockerized_labs/broken_auth_lab/app.py` | 8 | CWE-798 | high | high | Hard-coded Flask session secret |
| finding-023 | `introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html` | 11 | CWE-79 | medium | high | Reflected cross-site scripting |
| finding-024 | `introduction/templates/Lab/ssrf/ssrf_lab2.html` | 23 | CWE-79 | medium | high | Cross-site scripting through the SSRF response |
| finding-028 | `introduction/views.py` | 1026 | CWE-328 | medium | high | Use of a broken hash algorithm for password storage |
| finding-029 | `introduction/views.py` | 1042 | CWE-916 | medium | high | Password hashing without a salt |
| finding-030 | `introduction/mitre.py` | 161 | CWE-328 | medium | high | Broken hash algorithm for password verification in the MITRE CSRF lab |
| finding-032 | `introduction/models.py` | 23 | CWE-256 | medium | high | Plain-text password storage in the shared login table |
| finding-033 | `pygoat/settings.py` | 30 | CWE-489 | medium | high | Debug mode is enabled in the shipped settings |
| finding-036 | `introduction/views.py` | 496 | CWE-330 | medium | high | Predictable one-time password |
| finding-038 | `introduction/views.py` | 943 | CWE-290 | medium | high | Access control based on a spoofable request header |
| finding-040 | `dockerized_labs/sensitive_data_exposure/dataexposure/views.py` | 87 | CWE-200 | medium | high | Exposure of sensitive personal data through an API |
| finding-044 | `dockerized_labs/broken_auth_lab/app.py` | 123 | CWE-489 | medium | high | The Flask development server is started with debug=True on 0.0.0.0 |
| finding-045 | `introduction/playground/A9/api.py` | 16 | CWE-532 | medium | high | Sensitive information written to a log file |
| finding-046 | `introduction/views.py` | 536 | CWE-807 | medium | high | Security decision based on a client supplied header |
| finding-047 | `introduction/views.py` | 291 | CWE-614 | medium | high | Authentication cookie issued without the Secure attribute |

## 逐条发现

### finding-003 — introduction/views.py:424（CWE-78，critical，置信度 high）

**问题说明 / 根因与安全影响**

OS command injection: the POST parameter 'domain' is only stripped of common URL prefixes and then interpolated into a shell command string ('nslookup {domain}' / 'dig {domain}') that is executed with subprocess.Popen(..., shell=True). Shell metacharacters such as ';' or '$()' allow arbitrary command execution with the privileges of the web server process.

**代码证据**

```python
            print(os)
            if(os=='win'):
                command="nslookup {}".format(domain)
            else:
                command = "dig {}".format(domain)
            
            try:
                # output=subprocess.check_output(command,shell=True,encoding="UTF-8")
                process = subprocess.Popen(
                    command,
                    shell=True,
```

**触发条件**

Source-confirmed: authenticated user session required; the view is also decorated with @csrf_exempt. Deployment-dependent: requires a POSIX-like shell available to the process (the deployment targets Linux/Docker); on Windows the same injection class applies through cmd.exe.

**数据流**

request.POST['domain'] -> regex strip at introduction/views.py:422 (protocols only) -> string .format() into command at introduction/views.py:424/426 -> subprocess.Popen(command, shell=True) at introduction/views.py:430 -> stdout/stderr rendered in Lab/CMD/cmd_lab.html.

**修复方向**

避免 `shell=True` 与字符串拼接；改用参数数组调用子进程（`subprocess.run([...], shell=False)`），或改用无 shell 的库函数（DNS 查询用 `socket`/`dnspython`）。

### finding-004 — introduction/views.py:460（CWE-95，critical，置信度 high）

**问题说明 / 根因与安全影响**

Code injection via eval(): the POST parameter 'val' is passed directly to eval() and the result is returned to the caller. Any authenticated user can execute arbitrary Python expressions (e.g. __import__('os').system(...)), giving full remote code execution.

**代码证据**

```python
            try:
                output = eval(val)
```

**触发条件**

Source-confirmed: authenticated user session required; the view is @csrf_exempt. No additional deployment condition.

**数据流**

request.POST['val'] -> eval(val) at introduction/views.py:460 -> result rendered in Lab/CMD/cmd_lab2.html.

**修复方向**

删除 `eval`/`exec` 及等价的动态求值；改用显式的解析器（如 `ast.literal_eval`、安全的表达式解析库）或白名单映射。

### finding-005 — introduction/mitre.py:218（CWE-95，critical，置信度 high）

**问题说明 / 根因与安全影响**

Unauthenticated remote code execution: the mitre/25/lab/api endpoint evaluates the POST parameter 'expression' with eval(). The authentication decorator is explicitly commented out ('# @authentication_decorator') and the view is @csrf_exempt, so any network client can execute arbitrary Python code in the web process.

**代码证据**

```python
@csrf_exempt
def mitre_lab_25_api(request):
    if request.method == "POST":
        expression = request.POST.get('expression')
        result = eval(expression)
        return JsonResponse({'result': result})
```

**触发条件**

Source-confirmed: no authentication or CSRF check in the view (commented-out decorator is visible in the source). Deployment-dependent: the endpoint must be reachable, i.e. included in introduction/urls.py (it is, at path 'mitre/25/lab/api').

**数据流**

request.POST['expression'] -> eval(expression) at introduction/mitre.py:218 -> JsonResponse({'result': result}) returned to the caller.

**修复方向**

删除 `eval`/`exec` 及等价的动态求值；改用显式的解析器（如 `ast.literal_eval`、安全的表达式解析库）或白名单映射。

### finding-006 — introduction/mitre.py:241（CWE-78，critical，置信度 high）

**问题说明 / 根因与安全影响**

OS command injection (unauthenticated): the POST parameter 'ip' is concatenated into 'nmap ' + ip and executed via command_out(), which runs subprocess.Popen(command, shell=True). Shell metacharacters allow arbitrary command execution. The view has neither authentication nor CSRF protection.

**代码证据**

```python
        ip = request.POST.get('ip')
        command = "nmap " + ip 
        res, err = command_out(command)
```

**触发条件**

Source-confirmed: no authentication decorator and @csrf_exempt on the view. Deployment-dependent: nmap must be present in the image for the normal flow; the injection itself does not depend on it.

**数据流**

request.POST['ip'] -> concatenation at introduction/mitre.py:241 -> command_out() at introduction/mitre.py:232-234 -> subprocess.Popen(command, shell=True) -> raw stdout/stderr returned in the JSON response.

**修复方向**

避免 `shell=True` 与字符串拼接；改用参数数组调用子进程（`subprocess.run([...], shell=False)`），或改用无 shell 的库函数（DNS 查询用 `socket`/`dnspython`）。

### finding-007 — introduction/views.py:214（CWE-502，critical，置信度 high）

**问题说明 / 根因与安全影响**

Insecure deserialization: the 'token' cookie is base64-decoded and passed to pickle.loads(). Pickle data is executable, so any authenticated user can craft a malicious pickle that executes arbitrary code during deserialization (RCE) and then set admin.admin == 1 to reach the admin-only content.

**代码证据**

```python
        else:
            token = base64.b64decode(token)
            admin = pickle.loads(token)
            if admin.admin == 1:
                response = render(request,'Lab/insec_des/insec_des_lab.html', {"message":"Welcome Admin, SECRETKEY:ADMIN123"})
```

**触发条件**

Source-confirmed: authenticated session required; the cookie value is fully attacker controlled (only base64 encoded). No deployment-specific condition.

**数据流**

request.COOKIES['token'] -> base64.b64decode at introduction/views.py:213 -> pickle.loads(token) at introduction/views.py:214 -> attribute access admin.admin used for the authorization decision.

**修复方向**

禁止反序列化不可信数据：改用 JSON 等无代码执行能力的数据格式；如必须使用 pickle/YAML，则使用 `yaml.safe_load`、带 HMAC 的签名数据或隔离的签名验证。

### finding-009 — dockerized_labs/insec_des_lab/main.py:36（CWE-502，critical，置信度 high）

**问题说明 / 根因与安全影响**

Insecure deserialization in the dockerized insecure-design lab: the POST parameter 'serialized_data' is base64-decoded and handed to pickle.loads(), which executes the embedded pickle opcodes. Any client that can reach the lab container can run arbitrary code inside it and can also forge the is_admin flag to read the admin secret.

**代码证据**

```python
def deserialize_data():
    try:
        serialized_data = request.form.get('serialized_data', '')
        decoded_data = base64.b64decode(serialized_data)
        # Intentionally vulnerable deserialization, matching PyGoat
        user = pickle.loads(decoded_data)
        
        if isinstance(user, User):
```

**触发条件**

Source-confirmed: the /deserialize route has no authentication. Deployment-dependent: the flask app must be deployed/reachable (docker-compose maps port 8080).

**数据流**

request.form['serialized_data'] -> base64.b64decode at main.py:34 -> pickle.loads(decoded_data) at dockerized_labs/insec_des_lab/main.py:36 -> user.is_admin used for the privileged message.

**修复方向**

禁止反序列化不可信数据：改用 JSON 等无代码执行能力的数据格式；如必须使用 pickle/YAML，则使用 `yaml.safe_load`、带 HMAC 的签名数据或隔离的签名验证。

### finding-012 — introduction/views.py:588（CWE-95，critical，置信度 medium）

**问题说明 / 根因与安全影响**

Code injection through Pillow's ImageMath.eval: the POST parameter 'function' is evaluated by ImageMath.eval() with attacker-controlled expression text. ImageMath.eval executes a Python expression built from the supplied string; with the pinned Pillow version (requirements.txt: Pillow==9.4.0) this allows arbitrary code execution in the application process.

**代码证据**

```python
            function_str = request.POST.get("function")
            img  = Image.open(file)
            img = img.convert("RGB")
            r,g,b  = img.split()
            # function_str = "convert(r+g, '1')"
            output = ImageMath.eval(function_str,img = img, b=b, r=r, g=g)

            # saving the image 
```

**触发条件**

Source-confirmed: authenticated session required; the view is @csrf_exempt. Deployment-dependent: exploitability of the expression evaluator depends on the installed Pillow version (Pillow < 10.3.0 is known to allow arbitrary code execution through ImageMath.eval).

**数据流**

request.POST['function'] -> ImageMath.eval(function_str, img=img, b=b, r=r, g=g) at introduction/views.py:588.

**修复方向**

删除 `eval`/`exec` 及等价的动态求值；改用显式的解析器（如 `ast.literal_eval`、安全的表达式解析库）或白名单映射。

### finding-025 — pygoat/settings.py:171（CWE-321，critical，置信度 high）

**问题说明 / 根因与安全影响**

Hard-coded cryptographic key used to sign and verify authentication tokens: SECRET_COOKIE_KEY is the literal string 'PYGOAT' and is used both to issue (jwt.encode) and to verify (jwt.decode) the admin JWT stored in the auth_cookie cookie. Anybody who has read the source can forge a token with payload {'user': 'admin'} and obtain administrator privileges in the security-misconfiguration lab.

**代码证据**

```python
SECRET_COOKIE_KEY = "PYGOAT"
```

**触发条件**

Source-confirmed: the constant is defined in the settings module and used by introduction/views.py:1095 and 1107. Deployment-dependent: the deployment must use the shipped settings module unmodified (no environment override exists for this value).

**数据流**

attacker known constant 'PYGOAT' -> jwt.encode({'user':'admin'}, 'PYGOAT', algorithm='HS256') -> cookie auth_cookie -> request to /sec_mis_lab3 -> jwt.decode(cookie, SECRET_COOKIE_KEY) at introduction/views.py:1095 -> payload['user'] == 'admin' grants the admin view.

**修复方向**

从环境变量/密钥管理系统读取随机生成的密钥，禁止硬编码；对密钥做轮换并避免提交到版本库。

### finding-001 — introduction/views.py:158（CWE-89，high，置信度 high）

**问题说明 / 根因与安全影响**

SQL injection: the 'name' and 'pass' POST parameters are concatenated directly into a raw SQL string that is executed with login.objects.raw(). An attacker can inject SQL (e.g. name=' OR '1'='1) to bypass authentication, read other tables such as introduction_authlogin (plaintext passwords) or the Django auth_user table, and modify data through stacked statements.

**代码证据**

```python
                sql_query = "SELECT * FROM introduction_login WHERE user='"+name+"' AND password='"+password+"'"
```

**触发条件**

Source-confirmed: attacker must be able to reach POST /sql_lab (the view only requires request.user.is_authenticated, and self-registration is available at /register). Deployment-dependent: the query is executed against the configured database (SQLite by default); sqlite3 rejects multiple stacked statements, so the practical impact is read/bypass of data rather than stacked writes.

**数据流**

request.POST['name'] / request.POST['pass'] -> string concatenation at introduction/views.py:158 -> login.objects.raw(sql_query) at introduction/views.py:162 -> results rendered back to the requester ('user1' / 'sql_error' in Lab/SQL/sql_lab.html).

**修复方向**

使用参数化查询（`cursor.execute(sql, [params])` 或 ORM 的过滤参数），禁止把请求参数拼接进 SQL 字符串；必要时对参数做类型校验。

### finding-002 — introduction/views.py:864（CWE-89，high，置信度 high）

**问题说明 / 根因与安全影响**

SQL injection in the 2021 A3 injection lab: the POST parameters 'name' and 'pass' are concatenated into a raw SQL query executed via sql_lab_table.objects.raw(). The query text is also echoed back to the client in the 'sql_error' template variable, which makes exploitation trivial.

**代码证据**

```python
            sql_query = "SELECT * FROM introduction_sql_lab_table WHERE id='"+name+"'AND password='"+password+"'"
```

**触发条件**

Source-confirmed: authenticated user session required (self-registration available at /register). No deployment-specific conditions needed.

**数据流**

request.POST['name'] + request.POST['pass'] -> string concatenation at introduction/views.py:864 -> sql_lab_table.objects.raw(sql_query) at introduction/views.py:878 -> returned rows / query string rendered in Lab_2021/A3_Injection/sql_lab.html.

**修复方向**

使用参数化查询（`cursor.execute(sql, [params])` 或 ORM 的过滤参数），禁止把请求参数拼接进 SQL 字符串；必要时对参数做类型校验。

### finding-008 — introduction/views.py:560（CWE-502，high，置信度 high）

**问题说明 / 根因与安全影响**

Unsafe YAML deserialization: the uploaded file is parsed with yaml.load(file, yaml.Loader), which constructs arbitrary Python objects. A malicious YAML payload (e.g. !!python/object/apply:os.system) achieves remote code execution while uploading the file.

**代码证据**

```python

            try :
                file=request.FILES["file"]
                try :
                    data = yaml.load(file,yaml.Loader)
                    
                    return render(request,"Lab/A9/a9_lab.html",{"data":data})
```

**触发条件**

Source-confirmed: authenticated session required; the view is @csrf_exempt. Deployment-dependent: the pinned PyYAML version (requirements.txt: PyYAML==5.1) supports the !!python/object tags used for exploitation.

**数据流**

request.FILES['file'] -> yaml.load(file, yaml.Loader) at introduction/views.py:560 -> parsed object rendered in Lab/A9/a9_lab.html.

**修复方向**

禁止反序列化不可信数据：改用 JSON 等无代码执行能力的数据格式；如必须使用 pickle/YAML，则使用 `yaml.safe_load`、带 HMAC 的签名数据或隔离的签名验证。

### finding-010 — introduction/views.py:926（CWE-22，high，置信度 high）

**问题说明 / 根因与安全影响**

Path traversal / arbitrary file read: the POST parameter 'blog' is joined onto the application directory and opened without any normalisation or containment check. Values like '../../../../etc/passwd' or '../templates/Lab/A10/debug.log' let an authenticated user read arbitrary files readable by the web process, and the content is echoed back in the response.

**代码证据**

```python
            file=request.POST["blog"]
            try :
                dirname = os.path.dirname(__file__)
                filename = os.path.join(dirname, file)
                file = open(filename,"r")
                data = file.read()
                return render(request,"Lab/ssrf/ssrf_lab.html",{"blog":data})
```

**触发条件**

Source-confirmed: authenticated session required. Deployment-dependent: the readable file set depends on the process permissions and the working directory of the deployed application.

**数据流**

request.POST['blog'] -> os.path.join(dirname, file) at introduction/views.py:926 -> open(filename,'r') at introduction/views.py:927 -> file content rendered in Lab/ssrf/ssrf_lab.html.

**修复方向**

对用户输入做规范化并用 `os.path.realpath` + 前缀校验限制在允许目录内；使用 `safe_join` 之类的安全拼接函数。

### finding-011 — introduction/views.py:963（CWE-918，high，置信度 high）

**问题说明 / 根因与安全影响**

Server-Side Request Forgery: the POST parameter 'url' is fetched by the server with requests.get(url) without any scheme/host allow-list or private-IP filtering. An authenticated user can make the server issue requests to internal services (e.g. http://127.0.0.1:8000/admin/, cloud metadata endpoints) and read the response body back in the page.

**代码证据**

```python
    elif request.method == "POST":
        url = request.POST["url"]
        try:
            response = requests.get(url)
            return render(request, "Lab/ssrf/ssrf_lab2.html", {"response": response.content.decode()})
```

**触发条件**

Source-confirmed: authenticated session required (@authentication_decorator). Deployment-dependent: outbound network access from the app process and reachability of the internal targets determine the impact.

**数据流**

request.POST['url'] -> requests.get(url) at introduction/views.py:963 -> response.content rendered in Lab/ssrf/ssrf_lab2.html (marked |safe, see the XSS finding for that sink).

**修复方向**

对出站请求做 URL 白名单/协议与主机校验，解析 DNS 后拒绝内网、回环与元数据地址，并禁用重定向跟随到私网地址。

### finding-013 — introduction/views.py:984（CWE-1336，high，置信度 high）

**问题说明 / 根因与安全影响**

Server-Side Template Injection: the POST parameter 'blog' is passed through filter_blog(), which returns the input unchanged (introduction/utility.py:55-56), concatenated into a Django template source and written to a template file that is later rendered by the server. The attacker controls Django template syntax (e.g. {% debug %} or object/method traversal such as {{ request.META }}) leading to information disclosure of settings/context and potentially further code execution depending on the available template tags and filters.

**代码证据**

```python
            blog = request.POST["blog"]
            id = str(uuid.uuid4()).split('-')[-1]

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
```

**触发条件**

Source-confirmed: authenticated session required. Deployment-dependent: the exact impact depends on the template tags/filters and the request context available in the deployment.

**数据流**

request.POST['blog'] -> filter_blog(blog) (identity function) at introduction/views.py:984 -> template source concatenation at introduction/views.py:990 -> open(filename,'w+')/file.write(blog) at introduction/views.py:995-996 -> later rendered by ssti_view_blog (introduction/views.py:1003).

**修复方向**

不要把用户输入当作模板源码；用 `Template(user_string).render(...)` 并关闭自动转义，或对用户内容严格转义后再拼入模板。

### finding-014 — introduction/apis.py:70（CWE-94，high，置信度 medium）

**问题说明 / 根因与安全影响**

Unauthenticated arbitrary Python source injection: the POST parameters 'log_code' and 'api_code' are written verbatim into the application's own modules introduction/playground/A9/main.py and introduction/playground/A9/api.py. These files are imported by the running application (introduction/urls.py imports log_function_target from that package), so the planted code is imported and executed as soon as the module is (re)loaded - the shipped docker-compose/Dockerfile run gunicorn, while the development server reloads on source change. The authentication decorator is commented out, so any client can plant code.

**代码证据**

```python
        dirname = os.path.dirname(__file__)
        log_filename = os.path.join(dirname, "playground/A9/main.py")
        api_filename = os.path.join(dirname, "playground/A9/api.py")
        f = open(log_filename,"w")
        f.write(log_code)
        f.close()
        f = open(api_filename,"w")
        f.write(api_code)
        f.close()
```

**触发条件**

Source-confirmed: the decorator is commented out in the source ('# @authentication_decorator') and the view is @csrf_exempt; the write targets are fixed application source files. Deployment-dependent: in-process execution of the planted code requires a module reload (development server auto-reload or a process restart); without it the confirmed impact is arbitrary modification of application source code.

**数据流**

request.POST['log_code'] / request.POST['api_code'] -> f.write(log_code) at introduction/apis.py:70 and f.write(api_code) at introduction/apis.py:73 -> introduction/playground/A9/main.py and introduction/playground/A9/api.py -> imported by introduction/urls.py (from introduction.playground.A9.api import log_function_target).

**修复方向**

禁止把请求参数写入可执行源码文件；如需“代码练习”功能，应在受限沙箱/子进程中执行用户代码，且不得写入应用自身的模块路径。

### finding-015 — introduction/apis.py:134（CWE-94，high，置信度 medium）

**问题说明 / 根因与安全影响**

Unauthenticated arbitrary Python source injection: the POST parameter 'code' is written verbatim into introduction/playground/A6/utility.py, a module that the application imports (introduction/apis.py: 'from introduction.playground.A6.utility import check_vuln'). There is no authentication check and no CSRF protection, so any client can overwrite application source code with attacker-controlled Python that will be executed when the module is (re)loaded.

**代码证据**

```python
    try:
        code = request.POST.get('code')
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, "playground/A6/utility.py")
        f = open(filename,"w")
        f.write(code)
        f.close()
```

**触发条件**

Source-confirmed: no authentication decorator and @csrf_exempt on the view; the write target is fixed. Deployment-dependent: execution of the injected code requires a module reload/restart of the process; until then the confirmed impact is arbitrary modification of application source.

**数据流**

request.POST['code'] -> f.write(code) at introduction/apis.py:134 -> introduction/playground/A6/utility.py -> imported by introduction/apis.py (from introduction.playground.A6.utility import check_vuln).

**修复方向**

禁止把请求参数写入可执行源码文件；如需“代码练习”功能，应在受限沙箱/子进程中执行用户代码，且不得写入应用自身的模块路径。

### finding-016 — introduction/utility.py:36（CWE-94，high，置信度 medium）

**问题说明 / 根因与安全影响**

Arbitrary Python source injection through the SSRF playground: ssrf_code_converter() writes the user supplied 'python_code' (transformed only by indentation handling) into introduction/playground/ssrf/main.py, and introduction/apis.py:38 then calls main.ssrf_lab(...) on that module. The file is therefore attacker-controlled application source code; it is executed whenever the module is (re)loaded.

**代码证据**

```python
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, "playground/ssrf/main.py")
    f = open(filename,"w")
    f.write(output_Code)
    f.close()
```

**触发条件**

Source-confirmed: the converter writes attacker code to a fixed application module path without any sanitisation of the code content. Deployment-dependent: whether the overwritten file is executed in-process depends on module reloading (development server auto-reload or restart); the write itself is unconditional.

**数据流**

request.POST['python_code'] -> ssrf_code_converter(python_code) at introduction/apis.py:32 -> f.write(output_Code) at introduction/utility.py:36 -> introduction/playground/ssrf/main.py -> imported as 'from introduction.playground.ssrf import main' (introduction/apis.py) and invoked at introduction/apis.py:38.

**修复方向**

禁止把请求参数写入可执行源码文件；如需“代码练习”功能，应在受限沙箱/子进程中执行用户代码，且不得写入应用自身的模块路径。

### finding-017 — introduction/views.py:259（CWE-611，high，置信度 high）

**问题说明 / 根因与安全影响**

XML External Entity (XXE) injection: the XML parser is created with external general entities explicitly enabled (parser.setFeature(feature_external_ges, True)) and parses the raw request body. An attacker can define an external entity pointing at local files (e.g. file:///etc/passwd) or internal hosts, and the resolved content is written into the comments table and rendered back.

**代码证据**

```python
@csrf_exempt
def xxe_parse(request):

    parser = make_parser()
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

**触发条件**

Source-confirmed: the feature is enabled in the source and the parsed body is attacker controlled. Deployment-dependent: the endpoint is @csrf_exempt but still requires an authenticated session; the read set depends on process permissions.

**数据流**

request.body -> parseString(request.body.decode('utf-8'), parser=parser) at introduction/views.py:260 with external entity support enabled at introduction/views.py:259 -> doc.expandNode(node) at introduction/views.py:263 -> text stored via comments.objects.filter(id=1).update(comment=text) and displayed by xxe_see.

**修复方向**

使用 `defusedxml` 或禁用外部实体（`feature_external_ges = False`、禁用 DTD），并限制解析器访问本地文件与网络。

### finding-018 — introduction/views.py:347（CWE-602，high，置信度 high）

**问题说明 / 根因与安全影响**

Broken access control: the administrator decision in the broken-access lab is taken from a client supplied cookie ('admin' == '1'). Any user can simply set the cookie admin=1 in the browser and receive the administrator secret key, without any server side credential check.

**代码证据**

```python
@csrf_exempt
def ba_lab(request):
    if request.user.is_authenticated:
        name = request.POST.get('name')
        password = request.POST.get('pass')
        if name:
            if request.COOKIES.get('admin') == "1":
                return render(
                    request, 
                    'Lab/BrokenAccess/ba_lab.html', 
                    {
                        "data":"0NLY_F0R_4DM1N5",
                        "username": "admin"
                    })
```

**触发条件**

Source-confirmed: the cookie value is read directly from the request and used as the authorization decision; the surrounding view is @csrf_exempt. No deployment condition.

**数据流**

request.COOKIES['admin'] -> equality check at introduction/views.py:347 -> render of the admin secret '0NLY_F0R_4DM1N5' in Lab/BrokenAccess/ba_lab.html.

**修复方向**

授权判断必须在服务端基于会话/数据库状态完成，禁止使用客户端可伪造的 Cookie、User-Agent 等请求数据作为权限依据。

### finding-019 — introduction/views.py:758（CWE-602，high，置信度 high）

**问题说明 / 根因与安全影响**

Broken access control (2021 A1 lab): the administrator secret is returned whenever the client sends the cookie admin=1, i.e. the access-control decision is entirely client side and trivially forgeable.

**代码证据**

```python
    print(password)
    print(name)
    if name:
        if request.COOKIES.get('admin') == "1":
            return render(
                request, 
                'Lab_2021/A1_BrokenAccessControl/broken_access_lab_1.html', 
                {
                    "data":"0NLY_F0R_4DM1N5",
                    "username": "admin"
                })
        elif (name=='jack' and password=='jacktheripper'): # Will implement hashing here
            html = render(
            request, 
```

**触发条件**

Source-confirmed: client supplied cookie used as the only authorization check. No deployment condition.

**数据流**

request.COOKIES['admin'] -> equality check at introduction/views.py:758 -> render of the admin secret '0NLY_F0R_4DM1N5' in Lab_2021/A1_BrokenAccessControl/broken_access_lab_1.html.

**修复方向**

授权判断必须在服务端基于会话/数据库状态完成，禁止使用客户端可伪造的 Cookie、User-Agent 等请求数据作为权限依据。

### finding-020 — introduction/views.py:791（CWE-807，high，置信度 high）

**问题说明 / 根因与安全影响**

Broken access control based on a spoofable client header: the 2021 A1 lab grants administrator access (secret key) whenever the User-Agent header equals 'pygoat_admin'. The header is fully controlled by the client, so any authenticated user can become 'admin'.

**代码证据**

```python
    name = request.POST.get('name')
    password = request.POST.get('pass')
    user_agent = request.META['HTTP_USER_AGENT']

    # print(name)
    # print(password)
    print(user_agent)
    if name :  
        if (user_agent == "pygoat_admin"):
            return render(
                request, 
                'Lab_2021/A1_BrokenAccessControl/broken_access_lab_2.html', 
```

**触发条件**

Source-confirmed: request header read directly from the request and used as the authorization decision. No deployment condition.

**数据流**

request.META['HTTP_USER_AGENT'] -> comparison at introduction/views.py:792 -> render of the admin secret in Lab_2021/A1_BrokenAccessControl/broken_access_lab_2.html.

**修复方向**

不要把客户端可控的请求头（X-Host、User-Agent、X-Forwarded-For 等）当作可信身份或来源依据；如需信任代理头，必须配置可信代理列表。

### finding-021 — introduction/templates/Lab/XSS/xss_lab.html:27（CWE-79，high，置信度 high）

**问题说明 / 根因与安全影响**

Reflected cross-site scripting: the 'q' query parameter is rendered with the |safe filter, which disables Django's HTML autoescaping. A crafted URL such as /xssL?q=<script>alert(1)</script> executes attacker JavaScript in the victim's browser (session/token theft, actions on behalf of the victim).

**代码证据**

```python
    <h3> The company '{{query|safe}}' You searched for is not Part of FAANG</h3>
```

**触发条件**

Source-confirmed: the view passes the raw GET parameter into the template as 'query' (introduction/views.py:101) and the template disables escaping. Deployment-dependent: the payload is only reflected when the query does not match an existing FAANG company (otherwise a different branch is taken).

**数据流**

request.GET['q'] -> introduction/views.py:95-101 -> context {'query': q} -> {{query|safe}} in introduction/templates/Lab/XSS/xss_lab.html:27.

**修复方向**

移除 `|safe`（或 `{% autoescape off %}`），依赖 Django 默认自动转义；如需输出富文本，使用白名单净化库。

### finding-022 — introduction/templates/Lab/XSS/xss_lab_2.html:20（CWE-79，high，置信度 high）

**问题说明 / 根因与安全影响**

Reflected cross-site scripting: the POST parameter 'username' is only cleaned by removing the literal strings '<script>' and '</script>' and is then rendered with the |safe filter. The blacklist is trivially bypassed with any other HTML/JavaScript vector (e.g. '<img src=x onerror=alert(1)>'), producing script execution in the victim's browser.

**代码证据**

```python
<p>Hello, {{ username|safe }}</p>
```

**触发条件**

Source-confirmed: view code (introduction/views.py:109-118) and template rendering with |safe. No deployment condition.

**数据流**

request.POST['username'] -> introduction/views.py:109-112 (string replace blacklist) -> context {'username': username} -> {{ username|safe }} in introduction/templates/Lab/XSS/xss_lab_2.html:20.

**修复方向**

移除 `|safe`（或 `{% autoescape off %}`），依赖 Django 默认自动转义；如需输出富文本，使用白名单净化库。

### finding-026 — introduction/mitre.py:169（CWE-321，high，置信度 high）

**问题说明 / 根因与安全影响**

Hard-coded JWT signing secret: the MITRE CSRF lab signs and verifies its authentication cookies with the literal string 'csrf_vulneribility'. The secret is public in the source, so an attacker can forge a valid auth_cookiee token for any username and then call the money transfer endpoint of the lab for arbitrary accounts.

**代码证据**

```python
            cookie = jwt.encode(payload, 'csrf_vulneribility', algorithm='HS256')
            response = redirect("/mitre/9/lab/transaction")
            response.set_cookie('auth_cookiee', cookie)
```

**触发条件**

Source-confirmed: the constant is used in jwt.encode (line 169) and jwt.decode (lines 182, 194). Deployment-dependent: the lab endpoints must be exposed.

**数据流**

known secret 'csrf_vulneribility' -> jwt.encode({'username':'victim','exp':...}) -> auth_cookiee cookie -> csrf_transfer_monei_api (introduction/mitre.py:191-208) -> jwt.decode(cookie, 'csrf_vulneribility') at introduction/mitre.py:194 -> balance transfer between accounts.

**修复方向**

从环境变量/密钥管理系统读取随机生成的密钥，禁止硬编码；对密钥做轮换并避免提交到版本库。

### finding-027 — introduction/views.py:1053（CWE-345，high，置信度 high）

**问题说明 / 根因与安全影响**

Unsigned client-side session cookie drives an authorization decision: the crypto-failure lab reads a 'cookie' value of the form '<username>|<expiry>' straight from the request and decides administrator status from the username part ('admin'), with no signature, MAC or server-side session record. An attacker can set cookie='admin|2999-01-01 00:00:00' and be treated as administrator.

**代码证据**

```python
            try :
                cookie = request.COOKIES["cookie"]
                print(cookie)
                expire = cookie.split('|')[1]
                expire = datetime.datetime.fromisoformat(expire)
                now = datetime.datetime.now()
                if now > expire :
                    return render(request,"Lab_2021/A2_Crypto_failur/crypto_failure_lab3.html",{"success":False,"failure":False})
                elif cookie.split('|')[0] == 'admin':
                    return render(request,"Lab_2021/A2_Crypto_failur/crypto_failure_lab3.html",{"success":True,"failure":False,"admin":True})
                else:
```

**触发条件**

Source-confirmed: the value is only parsed and compared; nothing signs it. No deployment condition.

**数据流**

request.COOKIES['cookie'] -> split/parse at introduction/views.py:1055-1056 -> comparison cookie.split('|')[0] == 'admin' at introduction/views.py:1060 -> admin view rendered.

**修复方向**

对会话/权限数据使用服务端签名（HMAC）或服务端会话存储，并校验完整性与有效期，禁止直接信任客户端提供的身份字段。

### finding-031 — introduction/views.py:287（CWE-256，high，置信度 high）

**问题说明 / 根因与安全影响**

Plain-text storage of user passwords: the registration endpoint of the AUTH lab stores the submitted password verbatim in the authLogin table and the login endpoint compares it verbatim, so the database contains clear-text credentials (which are also exposed through the SQL injection findings).

**代码证据**

```python
        try:
            name = request.POST['name']
            user_name = request.POST['username']
            passwd  = request.POST['pass']
            obj = authLogin.objects.create(name=name,username=user_name,password=passwd)
            try:
```

**触发条件**

Source-confirmed: authLogin.objects.create(name=name, username=user_name, password=passwd) with passwd taken unmodified from the POST body, and the model field is a plain CharField (introduction/models.py:31). No deployment condition.

**数据流**

request.POST['pass'] -> authLogin.objects.create(..., password=passwd) at introduction/views.py:287 -> stored clear-text in introduction_authlogin table -> compared at introduction/views.py:311.

**修复方向**

以单向带盐哈希（argon2/bcrypt/PBKDF2）存储口令，不得明文落库；比较时使用哈希验证函数。

### finding-034 — pygoat/settings.py:25（CWE-798，high，置信度 high）

**问题说明 / 根因与安全影响**

Hard-coded Django SECRET_KEY committed to the repository: the value is a fixed literal used to sign sessions, password-reset tokens and other cryptographic material. Anyone with access to the source (it is public) can forge signed cookies and reset tokens.

**代码证据**

```python
SECRET_KEY = 'lr66%-a!$km5ed@n5ug!tya5bv!0(yqwa1tn!q%0%3m2nh%oml'
```

**触发条件**

Source-confirmed: literal assignment in pygoat/settings.py; no environment variable override is provided in the file. Deployment-dependent: impact requires that the deployment keeps this key (the shipped Dockerfile/docker-compose do).

**数据流**

known SECRET_KEY -> forge Django session cookies / signed values -> act as any account (including staff/admin) in the deployment.

**修复方向**

把密钥/口令改为环境变量或密钥管理服务注入，禁止在源码中硬编码。

### finding-035 — introduction/views.py:514（CWE-287，high，置信度 high）

**问题说明 / 根因与安全影响**

Authentication bypass in the OTP login: the POST verification accepts the administrator record whenever its stored OTP matches, independently of the e-mail address in the cookie ('or otp.objects.filter(id=2,otp=otpR)'). The administrator OTP is a three digit number, so it can be guessed within a few hundred requests and the attacker is then logged in as the administrator.

**代码证据**

```python
    else:
        otpR=request.POST.get("otp")
        email=request.COOKIES.get("email")
        if otp.objects.filter(email=email,otp=otpR) or otp.objects.filter(id=2,otp=otpR):
            # return HttpResponse("<h3>Login Success for email:::"+email+"</h3>")
            return render (request,"Lab/BrokenAuth/otp.html",{"email":email})
        else:
            return render (request,"Lab/BrokenAuth/otp.html",{"otp":"Invalid OTP Please Try Again"})
```

**触发条件**

Source-confirmed: the second disjunct matches the fixed administrator row without comparing the e-mail, and no rate limiting/lockout exists on the endpoint (it is @csrf_exempt and requires no session). Deployment-dependent: the administrator OTP row (id=2) must exist in the database, which the lab data provides.

**数据流**

request.POST['otp'] + request.COOKIES['email'] -> boolean check at introduction/views.py:514 -> 'Login Success as user' page rendered for the attacker without proving ownership of the administrator mailbox.

**修复方向**

为每个账户单独校验验证码/OTP，并校验其归属的账户；增加失败次数限制、锁定与过期时间。

### finding-037 — introduction/mitre.py:191（CWE-352，high，置信度 high）

**问题说明 / 根因与安全影响**

State changing operation without CSRF protection: the money transfer endpoint performs the balance change on a plain GET request and the authentication decorator is commented out ('# @authentication_decorator'), so a third-party site can make an authenticated victim's browser trigger the transfer (the cookie auth_cookiee is attached automatically), and no CSRF token is validated.

**代码证据**

```python
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
```

**触发条件**

Source-confirmed: GET-based state change, no CSRF token check, no authentication decorator in the source. Deployment-dependent: the victim must have a valid auth_cookiee cookie, and the hard-coded JWT secret (finding-026) also allows forging that cookie directly.

**数据流**

cross-site GET request to /mitre/9/lab/api/<recipent>/<amount> with the victim's auth_cookiee cookie -> jwt.decode at introduction/mitre.py:194 -> recipent.balance += amount / User[0].balance -= amount (introduction/mitre.py:203-207).

**修复方向**

对所有状态变更请求启用 CSRF 保护（`{% csrf_token %}` + `CsrfViewMiddleware`），不要用 GET 执行状态变更，并移除不必要的 `@csrf_exempt`。

### finding-039 — dockerized_labs/sensitive_data_exposure/dataexposure/views.py:112（CWE-306，high，置信度 high）

**问题说明 / 根因与安全影响**

Missing authentication on a sensitive data endpoint: the view exposes the credit card number, social security number and API key of every registered user as JSON without any authentication or authorization check (the code comments state this explicitly). Any unauthenticated client can harvest all users' personal data and API keys.

**代码证据**

```python
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

**触发条件**

Source-confirmed: the view has no @login_required and performs no permission check before serialising UserData.objects.all(). Deployment-dependent: the lab container must be reachable (docker-compose exposes port 8000).

**数据流**

unauthenticated GET to the all-users endpoint -> dataexposure/views.py:112-132 -> UserData.objects.all() -> JsonResponse with username, credit_card, ssn and api_key of every user.

**修复方向**

为数据导出接口添加认证与授权检查（`@login_required` + 角色检查），并按最小化原则返回字段。

### finding-041 — dockerized_labs/broken_auth_lab/app.py:111（CWE-565，high，置信度 high）

**问题说明 / 根因与安全影响**

Forgable session token: the session cookie is only base64(username:timestamp) with no signature, HMAC or server-side state, so an attacker can craft base64('admin:<any timestamp>') and is accepted as the administrator account with access to the dashboard and the admin e-mail.

**代码证据**

```python
    
    try:
        # Vulnerable: Insecure session validation
        username = base64.b64decode(session_token).decode().split(':')[0]
        if username in users:
            return render_template('dashboard.html', 
                                username=username, 
                                role=users[username]['role'],
                                email=users[username]['email'])
    except:
        pass
```

**触发条件**

Source-confirmed: the dashboard only decodes the cookie and takes the username part; no integrity check exists. Deployment-dependent: the lab container must be reachable (port 5000).

**数据流**

attacker crafted cookie 'session' = base64('admin:2024-01-01 00:00:00') -> app.py:111 username = base64.b64decode(session_token).decode().split(':')[0] -> users[username]['role'] used to render the dashboard.

**修复方向**

会话标识必须由服务端生成并保存/签名，使用不可预测的随机值，禁止使用可伪造的明文编码。

### finding-042 — dockerized_labs/broken_auth_lab/app.py:86（CWE-330，high，置信度 high）

**问题说明 / 根因与安全影响**

Weak password reset mechanism: the reset token is md5(email:timestamp), i.e. derived from public data with second precision and no random component, and the token is disclosed directly in the HTTP response ('Password reset link: /reset/<token>') to whoever requested the reset for that e-mail address. An attacker can therefore request a reset for another user's e-mail address and immediately obtain the token to take over that account.

**代码证据**

```python
    email = request.form.get('email')
    
    # Vulnerable: Password reset token generation
    for username, user_data in users.items():
        if user_data['email'] == email:
            # Vulnerable: Predictable token generation
            token = hashlib.md5(f"{email}:{datetime.now()}".encode()).hexdigest()
            password_reset_tokens[token] = username
            
            # In a real application, this would send an email
            # Vulnerable: Token exposed in response
            flash(f'Password reset link: /reset/{token}')
            return redirect(url_for('lab'))
    
    flash('Email not found')
    return redirect(url_for('lab'))
```

**触发条件**

Source-confirmed: token generation at app.py:86 and disclosure in the flashed message at app.py:90. Deployment-dependent: the target account's e-mail must be known (the lab stores them in the users dictionary).

**数据流**

POST /reset-password with the victim's e-mail -> token = hashlib.md5(f'{email}:{datetime.now()}').hexdigest() at app.py:86 -> flash(f'Password reset link: /reset/{token}') at app.py:90 -> GET /reset/<token> renders the reset form.

**修复方向**

使用 `secrets`/`os.urandom` 生成足够长度的随机值，覆盖整个取值空间，避免依赖可枚举的小数值空间。

### finding-043 — dockerized_labs/broken_auth_lab/app.py:8（CWE-798，high，置信度 high）

**问题说明 / 根因与安全影响**

Hard-coded Flask session secret: app.secret_key is the literal 'your-secret-key-here'. All Flask session cookies are signed with this publicly known value, so an attacker can forge arbitrary session cookies (including admin sessions) for this application.

**代码证据**

```python
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Vulnerable: Hardcoded secret key
```

**触发条件**

Source-confirmed: literal assignment in the source; the Dockerfile/docker-compose start the app with this file unmodified. Deployment-dependent: the lab container must be reachable.

**数据流**

known secret 'your-secret-key-here' -> forge Flask session cookie -> authenticated access to the lab without knowing the credentials.

**修复方向**

把密钥/口令改为环境变量或密钥管理服务注入，禁止在源码中硬编码。

### finding-023 — introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html:11（CWE-79，medium，置信度 high）

**问题说明 / 根因与安全影响**

Reflected cross-site scripting: the GET parameter 'username' is echoed into the page with the |safe filter, so a link such as /2021/A8/lab2?username=<script>alert(1)</script> runs attacker script in the victim's browser.

**代码证据**

```python
<h1>Hey {{username | safe}},</h1>
```

**触发条件**

Source-confirmed: the view passes request.GET['username'] unchanged into the template (introduction/views.py:1223-1224) and the template disables escaping. No deployment condition.

**数据流**

request.GET['username'] -> software_and_data_integrity_failure_lab2 at introduction/views.py:1162-1166 -> {{username | safe }} in introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html:11.

**修复方向**

移除 `|safe`（或 `{% autoescape off %}`），依赖 Django 默认自动转义；如需输出富文本，使用白名单净化库。

### finding-024 — introduction/templates/Lab/ssrf/ssrf_lab2.html:23（CWE-79，medium，置信度 high）

**问题说明 / 根因与安全影响**

Cross-site scripting through the SSRF response: the body of the server-side fetched URL is rendered with the |safe filter. If the target response contains HTML/JavaScript (or the attacker points the URL at a page they control), the content is injected unescaped into the page and executed in the victim's browser.

**代码证据**

```python
        <div style="width:70%;overflow:scroll;background-color:#000">{{response | safe}}<div>
```

**触发条件**

Source-confirmed: introduction/views.py:963-964 places the fetched content into the 'response' context variable and the template renders it with |safe. Deployment-dependent: the payload requires the fetched response to contain attacker chosen markup.

**数据流**

request.POST['url'] -> requests.get(url) at introduction/views.py:963 -> context {'response': ...} -> {{response | safe }} in introduction/templates/Lab/ssrf/ssrf_lab2.html:23.

**修复方向**

移除 `|safe`（或 `{% autoescape off %}`），依赖 Django 默认自动转义；如需输出富文本，使用白名单净化库。

### finding-028 — introduction/views.py:1026（CWE-328，medium，置信度 high）

**问题说明 / 根因与安全影响**

Use of a broken hash algorithm for password storage: the crypto-failure lab stores and compares passwords using unsalted MD5. MD5 is fast and collision-prone, so the stored hashes are trivially brute-forced or rainbow-tabled, and identical passwords produce identical hashes.

**代码证据**

```python
            password = request.POST["password"]
            try:
                password = md5(password.encode()).hexdigest()
                user = CF_user.objects.filter(username=username,password=password).first()
```

**触发条件**

Source-confirmed: md5(password.encode()).hexdigest() is stored/compared against the CF_user table. No deployment condition beyond the lab being reachable.

**数据流**

request.POST['password'] -> md5(password.encode()).hexdigest() at introduction/views.py:1026 -> CF_user.objects.filter(username=username, password=password) -> login success/failure decision.

**修复方向**

改用 Argon2/bcrypt/PBKDF2 等带盐的慢哈希（项目已依赖 argon2-cffi），或按 OWASP 口令存储建议处理。

### finding-029 — introduction/views.py:1042（CWE-916，medium，置信度 high）

**问题说明 / 根因与安全影响**

Password hashing without a salt: customHash() (introduction/utility.py:58-59) computes sha256(password) and reverses the hex digest; no per-user random salt and no work factor are used. Identical passwords yield identical hashes and the value is fast to brute force, so a leaked CF_user table can be cracked at high speed.

**代码证据**

```python
            password = request.POST["password"]
            try:
                password = customHash(password)
                user = CF_user.objects.filter(username=username,password2=password).first()
```

**触发条件**

Source-confirmed: the implementation of customHash is visible in introduction/utility.py and is used directly for the stored password comparison. No deployment condition.

**数据流**

request.POST['password'] -> customHash(password) at introduction/views.py:1042 (sha256 of the raw password, no salt) -> CF_user.objects.filter(username=username, password2=password).

**修复方向**

为每个用户生成随机盐并使用带盐的慢哈希（argon2/bcrypt/PBKDF2）存储口令。

### finding-030 — introduction/mitre.py:161（CWE-328，medium，置信度 high）

**问题说明 / 根因与安全影响**

Broken hash algorithm for password verification in the MITRE CSRF lab: the login password is hashed with unsalted MD5 before being compared against the stored value, so the lab's password table provides no protection against offline cracking.

**代码证据**

```python
        password = request.POST.get('password')
        username = request.POST.get('username')
        password = md5(password.encode()).hexdigest()
        User = CSRF_user_tbl.objects.filter(username=username, password=password)
        if User:
```

**触发条件**

Source-confirmed: md5(password.encode()).hexdigest() at introduction/mitre.py:161 compared with CSRF_user_tbl.password. No deployment condition.

**数据流**

request.POST['password'] -> md5(password.encode()).hexdigest() at introduction/mitre.py:161 -> CSRF_user_tbl.objects.filter(username=username, password=password).

**修复方向**

改用 Argon2/bcrypt/PBKDF2 等带盐的慢哈希（项目已依赖 argon2-cffi），或按 OWASP 口令存储建议处理。

### finding-032 — introduction/models.py:23（CWE-256，medium，置信度 high）

**问题说明 / 根因与安全影响**

Plain-text password storage in the shared login table: the 'login' model keeps the password as a raw character field, and the SQL lab, broken-access lab and A10 lab all compare submitted passwords against it in clear text. A database dump therefore yields usable credentials directly.

**代码证据**

```python
class login(models.Model):
    id = models.AutoField(primary_key=True)
    user=models.CharField(max_length=200)
    password=models.CharField(max_length=300)
```

**触发条件**

Source-confirmed: model definition introduction/models.py:23 plus the clear-text comparisons in introduction/views.py (e.g. login.objects.filter(user=name,password=password) at line 355 and 666). No deployment condition.

**数据流**

request.POST['pass'] -> login.objects.filter(user=..., password=...) (introduction/views.py:355, 628, 666) -> clear-text column introduction_login.password.

**修复方向**

以单向带盐哈希（argon2/bcrypt/PBKDF2）存储口令，不得明文落库；比较时使用哈希验证函数。

### finding-033 — pygoat/settings.py:30（CWE-489，medium，置信度 high）

**问题说明 / 根因与安全影响**

Debug mode is enabled in the shipped settings: with DEBUG=True Django exposes detailed error pages including stack traces, source snippets, local variables and settings (including the SECRET_KEY and database configuration) to every client, which greatly speeds up exploitation of other defects. The deployed Dockerfile/docker-compose run the application with exactly these settings.

**代码证据**

```python
DEBUG = True
```

**触发条件**

Source-confirmed: DEBUG = True in pygoat/settings.py and no environment override exists in the file. Deployment-dependent: the deployment must use the shipped settings module (the shipped Dockerfile and docker-compose.yml do).

**数据流**

any request that triggers an unhandled exception -> Django technical error page -> disclosure of settings, stack traces and source code.

**修复方向**

生产环境设置 `DEBUG = False`（并配置 `ALLOWED_HOSTS`），关闭 Flask 调试器/交互式控制台。

### finding-036 — introduction/views.py:496（CWE-330，medium，置信度 high）

**问题说明 / 根因与安全影响**

Predictable one-time password: the OTP is a three digit number generated with random.randint(100,999), i.e. only 900 possible values, is transmitted to the client in the response body (introduction/views.py:506) and is never invalidated after use or rate limited.

**代码证据**

```python
    if request.method=="GET":
        email=request.GET.get('email')
        otpN=randint(100,999)
        if email and otpN:
            if email=="admin@pygoat.com":
                otp.objects.filter(id=2).update(otp=otpN)
                html = render(request, "Lab/BrokenAuth/otp.html", {"otp":"Sent To Admin Mail ID"})
                html.set_cookie("email", email)
                return html

            else:
                otp.objects.filter(id=1).update(email=email, otp=otpN)
                html=render (request,"Lab/BrokenAuth/otp.html",{"otp":otpN})
                html.set_cookie("email",email)
                return html
```

**触发条件**

Source-confirmed: generation at introduction/views.py:496 and disclosure in the same response at line 506. No deployment condition.

**数据流**

GET /otp?email=... -> otpN=randint(100,999) -> rendered in Lab/BrokenAuth/otp.html -> brute force of at most 900 values against /otp POST.

**修复方向**

使用 `secrets`/`os.urandom` 生成足够长度的随机值，覆盖整个取值空间，避免依赖可枚举的小数值空间。

### finding-038 — introduction/views.py:943（CWE-290，medium，置信度 high）

**问题说明 / 根因与安全影响**

Access control based on a spoofable request header: the ssrf_target view decides whether the caller is 'local' by inspecting the X-Forwarded-For header, which any client can set, so the intended restriction (only loopback clients may access the target page) can be bypassed by sending a forged header.

**代码证据**

```python
def ssrf_target(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    if ip == '127.0.0.1':
        return render(request,"Lab/ssrf/ssrf_target.html")
    else:
        return render(request,"Lab/ssrf/ssrf_target.html",{"access_denied":True})
```

**触发条件**

Source-confirmed: the header value is trusted without validation and used for the authorization decision. Deployment-dependent: whether the deployment strips/normalises X-Forwarded-For (no trusted-proxy configuration is present in the settings).

**数据流**

request header X-Forwarded-For: 127.0.0.1 -> introduction/views.py:943-948 -> ip == '127.0.0.1' check at introduction/views.py:950 -> access to Lab/ssrf/ssrf_target.html.

**修复方向**

访问控制不得基于可伪造的请求头；使用可信代理配置或真实连接地址。

### finding-040 — dockerized_labs/sensitive_data_exposure/dataexposure/views.py:87（CWE-200，medium，置信度 high）

**问题说明 / 根因与安全影响**

Exposure of sensitive personal data through an API: the /api data endpoint returns the full credit card number, SSN and the API key of the authenticated user in clear text (the code itself is marked as insecure), so any script or browser extension able to issue the request obtains reusable secrets.

**代码证据**

```python
def api_data_view(request):
    # FIXME: this is insecure AF - just for demo purposes!!
    # sends all user data as json - bad practice!!
    try:
        user_data = UserData.objects.get(user=request.user)
    except UserData.DoesNotExist:
        # If no user data exists, create some dummy data for demo
        user_data = UserData.objects.create(
            user=request.user,
            credit_card='4111111111111111',  # test card number
            ssn='123456789',  # demo SSN
            api_key=generate_api_key()  # simple api key
        )
    
    data = {
        'username': request.user.username,
        'credit_card': user_data.credit_card,
        'ssn': user_data.ssn,
        'api_key': user_data.api_key
    }
    # Intentionally exposing sensitive data through API
    # cuz we're teaching about data exposure, duh!
    return JsonResponse(data)

```

**触发条件**

Source-confirmed: the response payload contains credit_card, ssn and api_key in clear text. Deployment-dependent: requires an authenticated session in the lab.

**数据流**

authenticated request -> api_data_view at dataexposure/views.py:87-110 -> JsonResponse({'username','credit_card','ssn','api_key'}).

**修复方向**

敏感字段（信用卡号、SSN、API 密钥）默认脱敏或不返回，按需最小化暴露。

### finding-044 — dockerized_labs/broken_auth_lab/app.py:123（CWE-489，medium，置信度 high）

**问题说明 / 根因与安全影响**

The Flask development server is started with debug=True on 0.0.0.0:5000. The interactive Werkzeug debugger console is then exposed, which allows arbitrary code execution by anyone who can reach the port when an exception is triggered.

**代码证据**

```python

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # Vulnerable: Debug mode enabled in production 
```

**触发条件**

Source-confirmed: app.run(host='0.0.0.0', port=5000, debug=True) as the process entry point. Deployment-dependent: the debugger PIN is derived from machine data, but the console is exposed whenever an unhandled exception occurs.

**数据流**

any request triggering an exception in the Flask app -> Werkzeug interactive debugger with console -> arbitrary Python execution.

**修复方向**

生产环境设置 `DEBUG = False`（并配置 `ALLOWED_HOSTS`），关闭 Flask 调试器/交互式控制台。

### finding-045 — introduction/playground/A9/api.py:16（CWE-532，medium，置信度 high）

**问题说明 / 根因与安全影响**

Sensitive information written to a log file: the plaintext password submitted to the A9 logging target is written to the 'test.log' file in the working directory. Log files are frequently readable by other users or collected by log shippers, so credentials end up stored in clear text outside the credential store.

**代码证据**

```python
        username = request.POST['username']
        password = request.POST['password']
        L.info(f"POST request with username {username} and password {password}")
        if username == "admin" and password == "admin":
```

**触发条件**

Source-confirmed: L.info(f"POST request with username {username} and password {password}") writes the raw password to test.log (introduction/playground/A9/archive.py:48-50 shows the writer). Deployment-dependent: file permissions and log collection determine who can read it.

**数据流**

request.POST['password'] -> Log.info() at introduction/playground/A9/api.py:16 -> f.write(f'INFO:{now}:{msg}') to 'test.log'.

**修复方向**

禁止把口令等机密写入日志；对日志做脱敏并限制日志文件访问权限。

### finding-046 — introduction/views.py:536（CWE-807，medium，置信度 high）

**问题说明 / 根因与安全影响**

Security decision based on a client supplied header: the 'secret' view returns the secret key S3CR37K3Y to any request whose X-Host header equals 'admin.localhost:8000'. The header is entirely attacker controlled, so the protection can be bypassed trivially.

**代码证据**

```python
def secret(request):
    XHost = request.headers.get('X-Host', 'None')
    if(XHost == 'admin.localhost:8000'):
        return render(request,"Lab/sec_mis/sec_mis_lab.html", {"secret": "S3CR37K3Y"})
    else:
        return render(request,"Lab/sec_mis/sec_mis_lab.html", {"no_secret": "Only admin.localhost:8000 can access, Your X-Host is " + XHost})


#**********************************************************A9*************************************************#
```

**触发条件**

Source-confirmed: the value is read directly from request.headers and compared. No deployment condition.

**数据流**

request header 'X-Host: admin.localhost:8000' -> introduction/views.py:536-540 -> render of the secret 'S3CR37K3Y'.

**修复方向**

不要把客户端可控的请求头（X-Host、User-Agent、X-Forwarded-For 等）当作可信身份或来源依据；如需信任代理头，必须配置可信代理列表。

### finding-047 — introduction/views.py:291（CWE-614，medium，置信度 high）

**问题说明 / 根因与安全影响**

Authentication cookie issued without the Secure attribute: the session identity cookie 'userid' (and the identical cookies issued at introduction/views.py:305 and 319) is set with secure=False and samesite=None, and is valid for roughly one year (max_age=31449600). Over plain HTTP or through any SSL-stripping position the cookie, which is the only credential used by the AUTH lab login flow, is transmitted in clear text and can be replayed to impersonate the user.

**代码证据**

```python
            obj = authLogin.objects.create(name=name,username=user_name,password=passwd)
            try:
                rendered = render_to_string('Lab/AUTH/auth_success.html', {'username': obj.username,'userid':obj.userid,'name':obj.name,'err_msg':'Cookie Set'})
                response = HttpResponse(rendered)
                response.set_cookie('userid', obj.userid, max_age=31449600, samesite=None, secure=False)
                print('Setting cookie successful')
                return response
```

**触发条件**

Source-confirmed: the set_cookie() calls explicitly pass secure=False. Deployment-dependent: the impact requires the application to be reachable over plain HTTP or via a downgrade/SSL-stripping attacker.

**数据流**

login/signup -> authLogin row -> response.set_cookie('userid', obj.userid, max_age=31449600, samesite=None, secure=False) at introduction/views.py:291 -> later auth_lab_login reads request.COOKIES['userid'] (introduction/views.py:303) as the authenticated identity.

**修复方向**

认证/会话 Cookie 设置 `secure=True`、`httponly=True` 与合适的 `samesite`，并缩短有效期。

## 未覆盖范围与分析局限

- 未覆盖：`introduction/templates/` 下绝大多数 HTML 模板、`introduction/static/` 下的 CSS/JS 静态资源、全部 `introduction/migrations/*.py`、`dockerized_labs/*` 中的 Dockerfile/docker-compose/entrypoint/模板与配置脚本、`installer.sh`、`uninstaller.sh`、`gh-md-toc`、`.all-contributorsrc`、`.gitignore`、`LICENSE.md` 等。这些文件只做了关键字级检索（`|safe`/`autoescape`/用户输入变量名）或简单浏览，没有逐行通读；其中 CSS/JS 与模板中的客户端逻辑可能还存在本报告未覆盖的问题。
- 未做动态验证：所有“触发条件”均为静态推断；涉及运行期行为（如模块重载后执行被写入的代码、Pillow `ImageMath.eval` 的实际可利用性、被写入文件的执行时机）的结论已标注为部署相关条件或降低置信度。
- 未审计依赖的第三方组件本身（如 Django/PyYAML/Pillow 的内部实现），只审计了本仓库代码对这些组件的调用方式；`requirements.txt` 中的固定版本仅作为判断前提引用。
- 未审计 `challenge/challenge.json`、数据库初始数据与运行时状态，因此部分依赖预置数据（如 OTP 管理员行 `id=2`）的结论标注为部署相关条件。
- 模板上下文、自动转义行为等仅按 Django 默认语义推理，未实际渲染验证。
- 本报告不构成“仓库安全”或“已覆盖全部漏洞”的结论；未列出某处问题只代表本次静态审查未发现或未深入，不等于该处安全。
