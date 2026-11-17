# PyGoat 静态安全代码审查报告

- 实验: `01-pygoat-models-pi-agent` / 组: `B-with-extra-rules`
- 模型标签: `minimax-m3.1-flash`；运行 ID: `r01`；harness: `pi-agent`
- 审查对象: `D:/ai_share/langgraph/benchmark-data/pygoat-baseline/inputs/experiment-01/pygoat`（提交 `2fb0c600245f50670e8b9233c784afe61e8b340b`）
- 规范来源: `D:/ai_share/langgraph/benchmark-data/pygoat-baseline/inputs/experiment-01/rules-v1`（core/ 与 supplemental/ 全部 9 份文件）
- 方法: **纯静态分析**。未安装依赖、未启动应用、未执行测试或利用代码、未调用扫描器、未联网。
- 确认发现: **53** 条；未确认候选: 6 条（见 `uncertain-findings.json`）

严重度分布: critical 12，high 30，medium 11

下表为发现索引，随后逐条给出证据、触发条件、根因、影响与修复方向。

| 编号 | 文件 | 行 | CWE | 严重度 | 置信度 | 问题摘要 |
| --- | --- | --- | --- | --- | --- | --- |
| finding-001 | `introduction/views.py` | 158 | CWE-89 | critical | high | SQL injection: the SQL statement is built by concatenating the raw POST fields 'name' and 'pass' and then exec |
| finding-002 | `introduction/views.py` | 864 | CWE-89 | critical | high | SQL injection (second, independent occurrence): the 2021 injection lab builds the raw SQL statement by concate |
| finding-003 | `introduction/views.py` | 424 | CWE-78 | critical | high | OS command injection: the 'domain' POST field is only stripped of an optional scheme/www prefix and is then in |
| finding-004 | `introduction/views.py` | 460 | CWE-95 | critical | high | Arbitrary code execution via eval(): the POST field 'val' is passed directly to eval(), so any authenticated u |
| finding-005 | `introduction/mitre.py` | 215 | CWE-95 | critical | high | Unauthenticated remote code execution via eval(): the mitre_lab_25_api view is decorated with @csrf_exempt and |
| finding-006 | `introduction/mitre.py` | 238 | CWE-78 | critical | high | OS command injection in the port-scanning API: the POST field 'ip' is concatenated into the command string 'nm |
| finding-007 | `introduction/views.py` | 208 | CWE-502 | critical | high | Insecure deserialization of a client-controlled cookie: insec_des_lab reads the 'token' cookie, base64-decodes |
| finding-008 | `dockerized_labs/insec_des_lab/main.py` | 33 | CWE-502 | critical | high | Insecure deserialization in the standalone insec_des_lab Flask application: the 'serialized_data' form field i |
| finding-009 | `introduction/views.py` | 560 | CWE-502 | critical | high | Unsafe YAML deserialization of an uploaded file: a9_lab loads the uploaded file with yaml |
| finding-010 | `introduction/views.py` | 256 | CWE-611 | high | high | XML External Entity (XXE) injection: the XML parser used by xxe_parse explicitly enables external general enti |
| finding-011 | `introduction/views.py` | 984 | CWE-1336 | critical | high | Server-side template injection through template source injection: the POST field 'blog' is only passed through |
| finding-012 | `introduction/views.py` | 926 | CWE-22 | high | high | Path traversal / arbitrary file read: the POST field 'blog' is joined to the application directory with os |
| finding-013 | `introduction/views.py` | 963 | CWE-918 | high | high | Server-Side Request Forgery: the POST field 'url' is passed unchecked to requests |
| finding-014 | `introduction/templates/Lab/XSS/xss_lab.html` | 27 | CWE-79 | high | high | Reflected XSS: the 'q' query parameter is passed into the template and rendered with the \|safe filter, which d |
| finding-015 | `introduction/templates/Lab/XSS/xss_lab_2.html` | 20 | CWE-79 | high | high | Reflected XSS with an insufficient blacklist filter: the view (introduction/views |
| finding-016 | `introduction/templates/Lab/XSS/xss_lab_3.html` | 22 | CWE-79 | high | medium | XSS through a JavaScript context with an insufficient input filter: xss_lab3 removes only alphanumeric charact |
| finding-017 | `introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html` | 11 | CWE-79 | medium | high | Reflected XSS: the 'username' GET parameter is rendered with the \|safe filter in the A8 lab page |
| finding-018 | `introduction/templates/Lab/ssrf/ssrf_lab2.html` | 23 | CWE-79 | medium | high | XSS via unescaped remote content: the body fetched by the SSRF lab is rendered with the \|safe filter, so any H |
| finding-019 | `introduction/views.py` | 347 | CWE-639 | high | high | Broken access control / privilege escalation via a client-controlled cookie: ba_lab grants the admin-only secr |
| finding-020 | `introduction/views.py` | 758 | CWE-639 | high | high | Broken access control via a client-controlled cookie (second, independent occurrence): a1_broken_access_lab_1  |
| finding-021 | `introduction/views.py` | 535 | CWE-807 | high | high | Security decision based on a client-supplied HTTP header: the 'secret' view exposes the secret key S3CR37K3Y t |
| finding-022 | `introduction/views.py` | 791 | CWE-807 | high | high | Administrator impersonation via the User-Agent header: a1_broken_access_lab_2 grants the admin secret and the  |
| finding-023 | `introduction/views.py` | 943 | CWE-290 | medium | high | Access control based on a spoofable client header: ssrf_target decides whether the requester may see the restr |
| finding-024 | `introduction/views.py` | 287 | CWE-256 | high | high | Plaintext storage of user passwords: auth_lab_signup stores the submitted password verbatim in the authLogin |
| finding-025 | `introduction/views.py` | 1026 | CWE-328 | high | high | Weak password hashing: crypto_failure_lab verifies passwords with a single unsalted MD5 digest (md5(password |
| finding-026 | `introduction/mitre.py` | 159 | CWE-328 | high | high | Weak password hashing in the CSRF lab login: the submitted password is reduced to a single unsalted MD5 digest |
| finding-027 | `introduction/views.py` | 1194 | CWE-328 | high | high | Unsalted SHA-256 used for password verification: auth_failure_lab3 hashes the submitted password with a single |
| finding-028 | `introduction/mitre.py` | 169 | CWE-798 | high | high | Hardcoded JWT signing key: the CSRF lab signs and verifies its authentication cookie with the literal string ' |
| finding-029 | `introduction/mitre.py` | 191 | CWE-352 | high | high | State-changing financial operation without CSRF protection and without authentication: csrf_transfer_monei_api |
| finding-030 | `pygoat/settings.py` | 171 | CWE-321 | high | high | Hardcoded, weak JWT signing key: SECRET_COOKIE_KEY = "PYGOAT" is a literal constant committed to the repositor |
| finding-031 | `pygoat/settings.py` | 25 | CWE-798 | medium | high | Django SECRET_KEY hardcoded in the source repository: the value is a fixed literal committed to version contro |
| finding-032 | `pygoat/settings.py` | 30 | CWE-489 | high | high | DEBUG mode is enabled in the shipped settings module |
| finding-033 | `introduction/views.py` | 291 | CWE-614 | medium | high | Authentication cookie set without secure/httponly/samesite protections: the 'userid' cookie that identifies th |
| finding-034 | `introduction/views.py` | 496 | CWE-330 | high | high | One-time-password verification code disclosed in the HTTP response: the /otp GET handler renders the generated |
| finding-035 | `introduction/views.py` | 512 | CWE-287 | high | high | OTP authentication not bound to the requested account and without attempt limits: the POST branch of /otp acce |
| finding-036 | `introduction/views.py` | 679 | CWE-330 | medium | high | Predictable ticket codes generated with a non-cryptographic PRNG: gentckt() builds ticket identifiers with ran |
| finding-037 | `dockerized_labs/sensitive_data_exposure/dataexposure/views.py` | 38 | CWE-330 | medium | high | API keys generated with a non-cryptographic PRNG: generate_api_key() builds the per-user API key with random |
| finding-038 | `dockerized_labs/sensitive_data_exposure/dataexposure/views.py` | 112 | CWE-306 | critical | high | Unauthenticated endpoint discloses every user's sensitive data: all_users_data_view has no authentication or a |
| finding-039 | `dockerized_labs/sensitive_data_exposure/dataexposure/views.py` | 87 | CWE-200 | high | high | Sensitive data returned unmasked by the authenticated API: api_data_view returns the full credit card number,  |
| finding-040 | `dockerized_labs/broken_auth_lab/app.py` | 45 | CWE-345 | high | high | Forgeable session token: the 'session' cookie only contains base64(username:timestamp) and the dashboard re-de |
| finding-041 | `dockerized_labs/broken_auth_lab/app.py` | 8 | CWE-798 | medium | high | Hardcoded Flask secret key: app |
| finding-042 | `dockerized_labs/broken_auth_lab/app.py` | 11 | CWE-798 | high | high | Hardcoded administrator credentials and plaintext password storage: the in-memory user table contains the hard |
| finding-043 | `dockerized_labs/broken_auth_lab/app.py` | 86 | CWE-330 | high | high | Predictable and disclosed password-reset token: the reset token is md5(f'{email}:{datetime |
| finding-044 | `introduction/apis.py` | 61 | CWE-94 | critical | high | Unauthenticated arbitrary write of Python source files: log_function_checker (the @authentication_decorator ab |
| finding-045 | `introduction/apis.py` | 126 | CWE-94 | high | high | Arbitrary write of an imported Python module: A6_disscussion_api_2 accepts the POST field 'code' and writes it |
| finding-046 | `introduction/utility.py` | 34 | CWE-94 | high | medium | User-supplied code written into an imported Python module: ssrf_code_converter takes the POST field 'python_co |
| finding-047 | `introduction/views.py` | 583 | CWE-95 | high | medium | Expression evaluation of user-controlled input: a9_lab2 passes the POST field 'function' to PIL's ImageMath |
| finding-048 | `introduction/views.py` | 831 | CWE-798 | medium | high | Hardcoded credentials in the application source: the broken access control lab authenticates users by comparin |
| finding-049 | `introduction/views.py` | 837 | CWE-862 | medium | medium | Missing authorization on a sensitive endpoint: a1_broken_access_lab3_secret only verifies that a session exist |
| finding-050 | `dockerized_labs/broken_auth_lab/app.py` | 121 | CWE-489 | medium | high | Flask debug mode enabled and bound to all interfaces: the standalone broken-auth lab starts with app |
| finding-051 | `dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py` | 8 | CWE-489 | high | high | Insecure deployment settings in the sensitive-data lab: the Django settings module hardcodes SECRET_KEY = 'dja |
| finding-052 | `introduction/views.py` | 1060 | CWE-565 | high | high | Authentication token stored in an unsigned cookie: crypto_failure_lab3 issues the cookie value f"{username}/{e |
| finding-053 | `introduction/views.py` | 302 | CWE-639 | high | high | Account takeover through a predictable, client-supplied identifier: the GET branch of auth_lab_login identifie |

---

## 详细发现

### finding-001 — introduction/views.py:158

- **CWE**: CWE-89
- **严重度**: critical；**置信度**: high
- **位置**: `introduction/views.py` 第 158 行（区间 158-162）

**代码证据**

```python
name=request.POST.get('name')

password=request.POST.get('pass')
...
sql_query = "SELECT * FROM introduction_login WHERE user='"+name+"' AND password='"+password+"'"
print(sql_query)
try:
    print("\nin try\n")
    val=login.objects.raw(sql_query)
```

**触发条件**: Confirmed in source: the view requires an authenticated session (request.user.is_authenticated) and reads both values from request.POST. Needs deployment confirmation: whether the /sql_lab endpoint is reachable in the deployed environment and whether the database user has broad table privileges.

**数据流**: request.POST['name'] / request.POST['pass'] (untrusted, attacker controlled) -> string concatenation into sql_query -> login.objects.raw(sql_query) -> database executes attacker-controlled SQL text.

**根因与安全影响**: SQL injection: the SQL statement is built by concatenating the raw POST fields 'name' and 'pass' and then executed through QuerySet.raw(). An attacker who can authenticate to the lab (any registered user) can inject SQL (e.g. name=' OR '1'='1 --) and read/modify arbitrary rows of introduction_login, or reach other tables through UNION. Root cause: user input is interpolated into SQL text instead of being bound as a query parameter (rule 1.2.1 '使用参数化查询' / django-4.2-security 'SQL injection protection').

**修复方向**: Use parameter binding: `login.objects.filter(user=name, password=password)` or `sql_lab_table.objects.raw('... WHERE id=%s AND password=%s', [name, password])`; never concatenate request data into SQL text.

### finding-002 — introduction/views.py:864

- **CWE**: CWE-89
- **严重度**: critical；**置信度**: high
- **位置**: `introduction/views.py` 第 864 行（区间 864-878）

**代码证据**

```python
name=request.POST.get('name')
password=request.POST.get('pass')
...
sql_query = "SELECT * FROM introduction_sql_lab_table WHERE id='"+name+"'AND password='"+password+"'"
...
user = sql_lab_table.objects.raw(sql_query)
```

**触发条件**: Confirmed in source: authenticated user required (request.user.is_authenticated), POST body controls 'name' and 'pass'. Needs deployment confirmation: reachability of /injection_sql_lab.

**数据流**: request.POST['name'], request.POST['pass'] -> string concatenation -> sql_query -> sql_lab_table.objects.raw(sql_query) -> SQL execution with attacker-controlled input.

**根因与安全影响**: SQL injection (second, independent occurrence): the 2021 injection lab builds the raw SQL statement by concatenating request.POST['name'] and request.POST['pass'] and executes it with sql_lab_table.objects.raw(). Any authenticated user can inject SQL to bypass the password check or to read/alter other tables. Same root cause as the other raw() call but a different code location and view.

**修复方向**: Use parameter binding: `login.objects.filter(user=name, password=password)` or `sql_lab_table.objects.raw('... WHERE id=%s AND password=%s', [name, password])`; never concatenate request data into SQL text.

### finding-003 — introduction/views.py:424

- **CWE**: CWE-78
- **严重度**: critical；**置信度**: high
- **位置**: `introduction/views.py` 第 424 行（区间 424-434）

**代码证据**

```python
domain=request.POST.get('domain')
domain = re.sub(r'^(?:(https?|ftp)://)?(?:www\.)?', '', domain, flags=re.IGNORECASE)
...
if(os=='win'):
    command="nslookup {}".format(domain)
else:
    command = "dig {}".format(domain)
...
process = subprocess.Popen(
    command,
    shell=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)
```

**触发条件**: Confirmed in source: authenticated session required; POST 'domain' and 'os' fields are attacker controlled; shell=True is used. Needs deployment confirmation: whether the OS user running the server is privileged.

**数据流**: request.POST['domain'] -> regex prefix stripping (does not neutralise shell metacharacters) -> format() into 'dig {}'/'nslookup {}' -> subprocess.Popen(shell=True) -> OS shell interprets injected metacharacters.

**根因与安全影响**: OS command injection: the 'domain' POST field is only stripped of an optional scheme/www prefix and is then interpolated into a shell command string executed with subprocess.Popen(..., shell=True). A value such as 'example.com; id' or '$(id)' runs arbitrary commands with the web server's privileges. Root cause: untrusted data concatenated into a shell command (rule 1.3.2 '安全传递外部程序参数').

**修复方向**: Do not build shell command strings from request data. Use `subprocess.run(['dig', domain], shell=False, ...)` with the argument validated against a strict hostname/IP allowlist (rule 1.3.2).

### finding-004 — introduction/views.py:460

- **CWE**: CWE-95
- **严重度**: critical；**置信度**: high
- **位置**: `introduction/views.py` 第 460 行（区间 460-460）

**代码证据**

```python
val=request.POST.get('val')
print(val)
try:
    output = eval(val)
```

**触发条件**: Confirmed in source: authenticated session required; 'val' is taken verbatim from request.POST. Needs deployment confirmation: reachability of /cmd_lab2 and the privileges of the service account.

**数据流**: request.POST['val'] -> eval() -> arbitrary Python execution in the Django process context.

**根因与安全影响**: Arbitrary code execution via eval(): the POST field 'val' is passed directly to eval(), so any authenticated user can execute arbitrary Python on the server (e.g. __import__('os').system('id')). Root cause: untrusted input used as program code (rule 1.3.3 '禁止不安全的代码执行').

**修复方向**: Replace eval/ImageMath expression evaluation with a parser over a whitelist of allowed operations (e.g. `ast.literal_eval` for constants, or an explicit arithmetic parser); never evaluate request data as code (rule 1.3.3).

### finding-005 — introduction/mitre.py:215

- **CWE**: CWE-95
- **严重度**: critical；**置信度**: high
- **位置**: `introduction/mitre.py` 第 215 行（区间 215-218）

**代码证据**

```python
@csrf_exempt
def mitre_lab_25_api(request):
    if request.method == "POST":
        expression = request.POST.get('expression')
        result = eval(expression)
        return JsonResponse({'result': result})
```

**触发条件**: Confirmed in source: no authentication decorator, @csrf_exempt, POST body 'expression' fully attacker controlled. Needs deployment confirmation: whether the /mitre/25/lab/api route is exposed by the deployed URL configuration (it is registered in introduction/urls.py).

**数据流**: request.POST['expression'] -> eval() -> arbitrary code execution, result returned to the attacker in the JSON response.

**根因与安全影响**: Unauthenticated remote code execution via eval(): the mitre_lab_25_api view is decorated with @csrf_exempt and has no login check, and passes the POST field 'expression' directly to eval(). Any network client can execute arbitrary Python code on the server. Root cause: untrusted input treated as code (rule 1.3.3).

**修复方向**: Replace eval/ImageMath expression evaluation with a parser over a whitelist of allowed operations (e.g. `ast.literal_eval` for constants, or an explicit arithmetic parser); never evaluate request data as code (rule 1.3.3).

### finding-006 — introduction/mitre.py:238

- **CWE**: CWE-78
- **严重度**: critical；**置信度**: high
- **位置**: `introduction/mitre.py` 第 238 行（区间 238-243）

**代码证据**

```python
def command_out(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process.communicate()

@csrf_exempt
def mitre_lab_17_api(request):
    if request.method == 'POST':
        ip = request.POST.get('ip')
        command = "nmap " + ip
        res, err = command_out(command)
```

**触发条件**: Confirmed in source: unauthenticated, @csrf_exempt, POST 'ip' fully attacker controlled, shell=True. Needs deployment confirmation: whether nmap is installed in the deployment image (irrelevant for the injection itself).

**数据流**: request.POST['ip'] -> string concatenation 'nmap ' + ip -> subprocess.Popen(shell=True) -> shell interprets injected metacharacters; command output is returned to the caller.

**根因与安全影响**: OS command injection in the port-scanning API: the POST field 'ip' is concatenated into the command string 'nmap ' + ip and executed through command_out(), which uses subprocess.Popen(command, shell=True). The view is @csrf_exempt and unauthenticated, so a remote client can append shell metacharacters and run arbitrary commands. Root cause: untrusted data concatenated into a shell command (rule 1.3.2).

**修复方向**: Do not build shell command strings from request data. Use `subprocess.run(['dig', domain], shell=False, ...)` with the argument validated against a strict hostname/IP allowlist (rule 1.3.2).

### finding-007 — introduction/views.py:208

- **CWE**: CWE-502
- **严重度**: critical；**置信度**: high
- **位置**: `introduction/views.py` 第 208 行（区间 208-216）

**代码证据**

```python
token = request.COOKIES.get('token')
if token == None:
    token = encoded_user
    response.set_cookie(key='token',value=token.decode('utf-8'))
else:
    token = base64.b64decode(token)
    admin = pickle.loads(token)
    if admin.admin == 1:
        response = render(request,'Lab/insec_des/insec_des_lab.html', {"message":"Welcome Admin, SECRETKEY:ADMIN123"})
```

**触发条件**: Confirmed in source: the value comes from the client cookie, base64 decoding is not a trust boundary; the view requires an authenticated session but the cookie value itself is fully attacker controlled. Needs deployment confirmation: none for the deserialization path itself.

**数据流**: request.COOKIES['token'] -> base64.b64decode() -> pickle.loads() -> arbitrary object reconstruction and code execution during unpickling.

**根因与安全影响**: Insecure deserialization of a client-controlled cookie: insec_des_lab reads the 'token' cookie, base64-decodes it and calls pickle.loads() on it. Pickle data is executable, so any user who can set the cookie can craft a payload whose __reduce__ executes arbitrary code on the server. Root cause: untrusted data passed to pickle.load/loads (rule 1.4.5).

**修复方向**: Remove the unsafe deserialization: use `yaml.safe_load` for YAML, `json.loads` for structured data, and for the pickle-based lab replace `pickle.loads` with a signed, server-side token (e.g. `django.core.signing`) that only carries an identity value (rule 1.4.5).

### finding-008 — dockerized_labs/insec_des_lab/main.py:33

- **CWE**: CWE-502
- **严重度**: critical；**置信度**: high
- **位置**: `dockerized_labs/insec_des_lab/main.py` 第 33 行（区间 33-36）

**代码证据**

```python
@app.route('/deserialize', methods=['POST'])
def deserialize_data():
    try:
        serialized_data = request.form.get('serialized_data', '')
        decoded_data = base64.b64decode(serialized_data)
        user = pickle.loads(decoded_data)
```

**触发条件**: Confirmed in source: no authentication on the /deserialize route; form field fully attacker controlled. Needs deployment confirmation: whether this lab container is deployed and reachable (dockerized_labs/insec_des_lab/docker-compose.yml exists).

**数据流**: request.form['serialized_data'] -> base64.b64decode() -> pickle.loads() -> arbitrary code execution.

**根因与安全影响**: Insecure deserialization in the standalone insec_des_lab Flask application: the 'serialized_data' form field is base64-decoded and passed to pickle.loads(). An unauthenticated client can submit a malicious pickle and achieve remote code execution. Root cause: untrusted data passed to pickle.load/loads (rule 1.4.5).

**修复方向**: Remove the unsafe deserialization: use `yaml.safe_load` for YAML, `json.loads` for structured data, and for the pickle-based lab replace `pickle.loads` with a signed, server-side token (e.g. `django.core.signing`) that only carries an identity value (rule 1.4.5).

### finding-009 — introduction/views.py:560

- **CWE**: CWE-502
- **严重度**: critical；**置信度**: high
- **位置**: `introduction/views.py` 第 560 行（区间 560-560）

**代码证据**

```python
file=request.FILES["file"]
try :
    data = yaml.load(file,yaml.Loader)
    
    return render(request,"Lab/A9/a9_lab.html",{"data":data})
```

**触发条件**: Confirmed in source: authenticated session required; the uploaded file content is fully attacker controlled; yaml.Loader (not safe_load) is used. Needs deployment confirmation: the exact installed PyYAML version at runtime (requirements.txt pins 5.1).

**数据流**: request.FILES['file'] -> yaml.load(file, yaml.Loader) -> object construction during parsing -> code execution with the web server privileges.

**根因与安全影响**: Unsafe YAML deserialization of an uploaded file: a9_lab loads the uploaded file with yaml.load(file, yaml.Loader). PyYAML's Loader resolves arbitrary Python objects, so a crafted YAML upload can instantiate attacker-chosen objects and execute code (requirements.txt pins PyYAML==5.1, whose default loaders are known to be exploitable). Root cause: untrusted data passed to an unsafe YAML loader (rule 1.4.5).

**修复方向**: Remove the unsafe deserialization: use `yaml.safe_load` for YAML, `json.loads` for structured data, and for the pickle-based lab replace `pickle.loads` with a signed, server-side token (e.g. `django.core.signing`) that only carries an identity value (rule 1.4.5).

### finding-010 — introduction/views.py:256

- **CWE**: CWE-611
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 256 行（区间 256-261）

**代码证据**

```python
parser = make_parser()
parser.setFeature(feature_external_ges, True)
doc = parseString(request.body.decode('utf-8'), parser=parser)
for event, node in doc:
    if event == START_ELEMENT and node.tagName == 'text':
        doc.expandNode(node)
        text = node.toxml()
```

**触发条件**: Confirmed in source: unauthenticated view (@csrf_exempt and no login check), body fully attacker controlled, external general entities enabled. Needs deployment confirmation: whether the deployed XML library still resolves external entities (expat behaviour) and whether the process can read local files/network.

**数据流**: request.body -> xml.sax parseString with feature_external_ges=True -> doc.expandNode(node) resolves external entities -> file/URL content stored in comments table and rendered back.

**根因与安全影响**: XML External Entity (XXE) injection: the XML parser used by xxe_parse explicitly enables external general entities (parser.setFeature(feature_external_ges, True)) and parses the raw request body, so a submitted DOCTYPE with an external entity can read local files (e.g. /etc/passwd, application settings) or trigger SSRF. The expanded entity text is then written to the database and rendered back to the user. Root cause: XML parser configured to resolve external entities (rule 1.4.4 '禁用XML外部实体的方法').

**修复方向**: Disable external entity resolution: `etree.XMLParser(resolve_entities=False, no_network=True)` / `defusedxml`, and do not enable `feature_external_ges`; reject DOCTYPE declarations (rule 1.4.4).

### finding-011 — introduction/views.py:984

- **CWE**: CWE-1336
- **严重度**: critical；**置信度**: high
- **位置**: `introduction/views.py` 第 984 行（区间 984-996）

**代码证据**

```python
blog = request.POST["blog"]
...
blog = filter_blog(blog)
prepend_code = "{% extends 'introduction/base.html' %}..."

blog = prepend_code + blog + "{% endblock %}"
new_blog = Blogs.objects.create(author = request.user, blog_id = id)
new_blog.save()
dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, f"templates/Lab_2021/A3_Injection/Blogs/{id}.html")
file = open(filename, "w+")
file.write(blog)
file.close()
return redirect(f'blog/{id}')
```

**触发条件**: Confirmed in source: authenticated session required; user content is written to a .html template file and rendered by ssti_view_blog; filter_blog performs no filtering. Needs deployment confirmation: whether the templates directory is writable at runtime and whether Django's template sandbox permits the injected constructs in the deployed configuration.

**数据流**: request.POST['blog'] -> filter_blog() (identity) -> written into a Django template file -> render(request, f'Lab_2021/A3_Injection/Blogs/{blog_id}.html') -> template engine executes the injected template tags.

**根因与安全影响**: Server-side template injection through template source injection: the POST field 'blog' is only passed through filter_blog(), which is a no-op (introduction/utility.py: def filter_blog(code): return code), and the user content is written verbatim into a new Django template file under templates/Lab_2021/A3_Injection/Blogs/<id>.html, which is later rendered by ssti_view_blog. A user can therefore inject template tags (e.g. {% load ... %}{% debug %} or {% %}-based code execution) that the Django template engine executes on the server. Root cause: user content used as template source rather than as template data (rule 1.3.4 '服务端模板与数据分离').

**修复方向**: Never render user content as template source. Pass it as template data (context variable) and let Django escape it; if a template must be dynamic, restrict it to an application-owned set of templates (rule 1.3.4).

### finding-012 — introduction/views.py:926

- **CWE**: CWE-22
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 926 行（区间 926-929）

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

**触发条件**: Confirmed in source: authenticated session required; 'blog' fully attacker controlled; os.path.join does not neutralise '../' segments. Needs deployment confirmation: the read permission of the service account on the target files.

**数据流**: request.POST['blog'] -> os.path.join(dirname, file) -> open(filename).read() -> file content rendered back in the HTTP response.

**根因与安全影响**: Path traversal / arbitrary file read: the POST field 'blog' is joined to the application directory with os.path.join and opened without any validation, so a value such as '../../pygoat/settings.py' or '../../../etc/passwd' reads files outside the intended templates/Lab/ssrf/blogs directory. The content is returned to the requester in the page. Root cause: file path built from unvalidated external input without containment check (rule 1.4.3 '避免路径穿越').

**修复方向**: Resolve the candidate path and verify it stays inside an allowed root (e.g. `Path(root).resolve()` and `root in candidate.parents`), and map the user choice to a fixed whitelist of files (rule 1.4.3).

### finding-013 — introduction/views.py:963

- **CWE**: CWE-918
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 963 行（区间 963-964）

**代码证据**

```python
url = request.POST["url"]
try:
    response = requests.get(url)
    return render(request, "Lab/ssrf/ssrf_lab2.html", {"response": response.content.decode()})
```

**触发条件**: Confirmed in source: authenticated session required (@authentication_decorator); 'url' fully attacker controlled; requests follows redirects by default. Needs deployment confirmation: whether the server can reach internal/metadata addresses in the deployment network.

**数据流**: request.POST['url'] -> requests.get(url) -> response body returned in the rendered template (also rendered unescaped, see the XSS finding).

**根因与安全影响**: Server-Side Request Forgery: the POST field 'url' is passed unchecked to requests.get(url), so an authenticated user can make the server issue requests to internal hosts (e.g. http://127.0.0.1:8000/... , cloud metadata endpoints) and read the response body. No protocol/host allowlist, no redirect restrictions and no private-address filtering are applied. Root cause: unrestricted outbound request to a user-supplied URL (rule 1.5.1 '限定访问网络资源地址范围').

**修复方向**: Restrict outbound requests: allowlist protocols/hosts/ports, resolve the hostname and reject loopback/private/link-local/metadata addresses, disable automatic redirects (rule 1.5.1).

### finding-014 — introduction/templates/Lab/XSS/xss_lab.html:27

- **CWE**: CWE-79
- **严重度**: high；**置信度**: high
- **位置**: `introduction/templates/Lab/XSS/xss_lab.html` 第 27 行（区间 27-27）

**代码证据**

```python
<h3> The company '{{query|safe}}' You searched for is not Part of FAANG</h3>
```

**触发条件**: Confirmed in source: the view requires an authenticated session; the query parameter is attacker controlled and reaches the template unescaped. Needs deployment confirmation: none for the escaping bypass itself.

**数据流**: request.GET['q'] -> view context 'query' -> template {{query|safe}} -> raw HTML injected into the response body -> script execution in the victim's browser.

**根因与安全影响**: Reflected XSS: the 'q' query parameter is passed into the template and rendered with the |safe filter, which disables Django's automatic HTML escaping. The view performs no sanitisation (introduction/views.py xss_lab: q=request.GET.get('q','') -> render(request,'Lab/XSS/xss_lab.html', {'query': q})), so a URL such as /xssL?q=<script>alert(1)</script> executes script in the victim's browser. Root cause: untrusted data marked as safe (rule 1.6.3 / OWASP XSS cheat sheet 'avoid the safe filter').

**修复方向**: Remove the `|safe` filter and the blacklist filters; render untrusted values with Django's auto-escaping and, in JavaScript contexts, use `json_script` or `textContent` (rules 1.6.3 / OWASP XSS cheat sheet).

### finding-015 — introduction/templates/Lab/XSS/xss_lab_2.html:20

- **CWE**: CWE-79
- **严重度**: high；**置信度**: high
- **位置**: `introduction/templates/Lab/XSS/xss_lab_2.html` 第 20 行（区间 20-20）

**代码证据**

```python
<p>Hello, {{ username|safe }}</p>

# view code:
username = request.POST.get('username', '')
if username:
    username = username.strip()
    username = username.replace("<script>", "").replace("</script>", "")
```

**触发条件**: Confirmed in source: authenticated session required; 'username' is attacker controlled; only the two <script> literals are stripped and |safe disables escaping. Needs deployment confirmation: none.

**数据流**: request.POST['username'] -> blacklist replace of two literals -> template {{username|safe}} -> HTML/JS injection in the response.

**根因与安全影响**: Reflected XSS with an insufficient blacklist filter: the view (introduction/views.py xss_lab2) only removes the literal strings '<script>' and '</script>' from the POST field 'username' and the result is rendered with the |safe filter, so payloads such as '<img src=x onerror=alert(1)>' or '<svg onload=alert(1)>' are rendered unescaped. Root cause: blacklist-based sanitisation combined with the |safe filter.

**修复方向**: Remove the `|safe` filter and the blacklist filters; render untrusted values with Django's auto-escaping and, in JavaScript contexts, use `json_script` or `textContent` (rules 1.6.3 / OWASP XSS cheat sheet).

### finding-016 — introduction/templates/Lab/XSS/xss_lab_3.html:22

- **CWE**: CWE-79
- **严重度**: high；**置信度**: medium
- **位置**: `introduction/templates/Lab/XSS/xss_lab_3.html` 第 22 行（区间 22-23）

**代码证据**

```python
pattern = r'[a-zA-Z0-9]'
result = re.sub(pattern, '', username)
context = {'code':result}
...
# template:
<script>
    // LAB 3 JS CODE
    {{code}}
</script>
```

**触发条件**: Confirmed in source: authenticated session required; the value is inserted into a <script> block; only letters/digits are stripped. Needs deployment confirmation: exact exploitability depends on the browser parsing of the surviving characters; not verified dynamically in this run.

**数据流**: request.POST['username'] -> re.sub removing alphanumerics -> template {{code}} inside <script> -> script context injection.

**根因与安全影响**: XSS through a JavaScript context with an insufficient input filter: xss_lab3 removes only alphanumeric characters from the POST field 'username' and the remainder is injected into a <script> block ({{code}} inside <script>...</script>). Because HTML escaping does not neutralise the surviving non-alphanumeric characters, an attacker can use bracket/parenthesis/operator-only payloads (JSFuck style) that the browser executes. Root cause: user data placed in a script context, protected only by a character blacklist.

**修复方向**: Remove the `|safe` filter and the blacklist filters; render untrusted values with Django's auto-escaping and, in JavaScript contexts, use `json_script` or `textContent` (rules 1.6.3 / OWASP XSS cheat sheet).

### finding-017 — introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html:11

- **CWE**: CWE-79
- **严重度**: medium；**置信度**: high
- **位置**: `introduction/templates/Lab_2021/A8_software_and_data_integrity_failure/lab2.html` 第 11 行（区间 11-11）

**代码证据**

```python
<h1>Hey {{username | safe}},</h1>

# view code:
username = request.GET["username"]
return render(request,"Lab_2021/A8_software_and_data_integrity_failure/lab2.html", {"username":username,"success":True})
```

**触发条件**: Confirmed in source: authenticated session required (@authentication_decorator); GET parameter fully attacker controlled. Needs deployment confirmation: none.

**数据流**: request.GET['username'] -> template context 'username' -> {{username | safe}} -> raw HTML in the response.

**根因与安全影响**: Reflected XSS: the 'username' GET parameter is rendered with the |safe filter in the A8 lab page. The view (introduction/views.py software_and_data_integrity_failure_lab2) passes request.GET['username'] straight into the template without escaping, so a crafted link executes script in the victim's browser.

**修复方向**: Remove the `|safe` filter and the blacklist filters; render untrusted values with Django's auto-escaping and, in JavaScript contexts, use `json_script` or `textContent` (rules 1.6.3 / OWASP XSS cheat sheet).

### finding-018 — introduction/templates/Lab/ssrf/ssrf_lab2.html:23

- **CWE**: CWE-79
- **严重度**: medium；**置信度**: high
- **位置**: `introduction/templates/Lab/ssrf/ssrf_lab2.html` 第 23 行（区间 23-23）

**代码证据**

```python
{% if response %}
    <div style="width:70%;overflow:scroll;background-color:#000">{{response | safe}}<div>
{% endif %}
```

**触发条件**: Confirmed in source: the view fetches an attacker-chosen URL and passes response.content.decode() into the template; |safe disables escaping. Needs deployment confirmation: attacker must control the fetched resource.

**数据流**: request.POST['url'] -> requests.get(url) -> response.content -> template {{response | safe}} -> attacker HTML/JS executed in the application origin.

**根因与安全影响**: XSS via unescaped remote content: the body fetched by the SSRF lab is rendered with the |safe filter, so any HTML/JavaScript contained in the fetched resource is injected into the application page. Combined with the unvalidated requests.get(url) this allows an attacker to host a page with a script and have it executed in the application's origin when a victim submits the SSRF lab form (stored/reflected XSS through a third-party response).

**修复方向**: Remove the `|safe` filter and the blacklist filters; render untrusted values with Django's auto-escaping and, in JavaScript contexts, use `json_script` or `textContent` (rules 1.6.3 / OWASP XSS cheat sheet).

### finding-019 — introduction/views.py:347

- **CWE**: CWE-639
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 347 行（区间 347-363）

**代码证据**

```python
if request.COOKIES.get('admin') == "1":
    return render(
        request, 
        'Lab/BrokenAccess/ba_lab.html', 
        {
            "data":"0NLY_F0R_4DM1N5",
            "username": "admin"
        })
...
html.set_cookie("admin", "1",max_age=200)
```

**触发条件**: Confirmed in source: authenticated session required; the 'admin' cookie value is attacker supplied and is the only authorization check for the privileged branch. Needs deployment confirmation: none.

**数据流**: request.COOKIES['admin'] -> equality check against '1' -> privileged render of the admin secret data.

**根因与安全影响**: Broken access control / privilege escalation via a client-controlled cookie: ba_lab grants the admin-only secret (0NLY_F0R_4DM1N5) whenever the request carries the cookie admin=1. Cookies are fully controlled by the client, so any authenticated user can set admin=1 and read the administrator-only data; the cookie is also set by the server after a successful admin login without any server-side signature. Root cause: authorization decision based on client-supplied, unvalidated state (rule 1.8.3 '避免越权访问').

**修复方向**: Perform the authorization check on the server using the session identity and the object's owner/role; never accept a role flag or object id that comes from a cookie or request parameter (rule 1.8.3).

### finding-020 — introduction/views.py:758

- **CWE**: CWE-639
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 758 行（区间 758-774）

**代码证据**

```python
if request.COOKIES.get('admin') == "1":
    return render(
        request, 
        'Lab_2021/A1_BrokenAccessControl/broken_access_lab_1.html', 
        {
            "data":"0NLY_F0R_4DM1N5",
            "username": "admin"
        })
```

**触发条件**: Confirmed in source: authenticated session required; cookie value fully attacker controlled. Needs deployment confirmation: none.

**数据流**: request.COOKIES['admin'] -> check against '1' -> privileged data rendered for any authenticated caller.

**根因与安全影响**: Broken access control via a client-controlled cookie (second, independent occurrence): a1_broken_access_lab_1 returns the admin-only secret 0NLY_F0R_4DM1N5 whenever the request contains the cookie admin=1, without any server-side check of the caller's role. Any authenticated user can forge the cookie and read administrator data.

**修复方向**: Perform the authorization check on the server using the session identity and the object's owner/role; never accept a role flag or object id that comes from a cookie or request parameter (rule 1.8.3).

### finding-021 — introduction/views.py:535

- **CWE**: CWE-807
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 535 行（区间 535-540）

**代码证据**

```python
XHost = request.headers.get('X-Host', 'None')
if(XHost == 'admin.localhost:8000'):
    return render(request,"Lab/sec_mis/sec_mis_lab.html", {"secret": "S3CR37K3Y"})
else:
    return render(request,"Lab/sec_mis/sec_mis_lab.html", {"no_secret": "Only admin.localhost:8000 can access, Your X-Host is " + XHost})
```

**触发条件**: Confirmed in source: the view has no authentication check at all and trusts request.headers['X-Host']. Needs deployment confirmation: whether a reverse proxy strips/overrides X-Host (none is configured in the repository).

**数据流**: request header 'X-Host' -> string comparison -> privileged secret rendered to the caller.

**根因与安全影响**: Security decision based on a client-supplied HTTP header: the 'secret' view exposes the secret key S3CR37K3Y to anyone who sends the header 'X-Host: admin.localhost:8000'. The header is entirely under the client's control, so the restriction provides no protection. Root cause: untrusted client header used to decide authorization (rule 1.8.5 '可信会话与授权决策').

**修复方向**: Do not derive authorization decisions from client-controllable headers (X-Host, User-Agent); use the authenticated session or a value set by a trusted reverse proxy that strips client-supplied copies (rule 1.8.5).

### finding-022 — introduction/views.py:791

- **CWE**: CWE-807
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 791 行（区间 791-799）

**代码证据**

```python
user_agent = request.META['HTTP_USER_AGENT']
...
if name :  
    if (user_agent == "pygoat_admin"):
        return render(
            request, 
            'Lab_2021/A1_BrokenAccessControl/broken_access_lab_2.html', 
            {
                "data":"0NLY_F0R_4DM1N5",
                "username": "admin",
                "status": "admin"
            })
```

**触发条件**: Confirmed in source: authenticated session required; User-Agent value fully attacker controlled. Needs deployment confirmation: none.

**数据流**: request.META['HTTP_USER_AGENT'] -> equality check -> privileged admin data rendered.

**根因与安全影响**: Administrator impersonation via the User-Agent header: a1_broken_access_lab_2 grants the admin secret and the 'status: admin' marker when request.META['HTTP_USER_AGENT'] equals 'pygoat_admin'. The User-Agent is fully attacker controlled, so any authenticated user can obtain administrator privileges/data by changing the header. Root cause: client-supplied header used as an authorization signal (rule 1.8.5).

**修复方向**: Do not derive authorization decisions from client-controllable headers (X-Host, User-Agent); use the authenticated session or a value set by a trusted reverse proxy that strips client-supplied copies (rule 1.8.5).

### finding-023 — introduction/views.py:943

- **CWE**: CWE-290
- **严重度**: medium；**置信度**: high
- **位置**: `introduction/views.py` 第 943 行（区间 943-950）

**代码证据**

```python
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

**触发条件**: Confirmed in source: no authentication and no trusted-proxy handling; the header value is taken verbatim from the client. Needs deployment confirmation: whether an upstream proxy strips client-supplied X-Forwarded-For (not configured in the repository).

**数据流**: request.META['HTTP_X_FORWARDED_FOR'] -> first element -> comparison with '127.0.0.1' -> access decision.

**根因与安全影响**: Access control based on a spoofable client header: ssrf_target decides whether the requester may see the restricted page using the first value of the X-Forwarded-For header, falling back to REMOTE_ADDR. X-Forwarded-For is supplied by the client and no trusted-proxy configuration exists, so any client can spoof '127.0.0.1' and bypass the restriction. Root cause: client-controlled header used for an authorization decision (rule 1.8.5).

**修复方向**: Determine the client address from REMOTE_ADDR, or from a proxy header only when a trusted proxy is configured and the header is rewritten by it (rule 1.8.5).

### finding-024 — introduction/views.py:287

- **CWE**: CWE-256
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 287 行（区间 287-291）

**代码证据**

```python
passwd  = request.POST['pass']
obj = authLogin.objects.create(name=name,username=user_name,password=passwd)
...
obj = authLogin.objects.filter(username=user_name,password=passwd)[0]
```

**触发条件**: Confirmed in source: password is stored and compared in cleartext; the signup view is unauthenticated. Needs deployment confirmation: database access by other principals (e.g. backups) determines the impact.

**数据流**: request.POST['pass'] -> authLogin.password column (plaintext) -> later equality comparison in auth_lab_login.

**根因与安全影响**: Plaintext storage of user passwords: auth_lab_signup stores the submitted password verbatim in the authLogin.password column (models.py: password = models.CharField(max_length=200)), and auth_lab_login compares the submitted plaintext against it. A database dump therefore discloses every user's password in cleartext, and the same plaintext comparison pattern is used for the login model (a10_lab, ba_lab). Root cause: passwords stored without a dedicated one-way hash (rule 1.3.3 '口令存储安全').

**修复方向**: Store passwords with a one-way, salted, adaptive hash (`make_password` / Argon2id / bcrypt) and verify them with `check_password`; never store or compare plaintext (rule 1.3.3).

### finding-025 — introduction/views.py:1026

- **CWE**: CWE-328
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 1026 行（区间 1026-1027）

**代码证据**

```python
username = request.POST["username"]
password = request.POST["password"]
try:
    password = md5(password.encode()).hexdigest()
    user = CF_user.objects.filter(username=username,password=password).first()
```

**触发条件**: Confirmed in source: MD5 with no salt and no iteration count; the compared column is CF_user.password. Needs deployment confirmation: whether the CF_user table is populated with real credentials in the deployment.

**数据流**: request.POST['password'] -> md5 digest -> equality filter against CF_user.password.

**根因与安全影响**: Weak password hashing: crypto_failure_lab verifies passwords with a single unsalted MD5 digest (md5(password.encode()).hexdigest()) and compares it with the stored value. MD5 is fast and unsalted, so stored hashes can be cracked or rainbow-tabled in bulk. Root cause: single fast digest used instead of a salted, adaptive password hash (rule 1.3.3).

**修复方向**: Replace the fast digest with a salted, adaptive password hash (Django's `make_password`/`check_password`, Argon2id, bcrypt, PBKDF2) and migrate the stored values (rule 1.3.3).

### finding-026 — introduction/mitre.py:159

- **CWE**: CWE-328
- **严重度**: high；**置信度**: high
- **位置**: `introduction/mitre.py` 第 159 行（区间 159-162）

**代码证据**

```python
password = request.POST.get('password')
username = request.POST.get('username')
password = md5(password.encode()).hexdigest()
User = CSRF_user_tbl.objects.filter(username=username, password=password)
```

**触发条件**: Confirmed in source: unsalted single MD5; stored column CSRF_user_tbl.password (models.py password = models.CharField(max_length=200)). Needs deployment confirmation: presence of populated credentials in the deployment.

**数据流**: request.POST['password'] -> md5 hexdigest -> equality filter on CSRF_user_tbl.password.

**根因与安全影响**: Weak password hashing in the CSRF lab login: the submitted password is reduced to a single unsalted MD5 digest and compared with the stored value in CSRF_user_tbl. MD5 digests are fast to compute, so attackers with read access to the table can crack the passwords offline. Root cause: single fast digest instead of a salted, adaptive password hash (rule 1.3.3).

**修复方向**: Replace the fast digest with a salted, adaptive password hash (Django's `make_password`/`check_password`, Argon2id, bcrypt, PBKDF2) and migrate the stored values (rule 1.3.3).

### finding-027 — introduction/views.py:1194

- **CWE**: CWE-328
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 1194 行（区间 1194-1194）

**代码证据**

```python
username = request.POST["username"]
password = request.POST["password"]
password = hashlib.sha256(password.encode()).hexdigest()
...
if USER_A7_LAB3[username]['password'] == password:
```

**触发条件**: Confirmed in source: single unsalted SHA-256; digests are hardcoded in the source. Needs deployment confirmation: none for the weakness itself.

**数据流**: request.POST['password'] -> sha256 hexdigest -> comparison with hardcoded digest table.

**根因与安全影响**: Unsalted SHA-256 used for password verification: auth_failure_lab3 hashes the submitted password with a single unsalted SHA-256 call and compares it with the hardcoded digest table USER_A7_LAB3. A single fast, unsalted digest allows identical passwords to be recognised across accounts and makes offline cracking cheap; it is not a password hashing function. Root cause: rule 1.3.3 '口令存储安全' requires salted, adaptive hashing.

**修复方向**: Replace the fast digest with a salted, adaptive password hash (Django's `make_password`/`check_password`, Argon2id, bcrypt, PBKDF2) and migrate the stored values (rule 1.3.3).

### finding-028 — introduction/mitre.py:169

- **CWE**: CWE-798
- **严重度**: high；**置信度**: high
- **位置**: `introduction/mitre.py` 第 169 行（区间 169-171）

**代码证据**

```python
cookie = jwt.encode(payload, 'csrf_vulnerability', algorithm='HS256')
response = redirect("/mitre/9/lab/transaction")
response.set_cookie('auth_cookiee', cookie)
...
payload = jwt.decode(cookie, 'csrf_vulnerability', algorithms=['HS256'])
```

**触发条件**: Confirmed in source: the key is a literal string in the repository; no key rotation or external secret is used. Needs deployment confirmation: whether the deployed code uses the same key (the value is baked into the source).

**数据流**: attacker-known literal key -> jwt.encode({'username': '<victim>'}) -> cookie auth_cookiee accepted by csrf_transfer_monei / csrf_transfer_monei_api.

**根因与安全影响**: Hardcoded JWT signing key: the CSRF lab signs and verifies its authentication cookie with the literal string 'csrf_vulnerability'. Anyone who knows this value (it is in the source) can forge a valid auth_cookiee token with an arbitrary 'username' claim and thereby act as any user of the CSRF_user_tbl table, including accounts with credit balance. Root cause: hardcoded cryptographic key used for token signing (rule 2.3.1/2.3.2).

**修复方向**: Remove the credential/secret literals from the source: load secrets from the environment or a secret manager, generate strong random values, and rotate anything that was published (rules 2.3.1 / 2.3.2).

### finding-029 — introduction/mitre.py:191

- **CWE**: CWE-352
- **严重度**: high；**置信度**: high
- **位置**: `introduction/mitre.py` 第 191 行（区间 191-206）

**代码证据**

```python
def csrf_transfer_monei_api(request,recipent,amount):
    if request.method == "GET":
        cookie = request.COOKIES['auth_cookiee']
        payload = jwt.decode(cookie, 'csrf_vulnerability', algorithms=['HS256'])
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
```

**触发条件**: Confirmed in source: no authentication decorator, no CSRF token check, state change performed for the GET method. Needs deployment confirmation: the victim must have a valid auth_cookiee cookie and a balance; the route is registered in introduction/urls.py.

**数据流**: cross-site GET request (browser attaches auth_cookiee automatically) -> jwt.decode -> balance of the victim is debited and credited to the attacker-chosen recipient.

**根因与安全影响**: State-changing financial operation without CSRF protection and without authentication: csrf_transfer_monei_api performs a money transfer when called with GET, and the view is neither decorated with @authentication_decorator nor protected against CSRF. A third-party page can therefore cause a logged-in victim's browser to issue GET /mitre/9/lab/api/<recipient>/<amount> and move money from the victim's balance (cookie auth_cookiee is attached automatically by the browser). Root cause: rule 1.8.6 '浏览器请求防伪造' and rule 1.8.1 '默认鉴权'.

**修复方向**: Require a CSRF token on state-changing requests, use POST/PUT instead of GET for the transfer, and authenticate the operation server-side (rule 1.8.6).

### finding-030 — pygoat/settings.py:171

- **CWE**: CWE-321
- **严重度**: high；**置信度**: high
- **位置**: `pygoat/settings.py` 第 171 行（区间 171-171）

**代码证据**

```python
SECRET_COOKIE_KEY = "PYGOAT"

# usage in introduction/views.py:
payload = jwt.decode(cookie, SECRET_COOKIE_KEY, algorithms=['HS256'])
if payload['user'] == 'admin':
    return render(request,"Lab/sec_mis/sec_mis_lab3.html", {"admin":True} )
```

**触发条件**: Confirmed in source: the key is a short literal in the settings module and is imported by introduction/views.py. Needs deployment confirmation: whether the deployment overrides SECRET_COOKIE_KEY (no override exists in the repository).

**数据流**: known constant 'PYGOAT' -> jwt.encode({'user':'admin'}) -> cookie auth_cookie -> jwt.decode accepts it -> admin branch rendered.

**根因与安全影响**: Hardcoded, weak JWT signing key: SECRET_COOKIE_KEY = "PYGOAT" is a literal constant committed to the repository and is used to sign and verify the 'auth_cookie' JWT in sec_misconfig_lab3. Anybody who reads the source can craft a token with the claim {'user': 'admin'} and obtain the administrator view. Root cause: hardcoded cryptographic key (rule 2.3.1/2.3.2 '禁止硬编码敏感配置').

**修复方向**: Generate the JWT signing key with a cryptographically secure random value of sufficient length, keep it in the environment/secret manager and support rotation (rules 2.3.1 / 2.3.2).

### finding-031 — pygoat/settings.py:25

- **CWE**: CWE-798
- **严重度**: medium；**置信度**: high
- **位置**: `pygoat/settings.py` 第 25 行（区间 25-25）

**代码证据**

```python
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'lr66%-a!$km5ed@n5ug!tya5bv!0(yqwa1tn!q%0%3m2nh%oml'
```

**触发条件**: Confirmed in source: literal key in the settings module; no environment override. Needs deployment confirmation: whether the deployed instance uses this exact value (django_heroku.settings(locals()) does not replace it).

**数据流**: repository source -> SECRET_KEY -> signing of session cookies, CSRF tokens and any password-reset tokens.

**根因与安全影响**: Django SECRET_KEY hardcoded in the source repository: the value is a fixed literal committed to version control and is used for signing sessions, CSRF tokens and password-reset tokens. Disclosure of the repository therefore discloses the key, allowing session/CSRF token forgery and password-reset token forgery. Root cause: rule 2.3.2 '禁止硬编码敏感配置' and the Django deployment checklist ('keep SECRET_KEY secret, load it from the environment').

**修复方向**: Remove the credential/secret literals from the source: load secrets from the environment or a secret manager, generate strong random values, and rotate anything that was published (rules 2.3.1 / 2.3.2).

### finding-032 — pygoat/settings.py:30

- **CWE**: CWE-489
- **严重度**: high；**置信度**: high
- **位置**: `pygoat/settings.py` 第 30 行（区间 30-30）

**代码证据**

```python
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
```

**触发条件**: Confirmed in source: DEBUG = True in the only settings module of the project; the Dockerfile runs gunicorn against this settings module. Needs deployment confirmation: whether the deployment overrides DEBUG through an environment-specific settings module (none is present in the repository).

**数据流**: settings.DEBUG -> Django technical error pages -> source code, settings and local variables returned to unauthenticated clients.

**根因与安全影响**: DEBUG mode is enabled in the shipped settings module. With DEBUG=True Django exposes detailed tracebacks, source snippets, local variables and settings values to any client that triggers an error, turning application errors into an information-disclosure channel. Root cause: rule 1.11.1 '生产环境关闭调试模式' and the Django deployment checklist ('You must never enable debug in production').

**修复方向**: Set DEBUG = False in the deployed settings, keep DEBUG/SECRET_KEY/ALLOWED_HOSTS in environment-specific settings modules, and run `manage.py check --deploy` (rules 1.11.1 / 1.10.1).

### finding-033 — introduction/views.py:291

- **CWE**: CWE-614
- **严重度**: medium；**置信度**: high
- **位置**: `introduction/views.py` 第 291 行（区间 291-291）

**代码证据**

```python
response.set_cookie('userid', obj.userid, max_age=31449600, samesite=None, secure=False)
```

**触发条件**: Confirmed in source: set_cookie is called with secure=False, samesite=None and no httponly argument (Django default httponly=False). Needs deployment confirmation: whether the site is served over HTTPS (the cookie would still be transmitted over any plain-HTTP request).

**数据流**: set_cookie('userid', ...) -> browser stores and sends the identity cookie over HTTP and exposes it to scripts.

**根因与安全影响**: Authentication cookie set without secure/httponly/samesite protections: the 'userid' cookie that identifies the logged-in user of the AUTH lab is issued with secure=False and samesite=None and without httponly=True, so it can be sent over plain HTTP and read by JavaScript. Root cause: rule 1.6.2 '设置安全的HTTP响应头' requires HttpOnly/Secure/SameSite on credential cookies.

**修复方向**: Set `secure=True`, `httponly=True` and an explicit `samesite` value on credential cookies, and serve the site over HTTPS only (rule 1.6.2).

### finding-034 — introduction/views.py:496

- **CWE**: CWE-330
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 496 行（区间 496-507）

**代码证据**

```python
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
```

**触发条件**: Confirmed in source: unauthenticated endpoints; the OTP value is written into the response template; randint() is not a CSPRNG; no expiry and no attempt counter. Needs deployment confirmation: none.

**数据流**: request.GET['email'] -> randint(100,999) -> otp table -> rendered into the response body -> the same code is later accepted by the POST verification branch.

**根因与安全影响**: One-time-password verification code disclosed in the HTTP response: the /otp GET handler renders the generated 3-digit code into the page ('otp': otpN), so anybody who requests a code for an address learns the code and can immediately complete the login. In addition the code is generated with the non-cryptographic randint(), is only 3 digits long, is stored in a shared table row and is never invalidated after use. Root cause: rule 1.3.6 '安全生成和验证认证令牌' and '不得在请求验证码的普通响应中直接返回答案'.

**修复方向**: Use `secrets.token_urlsafe()`/`secrets.randbelow()` for tokens, OTP codes and API keys, bind them to the account and purpose, add an expiry, a single use and an attempt limit (rule 1.3.6).

### finding-035 — introduction/views.py:512

- **CWE**: CWE-287
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 512 行（区间 512-518）

**代码证据**

```python
otpR=request.POST.get("otp")
email=request.COOKIES.get("email")
if otp.objects.filter(email=email,otp=otpR) or otp.objects.filter(id=2,otp=otpR):
    return render (request,"Lab/BrokenAuth/otp.html",{"email":email})
else:
    return render (request,"Lab/BrokenAuth/otp.html",{"otp":"Invalid OTP Please Try Again"})
```

**触发条件**: Confirmed in source: the account identifier comes from a client cookie, the code space is 900 values, there is no attempt counter or expiry, and the id=2 admin row is checked independently of the requested email. Needs deployment confirmation: none.

**数据流**: request.POST['otp'] + request.COOKIES['email'] (both client controlled) -> database filter on (email, otp) or (id=2, otp) -> successful login rendering.

**根因与安全影响**: OTP authentication not bound to the requested account and without attempt limits: the POST branch of /otp accepts a code when otp.objects.filter(email=email,otp=otpR) matches, where 'email' is taken from the client-controlled 'email' cookie, or when the single admin record (id=2) matches, without any binding to the session, no expiry, no one-time use and no rate limiting. With only 3-digit codes, an attacker can brute-force the admin code or reuse a disclosed code for any address. Root cause: rule 1.3.6 '验证码与目标账号和用途绑定，限制有效期、尝试次数和使用次数'.

**修复方向**: Bind the credential to the session/account that requested it, enforce expiry, single use and attempt limits, and never accept an identifier from a client-controlled cookie (rules 1.3.6 / 1.8.5).

### finding-036 — introduction/views.py:679

- **CWE**: CWE-330
- **严重度**: medium；**置信度**: high
- **位置**: `introduction/views.py` 第 679 行（区间 679-680）

**代码证据**

```python
def gentckt():
    return (''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=10)))
```

**触发条件**: Confirmed in source: random.choices (Mersenne Twister) is used for security-relevant ticket codes; the tickets are stored in the DB and used as ownership tokens. Needs deployment confirmation: whether ticket codes are used as an authorization token in the deployment (the lab treats them as such).

**数据流**: random.choices() -> ticket code stored in tickits.tickit -> used as the user ticket identifier.

**根因与安全影响**: Predictable ticket codes generated with a non-cryptographic PRNG: gentckt() builds ticket identifiers with random.choices() from the Mersenne Twister, whose state can be recovered from observed outputs, so the tickets that are supposed to be unique and unguessable can be predicted. Root cause: rule 1.3.6 '会话令牌、API Key ... 使用密码学安全随机源，例如 Python secrets'.

**修复方向**: Use `secrets.token_urlsafe()`/`secrets.randbelow()` for tokens, OTP codes and API keys, bind them to the account and purpose, add an expiry, a single use and an attempt limit (rule 1.3.6).

### finding-037 — dockerized_labs/sensitive_data_exposure/dataexposure/views.py:38

- **CWE**: CWE-330
- **严重度**: medium；**置信度**: high
- **位置**: `dockerized_labs/sensitive_data_exposure/dataexposure/views.py` 第 38 行（区间 38-42）

**代码证据**

```python
def generate_api_key():
    # generate a random api key
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=16))  # 16 chars should be enough right?
```

**触发条件**: Confirmed in source: random.choices used for an API credential; 16 chars from a 36-symbol alphabet is also a small key space. Needs deployment confirmation: whether the API key is accepted anywhere as an authentication credential in the deployment (it is exposed by the API endpoints).

**数据流**: random.choices() -> UserData.api_key -> returned in api_data_view / all_users_data_view JSON responses.

**根因与安全影响**: API keys generated with a non-cryptographic PRNG: generate_api_key() builds the per-user API key with random.choices(), so the Mersenne Twister state can be reconstructed and the keys predicted; the key is stored per user and returned by the data-exposure API. Root cause: rule 1.3.6 'API Key ... 使用密码学安全随机源'.

**修复方向**: Use `secrets.token_urlsafe()`/`secrets.randbelow()` for tokens, OTP codes and API keys, bind them to the account and purpose, add an expiry, a single use and an attempt limit (rule 1.3.6).

### finding-038 — dockerized_labs/sensitive_data_exposure/dataexposure/views.py:112

- **CWE**: CWE-306
- **严重度**: critical；**置信度**: high
- **位置**: `dockerized_labs/sensitive_data_exposure/dataexposure/views.py` 第 112 行（区间 112-126）

**代码证据**

```python
def all_users_data_view(request):
    # MAJOR SECURITY FLAW: This endpoint allows ANY user (even unauthenticated ones!)
    # to see ALL users' sensitive data!
    all_users_data = []
    for user_data in UserData.objects.all():
        all_users_data.append({
            'username': user_data.user.username,
            'credit_card': user_data.credit_card,
            'ssn': user_data.ssn,
            'api_key': user_data.api_key
        })
    return JsonResponse({'users': all_users_data})
```

**触发条件**: Confirmed in source: no @login_required, no role check; the route /api/all-users/ is registered in dataexposure/urls.py. Needs deployment confirmation: whether the lab container is deployed and reachable.

**数据流**: anonymous HTTP request -> UserData.objects.all() -> JSON response containing credit card numbers, SSNs and API keys of all users.

**根因与安全影响**: Unauthenticated endpoint discloses every user's sensitive data: all_users_data_view has no authentication or authorization check and returns, for all accounts, the username, full credit card number, full SSN and API key as JSON. Any anonymous client can harvest this data. Root cause: rule 1.8.1 '默认鉴权' and rule 1.7.3 '高敏感信息禁止存储、展示'.

**修复方向**: Require authentication (and an appropriate role) for the endpoint, and return only the data the caller is allowed to see (rule 1.8.1).

### finding-039 — dockerized_labs/sensitive_data_exposure/dataexposure/views.py:87

- **CWE**: CWE-200
- **严重度**: high；**置信度**: high
- **位置**: `dockerized_labs/sensitive_data_exposure/dataexposure/views.py` 第 87 行（区间 87-107）

**代码证据**

```python
data = {
    'username': request.user.username,
    'credit_card': user_data.credit_card,
    'ssn': user_data.ssn,
    'api_key': user_data.api_key
}
# Intentionally exposing sensitive data through API
return JsonResponse(data)
```

**触发条件**: Confirmed in source: only @login_required is applied (no staff/owner check), and no masking is performed. Needs deployment confirmation: whether the JSON endpoint is exposed publicly in the deployment.

**数据流**: authenticated request -> UserData row -> unmasked credit card / SSN / API key in the JSON body.

**根因与安全影响**: Sensitive data returned unmasked by the authenticated API: api_data_view returns the full credit card number, the full SSN and the API key of the requesting user as JSON without any masking, although the same data is masked in the profile page. Root cause: rule 1.7.2/1.7.4 '敏感信息须在后台进行脱敏处理' and '个人敏感信息需脱敏展示'.

**修复方向**: Mask or omit sensitive values in API responses (e.g. only the last 4 digits of a card number) and return them only to the data owner; apply data-minimisation (rules 1.7.2 / 1.7.4).

### finding-040 — dockerized_labs/broken_auth_lab/app.py:45

- **CWE**: CWE-345
- **严重度**: high；**置信度**: high
- **位置**: `dockerized_labs/broken_auth_lab/app.py` 第 45 行（区间 45-51）

**代码证据**

```python
session_token = base64.b64encode(f"{username}:{datetime.now()}".encode()).decode()
...
response.set_cookie('session', session_token)
...
def dashboard():
    session_token = request.cookies.get('session')
    ...
    username = base64.b64decode(session_token).decode().split(':')[0]
    if username in users:
        return render_template('dashboard.html', username=username, role=users[username]['role'], email=users[username]['email'])
```

**触发条件**: Confirmed in source: no signature/HMAC on the cookie, no server-side session store, no expiry validation. Needs deployment confirmation: whether the lab container is deployed and reachable.

**数据流**: attacker-crafted base64 cookie -> base64.b64decode -> username extracted -> users[username] loaded -> role/email rendered as an authenticated user.

**根因与安全影响**: Forgeable session token: the 'session' cookie only contains base64(username:timestamp) and the dashboard re-derives the identity by base64-decoding it (username = base64.b64decode(session_token).decode().split(':')[0]). The value has no signature, no server-side session record and no expiry check, so anyone can craft base64('admin:<timestamp>') and be accepted as the administrator. Root cause: CWE-345 insufficient verification of data authenticity / CWE-287 improper authentication.

**修复方向**: Sign session/identity values with a server-side secret (or store them server-side) and validate the signature and expiry before use; never trust a client-supplied, unsigned token (rule 1.8.5).

### finding-041 — dockerized_labs/broken_auth_lab/app.py:8

- **CWE**: CWE-798
- **严重度**: medium；**置信度**: high
- **位置**: `dockerized_labs/broken_auth_lab/app.py` 第 8 行（区间 8-8）

**代码证据**

```python
app.secret_key = 'your-secret-key-here'  # Vulnerable: Hardcoded secret key
```

**触发条件**: Confirmed in source: literal key committed to the repository; no environment override in the lab. Needs deployment confirmation: whether the lab is deployed with an overridden key (none configured).

**数据流**: source code -> known Flask secret key -> ability to sign arbitrary session cookies.

**根因与安全影响**: Hardcoded Flask secret key: app.secret_key is the literal 'your-secret-key-here'. Because Flask signs its session cookies with this key, anybody who knows the source can forge valid Flask session cookies for the application. Root cause: rule 2.3.2 '禁止硬编码敏感配置'.

**修复方向**: Remove the credential/secret literals from the source: load secrets from the environment or a secret manager, generate strong random values, and rotate anything that was published (rules 2.3.1 / 2.3.2).

### finding-042 — dockerized_labs/broken_auth_lab/app.py:11

- **CWE**: CWE-798
- **严重度**: high；**置信度**: high
- **位置**: `dockerized_labs/broken_auth_lab/app.py` 第 11 行（区间 11-25）

**代码证据**

```python
users = {
    'admin': {
        'password': 'admin123',
        'email': 'admin@example.com',
        'role': 'admin'
    },
    'user': {
        'password': 'password123',
        'email': 'user@example.com',
        'role': 'user'
    }
}
```

**触发条件**: Confirmed in source: credentials are literals in the source and are used by the /login route. Needs deployment confirmation: whether the lab container is deployed and reachable.

**数据流**: hardcoded credential -> login comparison -> role 'admin' session for the attacker.

**根因与安全影响**: Hardcoded administrator credentials and plaintext password storage: the in-memory user table contains the hardcoded account 'admin' with password 'admin123' and 'user' with password 'password123', and the passwords of newly registered users are also stored in cleartext and compared in cleartext (users[username]['password'] == password). Root cause: rule 1.3.3 '口令存储安全' and CWE-798 use of hard-coded credentials.

**修复方向**: Remove the credential/secret literals from the source: load secrets from the environment or a secret manager, generate strong random values, and rotate anything that was published (rules 2.3.1 / 2.3.2).

### finding-043 — dockerized_labs/broken_auth_lab/app.py:86

- **CWE**: CWE-330
- **严重度**: high；**置信度**: high
- **位置**: `dockerized_labs/broken_auth_lab/app.py` 第 86 行（区间 86-91）

**代码证据**

```python
for username, user_data in users.items():
    if user_data['email'] == email:
        # Predictable token generation
        token = hashlib.md5(f"{email}:{datetime.now()}".encode()).hexdigest()
        password_reset_tokens[token] = username
        flash(f'Password reset link: /reset/{token}')
```

**触发条件**: Confirmed in source: the token is derived from the e-mail address and the current time via MD5 and is echoed in the response; it never expires and is not single-use. Needs deployment confirmation: whether the lab container is deployed.

**数据流**: request.form['email'] -> md5(email:timestamp) -> token disclosed in the response -> token accepted by /reset/<token>.

**根因与安全影响**: Predictable and disclosed password-reset token: the reset token is md5(f'{email}:{datetime.now()}') - a fast, unsalted digest over predictable inputs - and the token is additionally printed back to the requester in the response ('Password reset link: /reset/<token>'), so anybody who knows an account's e-mail address can obtain a valid reset token. Root cause: rule 1.3.6 '密码重置令牌应足够难猜、限时、一次性使用'.

**修复方向**: Use `secrets.token_urlsafe()`/`secrets.randbelow()` for tokens, OTP codes and API keys, bind them to the account and purpose, add an expiry, a single use and an attempt limit (rule 1.3.6).

### finding-044 — introduction/apis.py:61

- **CWE**: CWE-94
- **严重度**: critical；**置信度**: high
- **位置**: `introduction/apis.py` 第 61 行（区间 61-74）

**代码证据**

```python
@csrf_exempt
# @authentication_decorator
def log_function_checker(request):
    if request.method == 'POST':
        csrf_token = request.POST.get("csrfmiddlewaretoken")
        log_code = request.POST.get('log_code')
        api_code = request.POST.get('api_code')
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

**触发条件**: Confirmed in source: no authentication check (decorator commented out), @csrf_exempt, POST body fully attacker controlled, the written files are imported application modules. Needs deployment confirmation: the application package directory must be writable at runtime (it is in the Docker image where the source is copied to /app), and a process restart (or reload) is required for the injected code to execute.

**数据流**: request.POST['log_code'] / request.POST['api_code'] -> open(...,'w').write(...) -> introduction/playground/A9/main.py and api.py -> imported by the Django app on the next start -> attacker code executes with the application privileges.

**根因与安全影响**: Unauthenticated arbitrary write of Python source files: log_function_checker (the @authentication_decorator above it is commented out) takes the POST fields 'log_code' and 'api_code' and writes them verbatim over introduction/playground/A9/main.py and introduction/playground/A9/api.py. Both modules are imported by the application (introduction/urls.py imports log_function_target from A9.api, introduction/apis.py imports Log from A9.main), so the injected source is executed by the interpreter the next time the application starts - persistent remote code execution. Root cause: rule 1.3.3/1.3.4 '禁止外部输入覆写会被导入执行的源文件'.

**修复方向**: Never write request data into source files that the application imports. Accept the code as data in a sandbox, or store it in a non-executed location and validate it against a strict grammar (rules 1.3.3 / 1.3.4).

### finding-045 — introduction/apis.py:126

- **CWE**: CWE-94
- **严重度**: high；**置信度**: high
- **位置**: `introduction/apis.py` 第 126 行（区间 126-135）

**代码证据**

```python
@csrf_exempt
def A6_disscussion_api_2(request):
    if request.method != 'POST':
        return JsonResponse({"message":"method not allowed"},status = 405)
    try:
        code = request.POST.get('code')
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, "playground/A6/utility.py")
        f = open(filename,"w")
        f.write(code)
        f.close()
```

**触发条件**: Confirmed in source: no authentication check, @csrf_exempt, code fully attacker controlled, target file is an imported module. Needs deployment confirmation: writable package directory and a restart/reload of the application for the injected code to run.

**数据流**: request.POST['code'] -> introduction/playground/A6/utility.py -> imported by introduction/apis.py at start-up -> attacker code executed.

**根因与安全影响**: Arbitrary write of an imported Python module: A6_disscussion_api_2 accepts the POST field 'code' and writes it over introduction/playground/A6/utility.py, which is imported at application start (introduction/apis.py: from introduction.playground.A6.utility import check_vuln). The written source therefore runs at the next application start, giving persistent code execution. Root cause: rule 1.3.3/1.3.4 (external input overwriting source files that are imported and executed).

**修复方向**: Never write request data into source files that the application imports. Accept the code as data in a sandbox, or store it in a non-executed location and validate it against a strict grammar (rules 1.3.3 / 1.3.4).

### finding-046 — introduction/utility.py:34

- **CWE**: CWE-94
- **严重度**: high；**置信度**: medium
- **位置**: `introduction/utility.py` 第 34 行（区间 34-36）

**代码证据**

```python
def ssrf_code_converter(code):
    ...
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, "playground/ssrf/main.py")
    f = open(filename,"w")
    f.write(output_Code)
    f.close()
    return 1
```

**触发条件**: Confirmed in source: 'python_code' is fully attacker controlled (authenticated), the derived text is written to an imported module file. Needs deployment confirmation: whether the deployment re-imports the module after the write (the module is imported once at start-up, so the injected code runs on the next start-up or after a reload); this was not verified dynamically.

**数据流**: request.POST['python_code'] -> ssrf_code_converter() -> introduction/playground/ssrf/main.py -> imported by introduction/apis.py -> executed in the application context.

**根因与安全影响**: User-supplied code written into an imported Python module: ssrf_code_converter takes the POST field 'python_code' and writes the derived source into introduction/playground/ssrf/main.py. That module is imported by introduction/apis.py (from introduction.playground.ssrf import main) and its function is then invoked, so the attacker-controlled source becomes part of the executed application code (immediately after a reload, and on the next start-up). Root cause: rule 1.3.3/1.3.4.

**修复方向**: Never write request data into source files that the application imports. Accept the code as data in a sandbox, or store it in a non-executed location and validate it against a strict grammar (rules 1.3.3 / 1.3.4).

### finding-047 — introduction/views.py:583

- **CWE**: CWE-95
- **严重度**: high；**置信度**: medium
- **位置**: `introduction/views.py` 第 583 行（区间 583-588）

**代码证据**

```python
file=request.FILES["file"]
function_str = request.POST.get("function")
img  = Image.open(file)
img = img.convert("RGB")
r,g,b  = img.split()
output = ImageMath.eval(function_str,img = img, b=b, r=r, g=g)
```

**触发条件**: Confirmed in source: authenticated session required; 'function' is fully attacker controlled and is evaluated by ImageMath.eval. Needs deployment confirmation: the exact escape depends on the installed Pillow version (requirements.txt pins Pillow==9.4.0) and its ImageMath sandbox; the concrete exploit was not validated in this run.

**数据流**: request.POST['function'] -> ImageMath.eval(expression) -> evaluation of attacker-controlled expression inside the server process.

**根因与安全影响**: Expression evaluation of user-controlled input: a9_lab2 passes the POST field 'function' to PIL's ImageMath.eval(), which compiles and evaluates the string in the interpreter. The expression language is restricted to the predeclared ImageMath namespace, but the attacker controls the source text that is evaluated, and Python object introspection inside an eval() context allows escaping the intended namespace. Root cause: rule 1.3.3 '禁止把不可信输入当作程序执行'.

**修复方向**: Replace eval/ImageMath expression evaluation with a parser over a whitelist of allowed operations (e.g. `ast.literal_eval` for constants, or an explicit arithmetic parser); never evaluate request data as code (rule 1.3.3).

### finding-048 — introduction/views.py:831

- **CWE**: CWE-798
- **严重度**: medium；**置信度**: high
- **位置**: `introduction/views.py` 第 831 行（区间 831-833）

**代码证据**

```python
if username == 'John' and password == 'reaper':
    return render(request,'Lab_2021/A1_BrokenAccessControl/broken_access_lab_3.html', {'loggedin':True, 'admin': False})
elif username == 'admin' and password == 'admin_pass':
    return render(request,'Lab_2021/A1_BrokenAccessControl/broken_access_lab_3.html', {'loggedin':True, 'admin': True})
```

**触发条件**: Confirmed in source: credential literals in the source file; the view is reachable for authenticated users. Needs deployment confirmation: whether the deployment keeps these values (they are hardcoded, so yes).

**数据流**: hardcoded credential pair -> comparison -> privileged 'admin': True context rendered.

**根因与安全影响**: Hardcoded credentials in the application source: the broken access control lab authenticates users by comparing the submitted values against literals in the source ('John'/'reaper' and 'admin'/'admin_pass'), so the administrator account password is publicly known from the repository. Root cause: rule 2.3.2 '禁止硬编码敏感配置' / CWE-798.

**修复方向**: Remove the credential/secret literals from the source: load secrets from the environment or a secret manager, generate strong random values, and rotate anything that was published (rules 2.3.1 / 2.3.2).

### finding-049 — introduction/views.py:837

- **CWE**: CWE-862
- **严重度**: medium；**置信度**: medium
- **位置**: `introduction/views.py` 第 837 行（区间 837-843）

**代码证据**

```python
def a1_broken_access_lab3_secret(request):
    if not request.user.is_authenticated:
        return redirect('login')
    # no checking applied here
    return render(request, 'Lab_2021/A1_BrokenAccessControl/secret.html')
```

**触发条件**: Confirmed in source: only an authentication check is present; the secret content is rendered for every authenticated user. Needs deployment confirmation: the sensitivity of the rendered secret.html content.

**数据流**: any authenticated session -> render of secret.html without a permission check.

**根因与安全影响**: Missing authorization on a sensitive endpoint: a1_broken_access_lab3_secret only verifies that a session exists and then returns the secret page to every authenticated user; the code comment explicitly states 'no checking applied here'. No object- or role-level permission check is performed, so any registered user can read the protected secret. Root cause: rule 1.8.3 '避免越权访问' / CWE-862 missing authorization.

**修复方向**: 按框架安全实践重构该处理流程。

### finding-050 — dockerized_labs/broken_auth_lab/app.py:121

- **CWE**: CWE-489
- **严重度**: medium；**置信度**: high
- **位置**: `dockerized_labs/broken_auth_lab/app.py` 第 121 行（区间 121-121）

**代码证据**

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

**触发条件**: Confirmed in source: debug=True and host 0.0.0.0 in the entry point. Needs deployment confirmation: whether the lab container actually runs this entry point and is reachable from untrusted networks.

**数据流**: untrusted network access -> Werkzeug interactive debugger -> arbitrary Python execution.

**根因与安全影响**: Flask debug mode enabled and bound to all interfaces: the standalone broken-auth lab starts with app.run(host='0.0.0.0', port=5000, debug=True). The Werkzeug debugger provides an interactive Python console to any client that can reach the port, which leads to remote code execution, and it exposes detailed stack traces. Root cause: rule 1.10.1 '生产环境关闭调试模式'.

**修复方向**: Set DEBUG = False in the deployed settings, keep DEBUG/SECRET_KEY/ALLOWED_HOSTS in environment-specific settings modules, and run `manage.py check --deploy` (rules 1.11.1 / 1.10.1).

### finding-051 — dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py:8

- **CWE**: CWE-489
- **严重度**: high；**置信度**: high
- **位置**: `dockerized_labs/sensitive_data_exposure/sensitive_data_lab/settings.py` 第 8 行（区间 8-13）

**代码证据**

```python
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-key-for-demonstration-only'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
```

**触发条件**: Confirmed in source: this is the only settings module of the lab application (sensitive_data_lab/urls.py refers to it). Needs deployment confirmation: whether the lab container is deployed and reachable.

**数据流**: settings module -> DEBUG/ALLOWED_HOSTS/SECRET_KEY -> error pages, Host header handling and Django signature verification.

**根因与安全影响**: Insecure deployment settings in the sensitive-data lab: the Django settings module hardcodes SECRET_KEY = 'django-insecure-key-for-demonstration-only', enables DEBUG = True and sets ALLOWED_HOSTS = ['*']. Together these allow Host header poisoning, detailed error pages with source/settings disclosure and forging of any signed Django value (sessions, CSRF tokens). Root cause: rules 1.11.1 and 2.3.2, and the Django deployment checklist.

**修复方向**: Set DEBUG = False in the deployed settings, keep DEBUG/SECRET_KEY/ALLOWED_HOSTS in environment-specific settings modules, and run `manage.py check --deploy` (rules 1.11.1 / 1.10.1).

### finding-052 — introduction/views.py:1060

- **CWE**: CWE-565
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 1060 行（区间 1060-1060）

**代码证据**

```python
cookie = request.COOKIES["cookie"]
...
elif cookie.split('|')[0] == 'admin':
    return render(request,"Lab_2021/A2_Crypto_failur/crypto_failure_lab3.html",{"success":True, "failure":False, "admin":True})
...
cookie = f"{username}|{expire}"
response.set_cookie("cookie", cookie)
```

**触发条件**: Confirmed in source: the cookie is read back from the request and its unsigned content decides the admin flag; only the expiry timestamp is validated, not the origin of the value. Needs deployment confirmation: the view requires an authenticated session (the forged cookie only changes the role flag, the session itself is still required).

**数据流**: request.COOKIES['cookie'] -> split('|')[0] compared with 'admin' -> administrator context rendered; the same unsigned value is issued by the POST branch.

**根因与安全影响**: Authentication token stored in an unsigned cookie: crypto_failure_lab3 issues the cookie value f"{username}|{expire}" and later treats the part before '|' as the authenticated identity. The cookie carries no signature, MAC or server-side session state, so a client can simply set cookie="admin|<future timestamp>" and be granted the administrator branch (admin=True). Root cause: reliance on client-supplied data without integrity protection (rule 1.8.5 '可信会话与授权决策').

**修复方向**: Sign the cookie value (e.g. with `django.core.signing`) or keep the session state on the server, and verify the signature and expiry before trusting the identity claim (rule 1.8.5).

### finding-053 — introduction/views.py:302

- **CWE**: CWE-639
- **严重度**: high；**置信度**: high
- **位置**: `introduction/views.py` 第 302 行（区间 302-305）

**代码证据**

```python
def auth_lab_login(request):
    if request.method == 'GET':
        try:
            obj = authLogin.objects.filter(userid=request.COOKIES['userid'])[0]
            rendered = render_to_string('Lab/AUTH/auth_success.html', {'username': obj.username,'userid':obj.userid,'name':obj.name, 'err_msg':'Login Successful'})
            response = HttpResponse(rendered)
            response.set_cookie('userid', obj.userid, max_age=31449600, samesite=None, secure=False)
```

**触发条件**: Confirmed in source: the identity is selected by a client-provided cookie value that is an AutoField primary key; the exception handler silently falls back to the login page. Needs deployment confirmation: whether the deployed database contains accounts with such identifiers (the lab creates them through the signup view).

**数据流**: request.COOKIES['userid'] -> authLogin.objects.filter(userid=...) -> the account's username/role is rendered as the logged-in identity.

**根因与安全影响**: Account takeover through a predictable, client-supplied identifier: the GET branch of auth_lab_login identifies the logged-in user purely by the 'userid' cookie, and authLogin.userid is an AutoField (sequential integer). An attacker only has to set the cookie to userid=1 (or any small integer) to be logged in as the first registered account - no password check and no signature are involved. Root cause: identity taken from an unvalidated client-controlled key (rule 1.8.3 / rule 1.8.5).

**修复方向**: Perform the authorization check on the server using the session identity and the object's owner/role; never accept a role flag or object id that comes from a cookie or request parameter (rule 1.8.3).

---

## 未覆盖范围

- 绝大多数 HTML 模板（约 170 个）只做了针对性检索（`|safe`、`mark_safe`、`csrf_token`、`form action`）而没有逐行阅读；未出现在发现中的模板不能据此认为安全。
- `introduction/static/` 下的 CSS/JS 静态资源仅检索了 `innerHTML`/`document.write`/`eval` 等 DOM sink，未做完整前端审计。
- `introduction/migrations/`、`challenge/migrations/` 与 `dockerized_labs/sensitive_data_exposure/dataexposure/migrations/` 仅做结构性查看（模型字段与表结构）。
- `introduction/static/js/a6.js`、`a7.js`、`a9.js` 只读入了与被审视图相关的前端调用片段；`introduction/templates/mitre/*`、`Lab_2021/*` 的说明性页面只做了安全关键字检索。
- `installer.sh` / `uninstaller.py` / `uninstaller.sh` / `PyGoatBot.py` 仅做片段查看；`challenge/challenge.json` 未逐条核对。
- 未做依赖漏洞情报检索（无网络），因此第三方组件版本的已知 CVE 未在确认发现中列出，仅作为候选记录。

## 分析局限

- 全部结论来自静态阅读，未运行应用、未复现攻击、未通过测试验证；所有 `validation` 字段均为 `static_analysis_only`。
- 触发条件中标注“需部署确认”的部分（路由是否可达、反向代理是否清洗头部、运行时的库版本与沙箱行为、数据库中是否存在相应账号数据）无法在本地确认。
- `finding-046`（写入 `playground/ssrf/main.py`）与 `finding-047`（`ImageMath.eval`）的具体可利用性依赖运行时的模块重载与库版本，已相应下调置信度并写入 `uncertain-findings.json` 的说明。
- 未计算精确率/召回率/F1，未读取任何标准答案或判分程序。
- 本报告不构成“整个仓库安全”或“完整覆盖所有漏洞”的结论：它只列出本次静态分析在预算内确认的、有源码证据支持的问题。
