# Node2Graph 部署指南

## 环境要求
- Python 3.8+
- Django 6.0+
- Graphviz (系统依赖)

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 环境变量配置
创建 `.env` 文件或设置系统环境变量：

```bash
# 生产环境密钥（必须修改）
export DJANGO_SECRET_KEY='your-strong-secret-key-here-minimum-50-characters'

# 允许访问的主机（逗号分隔）
export DJANGO_ALLOWED_HOSTS='your-domain.com,www.your-domain.com'

# 可选：数据库配置
# export DATABASE_URL='postgres://user:password@localhost/dbname'
```

生成强密钥：
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. 数据库迁移
```bash
python manage.py migrate
```

### 4. 收集静态文件
```bash
python manage.py collectstatic --noinput
```

### 5. 创建超级用户（可选）
```bash
python manage.py createsuperuser
```

## 生产环境配置

### 安全设置
已配置的安全设置包括：
- DEBUG=False
- HSTS 启用（1年）
- 安全 Cookie（SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE）
- 环境变量密钥支持

### SSL/HTTPS 配置
如需启用 HTTPS，在 settings.py 中设置：
```python
SECURE_SSL_REDIRECT = True
```

## 运行服务器

### 开发环境
```bash
python manage.py runserver
```

### 生产环境（使用 Gunicorn）
```bash
pip install gunicorn
gunicorn node2graph.wsgi:application
```

### 生产环境（使用 Gunicorn + Nginx）
```bash
# Gunicorn 配置示例
gunicorn --workers 3 --bind 0.0.0.0:8000 node2graph.wsgi:application

# Nginx 配置参考
# server {
#     listen 80;
#     server_name your-domain.com;
#     
#     location /static/ {
#         alias /path/to/staticfiles/;
#     }
#     
#     location / {
#         proxy_pass http://127.0.0.1:8000;
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#     }
# }
```

## 维护任务

### 清理旧数据
```bash
# 清理30天前的可视化记录
python manage.py shell -c "
from visualizer.models import Visualization
from django.utils import timezone
from datetime import timedelta

old_date = timezone.now() - timedelta(days=30)
old_viz = Visualization.objects.filter(created_at__lt=old_date)
count = old_viz.count()
for viz in old_viz:
    if viz.graph_image:
        viz.graph_image.delete()
    viz.delete()
print(f'Deleted {count} old records')
"
```

### 备份数据库
```bash
# SQLite 备份
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d)

# 或导出数据
python manage.py dumpdata --indent 2 > backup_$(date +%Y%m%d).json
```

## 故障排除

### 常见问题
1. **静态文件404错误**：确保运行了 `collectstatic` 命令
2. **数据库权限错误**：检查数据库文件读写权限
3. **ALLOWED_HOSTS错误**：正确设置 DJANGO_ALLOWED_HOSTS 环境变量

### 日志查看
```bash
# 查看应用日志
tail -f deletion.log

# 查看Django日志
python manage.py runserver --verbosity 2
```

## 版本信息
- Django: 6.0
- Python: 3.13
- Graphviz: 0.21
- Pillow: 12.0.0

## 许可证
[根据项目实际情况填写]
