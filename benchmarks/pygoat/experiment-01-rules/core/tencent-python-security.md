# Python 安全规范（实验修订版）

#  通用类

## I. 代码实现

### 1.1 加密算法

#### 1.1.1 【必须】避免使用不安全的对称加密算法

- DES和3DES已经不再适用于现代应用程序，应改为使用AES。

### 1.2 程序日志

#### 1.2.1 【建议】对每个重要行为都记录日志

- 确保重要行为都记录日志，且可靠保存6个月以上。


#### 1.2.2 【建议】禁止将未经验证的用户输入直接记录日志

- 不得把用户输入中的换行符、回车或日志分隔符原样拼接到日志记录中。使用结构化日志并正确编码字段，或规范化这些控制字符，防止伪造日志条目。记录认证和授权行为时，不记录口令、令牌或完整敏感数据。

#### 1.2.3 【建议】避免在日志中保存敏感信息

- 不能在日志保存密码（包括明文密码和密文密码）、密钥和其它敏感信息


### 1.3 系统口令

#### 1.3.1 【必须】禁止使用空口令、弱口令、已泄露口令

#### 1.3.2 【必须】口令强度要求

>  口令强度须同时满足：
>  1. 密码长度大于14位
>  2. 必须包含下列元素：大小写英文字母、数字、特殊字符
>  3. 不得使用各系统、程序的默认初始密码
>  4. 不能与最近6次使用过的密码重复
>  5. 不得与其他外部系统使用相同的密码

#### 1.3.3 【必须】口令存储安全

- 禁止明文或可逆加密保存用于校验身份的口令。
- 使用带独立随机盐及可调工作因子的口令哈希实现，如框架密码哈希接口、Argon2id、scrypt、bcrypt 或 PBKDF2。已有算法的参数还需满足所用库和部署环境的安全要求。
- 单次 MD5、SHA-1、SHA-256 以及对摘要进行倒序、拼接等变换，都不能替代专用口令哈希。已有摘要值不等于明文口令泄漏；仍须分别检查其存储算法、实际用途和访问路径。
- 验证口令应使用对应框架的安全校验接口，迁移算法时保留升级路径，不把全部账号设为同一密码。

#### 1.3.4 【必须】禁止传递明文口令

#### 1.3.5 【必须】禁止在不安全的信道中传输口令

#### 1.3.6 【必须】安全生成和验证认证令牌

- 会话令牌、API Key、密码重置令牌和验证码使用密码学安全随机源，例如 Python secrets 或框架安全生成器，不能用普通 random、时间戳或可预测数据的 MD5 摘要替代。
- 验证码与目标账号和用途绑定，限制有效期、尝试次数和使用次数。短验证码还需严格的限速与失败控制；不得在请求验证码的普通响应中直接返回答案，也不能让其他账号的验证码通过本账号验证。
- 密码重置令牌应足够难猜、限时、一次性使用，并通过目标用户控制的可信渠道发送；不得把重置能力直接交给任意提交邮箱地址的请求者。
- 登录和令牌验证应实施适当限速、失败计数或锁定；不能仅因使用强口令哈希就认为在线暴力猜测已受控，也不能忽略已经正确实施的限速或锁定。

## II. 配置&环境

### 2.1 Python版本选择

#### 2.1.1 【建议】使用仍受安全维护的Python版本

- 使用仍有安全维护、且与应用依赖兼容的 Python 版本。不能以满足某个过时的最低版本号作为安全证明；升级前确认框架、第三方库和部署兼容性。

### 2.2 第三方包安全

#### 2.2.2 【必须】禁止使用不安全的组件

### 2.3 配置信息

#### 2.3.1 【必须】密钥存储安全

- 签名或加密密钥必须限制访问并与受保护数据分离，采用密钥管理服务、受控配置或等价机制。字符串变换、编码及把密钥藏在源码中都不能代替密钥管理。
- 根据实际用途选择协议与算法，支持轮换和吊销；密码哈希所用随机盐不需要当作秘密密钥保存。

#### 2.3.2 【必须】禁止硬编码敏感配置

- 禁止把实际用于认证或签名的明文口令、AK/SK、数据库口令和有效密钥写在源码中；使用配置系统或密钥管理服务，并限制访问、支持轮换。
- 先区分明文凭据、密码摘要、普通常量和占位示例，再判断实际使用与暴露路径。不得仅凭名称含 password、secret 或 flag 就断定真实凭据泄漏；也不能仅因代码标为演示就豁免实际生效的明文凭据。
- 密钥需要足够随机性与强度，不能使用项目名称、固定短词或可预测值。

#  后台类

## I. 代码实现

### 1.1 输入验证
#### 1.1.1 【必须】按类型进行数据校验
- 所有程序外部输入的参数值，应进行数据校验。校验内容包括但不限于：数据长度、数据范围、数据类型与格式。校验不通过，应拒绝。

- 推荐使用组件：[Cerberus](https://github.com/pyeve/cerberus)、[jsonschema](https://github.com/Julian/jsonschema)、[Django-Validators](https://docs.djangoproject.com/en/dev/ref/validators/)

```python
# Cerberus示例
v = Validator({'name': {'type': 'string'}})
v.validate({'name': 'john doe'})

# jsonschema示例
schema = {
     "type" : "object",
     "properties" : {
         "price" : {"type" : "number"},
         "name" : {"type" : "string"},
     },
}

validate(instance={"name" : "Eggs", "price" : 34.99}, schema=schema)
```

### 1.2 SQL操作

#### 1.2.1 【必须】使用参数化查询

- 使用参数化SQL语句，强制区分数据和命令，避免产生SQL注入漏洞。

```python
# 错误示例
import mysql.connector

mydb = mysql.connector.connect(
... ...
)

cur = mydb.cursor()
userid = get_id_from_user()
# 使用%直接格式化字符串拼接SQL语句
cur.execute("SELECT `id`, `password` FROM `auth_user` WHERE `id`=%s " % (userid,)) 
myresult = cur.fetchall()
```

```python
# 安全示例
import mysql.connector

mydb = mysql.connector.connect(
... ...
)
cur = mydb.cursor()
userid = get_id_from_user()
# 将元组以参数的形式传入
cur.execute("SELECT `id`, `password` FROM `auth_user` WHERE `id`=%s " , (userid,))
myresult = cur.fetchall()
```

* 推荐使用ORM框架来操作数据库，如：使用`SQLAlchemy`。

```python
# 安装sqlalchemy并初始化数据库连接
# pip install sqlalchemy
from sqlalchemy import create_engine
# 初始化数据库连接，修改为你的数据库用户名和密码
engine = create_engine('mysql+mysqlconnector://user:password@host:port/DATABASE')
```

```python
# 引用数据类型
from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
# 定义 Player 对象:
class Player(Base):
    # 表的名字:
    __tablename__ = 'player'

    # 表的结构:
    player_id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer)
    player_name = Column(String(255))
    height = Column(Float(3, 2))
```

```python
# 增删改查
from sqlalchemy.orm import sessionmaker
# 创建 DBSession 类型:
DBSession = sessionmaker(bind=engine)
# 创建 session 对象:
session = DBSession()

# 增:
new_player = Player(team_id=101, player_name="Tom", height=1.98)
session.add(new_player)
# 删:
row = session.query(Player).filter(Player.player_name=="Tom").first()
session.delete(row)
# 改:
row = session.query(Player).filter(Player.player_name=="Tom").first()
row.height = 1.99
# 查:
rows = session.query(Player).filter(Player.height >= 1.88).all()

# 提交即保存到数据库:
session.commit()
# 关闭 session:
session.close()
```

#### 1.2.2 【必须】验证输入并保持参数绑定

- 输入格式、长度和类型验证是参数绑定的补充，不能替代参数化查询。
- 不得使用删除引号、注释符或其他字符的黑名单处理后继续拼接数据值。普通 ORM 的参数化过滤不应仅因接收外部输入就认定为 SQL 注入。
- 表名、列名及排序方向不能作为普通数据值绑定时，将用户选择映射到应用固定白名单中的标识符，不直接拼接用户原文。

### 1.3 执行命令

#### 1.3.1 【建议】避免直接调用函数执行系统命令

- 相关功能的实现应避免直接调用系统命令（如`os.system()`、`os.popen()`、`subprocess.call()`等），优先使用其他同类操作进行代替，比如：通过文件系统API进行文件操作而非直接调用操作系统命令
- 如评估无法避免，执行命令应避免拼接外部数据，同时进行执行命令的白名单限制。

#### 1.3.2 【必须】安全传递外部程序参数

- 不把不可信数据拼接成 shell 命令。优先使用库接口；确需启动外部程序时固定程序和操作，把参数作为列表传递并关闭 shell，校验参数业务范围及选项注入风险。
- 不把字符黑名单、URL 前缀替换或一次转义作为通用安全保证。`shlex.quote()` 只针对 POSIX shell，不保证适用于 Windows shell。
- 要沿调用链检查真正执行命令的位置。一个没有外部可控调用路径的辅助函数，不能仅因名字或危险 API 就认定已存在可利用的命令注入。

#### 1.3.3 【必须】禁止不安全的代码执行

- 禁止把不可信输入当作程序执行，包括 `eval`、`exec`、第三方表达式求值接口及动态导入路径。受限表达式功能应采用明确的数据语法、白名单操作和资源限制，不能假定带有 eval 名称的沙箱天然安全。
- 不允许外部输入覆写会被导入执行的源文件；不得把用户输入当作服务端模板源码编译或渲染。模板应由应用控制，用户数据通过上下文变量传入。
- 判断第三方求值接口时核对实际库版本、可传入对象及安全边界，区分危险能力与已经证明的利用条件。

#### 1.3.4 【必须】服务端模板与数据分离

- 由应用选择固定模板；用户内容只作为模板数据传入。把用户内容写成模板文件后在另一个请求中渲染，仍属于模板源码注入，需要跟踪跨请求的写入和使用路径。

### 1.4 文件操作

#### 1.4.1 【必须】文件类型限制

- 通过白名单对上传或者下载的文件类型、大小进行严格校验。仅允许业务所需文件类型上传，避免上传木马、WebShell等文件。

```python
import os
  
ALLOWED_EXTENSIONS = ['txt','jpg','png']
  
def allowed_file(filename):
    if ('.' in filename and 
        '..' not in filename and 
        os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS):
        
        return filename
    return None
```

#### 1.4.2 【必须】禁止外部文件存储于可执行目录

- 禁止外部文件存储于WEB容器的可执行目录（appBase）。建议使用 [tempfile](https://docs.python.org/3/library/tempfile.html) 库处理临时文件和临时目录。


#### 1.4.3 【必须】避免路径穿越

- 对文件路径进行规范化并检查最终解析路径确实位于允许的根目录中；仅检查字符串前缀或删除 `..` 不构成充分防护。
- 使用路径组件比较，并考虑绝对路径、分隔符、大小写和符号链接。示例仅适用于根目录受信任且攻击者不能并发修改目录项的情况：

```python
from pathlib import Path

root = Path('/srv/app/uploads').resolve()
candidate = (root / user_filename).resolve()
if root not in candidate.parents:
    raise ValueError('Path outside upload directory')
```

- 攻击者可修改符号链接或目录时，还需使用安全的目录句柄及不跟随链接的文件操作等手段，防止检查与打开之间的竞态。

#### 1.4.4 【必须】禁用XML外部实体的方法

* 禁用XML外部实体的方法，来预防XXE攻击。

    ```python
    from lxml import etree
      
    xmlData = etree.parse(xmlSource,etree.XMLParser(resolve_entities=False))
    ```

#### 1.4.5 【必须】禁用不安全的反序列化函数

- 不对不可信数据调用 `pickle.load/loads` 或其他可恢复任意对象、触发代码执行的反序列化接口；Base64 解码不建立信任。
- 对不可信 YAML 使用 `yaml.safe_load` 或等价安全 Loader，不使用 `yaml.Loader`、`yaml.UnsafeLoader`、`yaml.unsafe_load`，也不注册可恢复任意对象的构造器。核对实际 PyYAML 版本和 Loader 参数。
- 优先采用有结构校验的纯数据格式。服务端对固定可信对象的序列化本身，不等于不可信对象反序列化漏洞。

#### 1.4.6 【建议】避免路径拼接

- 文件目录避免外部参数拼接。保存文件目录建议后台写死并对文件名进行校验（字符类型、长度）。


#### 1.4.7 【建议】文件名hash化处理

- 建议文件保存时，将文件名替换为随机字符串。

```python
import uuid

def random_filename(filename):
    ext = os.path.splitext(filename)[1]
    new_filename = uuid.uuid4().hex + ext
    return new_filename
```



### 1.5 网络请求

#### 1.5.1 【必须】限定访问网络资源地址范围

- 业务只需访问固定服务时，使用明确的协议、主机和端口白名单；开放式外部抓取则限制协议、端口及可访问的网络范围。
- 校验解析后的 IPv4、IPv6 地址和所有 DNS 解析结果，拒绝未经业务授权的回环、私网、链路本地、云元数据及其他特殊目的地址。考虑地址规范化和 DNS 重绑定，实际连接不得转向未验证的目标。
- 默认关闭自动跳转。确需跳转时，每次跳转重新完整验证协议、目标及解析地址，并限制次数；未验证前不得发起后续请求。
- 可信内部服务调用与面向用户的开放抓取不是同一种信任边界；不能无条件禁止所有内部网络请求。

### 1.6 响应输出

#### 1.6.1 【必须】设置正确的HTTP响应包类型
响应包的HTTP头“Content-Type”必须正确配置响应包的类型，禁止非HTML类型的响应包设置为“text/html”。

#### 1.6.2 【必须】设置安全的HTTP响应头

- 按响应类型设置 `X-Content-Type-Options: nosniff`，并采用合适的点击劫持防护，例如 `X-Frame-Options: DENY/SAMEORIGIN` 或相应 CSP。不能把已废弃且支持不一致的 ALLOW-FROM 当作通用解决办法。
- 身份凭据 Cookie 设置适当的 HttpOnly、Secure 和 SameSite 属性；自定义 Cookie 也需逐项检查，不能只依赖框架默认会话 Cookie 设置。HTTPS、安全属性和 CSRF 校验需要协同，不能以其中一个替代其他控制。

#### 1.6.3 【必须】对外输出页面包含第三方数据时须进行编码处理

- 按 HTML 文本、属性、URL、JavaScript 等具体输出位置选择正确编码；不要对整份 HTML 统一转义，也不要把 HTML 自动转义当作 JavaScript 表达式的保护。
- 普通文本使用模板自动转义或 DOM 的 textContent/value；需要富文本时采用维护中的 HTML 净化器，并按实际解析上下文验证。
- 不把用户输入作为脚本、事件处理器或模板源码；不得把不可信内容直接交给 innerHTML、document.write 或标记为 safe。不能只删除 script 标签或依赖 CSP 就视为消除了 XSS。

### 1.7 数据输出

#### 1.7.1 【必须】敏感数据加密存储

- 对必须可恢复的个人敏感数据，按数据分类使用有认证的加密方案、独立密钥管理和访问控制，数据库字段类型本身不构成加密。
- SHA2 是哈希算法，不是可恢复的加密算法。口令按口令存储规则处理；不得把普通 SHA-256 摘要当作保护密码的充分措施。
- 敏感数据使用独立存储和访问控制；不再需要的临时文件或缓存及时删除。

#### 1.7.2 【必须】敏感信息必须由后台进行脱敏处理

- 敏感信息须再后台进行脱敏后返回，禁止接口返回敏感信息交由前端/客户端进行脱敏处理。


#### 1.7.3 【必须】高敏感信息禁止存储、展示

- 口令、认证答案和内部长期凭据不得写入日志、错误页或返回给无权获知的调用者；非金融业务不得保存信用卡 CVV。
- HTML 注释、隐藏元素和浏览器 JavaScript 中的值同样已发送给客户端，不能充当保密手段。不要把内部授权密钥或不需要前端持久保存的会话凭据写入 localStorage。
- 敏感 API、调试日志、配置内容和静态资源均需按身份、对象权限及数据最小化规则控制访问；接口返回 JSON 或 text/plain 不会自动使敏感内容安全。
- 信息泄露需有敏感数据及相应的访问、发送或存储路径；仅在服务端存在的未使用普通常量，不等于已向客户端泄露。

#### 1.7.4 【必须】个人敏感信息脱敏展示

在满足业务需求的情况下，个人敏感信息需脱敏展示。

- 身份证只显示第一位和最后一位字符，如3****************1。
- 移动电话号码隐藏中间6位字符，如134******48。
- 工作地址/家庭地址最多显示到“区”一级。
- 银行卡号仅显示最后4位字符，如************8639

#### 1.7.5 【必须】保护管理后台

- 管理后台必须进行认证、授权及必要的网络访问限制。修改默认 URL 只可作为降低自动化探测的附加措施，不能代替访问控制；保留默认路径本身不自动构成可利用漏洞。

### 1.8 权限管理

#### 1.8.1 【必须】默认鉴权

- 除非资源完全可对外开放，否则系统默认进行身份认证（使用白名单的方式放开不需要认证的接口或页面）。


#### 1.8.2 【必须】授权遵循最小权限原则

- 程序默认用户应不具备任何操作权限。


#### 1.8.3 【必须】避免越权访问

- 对于非公共操作，应当校验当前访问账号进行操作权限（常见于CMS）和数据权限校验。


1. 验证当前用户的登录态；
2. 从可信结构中获取经过校验的当前请求账号的身份信息（如：session），禁止从用户请求参数或Cookie中获取外部传入不可信用户身份直接进行查询；
3. 校验当前用户是否具备该操作权限；
4. 校验当前用户是否具备所操作数据的权限；
5. 校验当前操作是否账户是否预期账户。

#### 1.8.4 【建议】及时清理不需要的权限

- 程序应定期清理非必需用户的权限。


#### 1.8.5 【必须】可信会话与授权决策

- 身份从经过验证的服务端会话或验证完整性、有效期等约束的令牌取得。可预测用户 ID、明文用户名、Base64 编码内容或未签名 Cookie 都不能单独作为身份或角色证明。
- User-Agent、X-Host、X-Forwarded-For 等客户端可提交的头部不能直接决定管理员身份。依赖代理信息时，确认代理清洗并重写头部，且客户端不能绕过代理。
- 区分已登录和已授权；每个非公开请求都应验证具体操作及对象的权限，包括直接 URL 访问、API 和敏感静态资源。
- 访问控制不能依赖前端隐藏、HTML 注释、客户端校验或未公开的管理路径。对外返回的注释和脚本中不得包含内部鉴权秘密、绕过口令或敏感数据。

#### 1.8.6 【必须】浏览器请求防伪造

- 依赖浏览器自动携带的会话或其他凭据执行敏感操作时，应使用适用的 CSRF 防护。登录、重置状态或创建会话同样需要检查，不只检查转账等业务操作。
- GET、HEAD 等安全方法不应修改账号、验证码、会话或其他安全相关状态。需要变更时使用合适方法并验证请求来源与 CSRF 令牌。
- csrf_exempt 必须有替代防护或明确的、不依赖浏览器自动凭据的调用边界；不能只看装饰器就认定漏洞，也不能只添加中间件却保留可绕过的豁免。

### 1.9 异常处理

#### 1.9.1 【必须】不向对外错误提示

* 应合理使用`try/except/finally` 处理系统异常，避免出错信息输出到前端。
* 对外环境禁止开启debug模式，或将程序运行日志输出到前端。

#### 1.9.2 【必须】禁止异常抛出敏感信息

### 1.10 Flask安全

#### 1.10.1 【必须】生产环境关闭调试模式

#### 1.10.2 【建议】遵循Flask安全规范

- 参考Flask文档中的安全注意事项 https://flask.palletsprojects.com/en/latest/security/


### 1.11 Django安全

#### 1.11.1 【必须】生产环境关闭调试模式

#### 1.11.2 【建议】保持Django自带的安全特性开启

- 保持Django自带的安全特性开启 https://docs.djangoproject.com/en/4.2/topics/security/

- 在默认配置下，Django自带的安全特性对XSS、CSRF、SQL注入、点击劫持等类型漏洞可以起到较好防护效果。应尽量避免关闭这些安全特性。

