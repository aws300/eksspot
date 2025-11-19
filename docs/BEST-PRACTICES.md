# 最佳实践

## 实例类型选择

### 1. 基于 Spot Placement Score

```bash
# 查询评分
./scripts/query-spot-score.sh us-west-2 8

# 选择评分 >= 8 的实例类型
```

**推荐实例系列**:
- C5/C6i: 计算优化（评分 9/10）
- M5/M6i: 通用型（评分 9/10）
- R5/R6i: 内存优化（评分 9/10）

### 2. 使用多个实例系列

```yaml
- key: eks.amazonaws.com/instance-family
  operator: In
  values:
    - c5
    - c6i
    - m5
    - m6i
```

**优点**:
- 增加 Spot 可用性
- 降低中断风险
- 提高调度灵活性

### 3. 合理的实例大小范围

```yaml
- key: eks.amazonaws.com/instance-cpu
  operator: In
  values:
    - "2"   # large
    - "4"   # xlarge
    - "8"   # 2xlarge
    - "16"  # 4xlarge
```

## NodePool 配置

### 1. 权重策略

```yaml
# Spot NodePool - 默认权重（优先）
metadata:
  name: workload-spot
# 不设置 weight

# On-Demand NodePool - 低权重（备用）
metadata:
  name: workload-ondemand
spec:
  weight: 10
```

### 2. 统一标签和污点

```yaml
# 两个 NodePool 使用相同的标签和污点
labels:
  workload-type: flexible
taints:
  - key: workload-type
    value: flexible
    effect: NoSchedule
```

**优点**: Pod 可以在两种节点类型间无缝切换

### 3. 资源限制

```yaml
limits:
  cpu: "100"
  memory: 200Gi
```

**建议**:
- 根据实际需求设置
- 避免无限制扩展
- 定期审查和调整

### 4. 整合策略

```yaml
disruption:
  consolidationPolicy: WhenEmpty
  consolidateAfter: 30s
```

**说明**:
- `WhenEmpty`: 节点空闲时整合
- `30s`: 快速回收空闲节点

## Pod 配置

### 1. Tolerations

```yaml
tolerations:
  - key: workload-type
    operator: Equal
    value: flexible
    effect: NoSchedule
```

### 2. NodeSelector

```yaml
nodeSelector:
  workload-type: flexible
```

### 3. 亲和性配置

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100  # Spot 优先
        preference:
          matchExpressions:
            - key: capacity-type
              operator: In
              values: [spot]
      - weight: 50   # On-Demand 备用
        preference:
          matchExpressions:
            - key: capacity-type
              operator: In
              values: [ondemand]
```

### 4. 资源请求

```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

**建议**:
- 设置合理的 requests
- limits 略高于 requests
- 避免过度分配

## 应用设计

### 1. 无状态应用

✅ **推荐**: 
- Web 服务
- API 服务
- 批处理任务
- 数据处理

❌ **不推荐**:
- 数据库
- 有状态服务
- 关键业务系统

### 2. 优雅关闭

```yaml
spec:
  terminationGracePeriodSeconds: 120
  containers:
    - name: app
      lifecycle:
        preStop:
          exec:
            command: ["/bin/sh", "-c", "sleep 15"]
```

### 3. 健康检查

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 4. 多副本部署

```yaml
spec:
  replicas: 3  # 至少 3 个副本
```

### 5. PodDisruptionBudget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

## 监控和告警

### 1. 关键指标

```bash
# 节点类型分布
kubectl get nodes -L karpenter.sh/capacity-type

# Spot 节点数量
kubectl get nodes -l capacity-type=spot --no-headers | wc -l

# On-Demand 节点数量
kubectl get nodes -l capacity-type=ondemand --no-headers | wc -l
```

### 2. 告警规则

| 指标 | 阈值 | 说明 |
|------|------|------|
| Spot 中断率 | > 10% | 考虑调整实例类型 |
| On-Demand 使用率 | > 30% | Spot 可用性下降 |
| 节点创建失败 | > 5 次/小时 | 检查配置和配额 |
| 成本异常 | > 预算 20% | 检查资源使用 |

### 3. 日志监控

```bash
# Karpenter 日志
kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter -f

# 过滤关键事件
kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter | grep -i "spot\|error"
```

## 成本优化

### 1. 定期更新配置

```bash
# 每周查询一次 Spot 评分
./scripts/query-spot-score.sh us-west-2 8

# 根据结果更新 NodePool
./scripts/generate-nodepool.sh us-west-2 8 > nodepool-updated.yaml
kubectl apply -f nodepool-updated.yaml
```

### 2. 调整实例大小

根据实际使用情况调整：

```yaml
# 小型工作负载
- key: eks.amazonaws.com/instance-cpu
  operator: In
  values: ["2", "4"]

# 大型工作负载
- key: eks.amazonaws.com/instance-cpu
  operator: In
  values: ["8", "16", "32"]
```

### 3. 优化资源请求

```bash
# 查看实际使用
kubectl top pods
kubectl top nodes

# 调整 requests 和 limits
```

## 故障处理

### 1. Spot 频繁中断

**原因**:
- 实例类型可用性低
- 单一实例类型
- 区域容量不足

**解决方案**:
- 增加实例类型多样性
- 查询最新 Spot 评分
- 考虑多区域部署

### 2. Pod 无法调度

**检查**:
```bash
kubectl describe pod <pod-name>
```

**常见原因**:
- tolerations 配置错误
- nodeSelector 不匹配
- 资源不足

### 3. 节点未创建

**检查**:
```bash
kubectl get nodepools -o yaml
kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter
```

**常见原因**:
- NodePool 配置错误
- 实例类型不可用
- 配额限制

## 安全最佳实践

### 1. 网络策略

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-network-policy
spec:
  podSelector:
    matchLabels:
      app: myapp
  policyTypes:
    - Ingress
    - Egress
```

### 2. Pod Security Standards

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: myapp
  labels:
    pod-security.kubernetes.io/enforce: restricted
```

### 3. IRSA 权限

使用最小权限原则：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}
```

## 测试策略

### 1. 定期测试

```bash
# 每月测试一次故障转移
./scripts/test-failover.sh

# 每月测试一次实例回收
./scripts/test-reclaim.sh
```

### 2. 压力测试

```bash
# 扩展副本数
kubectl scale deployment myapp --replicas=20

# 观察调度行为
watch kubectl get pods -o wide
```

### 3. 混沌工程

使用 AWS FIS 模拟真实 Spot 中断。

## 维护计划

### 每周

- 查询 Spot 评分
- 检查成本报告
- 审查告警

### 每月

- 运行故障转移测试
- 更新 NodePool 配置
- 审查资源使用

### 每季度

- 评估实例类型选择
- 优化成本策略
- 更新文档

## 常见问题

### Q: 如何选择实例类型？

A: 使用 `query-spot-score.sh` 查询评分，选择评分 >= 8 的实例类型。

### Q: Spot 中断率多少是正常的？

A: 通常 < 5% 是正常的，> 10% 需要调整配置。

### Q: 如何平衡成本和可用性？

A: 
- 使用多个实例类型
- 配置合理的 On-Demand 比例
- 定期测试故障转移

### Q: 是否需要手动干预？

A: 通常不需要，Karpenter 会自动处理。但建议定期检查和测试。
