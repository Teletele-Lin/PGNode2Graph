from django.db import models
import uuid
from django.utils import timezone

class Visualization(models.Model):
    """存储每次可视化结果的模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, blank=True, help_text="自动生成的名称")
    input_data = models.TextField(help_text="用户输入的原始序列化字符串")
    processed_data = models.TextField(help_text="提取最外层花括号后的数据", blank=True)
    dot_source = models.TextField(help_text="Graphviz DOT源码", blank=True)
    graph_image = models.ImageField(upload_to='visualizations/%Y/%m/%d/', blank=True, null=True)
    session_key = models.CharField(max_length=100, blank=True, help_text="用户会话ID，用于隔离数据")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '可视化记录'
        verbose_name_plural = '可视化记录'
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
