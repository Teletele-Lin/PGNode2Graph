import json
import re
import uuid
import logging
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.conf import settings
import graphviz
import tempfile
import os
from .models import Visualization

# 导入新的node2dot模块
from .node2dot import node2dot

# 设置日志
logger = logging.getLogger(__name__)

def generate_dot_from_postgresql(data_str, skip_empty=False):
    """
    将PostgreSQL调试格式转换为Graphviz DOT格式
    使用新的node2dot.py实现（基于node2dot.c）
    """
    try:
        # 使用新的node2dot模块进行转换
        dot_source = node2dot(data_str, skip_empty=skip_empty, use_color=True)
        return dot_source
    except Exception as e:
        # 如果转换失败，返回一个简单的错误图
        print(f"Error converting PostgreSQL format: {e}")
        return f'digraph G {{\n  node [shape=box, style=filled, fillcolor="lightgray"];\n  "Error: {str(e)[:50]}...";\n}}'

def generate_dot_from_dict(data):
    """
    从解析后的字典生成DOT格式
    """
    dot_lines = ['digraph G {', '  node [shape=box, style=filled];', '  rankdir=LR;']

    # 颜色映射，根据节点类型分配不同颜色
    color_map = {
        'rawstmt': 'lightblue',
        'selectstmt': 'lightgreen',
        'restarget': 'lightyellow',
        'columnref': 'lightcoral',
        'rangevar': 'lightpink',
        'a_expr': 'lightsalmon',
        'a_const': 'lightseagreen',
        'a_star': 'lightsteelblue',
        'query': 'lightblue',
        'plan': 'lightgreen',
        'parse': 'lightyellow',
        'expr': 'lightcoral',
        'scan': 'lightpink',
        'join': 'lightsalmon',
        'agg': 'lightseagreen',
        'sort': 'lightsteelblue',
        'default': 'lightgray'
    }

    # 递归遍历字典，生成节点和边
    node_counter = 0
    node_map = {}  # 存储节点ID映射

    def process_node(obj, parent_id=None, edge_label=""):
        nonlocal node_counter
        if isinstance(obj, dict):
            node_id = f'node{node_counter}'
            node_counter += 1

            # 确定节点类型和标签
            node_type = obj.get('type', 'default').lower()
            node_label = obj.get('type', 'default')
            
            # 如果有特定字段作为标签，使用它们
            label_parts = [node_type]
            if 'relname' in obj:
                label_parts.append(f"rel: {obj['relname']}")
            if 'name' in obj and obj['name']:
                label_parts.append(f"name: {obj['name']}")
            if 'val' in obj and obj['val'] is not None:
                label_parts.append(f"val: {obj['val']}")
                
            node_label = "\\n".join(label_parts)

            # 获取颜色
            fillcolor = color_map.get(node_type, color_map['default'])

            # 创建节点
            dot_lines.append(f'  {node_id} [label="{node_label}", fillcolor="{fillcolor}"];')
            node_map[id(obj)] = node_id

            # 如果有父节点，创建边
            if parent_id:
                dot_lines.append(f'  {parent_id} -> {node_id} [label="{edge_label}"];')

            # 处理子节点
            for key, value in obj.items():
                if key not in ['type', 'relname', 'name', 'val']:
                    if isinstance(value, (dict, list)):
                        process_node(value, node_id, key)
                    elif value is not None:
                        # 将简单值作为叶子节点
                        leaf_id = f'node{node_counter}'
                        node_counter += 1
                        display_value = str(value)
                        if len(display_value) > 30:
                            display_value = display_value[:27] + "..."
                        dot_lines.append(f'  {leaf_id} [label="{key}: {display_value}", shape=ellipse, fillcolor="white"];')
                        dot_lines.append(f'  {node_id} -> {leaf_id} [label=""];')

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                process_node(item, parent_id, f"{edge_label}[{i}]")

    process_node(data)
    dot_lines.append('}')
    return '\n'.join(dot_lines)

def index(request):
    """首页，显示输入表单和历史记录"""
    # 不再限制会话，显示所有记录（最新10条）
    visualizations = Visualization.objects.all()[:10]
    return render(request, 'visualizer/index.html', {'visualizations': visualizations})

@csrf_exempt
def generate_graph(request):
    """接收数据，生成图形并保存"""
    if request.method == 'POST':
        input_data = request.POST.get('data', '') or request.body.decode('utf-8')
        if not input_data:
            return JsonResponse({'error': 'No data provided'}, status=400)

        # 获取 skip_empty 参数，默认为 False
        skip_empty_str = request.POST.get('skip_empty', 'false')
        skip_empty = skip_empty_str.lower() == 'true'

        # 保存会话ID用于用户隔离
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        
        # 尝试多种解析方式
        dot_source = None
        
        # 首先尝试作为PostgreSQL调试格式解析
        try:
            dot_source = generate_dot_from_postgresql(input_data, skip_empty=skip_empty)
            if not dot_source or "Error:" in dot_source:
                dot_source = None
        except Exception as e:
            print(f"PostgreSQL parse error: {e}")
            dot_source = None
        
        # 如果失败，尝试作为JSON解析
        if not dot_source:
            try:
                # 尝试提取最外层花括号
                pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                match = re.search(pattern, input_data)
                if match:
                    json_str = match.group(0)
                    data = json.loads(json_str)
                    dot_source = generate_dot_from_dict(data)
                else:
                    # 如果不是有效JSON，则作为纯文本处理
                    dot_source = f'digraph G {{\n  node [shape=box, style=filled, fillcolor="lightgray"];\n  "{input_data[:50]}...";\n}}'
            except json.JSONDecodeError:
                # 最后兜底方案
                dot_source = f'digraph G {{\n  node [shape=box, style=filled, fillcolor="lightgray"];\n  "{input_data[:50]}...";\n}}'

        # 创建自动生成的名称
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        auto_name = f'Visualization_{timestamp}'

        # 创建可视化记录，关联会话
        viz = Visualization.objects.create(
            name=auto_name,
            input_data=input_data[:10000],  # 限制长度
            processed_data=input_data[:500],  # 保存前500字符作为预览
            dot_source=dot_source,
            session_key=session_key  # 存储会话ID
        )

        # 不再自动生成图像，只保存DOT源码
        # 注意：移除了graphviz生成图像的部分
        
        return JsonResponse({
            'success': True,
            'id': str(viz.id),
            'name': viz.name,
            'dot_source': dot_source,
            'created_at': viz.created_at.isoformat()
        })

    return JsonResponse({'error': 'Method not allowed'}, status=405)

def generate_svg_from_dot(dot_source):
    """使用Graphviz将DOT源码转换为SVG字符串"""
    try:
        dot = graphviz.Source(dot_source)
        svg_bytes = dot.pipe(format='svg')
        return svg_bytes.decode('utf-8')
    except Exception as e:
        # 如果生成失败，返回一个简单的错误SVG
        print(f"Error generating SVG: {e}")
        return f'''<svg width="400" height="100" xmlns="http://www.w3.org/2000/svg">
            <rect width="400" height="100" fill="#f8d7da"/>
            <text x="10" y="30" font-family="Arial" font-size="14" fill="#721c24">
                Error generating SVG: {str(e)[:100]}
            </text>
            <text x="10" y="60" font-family="Arial" font-size="12" fill="#721c24">
                Please check if Graphviz is installed on the server.
            </text>
        </svg>'''

def view_history(request, viz_id=None):
    """查看历史记录"""
    if viz_id:
        # 查看任意记录，无会话限制
        viz = get_object_or_404(Visualization, id=viz_id)
        # 生成SVG字符串
        svg_content = generate_svg_from_dot(viz.dot_source)
        return render(request, 'visualizer/detail.html', {
            'viz': viz,
            'svg_content': svg_content
        })

    # 显示所有记录
    visualizations = Visualization.objects.all().order_by('-created_at')
    return render(request, 'visualizer/history.html', {'visualizations': visualizations})

def get_dot_source(request, viz_id):
    """获取特定记录的DOT源码"""
    # 获取任意记录，无会话限制
    viz = get_object_or_404(Visualization, id=viz_id)
    return HttpResponse(viz.dot_source, content_type='text/plain')

def delete_visualization(request, viz_id):
    """删除可视化记录"""
    if request.method == 'POST':
        # 删除任意记录，无会话限制
        viz = get_object_or_404(Visualization, id=viz_id)
        # 获取客户端IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[0]
        else:
            client_ip = request.META.get('REMOTE_ADDR', '未知IP')
        # 记录删除日志，包含客户端IP
        logger.info(
            f"可视化记录被删除: ID={viz_id}, 名称='{viz.name}', "
            f"创建时间={viz.created_at}, 输入数据长度={len(viz.input_data)}, "
            f"客户端IP={client_ip}"
        )
        viz.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def open_svg(request, viz_id):
    """打开SVG在独立页面，支持自由缩放"""
    viz = get_object_or_404(Visualization, id=viz_id)
    # 生成SVG字符串
    svg_content = generate_svg_from_dot(viz.dot_source)
    return render(request, 'visualizer/svg_viewer.html', {
        'viz': viz,
        'svg_content': svg_content
    })
