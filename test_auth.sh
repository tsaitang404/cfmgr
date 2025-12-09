#!/bin/bash
# API 认证测试脚本

BASE_URL="http://localhost:8787"
API_KEY="your-test-api-key"

echo "======================================"
echo "cfmgr API 认证测试"
echo "======================================"
echo ""

echo "1. 测试公开路由（无需认证）"
echo "-----------------------------------"
echo "GET /health"
curl -s "$BASE_URL/health" | jq . 2>/dev/null || curl -s "$BASE_URL/health"
echo ""

echo "GET /"
curl -s "$BASE_URL/" | jq .service 2>/dev/null || curl -s "$BASE_URL/"
echo ""

echo ""
echo "2. 测试受保护路由"
echo "-----------------------------------"
echo "如果配置了 API_KEY，以下请求需要认证"
echo ""

echo "GET /d1/tables (无认证)"
curl -s "$BASE_URL/d1/tables"
echo ""

echo "GET /d1/tables (带认证)"
curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/d1/tables"
echo ""

echo ""
echo "3. 配置说明"
echo "-----------------------------------"
echo "当前配置: 无 API_KEY（所有端点公开访问）"
echo ""
echo "要启用认证，在 wrangler.toml 中添加:"
echo "[vars]"
echo 'API_KEY = "your-secret-key"'
